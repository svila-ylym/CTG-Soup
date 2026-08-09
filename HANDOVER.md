# 海龟汤社区项目交接手册

更新日期：2026-08-08

最新设计基线：已确认社交平台扩展方案，覆盖汤底按需公开、人物文本字段、`SkyUnreal` 根用户、幂等邮箱验证和公开链接配置、搜索修复、用户设置与主题、个人主页、签到等级、@ 提及、会话式私信、Emoji、根用户系统消息/附件/批量邮件及旧库迁移。设计文档为 `docs/superpowers/specs/2026-08-08-social-platform-expansion-design.md`，实施计划为 `docs/superpowers/plans/2026-08-08-social-platform-expansion.md`；当前已完成任务 2/13：安全备份/统一迁移骨架、汤底默认隐藏并可匿名点击展开、人物描述任意文本及真实库 TEXT 迁移。

本次交接基线：数据库自动创建、邮箱验证注册、access/refresh token 隔离、bcrypt 兼容和 JWT 安全默认值已实现并通过测试；海龟汤内容元数据第一阶段已经实现模型、可重复迁移、标签 API、发布/列表/详情契约和前端类型。竞赛关键词收录、后台标签治理、公告栏和完整响应式改造仍只有设计，尚未实现。

## 1. 项目结论

本项目是一个前后端分离的海龟汤社区原型：前端使用 Vue 3、TypeScript、Vite 和 Pinia，后端使用 FastAPI、SQLModel、PostgreSQL。当前代码已经覆盖认证、海龟汤、帖子、比赛、社交、消息、成就、搜索、管理和上传等路由，但不同模块的成熟度不一致。

接手时请区分以下三种状态：

- **有代码**：页面、路由或模型存在，不代表已完成联调。
- **有规则测试**：纯业务规则经过 pytest 验证，不代表数据库和 HTTP 链路可用。
- **可端到端使用**：需要本机服务启动、数据库建表、前后端联调及实际操作验证；目前尚未形成完整 E2E 测试。

## 2. 技术栈与运行端口

| 部分 | 技术 | 本机地址 |
| --- | --- | --- |
| 前端 | Vue 3、TypeScript、Vite、Pinia、Vue Router | `http://localhost:10000` |
| 后端 | Python 3、FastAPI、SQLModel、Uvicorn | `http://localhost:8000` |
| API 文档 | Swagger UI，仅 `DEBUG=true` 时开放 | `http://localhost:8000/docs` |
| 健康检查 | FastAPI | `http://localhost:8000/health` |
| 数据库 | PostgreSQL | `localhost:5432/turtle_soup` |
| 缓存 | Redis | `localhost:6379/0` |

Vite 在 `0.0.0.0:10000` 监听，并把 `/api` 和 `/ws` 代理到本机后端。后端 CORS 允许通过 `localhost`、`127.0.0.1` 和 `0.0.0.0` 的 10000 端口访问。

## 3. 关键目录

```text
CTG/
├── backend/
│   ├── app/api/              # FastAPI 路由
│   ├── app/core/config.py    # Pydantic 环境配置
│   ├── app/models/models.py  # SQLModel 数据模型
│   ├── app/services/         # 可独立测试的业务规则
│   ├── backups/              # pg_dump 运行时备份（Git 忽略）
│   ├── app/utils/email.py    # SMTP 邮件服务
│   ├── app/db.py             # 数据库引擎与建表
│   ├── tests/                # 后端测试
│   ├── .env                  # 本机秘密配置，不进入 Git
│   └── .env.example          # 无秘密配置模板
├── frontend/
│   ├── src/api/              # Axios API 客户端
│   ├── src/stores/           # Pinia 状态
│   ├── src/views/            # 页面
│   └── vite.config.ts        # 端口和代理
├── docs/superpowers/         # 已确认的设计和实施计划
├── dev.sh                    # 推荐的 Linux/macOS 开发入口
├── setup.ps1                 # Windows PowerShell 初始化入口
└── HANDOVER.md               # 本手册
```

## 4. 当前功能状态

### 已实现并有针对性测试

- 角色层级、处罚撤销、治理和举报规则。
- 海龟汤评分范围、0.5 步进、平均分、点赞/收藏幂等规则。
- 上传文件大小、扩展名和 MIME 类型规则。
- 用户请求/响应契约及部分管理契约。
- SMTP SSL 与 STARTTLS 连接选择。
- 注册用户以 `pending_email` 状态创建，验证令牌仅保存哈希，验证成功后才能登录。
- access/refresh token 类型隔离、密码 72 字节边界、JWT 弱默认密钥拒绝和登录重定向校验。
- 本机 PostgreSQL 缺失数据库的显式自动创建逻辑及安全标识符测试。
- 已发布海龟汤首次详情响应固定隐藏汤底；匿名用户可通过明确的 `reveal=true` 请求按需展开。
- 用户固定 `/me` 路由不再被动态 UID 路由截获，公开用户入口统一为 `/api/users/uid/{uid}`。
- 海龟汤流派、汤色、主要/次要人物描述和规范标签实体；创建/更新校验分类、停用标签和最多 10 个标签，人物字段为必传字符串且允许任意 Unicode 或空文本。
- `Tag`、`SoupTag`、`TagAlias` 模型及作品/标签联合主键；旧 JSON 标签可通过迁移脚本规范化导入。
- 标签列表、海龟汤元数据筛选、标签使用数和成功标签筛选页浏览计数。
- PostgreSQL 自定义格式备份服务：密码不进入 `pg_dump` 命令参数，输出包含备份路径、UTC 时间和 SHA-256。
- 社交平台统一迁移入口：支持 `foundation|accounts|community|chat|broadcast|all` 阶段、`--dry-run`、动作计数和重复执行；当前 `foundation` 汇总既有元数据及最终结构迁移。

### 已实现主要代码，但仍需完整联调

- 注册、登录、刷新令牌和当前用户接口。
- 海龟汤发布、详情、揭示、评分、点赞和收藏。
- 帖子、比赛、社交、私信、成就、搜索和管理路由。
- 本地图片上传；配置完整对象存储参数时可切换 S3/R2。
- 前端页面和 API 客户端。
- 发布页已经提交必选流派、汤色、人数、正式标签 ID 和自定义标签；列表页支持流派、汤色和标签筛选，详情/排行消费者已改用规范评分字段。

### 明确未完成或存在风险

- 海龟汤评论 API 和前端评论组件未形成完整闭环。
- 部分旧路由仍使用 `id`、`user_id`、`TurtleSoup` 等过渡字段或别名，需要逐模块迁移到规范模型字段。
- 没有 Alembic；本批提供了专用、可重复执行且支持 dry-run 的海龟汤元数据迁移模块，但它不是通用生产迁移框架，生产执行前仍必须备份数据库。
- Redis、Elasticsearch、WebSocket、Celery、比赛结算和排行榜等依赖虽有配置或代码入口，但未完成端到端验证。
- 没有 Vitest 或完整浏览器 E2E 测试；当前前端生产构建已通过，但社交平台新增流程仍需在后续任务补齐 Playwright 验收。
- 本机配置启用 `AUTO_CREATE_DATABASE=true`；当前已连接并迁移真实 `turtle_soup`。服务端为 PostgreSQL 17.6，系统默认 PATH 中客户端为 16.14，备份时必须优先使用 `/www/server/pgsql/bin` 下的 17.6 工具。

## 5. 本机前置条件

建议版本：

- Python 3.9 以上；当前本机虚拟环境为 Python 3.12。
- Node.js 18 以上和 npm。
- PostgreSQL 14 以上。
- Redis 6 以上。

确认服务状态：

```bash
python3 --version
node --version
npm --version
pg_isready -h localhost -p 5432
redis-cli -u redis://localhost:6379/0 ping
```

若数据库尚未创建：

```bash
sudo -u postgres psql -c "ALTER USER postgres WITH PASSWORD 'postgres';"
sudo -u postgres createdb -O postgres turtle_soup
```

这些凭据仅适用于本机开发，不得用于公网或生产环境。

## 6. 首次初始化

Linux/macOS 推荐：

```bash
chmod +x dev.sh
./dev.sh init
```

该命令创建或复用 `backend/venv`，安装后端和前端依赖，并在 `.env` 不存在时从 `.env.example` 复制。本项目当前已配置 `backend/.env`，脚本会保留它。

手动安装：

```bash
cd backend
python3 -m venv venv
venv/bin/pip install -r requirements.txt

cd ../frontend
npm install
```

## 7. 本机环境配置

配置文件必须位于 `backend/.env`，因为后端从工作目录加载 `.env`，而 `dev.sh` 会先进入 `backend/` 再启动 Uvicorn。

当前本机配置如下，但秘密值不在手册中展示：

| 配置组 | 当前设置 |
| --- | --- |
| 应用 | `DEBUG=true`，`APP_URL=http://localhost:10000` |
| PostgreSQL | `postgres@localhost:5432/turtle_soup` |
| Redis | `redis://localhost:6379/0` |
| JWT | 本机随机密钥，访问令牌 30 分钟，刷新令牌 7 天 |
| SMTP | `smtp.126.com:465`，SSL，发件地址为已配置的 126 邮箱 |
| 上传 | `S3_ENABLED=false`，文件写入 `backend/storage` |
| Elasticsearch | `http://localhost:9200`，当前非核心启动依赖 |

`AUTO_CREATE_DATABASE` 仅应在本机开发环境开启。`.env.example` 默认关闭，生产环境必须通过受控迁移创建数据库和升级结构。

模板见 `backend/.env.example`。修改配置后必须重启后端；`get_settings()` 使用缓存，运行中的进程不会自动重新读取所有值。

安全要求：

```bash
chmod 600 backend/.env
git check-ignore -v backend/.env
```

预期权限为 `600`，且 Git 忽略检查命中根目录 `.gitignore`。禁止把 `.env`、SMTP 授权码或 JWT 密钥粘贴到 issue、日志、截图、提交和文档中。

## 8. 启动与停止

同时启动前后端：

```bash
./dev.sh dev
```

分别启动：

```bash
./dev.sh backend
./dev.sh frontend
```

访问：

- 前端：`http://localhost:10000`
- 后端健康检查：`http://localhost:8000/health`
- Swagger：`http://localhost:8000/docs`

`./dev.sh dev` 在前台运行，按 `Ctrl+C` 会停止两个子进程。后端首次成功启动会通过 `create_all()` 创建缺失表。

## 9. 验证命令

后端完整测试：

```bash
PYTHONPATH=backend backend/venv/bin/python -m pytest -q backend/tests
backend/venv/bin/python -m compileall -q backend/app
```

海龟汤元数据迁移先预览，再执行：

```bash
cd backend
PYTHONPATH=. venv/bin/python -m app.migrations.soup_metadata --dry-run
PYTHONPATH=. venv/bin/python -m app.migrations.soup_metadata
```

`--dry-run` 不执行 DDL 或数据写入，会报告将新增的列/表、标签和关联计数。正式执行会重复安全地添加缺失结构、从旧 `Soup.tags` 导入规范标签并重算 `usage_count`。生产数据库执行前必须先备份。

社交平台统一迁移必须先 dry-run，再创建备份，最后才可写入：

```bash
cd backend
PYTHONPATH=. venv/bin/python -m app.migrations.social_platform --phase all --dry-run
PATH=/www/server/pgsql/bin:$PATH PYTHONPATH=. venv/bin/python -m app.services.database_backup
PYTHONPATH=. venv/bin/python -m app.migrations.social_platform --phase all
```

备份默认写入 `backend/backups/`，该目录已被 Git 忽略。备份命令只输出路径、创建时间和 SHA-256，不输出数据库 URL 或密码；密码仅通过 `PGPASSWORD` 子进程环境传递。`pg_dump` 主版本不得低于数据库服务端，本机应使用上例 PATH。任何真实数据库结构或数据写入前都必须重新生成备份，不得复用旧文件。

前端类型检查和生产构建：

```bash
cd frontend
npm run build
```

服务启动后的最小检查：

```bash
curl --fail http://localhost:8000/health
curl --fail http://localhost:8000/docs >/dev/null
curl --fail http://localhost:10000 >/dev/null
```

SMTP 配置支持 126 邮箱的 SSL 端口 465。注册后会发送不透明验证令牌，数据库只保存 SHA-256 哈希；验证链接默认 30 分钟过期，重新发送至少间隔 60 秒。

2026-08-08 任务 1 验证基线：新增定向测试 `3 passed`；完整后端回归 `122 passed`；`compileall` 成功；前端 `npm run build` 成功。测试仍报告既有弃用警告，不影响本次退出状态。

2026-08-08 任务 2 验收：备份 `backend/backups/ctg-20260808T110459445874Z.dump`，SHA-256 `e9f6674e5559e30a25ddbb7f32cbe57e045d275c28ffd4628147d203e941bb06`，已通过独立 `sha256sum` 与 PostgreSQL 17.6 `pg_restore -l` 校验。真实库 `foundation` 应用 1 个 TEXT 转换动作；迁移后 `main_player_count`、`secondary_player_count` 均为 `text NOT NULL DEFAULT ''`，再次 dry-run 为 0 动作。定向后端测试 `18 passed`，完整回归 `126 passed`，汤相关 Playwright `4 passed`，`compileall` 与前端生产构建成功。

## 10. 本地上传

本机配置关闭 S3，`POST /api/uploads/images` 的文件写入 `backend/storage`，通过后端 `/storage/...` 暴露。目录属于运行时数据，已被 Git 忽略。

切换 S3/R2 时必须同时配置 `S3_ENDPOINT_URL`、`S3_BUCKET_NAME`、`S3_ACCESS_KEY`、`S3_SECRET_KEY` 并设置 `S3_ENABLED=true`。切换前需验证返回的对象 URL 是否符合存储服务的公开访问规则。

## 11. 常见故障

### 后端启动时报数据库连接失败

检查 PostgreSQL 是否启动，以及 `DATABASE_URL` 的用户名、密码和端口。本机 `AUTO_CREATE_DATABASE=true` 时应用会创建缺失数据库；若账号没有 `CREATEDB` 权限，可手动执行 `sudo -u postgres createdb -O postgres turtle_soup`。应用随后通过 `create_all()` 创建缺失表。

### `Settings` 报 extra inputs

`.env` 中存在 `config.py` 不接受的旧键。不要使用 `REDIS_HOST`、`REDIS_PORT`、`ELASTICSEARCH_HOST` 或 `ELASTICSEARCH_PORT`；应使用完整的 `REDIS_URL` 和 `ELASTICSEARCH_URL`。

### Redis 连接失败

运行：

```bash
redis-cli -u redis://localhost:6379/0 ping
```

预期返回 `PONG`。当前部分主要流程可能不立即访问 Redis，但相关异步、缓存或排行功能仍会受影响。

### 126 邮箱登录失败

确认邮箱后台已开启 SMTP 服务，使用的是授权码而不是网页登录密码，主机为 `smtp.126.com`、端口为 `465`、`SMTP_USE_SSL=true`。授权码变更后应更新 `.env` 并重启后端。

### 前端 API 返回 404 或连接拒绝

确认前端通过 `10000` 端口访问且后端运行在 `8000`。开发时应请求相对路径 `/api/...`，由 Vite 代理转发。

### 前端生产构建失败

当前 `MessageView.vue`、`PostDetailView.vue`、`NotificationView.vue`、`CompetitionDetailView.vue`、`CompetitionListView.vue`、`SearchView.vue`、`PostListView.vue` 和 `admin/AdminDashboard.vue` 是空文件。需要按模块设计补齐页面或移除对应路由后，`npm run build` 才能通过；不要用无业务含义的空模板掩盖未完成功能。

### 端口被占用

当前端口写在 `dev.sh` 和 `frontend/vite.config.ts` 中，不由 `.env` 的 `BACKEND_PORT` 或 `FRONTEND_PORT` 控制。改端口时需要同步修改启动脚本、Vite 代理、后端 CORS 和 `APP_URL`。

## 12. 后续工作优先级

1. 在本机 PostgreSQL 备份后运行海龟汤元数据迁移，并完成真实数据库与浏览器联调。
2. 实现竞赛关键词标签自动收录和后台标签/公告管理。
3. 修复比赛、帖子、社交、私信、成就和搜索路由的旧字段及前端接口错配，建立 OpenAPI 契约测试。
4. 补齐 8 个空 Vue 页面，完成导航、公告栏和全站响应式改造，使 `npm run build` 通过。
5. 为邮箱验证增加 Redis/IP 级限流、异步发送重试和浏览器端到端测试。
6. 完成海龟汤评论 API、回复规则和前端评论组件。
7. 为评分、点赞、收藏和竞赛收录增加数据库唯一约束与并发测试。
8. 最后推进 Redis 排行榜、比赛异步结算、WebSocket 通知、Elasticsearch 和生产部署。

每个阶段的完成条件应包括：迁移可重复执行、关键权限有测试、前后端联调成功、后端测试通过、前端构建通过，以及本手册同步更新。

## 13. 许可证与交接安全

源码使用限制以根目录 `LICENSE` 为准。交接前应再次确认：

- `backend/.env` 未被 Git 跟踪且权限为 `600`。
- SMTP 授权码和 JWT 密钥通过安全渠道交接，必要时立即轮换。
- 本地数据库和上传目录是否需要备份由项目负责人明确决定。
- 不把本机开发密码复用到生产环境。

## 14. 下一批设计基线

设计文档：`docs/superpowers/specs/2026-08-08-soup-metadata-announcement-design.md`。

已确认的产品规则：

- 海龟汤必须分别选择一个流派（本格/变格/鳖汤）和一个汤色（清汤/红汤/黑汤）。
- 发布时必须填写主要人数和次要人数；主要人数至少 1，次要人数可以为 0。
- 普通标签可多选，用户自定义标签创建后立即可用；管理员可以停用、改名和合并标签。
- 竞赛关键词必须绑定管理员已发布的正式标签。作品标签命中竞赛标签且发布时间在竞赛范围内时自动收录，联合唯一约束保证幂等。
- 标签页浏览量、标签使用作品数和作品详情浏览量使用不同统计口径。
- 公告由管理员创建、发布和撤回，前端在导航下显示不遮挡内容的响应式公告条。

当前明确的接口错配：

| 模块 | 问题 |
| --- | --- |
| 竞赛 | 路由使用不存在的 `creator_id`、`entry_tags`、`scoring_method`、`result_snapshot`、`updated_at` |
| 帖子/社交/私信 | 大量使用 `User.id`、`author_id`、`sender_id` 等旧字段，规范模型使用 `uid` 后缀 |
| 成就 | 过渡别名仍引用当前模型不存在的状态、时间和关系字段 |
| 前端海龟汤 | 排行、搜索、我的评分、更新和删除客户端方法没有对应后端路由，部分路径仍为 `/soups/*` |
| 前端认证 | 修改密码和重置密码客户端方法没有对应后端接口 |
| 前端页面 | 比赛、论坛、消息、通知、搜索、后台等 8 个 Vue 文件为空，生产构建会失败 |
| 汤底权限 | `GET /api/turtle-soups/{id}?reveal=true` 当前可能绕过作者/管理员判断并返回未公开汤底 |
| 匿名详情 | 公共路由依赖的 OAuth2 scheme 默认强制令牌，未登录访问可能收到 401 |
| 用户路由 | 动态 `/{user_id}` 在 `/me` 前声明，存在固定路径被截获的风险 |
| 错误显示 | soup store 仍读取 `response.data.message`，无法显示 FastAPI 的 `detail` |

实施时不得继续增加过渡别名掩盖字段问题。海龟汤新接口已切换为规范 Schema 和标签实体，旧 `Soup.tags` 仅保留为迁移输入；每修复其他模块，先定义 Pydantic 请求/响应 Schema，再补 API 契约测试和前端类型，最后删除该模块旧字段访问。
