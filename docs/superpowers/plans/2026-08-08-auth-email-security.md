# Auth Email Verification and Security Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make local database startup self-initializing when explicitly enabled and deliver a secure registration, email verification, login, and token refresh flow.

**Architecture:** Add an opt-in PostgreSQL database provisioning helper before SQLModel table creation. Keep email-token generation and hashing in a focused authentication service, persist only hashes, and expose narrow FastAPI request models. Frontend pages consume the corrected contracts and sanitize login redirects.

**Tech Stack:** Python 3.12, FastAPI, SQLModel, SQLAlchemy, psycopg2, python-jose, passlib, pytest, Vue 3, TypeScript, Vite

## Global Constraints

- `AUTO_CREATE_DATABASE` defaults to `false`; only local `backend/.env` enables it.
- Verification tokens use `secrets.token_urlsafe(32)` and only SHA-256 hashes are stored.
- Verification tokens expire after 30 minutes and resend is limited to once per 60 seconds.
- Pending users cannot log in or access authenticated endpoints.
- Access and refresh JWTs are not interchangeable.
- API responses and logs never expose secrets, password hashes, or token hashes.
- Existing users and production databases require a future Alembic migration; this change targets the currently missing local database.

---

### Task 1: Opt-In PostgreSQL Database Provisioning

**Files:**
- Modify: `backend/app/core/config.py`
- Modify: `backend/app/db.py`
- Create: `backend/tests/test_database_initialization.py`
- Modify: `backend/.env.example`
- Modify locally: `backend/.env`

**Interfaces:**
- Produces: `ensure_database_exists(database_url: str, enabled: bool) -> None`
- Consumes: `Settings.AUTO_CREATE_DATABASE`, `Settings.DATABASE_URL`

- [ ] Write tests proving disabled and non-PostgreSQL calls do nothing, existing databases are not created, and missing databases execute one safely quoted `CREATE DATABASE` statement.
- [ ] Run the focused tests and confirm failure because the helper does not exist.
- [ ] Implement URL parsing, maintenance connection, parameterized existence query, psycopg2 identifier quoting, and password-free error guidance.
- [ ] Call the helper from `init_db()` before `create_all()` and update local/example configuration.
- [ ] Run focused tests and the application import test.

### Task 2: Verification Data Model and Token Service

**Files:**
- Modify: `backend/app/models/models.py`
- Modify: `backend/app/models/database.py`
- Modify: `backend/app/core/enums.py`
- Modify: `backend/app/schemas/__init__.py`
- Create: `backend/app/services/email_verification.py`
- Create: `backend/tests/test_email_verification.py`

**Interfaces:**
- Produces: `EmailVerification`, `hash_verification_token(token: str) -> str`, `new_verification_token() -> str`, `verification_expiry(now: datetime) -> datetime`
- Produces schemas: `RefreshTokenRequest`, `EmailVerificationRequest`, `EmailVerificationResendRequest`, `MessageResponse`

- [ ] Write failing tests for opaque token length/uniqueness, deterministic hashing, expiry, and pending status availability.
- [ ] Add `PENDING_EMAIL` to both model and schema enums and add the verification table with hash, expiry, creation and used timestamps.
- [ ] Implement the focused service with timezone-consistent UTC datetimes.
- [ ] Add explicit request/response schemas and exports.
- [ ] Run focused model/service and application import tests.

### Task 3: Secure Authentication API

**Files:**
- Modify: `backend/app/api/auth.py`
- Modify: `backend/app/utils/email.py`
- Modify: `backend/app/utils.py`
- Create: `backend/tests/test_auth_security.py`

**Interfaces:**
- Consumes: Task 2 token helpers, schemas, `EmailVerification`, `SMTPService`
- Produces: `/register`, `/send-verification`, `/verify-email`, `/login`, `/refresh`, `/me`

- [ ] Write failing unit/API-contract tests for string JWT subjects, token-type rejection, pending-login rejection, refresh JSON body, and verification state transitions.
- [ ] Make token creators always add an exact token type and string subject; enforce the expected type in access and refresh decoders.
- [ ] Register pending users, persist token hashes, and send the opaque token after commit.
- [ ] Implement verify and resend endpoints with generic responses, expiration checks, invalidation and 60-second cooldown.
- [ ] Update the email template link parameter from `code` to `token` and remove hard-coded JWT behavior from `app/utils.py`.
- [ ] Run focused and full backend tests.

### Task 4: Frontend Authentication Flow

**Files:**
- Modify: `frontend/src/api/auth.ts`
- Modify: `frontend/src/stores/auth.ts`
- Modify: `frontend/src/views/RegisterView.vue`
- Modify: `frontend/src/views/LoginView.vue`
- Create: `frontend/src/views/VerifyEmailView.vue`
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/src/types/index.ts`
- Create: `frontend/src/utils/auth.ts`
- Create: `frontend/src/utils/auth.test.ts` only if a test runner is available; otherwise verify with TypeScript compilation.

**Interfaces:**
- Produces: `extractApiError(error: unknown, fallback: string) -> string`, `safeRedirect(value: unknown) -> string`
- Consumes: JSON refresh and verification endpoints from Task 3

- [ ] Add pure helpers for FastAPI error extraction and same-origin redirect validation; verify representative inputs with a TypeScript one-off test or configured runner.
- [ ] Update auth API and store contracts to use JSON refresh, verification token, resend email and `detail` errors.
- [ ] Route successful registration to the verification page and add verification/resend UI states.
- [ ] Sanitize the login redirect and expose a verification link for pending accounts.
- [ ] Align the user type with backend fields and add `pending_email`.
- [ ] Run `vue-tsc --noEmit` or `npm run build`, recording unrelated empty-page failures separately.

### Task 5: Security and End-to-End Regression

**Files:**
- Modify: `HANDOVER.md`
- Modify: `README.md` if initialization instructions conflict
- Modify only files required by regressions caused by Tasks 1-4

**Interfaces:**
- Consumes: all completed backend and frontend changes
- Produces: verified operational documentation and evidence

- [ ] Update handover configuration, database provisioning, verification flow, security limits and migration warning.
- [ ] Run full backend pytest and compileall, then import `app.main`.
- [ ] Verify `.env` mode and ignore behavior and scan for the real SMTP credential outside `.env`.
- [ ] Run frontend dependency validation and build/type checks; distinguish the known empty Vue pages and unavailable npm networking.
- [ ] If PostgreSQL is reachable, start the backend and call `/health`; otherwise report the external service prerequisite.
- [ ] Run `git diff --check` on all changed files and summarize residual risks without claiming blocked checks passed.
