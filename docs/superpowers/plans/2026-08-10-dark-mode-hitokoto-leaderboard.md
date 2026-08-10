# 深色模式、一言与排行榜视觉升级实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Execute this plan task-by-task with checkpoints.

**Goal:** 修复 class 深色模式、接入首页 Hitokoto 一言，并升级排行榜与共享页面动效。

**Architecture:** 继续使用现有 Vue 组件、Tailwind 4 和 CSS 动画。主题修复放在全局 Tailwind 变体；一言只在首页客户端读取并提供超时回退；排行榜只改展示层，不改变 Pinia store 或后端。

**Tech Stack:** Vue 3, TypeScript, Tailwind CSS 4, Vite, Heroicons。

## Global Constraints

- 不新增依赖，不改数据库、迁移或后端 API。
- 不运行 TDD 或浏览器测试；完成前运行 `npm run build`。
- 一言接口失败必须回退到本地文案。
- 动效必须尊重 `prefers-reduced-motion`。

### Task 1: 修复主题并接入一言

**Files:**
- Modify: `frontend/src/assets/main.css`
- Modify: `frontend/src/views/HomeView.vue`

- [ ] 在 Tailwind 导入后增加 `@custom-variant dark (&:where(.dark, .dark *));`。
- [ ] 在首页增加 `hitokotoText`、AbortController 和 `loadHitokoto()`，请求 `https://v1.hitokoto.cn/?encode=json`，仅接受非空 `hitokoto`。
- [ ] 将 hero kicker 的固定文案改为 `{{ hitokotoText }}`，失败保持 `每一条线索都算数`。
- [ ] 为首页硬编码浅色 hero 文本和场景补充深色样式，避免深色模式下标题仍为深蓝、场景仍为亮色。

### Task 2: 升级排行榜与通用页面动效

**Files:**
- Modify: `frontend/src/views/LeaderboardView.vue`
- Modify: `frontend/src/assets/main.css`

- [ ] 用 `topThree` 与 `restEntries` 计算值拆分榜单，前三名使用带奖牌、评分和作者信息的舞台卡片，其余使用可点击的列表行。
- [ ] 用 `router-link` 保持整行键盘可访问，保留标题、谜面、评分、评分人数和点赞数据。
- [ ] 增加榜单错峰入场、卡片悬浮与加载/空状态视觉，移动端单列并避免内容溢出。
- [ ] 给 `.page-shell > .page-container` 增加一次性入场动画，并在 reduced-motion 规则中关闭。

### Task 3: 验证与交付

**Files:**
- Inspect: `frontend/package.json`, `frontend/src`

- [ ] 运行 `npm run build`，确认 `vue-tsc` 与 Vite 均退出 0。
- [ ] 用 `rg` 核对 `@custom-variant`、Hitokoto URL、回退文案和排行榜关键 class 均存在。
- [ ] 检查 `git diff`，确保没有数据库、后端环境和依赖锁文件的非必要变更。
