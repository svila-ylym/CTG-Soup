# Redis Cache, Glass UI, and Loading Experience Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship version 1.5.0 with a resilient Redis cache for surveys, fewer database queries, smoother survey loading, corrected glass/rounded styling, and a black blurred profile overlay in dark mode.

**Architecture:** Keep Redis optional behind a synchronous cache adapter with short timeouts and a retry cooldown. Cache only JSON-safe survey response data under versioned keys, keep authorization and per-user submission state outside shared cache, and invalidate after successful database writes. Improve perceived loading with stable skeleton layouts and non-destructive refresh states while centralizing glass theme variables in CSS.

**Tech Stack:** FastAPI, SQLModel/SQLAlchemy, redis-py 5, Pydantic 2, Vue 3 Composition API, TypeScript, Tailwind CSS 4, Playwright, pytest.

## Global Constraints

- Release version is exactly `1.5.0`.
- Redis remains optional; every cache failure falls back to the database without failing the request.
- Do not cache ORM instances, sessions, credentials, or user-private response state.
- Do not use Redis `KEYS`; pattern invalidation uses bounded `SCAN` batches.
- Shared detail cache contains only common survey fields; `has_submitted` is calculated per current user.
- Preserve existing authorization checks before serving shared cached data.
- Follow the user's instruction not to use TDD: implement first, then add/run focused regression tests.
- Do not introduce a new frontend or backend dependency.

---

## File Map

- `backend/app/utils/cache.py`: Redis lifecycle, cooldown, JSON encoding, versioned key generation, cache commands, and scan deletion.
- `backend/app/utils/__init__.py`: public cache exports without the unsafe unused decorator.
- `backend/app/core/config.py`: validated Redis timeout and cooldown settings.
- `backend/.env.example`: documented cache tuning defaults.
- `backend/app/schemas/surveys.py`: per-user `has_submitted` response field and safe list defaults.
- `backend/app/api/surveys.py`: optimized queries, explicit list/detail caching, user submission state, and write invalidation.
- `backend/tests/test_cache.py`: adapter behavior after implementation.
- `backend/tests/test_surveys_api.py`: cache, authorization, counts, submission state, and invalidation regressions.
- `frontend/src/api/surveys.ts`: typed `has_submitted` and status parameters.
- `frontend/src/views/SurveyListView.vue`: skeletons, retained-content refresh, errors, and accessible busy state.
- `frontend/src/views/SurveyDetailView.vue`: skeletons, direct `has_submitted` use, and load errors.
- `frontend/src/assets/main.css`: glass tokens, fallbacks, correct rounding/clipping, skeletons, and reduced motion.
- `frontend/src/App.vue`: non-blanking route transition.
- `frontend/src/views/ProfileView.vue`: light/dark blurred overlay colors.
- `frontend/tests/e2e/survey-loading-glass.spec.ts`: loading and visual-class behavior with mocked APIs.
- `VERSION`, `frontend/package.json`, `frontend/package-lock.json`: release version alignment.

---

### Task 1: Resilient Redis cache adapter

**Files:**
- Modify: `backend/app/utils/cache.py`
- Modify: `backend/app/utils/__init__.py`
- Modify: `backend/app/core/config.py`
- Modify: `backend/.env.example`
- Create: `backend/tests/test_cache.py`

**Interfaces:**
- Produces: `get_redis() -> Optional[redis.Redis]`
- Produces: `generate_cache_key(namespace: str, **parameters: JSONScalar) -> str`
- Produces: `cache_get(key: str) -> Optional[Any]`
- Produces: `cache_set(key: str, value: Any, ttl: Optional[int] = None) -> bool`
- Produces: `cache_delete(key: str) -> bool`
- Produces: `cache_delete_pattern(pattern: str, batch_size: int = 100) -> bool`
- Produces: `_reset_cache_state() -> None` for deterministic tests and settings reloads.

- [ ] **Step 1: Add validated cache resilience settings**

In `Settings`, replace the unvalidated Redis cache fields with:

```python
REDIS_CACHE_ENABLED: bool = True
REDIS_CACHE_DEFAULT_TTL: int = Field(default=300, ge=1, le=86400)
REDIS_CACHE_CONNECT_TIMEOUT_SECONDS: float = Field(default=0.25, gt=0, le=5)
REDIS_CACHE_SOCKET_TIMEOUT_SECONDS: float = Field(default=0.5, gt=0, le=10)
REDIS_CACHE_RETRY_SECONDS: float = Field(default=5.0, ge=0.1, le=300)
```

Add the same three new keys with those defaults beneath the existing Redis variables in `backend/.env.example`.

- [ ] **Step 2: Replace the cache module with a bounded, explicit adapter**

Use `logging.getLogger(__name__)`, `threading.Lock`, and `time.monotonic`. Catch `(RedisError, OSError, ConnectionError)` for Redis commands. Build the client with `decode_responses=True`, the configured short timeouts, `health_check_interval=30`, and `retry_on_timeout=False`.

Maintain `_redis_client`, `_redis_retry_at`, and `_redis_lock`. When construction, ping, or a command fails, close the client if present, set it to `None`, and set `_redis_retry_at = monotonic() + REDIS_CACHE_RETRY_SECONDS`. During cooldown, `get_redis()` returns `None` without a network attempt. Log only the exception class and operation name, never the URL.

Generate compact stable keys from canonical JSON:

```python
def generate_cache_key(namespace: str, **parameters: JSONScalar) -> str:
    payload = json.dumps(parameters, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:20]
    return f"ctg:v1:{namespace}:{digest}"
```

Serialize with `json.dumps(..., ensure_ascii=False, separators=(",", ":"))` and no `default=str`. Reject non-positive TTLs. On invalid cached JSON, delete the bad key and return `None`. Delete patterns by collecting at most `batch_size` keys from `scan_iter(match=pattern, count=batch_size)`, deleting each batch, then deleting the remainder.

Remove the unused `cached` decorator and its export. It currently generates keys from sessions/users and detects coroutine functions incorrectly; explicit endpoint caching replaces it.

- [ ] **Step 3: Add post-implementation adapter tests**

Create fake Redis clients that record `get`, `setex`, `delete`, `scan_iter`, `ping`, and `close`. Cover:

```python
def test_cache_key_is_stable_across_parameter_order(): ...
def test_cache_set_uses_compact_json_and_default_ttl(monkeypatch): ...
def test_cache_set_rejects_non_json_values(monkeypatch): ...
def test_cache_get_deletes_corrupt_json(monkeypatch): ...
def test_pattern_delete_uses_scan_batches(monkeypatch): ...
def test_connection_failure_enters_cooldown(monkeypatch): ...
def test_disabled_cache_never_constructs_client(monkeypatch): ...
```

The cooldown test calls `get_redis()` twice at the same mocked monotonic time and asserts `redis.Redis.from_url` is called once.

- [ ] **Step 4: Run focused cache verification**

Run: `python3 -m pytest backend/tests/test_cache.py -q`

Expected: all cache tests pass; no live Redis server is required.

- [ ] **Step 5: Commit the adapter**

```bash
git add backend/app/utils/cache.py backend/app/utils/__init__.py backend/app/core/config.py backend/.env.example backend/tests/test_cache.py
git commit -m "fix: make Redis cache resilient"
```

---

### Task 2: Survey query optimization, caching, and invalidation

**Files:**
- Modify: `backend/app/schemas/surveys.py`
- Modify: `backend/app/api/surveys.py`
- Create: `backend/tests/test_surveys_api.py`

**Interfaces:**
- Consumes: cache functions from Task 1.
- Produces: `SurveyDetail.has_submitted: bool`.
- Produces: `_survey_detail(survey: Survey, questions: Sequence[SurveyQuestion], *, has_submitted: bool = False) -> SurveyDetail`.
- Produces: `_invalidate_survey_cache(survey_id: Optional[int] = None) -> None`.

- [ ] **Step 1: Make survey response schemas safe and user-aware**

Import `SurveyQuestionResponse` in the API (it is currently referenced without import). In schemas, use `Field(default_factory=list)` for `SurveyCreate.questions` and `SurveyDetail.questions`; add `has_submitted: bool = False` to `SurveyDetail`.

- [ ] **Step 2: Replace list N+1 queries with aggregate scalar subqueries**

Validate the parameter as `status: Literal["active", "all"] = "active"`. Determine `is_manager` from the role. Non-managers always receive the active/time-window filters even if they request `all`; managers requesting `all` receive all rows.

Use:

```python
question_count = (
    select(func.count(SurveyQuestion.id))
    .where(SurveyQuestion.survey_id == Survey.id)
    .correlate(Survey)
    .scalar_subquery()
)
response_count = (
    select(func.count(SurveyResponse.id))
    .where(SurveyResponse.survey_id == Survey.id)
    .correlate(Survey)
    .scalar_subquery()
)
```

Run one scalar count for pagination and one paginated select returning `Survey`, `question_count`, and `response_count`. Construct `SurveyPageResponse`, cache `model_dump(mode="json")`, and return the model. The cache key is `generate_cache_key("surveys:list", page=page, page_size=page_size, status=effective_status, scope=scope)`.

- [ ] **Step 3: Cache common detail while keeping submission state private**

Always load the `Survey` row and enforce the existing non-active visibility rule first. For active surveys only, read `ctg:v1:surveys:detail:<survey_id>`. On a miss, load questions, build a common detail dictionary, force `has_submitted=False`, and cache it.

Independently calculate submission state with an existence/count query on `(survey_id, current_user.uid)`. Return `SurveyDetail.model_validate({**common_detail, "has_submitted": has_submitted})`. Draft/non-active details bypass shared caching.

- [ ] **Step 4: Invalidate after every successful relevant write**

Define constants:

```python
SURVEY_LIST_CACHE_PATTERN = "ctg:v1:surveys:list:*"

def _survey_detail_cache_key(survey_id: int) -> str:
    return f"ctg:v1:surveys:detail:{survey_id}"
```

After all database commits for create, call `_invalidate_survey_cache(survey.id)` outside the notification-only branch. After update, clear list and detail. After submit, clear list so response counts refresh. Cache deletion failures must not alter the response.

Correct the statistics total count to a scalar count rather than `len(...all())`, which currently reports one row rather than response count.

- [ ] **Step 5: Add post-implementation survey API regression tests**

Build an in-memory SQLite FastAPI test app following `test_soup_collections_api.py`. Override current user and cache functions. Cover:

```python
def test_list_returns_real_question_and_response_counts_without_n_plus_one(): ...
def test_list_cache_key_separates_public_and_manager_views(): ...
def test_non_manager_all_view_does_not_expose_drafts(): ...
def test_detail_cache_does_not_share_has_submitted_between_users(): ...
def test_create_update_and_submit_invalidate_expected_keys(): ...
def test_statistics_returns_actual_response_count(): ...
```

For the N+1 regression, count SQL statements via SQLAlchemy's `before_cursor_execute` event and assert list query count remains constant when a second survey is added.

- [ ] **Step 6: Run survey and cache tests**

Run: `python3 -m pytest backend/tests/test_cache.py backend/tests/test_surveys_api.py -q`

Expected: all pass with SQLite and fake cache clients.

- [ ] **Step 7: Commit survey caching**

```bash
git add backend/app/schemas/surveys.py backend/app/api/surveys.py backend/tests/test_surveys_api.py
git commit -m "perf: cache and aggregate survey reads"
```

---

### Task 3: Glass styles, rounded clipping, route transitions, and profile overlay

**Files:**
- Modify: `frontend/src/assets/main.css`
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/views/ProfileView.vue`

**Interfaces:**
- Produces reusable CSS classes: `.glass-panel`, `.glass-card`, `.glass-card-interactive`, `.glass-button`, `.survey-page`, `.skeleton-block`.

- [ ] **Step 1: Centralize glass tokens and fallbacks**

Add light variables to `:root` and dark overrides to `.dark`:

```css
--glass-panel: rgba(255, 255, 255, .68);
--glass-card: rgba(255, 255, 255, .82);
--glass-button: rgba(255, 255, 255, .72);
--glass-border: rgba(255, 255, 255, .58);
--glass-shadow: 0 18px 45px rgba(15, 23, 42, .10);
--glass-radius-panel: 1rem;
--glass-radius-card: .75rem;
```

Dark values use black/neutral translucent surfaces and lower white border opacity. Base classes use `background-clip: padding-box`, `overflow: hidden` on panels/cards, `isolation: isolate`, and fallback opaque-enough backgrounds. Put `backdrop-filter: blur(...) saturate(130%)` and the prefixed form inside `@supports ((backdrop-filter: blur(1px)) or (-webkit-backdrop-filter: blur(1px)))`.

Do not give every `.glass-card` a hover transform. Move transform/shadow hover rules to `.glass-card-interactive`. Keep `.glass-button` neutral; primary actions use only `.btn-primary`, preventing the unlayered glass background from overriding the blue button.

- [ ] **Step 2: Add perceptible survey backdrop and skeleton styles**

`.survey-page` receives two low-contrast radial gradients over `var(--page)`; dark mode uses deep blue/black gradients. `.skeleton-block` uses a clipped linear-gradient shimmer, matching glass rounding. Under `prefers-reduced-motion: reduce`, disable the shimmer.

- [ ] **Step 3: Prevent blank route transitions**

Remove `mode="out-in"` from the root `<transition>`. Add a keyed component so transitions still run correctly:

```vue
<router-view v-slot="{ Component, route }">
  <transition name="fade">
    <component :is="Component" :key="route.fullPath" />
  </transition>
</router-view>
```

Adjust fade CSS so leaving content is absolutely layered only within the content region if needed, without collapsing the page or causing horizontal overflow.

- [ ] **Step 4: Make the profile overlay explicitly blurred and black in dark mode**

Keep the light gradient, then add blur support and black dark values:

```css
.profile-hero-overlay {
  background: linear-gradient(90deg, rgba(255,255,255,.94), rgba(255,255,255,.74) 58%, rgba(255,255,255,.34));
  backdrop-filter: blur(10px) saturate(110%);
  -webkit-backdrop-filter: blur(10px) saturate(110%);
}

:global(.dark) .profile-hero-overlay {
  background: linear-gradient(90deg, rgba(0,0,0,.94), rgba(0,0,0,.78) 58%, rgba(0,0,0,.42));
}
```

- [ ] **Step 5: Run CSS/type build smoke check**

Run: `npm run build`

Expected: Vue type checking and Vite build succeed without missing Tailwind utilities or CSS parse errors.

- [ ] **Step 6: Commit visual foundations**

```bash
git add frontend/src/assets/main.css frontend/src/App.vue frontend/src/views/ProfileView.vue
git commit -m "fix: restore glass surfaces and dark profile overlay"
```

---

### Task 4: Survey loading experience and submission state

**Files:**
- Modify: `frontend/src/api/surveys.ts`
- Modify: `frontend/src/views/SurveyListView.vue`
- Modify: `frontend/src/views/SurveyDetailView.vue`
- Create: `frontend/tests/e2e/survey-loading-glass.spec.ts`

**Interfaces:**
- Consumes: `SurveyDetail.has_submitted` from Task 2.
- Consumes: glass/skeleton classes from Task 3.
- Produces: retained-content page refresh and layout-stable initial loading.

- [ ] **Step 1: Correct survey TypeScript contracts**

Add `has_submitted?: boolean` to `Survey`. Change list status from `string` to `'active' | 'all'`. In `SurveyListView`, import `Survey` from `@/api/surveys` and use it for the list; remove the invalid `SurveySummary` import from `@/types`.

- [ ] **Step 2: Implement list skeleton and retained refresh**

Replace one `loading` flag with:

```ts
const initialLoading = ref(true)
const refreshing = ref(false)
const loadError = ref('')
let requestId = 0
```

`loadSurveys()` increments `requestId`, uses `initialLoading` only when no items exist, otherwise uses `refreshing`, and ignores stale responses. Do not clear `surveys` before a request. On failure, set `loadError = '问卷加载失败，请稍后重试。'`; preserve current items. Disable pagination while refreshing and set `aria-busy` on the results region.

Initial loading renders six fixed-height glass skeleton cards. Existing results remain visible during pagination with a small spinner beside the page indicator. Add `survey-page` to the root, `glass-card-interactive` only to clickable cards, and remove `glass-button` from `.btn-primary` combinations.

- [ ] **Step 3: Implement detail skeleton and remove the redundant statistics request**

Use `survey.value = res.data` and `alreadySubmitted.value = Boolean(res.data.has_submitted)`. Delete the `getStatistics()` probe that currently turns every normal user's 403 into “already submitted” and adds an avoidable request.

Add `loadError`. On initial load render a stable glass header plus three question skeleton cards. On error with no survey, show the message and a retry button. Set `aria-busy` while loading. Keep submission errors user-readable and do not wipe answers.

- [ ] **Step 4: Add browser regressions with API mocks**

Mock auth, announcements, survey list, and survey detail. Verify:

```ts
test('survey list shows skeletons then glass cards without page errors', async ({ page }) => { ... })
test('survey detail trusts has_submitted without requesting statistics', async ({ page }) => { ... })
test('dark profile overlay uses a black translucent background and blur', async ({ page }) => { ... })
```

For the detail test, record requested paths and assert none ends with `/statistics`. For the profile test, mock `/api/users/<uid>/profile`, enable dark mode through local storage using the existing theme key, then inspect computed `backgroundImage` and `backdropFilter` on `.profile-hero-overlay`.

- [ ] **Step 5: Run frontend verification**

Run: `npm run build`

Run: `npx playwright test tests/e2e/survey-loading-glass.spec.ts tests/e2e/responsive-smoke.spec.ts`

Expected: build passes; tests report no page errors, no horizontal overflow, no statistics request, and correct dark overlay styling.

- [ ] **Step 6: Commit loading UX**

```bash
git add frontend/src/api/surveys.ts frontend/src/views/SurveyListView.vue frontend/src/views/SurveyDetailView.vue frontend/tests/e2e/survey-loading-glass.spec.ts
git commit -m "perf: smooth survey loading states"
```

---

### Task 5: Release version and full verification

**Files:**
- Modify: `VERSION`
- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`

**Interfaces:**
- Produces: all runtime and package metadata report `1.5.0`.

- [ ] **Step 1: Align version metadata**

Set `VERSION` to `1.5.0`. Set the root package version in `frontend/package.json` and both root-package occurrences at the top of `frontend/package-lock.json` to `1.5.0`; do not replace transitive dependency versions equal to `1.2.0`.

- [ ] **Step 2: Install missing local dependencies if required**

If `python3 -m pytest --version` fails, create `.venv` and install `backend/requirements.txt`. If `frontend/node_modules/.bin/vue-tsc` is absent, run `npm ci` in `frontend`. These are local ignored artifacts and must not be committed.

- [ ] **Step 3: Run complete verification**

Run from `backend`: `python3 -m pytest -q`

Run from `frontend`: `npm run build`

Run from `frontend`: `npx playwright test`

Run from repository root: `git diff --check`

Expected: all backend tests pass, frontend builds, Playwright passes, and diff check prints nothing.

- [ ] **Step 4: Inspect release diff and tracked artifacts**

Run:

```bash
git status --short
git diff --stat 7c5793e..HEAD
git diff --name-only 7c5793e..HEAD
```

Confirm no `.env`, `node_modules`, `.venv`, bytecode, credentials, screenshots, traces, or runtime storage files are tracked.

- [ ] **Step 5: Commit the release version**

```bash
git add VERSION frontend/package.json frontend/package-lock.json
git commit -m "chore: release version 1.5.0"
```

- [ ] **Step 6: Re-run final targeted smoke checks after the last commit**

Run: `python3 -m pytest backend/tests/test_cache.py backend/tests/test_surveys_api.py -q`

Run: `npm run build`

Expected: both commands pass against the committed tree.

