# No-Release OTA State And Version 1.3.1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Treat an empty GitHub Release history as a normal OTA state and publish the application runtime version as `1.3.1`.

**Architecture:** Keep GitHub Latest as the only release source. Classify only an explicit GitHub 404 as `no_release`, preserve the existing error path for every other failure, and extend the admin presentation type/copy without changing the OTA run contract. Continue using the root `VERSION` file as the single runtime version source.

**Tech Stack:** FastAPI, httpx, pytest, Vue 3, TypeScript, Vite.

## Global Constraints

- GitHub Latest remains the only release source; do not fall back to tags, drafts, or prereleases.
- `404 Not Found` produces `status="no_release"`, empty release fields, `update_available=false`, and no user-facing error.
- Other HTTP, network, timeout, and JSON failures continue to produce `status="error"`.
- Set the root `VERSION` file to exactly `1.3.1`.
- Do not create a GitHub Release from the unmerged pull request.
- Do not use a TDD red-green cycle or browser validation; add focused tests and run normal verification after implementation.

---

### Task 1: Classify An Empty Release History

**Files:**
- Modify: `backend/app/services/ota.py`
- Modify: `backend/tests/test_ota.py`

**Interfaces:**
- Consumes: `httpx.Response.status_code`, `Settings.APP_VERSION`, and `LatestReleaseResult`.
- Produces: `LatestReleaseService._fetch_latest() -> LatestReleaseResult` with the new `status="no_release"` result.

- [ ] **Step 1: Add focused 404 and non-404 tests**

Add a reusable fake `httpx.AsyncClient` response whose `raise_for_status()` raises `httpx.HTTPStatusError`. Assert that a 404 result has no error and that a 403 result remains an error:

```python
@pytest.mark.asyncio
async def test_latest_release_404_means_no_published_release(monkeypatch, tmp_path):
    service = ota.LatestReleaseService(_settings(tmp_path))
    # Fake GET returns an httpx.Response(status_code=404, request=...).
    result = await service.check(force=True)
    assert result.status == "no_release"
    assert result.update_available is False
    assert result.latest_version is None
    assert result.error is None


@pytest.mark.asyncio
async def test_latest_release_non_404_http_error_remains_error(monkeypatch, tmp_path):
    service = ota.LatestReleaseService(_settings(tmp_path))
    # Fake GET returns an httpx.Response(status_code=403, request=...).
    result = await service.check(force=True)
    assert result.status == "error"
    assert result.error == "无法读取 GitHub Latest Release"
```

- [ ] **Step 2: Implement explicit 404 classification**

Catch `httpx.HTTPStatusError` before the general exception handler and return the normal empty-release result only for status 404:

```python
except httpx.HTTPStatusError as exc:
    if exc.response.status_code == 404:
        return LatestReleaseResult(
            current_version=self.settings.APP_VERSION,
            latest_version=None,
            tag_name=None,
            release_name=None,
            published_at=None,
            html_url=None,
            status="no_release",
            update_available=False,
            checked_at=checked_at,
            error=None,
        )
    logger.warning("GitHub Latest Release check failed: HTTPStatusError")
    return self._error_result(checked_at)
```

Keep JSON, network, timeout, and other HTTP failures routed to the existing generic error result; a small private helper may remove duplicated construction.

- [ ] **Step 3: Run focused OTA tests**

Run:

```bash
PYTHONPATH=backend /tmp/ctg-verify.xA2dJy/bin/python -m pytest -q backend/tests/test_ota.py
```

Expected: all OTA tests pass, including the new 404/403 cases.

---

### Task 2: Present The State And Publish Version 1.3.1

**Files:**
- Modify: `frontend/src/views/admin/AdminDashboard.vue`
- Modify: `VERSION`

**Interfaces:**
- Consumes: `UpdateStatus.status` from `/api/admin/update/status`.
- Produces: frontend support for `status: "no_release"` and runtime version `1.3.1` through the existing version endpoints/footer.

- [ ] **Step 1: Extend the frontend status type and label**

Add `no_release` to the union and label map:

```ts
status: 'up_to_date' | 'update_available' | 'ahead' | 'invalid_latest_version' | 'unknown_current_version' | 'no_release' | 'error'

no_release: '暂无正式发行版'
```

- [ ] **Step 2: Render the empty Latest field precisely**

Replace the fallback `不可用` with a status-aware value:

```vue
{{ updateInfo.latest_version
  ? `v${updateInfo.latest_version}`
  : updateInfo.status === 'no_release'
    ? '暂无正式发行版'
    : '不可用' }}
```

The existing button remains disabled because `update_available` is false, and the existing color expression treats `no_release` as a non-error green state.

- [ ] **Step 3: Update the single version source**

Set `VERSION` to:

```text
1.3.1
```

- [ ] **Step 4: Build the frontend**

Run:

```bash
npm --prefix frontend ci --no-audit --no-fund
npm --prefix frontend run build
```

Expected: `vue-tsc` and Vite exit zero.

---

### Task 3: Verify, Publish, And Redeploy

**Files:**
- Modify only files required by verification failures.

**Interfaces:**
- Consumes: the completed feature branch and existing repository/remote deployment credentials outside version control.
- Produces: an updated PR #10 and remote Screen deployment running version `1.3.1`.

- [ ] **Step 1: Run final verification**

Run:

```bash
PYTHONPATH=backend /tmp/ctg-verify.xA2dJy/bin/python -m pytest -q backend/tests
/tmp/ctg-verify.xA2dJy/bin/python -m compileall -q backend/app
bash -n Update.sh dev.sh setup.sh
git diff --check
```

Expected: 0 test failures and every command exits zero.

- [ ] **Step 2: Audit and commit**

Confirm staged paths contain no PAT, `.env`, runtime storage, dependency, build, cache, archive, or temporary files. Commit implementation with:

```bash
git commit -m "fix: handle repositories without releases"
```

- [ ] **Step 3: Push the existing PR branch**

Push `codex/ota-ratings-session-competition-v2` normally without force and confirm PR #10 head matches the local commit.

- [ ] **Step 4: Deploy without database writes**

Create a remote source backup, upload tracked source while preserving `.env`, virtual environments, dependencies, builds, storage, archives, and Git metadata. Run the migration entry point with `--dry-run`; apply no migration when its action list is empty. Restart the existing `ctg` Screen session through `/usr/local/sbin/ctg-screen-restart`.

- [ ] **Step 5: Verify the remote runtime**

Poll `http://127.0.0.1:10001/health` and `/api/version` until both report version `1.3.1`. Authenticate to the admin status endpoint and confirm it returns `status="no_release"`, `error=null`, and HTTP 200. Do not use browser validation.
