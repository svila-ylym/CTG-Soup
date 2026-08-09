# Local Handover and Environment Setup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce an accurate handover manual and a secure, working local configuration for PostgreSQL, Redis, local uploads, JWT, and 126 Mail SMTP.

**Architecture:** Keep all runtime configuration in Pydantic `Settings`, with secrets in ignored `backend/.env` and non-secret defaults in `backend/.env.example`. Extend the SMTP connection factory with an explicit SSL mode so port 465 works while retaining the existing STARTTLS mode.

**Tech Stack:** Python 3.12, FastAPI, pydantic-settings, smtplib, pytest, Vue 3, TypeScript, Vite

## Global Constraints

- Real SMTP credentials and JWT secrets must exist only in `backend/.env`.
- `backend/.env` must be ignored by Git and have mode `0600`.
- Local PostgreSQL is `postgresql://postgres:postgres@localhost:5432/turtle_soup`.
- Local Redis is `redis://localhost:6379/0`.
- Local frontend URL is `http://localhost:10000`; backend is `http://localhost:8000`.
- Local uploads use `backend/storage`; S3 is disabled.
- SMTP uses `smtp.126.com:465` with SSL and the configured 126 Mail account.
- Verification output must never print secret values.

---

### Task 1: Add SMTP SSL Support

**Files:**
- Modify: `backend/app/core/config.py`
- Modify: `backend/app/utils/email.py`
- Create: `backend/tests/test_email_connection.py`

**Interfaces:**
- Consumes: `get_settings() -> Settings`
- Produces: `Settings.SMTP_USE_SSL: bool` and `SMTPService._create_connection() -> smtplib.SMTP`

- [ ] **Step 1: Write failing SSL and STARTTLS connection tests**

Create tests that monkeypatch module-level `settings`, `smtplib.SMTP_SSL`, and `smtplib.SMTP`. Assert SSL mode constructs `SMTP_SSL(host, port)`, logs in, and never calls `starttls`; assert non-SSL mode constructs `SMTP(host, port)`, calls `starttls`, then logs in.

```python
def test_create_connection_uses_smtp_ssl(monkeypatch):
    fake = Mock()
    monkeypatch.setattr(email_module.settings, "SMTP_USE_SSL", True, raising=False)
    monkeypatch.setattr(email_module.smtplib, "SMTP_SSL", Mock(return_value=fake))
    service = email_module.SMTPService()
    assert service._create_connection() is fake
    email_module.smtplib.SMTP_SSL.assert_called_once_with("smtp.126.com", 465)
    fake.starttls.assert_not_called()
```

- [ ] **Step 2: Run the focused test and confirm it fails**

Run: `cd backend && PYTHONPATH=. venv/bin/python -m pytest -q tests/test_email_connection.py`

Expected: FAIL because `SMTP_USE_SSL` is not read and `SMTP_SSL` is not selected.

- [ ] **Step 3: Implement the minimal SSL branch**

Add `SMTP_USE_SSL: bool = False` to `Settings`; copy it in `SMTPService.__init__`; select the connection type before login.

```python
if self.smtp_use_ssl:
    server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port)
else:
    server = smtplib.SMTP(self.smtp_host, self.smtp_port)
    server.starttls()
```

- [ ] **Step 4: Run the focused test**

Run: `cd backend && PYTHONPATH=. venv/bin/python -m pytest -q tests/test_email_connection.py`

Expected: `2 passed`.

- [ ] **Step 5: Commit the SMTP change if Git metadata is writable**

```bash
git add backend/app/core/config.py backend/app/utils/email.py backend/tests/test_email_connection.py
git commit -m "feat: support SSL SMTP connections"
```

If `/root/.git` remains read-only, record that constraint and continue without a commit.

### Task 2: Secure and Configure Local Environment

**Files:**
- Replace: `.gitignore`
- Modify: `backend/.env.example`
- Modify locally: `backend/.env`

**Interfaces:**
- Consumes: all uppercase fields in `backend/app/core/config.py`
- Produces: a secret-free example and a local settings file loadable by `Settings`

- [ ] **Step 1: Replace the invalid ignore file**

Add ignore rules for `.env`, `.env.*` with `!.env.example`, Python caches and virtual environments, Node dependencies/build output, test caches, local storage, logs, OS files, and editor settings.

- [ ] **Step 2: Align the example with Settings**

Include `APP_URL`, `EMAIL_DOMAIN_WHITELIST`, `SMTP_USE_SSL`, `S3_ENABLED`, `MAX_UPLOAD_BYTES`, and every other field currently accepted by `Settings`; use empty values for credentials.

- [ ] **Step 3: Write the local environment file without exposing secrets**

Use the approved local service URLs, generate a random JWT key, write the supplied SMTP account and authorization code, set `SMTP_USE_SSL=true`, and set `S3_ENABLED=false`.

- [ ] **Step 4: Restrict file permissions and verify ignore behavior**

Run: `chmod 600 backend/.env && stat -c '%a' backend/.env`

Expected: `600`.

Run: `git check-ignore -v backend/.env`

Expected: `.gitignore` reports a matching environment-file rule.

- [ ] **Step 5: Verify Pydantic settings without printing secrets**

Run a Python assertion script from `backend/` that checks database URL, Redis URL, SMTP host/port/SSL, local storage, and that secret fields are non-default and non-empty.

### Task 3: Rewrite the Handover Manual

**Files:**
- Replace: `HANDOVER.md`
- Modify: `README.md` only if commands or configuration examples conflict with the handover manual

**Interfaces:**
- Consumes: verified repository structure, scripts, settings, routes, tests, and build commands
- Produces: an operational guide for the next maintainer

- [ ] **Step 1: Document verified project status**

Describe the architecture and distinguish implemented code, tested rules, incomplete integration, and known legacy field mismatches.

- [ ] **Step 2: Document local setup in execution order**

Cover Python/Node/PostgreSQL/Redis prerequisites; database creation; `./dev.sh init`; environment configuration; `./dev.sh dev`; URLs; and stopping services.

- [ ] **Step 3: Document configuration and security**

Explain each variable group, 126 SMTP SSL settings without secrets, local upload behavior, `.env` permissions, and secret rotation requirements.

- [ ] **Step 4: Document verification, troubleshooting, and priorities**

Provide exact test/build/health commands, likely failure causes, current limitations, and a prioritized continuation list.

- [ ] **Step 5: Check all documented paths and commands against the repository**

Run `rg` checks for every referenced script, port, route, settings key, and test path. Remove claims that cannot be supported by code or command output.

### Task 4: Regression Verification

**Files:**
- Modify only files required to fix regressions caused by Tasks 1-3

**Interfaces:**
- Consumes: completed SMTP, environment, and documentation changes
- Produces: verification evidence and a list of external prerequisites not testable in the workspace

- [ ] **Step 1: Run focused and full backend tests**

Run: `cd backend && PYTHONPATH=. venv/bin/python -m pytest -q tests/test_email_connection.py`

Run: `PYTHONPATH=backend backend/venv/bin/python -m pytest -q backend/tests`

- [ ] **Step 2: Compile backend source**

Run: `backend/venv/bin/python -m compileall -q backend/app`

- [ ] **Step 3: Build the frontend**

Run: `cd frontend && npm run build`

- [ ] **Step 4: Perform non-secret configuration checks**

Confirm `.env` mode, Git ignore matching, Settings assertions, and absence of the authorization code from tracked/example/documentation files.

- [ ] **Step 5: Check local services and SMTP connectivity without sending email**

Check PostgreSQL and Redis using available local clients or TCP probes. Attempt an SMTP SSL connection/login only if outbound network access is available, then close it without sending a message. Report unavailable services or blocked networking as external prerequisites.

- [ ] **Step 6: Review the final diff and hand off**

Run `git diff --check` on changed source and documentation files. Summarize files changed, commands passed, unavailable external checks, and the read-only Git metadata constraint.
