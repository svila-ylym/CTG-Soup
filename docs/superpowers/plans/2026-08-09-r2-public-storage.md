# Cloudflare R2 Public Storage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Store public user-uploaded images in Cloudflare R2 using backend-only credentials configured through `.env`, while preserving local storage for development and existing URLs.

**Architecture:** Add conditional storage configuration and a focused `PublicStorage` provider with local and R2 implementations. Inject the provider into the existing upload route, run blocking object-store calls in a worker thread, and compensate by deleting a new object when its database row cannot be committed.

**Tech Stack:** FastAPI, Pydantic Settings 2, SQLModel/SQLAlchemy, boto3 S3 client, pytest

## Global Constraints

- Real Cloudflare or S3 credentials must never be written to source-controlled files, logs, API responses, tests, or frontend code.
- Production selects R2 with `PUBLIC_STORAGE_BACKEND=r2`; development and tests may use `local`.
- Private system-message and email-campaign attachments remain in `PRIVATE_STORAGE_DIR`.
- Existing `/storage/...` database URLs remain usable.
- R2 is accessed only by the backend; no browser PUT, presigned upload, or Cloudflare User API token is required.

---

### Task 1: Validate Environment-Driven Storage Configuration

**Files:**
- Modify: `backend/app/core/config.py`
- Modify: `backend/.env.example`
- Test: `backend/tests/test_public_storage.py`

**Interfaces:**
- Produces: `Settings.PUBLIC_STORAGE_BACKEND: Literal["local", "r2"]`
- Produces: optional `R2_ENDPOINT_URL`, `R2_BUCKET_NAME`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, and `R2_PUBLIC_BASE_URL`, plus `R2_REGION: str`
- Produces: validated `Settings.r2_public_base_url: str`

- [x] **Step 1: Write failing configuration tests**

Add tests that instantiate `Settings(_env_file=None, PUBLIC_STORAGE_BACKEND="local")` without R2 fields, instantiate a complete R2 configuration successfully, and assert `ValidationError` for a missing field, an endpoint with `/bucket`, and a non-HTTPS public URL.

- [x] **Step 2: Run the configuration tests and confirm failure**

Run: `cd backend && pytest -q tests/test_public_storage.py -k settings`

Expected: FAIL because the storage settings and validators do not exist.

- [x] **Step 3: Implement conditional Pydantic validation**

Add the environment fields to `Settings`, validate `PUBLIC_STORAGE_BACKEND` with `Literal`, and use a Pydantic `model_validator(mode="after")` to require and normalize every R2 value only in R2 mode. Validate `R2_ENDPOINT_URL` as an HTTPS origin with no path and validate `R2_PUBLIC_BASE_URL` as an HTTPS origin with no path, query, or fragment.

- [x] **Step 4: Add placeholder-only environment documentation**

Add this block to `backend/.env.example` without any real identifiers or credentials:

```dotenv
# Public uploads: use "r2" in production and "local" for development/tests.
PUBLIC_STORAGE_BACKEND=local
R2_ENDPOINT_URL=https://your-account-id.r2.cloudflarestorage.com
R2_BUCKET_NAME=your-bucket-name
R2_REGION=auto
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_PUBLIC_BASE_URL=https://assets.example.com
```

- [x] **Step 5: Re-run the configuration tests**

Run: `cd backend && pytest -q tests/test_public_storage.py -k settings`

Expected: PASS.

### Task 2: Implement Local And R2 Storage Providers

**Files:**
- Create: `backend/app/services/public_storage.py`
- Modify: `backend/requirements.txt`
- Test: `backend/tests/test_public_storage.py`

**Interfaces:**
- Produces: `PublicStorageError`
- Produces: `LocalPublicStorage.put/delete/public_url` and `name == "local"`
- Produces: `R2PublicStorage.put/delete/public_url` and `name == "r2"`
- Produces: `get_public_storage() -> PublicStorage`

- [x] **Step 1: Write failing provider tests**

Use a temporary directory to assert local write/delete behavior. Use a fake S3 client to assert R2 `put_object` receives `Bucket`, generated `Key`, bytes, `ContentType`, and immutable public caching, `delete_object` receives the same bucket/key, and `public_url` joins the custom domain with the object key.

- [x] **Step 2: Run provider tests and confirm failure**

Run: `cd backend && pytest -q tests/test_public_storage.py -k storage`

Expected: FAIL because `app.services.public_storage` does not exist.

- [x] **Step 3: Add the pinned S3 dependency**

Add `boto3==1.35.99` to `backend/requirements.txt`. Do not add Cloudflare SDKs because R2 uses the standard S3-compatible API.

- [x] **Step 4: Implement the provider module**

Define a `PublicStorage` protocol, local and R2 implementations, and a cached `get_public_storage()` factory. Construct boto3 with endpoint, region, access key, and secret key from `Settings`; do not set an S3 ACL. Convert SDK and filesystem failures into `PublicStorageError` without including secrets. Use `CacheControl="public, max-age=31536000, immutable"` for UUID-keyed uploads.

- [x] **Step 5: Re-run provider tests**

Run: `cd backend && pytest -q tests/test_public_storage.py -k storage`

Expected: PASS.

### Task 3: Route Image Uploads Through The Selected Provider

**Files:**
- Modify: `backend/app/api/uploads.py`
- Test: `backend/tests/test_public_storage.py`

**Interfaces:**
- Consumes: `get_public_storage()`, `PublicStorage`, and `PublicStorageError`
- Preserves: `POST /api/uploads/images` request and `UploadImageResponse`
- Produces: response `storage` equal to the active provider name and an absolute R2 URL in `url`/`UploadedAsset.public_url`

- [x] **Step 1: Write failing route tests**

Call `upload_image` with an in-memory PNG `UploadFile`, a user stub, a recording storage stub, and a session stub. Assert a successful call stores `images/<uid>/<uuid>.png`, writes the returned public URL to the asset, and reports `storage="r2"`. Add a storage-failure test asserting HTTP 503 and no database `add`, plus a commit-failure test asserting the stored key is deleted before the SQLAlchemy error is re-raised.

- [x] **Step 2: Run route tests and confirm failure**

Run: `cd backend && pytest -q tests/test_public_storage.py -k upload`

Expected: FAIL because the upload route still writes directly to local disk.

- [x] **Step 3: Inject and use public storage**

Replace direct `Path.write_bytes` logic with `storage: PublicStorage = Depends(get_public_storage)`. Execute `put` and compensation `delete` with `fastapi.concurrency.run_in_threadpool`. Return HTTP 503 with `公开图片存储暂时不可用` for provider failures, log only provider name/key/error type, and persist the provider's public URL.

- [x] **Step 4: Compensate on database failure**

Wrap `add`, `commit`, and `refresh` in a SQLAlchemy exception handler. Roll back the session, attempt to delete the just-created object, log a cleanup error without replacing the original exception, and re-raise the database exception for the existing global handler.

- [x] **Step 5: Run all new storage tests**

Run: `cd backend && pytest -q tests/test_public_storage.py`

Expected: PASS.

### Task 4: Verify Compatibility And Prepare The Existing PR

**Files:**
- Modify: `docs/superpowers/plans/2026-08-09-r2-public-storage.md` (checkbox status only)
- Copy the reviewed R2 changes into the existing clean GitHub worktree before committing.

**Interfaces:**
- Consumes: all preceding tasks
- Produces: a pushed branch and GitHub PR containing earlier requested changes plus R2 storage support

- [x] **Step 1: Install the pinned backend dependency**

Run: `cd backend && python -m pip install -r requirements.txt`

Expected: dependency installation succeeds without using production R2 credentials.

- [x] **Step 2: Run focused backend verification**

Run: `cd backend && pytest -q tests/test_public_storage.py tests/test_upload_rules.py tests/test_user_routes.py`

Expected: PASS.

- [x] **Step 3: Run the complete backend suite**

Run: `cd backend && pytest -q`

Expected: no new failures; separately report the four known pre-existing failures if they remain.

- [ ] **Step 4: Build the frontend**

Run: `cd frontend && npm run build`

Expected: production build succeeds. Browser automation is omitted per user request.

- [ ] **Step 5: Secret-scan the exact staged diff**

Inspect `git diff --cached` and search staged files for credential-shaped values and the disclosed credential strings without printing matches. Expected: no real R2/Cloudflare credentials and no unrelated `/root` files are staged.

- [ ] **Step 6: Commit, push, and open/update the PR**

Commit the source, test, environment example, spec, and plan files on `codex/system-message-realtime-unread`; push it to `origin`; then create the GitHub PR through the API using the existing ignored local GitHub credential. The PR description must list verification results, the four known unrelated backend failures if still present, required deployment environment variables, and the credential-rotation warning.
