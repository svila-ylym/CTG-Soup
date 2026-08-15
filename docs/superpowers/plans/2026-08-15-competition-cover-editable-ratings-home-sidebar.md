# Competition Cover, Editable Ratings, Home, and Sidebar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship version 1.5.0 with competition cover uploads, editable soup ratings, a compact scenery Banner plus latest-competition/random-soup homepage, and the supplied animated theme switch integrated into the optimized sidebar.

**Architecture:** Reuse authenticated public image uploads and store the validated optional cover reference inside the existing competition page configuration while exposing first-class API fields. Change the rating `PUT` endpoint into a row-locked upsert that recalculates aggregates. Serve homepage discovery through one public, short-cached endpoint, and encapsulate the supplied theme markup/CSS in a Vue component backed by the existing theme state.

**Tech Stack:** FastAPI, SQLModel/SQLAlchemy, Pydantic 2, optional Redis JSON cache, Vue 3 Composition API, TypeScript, Tailwind CSS 4, pytest, Playwright.

## Global Constraints

- Release version remains exactly `1.5.0`.
- Follow the user's instruction not to use TDD: implement first, then add and run focused regression tests.
- Do not add a backend or frontend dependency.
- Do not create a database column or migration for the optional competition cover.
- Every referenced cover/body image must be an existing `UploadedAsset` owned by the competition creator.
- Redis remains optional; homepage cache failures fall back to the database.
- Keep the existing `theme_preference`/system-theme data flow and `html.dark` contract.
- Do not copy the supplied universal reset or `body` layout rules into the application.
- Do not dispatch subagents; execute inline in the existing `feat/redis-cache-glass-1.5.0` worktree.

---

## File Map

- `backend/app/schemas/competitions.py`: cover request/response fields.
- `backend/app/api/competitions.py`: cover ownership validation, controlled config storage, response export.
- `backend/app/api/turtle_soups.py`: rating upsert and aggregate refresh.
- `backend/app/api/home.py`: lightweight discovery schemas, query, Redis/HTTP cache behavior.
- `backend/tests/test_competition_contract.py`: cover contract regressions.
- `backend/tests/test_soup_metadata_api.py`: editable rating aggregation regression using the existing API fixture.
- `backend/tests/test_home_api.py`: homepage discovery/cache regressions.
- `frontend/src/types/index.ts`: competition cover and homepage discovery contracts.
- `frontend/src/api/home.ts`: one typed discovery request.
- `frontend/src/components/CompetitionCoverPicker.vue`: single cover upload/preview/remove component.
- `frontend/src/components/ThemeToggle.vue`: supplied switch markup, SVG, behavior and scoped CSS.
- `frontend/src/views/CompetitionCreateView.vue`: cover selection and request.
- `frontend/src/views/CompetitionEditView.vue`: restore, replace, preserve and remove cover.
- `frontend/src/views/CompetitionListView.vue`: cover thumbnails and stable fallbacks.
- `frontend/src/views/CompetitionDetailView.vue`: cover hero.
- `frontend/src/views/SoupDetailView.vue`: editable slider and confirmation language.
- `frontend/src/views/HomeView.vue`: compact Banner and Bilibili-like discovery grid.
- `frontend/src/components/NavBar.vue`: animated toggle integration and drawer interaction/layout.
- `frontend/index.html`: early, preference-compatible dark-class bootstrap.
- `frontend/tests/e2e/rating-lock.spec.ts`: replace immutable-rating expectations with update behavior.
- `frontend/tests/e2e/home-sidebar-discovery.spec.ts`: Banner, discovery and sidebar theme regressions.

---

### Task 1: Competition cover API contract and validation

**Files:**
- Modify: `backend/app/schemas/competitions.py`
- Modify: `backend/app/api/competitions.py`

**Interfaces:**
- Produces request field: `cover_asset_id: int | None` on create/update.
- Produces response fields: `cover_asset_id: int | None`, `cover_url: str | None`.
- Produces helpers: `_config_optional_int(config, key)`, `_config_optional_str(config, key)` for defensive response extraction.
- Changes `_competition_content(...) -> tuple[str, dict]` to validate and write cover config.

- [ ] **Step 1: Add explicit schema fields**

Add `cover_asset_id: int | None = Field(default=None, gt=0)` to `CompetitionCreate`. Add nullable `cover_asset_id` and `cover_url` to `CompetitionResponse`. Keep `CompetitionUpdate` inheriting the create schema so `model_fields_set` can distinguish omitted from explicit `null`.

- [ ] **Step 2: Export controlled cover values from `_payload`**

Read only integer `custom_page_config["cover_asset_id"]` and non-empty string `custom_page_config["cover_url"]`; return `None` for malformed legacy values. Include the two fields next to `competition_color` in every list/detail/create/update response.

- [ ] **Step 3: Validate and persist the cover alongside rich content**

Inside `_competition_content`, resolve `data.cover_asset_id` with:

```python
cover = db.exec(select(UploadedAsset).where(
    UploadedAsset.id == data.cover_asset_id,
    UploadedAsset.owner_uid == owner_uid,
    UploadedAsset.kind == "image",
)).first()
```

Raise `403` with “比赛封面必须使用本人上传的图片” when not found. Always remove client-provided `cover_asset_id`/`cover_url` from the copied config, then add the verified values when a cover exists. Continue validating all rich-text `<img>` sources against owned body asset URLs.

- [ ] **Step 4: Preserve an omitted cover on update**

Before content validation, if `cover_asset_id` is not in `data.model_fields_set`, copy the current controlled ID into `resolved_data`. Pass `resolved_data`, not the unmodified request, to `_competition_content`. Explicit `cover_asset_id: null` removes both stored cover keys.

- [ ] **Step 5: Review create/update behavior manually**

Confirm create saves a verified cover, update replacement changes both ID and URL, omitted update preserves, explicit null removes, and arbitrary `custom_page_config.cover_url` is overwritten.

---

### Task 2: Competition cover form and display

**Files:**
- Modify: `frontend/src/types/index.ts`
- Create: `frontend/src/components/CompetitionCoverPicker.vue`
- Modify: `frontend/src/views/CompetitionCreateView.vue`
- Modify: `frontend/src/views/CompetitionEditView.vue`
- Modify: `frontend/src/views/CompetitionListView.vue`
- Modify: `frontend/src/views/CompetitionDetailView.vue`

**Interfaces:**
- `CompetitionCoverPicker` models `assetId: number | null` and `url: string | null`.
- `Competition.cover_asset_id`, `Competition.cover_url` are nullable.
- `CompetitionCreate.cover_asset_id` is nullable.

- [ ] **Step 1: Extend TypeScript competition contracts**

Add the nullable fields to `Competition` and `CompetitionCreate`; inherited `CompetitionUpdate` updates automatically.

- [ ] **Step 2: Build the single-cover picker**

Use `uploadApi.image(file)` with a hidden image input. On success emit both the returned asset ID and URL. Render a fixed `aspect-[16/7]` preview with `object-cover`, upload/replace button, remove button, busy state and `extractApiError` feedback. Never clear the current model before a replacement upload succeeds.

- [ ] **Step 3: Connect create and edit forms**

Add `cover_asset_id`/`cover_url` form state, place the picker before the rich-text description, and send `cover_asset_id`. On edit, initialize from the first-class response fields and preserve unrelated `custom_page_config` values.

- [ ] **Step 4: Display covers without layout shifts**

Competition list cards get a fixed aspect cover area above their content. Competition detail gets a wide cover hero before metadata. Use lazy image loading outside the first homepage hero and an accessible alt based on competition name. If `cover_url` is null, render a gradient using `competition_color` rather than an empty `<img>`.

- [ ] **Step 5: Run a frontend build checkpoint**

Run: `npm run build` in `frontend`.

Expected: Vue type checking and Vite build succeed with no invalid model bindings.

---

### Task 3: Editable soup ratings

**Files:**
- Modify: `backend/app/api/turtle_soups.py`
- Modify: `frontend/src/views/SoupDetailView.vue`

**Interfaces:**
- `PUT /api/turtle-soups/{soup_id}/rating` creates or updates one rating.
- Response remains `{ average_score, rating_count, my_rating }`.

- [ ] **Step 1: Replace permanent conflict with a row-locked upsert**

Remove `_rating_already_submitted`. After locking/loading the soup and rejecting self-rating, select the current user's rating. If found, assign `score` and `updated_at=datetime.utcnow()`. Otherwise insert within the existing nested transaction. If the insert hits the unique constraint, re-read the row after the savepoint and update it; re-raise only if it still does not exist.

- [ ] **Step 2: Keep derived data transactionally consistent**

Call `_refresh_soup_rating(db, soup)` and `refresh_soup_competition_scores(db, soup)` after either create or update, then commit and refresh the soup. Keep the all-public-soups achievement check idempotent.

- [ ] **Step 3: Make the slider editable after first save**

Replace `ratingLocked` with `hasRating` and `ratingChanged`. Disable the slider only while submitting. Always show the action; label it “确认评分” for a first score and “修改评分” for an existing score. Disable an unchanged update.

- [ ] **Step 4: Update confirmation and failure behavior**

First submission copy says the score can be changed later. Modification copy shows old and new scores. Remove the special 409 reload/lock path; on any failure preserve the selected value and show the server message. On success update the three returned fields in local soup state.

---

### Task 4: Compact cached homepage discovery API

**Files:**
- Modify: `backend/app/api/home.py`
- Create: `frontend/src/api/home.ts`
- Modify: `frontend/src/types/index.ts`

**Interfaces:**
- Produces `GET /api/home/discovery`.
- Produces `HomeDiscovery`, `HomeCompetitionSummary`, `HomeSoupSummary` in TypeScript.
- Cache key: `generate_cache_key("home:discovery", schema=1)` with 60-second TTL.

- [ ] **Step 1: Define public response models**

In `home.py`, define focused Pydantic models for lines, a nullable latest competition, and a list of random soups. Dates serialize in ISO format. Soup summaries include ID, title, puzzle excerpt, genre, soup color, score/count, author name, competition colors and creation time. Competition summary includes cover fields, color, status, description excerpt, times, scoring mode, top N, required tag names and entry count.

- [ ] **Step 2: Query latest competition and random public soups efficiently**

Load the latest competition by `created_at DESC, id DESC`, derive its current status without mutating the row, count entries with `COUNT`, and resolve required tag names in one query. Load at most four soups joined to authors from statuses `published` and `revealed`, ordered randomly, then resolve competition border colors in one batch.

- [ ] **Step 3: Add safe Redis and HTTP caching**

Read/validate cached JSON first. On miss, build a `HomeDiscoveryResponse`, cache `model_dump(mode="json")` for 60 seconds, and return it. Set `Cache-Control: public, max-age=30, stale-while-revalidate=120`. Invalid cache values are treated as misses without exposing exceptions.

- [ ] **Step 4: Add the frontend client**

Create `homeApi.discovery()` using the shared Axios instance. Keep the response free of current-user state so the public cache is safe.

---

### Task 5: Homepage Banner and Bilibili-like discovery layout

**Files:**
- Replace: `frontend/src/views/HomeView.vue`

**Interfaces:**
- Consumes `homeApi.discovery()` and the home discovery types.
- Keeps the existing time-period scenery state and pointer parallax locally.

- [ ] **Step 1: Reduce the scenery section to a Banner**

Keep the SVG landscape and time-based color classes, but cap the section at roughly `15rem` mobile and `20rem` desktop. Remove the puzzle-note stage, external hitokoto request, feature-card section and large leaderboard section. Keep a compact title, current local home line and two primary navigation actions over the scenery.

- [ ] **Step 2: Implement the discovery grid**

Under the Banner render a desktop `grid-cols-[minmax(0,7fr)_minmax(20rem,5fr)]`. The left large card displays the latest competition cover/fallback plus partial details. The right section displays four random soup cards with title, excerpt, metadata, score and author. Stack sections on narrow screens and prevent horizontal overflow.

- [ ] **Step 3: Optimize request and loading states**

Use one `loadDiscovery()` request on mount. Render layout-matched skeletons during first load. On error show a compact retry state. Use `loading="eager" fetchpriority="high"` for the visible latest competition cover and `loading="lazy"` for recommendation imagery if later added. Keep local fallback lines if the endpoint fails.

- [ ] **Step 4: Preserve accessible/reduced animation behavior**

Keep headings in semantic order, use links for navigation cards, mark scenery SVG decorative, and disable continuous/parallax animations under `prefers-reduced-motion`.

---

### Task 6: Animated theme toggle and optimized sidebar

**Files:**
- Create: `frontend/src/components/ThemeToggle.vue`
- Modify: `frontend/src/components/NavBar.vue`
- Modify: `frontend/index.html`

**Interfaces:**
- `ThemeToggle` props: `id: string`, `isDark: boolean`; emits `toggle`.
- Navigation continues to listen for `themechange` and call `applyTheme('light' | 'dark')`.

- [ ] **Step 1: Encapsulate the supplied markup and SVG**

Use the supplied button/container/clouds/stars SVG/sun/moon/crater hierarchy. Bind `id`, `aria-checked`, `aria-label` and `type="button"`. On click add `html.is-animating` and emit; remove the class when the container's `background-color` transition ends or on unmount.

- [ ] **Step 2: Port and scope the supplied CSS safely**

Copy the component-specific color, shadow, cloud, star, moon and hover rules. Fix `height: 1.25em;`, use an approximately `12px` base font size so the control fits navigation, and use `:global(html.dark)` selectors. Add focus-visible and reduced-motion rules. Omit all global reset, tutorial-link and body rules.

- [ ] **Step 3: Replace old navigation theme buttons**

Use `ThemeToggle id="theme-toggle-btn"` in desktop navigation and `ThemeToggle id="theme-toggle-sidebar"` inside a dedicated mobile “外观” card. Remove `MoonIcon`/`SunIcon` imports and the old mobile text theme button.

- [ ] **Step 4: Improve sidebar layout and focus behavior**

Use a rounded glass drawer panel with clearer header/account/appearance/navigation sections and stronger active states. Add refs to the menu trigger and close button; focus close after opening and restore trigger after closing. Keep Escape, backdrop, route-change close, safe-area padding and body scroll restoration.

- [ ] **Step 5: Apply theme before Vue renders**

In `index.html` head, add a guarded inline script that reads `theme_preference`. Add `dark` for an explicit dark preference or a system preference matching `prefers-color-scheme: dark`; do not write storage or duplicate later theme events.

---

### Task 7: Post-implementation regressions and complete verification

**Files:**
- Modify: `backend/tests/test_competition_contract.py`
- Modify: `backend/tests/test_soup_metadata_api.py`
- Create: `backend/tests/test_home_api.py`
- Modify: `frontend/tests/e2e/rating-lock.spec.ts`
- Create: `frontend/tests/e2e/home-sidebar-discovery.spec.ts`

**Interfaces:**
- Tests exercise public API behavior and user-visible interactions, not implementation details.

- [ ] **Step 1: Add competition cover backend regressions**

Extend the competition fixture with owned and foreign `UploadedAsset` rows. Verify create returns the controlled cover URL, foreign cover is rejected, omitted update preserves, explicit null removes, and spoofed config URL cannot escape the owned URL.

- [ ] **Step 2: Add editable rating backend regression**

Submit a first score, submit a different score for the same user, assert one `Rating` row remains, `updated_at` advances, response `rating_count` stays one, and the average/competition score becomes the replacement score.

- [ ] **Step 3: Add homepage API regressions**

With SQLite fixtures, assert the response chooses the newest competition, emits controlled cover fields, returns only public soups, caps recommendations at four, and falls back to the database when cache functions return misses/failures. Verify cached response validation and cache-control header.

- [ ] **Step 4: Rewrite rating browser expectations**

Verify first submission leaves the slider enabled, changing 8.5 to 7 sends a second `PUT`, the count stays one, and historical ratings render as editable. Remove immutable-lock conflict assertions.

- [ ] **Step 5: Add homepage/sidebar browser regressions**

Mock `/api/home/discovery` and announcements. Assert the scenery section is a bounded Banner, latest competition and random recommendations are visible, no old leaderboard/external one-liner request is made, the mobile sidebar contains the supplied theme switch, and clicking it updates `aria-checked` plus `html.dark` without page errors or overflow.

- [ ] **Step 6: Run focused verification**

Run from repository root:

```bash
python3 -m pytest backend/tests/test_competition_contract.py backend/tests/test_soup_metadata_api.py backend/tests/test_home_api.py -q
```

Run from `frontend`:

```bash
npm run build
npx playwright test tests/e2e/rating-lock.spec.ts tests/e2e/home-sidebar-discovery.spec.ts tests/e2e/responsive-smoke.spec.ts
```

- [ ] **Step 7: Run full backend regression**

Run: `python3 -m pytest backend/tests -q`

Expected: the pre-existing backend suite plus new tests pass. Any failure is investigated with systematic debugging before a code change.

- [ ] **Step 8: Review and commit**

Inspect `git diff --check`, `git status --short`, verify `VERSION` and frontend package metadata remain `1.5.0`, then commit focused implementation groups followed by a final verification/docs commit. Do not merge into `main` without a new user request.
