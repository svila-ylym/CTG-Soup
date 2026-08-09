# 本机数据库、邮箱验证与认证安全设计

## 目标

让本机 PostgreSQL 数据库缺失时能够安全初始化；修复注册、登录和刷新令牌的前后端契约；实现“邮箱验证后才能登录”的闭环；修复本轮审计中确认的认证安全问题。

## 范围

本次包含：

- 仅在显式配置开启时自动创建缺失的 PostgreSQL 数据库。
- 用户待邮箱验证状态和邮箱验证记录。
- 注册、验证、重新发送、登录、刷新令牌和当前用户接口。
- 前端注册、登录、邮箱验证页面和错误显示。
- access/refresh token 类型隔离、统一 JWT 配置、开放重定向防护。
- 相关测试、示例配置和交接手册。

本次不包含：Alembic、Redis 分布式限流、JWT 服务端撤销列表、密码重置、第三方登录、全站旧路由字段迁移。

## 数据库初始化

新增 `AUTO_CREATE_DATABASE: bool = False`。只有该配置为 `true` 且 `DATABASE_URL` 使用 PostgreSQL 时，`init_db()` 才在目标数据库不存在时连接同一服务器的 `postgres` 管理库并执行创建。

数据库名使用 SQLAlchemy URL 解析，不拼接用户输入；存在性查询参数化，创建语句使用 psycopg2 SQL 标识符转义。连接失败或账号无 `CREATEDB` 权限时保留原异常，并输出不包含密码的操作提示。SQLite 或其他数据库不执行自动创建逻辑。

本机 `.env` 启用该开关，`.env.example` 默认关闭，避免生产环境意外获得建库行为。

## 用户与验证记录

规范 `UserStatus` 增加 `PENDING_EMAIL = "pending_email"`。注册用户初始状态为待验证；只有验证成功后才更新为 `ACTIVE`。

新增 `EmailVerification` 表：

- `id`：主键。
- `user_uid`：用户外键和索引。
- `token_hash`：SHA-256 哈希，唯一索引；数据库不保存明文令牌。
- `expires_at`：过期时间。
- `created_at`：创建时间，用于重发冷却。
- `used_at`：成功使用时间；非空记录不可再次使用。

验证令牌使用 `secrets.token_urlsafe(32)` 生成，默认 30 分钟过期。新令牌创建时使该用户以前未使用的令牌失效。重新发送至少间隔 60 秒；接口对不存在邮箱和已激活邮箱返回相同通用响应，降低账号枚举风险。

## 注册与邮件流程

注册流程：规范化用户名和邮箱，检查唯一性，哈希密码，以 `PENDING_EMAIL` 创建用户和验证记录并提交，然后发送邮件。

若 SMTP 发送失败，用户和验证记录保留，注册接口返回 `503` 和可操作提示；用户可在邮件服务恢复后调用重新发送。这样不会因外部邮件失败回滚已经占用的唯一用户名，也不会产生状态不明的事务。

邮件链接指向 `/verify-email?token=<opaque-token>`。邮件模板不再把用户 UID 当验证码。

验证接口在事务内查找令牌哈希，拒绝不存在、已使用或已过期令牌；成功后把用户设为 `ACTIVE`、写入 `used_at` 并提交。重复使用返回统一无效/过期信息。

## API 契约

- `POST /api/auth/register`：JSON `username`、`nickname`、`email`、`password`；成功返回用户公开字段，状态为 `pending_email`。
- `POST /api/auth/send-verification`：JSON `email`；始终返回通用信息，冷却期返回 `429`。
- `POST /api/auth/verify-email`：JSON `token`；成功返回确认信息。
- `POST /api/auth/login`：保持 OAuth2 form 编码；待验证账号返回 `403`。
- `POST /api/auth/refresh`：改为 JSON `{ "refresh_token": "..." }`，与前端一致。

前端统一优先读取 FastAPI 的 `detail`，兼容字符串及 `{message}` 形式，不再只读取不存在的 `message` 字段。

## JWT 与授权安全

access token 和 refresh token 的 `sub` 均编码为字符串 UID，并带 `token_type`。普通鉴权依赖必须验证 `token_type == "access"`；刷新接口必须验证 `token_type == "refresh"`。所有 JWT 操作只读取 `Settings.SECRET_KEY`，删除 `app/utils.py` 中硬编码密钥的认证实现或改为调用规范实现，避免同一应用出现两套签名源。

前端登录成功后的跳转只接受站内绝对路径：必须以单个 `/` 开头，拒绝 `//host`、带协议或其他外部值，防止开放重定向。

## 前端流程

注册成功后跳转 `/verify-email?email=<encoded-email>`，页面允许粘贴邮件令牌、自动读取链接中的 `token` 并提交验证，也允许按邮箱重新发送。验证成功后引导登录。

登录页显示后端实际错误；待验证错误中提供前往验证页的入口。前端类型中的用户字段与 `UserResponse` 对齐，状态增加 `pending_email`。

## 错误与隐私

- 响应不返回密码哈希、验证令牌哈希、JWT 密钥或 SMTP 凭据。
- 唯一性冲突对注册用户保持现有通用文案，不说明冲突的是用户名还是邮箱。
- 重新发送接口不暴露邮箱是否存在。
- 生产环境必须设置 `DEBUG=false`，避免数据库异常细节返回客户端；本机保留调试模式。
- SMTP 和数据库日志不得包含连接密码或明文验证令牌。

## 测试

- 数据库 URL 解析、数据库已存在、缺失时创建、开关关闭和非 PostgreSQL 分支。
- 注册创建待验证用户、哈希令牌、SMTP 成功和失败状态。
- 验证成功、过期、已使用和无效令牌。
- 重新发送通用响应和 60 秒冷却。
- 待验证用户拒绝登录；激活用户登录成功。
- refresh/access token 交叉使用均被拒绝。
- 前端 API 请求格式、错误提取和安全重定向辅助函数。
- 完整后端测试、应用导入、前端类型检查和构建；已有空 Vue 页面导致的构建阻塞需与本次改动区分。

## 迁移与兼容

当前项目没有 Alembic。`create_all()` 会为全新本机数据库创建新表，但不会给已有 PostgreSQL 枚举类型自动添加 `pending_email`。本机尚无目标数据库，因此可直接按新模型建表。已有部署必须在后续 Alembic 工作中增加枚举值和验证表迁移，不能依赖 `create_all()` 升级旧结构。
