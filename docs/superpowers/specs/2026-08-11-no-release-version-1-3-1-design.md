# GitHub 无发行版状态与 1.3.1 版本设计

## 目标

当 GitHub 仓库尚未发布正式 Release 时，管理后台将 GitHub API 的 `404 Not Found` 展示为正常的“暂无正式发行版”，而不是“检查失败”。同时将应用运行版本从 `1.2.0` 更新为 `1.3.1`。

## 后端行为

- `LatestReleaseService` 仍只请求 GitHub `releases/latest`，不回退到 tags、草稿或预发行版列表。
- GitHub 明确返回 404 时，返回 `status="no_release"`、`update_available=false`，所有发行版字段为空，`error` 为空。
- 网络错误、超时、权限问题、无效 JSON 和其他 HTTP 错误继续返回 `status="error"`，避免掩盖真实故障。
- OTA 执行接口在 `no_release` 状态下继续返回“没有可用的新版本”，不会启动升级任务。

## 前端行为

- 系统更新面板支持 `no_release` 状态。
- Latest 字段显示“暂无正式发行版”，状态字段同样显示“暂无正式发行版”，不使用红色错误样式。
- ROOT 的“升级到 Latest”按钮保持禁用。

## 版本来源

- 根目录 `VERSION` 更新为 `1.3.1`。
- `/api/version`、`/health`、页脚和 OTA 当前版本继续从同一版本源读取，无额外硬编码。

## 验证与发布边界

- 增加后端测试，覆盖 404 与其他 HTTP 错误的不同结果。
- 运行 OTA 定向测试、后端全量测试、前端生产构建、Python 编译、Shell 语法和 Git 差异检查。
- 更新现有 PR 分支并重新部署远端 Screen 服务。
- 不自动创建 GitHub Release；首个 `v1.3.1` Release 应在 PR 合并后由仓库维护者发布，确保发行版源码包含本次变更。
