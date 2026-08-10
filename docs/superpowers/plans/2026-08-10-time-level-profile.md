# 时段风景、等级徽章与个人背景实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Execute this plan task-by-task with checkpoints.

**Goal:** 实现 UTC+8 时段风景、随机签到经验、跨内容等级徽章和无需迁移的个人背景图。

**Architecture:** 后端只扩展现有 JSON 配置和响应字段；前端以 `LevelBadge` 统一等级视觉，以现有上传资源选择器保存个人背景；首页时段只影响展示 CSS。

**Tech Stack:** FastAPI, SQLModel, Vue 3, TypeScript, Tailwind CSS 4。

## Global Constraints

- 不新增数据库表/字段、迁移或 npm 依赖。
- 不使用 TDD，不运行浏览器测试；完成前运行后端测试和 `npm run build`。
- 经验按每 100 点一级，签到奖励闭区间随机 5–15。
- 动效和背景失败均有默认回退。

### Task 1: 时段风景

**Files:** `frontend/src/views/HomeView.vue`

- 增加 Asia/Shanghai 分钟读取、每分钟定时器和 `scene-${period}` class。
- 增加日出/清晨薄雾/中午/傍晚/日落/夜晚的天空、雾层和景观 CSS，并在组件卸载时清理定时器。

### Task 2: 经验与等级响应

**Files:** `backend/app/services/levels.py`, `backend/app/api/users.py`, `backend/app/api/posts.py`, `backend/app/api/messages.py`, `backend/app/api/social.py`, `backend/app/api/turtle_soups.py`, `backend/app/schemas/community.py`, `backend/app/schemas/profiles.py`, `backend/app/schemas/__init__.py`

- 改为线性等级和 `random.randint(5, 15)` 签到奖励。
- 给用户摘要/个人资料补 `level`、`level_band` 字段，所有作者/消息 payload 统一填充。
- 给 `User` 增加从 `notification_prefs` 读取个人背景字段的属性，并在 `/users/me` 更新时校验资源归属并写入 JSON。

### Task 3: 前端等级徽章、签到和个人背景

**Files:** `frontend/src/components/LevelBadge.vue`, `frontend/src/views/PostListView.vue`, `frontend/src/views/PostDetailView.vue`, `frontend/src/views/MessageView.vue`, `frontend/src/views/ProfileView.vue`, `frontend/src/views/SettingsView.vue`, `frontend/src/types/index.ts`

- 新建等级徽章组件，显示 `Lv.N`，根据等级档位使用圆角、阴影、柔和颜色。
- 在帖子、评论、私信会话/消息作者旁插入徽章；个人主页显示同一徽章。
- 设置页用已有图片资产列表上传/选择/移除背景，保存到个人资料接口；主页使用背景图并叠加可读性遮罩。

### Task 4: 验证与交付

- `pytest -q`（后端）和 `npm run build`（前端）。
- `git diff --check`、检查迁移/模型结构没有表字段变更。
- 提交并推送到现有 PR 分支。
