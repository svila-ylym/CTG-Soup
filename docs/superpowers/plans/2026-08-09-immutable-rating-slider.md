# Immutable Rating Slider Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace immediate numeric rating updates with a confirmed slider and make every existing or new rating permanently immutable.

**Architecture:** Keep the current rating URL for compatibility, but make it create-only and return a structured 409 for existing or concurrently inserted ratings. Drive the Vue locked state from `my_rating`, and require a Headless UI confirmation dialog before submission.

**Tech Stack:** FastAPI, SQLModel, Pytest, Vue 3, TypeScript, Headless UI, Tailwind CSS, Playwright

## Global Constraints

- Scores remain 1 through 10 in increments of 0.5.
- Unrated drafts start at 5.0; moving the slider sends no request.
- Existing ratings are immediately locked without a migration.
- Confirmed ratings cannot be updated through the UI or direct API calls.
- Preserve unrelated worktree changes in shared files.

---

### Task 1: Enforce Immutable Ratings in the API

**Files:**
- Modify: `backend/tests/test_soup_comments_api.py`
- Modify: `backend/app/api/turtle_soups.py`

**Interfaces:**
- Consumes: `Rating`, `Soup`, `uq_ratings_user_soup`, and `RatingInput`.
- Produces: create-only `rate_soup(...)` and structured `409 RATING_ALREADY_SUBMITTED` responses.

- [ ] **Step 1: Write the failing lock test**

Keep repeated like/favorite coverage separate and add:

```python
def test_confirmed_rating_cannot_be_changed():
    client, engine, soup_id, users, _current = _test_app()
    first = client.put(f"/api/turtle-soups/{soup_id}/rating", json={"score": 8})
    repeated = client.put(f"/api/turtle-soups/{soup_id}/rating", json={"score": 9})
    assert first.status_code == 200
    assert repeated.status_code == 409
    assert repeated.json()["detail"] == {
        "code": "RATING_ALREADY_SUBMITTED",
        "message": "评分确认后不可修改",
    }
    with Session(engine) as session:
        rating = session.exec(select(Rating).where(
            Rating.user_uid == users[1].uid,
            Rating.soup_id == soup_id,
        )).one()
        soup = session.get(Soup, soup_id)
        assert rating.score == 8
        assert (soup.rating_count, soup.avg_rating) == (1, 8)
```

- [ ] **Step 2: Run the test to verify RED**

Run: `cd backend && pytest tests/test_soup_comments_api.py::test_confirmed_rating_cannot_be_changed -v`

Expected: FAIL because the second request currently returns 200 and stores 9.

- [ ] **Step 3: Implement the create-only endpoint**

Add:

```python
def _rating_already_submitted() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "code": "RATING_ALREADY_SUBMITTED",
            "message": "评分确认后不可修改",
        },
    )
```

In `rate_soup`, raise this error when the initial query finds a rating. In the `IntegrityError` branch, raise the same error after the nested transaction rollback. Delete all assignments to an existing rating. Refresh aggregates and commit only after a new row flushes successfully.

- [ ] **Step 4: Run focused tests to verify GREEN**

Run: `cd backend && pytest tests/test_soup_comments_api.py -v`

Expected: all tests pass; likes/favorites remain idempotent and ratings are immutable.

- [ ] **Step 5: Inspect the endpoint diff**

Run: `git diff -- backend/app/api/turtle_soups.py backend/tests/test_soup_comments_api.py`

Expected: no changes to comments, mentions, reveals, likes, or favorites.

### Task 2: Add the Confirmed Slider Experience

**Files:**
- Create: `frontend/tests/e2e/rating-lock.spec.ts`
- Modify: `frontend/src/views/SoupDetailView.vue`

**Interfaces:**
- Consumes: `TurtleSoup.my_rating`, `soupApi.rate(id, score)`, and `RATING_ALREADY_SUBMITTED`.
- Produces: an accessible range input, confirmation dialog, submission state, and locked status.

- [ ] **Step 1: Write failing Playwright tests**

Mock soup detail, comment list, and rating routes. For `my_rating: null`, assert:

```typescript
const slider = page.getByRole('slider', { name: '评分' })
await expect(slider).toHaveAttribute('min', '1')
await expect(slider).toHaveAttribute('max', '10')
await expect(slider).toHaveAttribute('step', '0.5')
await expect(slider).toHaveValue('5')
await slider.fill('8.5')
expect(ratingRequests).toHaveLength(0)
await page.getByRole('button', { name: '确认评分' }).click()
await expect(page.getByRole('dialog')).toContainText('8.5')
await page.getByRole('button', { name: '取消' }).click()
expect(ratingRequests).toHaveLength(0)
await page.getByRole('button', { name: '确认评分' }).click()
await page.getByRole('button', { name: '确认并提交' }).click()
await expect(slider).toBeDisabled()
await expect(page.getByText('已评分 8.5 分，评分已锁定')).toBeVisible()
```

Add a historical-rating test with `my_rating: 7.5`: slider starts disabled at 7.5 and `确认评分` is absent.

Add a third test for a stale page: the initial detail response has `my_rating: null`, the rating PUT returns `409 RATING_ALREADY_SUBMITTED`, and the next detail response has `my_rating: 6.5`. After confirming a draft of 9, assert that the dialog closes, the slider reloads to 6.5, and the page shows `已评分 6.5 分，评分已锁定`. This test proves the client never treats the rejected draft as authoritative.

- [ ] **Step 2: Run the browser tests to verify RED**

Run: `cd frontend && npx playwright test tests/e2e/rating-lock.spec.ts`

Expected: FAIL because the page still renders an auto-submitting number input.

- [ ] **Step 3: Implement slider draft and lock state**

Use:

```typescript
const score = ref(5)
const ratingDialogOpen = ref(false)
const ratingSubmitting = ref(false)
const ratingError = ref('')
const ratingLocked = computed(() => soup.value?.my_rating != null)
```

After load, set `score.value = soup.value.my_rating ?? 5`. Render `type="range"`, `min="1"`, `max="10"`, `step="0.5"`, `aria-label="评分"`, and `:disabled="ratingLocked || ratingSubmitting"`. Display one decimal place and attach no change submission.

- [ ] **Step 4: Implement confirmation and submission**

Use Headless UI `Dialog`, `DialogPanel`, `DialogTitle`, `TransitionChild`, and `TransitionRoot`. `确认评分` only opens the dialog. `确认并提交` calls `submitRating()`.

On success merge the response into `soup`, copy `my_rating` to `score`, close the dialog, and render the lock message. On HTTP 409 close and call `load()` to obtain the authoritative rating. On other failures keep the dialog open and show `detail.message`, string `detail`, or `评分提交失败`.

- [ ] **Step 5: Run browser tests to verify GREEN**

Run: `cd frontend && npx playwright test tests/e2e/rating-lock.spec.ts`

Expected: new and historical rating tests pass without console errors.

- [ ] **Step 6: Run the frontend build**

Run: `cd frontend && npm run build`

Expected: `vue-tsc -b` and `vite build` exit 0.

### Task 3: Verify Rating Behavior End to End

**Files:**
- Verify only.

**Interfaces:**
- Consumes: API and UI behavior from Tasks 1 and 2.
- Produces: verification evidence for immutable scoring.

- [ ] **Step 1: Run related backend tests**

Run: `cd backend && pytest tests/test_soup_comments_api.py tests/test_soup_rules.py tests/test_soup_metadata_api.py -v`

Expected: all tests pass.

- [ ] **Step 2: Run focused frontend suites**

Run: `cd frontend && npx playwright test tests/e2e/rating-lock.spec.ts tests/e2e/responsive-smoke.spec.ts`

Expected: all tests pass.

- [ ] **Step 3: Review the scoped diff**

Run: `git diff --check` and inspect the four task files.

Expected: no whitespace errors, no numeric score input, no update assignment for an existing rating, and no unrelated reversions.
