"""Shared user display data for public content and messaging responses."""

from sqlmodel import Session, select

from app.models.database import PermissionGroup, User, UserPermissionGroup


def permission_group_names(db: Session, user_uid: int) -> list[str]:
    rows = db.exec(
        select(PermissionGroup.name)
        .join(
            UserPermissionGroup,
            UserPermissionGroup.group_id == PermissionGroup.id,
        )
        .where(UserPermissionGroup.user_uid == user_uid)
        .order_by(PermissionGroup.name)
    ).all()
    return [name for name in rows if name]


def user_display_fields(db: Session, user: User | None) -> dict:
    if user is None:
        return {"role": "user", "permission_groups": []}
    return {
        "role": user.role,
        "permission_groups": permission_group_names(db, user.uid),
    }
