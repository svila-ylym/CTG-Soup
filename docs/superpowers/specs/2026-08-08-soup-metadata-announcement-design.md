# 海龟汤元数据、竞赛收录、公告与接口治理设计

更新日期：2026-08-08

## 1. 目标与分期

本设计解决四类需求：海龟汤的结构化分类和标签、按竞赛关键词自动收录、标签与内容浏览统计、公告栏和响应式体验；同时把当前已发现的后端旧字段与前端接口错配纳入同一套契约治理方案。

需求拆成三个可独立验收的阶段：

1. **内容元数据阶段**：流派、汤色、人数、系统标签、自定义标签、标签统计、发布和列表筛选。
2. **竞赛与公告阶段**：竞赛关键词自动收录、重复收录幂等、管理员标签/公告管理、前台公告栏。
3. **契约与响应式阶段**：迁移旧路由字段、补齐前端空页面、统一 API 类型和移动端布局。

每一阶段都必须有数据库迁移、API 契约测试、前端类型检查、构建和交接文档更新。

## 2. 内容元数据模型

### 2.1 必选维度

流派和汤色是两个不同的必选维度，不合并为一个字符串：

| 字段 | 初始值 | 说明 |
| --- | --- | --- |
| `genre` | `本格`、`变格`、`鳖汤` | 叙事/推理流派。后台可启用、停用和排序。 |
| `soup_color` | `清汤`、`红汤`、`黑汤` | 汤底表现分类。后台可启用、停用和排序。 |

每个海龟汤必须恰好选择一个流派和一个汤色。历史数据迁移前使用显式的 `未分类` 过渡值，禁止在 API 中用缺省值掩盖迁移遗漏。新建和更新接口拒绝停用项。

### 2.2 人数配置

海龟汤增加：

- `main_player_count`：主要人数，整数，最小值 1。
- `secondary_player_count`：次要人数，整数，最小值 0。

两者都在发布接口中必填，详情、列表和竞赛快照中返回。总人数由客户端展示为两者之和，不落库重复字段。后端负责校验上限，初始上限为 100，后续可由配置调整。

### 2.3 标签

标签从 `Soup.tags` JSON 数组迁移为规范化实体：

- `Tag`：`id`、唯一规范名 `slug`、展示名 `name`、`kind`（`system`/`custom`）、`status`（`active`/`disabled`）、`description`、`sort_order`、`view_count`、`usage_count`、创建/更新时间。
- `SoupTag`：`soup_id`、`tag_id`、创建时间，联合唯一约束防重复。
- 可选 `TagAlias`：旧名到规范标签的映射，用于改名和合并后的兼容查询。

规范化规则：去首尾空格、连续空白折叠、大小写不敏感的 `slug`、长度 1～30、拒绝控制字符和 HTML。单个海龟汤最多 10 个标签，系统维度不占用自定义标签配额。

系统标签由管理员创建、发布、停用、改名和合并。用户自定义标签创建后立即公开可用，后台可以停用、合并到系统标签或合并到另一个自定义标签；合并必须迁移关联并保留别名，不能静默删除历史筛选条件。停用标签不能用于新作品，但历史作品仍保留可显示的名称。

竞赛关键词只能引用状态为 `active` 的标签，不能接受仅存在于作品 JSON 中的自由字符串。

## 3. 浏览统计

统计拆成两个口径，避免把作品浏览与标签页浏览混为一谈：

- `Tag.view_count`：用户打开标签筛选页的请求次数。
- `Tag.usage_count`：当前公开作品与该标签的关联数量；通过关联表维护或定期重算。
- `Soup.view_count`：作品详情页有效浏览次数，保留现有字段。

标签筛选接口返回 `view_count`、`usage_count` 和分页结果；请求成功且返回页面时原子增加一次 `view_count`。作品详情浏览时只增加 `Soup.view_count`，不重复给每个标签增加浏览，避免一条详情请求被多个标签放大。后续如需“标签下作品曝光量”，新增独立事件表，不复用以上字段。

## 4. API 契约

### 4.1 海龟汤

- `POST /api/turtle-soups`：JSON 必填 `title`、`puzzle`、`solution`、`genre`、`soup_color`、`main_player_count`、`secondary_player_count`；`tag_ids` 为已存在标签 ID，`custom_tags` 为用户新建标签名；可选 `is_revealed`。
- `GET /api/turtle-soups`：支持 `genre`、`soup_color`、`tag`/`tag_id`、`competition_id`、`sort_by`、分页；返回统一 `items/total/page/page_size/total_pages`。
- `GET /api/turtle-soups/{id}`：返回流派、汤色、人数、规范标签、统计和作者权限状态；详情浏览计数只在有效公开内容上增加。
- `PUT /api/turtle-soups/{id}`：作者或管理员更新全部元数据，后端重新校验停用项和标签权限。
- `GET /api/tags`：公开返回 active 标签，支持 `kind`、关键词、分页和热度排序，同时增加标签页面浏览量。

所有响应统一使用 `uid`、`author_uid`、`average_score`、`rating_count`、`favorite_count`；不再混用 `id`、`author_id`、`avg_score`、`score_count`。

### 4.2 后台配置

- `GET/POST/PUT /api/admin/tags`：标签列表、创建系统标签、修改状态/排序/描述。
- `POST /api/admin/tags/{id}/merge`：指定目标标签，迁移 `SoupTag`、更新竞赛引用、保留别名。
- `GET /api/admin/soup-taxonomy`：管理流派和汤色启用状态、排序和展示名。

普通用户只能创建自定义标签并在作品中使用，不能创建系统标签、停用标签或修改统计字段。

## 5. 竞赛自动收录

竞赛模型统一为：

- `required_tag_ids`：管理员选择的 active 标签 ID 集合。
- `keyword`：面向用户展示的竞赛关键词，必须绑定至少一个标签；为了兼容用户描述的“2026原创大赛”，创建竞赛时由后台把该关键词解析为一个正式标签。
- `creator_uid`、时间范围、评分方式、`top_n`、状态和结算快照。

发布作品提交成功、标签关联提交成功后，异步或事务后钩子执行：查找时间范围内状态为 pending/ongoing 且任一 `required_tag_id` 命中的竞赛，写入 `CompetitionEntry`。`(competition_id, soup_id)` 唯一约束保证重复发布/编辑幂等。作品编辑增加或删除标签时重新评估未结算竞赛；已结算竞赛保留快照，不回溯改变排名。

竞赛详情返回收录原因（命中的标签）、收录时间和作品列表。管理员可手动移除一条收录，但不能绕过唯一约束重新创建重复记录。关键词匹配只按规范标签 ID，不使用模糊字符串匹配。

## 6. 公告栏

新增 `Announcement`：`id`、`title`、`content`、`status`（draft/published/expired）、`priority`、`published_at`、`expires_at`、`author_uid`、创建/更新时间。

- `GET /api/announcements`：公开返回当前有效公告，按优先级和发布时间排序，支持分页。
- `POST/PUT/DELETE /api/admin/announcements`：管理员创建、发布、编辑、撤回和删除；删除保留操作日志。
- 前端在导航下方显示响应式公告条；多条公告使用可关闭的轮播/列表，不遮挡主导航。关闭状态只保存在当前浏览器，不修改服务端发布状态。

公告正文按纯文本或受限 Markdown 保存和渲染，禁止直接注入未消毒 HTML。管理员接口复用现有 RBAC 和审计日志。

## 7. 接口错配与潜藏问题治理

下一阶段必须以 OpenAPI/Schema 为单一契约，优先修复以下已确认问题：

| 模块 | 当前问题 | 设计修复 |
| --- | --- | --- |
| 竞赛 | `creator_id`、`entry_tags`、`scoring_method`、`result_snapshot`、`updated_at` 不存在或命名不一致 | 统一 `creator_uid`、`required_tag_ids`、`score_type`，补结果快照字段或从响应移除 |
| 帖子 | 使用 `User.id`、`Post.author_id`，模型实际为 `uid`、`author_uid` | 全部改用规范 UID 字段，并补契约测试 |
| 社交 | `follower_id/followee_id`、`blocker_id/blocked_id` 为旧字段 | 迁移到 `follower_uid/followed_uid`、`blocker_uid/blocked_uid` |
| 私信 | `sender_id/receiver_id` 为旧字段 | 统一 `sender_uid/receiver_uid`，前端类型同步 |
| 成就 | 过渡别名后仍引用 `is_active`、`updated_at`、`user_id`、关系属性 | 按 `Achievement`、`UserAchievement.user_uid` 重写响应和查询 |
| 前端海龟汤 | `/soups/*` 排行/搜索/我的评分接口不存在，真实前缀为 `/turtle-soups` | API 客户端只保留真实路由，并统一错误 `detail` |
| 前端认证 | 修改密码、重置密码接口尚未实现 | 页面隐藏未实现入口，或先补后端契约再开放 |
| 前端页面 | 比赛、论坛、消息、通知、搜索、后台等 8 个 Vue 文件为空 | 按阶段补页面；路由在组件完成前显示明确的未开放状态 |
| 上传 | S3 返回 URL 依赖公开访问假设，本地路径未做缓存策略 | 增加对象 URL 配置和安全响应头，保持内容类型白名单 |
| 汤底权限 | 详情接口直接信任公开查询参数 `reveal=true`，普通请求可读取未公开汤底 | 查询参数只能表达展示意图，最终揭示必须由作者/管理员权限或已公开状态决定 |
| 可选认证 | 公共详情使用 `Depends(get_current_user)`，但 OAuth2 scheme 默认 `auto_error=true`，匿名请求会先返回 401 | 新增 `get_optional_current_user`，使用 `OAuth2PasswordBearer(auto_error=false)` 并只在存在令牌时解析 |
| 用户路由 | 动态 `/{user_id}` 在 `/me` 之前声明，可能截获固定路径并产生 422 | 固定路由优先，公开用户统一 `/uid/{uid}`，删除含糊动态路径 |
| 错误响应 | 前端 soup store 仍读取 `data.message`，FastAPI 通常返回 `detail` | 全部 API 客户端复用 `extractApiError` |
| CORS/公开地址 | CORS 来源硬编码本机地址，邮件 `APP_URL` 与远程访问地址可能不一致 | 使用显式 `CORS_ORIGINS` 与公开 `APP_URL` 配置，监听地址不作为用户链接 |

## 8. 响应式设计验收

导航和公告在 320px～1440px 宽度下不横向溢出；移动端使用折叠菜单，筛选控件可换行，标签使用可滚动/换行布局；发布表单把必选流派、汤色和人数放入首屏可见区域。列表卡片使用稳定网格和固定统计行，不能因标签数量或长标题改变布局。后台表格在窄屏转为分组列表，公告条在移动端允许多行。

响应式实现只使用现有 Vue/Tailwind 体系，不引入第二套组件库。验收必须覆盖 375x812、768x1024、1440x900 三个视口，并检查空状态、加载状态、错误状态和长标签。

## 9. 数据迁移与回滚

当前没有 Alembic，不能用 `create_all()` 作为线上升级方案。实施阶段先新增可重复执行的迁移脚本：

1. 创建标签、关联、别名、公告和竞赛收录约束。
2. 从旧 `Soup.tags` JSON 数组导入 `Tag`/`SoupTag`，未知值创建 custom 标签并记录导入日志。
3. 为旧作品填充 `genre=未分类`、`soup_color=未分类`、人数默认值，并在管理后台强制补全后才允许编辑发布。
4. 为旧竞赛把 `required_tags` 字符串解析为规范标签 ID；无法解析的竞赛进入人工修复队列。

每一步都支持 dry-run、计数校验和回滚备份。生产数据库必须先备份；本机全新数据库可以由 `create_all()` 创建，但仍需运行种子数据脚本。

## 10. 验收与安全

验收包含：API OpenAPI 快照、后端契约和权限测试、标签统计幂等测试、竞赛自动收录唯一性测试、公告消毒测试、前端类型检查、生产构建和三视口截图检查。

安全要求：标签和公告文本防 XSS；所有管理修改写操作日志；作品创建/编辑仍需 active 用户；竞赛收录不信任客户端传入的 competition ID；标签统计使用原子增量；不返回内部数据库字段、密码哈希或管理凭据。

实现第一批代码前必须先加入汤底越权读取回归测试、匿名公开详情测试和固定/动态路由顺序测试。这三项属于安全与可用性阻塞，不等待元数据功能完成后再修。
