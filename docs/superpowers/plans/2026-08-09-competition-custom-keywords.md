# Competition Custom Keywords Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let an administrator add reusable global custom tags while publishing a competition and use the resolved tags as that competition's keywords.

**Architecture:** Move ID/name tag resolution into a shared service that returns active global `Tag` rows without committing. Extend competition creation with `custom_tags`, resolve existing and new tags inside the competition transaction, and add a keyword editor beside the existing checkboxes.

**Tech Stack:** FastAPI, Pydantic, SQLModel, Pytest, Vue 3, TypeScript, Tailwind CSS, Playwright

## Global Constraints

- New keywords become active global `custom` tags reusable by soups and later competitions.
- Existing active tags with the same normalized slug are reused; disabled matches are rejected.
- Existing IDs and custom names resolve to 1 through 10 unique tags in total.
- Tag and competition creation commit or roll back together.
- Entry matching remains “any keyword matches”; do not modify `evaluate_soup_competitions`.
- Preserve unrelated worktree changes in shared files.

---

### Task 1: Extract Shared Tag Resolution

**Files:**
- Create: `backend/app/services/tag_resolution.py`
- Create: `backend/tests/test_tag_resolution.py`
- Modify: `backend/app/api/turtle_soups.py`

**Interfaces:**
- Consumes: `normalize_tag_name(value) -> tuple[str, str]`, `Tag`, `TagKind`, and `TagStatus`.
- Produces: `TagSelectionError(code, message)` and `resolve_active_tags(db, tag_ids, custom_names, *, min_count=0, max_count=10) -> list[Tag]`.

- [ ] **Step 1: Write failing resolver tests**

Create an in-memory SQLModel session and test real rows:

```python
def test_resolver_reuses_normalized_name_and_creates_custom_tag(session):
    existing = Tag(name="剧情 推理", slug="剧情-推理", kind=TagKind.SYSTEM)
    session.add(existing)
    session.commit()
    session.refresh(existing)
    tags = resolve_active_tags(
        session,
        [existing.id],
        ["  剧情   推理  ", "夏夜"],
        min_count=1,
        max_count=10,
    )
    assert [tag.name for tag in tags] == ["剧情 推理", "夏夜"]
    assert tags[1].kind == TagKind.CUSTOM
    assert tags[1].status == TagStatus.ACTIVE
```

Add separate tests asserting `TAG_NOT_ACTIVE` for disabled IDs and slugs, `NO_TAGS` for an empty set with `min_count=1`, `TOO_MANY_TAGS` for 11 unique items, and `INVALID_TAG_NAME` for invalid text.

- [ ] **Step 2: Run tests to verify RED**

Run: `cd backend && pytest tests/test_tag_resolution.py -v`

Expected: collection fails because `app.services.tag_resolution` does not exist.

- [ ] **Step 3: Implement the resolver without committing**

Define:

```python
class TagSelectionError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message
```

`resolve_active_tags` preserves first-seen order, validates active ID rows, normalizes custom names, reuses by slug, creates missing tags, and calls `db.flush()` only to obtain IDs. It never calls `db.commit()`. Convert normalization failures to `INVALID_TAG_NAME`; enforce counts after ID/slug deduplication.

- [ ] **Step 4: Run tests to verify GREEN**

Run: `cd backend && pytest tests/test_tag_resolution.py tests/test_tag_rules.py -v`

Expected: all resolver and normalization tests pass.

- [ ] **Step 5: Make soup creation use the shared resolver**

Keep `_resolve_tags(db, tag_ids, custom_names)` as the API adapter, but call `resolve_active_tags(..., min_count=0, max_count=10)`. Convert `TagSelectionError` to the current structured 422 format, retaining `TAG_NOT_ACTIVE` and `TOO_MANY_TAGS` codes.

- [ ] **Step 6: Verify soup tag behavior**

Run: `cd backend && pytest tests/test_soup_metadata_api.py tests/test_tag_resolution.py -v`

Expected: custom tag creation, disabled-tag rejection, and normalization still pass.

### Task 2: Accept Custom Keywords in Competition Creation

**Files:**
- Modify: `backend/app/schemas/competitions.py`
- Modify: `backend/app/api/competitions.py`
- Modify: `backend/tests/test_competition_contract.py`

**Interfaces:**
- Consumes: `resolve_active_tags(...)` and `TagSelectionError` from Task 1.
- Produces: `CompetitionCreate.custom_tags`, optional `required_tag_ids`, and atomic competition/global-tag creation.

- [ ] **Step 1: Write failing API tests**

Add a custom-only creation test:

```python
def test_create_competition_creates_global_custom_keyword():
    client, engine, _ids = _setup()
    response = client.post("/api/competitions", json={
        "name": "夏夜赛",
        "description": "说明",
        "start_time": "2026-08-08T00:00:00",
        "end_time": "2026-08-09T00:00:00",
        "required_tag_ids": [],
        "custom_tags": ["  夏夜   推理  "],
    })
    assert response.status_code == 201
    with Session(engine) as session:
        tag = session.exec(select(Tag).where(Tag.slug == "夏夜-推理")).one()
        assert tag.kind == TagKind.CUSTOM
        assert tag.status == TagStatus.ACTIVE
        assert response.json()["required_tag_ids"] == [tag.id]
```

Add tests for reusing an existing tag supplied by both ID and normalized name, rejecting 11 unique keywords, and rolling back a valid new tag when a later name is invalid.

- [ ] **Step 2: Run tests to verify RED**

Run: `cd backend && pytest tests/test_competition_contract.py -v`

Expected: custom-only creation fails because the schema currently requires one existing ID.

- [ ] **Step 3: Extend the schema**

Use:

```python
required_tag_ids: list[int] = Field(default_factory=list)
custom_tags: list[str] = Field(default_factory=list)
```

Keep positive-ID deduplication. Database-aware name validation belongs to the resolver. Keep time validation unchanged.

- [ ] **Step 4: Resolve tags inside competition creation**

Use:

```python
try:
    tags = resolve_active_tags(
        db,
        data.required_tag_ids,
        data.custom_tags,
        min_count=1,
        max_count=10,
    )
except TagSelectionError as exc:
    code = "COMPETITION_TAG_NOT_ACTIVE" if exc.code == "TAG_NOT_ACTIVE" else exc.code
    raise HTTPException(
        status_code=422,
        detail={"code": code, "message": exc.message},
    ) from exc
```

Construct `Competition(required_tag_ids=[tag.id for tag in tags], ...)`. Retain the one existing `db.commit()` after tags and competition are added. Do not commit inside the resolver or change entry matching.

- [ ] **Step 5: Run tests to verify GREEN**

Run: `cd backend && pytest tests/test_competition_contract.py tests/test_soup_metadata_api.py tests/test_tag_resolution.py -v`

Expected: all tests pass, including the existing disabled-tag error code.

### Task 3: Add the Competition Keyword Editor

**Files:**
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/views/CompetitionCreateView.vue`
- Create: `frontend/tests/e2e/competition-keywords.spec.ts`

**Interfaces:**
- Consumes: `CompetitionCreate.custom_tags` and `tagApi.list`.
- Produces: keyword chips, add/remove controls, combined validation, and a payload containing IDs and custom names.

- [ ] **Step 1: Write a failing browser test**

Mock tags with an empty page and capture competition POST:

```typescript
const input = page.getByRole('textbox', { name: '新增比赛关键词' })
await input.fill('夏夜推理')
await page.getByRole('button', { name: '添加关键词' }).click()
await input.fill('夏夜推理')
await input.press('Enter')
await expect(page.getByText('#夏夜推理')).toHaveCount(1)
await page.getByRole('button', { name: '发布比赛' }).click()
expect(createPayload.required_tag_ids).toEqual([])
expect(createPayload.custom_tags).toEqual(['夏夜推理'])
```

Also test the `移除关键词 夏夜推理` button and the empty error `请至少选择或新增一个比赛关键词`.

- [ ] **Step 2: Run the browser test to verify RED**

Run: `cd frontend && npx playwright test tests/e2e/competition-keywords.spec.ts`

Expected: FAIL because the keyword editor and payload field do not exist.

- [ ] **Step 3: Extend type and form state**

Add `custom_tags: string[]` to `CompetitionCreate`, `newKeyword = ref('')`, and `custom_tags: []` to the form. Add:

```typescript
function addKeyword() {
  const keyword = newKeyword.value.trim()
  if (!keyword || form.custom_tags.includes(keyword)) return
  if (form.required_tag_ids.length + form.custom_tags.length >= 10) {
    error.value = '比赛关键词最多 10 个'
    return
  }
  form.custom_tags.push(keyword)
  newKeyword.value = ''
}

function removeKeyword(keyword: string) {
  form.custom_tags = form.custom_tags.filter((item) => item !== keyword)
}
```

- [ ] **Step 4: Render controls and validate combined count**

Render chips, `aria-label="新增比赛关键词"`, an `添加关键词` button, and an icon-only remove button whose accessible name includes the keyword. Enter calls `addKeyword` instead of submitting.

Before date validation:

```typescript
const keywordCount = form.required_tag_ids.length + form.custom_tags.length
if (!keywordCount) {
  error.value = '请至少选择或新增一个比赛关键词'
  return
}
if (keywordCount > 10) {
  error.value = '比赛关键词最多 10 个'
  return
}
```

Include `custom_tags: form.custom_tags` in the payload. Remove `!tags.length` from the submit disabled expression so custom-only creation works.

- [ ] **Step 5: Run browser test and build**

Run: `cd frontend && npx playwright test tests/e2e/competition-keywords.spec.ts && npm run build`

Expected: browser test and production build pass.

### Task 4: Verify Competition Keywords End to End

**Files:**
- Verify only.

**Interfaces:**
- Consumes: shared resolver, API contract, and editor from Tasks 1 through 3.
- Produces: evidence that custom tags are reusable, atomic, and responsive.

- [ ] **Step 1: Run relevant backend tests**

Run: `cd backend && pytest tests/test_tag_rules.py tests/test_tag_resolution.py tests/test_competition_contract.py tests/test_soup_metadata_api.py -v`

Expected: all tests pass.

- [ ] **Step 2: Run focused frontend suites**

Run: `cd frontend && npx playwright test tests/e2e/competition-keywords.spec.ts tests/e2e/responsive-smoke.spec.ts`

Expected: all tests pass without layout or console errors.

- [ ] **Step 3: Review the scoped diff**

Run: `git diff --check` and inspect only the files listed by Tasks 1 through 3.

Expected: no whitespace errors, no commit inside tag resolution, no change to `evaluate_soup_competitions`, and no unrelated reversions.
