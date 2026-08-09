# 海龟汤社区系统可用性收尾实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将交接文档中的剩余功能收敛为可在本机启动、可通过契约测试和前端生产构建的核心社区系统。

**Architecture:** 先建立共享的规范 Schema、SQLite 测试夹具、唯一约束和错误响应，再按后端领域切片实现比赛/公告、旧字段模块和评论；前端页面只消费这些规范 API。Redis、搜索、Celery、WebSocket 作为可选适配器，服务不可用时核心 HTTP 流程安全降级并在健康检查中标记 degraded。

**Tech Stack:** FastAPI、SQLModel、Pydantic v2、pytest、SQLite/PostgreSQL；Vue 3、TypeScript、Pinia、Vite。

## Global Constraints

- 所有公开响应使用 `uid`、`author_uid`、`creator_uid`、`sender_uid`、`receiver_uid`、`average_score`、`rating_count`、`favorite_count`。
- 所有新建/更新接口使用独立 Pydantic Schema；不通过增加旧字段别名掩盖模型错配。
- 竞赛收录唯一键为 `(competition_id, soup_id)`；互动唯一键按用户、目标类型和目标 ID 组合定义。
- 管理修改写入操作日志；标签、公告、评论文本拒绝未消毒 HTML。
- 真实 SMTP、云存储、公网部署和生产运维不自动执行；本机服务均提供缺失依赖时的降级路径。

---

### Task 1: 共享契约、约束和健康检查

**Files:**
- Create: `backend/app/schemas/common.py`
- Create: `backend/app/testing.py`
- Modify: `backend/app/models/models.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/api/auth.py`
- Test: `backend/tests/test_contract_foundation.py`

**Interfaces:**
- Produces `PageResponse[T]`, `ApiError`, `extract_detail_message`。
- Produces SQLite `make_test_session()` 和 `make_test_client()` 测试夹具。
- Produces `/health` 的 `status`, `dependencies` 字段；依赖缺失时返回 200 + `degraded`。
- Produces互动和比赛收录唯一约束的数据库元数据。

- [ ] 写健康检查、唯一约束和统一分页 Schema 失败测试。
- [ ] 运行 `PYTHONPATH=backend backend/venv/bin/python -m pytest -q backend/tests/test_contract_foundation.py`，确认缺少实现而失败。
- [ ] 实现共享 Schema、测试夹具、唯一约束和无外部依赖健康检查。
- [ ] 重跑定向测试、原有 81 项后端测试和 `compileall`。

### Task 2: 规范化比赛与自动收录

**Files:**
- Modify: `backend/app/models/models.py`
- Modify: `backend/app/models/database.py`
- Create: `backend/app/schemas/competitions.py`
- Create: `backend/app/services/competition_entries.py`
- Rewrite: `backend/app/api/competitions.py`
- Test: `backend/tests/test_competition_contract.py`

**Interfaces:**
- `Competition.required_tag_ids: list[int]`, `score_type: CompetitionScoreType`, `result_snapshot` 和 `updated_at`。
- `evaluate_soup_competitions(db, soup) -> list[CompetitionEntry]`，只处理 pending/ongoing 且 active 标签命中的时间范围比赛。
- `GET /api/competitions`、`GET /api/competitions/{id}`、管理员 `POST /api/competitions` 使用规范分页/详情 Schema。
- 发布或编辑 Soup 后事务内调用收录服务；已完成比赛不回溯。

- [ ] 写创建、标签绑定、时间范围、自动收录、重复幂等和结算快照失败测试。
- [ ] 运行定向测试确认旧 `creator_id/entry_tags/scoring_method` 路由失败。
- [ ] 实现模型、服务、Schema 和 API，并在 Soup 创建/更新后调用收录。
- [ ] 运行比赛测试和后端全量测试。

### Task 3: 标签治理与公告 API

**Files:**
- Create: `backend/app/models/announcements.py` 或扩展 `models.py`
- Create: `backend/app/schemas/announcements.py`
- Create: `backend/app/api/announcements.py`
- Modify: `backend/app/api/tags.py`
- Modify: `backend/app/api/admin.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_taxonomy_announcement_contract.py`

**Interfaces:**
- 管理员 `GET/POST/PUT /api/admin/tags`、`POST /api/admin/tags/{id}/merge`。
- 公开 `GET /api/announcements`；管理员创建、发布、撤回、删除公告。
- `Announcement` 状态 draft/published/expired，支持优先级和过期时间；正文经过纯文本清洗。
- 标签合并迁移 SoupTag、更新竞赛引用、写 TagAlias 和 OperationLog。

- [ ] 写管理员权限、XSS 清洗、公告状态过滤、标签合并和别名保留失败测试。
- [ ] 运行定向测试确认接口缺失。
- [ ] 实现模型、Schema、路由和审计写入。
- [ ] 运行公告/标签治理测试和后端全量测试。

### Task 4: 帖子、社交、私信、成就和搜索契约治理

**Files:**
- Create: `backend/app/schemas/community.py`
- Rewrite: `backend/app/api/posts.py`
- Rewrite: `backend/app/api/social.py`
- Rewrite: `backend/app/api/messages.py`
- Rewrite: `backend/app/api/achievements.py`
- Rewrite: `backend/app/api/search.py`
- Modify: `frontend/src/types/index.ts`
- Create/modify: `frontend/src/api/community.ts`
- Test: `backend/tests/test_community_contract.py`

**Interfaces:**
- 帖子响应使用 `author_uid`；社交使用 `follower_uid/followed_uid` 和 `blocker_uid/blocked_uid`；私信使用 `sender_uid/receiver_uid`；成就使用 `user_uid/is_achieved/achieved_at`；搜索返回规范分页。
- 公共列表和搜索使用可选认证依赖；写操作使用 active 用户；私信/拉黑权限保持现有规则。
- 前端 API 只保留真实 `/api/posts`、`/api/social`、`/api/messages`、`/api/search` 路径。

- [ ] 为每个模块写一个成功和一个权限/字段错配失败测试。
- [ ] 运行定向测试确认旧字段访问会失败。
- [ ] 实现规范 Schema、查询和响应；删除旧字段访问。
- [ ] 运行社区契约测试和后端全量测试。

### Task 5: 海龟汤评论闭环与互动并发

**Files:**
- Create: `backend/app/schemas/comments.py`
- Create: `backend/app/api/comments.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/models/models.py`
- Modify: `frontend/src/api/soup.ts`
- Modify: `frontend/src/views/SoupDetailView.vue`
- Test: `backend/tests/test_comment_contract.py`
- Test: `backend/tests/test_interaction_constraints.py`

**Interfaces:**
- `GET/POST /api/turtle-soups/{soup_id}/comments`，支持一级回复、分页、作者/管理员删除和隐藏状态过滤。
- 评论响应使用 `author_uid`、`parent_id`、`created_at`、`replies`。
- 评分/点赞/收藏重复请求幂等，数据库唯一约束和事务计数保护并发写入。

- [ ] 写评论权限、回复深度、删除权限和互动唯一性失败测试。
- [ ] 运行定向测试确认路由/约束缺失。
- [ ] 实现 API、前端评论区和约束迁移。
- [ ] 运行评论/并发测试与全量回归。

### Task 6: 补齐前端页面、公告条和响应式导航

**Files:**
- Rewrite: `frontend/src/views/MessageView.vue`
- Rewrite: `frontend/src/views/PostDetailView.vue`
- Rewrite: `frontend/src/views/NotificationView.vue`
- Rewrite: `frontend/src/views/CompetitionDetailView.vue`
- Rewrite: `frontend/src/views/CompetitionListView.vue`
- Rewrite: `frontend/src/views/SearchView.vue`
- Rewrite: `frontend/src/views/PostListView.vue`
- Rewrite: `frontend/src/views/admin/AdminDashboard.vue`
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/components/NavBar.vue`
- Modify: `frontend/src/assets/main.css`
- Create: `frontend/src/api/announcements.ts`
- Test: `frontend` type/build checks and route smoke tests

**Interfaces:**
- 每个页面包含加载、空、错误、成功和表单提交状态；所有 API 字段与 Task 3/4/5 Schema 对齐。
- App 在导航下渲染可关闭公告条；关闭只写 session/local storage，不改变服务端状态。
- 移动端导航折叠，公告和筛选控件在 375/768/1440 宽度不溢出。

- [ ] 为页面路由和公告条写最小组件/类型失败检查。
- [ ] 运行 `npx vue-tsc -b` 和 `npm run build` 记录空文件失败。
- [ ] 实现页面、API、公告条和响应式样式。
- [ ] 运行类型检查、生产构建和三视口 Playwright smoke。

### Task 7: 邮箱限流、重试和可选依赖适配

**Files:**
- Create: `backend/app/services/rate_limit.py`
- Create: `backend/app/services/dependency_health.py`
- Modify: `backend/app/api/auth.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/core/config.py`
- Test: `backend/tests/test_rate_limit_and_health.py`

**Interfaces:**
- `RateLimiter.allow(scope, key, limit, window_seconds) -> bool`，Redis 可用时原子计数，不可用时使用进程内短期降级并标记健康状态。
- 邮箱验证发送按 IP、邮箱和全局窗口限流；SMTP 失败保留 pending 状态并支持有限重试。
- `/health` 返回每个外部依赖的状态，不因非核心依赖失败返回 500。

- [ ] 写 Redis 缺失降级、IP/邮箱限流和 SMTP 重试失败测试。
- [ ] 运行定向测试确认服务缺失时当前行为不满足约束。
- [ ] 实现适配器、配置和健康信息。
- [ ] 运行认证全量回归和 compileall。

### Task 8: 集成验收与交接

**Files:**
- Create: `backend/tests/test_openapi_snapshot.py`
- Create: `tests/e2e/critical-workflows.spec.ts`
- Modify: `frontend/package.json`
- Modify: `HANDOVER.md`

**Interfaces:**
- OpenAPI 快照覆盖认证、海龟汤、标签、比赛、公告、评论、消息和管理路由。
- Playwright 关键流程在本机服务启动时运行；服务未启动时测试明确跳过并报告前置条件。
- HANDOVER 只保留真实未完成项，包含启动、迁移、验证和降级说明。

- [ ] 写 OpenAPI 路由集合和关键流程失败检查。
- [ ] 运行完整后端测试、前端类型/构建和 Playwright smoke。
- [ ] 修复验证暴露的契约/启动问题。
- [ ] 更新交接文档并完成最终全量验证。
