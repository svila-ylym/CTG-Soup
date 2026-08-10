from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt
import re

from app.models.database import EmailVerification, get_db, User, UserStatus
from app.schemas import (
    EmailVerificationRequest,
    EmailVerificationResendRequest,
    PasswordResetEmailRequest,
    PasswordResetRequest,
    ChangePasswordRequest,
    MessageResponse,
    RefreshTokenRequest,
    Token,
    TokenData,
    UserCreate,
    UserResponse,
)
from app.core.config import get_settings
from app.models.database import UserRole
from app.services.moderation_locks import lock_user_punishments
from app.services.punishments import (
    active_punishment_types,
    effective_user_status,
    sync_user_punishment_status,
)
from app.services.email_verification import (
    hash_verification_token,
    new_verification_token,
    verification_expiry,
)
from app.services.rate_limiter import rate_limiter
from app.services.pending_accounts import allocate_user_uid
from app.utils.email import get_smtp_service

router = APIRouter()

settings = get_settings()

# OAuth2方案
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
optional_oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/login",
    auto_error=False,
)
smtp_service = get_smtp_service()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except (TypeError, ValueError):
        return False


def get_password_hash(password: str) -> str:
    """获取密码哈希"""
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > 72:
        raise ValueError("密码不能超过72字节")
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")


def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """创建访问令牌"""
    to_encode = data.copy()
    if "sub" in to_encode:
        to_encode["sub"] = str(to_encode["sub"])
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "token_type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """创建刷新令牌"""
    to_encode = data.copy()
    if "sub" in to_encode:
        to_encode["sub"] = str(to_encode["sub"])
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "token_type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_token(token: str, expected_type: str) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("token_type") != expected_type or payload.get("sub") is None:
            raise credentials_exception
        return payload
    except JWTError as exc:
        raise credentials_exception from exc


def _resolve_user_from_token(token: str, db: Session) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_token(token, expected_type="access")
    try:
        token_data = TokenData(user_id=int(payload["sub"]))
    except (TypeError, ValueError) as exc:
        raise credentials_exception from exc

    user = db.query(User).filter(User.uid == token_data.user_id).first()
    if user is None:
        raise credentials_exception
    if sync_user_punishment_status(db, user):
        db.commit()
        db.refresh(user)
    if payload.get("ver") != user.token_version:
        raise credentials_exception

    # 检查用户状态
    if user.status == UserStatus.BANNED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账户已被封禁"
        )
    if user.status == UserStatus.PENDING_EMAIL:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="请先完成邮箱验证",
        )

    return user


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """获取当前用户"""
    return _resolve_user_from_token(token, db)


async def get_optional_current_user(
    token: Optional[str] = Depends(optional_oauth2_scheme),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Return an authenticated user when a bearer token was supplied."""
    if token is None:
        return None
    return _resolve_user_from_token(token, db)


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """获取当前活跃用户"""
    if current_user.status not in [UserStatus.ACTIVE]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账户未激活"
        )
    return current_user


async def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """获取当前管理员用户"""
    if current_user.role not in [UserRole.ADMIN, UserRole.ROOT]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足"
        )
    return current_user


async def get_current_root_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """获取当前根用户"""
    if current_user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "ACCOUNT_INACTIVE", "message": "账户未激活"},
        )
    if current_user.role != UserRole.ROOT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "ROOT_REQUIRED", "message": "需要根用户权限"},
        )
    return current_user


def validate_email_domain(email: str) -> bool:
    """验证邮箱域名是否在白名单中"""
    if not settings.EMAIL_DOMAIN_WHITELIST:
        return True

    domain = email.split('@')[-1]
    return domain in settings.EMAIL_DOMAIN_WHITELIST


def _create_verification(
    db: Session,
    user: User,
    now: datetime,
) -> str:
    active_records = db.query(EmailVerification).filter(
        EmailVerification.user_uid == user.uid,
        EmailVerification.used_at.is_(None),
    ).all()
    for record in active_records:
        record.used_at = now

    token = new_verification_token()
    db.add(
        EmailVerification(
            user_uid=user.uid,
            token_hash=hash_verification_token(token),
            expires_at=verification_expiry(
                now,
                settings.VERIFICATION_CODE_EXPIRE_MINUTES,
            ),
        )
    )
    return token


def _request_ip(request: Optional[Request]) -> str:
    if request is None or request.client is None:
        return "unknown"
    return request.client.host


def _allow_verification_email(ip_address: str, email: str) -> bool:
    checks = (
        ("email-ip", ip_address, settings.EMAIL_VERIFICATION_IP_LIMIT, settings.EMAIL_VERIFICATION_IP_WINDOW_SECONDS),
        ("email-address", email, settings.EMAIL_VERIFICATION_EMAIL_LIMIT, settings.EMAIL_VERIFICATION_EMAIL_WINDOW_SECONDS),
        ("email-global", "all", settings.EMAIL_VERIFICATION_GLOBAL_LIMIT, settings.EMAIL_VERIFICATION_GLOBAL_WINDOW_SECONDS),
    )
    return all(
        rate_limiter.allow(scope, key, limit, window_seconds)
        for scope, key, limit, window_seconds in checks
    )


def _send_verification_email(email: str, username: str, token: str) -> bool:
    for _ in range(settings.SMTP_VERIFICATION_RETRY_ATTEMPTS):
        if smtp_service.send_verification_email(email, username, token):
            return True
    return False


def _allow_password_reset_email(ip_address: str, email: str) -> bool:
    checks = (
        ("password-reset-ip", ip_address, settings.EMAIL_VERIFICATION_IP_LIMIT, settings.EMAIL_VERIFICATION_IP_WINDOW_SECONDS),
        ("password-reset-address", email, settings.EMAIL_VERIFICATION_EMAIL_LIMIT, settings.EMAIL_VERIFICATION_EMAIL_WINDOW_SECONDS),
        ("password-reset-global", "all", settings.EMAIL_VERIFICATION_GLOBAL_LIMIT, settings.EMAIL_VERIFICATION_GLOBAL_WINDOW_SECONDS),
    )
    return all(
        rate_limiter.allow(scope, key, limit, window_seconds)
        for scope, key, limit, window_seconds in checks
    )


def _create_password_reset_token(user: User) -> str:
    payload = {
        "sub": str(user.uid),
        "username": user.username,
        "ver": user.token_version,
        "exp": datetime.utcnow() + timedelta(minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES),
        "token_type": "password_reset",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def _send_password_reset_email(email: str, username: str, token: str) -> bool:
    for _ in range(settings.SMTP_VERIFICATION_RETRY_ATTEMPTS):
        if smtp_service.send_password_reset_email(email, username, token):
            return True
    return False


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    request: Request = None,
):
    """用户注册"""
    # 检查用户名是否已存在
    username = user_data.username.strip()
    email = user_data.email.lower()
    existing_user = db.query(User).filter(
        (User.username == username) | (User.email == email)
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名或邮箱已被注册"
        )

    # 验证邮箱域名白名单
    if not validate_email_domain(email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱域名不在允许列表中"
        )

    if not _allow_verification_email(_request_ip(request), email):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="请求过于频繁，请稍后再试",
        )

    # 创建新用户
    hashed_password = get_password_hash(user_data.password)
    allocated_uid = allocate_user_uid(db)
    db_user = User(
        uid=allocated_uid,
        username=username,
        nickname=user_data.nickname,
        email=email,
        hashed_password=hashed_password,
        role=UserRole.USER,
        status=UserStatus.PENDING_EMAIL,
        allow_bulk_email=True,
    )

    try:
        db.add(db_user)
        db.flush()
        if db_user.uid == 1:
            db_user.role = UserRole.ROOT
        token = _create_verification(db, db_user, datetime.utcnow())
        db.commit()
        db.refresh(db_user)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名或邮箱已被注册",
        ) from exc

    if not _send_verification_email(db_user.email, db_user.username, token):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="账号已创建，但验证邮件发送失败，请稍后重新发送",
        )

    return db_user


@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(
    request: EmailVerificationRequest,
    db: Session = Depends(get_db),
):
    now = datetime.utcnow()
    verification = db.query(EmailVerification).filter(
        EmailVerification.token_hash == hash_verification_token(request.token),
    ).with_for_update().first()
    if verification is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "VERIFICATION_INVALID", "message": "验证链接无效"},
        )

    user = db.query(User).filter(User.uid == verification.user_uid).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "VERIFICATION_INVALID", "message": "验证链接无效"},
        )

    if verification.used_at is not None:
        if user.status == UserStatus.ACTIVE:
            return {"message": "邮箱已验证"}
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "VERIFICATION_INVALID", "message": "验证链接无效"},
        )

    if verification.expires_at < now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "VERIFICATION_EXPIRED",
                "message": "验证链接已过期，请重新发送",
            },
        )

    lock_user_punishments(db, user.uid)
    db.refresh(user)
    verification.used_at = now
    if user.status in {UserStatus.BANNED, UserStatus.SILENCED}:
        active_types = active_punishment_types(db, user.uid, now)
        user.status = effective_user_status(db, user, active_types)
    else:
        user.status = UserStatus.ACTIVE
    db.commit()
    return {"message": "邮箱验证成功，请登录"}


@router.post("/send-verification", response_model=MessageResponse)
async def resend_verification_email(
    request: EmailVerificationResendRequest,
    db: Session = Depends(get_db),
    http_request: Request = None,
):
    generic_message = "如果该邮箱存在且尚未验证，系统将发送验证邮件"
    user = db.query(User).filter(User.email == request.email.lower()).first()
    if user is None or user.status != UserStatus.PENDING_EMAIL:
        return {"message": generic_message}

    if not _allow_verification_email(_request_ip(http_request), user.email):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="请求过于频繁，请稍后再试",
        )

    now = datetime.utcnow()
    latest = db.query(EmailVerification).filter(
        EmailVerification.user_uid == user.uid,
    ).order_by(EmailVerification.created_at.desc()).first()
    if latest and (now - latest.created_at).total_seconds() < 60:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="请求过于频繁，请稍后再试",
        )

    token = _create_verification(db, user, now)
    db.commit()
    if not _send_verification_email(user.email, user.username, token):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="验证邮件发送失败，请稍后再试",
        )
    return {"message": generic_message}


@router.post("/reset-password-request", response_model=MessageResponse)
async def request_password_reset(
    request: PasswordResetEmailRequest,
    db: Session = Depends(get_db),
    http_request: Request = None,
):
    generic_message = "如果该邮箱已注册，系统将发送密码重置邮件"
    email = request.email.lower()
    if not _allow_password_reset_email(_request_ip(http_request), email):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="请求过于频繁，请稍后再试",
        )

    user = db.query(User).filter(User.email == email).first()
    if user is None or user.status == UserStatus.PENDING_EMAIL:
        return {"message": generic_message}

    token = _create_password_reset_token(user)
    if not _send_password_reset_email(user.email, user.username, token):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="重置邮件发送失败，请稍后再试",
        )
    return {"message": generic_message}


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    request: PasswordResetRequest,
    db: Session = Depends(get_db),
):
    invalid_token = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={"code": "PASSWORD_RESET_INVALID", "message": "重置链接无效或已过期，请重新申请"},
    )
    try:
        payload = decode_token(request.token, expected_type="password_reset")
        user_uid = int(payload["sub"])
    except (HTTPException, TypeError, ValueError, KeyError) as exc:
        raise invalid_token from exc

    user = db.query(User).filter(User.uid == user_uid).with_for_update().first()
    if (
        user is None
        or user.status == UserStatus.PENDING_EMAIL
        or payload.get("ver") != user.token_version
    ):
        raise invalid_token
    if verify_password(request.new_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "PASSWORD_UNCHANGED", "message": "新密码不能与原密码相同"},
        )

    user.hashed_password = get_password_hash(request.new_password)
    user.token_version += 1
    user.updated_at = datetime.utcnow()
    db.commit()
    return {"message": "密码重置成功，请使用新密码登录"}


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """用户登录"""
    # 查找用户（支持用户名或邮箱登录）
    user = db.query(User).filter(
        (User.username == form_data.username) | (User.email == form_data.username)
    ).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if sync_user_punishment_status(db, user):
        db.commit()
        db.refresh(user)

    if user.status == UserStatus.BANNED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账户已被封禁"
        )
    if user.status == UserStatus.PENDING_EMAIL:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="请先完成邮箱验证",
        )

    # 生成令牌
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user.uid,
            "username": user.username,
            "role": user.role.value,
            "ver": user.token_version,
        },
        expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(
        data={
            "sub": user.uid,
            "username": user.username,
            "ver": user.token_version,
        }
    )

    # 更新最后登录时间等
    # 这里可以添加登录日志等

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/refresh", response_model=Token)
async def refresh_token(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    """刷新令牌"""
    try:
        payload = decode_token(request.refresh_token, expected_type="refresh")
        user_id = int(payload["sub"])
    except (HTTPException, TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的刷新令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.uid == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if sync_user_punishment_status(db, user):
        db.commit()
        db.refresh(user)
    if payload.get("ver") != user.token_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的刷新令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.status == UserStatus.BANNED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账户已被封禁"
        )
    if user.status == UserStatus.PENDING_EMAIL:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="请先完成邮箱验证",
        )

    # 生成新的访问令牌
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user.uid,
            "username": user.username,
            "role": user.role.value,
            "ver": user.token_version,
        },
        expires_delta=access_token_expires
    )
    new_refresh_token = create_refresh_token(
        data={
            "sub": user.uid,
            "username": user.username,
            "ver": user.token_version,
        }
    )

    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_active_user)):
    """获取当前用户信息"""
    return current_user


@router.put("/change-password", response_model=MessageResponse)
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    if not verify_password(request.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "PASSWORD_INCORRECT", "message": "原密码不正确"},
        )
    if verify_password(request.new_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "PASSWORD_UNCHANGED", "message": "新密码不能与原密码相同"},
        )

    current_user.hashed_password = get_password_hash(request.new_password)
    current_user.token_version += 1
    current_user.updated_at = datetime.utcnow()
    db.commit()
    return {"message": "密码已修改，请重新登录"}


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_active_user)):
    """用户登出（前端删除令牌即可，服务端可添加令牌黑名单）"""
    # TODO: 将当前令牌加入黑名单
    return {"message": "已成功登出"}
