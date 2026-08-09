# 海龟汤内容元数据第一阶段实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现海龟汤流派、汤色、人数和规范标签的数据模型、可重复迁移、API 契约与前端类型，并先修复公开详情和用户路由的三个阻塞问题。

**Architecture:** 后端以 SQLModel 规范实体和 Pydantic 请求/响应 Schema 为单一契约，旧 `Soup.tags` 仅作为迁移输入，不再作为新接口的数据源。迁移模块把结构升级与历史数据导入分开，支持 dry-run 和重复执行；前端只消费规范标签对象和统一分页响应。

**Tech Stack:** Python 3.12、FastAPI、SQLModel/SQLAlchemy、Pydantic v2、pytest；Vue 3、TypeScript、Pinia、Vite。

## Global Constraints

- 流派只能为 `本格`、`变格`、`鳖汤`；历史记录可以保留显式 `未分类`，但创建和更新不得提交 `未分类`。
- 汤色只能为 `清汤`、`红汤`、`黑汤`；历史记录可以保留显式 `未分类`，但创建和更新不得提交 `未分类`。
- `main_player_count` 范围为 1～100；`secondary_player_count` 范围为 0～100，发布时均必填。
- 单个作品最多关联 10 个标签；标签名称规范化后长度为 1～30，拒绝控制字符和 HTML。
- 新增接口和响应只使用 `uid`、`author_uid`、`average_score`、`rating_count`、`favorite_count` 等规范字段。
- 不在本阶段实现竞赛自动收录、公告管理、旧业务模块全面迁移或空页面补齐。

---

### Task 1: 安全与路由阻塞回归

**Files:**
- Modify: `backend/app/api/auth.py`
- Modify: `backend/app/api/turtle_soups.py`
- Modify: `backend/app/api/users.py`
- Test: `backend/tests/test_soup_api_security.py`
- Test: `backend/tests/test_user_routes.py`

**Interfaces:**
- Produces: `get_optional_current_user(token: Optional[str], db: Session) -> Optional[User]`
- Produces: 公共详情允许匿名访问；`reveal=true` 不再绕过汤底权限。
- Produces: 固定 `/me` 路由不被动态用户路由截获，公开用户路由使用 `/uid/{uid}`。

- [x] **Step 1: 写匿名详情、越权揭示和固定路由的失败测试**

```python
def test_anonymous_can_read_public_soup_without_solution(client, soup):
    response = client.get(f"/api/turtle-soups/{soup.id}")
    assert response.status_code == 200
    assert response.json()["solution"] is None

def test_reveal_query_does_not_expose_solution_to_anonymous_user(client, soup):
    response = client.get(f"/api/turtle-soups/{soup.id}?reveal=true")
    assert response.status_code == 200
    assert response.json()["solution"] is None

def test_me_route_is_not_captured_by_dynamic_user_route(client):
    response = client.get("/api/users/me")
    assert response.status_code == 200
    assert response.json()["uid"] == 42
```

- [x] **Step 2: 运行定向测试，确认因当前强制认证、揭示分支和路由顺序而失败**

Run: `PYTHONPATH=backend backend/venv/bin/python -m pytest -q backend/tests/test_soup_api_security.py backend/tests/test_user_routes.py`

Expected: FAIL；匿名详情当前返回 401，`reveal=true` 当前返回汤底，`/me` 当前被 `/{user_id}` 捕获并返回 422。

- [x] **Step 3: 增加可选认证依赖，收紧汤底展示条件并整理用户路由顺序**

```python
optional_oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/login",
    auto_error=False,
)

async def get_optional_current_user(
    token: Optional[str] = Depends(optional_oauth2_scheme),
    db: Session = Depends(get_db),
) -> Optional[User]:
    if token is None:
        return None
    return _resolve_user_from_token(token, db)
```

`_payload()` 的汤底条件固定为 `soup.status == "revealed" or (reveal and can_manage)`；删除 `/api/users/{user_id}`，保留 `/api/users/uid/{uid}`。

- [x] **Step 4: 运行定向测试和现有认证/用户契约测试，确认通过**

Run: `PYTHONPATH=backend backend/venv/bin/python -m pytest -q backend/tests/test_soup_api_security.py backend/tests/test_user_routes.py backend/tests/test_auth_security.py backend/tests/test_user_contract.py`

Expected: PASS。

### Task 2: 元数据规则、Schema 与模型

**Files:**
- Create: `backend/app/services/tag_rules.py`
- Create: `backend/app/schemas/soups.py`
- Modify: `backend/app/models/models.py`
- Modify: `backend/app/models/database.py`
- Test: `backend/tests/test_soup_metadata_contract.py`
- Test: `backend/tests/test_tag_rules.py`

**Interfaces:**
- Produces: `normalize_tag_name(value: str) -> tuple[str, str]`，返回展示名与大小写不敏感的 slug。
- Produces: `SoupCreate`、`SoupUpdate`、`SoupResponse`、`SoupPageResponse`、`TagResponse`、`TagPageResponse`。
- Produces: `Tag`、`SoupTag`、`TagAlias` 与 `Soup` 的四个元数据字段。

- [x] **Step 1: 写标签规范化、人数边界、必选分类及联合唯一约束的失败测试**

```python
def test_tag_name_is_trimmed_folded_and_rejects_markup():
    assert normalize_tag_name("  剧情   推理  ") == ("剧情 推理", "剧情-推理")
    with pytest.raises(ValueError):
        normalize_tag_name("<script>")

def test_soup_create_requires_taxonomy_and_player_counts():
    item = SoupCreate(
        title="谜题", puzzle="谜面", solution="汤底", genre="本格",
        soup_color="清汤", main_player_count=1,
        secondary_player_count=0,
    )
    assert item.main_player_count == 1
```

另用 SQLite 实际提交两条相同 `(soup_id, tag_id)` 的 `SoupTag`，断言第二次提交抛出 `IntegrityError`。

- [x] **Step 2: 运行定向测试，确认缺少规则、Schema 和模型字段**

Run: `PYTHONPATH=backend backend/venv/bin/python -m pytest -q backend/tests/test_tag_rules.py backend/tests/test_soup_metadata_contract.py`

Expected: collection/import FAIL，因为 `tag_rules`、`schemas.soups` 和新模型尚不存在。

- [x] **Step 3: 实现最小规则、Schema、枚举模型与约束**

```python
class Tag(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    slug: str = Field(unique=True, index=True, max_length=64)
    name: str = Field(index=True, max_length=30)
    kind: TagKind = Field(default=TagKind.CUSTOM)
    status: TagStatus = Field(default=TagStatus.ACTIVE)
    view_count: int = Field(default=0, ge=0)
    usage_count: int = Field(default=0, ge=0)

class SoupTag(SQLModel, table=True):
    soup_id: int = Field(foreign_key="soups.id", primary_key=True)
    tag_id: int = Field(foreign_key="tags.id", primary_key=True)
```

`SoupCreate` 使用 `Literal["本格", "变格", "鳖汤"]`、`Literal["清汤", "红汤", "黑汤"]` 和 Pydantic 数值边界；`Soup` 历史默认值为显式 `未分类`、1、0。

- [x] **Step 4: 运行定向测试，确认所有规则通过**

Run: `PYTHONPATH=backend backend/venv/bin/python -m pytest -q backend/tests/test_tag_rules.py backend/tests/test_soup_metadata_contract.py`

Expected: PASS。

### Task 3: 可重复数据迁移

**Files:**
- Create: `backend/app/migrations/__init__.py`
- Create: `backend/app/migrations/soup_metadata.py`
- Test: `backend/tests/test_soup_metadata_migration.py`

**Interfaces:**
- Consumes: `Tag`、`SoupTag`、`normalize_tag_name`。
- Produces: `migrate_soup_metadata(session: Session, dry_run: bool = False) -> MigrationReport`。
- Produces: `python -m app.migrations.soup_metadata [--dry-run]` 命令入口。

- [x] **Step 1: 写旧 JSON 标签导入、默认元数据、幂等和 dry-run 无写入的失败测试**

```python
def test_migration_imports_legacy_tags_once(session, legacy_soup):
    first = migrate_soup_metadata(session)
    second = migrate_soup_metadata(session)
    assert first.created_tags == 2
    assert first.created_links == 2
    assert second.created_tags == 0
    assert second.created_links == 0

def test_dry_run_reports_without_writes(session, legacy_soup):
    report = migrate_soup_metadata(session, dry_run=True)
    assert report.created_tags == 2
    assert session.exec(select(Tag)).all() == []
```

- [x] **Step 2: 运行定向测试，确认迁移入口不存在**

Run: `PYTHONPATH=backend backend/venv/bin/python -m pytest -q backend/tests/test_soup_metadata_migration.py`

Expected: collection/import FAIL，因为 `app.migrations.soup_metadata` 尚不存在。

- [x] **Step 3: 实现结构预检、历史数据转换、计数报告和事务回滚**

```python
@dataclass(frozen=True)
class MigrationReport:
    scanned_soups: int
    created_tags: int
    created_links: int
    skipped_tags: int
    dry_run: bool

def migrate_soup_metadata(
    session: Session,
    dry_run: bool = False,
) -> MigrationReport:
    """Import legacy Soup.tags and recompute usage_count idempotently."""
```

结构函数通过 SQLAlchemy inspector 生成缺失列 DDL，并用 `SQLModel.metadata.create_all()` 创建标签表；`--dry-run` 只打印计划，不执行 DDL 或数据写入。

- [x] **Step 4: 连续运行迁移测试两次，确认关联和统计不重复**

Run: `PYTHONPATH=backend backend/venv/bin/python -m pytest -q backend/tests/test_soup_metadata_migration.py`

Expected: PASS，第二次报告的新增标签和关联均为 0。

### Task 4: 标签和海龟汤 API 契约

**Files:**
- Create: `backend/app/api/tags.py`
- Modify: `backend/app/api/turtle_soups.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_soup_metadata_api.py`

**Interfaces:**
- Consumes: Task 2 的 Schema、模型和标签规则。
- Produces: `GET /api/tags`，支持 `kind`、`keyword`、`sort_by`、分页，并在成功返回页面时增加命中标签的 `view_count`。
- Produces: `POST/GET/PUT /api/turtle-soups` 的规范元数据与标签契约，列表支持 `genre`、`soup_color`、`tag`、`tag_id` 和统一分页。

- [x] **Step 1: 写创建校验、自定义标签、筛选、详情和更新权限的失败 API 测试**

```python
def test_create_soup_returns_normalized_metadata(auth_client):
    response = auth_client.post("/api/turtle-soups", json={
        "title": "谜题", "puzzle": "谜面", "solution": "汤底",
        "genre": "本格", "soup_color": "清汤",
        "main_player_count": 1, "secondary_player_count": 0,
        "custom_tags": [" 剧情   推理 "], "tag_ids": [],
    })
    assert response.status_code == 201
    assert response.json()["tags"][0]["name"] == "剧情 推理"

def test_list_filters_by_genre_color_and_tag(client, created_soup):
    response = client.get(
        f"/api/turtle-soups?genre=本格&soup_color=清汤&tag_id={created_soup.tag_id}"
    )
    assert response.json()["total"] == 1
```

另覆盖停用标签 422、超过十个标签 422、非作者更新 403、成功按标签筛选后 `Tag.view_count` 原子增加一次。

- [x] **Step 2: 运行定向测试，确认旧 dict 接口和 JSON 标签查询不满足契约**

Run: `PYTHONPATH=backend backend/venv/bin/python -m pytest -q backend/tests/test_soup_metadata_api.py`

Expected: FAIL；旧接口缺少字段校验、标签实体与筛选。

- [x] **Step 3: 实现标签解析、关联同步、usage_count 维护与规范响应**

```python
def resolve_tags(
    db: Session,
    tag_ids: list[int],
    custom_names: list[str],
) -> list[Tag]:
    """Return unique active tags, creating normalized custom tags."""

def sync_soup_tags(db: Session, soup: Soup, tags: list[Tag]) -> None:
    """Replace links and recompute affected usage counts in one transaction."""
```

列表筛选通过 `SoupTag` 子查询，不再读取 JSON；响应由 `SoupResponse` 严格校验，不返回 `avg_score`、`score_count` 等过渡字段。

- [x] **Step 4: 运行元数据 API、安全回归和后端完整测试**

Run: `PYTHONPATH=backend backend/venv/bin/python -m pytest -q backend/tests/test_soup_metadata_api.py backend/tests/test_soup_api_security.py`

Expected: PASS。

### Task 5: 前端契约与元数据表单/筛选

**Files:**
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/api/soup.ts`
- Create: `frontend/src/api/tags.ts`
- Modify: `frontend/src/stores/soup.ts`
- Modify: `frontend/src/views/SoupCreateView.vue`
- Modify: `frontend/src/views/soup/SoupListView.vue`

**Interfaces:**
- Consumes: Task 4 的 OpenAPI 字段。
- Produces: `SoupGenre`、`SoupColor`、`Tag`、规范 `SoupCreate` 和列表筛选参数。
- Produces: 发布页必选流派/汤色/人数与规范标签输入，列表页支持流派、汤色和标签筛选。

- [x] **Step 1: 更新 TypeScript 类型，使旧字符串标签和缺失元数据产生编译错误**

```typescript
export type SoupGenre = '本格' | '变格' | '鳖汤' | '未分类'
export type SoupColor = '清汤' | '红汤' | '黑汤' | '未分类'
export interface Tag { id: number; slug: string; name: string; kind: 'system' | 'custom'; view_count: number; usage_count: number }
export interface SoupCreate {
  title: string; puzzle: string; solution: string
  genre: Exclude<SoupGenre, '未分类'>
  soup_color: Exclude<SoupColor, '未分类'>
  main_player_count: number; secondary_player_count: number
  tag_ids: number[]; custom_tags: string[]; is_revealed?: boolean
}
```

- [x] **Step 2: 运行 `npm run build`，记录预期失败位置**

Run: `npm run build`（工作目录 `frontend`）

Expected: FAIL；现有 store/页面仍提交 `tags: string[]` 且缺少必填元数据；若先遇到已知空 Vue 文件错误，同样保留完整输出。

- [x] **Step 3: 更新 API、store、发布表单和筛选页面以符合新契约**

`soupApi.getList()` 透传 `genre`、`soup_color`、`tag_id`；发布表单使用两个 `select` 和两个数值输入，自定义标签写入 `custom_tags`，列表卡片渲染 `tag.name`。

- [x] **Step 4: 运行生产构建；若仍被交接文档已知空页面阻塞，准确记录剩余错误**

Run: `npm run build`（工作目录 `frontend`）

Expected: 元数据相关类型错误为 0；允许仅剩交接文档列出的空 Vue 页面阻塞，并准确记录文件名。

### Task 6: 验证与交接同步

**Files:**
- Modify: `HANDOVER.md`

**Interfaces:**
- Consumes: 前五项实际验证结果。
- Produces: 当前功能状态、迁移命令和下一项优先级的准确交接记录。

- [x] **Step 1: 运行后端完整 pytest 与 compileall**

Run: `PYTHONPATH=backend backend/venv/bin/python -m pytest -q backend/tests && backend/venv/bin/python -m compileall -q backend/app`

Expected: exit 0，无失败测试或编译错误。

- [x] **Step 2: 运行前端生产构建并检查 `.env` 权限/忽略状态**

Run: `cd frontend && npm run build`；`stat -c '%a' backend/.env`；`git check-ignore -v backend/.env`

Expected: 构建结果按 Task 5 记录；权限为 `600` 且 `.gitignore` 命中。

- [x] **Step 3: 检查项目范围差异，确认未修改 `/root/project/CTG` 外文件**

Run: `find /root/project/CTG -type f -newermt '2026-08-08 00:00:00' | sort`，并人工核对本次文件清单。

- [ ] **Step 4: 按真实结果更新 `HANDOVER.md` 并复跑受影响验证**

更新“当前功能状态”“迁移命令”“后续工作优先级”，随后重跑 Step 1 和 Task 5 的构建命令，最终结果不得使用推测性描述。
