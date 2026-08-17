# 液态玻璃与页面动效实施计划

> **For agentic workers:** 按项目约束直接在当前工作区执行；不运行 TDD 或浏览器测试。

**目标：** 在现有 Vue 页面上统一液态玻璃视觉，替换首页旧默认文案，补充排行榜日夜主题、鼠标拖尾和加载动画，并完成 SQLite 基础运行验证。

**架构：** 复用 `main.css` 的 CSS 变量和现有 `glass-*` 类，新增 `App.vue` 的全局 loading/route 状态与独立鼠标拖尾组件；导航、首页、排行榜只负责自身语义和状态 class。后端 API、Pinia store 和数据库模型保持不变。

**技术栈：** Vue 3、TypeScript、Vue Router、Tailwind CSS 4、原生 CSS animation/requestAnimationFrame、FastAPI/SQLModel SQLite。

## 全局约束

- 不新增 npm 或 Python 依赖。
- 不运行 TDD，不运行 Playwright/浏览器测试；只做类型检查、生产构建和命令级基础检查。
- 尊重 `prefers-reduced-motion: reduce`；触屏设备不创建鼠标拖尾。
- 前端监听 `0.0.0.0:10000`，后端监听 `0.0.0.0:10001`。
- 测试数据库使用仓库内独立 SQLite 文件，不覆盖用户已有环境。

### Task 1: 全局玻璃基础与加载/拖尾

**文件：**
- 修改：`frontend/src/assets/main.css`
- 修改：`frontend/src/App.vue`
- 创建：`frontend/src/components/LiquidCursorTrail.vue`

- [ ] 扩展浅色/深色玻璃变量，增加 `glass-button` 的高光、按压态、焦点态，以及顶栏/侧栏专用表面 class。
- [ ] 在 `App.vue` 添加首次加载遮罩（品牌图标、波纹、可访问文本），用 `ref` 控制并设置最长显示保护；在路由事件链上显示/隐藏顶部 route progress。
- [ ] 在 `App.vue` 挂载桌面指针检测、`pointermove` + `requestAnimationFrame` 拖尾，限制最多 8 个节点，组件卸载时清理监听和节点；减少动态效果时跳过。
- [ ] 增加加载层、进度条、拖尾节点和路由淡入的 CSS，并在 reduced-motion 下禁用。
- [ ] 运行 `npm run build`，确认新增 TypeScript/CSS 编译无误。

### Task 2: 顶栏与移动侧栏玻璃化

**文件：**
- 修改：`frontend/src/components/NavBar.vue`
- 依赖：Task 1 的 `.glass-nav`、`.glass-drawer`、`.glass-button` 样式

- [ ] 将 sticky nav、搜索框、图标按钮、发布按钮、账户菜单替换为玻璃 class，保留现有导航、通知、主题切换和焦点行为。
- [ ] 将移动 drawer/backdrop 使用日夜主题玻璃层、内侧高光和阴影；不改变抽屉键盘焦点管理。
- [ ] 对可能过长的导航和搜索内容保持 `min-w-0`/truncate，验证 TypeScript 构建。

### Task 3：首页文案与按钮

**文件：**
- 修改：`frontend/src/views/HomeView.vue`

- [ ] 删除 `DEFAULT_HOME_LINE` 中“一碗汤，一群人，一场从为什么开始的推理冒险……”旧文案，替换为“每一条线索都算数”作为接口失败回退。
- [ ] 请求 `https://v1.hitokoto.cn/?encode=json` 恢复旧版一言，设置 6 秒超时，失败时保留本地回退且不影响首页内容接口。
- [ ] 将 hero 两个 router-link 使用 `glass-button` 与主题相关的强调色；保留图标、可访问文本和 hover/active 反馈。
- [ ] 运行 `npm run build` 并用 `rg` 核对旧文案不再出现在前端模板。

### Task 4：排行榜日夜模式顶部格子

**文件：**
- 修改：`frontend/src/views/LeaderboardView.vue`
- 修改：`frontend/src/assets/main.css`（仅在 Task 1 样式基础上补充需要的榜单主题 class）

- [ ] 将排行榜 header、scope tabs 和前三名 podium 卡片接入玻璃 surface class；浅色使用白色高透，深色使用黑色低亮玻璃。
- [ ] 保留现有前三名/完整榜单数据和路由链接，给 header 装饰、奖牌、评分和边框补充 `.dark` 对应色值。
- [ ] 确保顶部网格在移动端单列、内容不溢出，并保持现有错峰入场动画。
- [ ] 运行 `npm run build`。

### Task 5：SQLite 基础数据库与命令检查

**文件：**
- 创建：`backend/test-data/ui-test.sqlite3`（运行产物，加入 `.gitignore`）

- [ ] 使用进程级测试环境变量设置 `DATABASE_URL=sqlite:///./test-data/ui-test.sqlite3`、关闭 Redis/自动建库，并生成合法 `SECRET_KEY`。
- [ ] 使用现有 `app.db.init_db()` 创建 SQLite 表，查询 `sqlite_master` 确认核心表存在。
- [ ] 导入 FastAPI app 并使用测试客户端检查 `/health`，确认没有 PostgreSQL 连接错误。
- [ ] 执行 `npm run build` 作为最终前端检查；不运行 Playwright。

### Task 6：启动并监听 0.0.0.0

**文件：**
- 不修改业务文件；按需生成未跟踪运行日志。

- [ ] 使用 SQLite 测试环境启动 `uvicorn app.main:app --host 0.0.0.0 --port 10001`。
- [ ] 使用 `npm run dev -- --host 0.0.0.0 --port 10000` 启动前端。
- [ ] 用 `ss -ltnp` 或等价命令确认两个端口绑定到 `0.0.0.0`，并保留进程运行供用户访问。

## 自检

- `rg` 搜索旧默认文案、玻璃 class、loading/trail class，确认名称一致。
- `git diff --check` 确认无空白错误；忽略现有 `backend/venv` 与 Python 缓存等用户环境变更。
- SQLite 文件只用于本地验证，不改变默认 PostgreSQL 配置。
