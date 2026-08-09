# 社交平台扩展实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在保留现有用户和内容数据的前提下，完成汤底与搜索修复、账户和个人主页、签到等级、@ 提及、实时私信、根用户群发、邮件偏好和黑白主题 UI。

**Architecture:** 继续使用 FastAPI/SQLModel/PostgreSQL 和 Vue 3/Pinia；新增领域服务承载等级、提及、Markdown、消息连接和邮件队列，路由只做鉴权、事务和 Schema 转换。所有数据库升级集中到可重复执行的 `social_platform` 迁移入口，每个任务扩展自己负责的迁移动作，并在真实库写入前创建可校验备份。

**Tech Stack:** Python 3.12、FastAPI 0.109、SQLModel 0.0.22、PostgreSQL、Redis 可选适配、pytest；Vue 3.5、TypeScript 5.8、Pinia、Vue Router、Tailwind CSS 4、Heroicons、DOMPurify、Playwright。

## Global Constraints

- 浏览器个人主页端点固定为 `/profile/:uid`；公开 API 固定为 `GET /api/users/{uid}/profile`。
- `Soup.main_player_count` 和 `secondary_player_count` 使用数据库 `TEXT`，请求必须带字段但允许任意 Unicode 和空字符串，不做数值、范围或类别校验。
- 已发布作品的汤底对所有人可展开；首次详情响应固定为 `solution: null`。
- 只有 `root` 能调用系统站内信和邮件群发接口，`admin` 不等价于 `root`。
- `allow_bulk_email` 默认 `false`；它不影响验证、重置密码、安全邮件、站内信和 @ 通知。
- 浅色为白色系，深色为黑色系；移除大面积紫色、蓝紫渐变和装饰性渐变。
- 用户生成的 Markdown、提及和聊天正文不得通过未消毒 `v-html` 渲染。
- 新增接口错误固定为 `detail: {code: string, message: string}`，前端展示 `message`，测试断言稳定 `code`。
- 全站 `letter-spacing: 0`，文字和动态内容不得改变固定工具栏、消息列表或按钮尺寸。
- Redis 不可用时 HTTP 消息、数据库历史和签到继续工作；typing 跨进程能力可降级并由健康检查报告。
- 任何真实数据库写入前必须先生成 `pg_dump` 备份、SHA-256 和 dry-run 报告。
- 每个任务通过定向测试、完整后端回归和前端构建后，立即更新 `HANDOVER.md` 并单独提交。

## File Ownership Map

- `backend/app/migrations/social_platform.py`：本批唯一升级入口。
- `backend/app/services/database_backup.py`：PostgreSQL 备份和 SHA-256。
- `backend/app/services/levels.py`：签到日期、奖励和等级纯函数。
- `backend/app/services/mentions.py`：提及解析、差异同步和通知写入。
- `backend/app/services/message_gateway.py`：WebSocket、typing 过期和广播。
- `backend/app/services/safe_markdown.py`：禁用原始 HTML 的 Markdown 渲染。
- `backend/app/services/email_campaigns.py`：收件人快照、opt-in 过滤和队列批处理。
- `frontend/src/components/MentionText.vue`：按 mention spans 安全文本分片。
- `frontend/src/stores/chat.ts`：会话、消息、WebSocket 和轮询降级。
- `frontend/src/views/admin/BroadcastCenterView.vue`：根用户站内信和邮件工作台。

---

### Task 1: 备份与升级迁移骨架

**Files:**
- Create: `backend/app/services/database_backup.py`
- Create: `backend/app/migrations/social_platform.py`
- Create: `backend/tests/test_database_backup.py`
- Create: `backend/tests/test_social_platform_migration.py`
- Modify: `backend/app/migrations/__init__.py`
- Modify: `HANDOVER.md`

**Interfaces:**
- Produces `BackupResult(path: Path, sha256: str, created_at: datetime)`。
- Produces `create_database_backup(database_url: str, output_dir: Path, runner=subprocess.run) -> BackupResult`。
- Produces `UpgradeReport(actions: tuple[str, ...], applied: bool, counts: dict[str, int])`。
- Produces `upgrade_social_platform(engine: Engine = default_engine, dry_run: bool = False, phase: str = "all") -> UpgradeReport`。

- [ ] **Step 1: Write failing backup and migration-report tests**

```python
def test_backup_uses_custom_format_and_writes_checksum(tmp_path):
    calls = []
    def runner(args, **kwargs):
        calls.append((args, kwargs))
        Path(args[args.index("--file") + 1]).write_bytes(b"pgdump")
        return subprocess.CompletedProcess(args, 0)

    result = create_database_backup(
        "postgresql://user:secret@localhost/app", tmp_path, runner=runner
    )
    assert "--format=custom" in calls[0][0]
    assert result.sha256 == hashlib.sha256(b"pgdump").hexdigest()
    assert "secret" not in repr(result)


def test_social_upgrade_dry_run_never_executes_ddl(legacy_engine):
    report = upgrade_social_platform(legacy_engine, dry_run=True, phase="foundation")
    assert report.applied is False
    assert report.actions
```

- [ ] **Step 2: Run tests and confirm RED**

Run: `PYTHONPATH=backend backend/venv/bin/python -m pytest -q backend/tests/test_database_backup.py backend/tests/test_social_platform_migration.py`
Expected: collection fails because both modules are missing.

- [ ] **Step 3: Implement backup and phase-based migration runner**

```python
@dataclass(frozen=True)
class BackupResult:
    path: Path
    sha256: str
    created_at: datetime


def create_database_backup(database_url, output_dir, runner=subprocess.run):
    output_dir.mkdir(parents=True, exist_ok=True)
    created_at = datetime.now(timezone.utc)
    path = output_dir / f"ctg-{created_at:%Y%m%dT%H%M%SZ}.dump"
    runner(
        ["pg_dump", "--format=custom", "--no-owner", "--file", str(path), database_url],
        check=True, capture_output=True, text=True,
    )
    return BackupResult(path, hashlib.sha256(path.read_bytes()).hexdigest(), created_at)


PHASES = {
    "foundation": _upgrade_foundation,
    "accounts": _upgrade_accounts,
    "community": _upgrade_community,
    "chat": _upgrade_chat,
    "broadcast": _upgrade_broadcast,
}
```

The CLI accepts `--dry-run` and `--phase foundation|accounts|community|chat|broadcast|all`, prints action/count data, and never prints `DATABASE_URL`.

- [ ] **Step 4: Verify GREEN and regression**

```bash
PYTHONPATH=backend backend/venv/bin/python -m pytest -q backend/tests/test_database_backup.py backend/tests/test_social_platform_migration.py
PYTHONPATH=backend backend/venv/bin/python -m pytest -q backend/tests
backend/venv/bin/python -m compileall -q backend/app
cd frontend && npm run build
```

Expected: new tests, full baseline, compileall and build exit 0.

- [ ] **Step 5: Update handover and commit**

Document `backend/backups/` as Git-ignored runtime data and record exact verification counts.

```bash
git add backend/app/services/database_backup.py backend/app/migrations/social_platform.py backend/app/migrations/__init__.py backend/tests/test_database_backup.py backend/tests/test_social_platform_migration.py HANDOVER.md
git commit -m "feat: add safe social platform migration runner"
```

### Task 2: 汤底公开展开与人物文本字段

**Files:**
- Modify: `backend/app/models/models.py`
- Modify: `backend/app/schemas/soups.py`
- Modify: `backend/app/api/turtle_soups.py`
- Modify: `backend/app/migrations/social_platform.py`
- Modify: `backend/tests/test_soup_api_security.py`
- Modify: `backend/tests/test_soup_metadata_api.py`
- Modify: `backend/tests/test_social_platform_migration.py`
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/views/SoupCreateView.vue`
- Modify: `frontend/src/views/SoupDetailView.vue`
- Modify: `HANDOVER.md`

**Interfaces:**
- Changes `Soup.main_player_count: str` and `secondary_player_count: str`。
- Changes `SoupCreate`/`SoupUpdate` to require both string keys without content validators.
- Keeps `GET /api/turtle-soups/{soup_id}?reveal=false` returning `solution: null` and allows anonymous `reveal=true` for published soups.
- Extends migration `phase="foundation"` with PostgreSQL/SQLite integer-to-TEXT conversion.

- [ ] **Step 1: Write failing API and migration tests**

```python
def test_published_soup_is_hidden_initially_and_anonymous_can_reveal(client, published_soup):
    hidden = client.get(f"/api/turtle-soups/{published_soup.id}")
    revealed = client.get(f"/api/turtle-soups/{published_soup.id}?reveal=true")
    assert hidden.json()["solution"] is None
    assert revealed.status_code == 200
    assert revealed.json()["solution"] == published_soup.solution


@pytest.mark.parametrize("main,secondary", [
    ("一群人", "影子和一只猫"), ("", ""), ("👩‍🚀/AI", "不确定"),
])
def test_soup_people_fields_accept_arbitrary_text(auth_client, soup_payload, main, secondary):
    response = auth_client.post("/api/turtle-soups", json={
        **soup_payload,
        "main_player_count": main,
        "secondary_player_count": secondary,
    })
    assert response.status_code == 201
    assert response.json()["main_player_count"] == main
```

Migration test creates legacy integer values `2`/`0`, applies the phase, and asserts reflected TEXT columns with values `"2"`/`"0"`.

- [ ] **Step 2: Run focused tests and confirm RED**

Run: `PYTHONPATH=backend backend/venv/bin/python -m pytest -q backend/tests/test_soup_api_security.py backend/tests/test_soup_metadata_api.py backend/tests/test_social_platform_migration.py`
Expected: anonymous reveal or string validation and migration assertions fail.

- [ ] **Step 3: Implement model, route, migration and frontend**

```python
class Soup(SQLModel, table=True):
    main_player_count: str = Field(default="", sa_column=Column(Text, nullable=False))
    secondary_player_count: str = Field(default="", sa_column=Column(Text, nullable=False))


def _can_reveal_solution(soup: Soup, reveal: bool) -> bool:
    return reveal and soup.status in {SoupStatus.PUBLISHED, SoupStatus.REVEALED}
```

PostgreSQL uses:

```sql
ALTER TABLE soups
  ALTER COLUMN main_player_count TYPE TEXT USING main_player_count::text,
  ALTER COLUMN secondary_player_count TYPE TEXT USING secondary_player_count::text;
```

SQLite uses temporary TEXT columns, `CAST(main_player_count AS TEXT)`, `CAST(secondary_player_count AS TEXT)`, drop and rename in one transaction. The Vue form removes `type="number"`, `v-model.number`, `min` and `max`. Detail adds `revealing`/`revealError` and prevents overlapping requests.

- [ ] **Step 4: Verify API, migration and frontend**

```bash
PYTHONPATH=backend backend/venv/bin/python -m pytest -q backend/tests/test_soup_api_security.py backend/tests/test_soup_metadata_api.py backend/tests/test_social_platform_migration.py
PYTHONPATH=backend backend/venv/bin/python -m pytest -q backend/tests
cd frontend && npm run build
cd frontend && npx playwright test tests/e2e/responsive-smoke.spec.ts --grep "soup"
cd backend && PYTHONPATH=. venv/bin/python -m app.migrations.social_platform --phase foundation --dry-run
cd backend && PYTHONPATH=. venv/bin/python -m app.services.database_backup
cd backend && PYTHONPATH=. venv/bin/python -m app.migrations.social_platform --phase foundation
```

Expected: all commands exit 0, three viewports show text inputs plus hidden-then-expanded solution, and reflected PostgreSQL people columns are TEXT.

- [ ] **Step 5: Update handover and commit**

Record public reveal, backup checksum, applied TEXT migration and verification counts.

```bash
git add backend/app backend/tests frontend/src frontend/tests/e2e/responsive-smoke.spec.ts HANDOVER.md
git commit -m "fix: reveal soup solutions and accept text people fields"
```

### Task 3: 根用户、幂等邮箱验证与公开链接

**Files:**
- Modify: `backend/app/core/config.py`
- Modify: `backend/.env.example`
- Modify: `backend/app/api/auth.py`
- Modify: `backend/app/utils/email.py`
- Modify: `backend/app/migrations/social_platform.py`
- Modify: `backend/tests/test_auth_security.py`
- Modify: `backend/tests/test_email_verification.py`
- Modify: `backend/tests/test_email_connection.py`
- Modify: `backend/tests/test_social_platform_migration.py`
- Modify: `frontend/src/views/VerifyEmailView.vue`
- Modify: `HANDOVER.md`

**Interfaces:**
- Produces `Settings.PUBLIC_WEB_URL` and `Settings.public_web_url: str` with legacy `APP_URL` fallback.
- Makes `POST /api/auth/verify-email` idempotent for an already-used token whose user is active.
- Promotes exact username `SkyUnreal` to `root` in `phase="foundation"`.

- [ ] **Step 1: Write failing verification, URL and role tests**

```python
def test_used_token_for_active_user_is_idempotent(client, pending_user, token):
    assert client.post("/api/auth/verify-email", json={"token": token}).status_code == 200
    second = client.post("/api/auth/verify-email", json={"token": token})
    assert second.status_code == 200
    assert second.json()["message"] == "邮箱已验证"


def test_email_link_uses_public_web_url(monkeypatch):
    monkeypatch.setattr(email_module.settings, "PUBLIC_WEB_URL", "https://ctg.example")
    html = capture_verification_html("token-value-at-least-32-characters")
    assert 'href="https://ctg.example/verify-email?token=' in html
    assert "localhost:10000" not in html


def test_foundation_migration_promotes_only_exact_skyunreal(legacy_engine):
    report = upgrade_social_platform(legacy_engine, phase="foundation")
    assert fetch_role(legacy_engine, "SkyUnreal") == "root"
    assert fetch_role(legacy_engine, "skyunreal") == "user"
    assert report.counts["promoted_root_users"] == 1
```

```python
def test_unused_expired_and_unknown_tokens_have_distinct_codes(client, expired_token):
    expired = client.post("/api/auth/verify-email", json={"token": expired_token})
    unknown = client.post("/api/auth/verify-email", json={"token": "x" * 40})
    assert expired.json()["detail"]["code"] == "VERIFICATION_EXPIRED"
    assert unknown.json()["detail"]["code"] == "VERIFICATION_INVALID"
```

- [ ] **Step 2: Run focused tests and confirm RED**

Run: `PYTHONPATH=backend backend/venv/bin/python -m pytest -q backend/tests/test_auth_security.py backend/tests/test_email_verification.py backend/tests/test_email_connection.py backend/tests/test_social_platform_migration.py`
Expected: second verification returns 400, URL/root migration assertions fail.

- [ ] **Step 3: Implement transaction-safe idempotence and configuration**

```python
class Settings(BaseSettings):
    PUBLIC_WEB_URL: Optional[str] = None

    @property
    def public_web_url(self) -> str:
        value = (self.PUBLIC_WEB_URL or self.APP_URL or "http://localhost:10000").rstrip("/")
        if not value.startswith(("http://", "https://")):
            raise ValueError("PUBLIC_WEB_URL must be an absolute HTTP(S) URL")
        return value


verification = db.exec(
    select(EmailVerification)
    .where(EmailVerification.token_hash == hash_verification_token(request.token))
    .with_for_update()
).first()
if verification is None:
    raise HTTPException(
        status_code=400,
        detail={"code": "VERIFICATION_INVALID", "message": "验证链接无效"},
    )
user = db.get(User, verification.user_uid)
if verification.used_at is not None and user and user.status == UserStatus.ACTIVE:
    return {"message": "邮箱已验证"}
if verification.expires_at < utc_now_naive():
    raise HTTPException(
        status_code=400,
        detail={"code": "VERIFICATION_EXPIRED", "message": "验证链接已过期，请重新发送"},
    )
```

Use `settings.public_web_url` for verification/reset links. The Vue page caches one in-flight promise per token and ignores errors after `verified`.

- [ ] **Step 4: Verify, back up and migrate the real database**

```bash
PYTHONPATH=backend backend/venv/bin/python -m pytest -q backend/tests/test_auth_security.py backend/tests/test_email_verification.py backend/tests/test_email_connection.py backend/tests/test_social_platform_migration.py
PYTHONPATH=backend backend/venv/bin/python -m pytest -q backend/tests
cd frontend && npm run build
cd backend && PYTHONPATH=. venv/bin/python -m app.migrations.social_platform --phase foundation --dry-run
cd backend && PYTHONPATH=. venv/bin/python -m app.services.database_backup
cd backend && PYTHONPATH=. venv/bin/python -m app.migrations.social_platform --phase foundation
```

Expected: backup prints path/SHA without URL; migration succeeds; read-only `uid,username,role` query shows SkyUnreal=root. Do not send real email.

- [ ] **Step 5: Update handover and commit**

Record backup checksum, migration counts, root UID/role and `PUBLIC_WEB_URL` without database credentials.

```bash
git add backend/app backend/.env.example backend/tests frontend/src/views/VerifyEmailView.vue HANDOVER.md
git commit -m "fix: make email verification idempotent and promote root user"
```

### Task 4: 搜索契约与部分失败容错

**Files:**
- Modify: `backend/app/api/search.py`
- Modify: `backend/app/schemas/community.py`
- Modify: `backend/tests/test_community_contract.py`
- Create: `frontend/src/api/search.ts`
- Rewrite: `frontend/src/views/SearchView.vue`
- Modify: `frontend/src/components/NavBar.vue`
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/tests/e2e/responsive-smoke.spec.ts`
- Modify: `HANDOVER.md`

**Interfaces:**
- Produces typed `searchApi.users/posts/soups(query, page, pageSize)`.
- Uses post `excerpt` and soup `puzzle_excerpt` consistently.
- Produces `SearchSectionState<T> = {items, loading, error}` for independent failures.

- [ ] **Step 1: Write failing pagination and browser tests**

```python
def test_search_pages_in_database_and_returns_summary_fields(client, seeded_search_data):
    response = client.get("/api/search/turtle-soups?q=月&page=2&page_size=1")
    body = response.json()
    assert response.status_code == 200
    assert body["total"] == 2
    assert body["page"] == 2
    assert "puzzle_excerpt" in body["items"][0]
    assert "puzzle" not in body["items"][0]
```

Playwright mocks users/soups as 200 and posts as 503, then asserts successful sections remain and only posts shows “重新加载”.

- [ ] **Step 2: Run focused tests and confirm RED**

```bash
PYTHONPATH=backend backend/venv/bin/python -m pytest -q backend/tests/test_community_contract.py -k search
cd frontend && npx playwright test tests/e2e/responsive-smoke.spec.ts --grep "search"
```

Expected: frontend whole-search error hides successful results.

- [ ] **Step 3: Implement SQL paging and allSettled UI**

```typescript
export interface SearchSectionState<T> {
  items: T[]
  loading: boolean
  error: string
}

const results = await Promise.allSettled(requestedKinds.map(loadKind))
results.forEach((result, index) => {
  const section = sections[requestedKinds[index]]
  if (result.status === 'fulfilled') section.items = result.value.data.items
  else section.error = extractApiError(result.reason, '该分类搜索失败')
  section.loading = false
})
```

Backend uses `select(func.count())`, `offset`, `limit` and stable order; no Python slicing. Render `excerpt`/`puzzle_excerpt`.

- [ ] **Step 4: Verify search and regression**

```bash
PYTHONPATH=backend backend/venv/bin/python -m pytest -q backend/tests/test_community_contract.py
PYTHONPATH=backend backend/venv/bin/python -m pytest -q backend/tests
cd frontend && npm run build
cd frontend && npx playwright test tests/e2e/responsive-smoke.spec.ts --grep "search"
```

- [ ] **Step 5: Update handover and commit**

```bash
git add backend/app/api/search.py backend/app/schemas/community.py backend/tests/test_community_contract.py frontend/src frontend/tests/e2e/responsive-smoke.spec.ts HANDOVER.md
git commit -m "fix: restore typed resilient community search"
```

### Task 5: 用户设置、头像、密码与主题

**Files:**
- Modify: `backend/app/models/models.py`
- Modify: `backend/app/models/database.py`
- Modify: `backend/app/schemas/__init__.py`
- Modify: `backend/app/api/auth.py`
- Modify: `backend/app/api/users.py`
- Modify: `backend/app/api/uploads.py`
- Modify: `backend/app/migrations/social_platform.py`
- Create: `backend/tests/test_account_settings.py`
- Modify: `backend/tests/test_auth_security.py`
- Modify: `frontend/src/api/auth.ts`
- Modify: `frontend/src/api/upload.ts`
- Modify: `frontend/src/stores/auth.ts`
- Create: `frontend/src/utils/theme.ts`
- Modify: `frontend/src/main.ts`
- Rewrite: `frontend/src/views/SettingsView.vue`
- Modify: `HANDOVER.md`

**Interfaces:**
- Adds `User.allow_bulk_email: bool`, `theme_preference: ThemePreference`, `token_version: int` and `avatar_asset_id: Optional[int]`.
- Adds `UploadedAsset(id, owner_uid, kind, storage_key, public_url, mime_type, size, created_at)`.
- Produces `PUT /api/auth/change-password` and `PUT /api/users/me/preferences`.
- Produces `applyTheme("light"|"dark"|"system")` before Vue mount.

- [ ] **Step 1: Write failing settings and token-version tests**

```python
def test_change_password_invalidates_existing_tokens(client, active_user):
    access, refresh = login(client, active_user.username, "OldPassword1")
    changed = client.put("/api/auth/change-password", headers=bearer(access), json={
        "old_password": "OldPassword1", "new_password": "NewPassword2",
    })
    assert changed.status_code == 200
    assert client.get("/api/auth/me", headers=bearer(access)).status_code == 401
    assert client.post("/api/auth/refresh", json={"refresh_token": refresh}).status_code == 401


def test_user_cannot_select_another_users_avatar(client, user_a, asset_b):
    response = client.put("/api/users/me", headers=as_user(user_a), json={
        "avatar_asset_id": asset_b.id,
    })
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "AVATAR_NOT_OWNED"
```

```python
def test_new_user_defaults_to_system_theme_and_bulk_email_opt_out(session):
    user = User(
        username="defaults-user", nickname="Defaults",
        email="defaults@example.com", hashed_password="unused",
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    assert user.allow_bulk_email is False
    assert user.theme_preference == ThemePreference.SYSTEM
    assert user.token_version == 0
```

- [ ] **Step 2: Run focused tests and confirm RED**

Run: `PYTHONPATH=backend backend/venv/bin/python -m pytest -q backend/tests/test_account_settings.py backend/tests/test_auth_security.py`
Expected: columns/endpoints are absent and JWTs do not carry `ver`.

- [ ] **Step 3: Implement account fields, owned uploads and UI**

```python
class ThemePreference(str, Enum):
    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"


class User(SQLModel, table=True):
    allow_bulk_email: bool = Field(default=False, index=True)
    theme_preference: ThemePreference = Field(default=ThemePreference.SYSTEM)
    token_version: int = Field(default=0)
    avatar_asset_id: Optional[int] = Field(default=None, foreign_key="uploaded_assets.id")
```

JWTs include `"ver": user.token_version` and resolution rejects mismatches. Image upload inserts `UploadedAsset` and returns `asset_id`. The settings page has Profile/Security/Notifications/Appearance tabs, owned avatar selection, password form, bulk-email toggle and a three-option theme segmented control.

- [ ] **Step 4: Verify account flows, migration and build**

```bash
PYTHONPATH=backend backend/venv/bin/python -m pytest -q backend/tests/test_account_settings.py backend/tests/test_auth_security.py backend/tests/test_upload_rules.py
PYTHONPATH=backend backend/venv/bin/python -m pytest -q backend/tests
cd frontend && npm run build
cd backend && PYTHONPATH=. venv/bin/python -m app.migrations.social_platform --phase accounts --dry-run
cd backend && PYTHONPATH=. venv/bin/python -m app.services.database_backup
cd backend && PYTHONPATH=. venv/bin/python -m app.migrations.social_platform --phase accounts
```

Expected: tests/build pass, the phase applies after backup, and read-only inspection finds defaults plus `uploaded_assets`.

- [ ] **Step 5: Update handover and commit**

Document theme precedence, avatar ownership, token invalidation and default opt-out.

```bash
git add backend/app frontend/src backend/tests/test_account_settings.py backend/tests/test_auth_security.py HANDOVER.md
git commit -m "feat: add social account settings and themes"
```

### Task 6: UID 个人主页与五个代表作

**Files:**
- Modify: `backend/app/models/models.py`
- Modify: `backend/app/models/database.py`
- Create: `backend/app/services/levels.py`
- Create: `backend/app/schemas/profiles.py`
- Rewrite: `backend/app/api/users.py`
- Modify: `backend/app/migrations/social_platform.py`
- Create: `backend/tests/test_profile_contract.py`
- Create: `backend/tests/test_levels.py`
- Modify: `frontend/src/types/index.ts`
- Create: `frontend/src/api/profile.ts`
- Rewrite: `frontend/src/views/ProfileView.vue`
- Modify: `frontend/src/router/index.ts`
- Modify: `HANDOVER.md`

**Interfaces:**
- Adds `FeaturedSoup(user_uid, soup_id, position)` with unique user/soup and user/position keys.
- Produces `level_progress(points: int) -> LevelProgress` for profile and later sign-in responses.
- Produces `GET /api/users/{uid}/profile?page=1&page_size=20` returning `PublicProfileResponse`.
- Produces `PUT /api/users/me/featured-soups` with `{"soup_ids": number[]}`.

- [ ] **Step 1: Write failing privacy, ordering and pin tests**

```python
def test_public_profile_hides_private_fields_and_orders_soups(client, user, soups):
    response = client.get(f"/api/users/{user.uid}/profile")
    body = response.json()
    assert body["user"]["uid"] == user.uid
    assert "email" not in body["user"]
    assert "allow_bulk_email" not in body["user"]
    assert [item["id"] for item in body["soups"]["items"]] == [soups[1].id, soups[0].id]


def test_featured_soups_are_owned_published_and_at_most_five(auth_client, six_soup_ids):
    response = auth_client.put("/api/users/me/featured-soups", json={"soup_ids": six_soup_ids})
    assert response.status_code == 422


@pytest.mark.parametrize("points,level", [(0, 1), (99, 1), (100, 2), (400, 3), (980100, 100)])
def test_level_formula(points, level):
    assert level_progress(points).level == level
```

- [ ] **Step 2: Run focused tests and confirm RED**

Run: `PYTHONPATH=backend backend/venv/bin/python -m pytest -q backend/tests/test_profile_contract.py backend/tests/test_levels.py`
Expected: profile model/route and level service are missing, while the legacy profile still accesses stale fields.

- [ ] **Step 3: Implement canonical profile response and page**

```python
class PublicProfileUser(BaseModel):
    uid: int
    username: str
    nickname: str
    avatar_url: str | None
    bio: str | None
    role: UserRole
    level: int
    experience_points: int
    created_at: datetime


class FeaturedSoupInput(BaseModel):
    soup_ids: list[int] = Field(max_length=5)


def level_progress(points: int) -> LevelProgress:
    normalized = max(points, 0)
    level = min(100, 1 + math.isqrt(normalized // 100))
    start = 100 * (level - 1) ** 2
    next_start = None if level == 100 else 100 * level ** 2
    return LevelProgress(level, normalized, start, next_start)
```

Delete the broken legacy `/{user_id}/profile` implementation. Fixed `/me` routes stay before `/{uid}/profile`. Vue renders UID, level, self edit action, other-user follow/message actions, ordered representatives and newest-first paged soups.

- [ ] **Step 4: Verify profile API and responsive page**

```bash
PYTHONPATH=backend backend/venv/bin/python -m pytest -q backend/tests/test_profile_contract.py backend/tests/test_levels.py backend/tests/test_user_routes.py
PYTHONPATH=backend backend/venv/bin/python -m pytest -q backend/tests
cd frontend && npm run build
cd frontend && npx playwright test tests/e2e/responsive-smoke.spec.ts --grep "profile"
cd backend && PYTHONPATH=. venv/bin/python -m app.migrations.social_platform --phase community --dry-run
cd backend && PYTHONPATH=. venv/bin/python -m app.services.database_backup
cd backend && PYTHONPATH=. venv/bin/python -m app.migrations.social_platform --phase community
```

Expected: privacy assertions and five-item layout pass at 375/768/1440; `featured_soups` exists with both unique keys.

- [ ] **Step 5: Update handover and commit**

```bash
git add backend/app frontend/src backend/tests/test_profile_contract.py backend/tests/test_levels.py frontend/tests/e2e/responsive-smoke.spec.ts HANDOVER.md
git commit -m "feat: add uid profiles and featured soups"
```

### Task 7: 每日签到与等级

**Files:**
- Modify: `backend/app/models/models.py`
- Modify: `backend/app/core/config.py`
- Modify: `backend/.env.example`
- Modify: `backend/app/services/levels.py`
- Create: `backend/app/schemas/levels.py`
- Modify: `backend/app/api/users.py`
- Modify: `backend/app/migrations/social_platform.py`
- Create: `backend/tests/test_levels_and_signin.py`
- Create: `frontend/src/components/SigninControl.vue`
- Modify: `frontend/src/components/NavBar.vue`
- Modify: `frontend/src/views/ProfileView.vue`
- Modify: `frontend/src/types/index.ts`
- Modify: `HANDOVER.md`

**Interfaces:**
- Consumes `level_progress(points: int) -> LevelProgress` from Task 6.
- Produces `signin_day(now: datetime, timezone_name: str) -> date` and `signin_reward(streak: int) -> int`.
- Adds unique `SigninRecord(user_uid, signin_day)`.
- Produces `GET/POST /api/users/me/signin`.
- Adds `Settings.SIGNIN_TIMEZONE: str = "Asia/Shanghai"` and validates it with `zoneinfo.ZoneInfo` at startup.

- [ ] **Step 1: Write failing formula and duplicate tests**

```python
def test_signin_reward_caps_streak_bonus_at_seven():
    assert signin_reward(1) == 11
    assert signin_reward(7) == 17
    assert signin_reward(30) == 17


def test_signin_day_uses_configured_timezone():
    now = datetime(2026, 8, 8, 16, 30, tzinfo=timezone.utc)
    assert signin_day(now, "Asia/Shanghai") == date(2026, 8, 9)


def test_signin_rejects_same_business_day(client, user, monkeypatch):
    monkeypatch.setattr(
        levels, "utc_now",
        lambda: datetime(2026, 8, 8, 16, 30, tzinfo=timezone.utc),
    )
    first = client.post("/api/users/me/signin", headers=as_user(user))
    second = client.post("/api/users/me/signin", headers=as_user(user))
    assert first.json()["experience_gained"] == 11
    assert second.status_code == 409
    assert second.json()["detail"]["code"] == "ALREADY_SIGNED_IN"
```

```python
def test_concurrent_signin_increments_points_once(client_factory, shared_engine, user):
    def sign_in():
        with client_factory(shared_engine) as client:
            return client.post("/api/users/me/signin", headers=as_user(user)).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = sorted(pool.map(lambda _: sign_in(), range(2)))
    assert statuses == [200, 409]
    with Session(shared_engine) as session:
        refreshed = session.get(User, user.uid)
        assert refreshed.points == 11
        assert len(session.exec(select(SigninRecord)).all()) == 1
```

- [ ] **Step 2: Run focused tests and confirm RED**

Run: `PYTHONPATH=backend backend/venv/bin/python -m pytest -q backend/tests/test_levels_and_signin.py`
Expected: service/schema missing and old route lacks unique record protection.

- [ ] **Step 3: Implement pure rules and transactional sign-in**

```python
def signin_reward(streak: int) -> int:
    return 10 + min(max(streak, 1), 7)


def signin_day(now: datetime, timezone_name: str) -> date:
    return now.astimezone(ZoneInfo(timezone_name)).date()
```

Catch `uq_signin_user_day` IntegrityError and return structured 409. UI uses a stable-width control showing level, progress and streak.

- [ ] **Step 4: Verify levels, migration and frontend**

```bash
PYTHONPATH=backend backend/venv/bin/python -m pytest -q backend/tests/test_levels_and_signin.py
PYTHONPATH=backend backend/venv/bin/python -m pytest -q backend/tests
cd frontend && npm run build
cd backend && PYTHONPATH=. venv/bin/python -m app.migrations.social_platform --phase community --dry-run
cd backend && PYTHONPATH=. venv/bin/python -m app.services.database_backup
cd backend && PYTHONPATH=. venv/bin/python -m app.migrations.social_platform --phase community
```

- [ ] **Step 5: Update handover and commit**

```bash
git add backend/app frontend/src backend/tests/test_levels_and_signin.py HANDOVER.md
git commit -m "feat: add daily sign-in and user levels"
```

### Task 8: 帖子/评论 @ 提及与安全主页链接

**Files:**
- Modify: `backend/app/models/models.py`
- Modify: `backend/app/models/database.py`
- Create: `backend/app/services/mentions.py`
- Modify: `backend/app/schemas/community.py`
- Modify: `backend/app/api/posts.py`
- Modify: `backend/app/api/turtle_soups.py`
- Modify: `backend/app/api/notifications.py`
- Modify: `backend/app/migrations/social_platform.py`
- Create: `backend/tests/test_mentions.py`
- Create: `backend/tests/test_post_comments.py`
- Create: `frontend/src/components/MentionText.vue`
- Modify: `frontend/src/views/PostDetailView.vue`
- Modify: `frontend/src/views/SoupDetailView.vue`
- Modify: `frontend/src/views/NotificationView.vue`
- Modify: `frontend/src/types/index.ts`
- Modify: `HANDOVER.md`

**Interfaces:**
- Adds `Mention(actor_uid, mentioned_uid, target_type, target_id, start_offset, end_offset)`.
- Produces `parse_mentions(text: str) -> list[ParsedMention]` and `sync_mentions(db: Session, actor_uid: int, target_type: MentionTargetType, target_id: int, text: str) -> list[MentionRef]`.
- Adds `GET/POST /api/posts/{post_id}/comments`.
- Adds `mentions: MentionRef[]` to post/comment responses.

- [ ] **Step 1: Write failing parser, notification and XSS tests**

```python
def test_mentions_require_whitespace_boundary():
    assert [m.username for m in parse_mentions("@G先生 所提供的内容")] == ["G先生"]
    assert parse_mentions("abc@G先生 内容") == []


def test_connected_punctuation_does_not_resolve_to_g_user(db, users, post):
    refs = sync_mentions(db, users.actor.uid, "post", post.id, "@G先生，内容")
    assert refs == []


def test_mentions_are_deduplicated_and_diffed(db, users, post):
    refs = sync_mentions(db, users.actor.uid, "post", post.id, "@G先生 你好 @G先生 ")
    assert [ref.uid for ref in refs] == [users.mentioned.uid]
    assert count_notifications(db, users.mentioned.uid, "mention") == 1
    assert sync_mentions(db, users.actor.uid, "post", post.id, "不再提及") == []
```

```typescript
test('mention-like HTML remains inert text', async ({ page }) => {
  await loginAsOrdinaryUser(page)
  await page.goto('/posts/1')
  await page.getByLabel('评论内容').fill('@<img src=x onerror=alert(1)> ')
  await page.getByRole('button', { name: '发表评论' }).click()
  await expect(page.getByText('@<img src=x onerror=alert(1)>')).toBeVisible()
  await expect(page.locator('article img[src="x"]')).toHaveCount(0)
  await expect(page.locator('script')).toHaveCount(0)
})
```

- [ ] **Step 2: Run focused tests and confirm RED**

```bash
PYTHONPATH=backend backend/venv/bin/python -m pytest -q backend/tests/test_mentions.py backend/tests/test_post_comments.py
cd frontend && npx playwright test tests/e2e/responsive-smoke.spec.ts --grep "mention"
```

Expected: services/routes/components missing.

- [ ] **Step 3: Implement transactional mention spans**

```python
MENTION_RE = re.compile(r"(?<!\\S)@([^\\s@]+)(?=\\s|$)")


def parse_mentions(text: str) -> list[ParsedMention]:
    return [
        ParsedMention(match.group(1), match.start(), match.end())
        for match in MENTION_RE.finditer(text)
    ]
```

Resolve usernames in one query, de-duplicate UIDs, diff rows, skip self and create notifications in the content transaction. `MentionText.vue` uses text nodes and `RouterLink` slices, never `v-html`.

- [ ] **Step 4: Verify mention flows and browser safety**

```bash
PYTHONPATH=backend backend/venv/bin/python -m pytest -q backend/tests/test_mentions.py backend/tests/test_post_comments.py backend/tests/test_notification_contract.py
PYTHONPATH=backend backend/venv/bin/python -m pytest -q backend/tests
cd frontend && npm run build
cd frontend && npx playwright test tests/e2e/responsive-smoke.spec.ts --grep "mention"
cd backend && PYTHONPATH=. venv/bin/python -m app.migrations.social_platform --phase community --dry-run
cd backend && PYTHONPATH=. venv/bin/python -m app.services.database_backup
cd backend && PYTHONPATH=. venv/bin/python -m app.migrations.social_platform --phase community
```

- [ ] **Step 5: Update handover and commit**

```bash
git add backend/app frontend/src backend/tests/test_mentions.py backend/tests/test_post_comments.py frontend/tests/e2e/responsive-smoke.spec.ts HANDOVER.md
git commit -m "feat: add profile-linked mention notifications"
```

### Task 9: 私信会话模型、HTTP API 与旧消息迁移

**Files:**
- Modify: `backend/app/models/models.py`
- Modify: `backend/app/models/database.py`
- Create: `backend/app/schemas/chat.py`
- Rewrite: `backend/app/api/messages.py`
- Modify: `backend/app/migrations/social_platform.py`
- Create: `backend/tests/test_chat_contract.py`
- Modify: `backend/tests/test_social_platform_migration.py`
- Create: `frontend/src/api/chat.ts`
- Modify: `frontend/src/types/index.ts`
- Modify: `HANDOVER.md`

**Interfaces:**
- Adds `DirectConversation(id, low_uid, high_uid, last_message_at, created_at)` unique on `(low_uid, high_uid)`.
- Adds `PrivateMessage.conversation_id` while preserving all old message data.
- Produces conversation list/create, cursor message history/send and read endpoints under `/api/messages/conversations`.

- [ ] **Step 1: Write failing canonical, block and migration tests**

```python
def test_get_or_create_conversation_is_canonical(client, alice, bob):
    first = client.post("/api/messages/conversations", headers=as_user(alice), json={"user_uid": bob.uid})
    second = client.post("/api/messages/conversations", headers=as_user(bob), json={"user_uid": alice.uid})
    assert first.json()["id"] == second.json()["id"]


def test_blocked_users_keep_history_but_cannot_send(client, blocked_conversation):
    url = f"/api/messages/conversations/{blocked_conversation.id}/messages"
    assert client.get(url, headers=blocked_conversation.alice_header).status_code == 200
    sent = client.post(url, headers=blocked_conversation.alice_header, json={"content": "hello"})
    assert sent.status_code == 403
    assert sent.json()["detail"]["code"] == "MESSAGE_BLOCKED"
```

```python
def test_chat_migration_groups_both_directions_and_preserves_messages(legacy_engine):
    first_id = insert_legacy_message(legacy_engine, sender_uid=1, receiver_uid=2, content="a")
    second_id = insert_legacy_message(legacy_engine, sender_uid=2, receiver_uid=1, content="b")
    upgrade_social_platform(legacy_engine, phase="chat")
    conversations = fetch_rows(legacy_engine, "direct_conversations")
    messages = fetch_rows(legacy_engine, "private_messages")
    assert [(row["low_uid"], row["high_uid"]) for row in conversations] == [(1, 2)]
    assert {row["id"] for row in messages} == {first_id, second_id}
    assert {row["conversation_id"] for row in messages} == {conversations[0]["id"]}
```

- [ ] **Step 2: Run focused tests and confirm RED**

Run: `PYTHONPATH=backend backend/venv/bin/python -m pytest -q backend/tests/test_chat_contract.py backend/tests/test_social_platform_migration.py`
Expected: conversation model/routes absent.

- [ ] **Step 3: Implement canonical pair and cursor API**

```python
def canonical_pair(first_uid: int, second_uid: int) -> tuple[int, int]:
    if first_uid == second_uid:
        raise ValueError("cannot create a direct conversation with self")
    return min(first_uid, second_uid), max(first_uid, second_uid)


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
```

Use unique-key retry for concurrent creation. Every query verifies membership. Message send derives receiver from the pair and never trusts client receiver data.

- [ ] **Step 4: Verify HTTP API, migration and regression**

```bash
PYTHONPATH=backend backend/venv/bin/python -m pytest -q backend/tests/test_chat_contract.py backend/tests/test_social_platform_migration.py
PYTHONPATH=backend backend/venv/bin/python -m pytest -q backend/tests
cd frontend && npm run build
cd backend && PYTHONPATH=. venv/bin/python -m app.migrations.social_platform --phase chat --dry-run
cd backend && PYTHONPATH=. venv/bin/python -m app.services.database_backup
cd backend && PYTHONPATH=. venv/bin/python -m app.migrations.social_platform --phase chat
```

- [ ] **Step 5: Update handover and commit**

```bash
git add backend/app frontend/src/api/chat.ts frontend/src/types/index.ts backend/tests/test_chat_contract.py backend/tests/test_social_platform_migration.py HANDOVER.md
git commit -m "feat: migrate private messages to conversations"
```

### Task 10: WebSocket 输入状态、Emoji 与 QQ 式聊天

**Files:**
- Create: `backend/app/services/message_gateway.py`
- Create: `backend/app/api/message_socket.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/services/dependency_health.py`
- Create: `backend/tests/test_message_socket.py`
- Create: `frontend/src/stores/chat.ts`
- Create: `frontend/src/components/EmojiPicker.vue`
- Rewrite: `frontend/src/views/MessageView.vue`
- Modify: `frontend/src/router/index.ts`
- Create: `frontend/tests/e2e/chat.spec.ts`
- Modify: `HANDOVER.md`

**Interfaces:**
- Produces WebSocket `/ws/messages` with first-frame auth within 5 seconds.
- Supports `message.created`, `message.read`, `typing.start`, `typing.stop` and `presence.error`.
- Produces `ChatStore.connect/openConversation/sendMessage/setTyping`.
- Polls the active conversation every 5 seconds if WebSocket is unavailable.

- [ ] **Step 1: Write failing socket and typing-expiry tests**

```python
def test_socket_requires_auth_as_first_frame(socket_client):
    with socket_client.websocket_connect("/ws/messages") as ws:
        ws.send_json({"type": "typing.start", "conversation_id": 1})
        assert ws.receive_json()["code"] == "WS_AUTH_REQUIRED"


def test_typing_reaches_only_other_member_and_expires(chat_socket_pair, clock):
    alice, bob = chat_socket_pair
    alice.send_json({"type": "typing.start", "conversation_id": 7})
    assert bob.receive_json()["type"] == "typing.start"
    clock.advance(seconds=6)
    assert bob.receive_json()["type"] == "typing.stop"
```

```typescript
test('chat sends emoji and displays remote typing', async ({ page }) => {
  await loginAsOrdinaryUser(page)
  await page.goto('/messages')
  await page.getByRole('button', { name: '打开表情' }).click()
  await page.getByRole('button', { name: '😀' }).click()
  await expect(page.getByLabel('消息内容')).toHaveValue('😀')
  await mockRemoteTyping(page, 7)
  await expect(page.getByText('正在输入…')).toBeVisible()
  await page.getByRole('button', { name: '发送' }).click()
  await expect(page.getByTestId('outgoing-message').last()).toContainText('😀')
})
```

- [ ] **Step 2: Run focused tests and confirm RED**

```bash
PYTHONPATH=backend backend/venv/bin/python -m pytest -q backend/tests/test_message_socket.py
cd frontend && npx playwright test tests/e2e/chat.spec.ts
```

Expected: socket route/store/UI missing.

- [ ] **Step 3: Implement authenticated gateway and chat UI**

```typescript
type ClientEvent =
  | { type: 'auth'; token: string }
  | { type: 'typing.start' | 'typing.stop'; conversation_id: number }
  | { type: 'message.read'; conversation_id: number; message_id: number }

const emojiGroups = {
  常用: ['😀', '😂', '🥹', '😊', '😍', '🤔', '😭', '😡'],
  手势: ['👍', '👎', '👏', '🙏', '👌', '✌️', '🤝', '💪'],
  符号: ['❤️', '💔', '✨', '🎉', '🔥', '💡', '✅', '❓'],
}
```

Close unauthenticated sockets after 5 seconds; validate conversation membership for every event. Typing is ephemeral. Use Redis Pub/Sub when available and an in-memory manager otherwise. Replace inbox/sent UI with a stable desktop two-column layout and mobile conversation/detail switch.

- [ ] **Step 4: Verify socket, fallback, build and viewports**

```bash
PYTHONPATH=backend backend/venv/bin/python -m pytest -q backend/tests/test_message_socket.py backend/tests/test_chat_contract.py
PYTHONPATH=backend backend/venv/bin/python -m pytest -q backend/tests
cd frontend && npm run build
cd frontend && npx playwright test tests/e2e/chat.spec.ts
```

- [ ] **Step 5: Update handover and commit**

```bash
git add backend/app frontend/src frontend/tests/e2e/chat.spec.ts backend/tests/test_message_socket.py HANDOVER.md
git commit -m "feat: add realtime conversational private messages"
```

### Task 11: 根用户 Markdown 站内信与私有附件

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/.env.example`
- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`
- Modify: `backend/app/models/models.py`
- Modify: `backend/app/models/database.py`
- Modify: `backend/app/core/config.py`
- Create: `backend/app/services/safe_markdown.py`
- Create: `backend/app/schemas/system_messages.py`
- Create: `backend/app/api/system_messages.py`
- Modify: `backend/app/api/admin.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/migrations/social_platform.py`
- Create: `backend/tests/test_system_messages.py`
- Create: `backend/tests/test_safe_markdown.py`
- Create: `frontend/src/api/systemMessages.ts`
- Create: `frontend/src/views/SystemMessageView.vue`
- Create: `frontend/src/views/admin/BroadcastCenterView.vue`
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/src/components/NavBar.vue`
- Modify: `HANDOVER.md`

**Interfaces:**
- Adds `SystemMessage`, `SystemMessageRecipient` and `MessageAttachment(id, uploader_uid, system_message_id: Optional[int], storage_key, original_name, mime_type, size, sha256)`.
- Produces `render_safe_markdown(markdown: str) -> str` with raw HTML disabled.
- Produces user list/detail/read/download under `/api/system-messages`.
- Produces root preview/upload/send under `/api/admin/system-messages`.
- Produces `SystemMessageCreate(title: str, markdown: str, recipient_mode: Literal["selected", "all"], recipient_uids: list[int], attachment_ids: list[int])`; `all` snapshots every active user and `selected` snapshots exactly the validated UID list.
- Adds `Settings.PRIVATE_STORAGE_DIR: str = "private-storage"`; this directory is Git-ignored and is never mounted by `StaticFiles`.

- [ ] **Step 1: Write failing security and permission tests**

Write the tests before installing Markdown dependencies so the first run fails because the safe renderer does not exist, not because assertions accidentally cover old behavior.

```python
def test_markdown_disables_html_and_dangerous_protocols():
    rendered = render_safe_markdown('[x](javascript:alert(1))<img src=x onerror=alert(1)>')
    assert "javascript:" not in rendered
    assert "onerror" not in rendered
    assert "<img" not in rendered


def test_admin_cannot_send_root_system_message(admin_client):
    response = admin_client.post("/api/admin/system-messages", json={
        "title": "通知", "markdown": "**内容**",
        "recipient_mode": "selected", "recipient_uids": [1],
        "attachment_ids": [],
    })
    assert response.status_code == 403
```

```python
@pytest.mark.parametrize("filename,mime", [
    ("image.png", "image/png"), ("document.pdf", "application/pdf"),
    ("notes.txt", "text/plain"), ("archive.zip", "application/zip"),
])
def test_root_can_upload_allowed_private_attachment(root_client, filename, mime):
    response = root_client.post(
        "/api/admin/system-messages/attachments",
        files={"file": (filename, b"content", mime)},
    )
    assert response.status_code == 201
    assert response.json()["original_name"] == filename


def test_only_recipient_or_root_can_download_attachment(root_client, user_clients, sent_message):
    url = f"/api/system-messages/attachments/{sent_message.attachment_id}"
    assert user_clients.recipient.get(url).status_code == 200
    assert user_clients.other.get(url).status_code == 403
    assert root_client.get(url).status_code == 200


def test_all_recipient_snapshot_does_not_include_future_user(root_client, session, active_users):
    sent = root_client.post("/api/admin/system-messages", json={
        "title": "全体通知", "markdown": "正文", "recipient_mode": "all",
        "recipient_uids": [], "attachment_ids": [],
    }).json()
    create_active_user(session, "registered-later")
    recipients = recipient_uids(session, sent["id"])
    assert recipients == {user.uid for user in active_users}
```

```python
@pytest.mark.parametrize("files", [
    [(f"{index}.txt", b"x", "text/plain") for index in range(6)],
    [("large.pdf", b"x" * (10 * 1024 * 1024 + 1), "application/pdf")],
    [
        ("first.pdf", b"x" * (13 * 1024 * 1024), "application/pdf"),
        ("second.pdf", b"x" * (12 * 1024 * 1024 + 1), "application/pdf"),
    ],
])
def test_system_message_attachment_limits(root_client, files):
    response = root_client.post(
        "/api/admin/system-messages/attachments/batch",
        files=[("files", item) for item in files],
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "ATTACHMENT_LIMIT_EXCEEDED"
```

- [ ] **Step 2: Run focused tests and confirm RED**

Run: `PYTHONPATH=backend backend/venv/bin/python -m pytest -q backend/tests/test_safe_markdown.py backend/tests/test_system_messages.py`
Expected: service/models/routes missing.

- [ ] **Step 3: Pin dependencies and implement snapshots, safe Markdown and private files**

Add `markdown-it-py==3.0.0` and `bleach==6.1.0`, then run `npm install dompurify` so the lockfile records the exact resolved version.

```python
ALLOWED_ATTACHMENT_TYPES = {
    "image/png": ".png", "image/jpeg": ".jpg", "image/gif": ".gif",
    "image/webp": ".webp", "application/pdf": ".pdf",
    "text/plain": ".txt", "application/zip": ".zip",
}


def render_safe_markdown(markdown: str) -> str:
    rendered = MarkdownIt("commonmark", {"html": False, "linkify": True}).render(markdown)
    return bleach.clean(
        rendered, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES,
        protocols={"http", "https", "mailto"},
    )
```

Files live below `PRIVATE_STORAGE_DIR/system-messages`, never mounted `/storage`. Sending expands active recipients in one transaction and writes `OperationLog`. Frontend sanitizes returned HTML again with DOMPurify and keeps “系统消息” separate from “私信”.

- [ ] **Step 4: Verify Markdown, attachment auth and build**

```bash
PYTHONPATH=backend backend/venv/bin/python -m pytest -q backend/tests/test_safe_markdown.py backend/tests/test_system_messages.py
PYTHONPATH=backend backend/venv/bin/python -m pytest -q backend/tests
cd frontend && npm run build
cd frontend && npx playwright test tests/e2e/responsive-smoke.spec.ts --grep "system message"
cd backend && PYTHONPATH=. venv/bin/python -m app.migrations.social_platform --phase broadcast --dry-run
cd backend && PYTHONPATH=. venv/bin/python -m app.services.database_backup
cd backend && PYTHONPATH=. venv/bin/python -m app.migrations.social_platform --phase broadcast
```

- [ ] **Step 5: Update handover and commit**

```bash
git add backend/requirements.txt frontend/package.json frontend/package-lock.json backend/app frontend/src backend/tests/test_safe_markdown.py backend/tests/test_system_messages.py frontend/tests/e2e/responsive-smoke.spec.ts HANDOVER.md
git commit -m "feat: add root markdown system messages"
```

### Task 12: 批量邮件与 opt-in 发件队列

**Files:**
- Modify: `backend/app/models/models.py`
- Modify: `backend/app/models/database.py`
- Create: `backend/app/schemas/email_campaigns.py`
- Create: `backend/app/services/email_campaigns.py`
- Create: `backend/app/workers/__init__.py`
- Create: `backend/app/workers/email_campaigns.py`
- Modify: `backend/app/api/admin.py`
- Modify: `backend/app/utils/email.py`
- Modify: `backend/app/migrations/social_platform.py`
- Create: `backend/tests/test_email_campaigns.py`
- Modify: `frontend/src/api/systemMessages.ts`
- Modify: `frontend/src/views/admin/BroadcastCenterView.vue`
- Modify: `HANDOVER.md`

**Interfaces:**
- Adds `EmailCampaign`, `EmailCampaignRecipient` and `EmailCampaignAttachment` with category `notice|promotion` and status `draft|queued|sending|completed|cancelled`.
- Produces `queue_campaign(db, root_user, input) -> CampaignSummary`.
- Produces `process_campaign_batch(session_factory, smtp_service, batch_size=20) -> BatchResult`.
- Produces root create/list/queue/cancel endpoints under `/api/admin/email-campaigns`.
- Produces `EmailCampaignCreate(subject: str, markdown: str, category: Literal["notice", "promotion"], recipient_mode: Literal["selected", "all"], recipient_uids: list[int], attachment_ids: list[int])`; omitted UID selection is never used to infer mode.
- Produces CLI `PYTHONPATH=backend backend/venv/bin/python -m app.workers.email_campaigns --batch-size 20`, which exits 0 when no rows are pending and reports only counts.

- [ ] **Step 1: Write failing opt-in, retry and resume tests**

```python
def test_campaign_filters_non_opted_in_users(root_client, opted_in, opted_out):
    response = root_client.post("/api/admin/email-campaigns", json={
        "subject": "社区通知", "markdown": "正文", "category": "notice",
        "recipient_mode": "selected",
        "recipient_uids": [opted_in.uid, opted_out.uid],
        "attachment_ids": [],
    })
    assert response.json()["selected_count"] == 2
    assert response.json()["eligible_count"] == 1
    assert response.json()["filtered_count"] == 1


def test_worker_resumes_without_resending_delivered(session_factory, flaky_smtp, campaign):
    first = process_campaign_batch(session_factory, flaky_smtp, batch_size=20)
    second = process_campaign_batch(session_factory, flaky_smtp, batch_size=20)
    assert first.failed == 1
    assert second.delivered == 1
    assert flaky_smtp.deliveries.count(campaign.success_email) == 1
```

```python
def test_ordinary_admin_cannot_create_campaign(admin_client):
    response = admin_client.post("/api/admin/email-campaigns", json={
        "subject": "不可发送", "markdown": "正文", "category": "promotion",
        "recipient_mode": "all", "recipient_uids": [], "attachment_ids": [],
    })
    assert response.status_code == 403


def test_campaign_rejects_unowned_attachment(root_client, other_users_attachment):
    response = root_client.post("/api/admin/email-campaigns", json={
        "subject": "附件", "markdown": "正文", "category": "notice",
        "recipient_mode": "all", "recipient_uids": [],
        "attachment_ids": [other_users_attachment.id],
    })
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "ATTACHMENT_NOT_OWNED"


def test_worker_passes_sanitized_attachment_to_smtp(session_factory, smtp, campaign_with_attachment):
    result = process_campaign_batch(session_factory, smtp, batch_size=20)
    assert result.delivered == 1
    assert smtp.messages[0].attachments == [("report.pdf", b"pdf-bytes", "application/pdf")]
```

```python
@pytest.mark.parametrize("sizes", [
    [1, 1, 1, 1, 1, 1],
    [10 * 1024 * 1024 + 1],
    [13 * 1024 * 1024, 12 * 1024 * 1024 + 1],
])
def test_campaign_attachment_limits(root_client, owned_attachment_factory, sizes):
    attachment_ids = [owned_attachment_factory(size=size).id for size in sizes]
    response = root_client.post("/api/admin/email-campaigns", json={
        "subject": "附件限制", "markdown": "正文", "category": "notice",
        "recipient_mode": "all", "recipient_uids": [],
        "attachment_ids": attachment_ids,
    })
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "ATTACHMENT_LIMIT_EXCEEDED"


def test_campaign_logs_mask_recipient_email(session_factory, failing_smtp, campaign, caplog):
    process_campaign_batch(session_factory, failing_smtp, batch_size=20)
    assert campaign.recipient_email not in caplog.text
    assert masked_email(campaign.recipient_email) in caplog.text
```

- [ ] **Step 2: Run focused tests and confirm RED**

Run: `PYTHONPATH=backend backend/venv/bin/python -m pytest -q backend/tests/test_email_campaigns.py`
Expected: models/service/worker/routes missing.

- [ ] **Step 3: Implement durable recipient snapshots and worker**

```python
def eligible_users_statement(recipient_mode: str, recipient_uids: list[int]):
    statement = select(User).where(
        User.status == UserStatus.ACTIVE,
        User.allow_bulk_email.is_(True),
    )
    return statement if recipient_mode == "all" else statement.where(User.uid.in_(recipient_uids))


def masked_email(value: str) -> str:
    local, domain = value.split("@", 1)
    return f"{local[:1]}***@{domain}"
```

Queue stores snapshots only for eligible users and copies selected private-upload metadata into `EmailCampaignAttachment` rows. Worker attaches those files, uses `FOR UPDATE SKIP LOCKED` on PostgreSQL, retries at most three times and never sends a delivered row again. Root UI disables opted-out rows with tooltip and previews selected/eligible/filtered counts.

- [ ] **Step 4: Verify using fake SMTP only**

```bash
PYTHONPATH=backend backend/venv/bin/python -m pytest -q backend/tests/test_email_campaigns.py backend/tests/test_email_connection.py
PYTHONPATH=backend backend/venv/bin/python -m pytest -q backend/tests
cd frontend && npm run build
cd backend && PYTHONPATH=. venv/bin/python -m app.migrations.social_platform --phase broadcast --dry-run
cd backend && PYTHONPATH=. venv/bin/python -m app.services.database_backup
cd backend && PYTHONPATH=. venv/bin/python -m app.migrations.social_platform --phase broadcast
```

Expected: commands pass and none invokes configured real SMTP.

- [ ] **Step 5: Update handover and commit**

```bash
git add backend/app frontend/src backend/tests/test_email_campaigns.py HANDOVER.md
git commit -m "feat: add opt-in root email campaigns"
```

### Task 13: 白/黑主题收敛、最终迁移与端到端验收

**Files:**
- Modify: `frontend/src/assets/main.css`
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/components/NavBar.vue`
- Modify: `frontend/src/components/Footer.vue`
- Modify: `frontend/src/views/HomeView.vue`
- Modify: `frontend/src/views/LoginView.vue`
- Modify: `frontend/src/views/RegisterView.vue`
- Modify: `frontend/src/views/VerifyEmailView.vue`
- Modify: `frontend/src/views/SoupCreateView.vue`
- Modify: `frontend/src/views/SoupDetailView.vue`
- Modify: `frontend/src/views/PostListView.vue`
- Modify: `frontend/src/views/PostDetailView.vue`
- Modify: `frontend/src/views/ProfileView.vue`
- Modify: `frontend/src/views/SettingsView.vue`
- Modify: `frontend/src/views/MessageView.vue`
- Modify: `frontend/src/views/NotificationView.vue`
- Modify: `frontend/src/views/SystemMessageView.vue`
- Modify: `frontend/src/views/SearchView.vue`
- Modify: `frontend/src/views/CompetitionListView.vue`
- Modify: `frontend/src/views/CompetitionDetailView.vue`
- Modify: `frontend/src/views/LeaderboardView.vue`
- Modify: `frontend/src/views/soup/SoupListView.vue`
- Modify: `frontend/src/views/admin/AdminDashboard.vue`
- Modify: `frontend/src/views/admin/BroadcastCenterView.vue`
- Modify: `frontend/tests/e2e/responsive-smoke.spec.ts`
- Modify: `frontend/tests/e2e/chat.spec.ts`
- Create: `frontend/tests/e2e/social-workflows.spec.ts`
- Modify: `backend/tests/test_openapi_snapshot.py`
- Modify: `HANDOVER.md`

**Interfaces:**
- Finalizes CSS tokens `--page`, `--surface`, `--text`, `--muted`, `--border` and `--primary`.
- Covers verification stub, search, soup reveal/text, settings, profile/pins, sign-in, mention, chat, system messages and root email filtering in Playwright.
- Applies `social_platform --phase all` to the real PostgreSQL database after a fresh backup.

- [ ] **Step 1: Add failing visual and workflow assertions**

```typescript
test('themes use white and black page surfaces', async ({ page }) => {
  await page.goto('/settings')
  await page.getByRole('button', { name: '浅色' }).click()
  await expect(page.locator('body')).toHaveCSS('background-color', 'rgb(255, 255, 255)')
  await page.getByRole('button', { name: '深色' }).click()
  await expect(page.locator('body')).toHaveCSS('background-color', 'rgb(0, 0, 0)')
})

test('root tools are not visible to ordinary users', async ({ page }) => {
  await loginAsRoot(page)
  await expect(page.getByRole('link', { name: '邮件群发' })).toBeVisible()
  await loginAsOrdinaryUser(page)
  await expect(page.getByRole('link', { name: '邮件群发' })).toHaveCount(0)
})
```

```typescript
for (const viewport of [
  { width: 375, height: 812 },
  { width: 768, height: 1024 },
  { width: 1440, height: 900 },
]) {
  test('social surfaces fit ' + viewport.width + 'x' + viewport.height, async ({ page }) => {
    await page.setViewportSize(viewport)
    for (const path of ['/profile/1', '/settings', '/messages', '/system-messages', '/admin/broadcasts']) {
      await page.goto(path)
      const metrics = await page.evaluate(() => ({
        body: document.body.scrollWidth,
        viewport: document.documentElement.clientWidth,
      }))
      expect(metrics.body).toBeLessThanOrEqual(metrics.viewport)
      const regions = await page.locator('[data-layout-region]').evaluateAll(nodes =>
        nodes.map(node => {
          const box = node.getBoundingClientRect()
          return { top: box.top, bottom: box.bottom }
        })
      )
      expect(regions.length).toBeGreaterThanOrEqual(3)
      for (let index = 1; index < regions.length; index += 1) {
        expect(regions[index - 1].bottom).toBeLessThanOrEqual(regions[index].top + 1)
      }
    }
  })
}
```

- [ ] **Step 2: Run visual tests and confirm RED**

```bash
cd frontend && npx playwright test tests/e2e/social-workflows.spec.ts tests/e2e/responsive-smoke.spec.ts tests/e2e/chat.spec.ts
rg -n "gradient|purple|violet" frontend/src -g "*.vue" -g "*.css"
```

Expected: workflows fail on current theme/layout and scan reports legacy colors.

- [ ] **Step 3: Implement restrained white/black UI and all states**

```css
:root {
  --page: #ffffff;
  --surface: #ffffff;
  --text: #111111;
  --muted: #5f6368;
  --border: #e5e7eb;
  --primary: #2563eb;
}

.dark {
  --page: #000000;
  --surface: #111111;
  --text: #f5f5f5;
  --muted: #a3a3a3;
  --border: #2a2a2a;
  --primary: #60a5fa;
}
```

Replace gradient/purple classes, nested page cards and text-only icon substitutes. Use Heroicons and tooltips. Mark top-level nav/announcement/content/footer with ordered `data-layout-region` attributes for overlap checks. Every page retains loading, empty, error, disabled and success states with stable dimensions.

- [ ] **Step 4: Run full verification, backup, migrate and inspect**

```bash
PYTHONPATH=backend backend/venv/bin/python -m pytest -q backend/tests
backend/venv/bin/python -m compileall -q backend/app
cd frontend && npm run build
cd frontend && npx playwright test
cd frontend && if rg -n "gradient|purple|violet" src -g "*.vue" -g "*.css"; then exit 1; fi
cd backend && PYTHONPATH=. venv/bin/python -m app.migrations.social_platform --phase all --dry-run
cd backend && PYTHONPATH=. venv/bin/python -m app.services.database_backup
cd backend && PYTHONPATH=. venv/bin/python -m app.migrations.social_platform --phase all
```

Expected: tests/build/Playwright pass; style scan has no hits; migration succeeds. Read-only checks must show SkyUnreal=root, both people columns as PostgreSQL text, zero foreign-key orphans and zero duplicate unique-key groups.

Start backend/frontend on free ports. Verify `/health`, search, `/profile/1`, settings, chat and root admin. Save and inspect three viewport screenshots under `frontend/test-results/final/` for overlap/overflow.

- [ ] **Step 5: Final handover update and commit**

Replace stale build/page statements. Record test counts, Playwright count, backup checksum, migration counts, `PUBLIC_WEB_URL`, Redis fallback, SMTP worker command and external-production risks.

```bash
git add frontend/src frontend/tests backend/tests/test_openapi_snapshot.py HANDOVER.md
git commit -m "feat: complete social platform experience"
```
