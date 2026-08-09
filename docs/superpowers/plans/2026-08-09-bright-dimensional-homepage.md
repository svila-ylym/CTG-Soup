# 明亮立体风景首页 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将首页重构为明亮的立体文字与多层风景入口，并补齐高密度、可降级的页面动效。

**Architecture:** 保留现有排行榜 Store 和路由，不修改后端。`HomeView.vue` 负责风景 SVG、首页内容、视差状态和局部动画；`main.css` 负责路由过渡、通用交互反馈及减少动态效果降级。

**Tech Stack:** Vue 3、TypeScript、Tailwind CSS、CSS keyframes、内嵌 SVG、Heroicons。

## Global Constraints

- 不使用暗色霓虹或赛博风作为首页主视觉。
- 不引入外部图片、视频、Canvas 粒子系统或新动画库。
- 不修改后端接口、数据库或排行榜 Store 的数据语义。
- 不运行浏览器或 Playwright 测试。
- `prefers-reduced-motion: reduce` 下关闭循环、位移、视差和平滑滚动。

---

### Task 1: 重构立体风景首页

**Files:**
- Modify: `frontend/src/views/HomeView.vue`

**Interfaces:**
- Consumes: `useSoupStore().fetchLeaderboard(10)`、`soupStore.leaderboard`、`soupStore.isLoading`、现有 `/soups`、`/posts`、`/competitions`、`/leaderboard` 路由。
- Produces: 明亮多层风景首屏、立体逐字标题、社区入口卡片、排行榜立体卡片、桌面指针视差。

- [ ] **Step 1: 替换首页模板**

使用语义化 `section`、装饰性内嵌 SVG 和现有真实排行榜字段组成首屏、社区入口及热门汤三个区域；所有装饰层设置 `aria-hidden="true"`。

- [ ] **Step 2: 加入视差状态与生命周期清理**

在 `script setup` 中实现 `sceneStyle`、`handlePointerMove`、`resetPointer`，使用 CSS 变量 `--scene-x` 和 `--scene-y` 驱动图层，并在组件卸载时取消动画帧。

- [ ] **Step 3: 添加首页局部动画样式**

在组件 scoped CSS 中定义立体文字挤出、风景分层、云层漂移、湖面高光、便签悬浮、交错入场、卡片抬升和移动端降级。

### Task 2: 强化全局过渡并验证

**Files:**
- Modify: `frontend/src/assets/main.css`
- Test: production build and static diff checks

**Interfaces:**
- Consumes: `App.vue` 已使用的 `fade` transition 名称和现有按钮类。
- Produces: 页面淡入上移缩放、按钮按压反馈、平滑锚点滚动、全站减少动态效果规则。

- [ ] **Step 1: 更新全局过渡**

将 `.fade-*` 改为透明度、轻微上移和缩放的 320ms 组合，并补充按钮 hover/active 图形反馈。

- [ ] **Step 2: 添加减少动态效果规则**

在 `@media (prefers-reduced-motion: reduce)` 中关闭滚动平滑、关键帧、循环动画和大幅 transition。

- [ ] **Step 3: 运行静态验证**

Run: `npm run build`
Expected: `vue-tsc -b && vite build` exit 0.

Run: `git diff --check`
Expected: exit 0 with no output.

- [ ] **Step 4: 提交并更新已有 PR 分支**

```bash
git add frontend/src/views/HomeView.vue frontend/src/assets/main.css docs/superpowers/specs/2026-08-09-bright-dimensional-homepage-design.md docs/superpowers/plans/2026-08-09-bright-dimensional-homepage.md
git commit -m "feat: redesign homepage with dimensional scenery"
git push
```
