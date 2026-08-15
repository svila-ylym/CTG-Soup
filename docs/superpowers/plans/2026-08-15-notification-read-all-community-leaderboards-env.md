# Notification Read-All, Community Leaderboards, and Environment Template Implementation Plan

> **For agentic workers:** Execute inline in the existing worktree. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add one-click notification read-all, split the community ranking into ordinary and 鳖汤 scopes, and make environment initialization complete and reliable for release `1.5.0`.

**Architecture:** Add one recipient-scoped bulk notification endpoint and expose it through the existing notification page/store. Extend the existing soup-list query with an optional typed ranking scope, then make the ranking page a single reusable view driven by that scope. Keep `.env.example` declarative while startup scripts generate the required local secret.

**Tech Stack:** FastAPI, SQLModel/SQLAlchemy, Pydantic Settings, Vue 3, Pinia, TypeScript, Tailwind CSS, pytest, Playwright.

## Global Constraints

- Version remains exactly `1.5.0`.
- Do not use TDD; implement first, then add focused regression coverage.
- Do not add dependencies or database migrations.
- Do not alter competition rankings.
- Do not read, print, overwrite, or commit real environment secrets.
- Do not dispatch subagents.

---

### Task 1: Notification read-all contract and UI

**Files:**
- Modify: `backend/app/api/notifications.py`
- Modify: `backend/app/schemas/community.py`
- Modify: `frontend/src/stores/unread.ts`
- Modify: `frontend/src/views/NotificationView.vue`
- Modify: `backend/tests/test_notification_contract.py`

- [ ] Add `NotificationReadAllResponse(updated_count: int)`.
- [ ] Add `PUT /read-all` before the dynamic notification route and bulk-update only the active user's unread rows.
- [ ] Add a store method that invalidates in-flight red-dot refreshes and sets the known unread state to false.
- [ ] Add the disabled/busy “全部已读” action and update loaded rows only after API success.
- [ ] Add focused coverage for recipient isolation and idempotency.

### Task 2: Ordinary and 鳖汤 community ranking scopes

**Files:**
- Modify: `backend/app/api/turtle_soups.py`
- Modify: `frontend/src/api/soup.ts`
- Modify: `frontend/src/stores/soup.ts`
- Modify: `frontend/src/views/LeaderboardView.vue`
- Modify: `backend/tests/test_soup_metadata_api.py`

- [ ] Accept `ranking_scope: Literal["regular", "bie"] | None` in the soup list.
- [ ] Apply `genre != "鳖汤"` for regular and `genre == "鳖汤"` for bie before counting and pagination.
- [ ] Thread the typed scope through the API client and store; prevent stale requests from overwriting the active list.
- [ ] Add an accessible segmented scope switch and scoped header/empty-state copy without duplicating the ranking layout.
- [ ] Add focused API coverage proving categories do not mix and the unscoped list remains compatible.

### Task 3: Environment template and initialization

**Files:**
- Modify: `backend/.env.example`
- Modify: `dev.sh`
- Modify: `setup.ps1`
- Modify: `setup.bat`
- Modify: `README.md`

- [ ] Add missing `PASSWORD_RESET_EXPIRE_MINUTES` and empty optional R2 values.
- [ ] Generate and replace `SECRET_KEY` only when an initialization script creates a new `.env`.
- [ ] Keep existing `.env` files untouched and document secret rotation for production.
- [ ] Validate the example keys against `Settings` and load a temporary copied environment with a generated secret.

### Task 4: Verification and delivery

**Files:**
- Verify all modified files and the existing release work.

- [ ] Run focused backend notification, soup metadata, homepage, and competition contract tests.
- [ ] Run `npm run build` and focused Playwright coverage serially.
- [ ] Run `git diff --check`, confirm `VERSION` and frontend package version are `1.5.0`, and review the complete diff for secrets or unrelated files.
- [ ] Commit implementation, push `feat/redis-cache-glass-1.5.0`, create a PR to `main`, and preserve the worktree.
- [ ] Start backend on `10001` and frontend on `10000`, then confirm health and page responses for manual review.

