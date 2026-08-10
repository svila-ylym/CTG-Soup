# Account Recovery, Pending User Administration, Message Timezone, and Soup Badges Implementation Plan

> **For agentic workers:** Execute inline in the current session. The user explicitly requested no TDD and no browser automation.

**Goal:** Complete email-based password recovery, let root delete pending accounts, display private-message times in UTC+8, expose soup genre/color throughout the soup UI, and make all navigation available on mobile.

**Architecture:** Extend existing FastAPI auth/admin routers and SMTP/JWT helpers without a schema migration. Add two guest Vue views, reuse the existing admin table, centralize soup badge classes, and keep UTC storage unchanged while formatting timestamps at the frontend boundary.

**Tech Stack:** FastAPI, SQLAlchemy/SQLModel, JWT, SMTP, Vue 3, TypeScript, Tailwind CSS

## Global Constraints

- Do not use TDD.
- Do not run browser or Playwright tests.
- Do not add a database migration.
- Do not change database models or schema.
- Preserve UTC database timestamps and display private-message times in `Asia/Shanghai`.
- Update the existing pull request after verification.

---

### Task 1: Password Reset Backend

**Files:**
- Modify: `backend/app/core/config.py`
- Modify: `backend/app/schemas/__init__.py`
- Modify: `backend/app/api/auth.py`
- Modify: `backend/app/utils/email.py`

**Interfaces:**
- Consumes: existing `get_smtp_service()`, `rate_limiter`, JWT secret/algorithm, password hashing helpers.
- Produces: `POST /api/auth/reset-password-request` and `POST /api/auth/reset-password`.

- [ ] Add `PASSWORD_RESET_EXPIRE_MINUTES=30` and request schemas for an email and `{token, new_password}`.
- [ ] Create a `password_reset` JWT containing `sub`, `ver`, `token_type`, and expiry.
- [ ] Send reset mail only for existing non-pending accounts while returning a generic response for all email addresses.
- [ ] Validate token purpose, expiry, UID, and `token_version`; replace the password and increment `token_version`.
- [ ] Make email copy match the 30-minute expiry.

### Task 2: Root Pending-Account Deletion

**Files:**
- Modify: `backend/app/api/admin.py`
- Modify: `frontend/src/views/admin/AdminDashboard.vue`

**Interfaces:**
- Consumes: `lock_uid_allocation`, `EmailVerification`, and `ReusableUserUid`.
- Produces: `DELETE /api/admin/users/{uid}/pending` and a root-only table action.

- [ ] Add a root-protected endpoint that locks and rechecks the pending account.
- [ ] Delete verification records, release the UID, log the action, and commit atomically.
- [ ] Add a confirmation-protected delete button only on `pending_email` rows for root.
- [ ] Refresh admin data and surface API errors after deletion.

### Task 3: Password Reset Frontend

**Files:**
- Create: `frontend/src/views/ForgotPasswordView.vue`
- Create: `frontend/src/views/ResetPasswordView.vue`
- Modify: `frontend/src/views/LoginView.vue`
- Modify: `frontend/src/router/index.ts`

**Interfaces:**
- Consumes: existing `authApi.requestPasswordReset`, `authApi.resetPassword`, and `extractApiError`.
- Produces: public `/forgot-password` and `/reset-password?token=...` recovery flows.

- [ ] Build the email request form with a generic success state.
- [ ] Build the token reset form with password policy and confirmation validation.
- [ ] Add public recovery routes and a login-page forgot-password link.
- [ ] Redirect successful reset attempts to login with a visible completion message.

### Task 4: UTC+8 Private-Message Formatting

**Files:**
- Modify: `frontend/src/utils/datetime.ts`
- Modify: `frontend/src/views/MessageView.vue`

**Interfaces:**
- Consumes: timezone-less UTC API timestamps.
- Produces: `formatChinaMessageTime(value)` for same-day `HH:mm` and older `M/D` output.

- [ ] Parse missing timezone suffixes as UTC.
- [ ] Compare calendar dates and format output using `Asia/Shanghai`.
- [ ] Use the helper for conversation previews and message bubbles.

### Task 5: Soup Genre And Color Badges

**Files:**
- Create: `frontend/src/utils/soupMetadata.ts`
- Modify: `frontend/src/views/SoupDetailView.vue`
- Modify: `frontend/src/views/soup/SoupListView.vue`
- Modify: `frontend/src/views/HomeView.vue`

**Interfaces:**
- Consumes: existing `TurtleSoup.genre` and `TurtleSoup.soup_color` values.
- Produces: shared `genreBadgeClass` and `soupColorBadgeClass` helpers.

- [ ] Map each genre and color to compact light/dark badge classes.
- [ ] Render both badges below titles in list cards and homepage popular cards.
- [ ] Render both badges in the soup detail metadata header.

### Task 6: Mobile Navigation Drawer

**Files:**
- Modify: `frontend/src/components/NavBar.vue`
- Modify: `frontend/src/assets/main.css`

**Interfaces:**
- Consumes: current auth role, unread stores, router, and theme helpers.
- Produces: a responsive mobile side drawer with complete navigation.

- [ ] Reduce the mobile top bar to the brand and menu button.
- [ ] Add a full-width drawer search form and grouped browsing, message, creation, administration, and account links.
- [ ] Preserve unread indicators and role-based visibility inside the drawer.
- [ ] Add backdrop/Escape close behavior, body-scroll locking, drawer scrolling, and safe-area padding.

### Task 7: Verification And PR Update

**Files:**
- Review all modified files and the complete branch diff.

**Interfaces:**
- Consumes: finished implementation.
- Produces: verified commits pushed to the existing PR branch.

- [ ] Run Python compilation and backend import checks.
- [ ] Run the frontend production build.
- [ ] Run `git diff --check` and inspect `git diff --stat` plus security-sensitive changes.
- [ ] Commit implementation with a scoped message.
- [ ] Push `codex/community-updates-20260809` and confirm PR #8 points to the new head.
