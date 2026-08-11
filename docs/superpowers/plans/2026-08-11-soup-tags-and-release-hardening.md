# Soup Tags And Release Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete compact/full soup-tag display, repair the rating-count regression, harden session restoration and OTA execution, then publish the combined feature branch as a GitHub pull request.

**Architecture:** Reuse the complete `soup.tags` array already returned by the API and apply presentation-only truncation in the list view. Keep authentication restoration in the Pinia store and make the router await its one-time initialization. Keep OTA execution rooted in `Update.sh`, but make private files explicit, migrate only after dependency/build preparation, and restore the previous code/dependency/build state on failure while retaining the database backup for controlled recovery.

**Tech Stack:** Vue 3, Pinia, Vue Router, TypeScript, FastAPI, SQLModel/SQLAlchemy, Bash, pytest, Vite.

## Global Constraints

- List cards display at most the first 3 tags and show an ellipsis when more exist.
- Soup detail displays every selected system and custom tag without truncation.
- Empty tag arrays render no tag region.
- Do not perform browser verification or a real OTA/database operation.
- Do not use a TDD red-green cycle; add or update focused tests where practical, then run the full verification suite after implementation.
- Never stage or expose `GithubPAT.txt`, environment files, runtime storage, caches, archives, or dependency directories.

---

### Task 1: Repair Rating Pagination Regression

**Files:**
- Modify: `backend/app/api/turtle_soups.py`
- Test: `backend/tests/test_soup_comments_api.py`

**Interfaces:**
- Consumes: `Rating.soup_id`, `func.count`, and the existing paginated `GET /api/turtle-soups/{soup_id}/ratings` contract.
- Produces: Correct list-page totals and efficient rating totals without loading all rating rows.

- [ ] **Step 1: Restore the soup-list total query**

Keep `list_soups()` scoped to its filtered soup query:

```python
total = len(db.exec(query).all())
```

- [ ] **Step 2: Count ratings in the rating endpoint**

Inside `list_soup_ratings()` use:

```python
total = db.exec(
    select(func.count(Rating.id)).where(Rating.soup_id == soup_id)
).one()
```

- [ ] **Step 3: Run focused API tests**

Run `PYTHONPATH=backend /tmp/ctg-verify.xA2dJy/bin/python -m pytest -q backend/tests/test_soup_comments_api.py backend/tests/test_soup_metadata_api.py`.

Expected: all selected tests pass.

### Task 2: Render Compact And Complete Soup Tags

**Files:**
- Modify: `frontend/src/views/soup/SoupListView.vue`
- Modify: `frontend/src/views/SoupDetailView.vue`

**Interfaces:**
- Consumes: `TurtleSoup.tags: Tag[]` from the existing API response.
- Produces: A compact first-three tag row on cards and a complete wrapping tag row on detail pages.

- [ ] **Step 1: Add the list ellipsis**

After the existing `soup.tags.slice(0, 3)` loop, render only when tags remain:

```vue
<span
  v-if="soup.tags.length > 3"
  class="inline-flex h-6 min-w-6 items-center justify-center rounded-full bg-slate-100 px-2 text-xs text-slate-500 dark:bg-neutral-800 dark:text-slate-400"
  :title="`还有 ${soup.tags.length - 3} 个标签`"
  :aria-label="`还有 ${soup.tags.length - 3} 个标签`"
>…</span>
```

- [ ] **Step 2: Add all tags to detail**

Below the genre and soup-color badges, render the entire array without slicing:

```vue
<div v-if="soup.tags.length" class="mt-3 flex flex-wrap gap-2" aria-label="标签">
  <span
    v-for="tag in soup.tags"
    :key="tag.id"
    class="max-w-full break-all rounded-full bg-blue-100 px-2 py-1 text-xs text-blue-600 dark:bg-blue-900/30 dark:text-blue-400"
  >#{{ tag.name }}</span>
</div>
```

- [ ] **Step 3: Build the frontend**

Run `npm --prefix frontend run build`.

Expected: `vue-tsc` and Vite complete successfully.

### Task 3: Harden Session Restoration And OTA Files

**Files:**
- Modify: `frontend/src/stores/auth.ts`
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/src/App.vue`
- Modify: `dev.sh`
- Modify: `Update.sh`
- Modify: `backend/app/services/ota.py`
- Test: `backend/tests/test_ota.py`

**Interfaces:**
- Consumes: `authApi.refreshToken()`, `authApi.getCurrentUser()`, router metadata, `CTG_UPDATE_STATE_FILE`, `CTG_UPDATE_LOG_PATH`, and the existing OTA task state contract.
- Produces: `init(): Promise<void>` that is safe to await repeatedly, private configuration/log/state files, and a rollback path that restores old code/dependencies/build assets.

- [ ] **Step 1: Make auth initialization idempotent**

Add a module-local promise and route all calls through it:

```ts
let initPromise: Promise<void> | null = null

function init(): Promise<void> {
  if (!initPromise) initPromise = restoreSession()
  return initPromise
}
```

`restoreSession()` refreshes when only a refresh token exists, then fetches the current user when an access token exists.

- [ ] **Step 2: Await initialization in the router**

Import `useAuthStore`, make `beforeEach` async, await `auth.init()`, and use the refreshed access token/role before applying `requiresAuth`, `guestOnly`, admin, and root checks. Remove the redundant fire-and-forget call from `App.vue`.

- [ ] **Step 3: Protect generated configuration**

In `dev.sh`, create `backend/.env` and immediately apply `chmod 600 "$BACKEND_DIR/.env"`. Do not print configurable package-index URLs in logs.

- [ ] **Step 4: Protect OTA state and log files**

In `ota.py`, create update-log directories with mode `0700` and apply mode `0600` to JSON state and log files after creation. Keep invalid task IDs rejected before path construction.

- [ ] **Step 5: Make rollback restore executable assets**

In `Update.sh`, run dependency installation and frontend build before migration. Require a restart command and a matching health check before clearing maintenance. On failure before migration completes, restore the previous branch/commit, reinstall the previous pinned dependencies, and rebuild the previous frontend. Keep the timestamped database backup and print its location; do not automatically overwrite a production database. Signals retain maintenance and route through the same rollback path.

- [ ] **Step 6: Verify scripts and OTA tests**

Run `bash -n Update.sh dev.sh setup.sh` and `PYTHONPATH=backend /tmp/ctg-verify.xA2dJy/bin/python -m pytest -q backend/tests/test_ota.py`.

Expected: shell parsing and OTA tests pass.

### Task 4: Final Verification And Pull Request

**Files:**
- Modify: only files required by failures found during verification.

**Interfaces:**
- Consumes: the complete feature branch and repository PAT stored outside version control.
- Produces: a pushed branch and GitHub pull request targeting `main`.

- [ ] **Step 1: Run full verification**

Run:

```bash
PYTHONPATH=backend /tmp/ctg-verify.xA2dJy/bin/python -m pytest -q backend/tests
npm --prefix frontend run build
/tmp/ctg-verify.xA2dJy/bin/python -m compileall -q backend/app
bash -n Update.sh dev.sh setup.sh
git diff --check
```

Expected: all commands exit zero.

- [ ] **Step 2: Audit the staged file set**

Run `git status --short`, `git diff --cached --name-only`, and secret-pattern scans. Confirm no PAT, `.env`, runtime, build, cache, dependency, archive, or temporary paths are staged.

- [ ] **Step 3: Commit implementation**

Use `git commit -m "feat: add OTA updates and public rating details"`.

- [ ] **Step 4: Push and create the PR**

Push `codex/ota-ratings-session-competition`, then call the GitHub API to create a pull request with base `main`. Authentication must be supplied without printing or persisting the PAT.
