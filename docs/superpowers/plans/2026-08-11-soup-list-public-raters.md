# Soup List Public Raters Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let visitors open a paginated public rater list directly from every soup card while keeping the detail page on the same shared behavior.

**Architecture:** Extract the existing detail-page rater dialog into one focused component that owns fetching, pagination, stale-request protection, and presentation. The list and detail views only choose a soup and control the component's `open` prop. Continue using the existing public ratings API without backend contract changes.

**Tech Stack:** Vue 3, TypeScript, Headless UI, Axios, Vite, FastAPI/pytest regression suite.

## Global Constraints

- The rater list is globally public and uses `GET /api/turtle-soups/{id}/ratings?page=<n>&page_size=50`.
- Show nickname, username, individual score, and rating time; do not expose email or other private fields.
- Clicking the list-card entry must not navigate to the soup detail page.
- Loading, error, empty, pagination, close, and switching-soup states must be explicit.
- Keep `VERSION` exactly `1.3.1`.
- Do not use a TDD red-green cycle or browser validation.
- Update a current PR when possible; create a minimal follow-up PR if the current PR has already merged.

---

### Task 1: Extract The Shared Ratings Dialog

**Files:**
- Create: `frontend/src/components/SoupRatingsDialog.vue`
- Modify: `frontend/src/views/SoupDetailView.vue`

**Interfaces:**
- Consumes: `soupApi.listRatings(id, { page, page_size: 50 })`, `SoupRating`, and `formatChinaDateTime()`.
- Produces: `SoupRatingsDialog` props `{ open: boolean; soupId: number | null; soupTitle: string }` and event `{ close: [] }`.

- [ ] **Step 1: Create the component state contract**

Use explicit props/events and local pagination state:

```ts
const props = defineProps<{
  open: boolean
  soupId: number | null
  soupTitle: string
}>()
const emit = defineEmits<{ close: [] }>()
const ratings = ref<SoupRating[]>([])
const loading = ref(false)
const error = ref('')
const page = ref(1)
const total = ref(0)
const totalPages = ref(1)
let requestSerial = 0

function requestClose() {
  emit('close')
}
```

- [ ] **Step 2: Implement guarded loading and reset behavior**

Load 50 entries and only apply the response if the dialog still refers to the same soup/request:

```ts
async function loadRatings(targetPage: number) {
  const soupId = props.soupId
  if (!props.open || soupId == null) return
  const serial = ++requestSerial
  loading.value = true
  error.value = ''
  try {
    const response = (await soupApi.listRatings(soupId, { page: targetPage, page_size: 50 })).data
    if (serial !== requestSerial || soupId !== props.soupId || !props.open) return
    ratings.value = response.items || []
    page.value = response.page
    total.value = response.total
    totalPages.value = response.total_pages ?? 1
  } catch (cause) {
    if (serial !== requestSerial) return
    ratings.value = []
    error.value = extractApiError(cause, '评分列表加载失败')
  } finally {
    if (serial === requestSerial) loading.value = false
  }
}
```

Watch `[open, soupId]`. On a new open/soup ID, clear the previous rows and call `loadRatings(1)`; on close, increment `requestSerial` and reset state so an old response cannot repaint the next dialog:

```ts
watch(
  () => [props.open, props.soupId] as const,
  ([open, soupId]) => {
    requestSerial += 1
    ratings.value = []
    loading.value = false
    error.value = ''
    page.value = 1
    total.value = 0
    totalPages.value = 1
    if (open && soupId != null) void loadRatings(1)
  },
  { immediate: true },
)
```

- [ ] **Step 3: Render the accessible dialog**

Reuse `Dialog`, `DialogPanel`, `DialogTitle`, `TransitionChild`, and `TransitionRoot`. The title is `“<soupTitle>”的评分人`; each row renders:

```vue
<router-link :to="`/profile/${rating.user_uid}`">
  {{ rating.nickname || rating.username }}
</router-link>
<p>@{{ rating.username }} · {{ formatChinaDateTime(rating.created_at) }}</p>
<span>{{ rating.score.toFixed(1) }} 分</span>
```

Provide “加载中…”, “暂无公开评分。”, error text, total/page text, and disabled previous/next buttons. Bind both `Dialog @close` and the visible close button to `requestClose()` so all close paths emit `close`.

- [ ] **Step 4: Replace detail-page duplicate code**

In `SoupDetailView.vue`:

```vue
<SoupRatingsDialog
  :open="ratingsOpen"
  :soup-id="soup.id"
  :soup-title="soup.title"
  @close="ratingsOpen = false"
/>
```

Keep `ratingsOpen` and `openRatings()`, but remove the inline ratings dialog markup, `SoupRating` import, ratings collection/loading/error/page/total state, and `loadRatings()`. Change `openRatings()` to synchronously set `ratingsOpen.value = true`; do not alter rating submission.

- [ ] **Step 5: Run a TypeScript production build**

Run:

```bash
npm --prefix frontend ci --no-audit --no-fund
npm --prefix frontend run build
```

Expected: Vue type checking and Vite complete with exit code zero.

- [ ] **Step 6: Commit the shared component extraction**

```bash
git add frontend/src/components/SoupRatingsDialog.vue frontend/src/views/SoupDetailView.vue
git commit -m "refactor: share public soup ratings dialog"
```

---

### Task 2: Add The List-Card Entry Point

**Files:**
- Modify: `frontend/src/views/soup/SoupListView.vue`

**Interfaces:**
- Consumes: `SoupRatingsDialog`, `TurtleSoup.id`, `TurtleSoup.title`, and `TurtleSoup.rating_count`.
- Produces: one selected soup state and an event-safe “查看评分人” control on every card.

- [ ] **Step 1: Add the selected-soup state and helpers**

```ts
const selectedRatingsSoup = ref<TurtleSoup | null>(null)

function openRatings(soup: TurtleSoup) {
  selectedRatingsSoup.value = soup
}

function closeRatings() {
  selectedRatingsSoup.value = null
}
```

Import `SoupRatingsDialog`, `TurtleSoup`, and `UserGroupIcon`.

- [ ] **Step 2: Add the card control without navigation**

Next to the average-score statistic, render:

```vue
<button
  class="inline-flex items-center font-medium text-blue-600 hover:text-blue-700"
  type="button"
  @click.stop="openRatings(soup)"
>
  <UserGroupIcon class="mr-1 h-4 w-4" aria-hidden="true" />
  {{ soup.rating_count }} 人评分 · 查看评分人
</button>
```

The `@click.stop` is mandatory because the parent card navigates on click.

- [ ] **Step 3: Mount one dialog outside the card loop**

At the end of the page container, render:

```vue
<SoupRatingsDialog
  :open="selectedRatingsSoup !== null"
  :soup-id="selectedRatingsSoup?.id ?? null"
  :soup-title="selectedRatingsSoup?.title ?? ''"
  @close="closeRatings"
/>
```

- [ ] **Step 4: Rebuild the frontend**

Run `npm --prefix frontend run build`.

Expected: exit code zero with no Vue or TypeScript errors.

- [ ] **Step 5: Commit the list entry point**

```bash
git add frontend/src/views/soup/SoupListView.vue
git commit -m "feat: show public raters on soup list"
```

---

### Task 3: Verify, Publish, And Deploy

**Files:**
- Modify only files required by verification failures.

**Interfaces:**
- Consumes: the completed branch, repository PAT outside version control, and remote Screen deployment.
- Produces: an updated/open GitHub PR and a remote deployment that retains version `1.3.1`.

- [ ] **Step 1: Verify the existing public API contract**

Run:

```bash
PYTHONPATH=backend /tmp/ctg-verify.xA2dJy/bin/python -m pytest -q backend/tests/test_soup_comments_api.py
```

Expected: the public ratings endpoint tests pass.

- [ ] **Step 2: Run full verification**

Run:

```bash
PYTHONPATH=backend /tmp/ctg-verify.xA2dJy/bin/python -m pytest -q backend/tests
/tmp/ctg-verify.xA2dJy/bin/python -m compileall -q backend/app
bash -n Update.sh dev.sh setup.sh
git diff --check
test "$(cat VERSION)" = "1.3.1"
```

Expected: 0 failures and every command exits zero.

- [ ] **Step 3: Audit the branch**

Confirm committed and untracked paths contain no PAT, `.env`, runtime storage, dependency, build, cache, archive, or temporary files. Confirm the implementation commits from Tasks 1 and 2 are present and the worktree is clean.

```bash
git status --short
git log -2 --oneline
```

- [ ] **Step 4: Push and update/create the PR**

Push `codex/ota-ratings-session-competition-v2` normally without force. If its open PR still exists, its head updates automatically; if it has merged, create a follow-up PR against `main` containing only commits not already merged.

- [ ] **Step 5: Deploy without database writes**

Create a remote `git archive` backup, pull the branch with `--ff-only`, and run `app.migrations.social_platform --dry-run --phase all`. Apply no migration when `actions` is empty. Restart `/usr/local/sbin/ctg-screen-restart`.

- [ ] **Step 6: Verify the remote runtime without a browser**

Poll `/health` and `/api/version` until both report `1.3.1`. Fetch `/api/turtle-soups?page=1&page_size=1`, use its first soup ID to call the public `/api/turtle-soups/{id}/ratings`, and require HTTP 200. Fetch `/soups` from the Vite server and require HTTP 200. Confirm the remote Git HEAD matches the PR branch.
