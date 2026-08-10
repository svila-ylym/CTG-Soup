# 深色模式、一言与排行榜视觉升级设计

## 目标

修复手动深色模式不生效的问题，在首页接入 Hitokoto JSON 一言，并让排行榜与普通页面拥有更清晰的层次和轻量动效。

## 方案

- 在 `frontend/src/assets/main.css` 声明 Tailwind 4 的 class 深色变体，使现有 `dark:*` 工具类跟随 `<html class="dark">`，不再依赖操作系统媒体查询。
- 首页在 `HomeView.vue` 内使用原生 `fetch` 请求 `https://v1.hitokoto.cn/?encode=json`，校验 `hitokoto` 字符串后替换固定副标题；请求设 6 秒超时并支持组件卸载取消，失败回退本地文案。
- 排行榜保留原有 API 与数据模型，页面改为前三名舞台卡片和其余作品列表，使用 CSS 错峰入场、悬浮和徽章层次；小屏改为单列。
- 给共享的 `.page-shell` 内容容器增加一次性入场动画，所有动效在 `prefers-reduced-motion: reduce` 下关闭。

## 约束与错误处理

- 不新增 npm 依赖，不改后端、数据库或 API 合同。
- Hitokoto 不可用时首页继续显示“每一条线索都算数”，不能阻塞首屏或抛出未处理异常。
- 不运行浏览器测试；使用 `npm run build` 与静态源码核对验证。
