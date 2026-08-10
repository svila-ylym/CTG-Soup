# Unread Indicators And Email Default Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add boolean unread red dots for notifications, system messages, and private messages, and opt newly registered users into email pushes by default.

**Architecture:** The backend adds an unread-only filter for system-message recipients and sets the new-account email preference explicitly. A small frontend Pinia store polls notification/system-message totals, while the existing chat store supplies realtime private-message unread state through WebSocket events.

**Tech Stack:** FastAPI/SQLModel, Vue 3 Composition API, Pinia, TypeScript, Axios, existing WebSocket chat gateway.

## Global Constraints

- Display only a fixed red dot; never display unread counts.
- Keep notification and system-message polling non-blocking and preserve the last known state on errors.
- Reuse existing chat WebSocket and polling fallback; do not add a second private-message transport.
- Default email opt-in applies only to new registrations; preserve existing database values and the legacy migration default.
- Do not run browser automation; verify with backend tests and the frontend production build.

---

### Task 1: Backend Unread Filter And Registration Default

**Files:**
- Modify: `backend/app/api/system_messages.py`
- Modify: `backend/app/models/models.py:156`
- Modify: `backend/app/api/auth.py:301-310`
- Modify: `backend/app/schemas/__init__.py:64`

**Interfaces:**
- Extends: `GET /api/system-messages?page=1&page_size=20&unread_only=false`.
- Produces: `allow_bulk_email=True` for newly registered `User` rows.

- [ ] **Step 1: Add the system-message unread query parameter**

Add `unread_only: bool = Query(False)` to `list_system_messages`. When true, add `SystemMessageRecipient.read_at.is_(None)` to both the total count query and the joined page query. Keep the existing response shape and default behavior unchanged when false.

- [ ] **Step 2: Set the new-user email default**

Change the SQLModel field default to `True`, set `allow_bulk_email=True` explicitly in `auth.register`, and change only the response-schema fallback to `True`. Leave `social_platform.py` legacy `DEFAULT FALSE` migration SQL unchanged so existing accounts are not silently opted in.

- [ ] **Step 3: Run focused backend contract checks**

Run `PYTHONPATH=. .venv/bin/pytest -q tests/test_auth_security.py tests/test_notification_contract.py tests/test_contract_foundation.py` from `backend`. Record the exact result before moving to frontend work.

### Task 2: Shared Unread State And Chat Projection

**Files:**
- Create: `frontend/src/stores/unread.ts`
- Modify: `frontend/src/api/systemMessages.ts`
- Modify: `frontend/src/stores/chat.ts`

**Interfaces:**
- Produces: `useUnreadStore()` with `hasNotifications`, `hasSystemMessages`, `refreshNotifications()`, `refreshSystemMessages()`, `refreshAll()`, `startPolling()`, `stopPolling()`, and `reset()`.
- Produces: `systemMessagesApi.list(page?: number, pageSize?: number, unreadOnly?: boolean)`.
- Produces: `chatStore.unreadMessageCount` and `chatStore.hasUnreadMessages`.

- [ ] **Step 1: Extend the system-message API client**

Add the optional `unreadOnly` argument and send it as `unread_only` while retaining current callers that pass only page and page size.

- [ ] **Step 2: Implement the unread Pinia store**

Use `http.get('/notifications', { params: { page: 1, page_size: 1, unread_only: true } })` and `systemMessagesApi.list(1, 1, true)`. Set each boolean from `data.total > 0`; catch errors without changing the previous boolean. `startPolling()` must call `refreshAll()` once and install one 30-second interval; repeated starts must not create another timer. `stopPolling()` clears it and `reset()` stops polling and sets both booleans false.

- [ ] **Step 3: Expose private-message unread state**

Add a computed total over `conversations.value.reduce((total, item) => total + Math.max(0, item.unread_count || 0), 0)` and a boolean computed from that total. Add `reset()` to the chat store to disconnect, clear conversations/messages/cursors/active state, and restore offline defaults for account switches.

### Task 3: Navigation And Read-State Synchronization

**Files:**
- Modify: `frontend/src/components/NavBar.vue`
- Modify: `frontend/src/views/NotificationView.vue`
- Modify: `frontend/src/views/SystemMessageView.vue`

**Interfaces:**
- Consumes: unread store and chat-store interfaces from Task 2.
- Produces: fixed red dots on desktop notification/system/private icon buttons and matching dots in authenticated mobile links.

- [ ] **Step 1: Manage authenticated indicator lifecycle**

Watch `authStore.isAuthenticated` immediately. On true, start unread polling, load chat conversations, and connect the chat WebSocket. On false, stop/reset unread state and reset/disconnect chat. Repeat cleanup on component unmount. Do not connect without an access token.

- [ ] **Step 2: Replace the notification count badge**

Remove numeric `unreadCount`/`unreadLabel` rendering. Use a fixed `h-2.5 w-2.5` red dot with `aria-label="有未读通知"` when `unreadStore.hasNotifications` is true. Add equivalent relative-positioned dots to system messages and private messages, preserving the existing button dimensions.

- [ ] **Step 3: Add mobile red dots**

Keep mobile navigation text unchanged and append a small red dot beside the notification, system-message, and private-message labels when their corresponding boolean is true.

- [ ] **Step 4: Refresh state after reading**

After a notification is successfully marked read, call `unreadStore.refreshNotifications()`. After a system message is successfully marked read, call `unreadStore.refreshSystemMessages()`. Loading either page should also refresh its boolean once the list response succeeds.

### Task 4: Verification

**Files:**
- Verify: `backend/app/api/system_messages.py`, `backend/app/api/auth.py`, `backend/app/models/models.py`
- Verify: `frontend/src/stores/unread.ts`, `frontend/src/stores/chat.ts`, `frontend/src/components/NavBar.vue`

**Interfaces:**
- Consumes: completed backend and frontend changes from Tasks 1-3.
- Produces: test/build evidence without browser automation.

- [ ] **Step 1: Run frontend checks**

Run `npm run build` from `frontend`. Require `vue-tsc` and Vite to exit 0.

- [ ] **Step 2: Run backend focused and full checks**

Run the Task 1 focused pytest command, then `PYTHONPATH=. .venv/bin/pytest -q` from `backend`. Report any pre-existing failures separately from failures introduced by this change.

- [ ] **Step 3: Run static and service checks**

Run `git diff --check -- project/CTG` from `/root`, compile the changed backend modules, and confirm `/health` still responds. Do not run Playwright or other browser automation.
