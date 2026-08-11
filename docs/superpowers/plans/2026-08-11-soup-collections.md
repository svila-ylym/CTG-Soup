# Soup Collections And Version 1.4.0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add author-owned public soup collections across the API, profile, soup editor, soup detail, and a dedicated detail page, then set the runtime version to `1.4.0`.

**Architecture:** Store one nullable `collection_id` on each soup and keep collection ownership in a new `soup_collections` table. A dedicated collections router owns CRUD, visibility, pagination, and deletion detachment; the existing soup router only validates and serializes the optional association. Frontend collection API/types feed a focused profile management section, the shared soup editor, and a new collection detail view.

**Tech Stack:** FastAPI, SQLModel, SQLAlchemy, PostgreSQL/SQLite migration coverage, pytest, Vue 3, TypeScript, Headless UI, Heroicons, Axios, Vite.

## Global Constraints

- Each soup belongs to at most one collection, and a collection may contain only soups written by its owner.
- Collection soups are public only in status `published` or `revealed` and sort by `created_at ASC, id ASC`.
- Empty collections are visible only to their owner.
- Deleting a collection detaches soups and never deletes or changes soup status.
- Collection association never rewrites or prefixes a soup title.
- Collection names are trimmed strings of 1–100 characters; descriptions are plain text of at most 2000 characters.
- The canonical runtime `VERSION` must become exactly `1.4.0`.
- Create a GitHub Pull Request, but do not connect to SFTP/SSH, run a remote migration, restart Screen, or modify the deployment directory.

---

### Task 1: Collection Model And Idempotent Migration

**Files:**
- Create: `backend/app/migrations/soup_collections.py`
- Create: `backend/tests/test_soup_collection_migration.py`
- Modify: `backend/app/models/models.py`
- Modify: `backend/app/models/database.py`
- Modify: `backend/app/migrations/social_platform.py`
- Modify: `backend/tests/test_social_platform_migration.py`

**Interfaces:**
- Produces model `SoupCollection(id, owner_uid, name, description, created_at, updated_at)`.
- Produces `Soup.collection_id: int | None` with `ON DELETE SET NULL` metadata.
- Produces `ensure_soup_collection_schema(engine: Engine = default_engine, dry_run: bool = False) -> SoupCollectionMigrationReport`.
- Integrates collection migration actions into `_upgrade_foundation()`.

- [ ] **Step 1: Write the migration contract test**

Create a legacy SQLite database with `users`, `soups`, and one old soup, then assert dry-run, apply, old-data preservation, indexes, foreign keys, and repeatability:

```python
from sqlalchemy import inspect, text
from sqlmodel import create_engine

from app.migrations.soup_collections import ensure_soup_collection_schema


def _legacy_engine():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text(
            "CREATE TABLE users (uid INTEGER PRIMARY KEY)"
        ))
        connection.execute(text(
            "CREATE TABLE soups (id INTEGER PRIMARY KEY, author_uid INTEGER NOT NULL)"
        ))
        connection.execute(text("INSERT INTO users (uid) VALUES (1)"))
        connection.execute(text("INSERT INTO soups (id, author_uid) VALUES (10, 1)"))
    return engine


def test_collection_migration_is_dry_run_capable_and_repeatable():
    engine = _legacy_engine()

    preview = ensure_soup_collection_schema(engine, dry_run=True)
    assert preview.applied is False
    assert preview.actions == (
        "CREATE soup_collections",
        "ADD soups.collection_id",
        "CREATE INDEX ix_soups_collection_id",
    )
    assert "soup_collections" not in inspect(engine).get_table_names()

    applied = ensure_soup_collection_schema(engine)
    repeated = ensure_soup_collection_schema(engine)

    assert applied.applied is True
    assert repeated.actions == ()
    assert "soup_collections" in inspect(engine).get_table_names()
    assert "collection_id" in {
        column["name"] for column in inspect(engine).get_columns("soups")
    }
    assert "ix_soups_collection_id" in {
        index["name"] for index in inspect(engine).get_indexes("soups")
    }
    assert any(
        foreign_key["referred_table"] == "soup_collections"
        for foreign_key in inspect(engine).get_foreign_keys("soups")
    )
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT collection_id FROM soups WHERE id = 10")
        ).scalar_one() is None
```

- [ ] **Step 2: Run the migration test and verify the missing module failure**

Run:

```bash
PYTHONPATH=backend /tmp/ctg-verify.xA2dJy/bin/python -m pytest -q backend/tests/test_soup_collection_migration.py
```

Expected: FAIL during collection because `app.migrations.soup_collections` does not exist.

- [ ] **Step 3: Add the canonical models and exports**

In `models.py`, import `ForeignKey` and `Integer`, place `SoupCollection` immediately before `Soup`, and add the nullable column to `Soup`:

```python
class SoupCollection(SQLModel, table=True):
    __tablename__ = "soup_collections"

    id: Optional[int] = Field(default=None, primary_key=True)
    owner_uid: int = Field(foreign_key="users.uid", index=True)
    name: str = Field(max_length=100)
    description: str = Field(default="", sa_column=Column(Text, nullable=False))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Soup(SQLModel, table=True):
    collection_id: Optional[int] = Field(
        default=None,
        sa_column=Column(
            Integer,
            ForeignKey("soup_collections.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )
```

Add `SoupCollection` to imports and `__all__` in `database.py`. Keep the legacy `Collection = Favorite` alias unchanged.

- [ ] **Step 4: Implement the idempotent migration**

Create `SoupCollectionMigrationReport(actions: tuple[str, ...], applied: bool)`. Inspect existing tables, columns, indexes, and foreign keys before producing the three exact actions from Step 1. When applying:

```python
with engine.begin() as connection:
    if create_table:
        SoupCollection.__table__.create(connection)
    if add_column:
        connection.execute(text(
            "ALTER TABLE soups ADD COLUMN collection_id INTEGER NULL "
            "REFERENCES soup_collections(id) ON DELETE SET NULL"
        ))
    if create_index:
        connection.execute(text(
            "CREATE INDEX ix_soups_collection_id ON soups (collection_id)"
        ))
```

If either `users` or `soups` is absent, return an empty report. Dry-run returns the same pending actions without executing DDL.

- [ ] **Step 5: Integrate the migration into the foundation phase**

Import `ensure_soup_collection_schema` in `social_platform.py`, call it from `_upgrade_foundation()`, and append its actions after soup metadata actions. Extend the existing repeatability assertion so a second foundation run still returns only:

```python
{"promoted_root_users": 0, "actions": 0}
```

- [ ] **Step 6: Run migration and foundation tests**

Run:

```bash
PYTHONPATH=backend /tmp/ctg-verify.xA2dJy/bin/python -m pytest -q backend/tests/test_soup_collection_migration.py backend/tests/test_social_platform_migration.py
```

Expected: all selected tests pass.

- [ ] **Step 7: Commit the model and migration**

```bash
git add backend/app/models/models.py backend/app/models/database.py backend/app/migrations/soup_collections.py backend/app/migrations/social_platform.py backend/tests/test_soup_collection_migration.py backend/tests/test_social_platform_migration.py
git commit -m "feat: add soup collection schema"
```

---

### Task 2: Collection CRUD, Visibility, And Ordering API

**Files:**
- Create: `backend/app/schemas/collections.py`
- Create: `backend/app/api/collections.py`
- Create: `backend/tests/test_soup_collections_api.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Produces `CollectionCreate`, `CollectionUpdate`, `CollectionSummary`, `CollectionSoupSummary`, `CollectionDetail`, `CollectionPage`, and `CollectionMinePage` schemas.
- Produces router endpoints under `/api/collections` for public list/detail and owner CRUD.
- Consumes `competition_colors_for_soups()` for collection soup summaries.

- [ ] **Step 1: Build an isolated API fixture and failing CRUD test**

The test app creates owner, visitor, and other-owner users, overrides all auth/database dependencies, and registers `collections.router`. Define the shared helpers first:

```python
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.api import collections, turtle_soups
from app.api.auth import get_current_active_user, get_optional_current_user
from app.models.database import Soup, SoupCollection, User, UserStatus, get_db


def _test_app(include_soups: bool = False):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        users = [
            User(username="owner", nickname="作者", email="owner@example.com", hashed_password="x"),
            User(username="visitor", nickname="访客", email="visitor@example.com", hashed_password="x"),
            User(username="other", nickname="其他作者", email="other@example.com", hashed_password="x"),
        ]
        session.add_all(users)
        session.commit()
        for user in users:
            session.refresh(user)
        user_ids = [user.uid for user in users]

    users = [
        User(
            uid=uid,
            username=username,
            nickname=nickname,
            email=email,
            hashed_password="x",
            status=UserStatus.ACTIVE,
        )
        for uid, username, nickname, email in zip(
            user_ids,
            ("owner", "visitor", "other"),
            ("作者", "访客", "其他作者"),
            ("owner@example.com", "visitor@example.com", "other@example.com"),
        )
    ]
    current = {"user": users[0]}

    def override_db():
        with Session(engine) as session:
            yield session

    def override_active_user():
        if current["user"] is None:
            raise HTTPException(401, detail="未登录")
        return current["user"]

    def override_optional_user():
        return current["user"]

    app = FastAPI()
    app.include_router(collections.router, prefix="/api/collections")
    if include_soups:
        app.include_router(turtle_soups.router, prefix="/api/turtle-soups")
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_active_user] = override_active_user
    app.dependency_overrides[get_optional_current_user] = override_optional_user
    return TestClient(app), engine, users, current


def _add_collection(engine, owner_uid: int, name: str) -> int:
    with Session(engine) as session:
        collection = SoupCollection(owner_uid=owner_uid, name=name, description="")
        session.add(collection)
        session.commit()
        session.refresh(collection)
        return collection.id


def _add_soup(
    engine,
    author_uid: int,
    collection_id: int,
    title: str,
    day: int = 1,
    status: str = "published",
) -> int:
    with Session(engine) as session:
        soup = Soup(
            author_uid=author_uid,
            collection_id=collection_id,
            title=title,
            puzzle="谜面",
            solution="汤底",
            status=status,
            created_at=datetime(2026, 1, 1) + timedelta(days=day),
        )
        session.add(soup)
        session.commit()
        session.refresh(soup)
        return soup.id


def _soup_payload() -> dict:
    return {
        "title": "系列新作",
        "puzzle": "谜面",
        "solution": "汤底",
        "genre": "本格",
        "soup_color": "清汤",
        "main_player_count": "1",
        "secondary_player_count": "0",
        "tag_ids": [],
        "custom_tags": [],
        "puzzle_image_ids": [],
        "solution_image_ids": [],
        "is_revealed": False,
    }
```

Add this first contract:

```python
def test_owner_can_create_update_and_delete_collection_without_deleting_soups():
    client, engine, users, current = _test_app()
    created = client.post(
        "/api/collections",
        json={"name": "  夜航系列  ", "description": "按顺序阅读"},
    )
    assert created.status_code == 201
    collection_id = created.json()["id"]
    assert created.json()["name"] == "夜航系列"
    assert created.json()["soup_count"] == 0

    soup_id = _add_soup(engine, users[0].uid, collection_id, "第一夜")
    current["user"] = users[1]
    assert client.put(
        f"/api/collections/{collection_id}",
        json={"name": "越权", "description": ""},
    ).status_code == 403

    current["user"] = users[0]
    updated = client.put(
        f"/api/collections/{collection_id}",
        json={"name": "夜航", "description": "完整系列"},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "夜航"
    assert client.delete(f"/api/collections/{collection_id}").status_code == 204

    with Session(engine) as session:
        assert session.get(Soup, soup_id) is not None
        assert session.get(Soup, soup_id).collection_id is None
```

- [ ] **Step 2: Add failing visibility and ordering tests**

Create an empty collection plus public, revealed, and deleted soups with controlled timestamps. Assert:

```python
def test_empty_visibility_and_public_detail_order_are_identity_aware():
    client, engine, users, current = _test_app()
    empty_id = _add_collection(engine, users[0].uid, "空合集")
    series_id = _add_collection(engine, users[0].uid, "时间线")
    newest_id = _add_soup(engine, users[0].uid, series_id, "第三篇", day=3)
    oldest_id = _add_soup(engine, users[0].uid, series_id, "第一篇", day=1)
    middle_id = _add_soup(engine, users[0].uid, series_id, "第二篇", day=2, status="revealed")
    _add_soup(engine, users[0].uid, series_id, "已删除", day=0, status="deleted")

    owner_list = client.get("/api/collections", params={"owner_uid": users[0].uid}).json()
    assert {item["id"] for item in owner_list["items"]} == {empty_id, series_id}

    current["user"] = users[1]
    visitor_list = client.get("/api/collections", params={"owner_uid": users[0].uid}).json()
    assert [item["id"] for item in visitor_list["items"]] == [series_id]
    assert client.get(f"/api/collections/{empty_id}").status_code == 404

    detail = client.get(f"/api/collections/{series_id}").json()
    assert [item["id"] for item in detail["soups"]["items"]] == [
        oldest_id,
        middle_id,
        newest_id,
    ]
    assert detail["soup_count"] == 3
```

Add the authenticated/anonymous `mine` contract:

```python
def test_mine_includes_empty_collections_and_requires_authentication():
    client, engine, users, current = _test_app()
    empty_id = _add_collection(engine, users[0].uid, "空合集")

    mine = client.get("/api/collections/mine")
    assert mine.status_code == 200
    assert [item["id"] for item in mine.json()["items"]] == [empty_id]

    current["user"] = None
    assert client.get("/api/collections/mine").status_code == 401
```

- [ ] **Step 3: Run the API tests and verify the missing router failure**

Run:

```bash
PYTHONPATH=backend /tmp/ctg-verify.xA2dJy/bin/python -m pytest -q backend/tests/test_soup_collections_api.py
```

Expected: FAIL during import because collection schemas/router do not exist.

- [ ] **Step 4: Define exact request and response schemas**

Use validators that trim names and reject `<` or `>` in name/description:

```python
class CollectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=2000)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized or "<" in normalized or ">" in normalized:
            raise ValueError("合集名称不能为空或包含 HTML")
        return normalized

    @field_validator("description")
    @classmethod
    def plain_description(cls, value: str) -> str:
        if "<" in value or ">" in value:
            raise ValueError("合集简介不允许 HTML")
        return value.strip()


class CollectionUpdate(CollectionCreate):
    pass
```

Define response schemas with exact fields:

```python
class CollectionSummary(BaseModel):
    id: int
    owner_uid: int
    name: str
    description: str
    soup_count: int = Field(ge=0)
    created_at: datetime
    updated_at: datetime


class CollectionSoupSummary(BaseModel):
    id: int
    title: str
    puzzle_excerpt: str
    genre: str
    soup_color: str
    average_score: float
    rating_count: int
    like_count: int
    competition_colors: list[str] = Field(default_factory=list)
    created_at: datetime


class CollectionDetail(CollectionSummary):
    author: AuthorSummary
    soups: PageResponse[CollectionSoupSummary]


class CollectionPage(PageResponse[CollectionSummary]):
    pass


class CollectionMinePage(PageResponse[CollectionSummary]):
    pass
```

- [ ] **Step 5: Implement collection queries and permissions**

Register routes in this order: `POST ""`, `GET ""`, `GET "/mine"`, `GET "/{collection_id}"`, `PUT "/{collection_id}"`, `DELETE "/{collection_id}"`.

Use one public-status constant:

```python
PUBLIC_SOUP_STATUSES = ("published", "revealed")
```

For visitors, filter the list with an `EXISTS` subquery over public soups. For owners, omit that filter. Compute `soup_count` using only public statuses. Detail selects public soups with:

```python
select(Soup).where(
    Soup.collection_id == collection_id,
    Soup.status.in_(PUBLIC_SOUP_STATUSES),
).order_by(Soup.created_at.asc(), Soup.id.asc())
```

Sort collection lists by `SoupCollection.created_at.desc(), SoupCollection.id.desc()` so pagination remains stable.

Deletion executes an update that sets every matching `Soup.collection_id` to `None`, then deletes the collection and commits once.

- [ ] **Step 6: Register the router and rerun focused tests**

Import `collections` in `main.py` and register:

```python
app.include_router(collections.router, prefix="/api/collections", tags=["合集"])
```

Run:

```bash
PYTHONPATH=backend /tmp/ctg-verify.xA2dJy/bin/python -m pytest -q backend/tests/test_soup_collections_api.py
```

Expected: all focused API tests pass.

- [ ] **Step 7: Commit the collection API**

```bash
git add backend/app/schemas/collections.py backend/app/api/collections.py backend/app/main.py backend/tests/test_soup_collections_api.py
git commit -m "feat: add soup collection API"
```

---

### Task 3: Associate Soups With Owned Collections

**Files:**
- Modify: `backend/app/schemas/soups.py`
- Modify: `backend/app/api/turtle_soups.py`
- Modify: `backend/tests/test_soup_collections_api.py`

**Interfaces:**
- Extends `SoupCreate.collection_id: int | None` and `SoupUpdate.collection_id: int | None`.
- Extends `SoupResponse.collection: SoupCollectionRef | None` where `SoupCollectionRef` has `id`, `owner_uid`, and `name`.
- Produces `_resolve_owned_collection(db: Session, owner_uid: int, collection_id: int | None) -> SoupCollection | None`.

- [ ] **Step 1: Add failing soup create/update association tests**

Register `turtle_soups.router` in the Task 2 test app and add a valid full soup payload. Verify creation, response serialization, move, removal, cross-owner rejection, and missing-ID rejection:

```python
def test_soup_create_update_and_remove_collection_enforces_owner():
    client, engine, users, current = _test_app(include_soups=True)
    own_id = _add_collection(engine, users[0].uid, "自己的合集")
    other_id = _add_collection(engine, users[2].uid, "别人的合集")
    current["user"] = users[0]

    created = client.post(
        "/api/turtle-soups",
        json={**_soup_payload(), "collection_id": own_id},
    )
    assert created.status_code == 201
    soup_id = created.json()["id"]
    assert created.json()["collection"] == {
        "id": own_id,
        "owner_uid": users[0].uid,
        "name": "自己的合集",
    }

    forbidden = client.put(
        f"/api/turtle-soups/{soup_id}",
        json={"collection_id": other_id},
    )
    assert forbidden.status_code == 403
    assert client.put(
        f"/api/turtle-soups/{soup_id}",
        json={"collection_id": 999999},
    ).status_code == 422

    removed = client.put(
        f"/api/turtle-soups/{soup_id}",
        json={"collection_id": None},
    )
    assert removed.status_code == 200
    assert removed.json()["collection"] is None
```

Add an omission assertion before the explicit removal:

```python
    preserved = client.put(
        f"/api/turtle-soups/{soup_id}",
        json={"title": "改名后仍在合集"},
    )
    assert preserved.status_code == 200
    assert preserved.json()["collection"]["id"] == own_id
```

- [ ] **Step 2: Run the focused test and verify schema rejection**

Run:

```bash
PYTHONPATH=backend /tmp/ctg-verify.xA2dJy/bin/python -m pytest -q backend/tests/test_soup_collections_api.py
```

Expected: FAIL because `collection_id` is ignored/rejected and `SoupResponse` lacks `collection`.

- [ ] **Step 3: Extend soup schemas**

Add:

```python
class SoupCollectionRef(BaseModel):
    id: int
    owner_uid: int
    name: str
```

Set `collection_id: Optional[int] = Field(default=None, gt=0)` on `SoupCreate` and `SoupUpdate`, and `collection: Optional[SoupCollectionRef] = None` on `SoupResponse`. Pydantic `model_fields_set` plus `model_dump(exclude_unset=True)` must distinguish omitted update fields from explicit `null`.

- [ ] **Step 4: Validate ownership and serialize collection refs**

Implement:

```python
def _resolve_owned_collection(
    db: Session,
    owner_uid: int,
    collection_id: Optional[int],
) -> Optional[SoupCollection]:
    if collection_id is None:
        return None
    collection = db.get(SoupCollection, collection_id)
    if collection is None:
        raise HTTPException(422, detail={
            "code": "COLLECTION_NOT_FOUND",
            "message": "合集不存在",
        })
    if collection.owner_uid != owner_uid:
        raise HTTPException(403, detail={
            "code": "COLLECTION_OWNER_MISMATCH",
            "message": "只能选择自己创建的合集",
        })
    return collection
```

During create, resolve before constructing `Soup` and set `collection_id`. During update, pop `collection_id` only when it exists in `values`, resolve it, and assign the resulting ID or `None`. In `_payload()`, load `SoupCollection` once and serialize the exact three ref fields.

- [ ] **Step 5: Rerun collection and soup regression tests**

Run:

```bash
PYTHONPATH=backend /tmp/ctg-verify.xA2dJy/bin/python -m pytest -q backend/tests/test_soup_collections_api.py backend/tests/test_soup_comments_api.py backend/tests/test_soup_metadata_api.py
```

Expected: all selected tests pass.

- [ ] **Step 6: Commit soup association support**

```bash
git add backend/app/schemas/soups.py backend/app/api/turtle_soups.py backend/tests/test_soup_collections_api.py
git commit -m "feat: associate soups with collections"
```

---

### Task 4: Frontend Types, Client, Editor, And Drafts

**Files:**
- Create: `frontend/src/api/collections.ts`
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/components/SoupEditorForm.vue`
- Modify: `frontend/src/views/SoupCreateView.vue`
- Modify: `frontend/src/views/SoupEditView.vue`

**Interfaces:**
- Produces `collectionApi.list`, `collectionApi.mine`, `collectionApi.get`, `collectionApi.create`, `collectionApi.update`, and `collectionApi.delete`.
- Produces frontend types matching Task 2 and Task 3 response schemas.
- Consumes all owner collections in `SoupEditorForm` and binds `SoupEditorState.collection_id`.

- [ ] **Step 1: Add exact collection and soup types**

Define:

```ts
export interface SoupCollectionInput {
  name: string
  description: string
}

export interface SoupCollectionRef {
  id: number
  owner_uid: number
  name: string
}

export interface SoupCollectionSummary extends SoupCollectionRef {
  description: string
  soup_count: number
  created_at: string
  updated_at: string
}

export interface SoupCollectionSoupSummary {
  id: number
  title: string
  puzzle_excerpt: string
  genre: string
  soup_color: string
  average_score: number
  rating_count: number
  like_count: number
  competition_colors: string[]
  created_at: string
}

export interface SoupCollectionDetail extends SoupCollectionSummary {
  author: SoupAuthor
  soups: PageResult<SoupCollectionSoupSummary>
}
```

Add `collection: SoupCollectionRef | null` to `TurtleSoup` and `collection_id: number | null` to `SoupCreate`, which automatically carries into `SoupEditorState`.

- [ ] **Step 2: Implement the typed collection client**

Create methods with these signatures:

```ts
list(ownerUid: number, page = 1, pageSize = 20)
mine(page = 1, pageSize = 100)
get(id: number, page = 1, pageSize = 20)
create(input: SoupCollectionInput)
update(id: number, input: SoupCollectionInput)
delete(id: number)
```

Map them to `/collections`, `/collections/mine`, and `/collections/{id}` using `PageResult<SoupCollectionSummary>` and `SoupCollectionDetail` response types.

- [ ] **Step 3: Add the collection selector with isolated loading errors**

In `SoupEditorForm.vue`, load all pages from `collectionApi.mine` into `collections`. Add `collectionsLoading` and `collectionsError`; retry invokes the same loader. Render after the title:

```vue
<label class="block">
  <span class="mb-2 block text-sm font-medium">合集</span>
  <select v-model="state.collection_id" class="form-control" :disabled="collectionsLoading">
    <option :value="null">不加入合集</option>
    <option v-for="collection in collections" :key="collection.id" :value="collection.id">
      {{ collection.name }}
    </option>
  </select>
  <span v-if="collectionsLoading" class="mt-2 block text-xs text-slate-500">正在加载合集…</span>
  <span v-else-if="collectionsError" class="mt-2 flex items-center gap-2 text-xs text-red-600">
    {{ collectionsError }}
    <button class="text-blue-600 hover:underline" type="button" @click="loadCollections">重试</button>
  </span>
</label>
```

Keep tag loading independent so either request may fail without disabling the rest of the form.

- [ ] **Step 4: Carry association through create, edit, and draft restore**

Initialize both create/edit state objects with `collection_id: null`. Edit load uses:

```ts
collection_id: soup.collection?.id ?? null
```

The existing spread into create/update payloads then includes `collection_id` automatically. In draft restore, explicitly normalize old data:

```ts
collection_id: typeof draft.collection_id === 'number' ? draft.collection_id : null
```

Include `draft.collection_id !== null` in `hasDraft()` so selecting a collection alone persists a draft.

- [ ] **Step 5: Install dependencies and run the production build**

Run:

```bash
npm --prefix frontend ci --no-audit --no-fund
npm --prefix frontend run build
```

Expected: Vue type checking and Vite build exit zero.

- [ ] **Step 6: Commit frontend collection plumbing**

```bash
git add frontend/src/api/collections.ts frontend/src/types/index.ts frontend/src/components/SoupEditorForm.vue frontend/src/views/SoupCreateView.vue frontend/src/views/SoupEditView.vue
git commit -m "feat: select collections in soup editor"
```

---

### Task 5: Profile Collection Management

**Files:**
- Create: `frontend/src/components/SoupCollectionDialog.vue`
- Create: `frontend/src/components/ProfileCollectionsSection.vue`
- Modify: `frontend/src/views/ProfileView.vue`

**Interfaces:**
- `SoupCollectionDialog` props `{ open: boolean; collection: SoupCollectionSummary | null; saving: boolean; error: string }`, event `{ close: []; save: [input: SoupCollectionInput] }`.
- `ProfileCollectionsSection` props `{ ownerUid: number; isSelf: boolean }`; owns collection paging and CRUD calls.
- `ProfileView` consumes only the section component and does not duplicate collection request state.

- [ ] **Step 1: Create the reusable create/edit dialog**

Use Headless UI `Dialog`, `TransitionRoot`, and `TransitionChild`. Watch `[open, collection?.id]` and reset local fields from the selected collection. Submit only after trimming and checking name length and description length; emit:

```ts
emit('save', {
  name: name.value.trim(),
  description: description.value.trim(),
})
```

The title is `创建合集` or `编辑合集`; the close button and overlay emit `close`, except while `saving` is true. Render the provided API error without clearing form fields.

- [ ] **Step 2: Implement the focused profile section**

The section owns `items`, `page`, `totalPages`, `loading`, `error`, `saving`, `dialogOpen`, and `editingCollection`. `load()` calls `collectionApi.list(ownerUid, page, 10)`. Watch `ownerUid` and reset to page 1.

Create/update behavior:

```ts
if (editingCollection.value) {
  await collectionApi.update(editingCollection.value.id, input)
} else {
  await collectionApi.create(input)
}
await load()
dialogOpen.value = false
```

Delete requires:

```ts
window.confirm(`确定删除合集“${collection.name}”吗？合集内海龟汤会保留并移出合集。`)
```

After deletion, if the current page becomes empty and `page > 1`, decrement once before reloading.

- [ ] **Step 3: Render profile collection controls and states**

Render an unframed section with heading `合集`. For the owner, add a `FolderPlusIcon` button labeled `创建合集`; repeated collection items are individual compact cards linking to `/collections/{id}`. Owner edit/delete buttons use `PencilSquareIcon` and `TrashIcon`, stop link navigation, and include `title` plus `aria-label`.

Show loading, retained-data error, empty owner text `还没有合集，可以先创建一个再发布系列作品。`, visitor empty text `暂未公开合集`, and previous/next pagination controls. Mount one `SoupCollectionDialog` outside the loop.

- [ ] **Step 4: Mount the section in the personal profile**

Import and render between representative works and published soups:

```vue
<ProfileCollectionsSection
  :owner-uid="profile.user.uid"
  :is-self="isSelf"
/>
```

- [ ] **Step 5: Run the frontend build**

Run `npm --prefix frontend run build`.

Expected: exit zero with no Vue/TypeScript errors.

- [ ] **Step 6: Commit profile management**

```bash
git add frontend/src/components/SoupCollectionDialog.vue frontend/src/components/ProfileCollectionsSection.vue frontend/src/views/ProfileView.vue
git commit -m "feat: manage collections from profiles"
```

---

### Task 6: Collection Detail Page And Soup Source Link

**Files:**
- Create: `frontend/src/views/CollectionDetailView.vue`
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/src/views/SoupDetailView.vue`

**Interfaces:**
- Route `/collections/:id` loads `collectionApi.get(id, page, 20)`.
- Soup detail consumes `TurtleSoup.collection` from Task 4.
- Collection cards reuse `competitionBorderStyle()` for soup competition colors.

- [ ] **Step 1: Register the collection detail route**

Place it before the catch-all route:

```ts
{
  path: '/collections/:id',
  name: 'CollectionDetail',
  component: () => import('@/views/CollectionDetailView.vue'),
  meta: { title: '合集详情' },
}
```

- [ ] **Step 2: Implement detail loading and 404 behavior**

Validate the numeric ID. On a 404 response, replace with `{ name: 'Error', params: { code: '404' } }`. Other failures retain the view and use `extractApiError`. Use this explicit route watcher:

```ts
watch(
  () => route.params.id,
  () => {
    page.value = 1
    void load(1)
  },
  { immediate: true },
)

async function changePage(targetPage: number) {
  if (targetPage < 1 || targetPage > (collection.value?.soups.total_pages ?? 1)) return
  await load(targetPage)
}
```

`load(targetPage)` stores the response and sets `page.value = response.data.soups.page`; pagination buttons call `changePage(page - 1)` and `changePage(page + 1)`.

- [ ] **Step 3: Render the collection and chronological soup page**

Render collection name as `h1`, author as a link to `/profile/{owner_uid}`, description with `whitespace-pre-wrap`, and `soup_count`. Each soup item links to `/soups/{id}`, uses `competitionBorderStyle(soup.competition_colors)`, and shows title, puzzle excerpt, genre, soup color, average score, rating count, and China-local date.

When `soups.items` is empty, show owner copy `这个合集还没有公开作品。` and a `/soups/create` button only when `auth.user?.uid === collection.owner_uid`. Add previous/next controls using `collection.soups.total_pages`.

- [ ] **Step 4: Add the source link to soup detail**

Near the author and metadata area render only when associated:

```vue
<p v-if="soup.collection" class="mt-2 break-words text-sm text-slate-500">
  来源于
  <router-link class="font-medium text-blue-600 hover:underline" :to="`/collections/${soup.collection.id}`">
    「{{ soup.collection.name }}」合集
  </router-link>
</p>
```

Do not alter `soup.title` or list-card titles.

- [ ] **Step 5: Build the frontend**

Run `npm --prefix frontend run build`.

Expected: exit zero and the new lazy route chunk is emitted.

- [ ] **Step 6: Commit public collection navigation**

```bash
git add frontend/src/views/CollectionDetailView.vue frontend/src/router/index.ts frontend/src/views/SoupDetailView.vue
git commit -m "feat: add collection detail navigation"
```

---

### Task 7: Version, Full Verification, And Pull Request

**Files:**
- Modify: `VERSION`

**Interfaces:**
- Produces repository runtime version `1.4.0`.
- Produces a clean pushed feature branch and GitHub Pull Request against `main`.
- Must not access the deployment server.

- [ ] **Step 1: Update the canonical version**

Change the only line in `VERSION` from `1.3.1` to:

```text
1.4.0
```

Do not change `frontend/package.json`; runtime version consumers already read the root file through the backend.

- [ ] **Step 2: Run focused backend verification**

Run:

```bash
PYTHONPATH=backend /tmp/ctg-verify.xA2dJy/bin/python -m pytest -q backend/tests/test_soup_collection_migration.py backend/tests/test_soup_collections_api.py backend/tests/test_social_platform_migration.py
```

Expected: all collection and migration tests pass.

- [ ] **Step 3: Run full verification**

Run:

```bash
npm --prefix frontend run build
PYTHONPATH=backend /tmp/ctg-verify.xA2dJy/bin/python -m pytest -q backend/tests
/tmp/ctg-verify.xA2dJy/bin/python -m compileall -q backend/app
bash -n Update.sh dev.sh setup.sh
git diff --check
test "$(cat VERSION)" = "1.4.0"
```

Expected: frontend build exits zero, pytest reports zero failures, and every remaining command exits zero.

- [ ] **Step 4: Audit and commit the version**

Confirm no PAT, `.env`, runtime storage, dependencies, build output, cache, archives, or temporary files are staged. Commit:

```bash
git add VERSION
git commit -m "chore: bump version to 1.4.0"
```

- [ ] **Step 5: Verify the final commit tree**

Run:

```bash
git status --short
git log --oneline origin/main..HEAD
git diff --name-only origin/main...HEAD
```

Expected: clean status; only collection design/plan, backend collection/migration files, scoped soup integration, frontend collection/profile/detail files, router, and `VERSION` differ.

- [ ] **Step 6: Push and create the GitHub PR**

Push `codex/soup-collections-1-4-0` normally without force and create a PR against `main`. The PR body must summarize collection CRUD/visibility, one-collection soup association, profile/editor/detail UI, migration integration, and version `1.4.0`, and list focused/full verification results.

- [ ] **Step 7: Confirm publication without deployment**

Read the GitHub PR and require state `open`, base `main`, and head SHA equal to local `HEAD`. Stop after reporting the PR URL. Do not call SSH, SFTP, Screen, a remote health endpoint, or any deployment command.
