# Moderation And Root Bootstrap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete reporting, banning, soup deletion, and deterministic UID=1 ROOT bootstrap using the repository's existing governance models.

**Architecture:** Keep FastAPI routes thin and add focused moderation helpers for target resolution and competition cleanup. Reuse `Report`, `Punishment`, `Notification`, and `OperationLog`; frontend controls call the existing API client and admin dashboard patterns.

**Tech Stack:** FastAPI, SQLModel/SQLAlchemy, Pydantic, Vue 3, Pinia, Heroicons, Playwright, pytest.

## Global Constraints

- Deleted soups are soft-deleted and settled competition snapshots never change.
- Only UID 1 is automatically promoted to ROOT.
- A ROOT account cannot be banned through the punishment workflow.
- Existing dirty-worktree changes must be preserved.

---

### Task 1: ROOT Bootstrap

**Files:**
- Modify: `backend/app/api/auth.py`
- Test: `backend/tests/test_auth_security.py`

**Interfaces:**
- Consumes: database-assigned `User.uid` after `Session.flush()`.
- Produces: registration responses where UID 1 has `UserRole.ROOT` and later users have `UserRole.USER`.

- [ ] Add tests that register into an empty database and into a database with an existing account.
- [ ] Run the focused tests and confirm the UID=1 and later-user assertions fail.
- [ ] After flush, set `db_user.role = UserRole.ROOT` only when `db_user.uid == 1`.
- [ ] Re-run the focused tests and confirm they pass.

### Task 2: Report Validation And Decision Notification

**Files:**
- Create: `backend/app/services/reporting.py`
- Modify: `backend/app/api/admin.py`
- Modify: `backend/app/schemas/__init__.py`
- Test: `backend/tests/test_moderation_api.py`

**Interfaces:**
- Produces: `resolve_report_target(db, reporter, target_type, target_id)` and `report_target_metadata(db, report)`.
- Produces: HTTP 404 for missing/deleted targets, 403 for inaccessible/self targets, and 409 for duplicate pending reports.

- [ ] Add API tests for a valid soup report, a missing target, a self-report, a duplicate pending report, and an inaccessible private message.
- [ ] Run them and confirm the current endpoint accepts invalid cases.
- [ ] Implement typed target resolution and duplicate detection, then use it in report submission.
- [ ] Add a decision test asserting exactly one `REPORT_RESULT` notification and an operation log.
- [ ] Implement decision notification and target metadata in admin listings.
- [ ] Re-run moderation tests.

### Task 3: Audited Ban Workflow

**Files:**
- Modify: `backend/app/api/admin.py`
- Modify: `backend/app/schemas/__init__.py`
- Test: `backend/tests/test_moderation_api.py`

**Interfaces:**
- Consumes: `PunishmentCreate` with `punishment_type="ban"`.
- Produces: a `Punishment`, `User.status=banned`, incremented `token_version`, notification, and operation log in one transaction.

- [ ] Add tests for admin banning a user, duplicate ban rejection, self-ban rejection, admin-versus-admin rejection, and ROOT-target rejection.
- [ ] Run the tests and confirm the current route misses the required boundaries and token invalidation.
- [ ] Validate normalized reasons and role boundaries, reject active duplicate bans, increment `token_version`, and create a punishment notification.
- [ ] Re-run ban and authentication tests.

### Task 4: Turtle Soup Soft Deletion

**Files:**
- Modify: `backend/app/services/competition_entries.py`
- Modify: `backend/app/api/turtle_soups.py`
- Test: `backend/tests/test_soup_api_security.py`
- Test: `backend/tests/test_competition_contract.py`

**Interfaces:**
- Produces: `remove_soup_from_unsettled_competitions(db, soup_id) -> None`.
- Produces: `DELETE /api/turtle-soups/{id}` returning 204 for authors/admins and 403 for unrelated users.

- [ ] Add tests for author deletion, admin deletion, unrelated-user rejection, subsequent 404, unsettled-entry removal, and settled-entry preservation.
- [ ] Run them and confirm the delete route is absent.
- [ ] Implement locked unsettled-entry cleanup, soft deletion, timestamp update, and operation logging.
- [ ] Re-run soup and competition tests.

### Task 5: Frontend Moderation Controls

**Files:**
- Modify: `frontend/src/components/ReportDialog.vue`
- Modify: `frontend/src/views/SoupDetailView.vue`
- Modify: `frontend/src/views/admin/AdminDashboard.vue`
- Modify: `frontend/src/api/soup.ts`
- Test: `frontend/tests/e2e/moderation-actions.spec.ts`

**Interfaces:**
- Consumes: current report, punishment, and soup-delete endpoints.
- Produces: accessible confirmation/action controls with server error feedback.

- [ ] Add Playwright tests for report success/error, manageable-soup deletion, and admin banning with a required reason.
- [ ] Run them and confirm controls or behavior are missing.
- [ ] Use `extractApiError` in the report dialog, add the trash-icon confirmation flow, and add a ban reason/action in the admin user table.
- [ ] Re-run Playwright and `npm run build`.

### Task 6: Final Verification

**Files:**
- Verify only; no new production files.

- [ ] Run focused backend moderation, auth, soup, and competition suites.
- [ ] Run the full backend suite and separate unrelated baseline failures.
- [ ] Run frontend production build and moderation Playwright specs.
- [ ] Run `git diff --check` and inspect the final diff for unrelated changes.
