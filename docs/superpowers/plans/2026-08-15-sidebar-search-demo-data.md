# 侧栏搜索与演示数据实施计划

> **For agentic workers:** 在当前工作区内联执行；不运行 TDD 或浏览器测试。

**目标：** 完成移动侧栏液态玻璃搜索区，并为 SQLite 测试环境提供可重复运行的关联演示数据。

**架构：** `NavBar.vue` 只调整搜索区模板与局部样式；`backend/scripts/seed_demo.py` 使用现有 SQLModel 模型和 bcrypt 哈希函数写入固定演示数据。脚本校验数据库驱动必须是 SQLite。

**技术栈：** Vue 3、Tailwind CSS 4、SQLModel、SQLite、bcrypt。

## 全局约束

- root 凭据为 `root` / `RootTest!2026`。
- 不新增依赖，不修改默认 PostgreSQL 配置。
- 不运行 TDD 或 Playwright。
- 数据脚本重复执行不产生重复账号、内容或关系。

### Task 1：侧栏搜索区

**文件：**
- 修改：`frontend/src/components/NavBar.vue`

- [ ] 将现有绝对定位按钮改为输入框下方的全宽按钮。
- [ ] 增加 `drawer-search-panel`、`drawer-search-input` 和 `drawer-search-submit` 局部样式，复用全局玻璃变量。
- [ ] 保留 `handleMobileSearch()`、禁用状态和无障碍标签。
- [ ] 运行 `npm run build`。

### Task 2：SQLite 演示数据脚本

**文件：**
- 创建：`backend/scripts/seed_demo.py`

- [ ] 校验 `engine.dialect.name == "sqlite"`，否则立即退出。
- [ ] 以固定用户名创建或更新 root 和 2 个普通用户，并用 `get_password_hash()` 写入密码。
- [ ] 以固定标题创建或更新 6 碗汤、5 篇帖子、比赛和公告。
- [ ] 按固定用户/目标组合补齐评分、点赞、评论和比赛条目，并同步内容计数。
- [ ] 提交事务并输出各类数据数量与 root 凭据。

### Task 3：运行验证

**文件：**
- 运行产物：`backend/test-data/ui-test.sqlite3`

- [ ] 对当前 SQLite 测试库执行种子脚本两次，确认数量不增长。
- [ ] 使用 `/api/auth/login` 验证 root 凭据和 root 角色。
- [ ] 检查 `/api/home/discovery`、海龟汤列表、排行榜和帖子列表均返回内容。
- [ ] 运行最终 `npm run build` 与 `git diff --check`，保持前后端监听 `0.0.0.0`。
