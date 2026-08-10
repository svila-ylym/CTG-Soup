# Content Editing, Soup UX, Account Lifecycle, and Moderation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve and edit soup/post content correctly, add soup images and accurate list behavior, link message avatars, expire abandoned registrations with exact UID reuse, and let administrators revoke eligible user punishments.

**Architecture:** Add relational soup-image storage and shared Vue editors, compute comment counts independently, and drive soup pagination/tags from API metadata. Add durable UID allocator/release tables plus an in-process cleanup loop protected by a PostgreSQL advisory lock. Reuse existing profile, report, competition, and punishment contracts while widening revocation through the established role hierarchy.

**Tech Stack:** FastAPI, SQLModel/SQLAlchemy, Pydantic v2, PostgreSQL/SQLite test engines, Vue 3 Composition API, Pinia, Axios, Tailwind CSS, Heroicons, Playwright.

## Global Constraints

- Do not use a test-first TDD cycle; implement each task before adding or running its focused regression checks.
- Preserve soup puzzle and solution text exactly, including leading/trailing spaces and blank lines.
- Puzzle and solution each require non-whitespace text or at least one image and allow at most five images.
- Solution text and image URLs must stay out of unrevealed API responses.
- Admin and root users cannot update content they did not author; existing delete/moderation permissions remain unchanged.
- Soup comment count means published top-level comments, matching the existing comments page `total`.
- Soup pages contain 30 rows, use `total_pages` for navigation, and load active tag options from `/api/tags` by ID.
- Pending-email accounts expire exactly 30 minutes after account creation; cleanup runs immediately at startup and every 60 seconds.
- Only UIDs recorded by pending-account cleanup are reusable; normal allocations consumed while filling gaps are never inferred as reusable holes.
- Ordinary admins may revoke regular-user status punishments, review reports, and create competitions, but cannot manage self, peer admins, or root.
- Do not delete public upload objects when detaching them from a soup.
- Preserve unrelated working-tree and index changes. Target files already contain overlapping user edits, so implementation tasks create diff checkpoints but no Git commits.

---

### Task 1: Soup Image Persistence and API Types

**Files:**
- Modify: `backend/app/models/models.py`
- Modify: `backend/app/models/database.py`
- Modify: `backend/app/schemas/soups.py`
- Modify: `backend/tests/test_model_import.py`
- Modify: `backend/tests/test_soup_metadata_contract.py`

**Interfaces:**
- Produces: `SoupImage` SQLModel with `soup_id`, `asset_id`, `placement`, and `sort_order`.
- Produces: `SoupCreate.puzzle_image_ids`, `SoupCreate.solution_image_ids`, and optional update counterparts.
- Produces: `SoupResponse.puzzle_images`, `SoupResponse.solution_images`, `SoupResponse.comment_count`, and `SoupResponse.can_edit`.

- [ ] **Step 1: Add the relational image model and export it**

Add after `Soup` in `models.py`:

```python
class SoupImage(SQLModel, table=True):
    __tablename__ = "soup_images"
    __table_args__ = (
        UniqueConstraint("soup_id", "asset_id", name="uq_soup_images_soup_asset"),
        UniqueConstraint(
            "soup_id",
            "placement",
            "sort_order",
            name="uq_soup_images_placement_order",
        ),
        CheckConstraint(
            "placement IN ('puzzle', 'solution')",
            name="ck_soup_images_placement",
        ),
        CheckConstraint("sort_order >= 0", name="ck_soup_images_sort_order"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    soup_id: int = Field(foreign_key="soups.id", index=True)
    asset_id: int = Field(foreign_key="uploaded_assets.id", index=True)
    placement: str = Field(max_length=16, index=True)
    sort_order: int = Field(ge=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

Import and include `SoupImage` in `backend/app/models/database.py::__all__` so route and test modules use the canonical export.

- [ ] **Step 2: Extend soup request and response schemas**

Import `UploadedAssetResponse` from `app.schemas`. Change create text defaults and add image fields:

```python
class SoupCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    puzzle: str = ""
    solution: str = ""
    puzzle_image_ids: list[int] = Field(default_factory=list, max_length=5)
    solution_image_ids: list[int] = Field(default_factory=list, max_length=5)
```

Add a validator shared by both lists that rejects non-positive and duplicate IDs without reordering them. Make every `SoupUpdate` field optional with a default of `None`, including people fields, and add optional image-ID lists. Extend `SoupResponse` exactly as follows:

```python
puzzle_images: list[UploadedAssetResponse] = Field(default_factory=list)
solution_images: list[UploadedAssetResponse] = Field(default_factory=list)
comment_count: int = Field(ge=0)
can_edit: bool
```

- [ ] **Step 3: Add post-implementation model and schema regression checks**

Extend `test_model_import.py` to assert `SoupImage.__tablename__ == "soup_images"`. Extend `test_soup_metadata_contract.py` with:

```python
def test_soup_content_can_be_image_only_and_image_ids_keep_order():
    item = SoupCreate(
        title="图片汤",
        puzzle="",
        solution="",
        genre="本格",
        soup_color="清汤",
        main_player_count="",
        secondary_player_count="",
        puzzle_image_ids=[3, 1],
        solution_image_ids=[4],
    )
    assert item.puzzle == ""
    assert item.puzzle_image_ids == [3, 1]
    assert item.solution_image_ids == [4]
```

Also assert duplicate, zero, and six-item lists raise `ValidationError`.

- [ ] **Step 4: Run focused backend checks**

Run:

```bash
PYTHONPATH=backend backend/venv/bin/python -m pytest -q \
  backend/tests/test_model_import.py \
  backend/tests/test_soup_metadata_contract.py
```

Expected: exit code 0 with all selected tests passing.

- [ ] **Step 5: Review the Task 1 diff checkpoint**

```bash
git diff --check -- \
  backend/app/models/models.py \
  backend/app/models/database.py \
  backend/app/schemas/soups.py \
  backend/tests/test_model_import.py \
  backend/tests/test_soup_metadata_contract.py
```

### Task 2: Soup Image Validation, Exact Text, and Spoiler-Safe Responses

**Files:**
- Modify: `backend/app/api/turtle_soups.py`
- Modify: `backend/tests/test_soup_metadata_api.py`

**Interfaces:**
- Consumes: `SoupImage`, `UploadedAsset`, and the Task 1 request/response fields.
- Produces: `_resolve_owned_images`, `_sync_soup_images`, `_soup_images`, and `_validate_content_presence` helpers.
- Produces: transactional create/update behavior with ordered image relations.

- [ ] **Step 1: Add image lookup and content validation helpers**

Import `UploadedAsset` and `SoupImage`. Add helpers with these signatures:

```python
def _resolve_owned_images(
    db: Session,
    owner_uid: int,
    puzzle_ids: list[int],
    solution_ids: list[int],
) -> tuple[list[UploadedAsset], list[UploadedAsset]]:
    all_ids = [*puzzle_ids, *solution_ids]
    if len(all_ids) != len(set(all_ids)):
        raise HTTPException(
            status_code=422,
            detail={"code": "DUPLICATE_SOUP_IMAGE", "message": "同一图片不能重复添加"},
        )
    if not all_ids:
        return [], []
    assets = db.exec(
        select(UploadedAsset).where(UploadedAsset.id.in_(all_ids))
    ).all()
    by_id = {asset.id: asset for asset in assets}
    if any(
        asset_id not in by_id
        or by_id[asset_id].owner_uid != owner_uid
        or by_id[asset_id].kind != "image"
        for asset_id in all_ids
    ):
        raise HTTPException(
            status_code=422,
            detail={"code": "INVALID_SOUP_IMAGE", "message": "图片不存在或不属于当前用户"},
        )
    return (
        [by_id[asset_id] for asset_id in puzzle_ids],
        [by_id[asset_id] for asset_id in solution_ids],
    )

def _soup_images(db: Session, soup_id: int, placement: str) -> list[UploadedAsset]:
    return db.exec(
        select(UploadedAsset)
        .join(SoupImage, SoupImage.asset_id == UploadedAsset.id)
        .where(SoupImage.soup_id == soup_id, SoupImage.placement == placement)
        .order_by(SoupImage.sort_order)
    ).all()

def _sync_soup_images(
    db: Session,
    soup_id: int,
    puzzle_assets: list[UploadedAsset],
    solution_assets: list[UploadedAsset],
) -> None:
    for row in db.exec(select(SoupImage).where(SoupImage.soup_id == soup_id)).all():
        db.delete(row)
    for placement, assets in (
        ("puzzle", puzzle_assets),
        ("solution", solution_assets),
    ):
        for sort_order, asset in enumerate(assets):
            db.add(SoupImage(
                soup_id=soup_id,
                asset_id=asset.id,
                placement=placement,
                sort_order=sort_order,
            ))
    db.flush()

def _validate_content_presence(
    puzzle: str,
    solution: str,
    puzzle_assets: list[UploadedAsset],
    solution_assets: list[UploadedAsset],
) -> None:
    if not puzzle.strip() and not puzzle_assets:
        raise HTTPException(
            status_code=422,
            detail={"code": "PUZZLE_CONTENT_REQUIRED", "message": "谜面需要文字或图片"},
        )
    if not solution.strip() and not solution_assets:
        raise HTTPException(
            status_code=422,
            detail={"code": "SOLUTION_CONTENT_REQUIRED", "message": "汤底需要文字或图片"},
        )
```

`_resolve_owned_images` must preserve client order, reject IDs repeated across placements, and return a structured 422 error for missing, non-image, or foreign-owned assets. `_validate_content_presence` calls `.strip()` only for the emptiness decision and never returns normalized text.

- [ ] **Step 2: Return image lists without leaking solution URLs**

Extend `_payload` with an optional `comment_count` argument. Set:

```python
shown = _can_reveal_solution(soup, reveal)
puzzle_images = _soup_images(db, soup.id, "puzzle")
solution_images = _soup_images(db, soup.id, "solution") if shown else []
```

Return the original `soup.puzzle`, `soup.solution if shown else None`, both image lists, `comment_count`, `can_edit=is_author`, and the existing `can_manage` value.

- [ ] **Step 3: Preserve exact text and synchronize images in create/update**

Create uses `puzzle=data.puzzle` and `solution=data.solution` with no stripping. Resolve and validate assets before adding the soup, then call `_sync_soup_images` after the first soup flush. Keep tags, competition evaluation, image links, and `db.commit()` in one transaction.

Update must reject whenever `soup.author_uid != current_user.uid`, even for admin/root. Build effective values from stored text/images plus fields present in `SoupUpdate`, validate the effective puzzle and solution, synchronize both placements, apply scalar fields, evaluate competitions, commit, refresh, and return the revealed payload. Keep delete authorization unchanged.

- [ ] **Step 4: Add post-implementation API regression coverage**

Extend the SQLite fixture with author-owned and foreign `UploadedAsset` rows. Add API checks that:

```python
exact_puzzle = "\n    第一行\n      第二行\n\n"
exact_solution = "  \n汤底\n"
```

survive create and subsequent detail reads unchanged; image-only puzzle/solution creates return 201; empty text plus empty images returns 422; foreign assets return 422; solution image URLs are absent before `reveal=true` and present afterward; image order matches submitted IDs; and a root/admin user receives 403 when updating another author's soup.

- [ ] **Step 5: Run the soup API regression file**

Run:

```bash
PYTHONPATH=backend backend/venv/bin/python -m pytest -q \
  backend/tests/test_soup_metadata_api.py
```

Expected: exit code 0.

- [ ] **Step 6: Review the Task 2 diff checkpoint**

```bash
git diff --check -- \
  backend/app/api/turtle_soups.py \
  backend/tests/test_soup_metadata_api.py
```

### Task 3: Real Soup Comment Counts and Author-Only Post Updates

**Files:**
- Modify: `backend/app/api/turtle_soups.py`
- Modify: `backend/app/api/posts.py`
- Modify: `backend/app/schemas/community.py`
- Modify: `backend/tests/test_soup_comments_api.py`
- Modify: `backend/tests/test_community_contract.py`

**Interfaces:**
- Produces: `_soup_comment_counts(db, soup_ids) -> dict[int, int]`.
- Produces: `PostResponse.can_edit` and current-user-aware post payloads.

- [ ] **Step 1: Compute comment counts separately from ratings**

Import `func` from SQLAlchemy and add:

```python
def _soup_comment_counts(db: Session, soup_ids: list[int]) -> dict[int, int]:
    if not soup_ids:
        return {}
    rows = db.exec(
        select(Comment.target_id, func.count(Comment.id))
        .where(
            Comment.target_type == CommentTargetType.SOUP,
            Comment.target_id.in_(soup_ids),
            Comment.parent_id.is_(None),
            Comment.status == "published",
        )
        .group_by(Comment.target_id)
    ).all()
    return {target_id: count for target_id, count in rows}
```

The list route computes this map once for the current page and passes each count to `_payload`. Create passes `0`; detail and update query the current soup ID. Do not read `rating_count` for this field.

- [ ] **Step 2: Add author-only post edit capability to responses and route checks**

Add `can_edit: bool` to `PostResponse`. Change `_payload` to accept `current_user: User | None` and return `can_edit=bool(current_user and post.author_uid == current_user.uid)`. Pass the optional/current user from create, list, detail, and update routes. Replace the update authorization condition with:

```python
if post.author_uid != current_user.uid:
    raise HTTPException(status_code=403, detail="只能修改自己的帖子")
```

Do not change delete authorization.

- [ ] **Step 3: Add post-implementation count and permission checks**

In `test_soup_comments_api.py`, create two root comments, one reply, and one rating, then assert the soup list/detail `comment_count` is `2` and `rating_count` is `1`. Delete one root and assert the count becomes `1`.

In `test_community_contract.py`, assert post payloads expose `can_edit`, the author can update title/content/section, and the root user receives 403 when updating the other user's post while retaining delete permission.

- [ ] **Step 4: Run focused community checks**

Run:

```bash
PYTHONPATH=backend backend/venv/bin/python -m pytest -q \
  backend/tests/test_soup_comments_api.py \
  backend/tests/test_community_contract.py
```

Expected: exit code 0.

- [ ] **Step 5: Review the Task 3 diff checkpoint**

```bash
git diff --check -- \
  backend/app/api/turtle_soups.py \
  backend/app/api/posts.py \
  backend/app/schemas/community.py \
  backend/tests/test_soup_comments_api.py \
  backend/tests/test_community_contract.py
```

### Task 4: Shared Soup Editor and Image Picker

**Files:**
- Create: `frontend/src/components/SoupImagePicker.vue`
- Create: `frontend/src/components/SoupEditorForm.vue`
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/api/soup.ts`

**Interfaces:**
- Produces: `SoupImageRef`, extended `TurtleSoup`/`SoupCreate`, and `SoupEditorState` frontend types.
- Produces: `SoupImagePicker` `v-model` interface for up to five ordered images.
- Produces: `SoupEditorForm` `v-model` plus `submit`/`cancel` events.

- [ ] **Step 1: Extend frontend types and API wrapper**

Add:

```typescript
export interface SoupImageRef {
  id: number
  public_url: string
  mime_type: string
  size: number
}

export type SoupEditorState = Omit<
  SoupCreate,
  'puzzle_image_ids' | 'solution_image_ids'
> & {
  puzzle_images: SoupImageRef[]
  solution_images: SoupImageRef[]
}
```

Extend `TurtleSoup` with both image arrays, `comment_count`, and `can_edit`.
Extend `SoupCreate` with `puzzle_image_ids` and `solution_image_ids`. Change
`soupApi.update` to return:

```typescript
return http.put<TurtleSoup>(`/turtle-soups/${id}`, data)
```

- [ ] **Step 2: Build the bounded image picker**

`SoupImagePicker.vue` accepts `v-model: SoupImageRef[]`, `label`, `disabled`,
and `max=5`. It calls `uploadApi.image(file)` sequentially, maps each response
to `{ id: asset_id, public_url: url, mime_type, size }`, and emits a new array.
Use `PhotoIcon`, `ArrowLeftIcon`, `ArrowRightIcon`, and `XMarkIcon` buttons with
tooltips. Disable upload at five items, preserve aspect ratio with
`object-contain`, and expose upload errors without clearing prior selections.

- [ ] **Step 3: Extract the reusable soup form**

`SoupEditorForm.vue` uses:

```typescript
const state = defineModel<SoupEditorState>({ required: true })
const props = defineProps<{
  submitting: boolean
  error: string
  submitLabel: string
}>()
const emit = defineEmits<{ submit: []; cancel: [] }>()
```

Move the existing title, genre, color, people, tag, and reveal controls into
this component. Replace required textarea attributes with a combined
text-or-image error for each section. Render one `SoupImagePicker` below puzzle
and another below solution. On submit, emit only when title/taxonomy are valid
and each section has `text.trim()` or at least one image.

- [ ] **Step 4: Run frontend type/build verification**

Run:

```bash
cd frontend
npm run build
```

Expected: Vue type-check and Vite build exit 0.

- [ ] **Step 5: Review the Task 4 diff checkpoint**

```bash
git diff --check -- \
  frontend/src/components/SoupImagePicker.vue \
  frontend/src/components/SoupEditorForm.vue \
  frontend/src/types/index.ts \
  frontend/src/api/soup.ts
```

### Task 5: Soup Create/Edit Pages, Detail Galleries, and Comment UI

**Files:**
- Modify: `frontend/src/views/SoupCreateView.vue`
- Create: `frontend/src/views/SoupEditView.vue`
- Modify: `frontend/src/views/SoupDetailView.vue`
- Modify: `frontend/src/views/soup/SoupListView.vue`
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/tests/e2e/responsive-smoke.spec.ts`

**Interfaces:**
- Consumes: `SoupEditorForm`, `SoupEditorState`, image response fields, and `can_edit`.
- Produces: authenticated `/soups/:id/edit` route and spoiler-safe responsive galleries.

- [ ] **Step 1: Convert the create view into a wrapper around the shared form**

Keep draft persistence in `SoupCreateView`. Store the exact puzzle/solution
strings and image ID arrays. Resolve restored IDs through `uploadApi.images()`
before populating preview arrays. Submit this payload without trimming body
text:

```typescript
const { puzzle_images, solution_images, ...fields } = state.value
await soupStore.createSoup({
  ...fields,
  title: fields.title.trim(),
  puzzle: fields.puzzle,
  solution: fields.solution,
  puzzle_image_ids: puzzle_images.map(image => image.id),
  solution_image_ids: solution_images.map(image => image.id),
})
```

Clear the draft only after a successful create response.

- [ ] **Step 2: Add the soup edit page and route**

Register `/soups/:id/edit` with `requiresAuth: true`. `SoupEditView` loads
`soupApi.getById(id, true)`, rejects `!response.data.can_edit`, maps tag IDs and
image arrays into `SoupEditorState`, submits the full payload with
`soupApi.update`, then routes to `/soups/:id`.

- [ ] **Step 3: Add author editing and image galleries to soup detail**

Add a `PencilSquareIcon` edit button guarded by `soup.can_edit`. Keep delete
guarded by `soup.can_manage`. Render puzzle images immediately and solution
images only inside the existing revealed section. Use responsive grid tracks,
uncropped `object-contain` images, original-URL links, and alt text derived from
the soup title plus image position.

- [ ] **Step 4: Bind the comment icon to the correct field**

In `SoupListView.vue`, change only the comment bubble value:

```vue
<ChatBubbleLeftRightIcon class="mr-1 h-4 w-4" aria-hidden="true" />
{{ soup.comment_count }}
```

Rating surfaces on detail, home, search, and leaderboard continue using
`rating_count` and rating labels.

- [ ] **Step 5: Update responsive mocked soup contracts and run checks**

Add `puzzle_images: []`, `solution_images: []`, `comment_count: 0`, and
`can_edit: false` to the Playwright fixture. Run:

```bash
cd frontend
npm run build
npx playwright test tests/e2e/responsive-smoke.spec.ts
```

Expected: build and responsive smoke test exit 0 with no clipped image or edit controls.

- [ ] **Step 6: Review the Task 5 diff checkpoint**

```bash
git diff --check -- \
  frontend/src/views/SoupCreateView.vue \
  frontend/src/views/SoupEditView.vue \
  frontend/src/views/SoupDetailView.vue \
  frontend/src/views/soup/SoupListView.vue \
  frontend/src/router/index.ts \
  frontend/tests/e2e/responsive-smoke.spec.ts
```

### Task 6: Author-Only Post Edit Page

**Files:**
- Modify: `frontend/src/api/posts.ts`
- Modify: `frontend/src/types/index.ts`
- Create: `frontend/src/views/PostEditView.vue`
- Modify: `frontend/src/views/PostDetailView.vue`
- Modify: `frontend/src/router/index.ts`

**Interfaces:**
- Consumes: backend `PostResponse.can_edit` and `PUT /api/posts/{id}`.
- Produces: `postsApi.update` and authenticated `/posts/:id/edit` route.

- [ ] **Step 1: Add the typed post update wrapper**

Add `can_edit: boolean` to `Post` and:

```typescript
update(postId: number, data: Pick<Post, 'title' | 'content' | 'section'>) {
  return http.put<Post>(`/posts/${postId}`, data)
}
```

- [ ] **Step 2: Build the full-page post editor**

`PostEditView.vue` loads the post, displays title/section/content controls,
rejects a non-author response, and submits trimmed title/section plus content
through `postsApi.update`. Disable submit while saving, preserve the form after
API errors, and route back to the detail page after success.

- [ ] **Step 3: Register the route and detail edit button**

Register `/posts/:id/edit` before `/posts/:id`, with `requiresAuth: true`.
Add a `PencilSquareIcon` button in `PostDetailView` guarded by `post.can_edit`.
Keep the current delete guard unchanged so moderation still works.

- [ ] **Step 4: Build the complete frontend**

Run:

```bash
cd frontend
npm run build
```

Expected: exit code 0.

- [ ] **Step 5: Review the Task 6 diff checkpoint**

```bash
git diff --check -- \
  frontend/src/api/posts.ts \
  frontend/src/types/index.ts \
  frontend/src/views/PostEditView.vue \
  frontend/src/views/PostDetailView.vue \
  frontend/src/router/index.ts
```

### Task 7: Soup Pagination, Dynamic Tags, and Message Avatar Links

**Files:**
- Modify: `frontend/src/views/soup/SoupListView.vue`
- Modify: `frontend/src/views/MessageView.vue`
- Modify: `frontend/tests/e2e/responsive-smoke.spec.ts`

**Interfaces:**
- Consumes: existing `tagApi.list`, soup `PageResult.total_pages`, and `/profile/:uid` route.
- Produces: 30-row soup pages, real active-tag selection by ID, and navigable private-message avatars.

- [ ] **Step 1: Replace hard-coded tag options with all active API tags**

Import `tagApi` and `Tag`, store `availableTags: Tag[]` and
`selectedTagId: number | ''`, and load all pages in usage-count order:

```typescript
async function loadTags() {
  const first = await tagApi.list({ page: 1, page_size: 100, sort_by: 'usage_count' })
  const items = [...first.data.items]
  for (let page = 2; page <= first.data.total_pages; page += 1) {
    const response = await tagApi.list({ page, page_size: 100, sort_by: 'usage_count' })
    items.push(...response.data.items)
  }
  availableTags.value = items
}
```

The selector keeps its all-tags option and renders `tag.name`; soup requests
send `tag_id: selectedTagId || undefined`. A failed tag request sets
`availableTags` to an empty list and does not set the soup store error.

- [ ] **Step 2: Drive navigation from API page metadata**

Use `const pageSize = 30` and `const totalPages = ref(0)`. Both initial/filter
loads and page changes await `soupStore.fetchList`, then copy
`response.total_pages`. Reject page changes below 1 or above `totalPages`, and
render the next button only with:

```vue
<button v-if="currentPage < totalPages" @click="changePage(currentPage + 1)">
  下一页
</button>
```

Do not introduce a fixed-height or nested scroll container.

- [ ] **Step 3: Link both other-user avatars to profiles**

In the conversation list, keep conversation selection on the text portion and
wrap only the avatar image/fallback in a router link to
`/profile/${conversation.other_user.uid}`. In the active header, wrap the avatar
in the same link. Stop click propagation so avatar navigation does not also
open/replace the conversation route.

- [ ] **Step 4: Add post-implementation UI coverage and build**

Extend the responsive Playwright fixture to return exactly 30 soup rows with
`total_pages: 1`, assert no next-page button, then return 31 rows over two pages
and assert the button appears only on page one. Assert tag options come from the
mocked tags endpoint and both message avatar links target the expected profile.
Run:

```bash
cd frontend
npm run build
npx playwright test tests/e2e/responsive-smoke.spec.ts
```

- [ ] **Step 5: Review the Task 7 diff checkpoint**

```bash
git diff --check -- \
  frontend/src/views/soup/SoupListView.vue \
  frontend/src/views/MessageView.vue \
  frontend/tests/e2e/responsive-smoke.spec.ts
```

### Task 8: Durable UID Allocation and Pending-Account Cleanup Service

**Files:**
- Modify: `backend/app/models/models.py`
- Modify: `backend/app/models/database.py`
- Create: `backend/app/services/pending_accounts.py`
- Modify: `backend/tests/test_model_import.py`
- Create: `backend/tests/test_pending_accounts.py`

**Interfaces:**
- Produces: `UserUidAllocator`, `ReusableUserUid`, `allocate_user_uid(db) -> int`, and `cleanup_expired_pending_users(db, now=None) -> list[int]`.
- Consumes later: registration and application lifecycle tasks.

- [ ] **Step 1: Add allocator and released-UID tables**

Add:

```python
class UserUidAllocator(SQLModel, table=True):
    __tablename__ = "user_uid_allocator"
    id: int = Field(default=1, primary_key=True)
    next_uid: int = Field(ge=1)


class ReusableUserUid(SQLModel, table=True):
    __tablename__ = "reusable_user_uids"
    uid: int = Field(primary_key=True, ge=1)
    released_at: datetime = Field(default_factory=datetime.utcnow, index=True)
```

Export both through `app.models.database`. The startup `create_all` path creates
them for existing deployments.

- [ ] **Step 2: Implement serialized allocation**

In `pending_accounts.py`, define one signed 64-bit advisory-lock key and:

```python
def lock_uid_allocation(db: Session) -> None:
    if db.get_bind().dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": UID_LOCK_KEY})


def allocate_user_uid(db: Session) -> int:
    lock_uid_allocation(db)
    allocator = db.exec(
        select(UserUidAllocator).where(UserUidAllocator.id == 1).with_for_update()
    ).first()
    max_uid = db.exec(select(func.max(User.uid))).one() or 0
    if allocator is None:
        allocator = UserUidAllocator(id=1, next_uid=max_uid + 1)
        db.add(allocator)
        db.flush()
    normal_uid = max(allocator.next_uid, max_uid + 1)
    allocator.next_uid = normal_uid + 1
    released = db.exec(
        select(ReusableUserUid).order_by(ReusableUserUid.uid).with_for_update()
    ).first()
    if released is None:
        return normal_uid
    uid = released.uid
    db.delete(released)
    return uid
```

The caller owns commit/rollback so allocator advance, pool removal, and user
insert remain one transaction.

- [ ] **Step 3: Implement 30-minute cleanup**

`cleanup_expired_pending_users` uses a fixed 30-minute cutoff, takes the same
allocation lock, selects candidate UIDs, locks each user's verification rows
before the user row, and rechecks status/cutoff. It deletes every verification
row, inserts `ReusableUserUid(uid=user.uid)` when absent, deletes the user, and
commits once. Return deleted UIDs for logging. Roll back and re-raise on errors.

- [ ] **Step 4: Add post-implementation service checks**

Cover table imports, cleanup of legacy pending users, preservation of active and
younger pending users, deletion of verification rows, and the exact allocation
sequence. Seed users `1,2,7,8,9,10` plus released UIDs `3,4,5,6`; six committed
allocations must return:

```python
assert allocated == [3, 4, 5, 6, 15, 16]
```

Also assert pool removal rolls back when the surrounding transaction fails.

- [ ] **Step 5: Run focused checks and diff review**

```bash
PYTHONPATH=backend backend/venv/bin/python -m pytest -q \
  backend/tests/test_model_import.py \
  backend/tests/test_pending_accounts.py
git diff --check -- \
  backend/app/models/models.py \
  backend/app/models/database.py \
  backend/app/services/pending_accounts.py \
  backend/tests/test_model_import.py \
  backend/tests/test_pending_accounts.py
```

### Task 9: Registration Allocation and In-Process Cleanup Lifecycle

**Files:**
- Modify: `backend/app/api/auth.py`
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_auth_security.py`
- Modify: `backend/tests/test_database_initialization.py`

**Interfaces:**
- Consumes: Task 8 `allocate_user_uid` and `cleanup_expired_pending_users`.
- Produces: explicit UID assignment on registration and startup/60-second cleanup execution.

- [ ] **Step 1: Allocate the UID inside the registration transaction**

After validation/rate limiting and before constructing `User`, call
`allocated_uid = allocate_user_uid(db)` and pass `uid=allocated_uid`. Keep root
bootstrap based on `db_user.uid == 1`, verification creation, and the user
insert in the same transaction. Existing `IntegrityError` handling rolls back a
released pool removal.

- [ ] **Step 2: Add startup and shutdown lifecycle management**

Create a synchronous helper that opens `Session(engine)`, runs cleanup, and logs
deleted UIDs/count. Startup calls it immediately after `init_db()`, then stores
an `asyncio.create_task` loop on `app.state`. The loop sleeps 60 seconds before
each later cleanup, catches/logs exceptions, and continues. Shutdown cancels and
awaits the task with `contextlib.suppress(asyncio.CancelledError)`.

- [ ] **Step 3: Add post-implementation route/lifecycle checks**

Assert registration assigns the smallest released UID while advancing allocator
state, duplicate registration rollback preserves the released UID, startup
invokes cleanup once, the loop survives one cleanup exception, and shutdown
cancels it. Keep SMTP mocked; do not use real mail or sleep 60 seconds in tests.

- [ ] **Step 4: Run focused checks and diff review**

```bash
PYTHONPATH=backend backend/venv/bin/python -m pytest -q \
  backend/tests/test_auth_security.py \
  backend/tests/test_database_initialization.py \
  backend/tests/test_pending_accounts.py
git diff --check -- \
  backend/app/api/auth.py \
  backend/app/main.py \
  backend/tests/test_auth_security.py \
  backend/tests/test_database_initialization.py
```

### Task 10: Administrator Punishment Revocation in User Management

**Files:**
- Modify: `backend/app/api/admin.py`
- Modify: `frontend/src/views/admin/AdminDashboard.vue`
- Modify: `backend/tests/test_admin_management_completion.py`

**Interfaces:**
- Consumes: existing `POST /api/admin/punish/{id}/revoke`, `can_manage_role`, and loaded users/punishments.
- Produces: admin-or-root revocation with hierarchy enforcement and direct user-row controls.

- [ ] **Step 1: Widen the revoke endpoint with role checks**

Change the dependency to `get_current_admin_user`. Under the existing role and
punishment locks, reload actor, punishment, and target. Reject self-targeting,
root targets, and any target for which
`can_manage_role(current_user.role.value, target.role.value)` is false. Keep the
current two-character reason validation, remaining-punishment status derivation,
token invalidation, operation log, and notification unchanged.

- [ ] **Step 2: Expose safe revocation in both admin views**

Change `revokePunishment` to allow `auth.isAdmin`. Add helpers that find the
non-revoked, non-expired `ban` or `silence` punishment matching a user's current
status and check the actor/target hierarchy. In the user row, render the shared
reason input and `解除封禁` or `解除禁言` button. In punishment history, show the
same revoke control to eligible ordinary admins and show a read-only status for
admin/root targets they cannot manage.

- [ ] **Step 3: Add post-implementation permission checks**

Assert an ordinary admin can decide a report, create a competition, and revoke
a regular user's ban/silence. Assert the same admin receives 403 for self,
another admin, and root targets. Retain the existing case where revoking a ban
while silence remains changes `banned -> silenced`, then the second revocation
changes `silenced -> active`.

- [ ] **Step 4: Run focused checks and diff review**

```bash
PYTHONPATH=backend backend/venv/bin/python -m pytest -q \
  backend/tests/test_admin_management_completion.py \
  backend/tests/test_competition_contract.py
cd frontend && npm run build
git diff --check -- \
  backend/app/api/admin.py \
  frontend/src/views/admin/AdminDashboard.vue \
  backend/tests/test_admin_management_completion.py
```

### Task 11: End-to-End Verification and Deployment Check

**Files:**
- Modify when contract fixtures require it: `frontend/tests/e2e/rating-lock.spec.ts`
- Modify when contract snapshots require it: `backend/tests/test_openapi_snapshot.py`

**Interfaces:**
- Verifies all prior tasks together; produces no new runtime API.

- [ ] **Step 1: Run the full backend suite**

Run:

```bash
PYTHONPATH=backend backend/venv/bin/python -m pytest -q backend/tests
```

Expected: exit code 0 and zero failures.

- [ ] **Step 2: Run full frontend build and E2E suite**

Run:

```bash
cd frontend
npm run build
npx playwright test
```

Expected: exit code 0 for both commands.

- [ ] **Step 3: Verify the new table creation path**

Start the backend against a fresh disposable SQLite database or run the model
initialization test, then verify `inspect(engine).get_table_names()` contains
`soup_images`, `user_uid_allocator`, and `reusable_user_uids`. On PostgreSQL
deployment, restart the backend once so the existing startup
`SQLModel.metadata.create_all()` creates these tables and the first cleanup pass
processes legacy pending users.

- [ ] **Step 4: Exercise the five critical browser flows**

Verify: image-only soup creation; exact leading/trailing blank-line rendering;
unrevealed solution responses with no solution image URLs; author soup/post
edits; and admin/root receiving 403 when directly calling update on another
author's content. Confirm a rating changes `rating_count` without changing the
comment bubble, while adding a top-level comment changes `comment_count`.
Confirm 30/31-item pagination boundaries, API-backed tag options, both message
avatar links, 30-minute account cleanup and UID reuse, and ordinary-admin
report review, competition creation, and eligible punishment revocation.

- [ ] **Step 5: Review the final diff without committing user changes**

Run `git diff --check` and inspect every touched file. If Task 7 required the
listed fixture/snapshot updates, leave them in the working tree with the rest
of the implementation for user-controlled commit preparation:

```bash
git diff --check -- \
  frontend/tests/e2e/rating-lock.spec.ts \
  backend/tests/test_openapi_snapshot.py
```
