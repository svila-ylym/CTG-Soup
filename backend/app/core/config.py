from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, SecretStr, field_validator, model_validator
from functools import lru_cache
from typing import List, Literal, Optional
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import secrets
from pathlib import Path


_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def _default_app_version() -> str:
    try:
        value = (_REPOSITORY_ROOT / "VERSION").read_text(encoding="utf-8").strip()
    except OSError:
        value = ""
    return value or "1.2.0"


def _normalize_https_origin(value: str, field_name: str) -> str:
    parsed = urlsplit(value)
    try:
        parsed.port
    except ValueError as exc:
        raise ValueError(f"{field_name} must contain a valid port") from exc
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
        or "?" in value
        or "#" in value
        or parsed.username
        or parsed.password
        or any(character.isspace() for character in parsed.netloc)
    ):
        raise ValueError(f"{field_name} must be an HTTPS origin without a path")
    return value.rstrip("/")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
        hide_input_in_errors=True,
    )

    # 应用配置
    APP_NAME: str = "汤吧社区"
    APP_VERSION: str = Field(default_factory=_default_app_version)
    APP_VERSION_OVERRIDE: Optional[str] = None
    DEBUG: bool = True
    APP_URL: Optional[str] = "http://localhost:10000"  # 前端地址
    PUBLIC_WEB_URL: Optional[str] = None
    SIGNIN_TIMEZONE: str = "Asia/Shanghai"
    
    # 数据库配置
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/turtle_soup"
    # PostgreSQL client used for OTA backups. Leave empty to auto-detect pg_dump.
    PG_DUMP_BIN: Optional[str] = None
    AUTO_CREATE_DATABASE: bool = False
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    
    # Redis配置
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_ENABLED: bool = True
    REDIS_CACHE_DEFAULT_TTL: int = 300
    
    # Elasticsearch配置
    ELASTICSEARCH_URL: str = "http://localhost:9200"
    
    # JWT配置
    SECRET_KEY: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # 邮件配置 (SMTP)
    SMTP_HOST: str = "smtp.example.com"
    SMTP_PORT: int = 587
    SMTP_USE_SSL: bool = False
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@example.com"
    VERIFICATION_CODE_EXPIRE_MINUTES: int = 30
    PASSWORD_RESET_EXPIRE_MINUTES: int = 30
    EMAIL_DOMAIN_WHITELIST: Optional[List[str]] = None  # 邮箱域名白名单
    EMAIL_VERIFICATION_IP_LIMIT: int = 5
    EMAIL_VERIFICATION_EMAIL_LIMIT: int = 3
    EMAIL_VERIFICATION_GLOBAL_LIMIT: int = 100
    EMAIL_VERIFICATION_IP_WINDOW_SECONDS: int = 60
    EMAIL_VERIFICATION_EMAIL_WINDOW_SECONDS: int = 3600
    EMAIL_VERIFICATION_GLOBAL_WINDOW_SECONDS: int = 60
    SMTP_VERIFICATION_RETRY_ATTEMPTS: int = 3
    
    # 本地文件存储配置
    LOCAL_STORAGE_DIR: str = "storage"
    PRIVATE_STORAGE_DIR: str = "private-storage"
    MAX_UPLOAD_BYTES: int = 5 * 1024 * 1024

    # OTA 更新
    GITHUB_REPOSITORY: str = "svila-ylym/CTG-Soup"
    GITHUB_API_URL: str = "https://api.github.com"
    GITHUB_API_TOKEN: Optional[SecretStr] = None
    GITHUB_RELEASE_CACHE_SECONDS: int = Field(default=300, ge=0, le=86400)
    GITHUB_API_TIMEOUT_SECONDS: float = Field(default=10.0, gt=0, le=60)
    UPDATE_SCRIPT_PATH: Optional[str] = None
    UPDATE_REPOSITORY_PATH: Optional[str] = None
    UPDATE_LOG_DIR: str = "private-storage/update-logs"
    UPDATE_RESTART_COMMAND: Optional[str] = None
    UPDATE_HEALTH_URL: str = "http://127.0.0.1:10001/health"
    OTA_UPDATE_MODE: Literal["Latest", "Dev"] = "Latest"

    # 公开文件存储配置
    PUBLIC_STORAGE_BACKEND: Literal["local", "r2"] = "local"
    R2_ENDPOINT_URL: Optional[str] = None
    R2_BUCKET_NAME: Optional[str] = None
    R2_REGION: str = "auto"
    R2_ACCESS_KEY_ID: Optional[str] = None
    R2_SECRET_ACCESS_KEY: Optional[SecretStr] = None
    R2_PUBLIC_BASE_URL: Optional[str] = None
    
    # 分页配置
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100
    
    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, value: str) -> str:
        normalized = value.strip()
        insecure_prefixes = ("your-secret", "replace-with", "change-this")
        if len(normalized) < 32 or normalized.lower().startswith(insecure_prefixes):
            raise ValueError("SECRET_KEY must be a non-placeholder value of at least 32 characters")
        return normalized

    @property
    def public_web_url(self) -> str:
        value = (
            self.PUBLIC_WEB_URL or self.APP_URL or "http://localhost:10000"
        ).strip().rstrip("/")
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("PUBLIC_WEB_URL must be an absolute HTTP(S) URL")
        return value

    @field_validator("SIGNIN_TIMEZONE")
    @classmethod
    def validate_signin_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("SIGNIN_TIMEZONE must be a valid IANA timezone") from exc
        return value

    @model_validator(mode="after")
    def validate_public_storage(self):
        self.APP_VERSION = (self.APP_VERSION_OVERRIDE or _default_app_version()).strip()
        if self.PUBLIC_STORAGE_BACKEND == "local":
            return self

        required_fields = (
            "R2_ENDPOINT_URL",
            "R2_BUCKET_NAME",
            "R2_REGION",
            "R2_ACCESS_KEY_ID",
            "R2_SECRET_ACCESS_KEY",
            "R2_PUBLIC_BASE_URL",
        )
        for field_name in required_fields:
            value = getattr(self, field_name)
            raw_value = value.get_secret_value() if isinstance(value, SecretStr) else value
            if not raw_value or not raw_value.strip():
                raise ValueError(f"{field_name} is required when PUBLIC_STORAGE_BACKEND=r2")
            normalized = raw_value.strip()
            setattr(
                self,
                field_name,
                SecretStr(normalized) if isinstance(value, SecretStr) else normalized,
            )

        self.R2_ENDPOINT_URL = _normalize_https_origin(
            self.R2_ENDPOINT_URL or "",
            "R2_ENDPOINT_URL",
        )
        self.R2_PUBLIC_BASE_URL = _normalize_https_origin(
            self.R2_PUBLIC_BASE_URL or "",
            "R2_PUBLIC_BASE_URL",
        )
        return self

    @property
    def r2_public_base_url(self) -> str:
        if not self.R2_PUBLIC_BASE_URL:
            raise ValueError("R2_PUBLIC_BASE_URL is not configured")
        return self.R2_PUBLIC_BASE_URL

    @property
    def r2_secret_access_key(self) -> str:
        if not self.R2_SECRET_ACCESS_KEY:
            raise ValueError("R2_SECRET_ACCESS_KEY is not configured")
        return self.R2_SECRET_ACCESS_KEY.get_secret_value()


@lru_cache()
def get_settings() -> Settings:
    return Settings()
