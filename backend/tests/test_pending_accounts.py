from datetime import datetime, timedelta

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app.models.database import (
    EmailVerification,
    ReusableUserUid,
    User,
    UserStatus,
    UserUidAllocator,
)
from app.services.pending_accounts import (
    allocate_user_uid,
    cleanup_expired_pending_users,
)


def _engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return engine


def _user(uid: int, status: UserStatus, created_at: datetime) -> User:
    return User(
        uid=uid,
        username=f"user-{uid}",
        nickname=f"User {uid}",
        email=f"user-{uid}@example.com",
        hashed_password="unused",
        status=status,
        created_at=created_at,
    )


def test_cleanup_deletes_only_expired_pending_accounts_and_releases_uid():
    engine = _engine()
    now = datetime(2026, 8, 9, 12, 0, 0)
    with Session(engine) as session:
        expired = _user(3, UserStatus.PENDING_EMAIL, now - timedelta(minutes=31))
        young = _user(4, UserStatus.PENDING_EMAIL, now - timedelta(minutes=29))
        active = _user(5, UserStatus.ACTIVE, now - timedelta(hours=2))
        session.add_all([expired, young, active])
        session.commit()
        session.add_all([
            EmailVerification(
                user_uid=3,
                token_hash="expired-token",
                expires_at=now + timedelta(hours=1),
            ),
            EmailVerification(
                user_uid=4,
                token_hash="young-token",
                expires_at=now + timedelta(hours=1),
            ),
        ])
        session.commit()

        assert cleanup_expired_pending_users(session, now=now) == [3]
        assert session.get(User, 3) is None
        assert session.get(ReusableUserUid, 3) is not None
        assert session.exec(
            select(EmailVerification).where(EmailVerification.user_uid == 3)
        ).all() == []
        assert session.get(User, 4) is not None
        assert session.get(User, 5) is not None
        assert session.exec(
            select(EmailVerification).where(EmailVerification.user_uid == 4)
        ).one().token_hash == "young-token"


def test_uid_allocation_uses_released_ids_then_continues_high_water_sequence():
    engine = _engine()
    now = datetime(2026, 8, 9, 12, 0, 0)
    with Session(engine) as session:
        session.add_all([
            _user(uid, UserStatus.ACTIVE, now)
            for uid in (1, 2, 7, 8, 9, 10)
        ])
        session.add_all([
            ReusableUserUid(uid=uid, released_at=now)
            for uid in (3, 4, 5, 6)
        ])
        session.commit()

        allocated = []
        for index in range(6):
            uid = allocate_user_uid(session)
            allocated.append(uid)
            session.add(
                User(
                    uid=uid,
                    username=f"allocated-{index}",
                    nickname=f"Allocated {index}",
                    email=f"allocated-{index}@example.com",
                    hashed_password="unused",
                    status=UserStatus.PENDING_EMAIL,
                )
            )
            session.commit()

        assert allocated == [3, 4, 5, 6, 15, 16]
        assert session.exec(select(ReusableUserUid)).all() == []
        assert session.get(UserUidAllocator, 1).next_uid == 17


def test_uid_pool_removal_and_allocator_advance_roll_back_together():
    engine = _engine()
    now = datetime(2026, 8, 9, 12, 0, 0)
    with Session(engine) as session:
        session.add_all([
            _user(uid, UserStatus.ACTIVE, now)
            for uid in (1, 2, 4, 5)
        ])
        session.add(UserUidAllocator(id=1, next_uid=6))
        session.add(ReusableUserUid(uid=3, released_at=now))
        session.commit()

        assert allocate_user_uid(session) == 3
        session.rollback()

        assert session.get(ReusableUserUid, 3) is not None
        assert session.get(UserUidAllocator, 1).next_uid == 6
