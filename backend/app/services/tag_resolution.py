from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models.database import Tag, TagKind, TagStatus
from app.services.tag_rules import normalize_tag_name


class TagSelectionError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _insert_custom_tag_if_missing(db: Session, name: str, slug: str) -> Tag:
    values = {
        "name": name,
        "slug": slug,
        "kind": TagKind.CUSTOM,
        "status": TagStatus.ACTIVE,
    }
    dialect = db.get_bind().dialect.name
    if dialect == "postgresql":
        db.exec(
            postgresql_insert(Tag)
            .values(**values)
            .on_conflict_do_nothing(index_elements=["slug"])
        )
    elif dialect == "sqlite":
        db.exec(
            sqlite_insert(Tag)
            .values(**values)
            .on_conflict_do_nothing(index_elements=["slug"])
        )
    else:
        try:
            with db.begin_nested():
                candidate = Tag(**values)
                db.add(candidate)
                db.flush()
        except IntegrityError:
            pass

    tag = db.exec(select(Tag).where(Tag.slug == slug)).first()
    if tag is None:
        raise RuntimeError("自定义标签创建后无法读取")
    return tag


def resolve_active_tags(
    db: Session,
    tag_ids: list[int],
    custom_names: list[str],
    *,
    min_count: int = 0,
    max_count: int = 10,
) -> list[Tag]:
    tags: list[Tag] = []
    seen_ids: set[int] = set()

    def append_unique(tag: Tag) -> None:
        if tag.id in seen_ids:
            return
        tags.append(tag)
        seen_ids.add(tag.id)
        if len(tags) > max_count:
            raise TagSelectionError(
                "TOO_MANY_TAGS",
                f"标签最多选择或新增 {max_count} 个",
            )

    for tag_id in tag_ids:
        tag = db.get(Tag, tag_id)
        if tag is None or tag.status != TagStatus.ACTIVE:
            raise TagSelectionError("TAG_NOT_ACTIVE", "标签不存在或已停用")
        append_unique(tag)

    for raw_name in custom_names:
        try:
            name, slug = normalize_tag_name(raw_name)
        except ValueError as exc:
            raise TagSelectionError("INVALID_TAG_NAME", str(exc)) from exc
        tag = db.exec(select(Tag).where(Tag.slug == slug)).first()
        if tag is not None and tag.status != TagStatus.ACTIVE:
            raise TagSelectionError("TAG_NOT_ACTIVE", "标签不存在或已停用")
        if tag is None:
            tag = _insert_custom_tag_if_missing(db, name, slug)
            if tag.status != TagStatus.ACTIVE:
                raise TagSelectionError(
                    "TAG_NOT_ACTIVE",
                    "标签不存在或已停用",
                )
        append_unique(tag)

    if len(tags) < min_count:
        raise TagSelectionError(
            "NO_TAGS",
            f"请至少选择或新增 {min_count} 个标签",
        )

    return tags
