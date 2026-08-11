# OTA 更新与版本显示设计

## 背景

CTG 需要在管理后台监测 GitHub 仓库的 Latest Release，并允许 ROOT 管理员触发一次受控升级。普通页面页脚需要显示实际运行中的版本号，发行版源码需要提供可迁移的 `Update.sh`、`dev.sh` 和 `setup.sh`。

## 目标

- 只有一个应用版本来源：仓库根目录 `VERSION`。
- 后端公开返回当前版本，前端页脚动态读取并显示。
- 管理后台只读取 GitHub `repos/svila-ylym/CTG-Soup/releases/latest`，不扫描发行版列表。
- Latest tag 去除可选的 `v` 前缀后与当前版本比较，明确显示最新版本、发布日期、链接和检查时间。
- 只有 ROOT 可触发升级；升级命令只能执行仓库内固定的 `Update.sh`，不接受客户端命令或路径。
- 升级脚本支持备份、获取指定发行版、依赖安装、可重复迁移、服务重启和失败回滚，并兼容现有 Screen/前台启动方式。

## 方案

### 版本源

新增根目录 `VERSION`，当前值与项目基线版本 `1.2.0` 一致。后端启动时读取该文件作为 `APP_VERSION`；仅 `APP_VERSION_OVERRIDE` 用于明确的定制构建。前端 `package.json` 保持构建元数据同步；运行时页脚从 `/api/version` 读取后端真实版本，并每 5 分钟刷新一次。

### Latest Release 检查

新增 `GET /api/admin/update/status`，由管理员访问。配置项包括仓库名、GitHub API 地址、可选只读 token、缓存时间和超时。服务只请求 `/releases/latest`，使用内存缓存避免重复请求；响应包含 `current_version`、`latest_version`、`tag_name`、`release_name`、`published_at`、`html_url`、`status`、`update_available`、`checked_at` 和错误信息。网络失败时保留当前版本并返回可读错误，不把 token 或响应中的敏感头写入日志。

### 在线升级

新增 `POST /api/admin/update/run`，仅 ROOT 可用。后端先取得或复用 Latest Release 的已校验 tag，再以参数数组启动仓库根目录的 `Update.sh --tag <tag>`；任务在后台运行，状态写入进程内状态对象和受限日志文件。并发请求返回冲突，不允许通过 API 注入 shell 参数。升级脚本成功后服务由原有 Screen/进程管理方式重新启动；API 返回任务 ID 和日志位置，不阻塞 HTTP 请求。

### Update.sh

脚本默认以当前仓库为工作目录，要求 git、Python、Node、npm 和可用的 `backend/.env`。流程为：

1. 校验 tag 格式和 git 仓库，创建带时间戳的数据库备份（若配置为 PostgreSQL）以及 `.env`、存储目录的文件备份。
2. `git fetch --tags origin`，验证目标 tag 对应提交，再保存当前提交并切换到目标 tag。
3. 运行 `dev.sh init` 安装/更新依赖，执行所有现有的可重复迁移入口。
4. 通过必填的 `CTG_RESTART_COMMAND` 调用脱离 updater 控制组的重启 helper，并轮询健康地址确认新版本已经接管后才解除维护标记；会杀死 updater 的同控制组重启命令、未配置命令或健康检查失败都会保持维护模式。
5. 任一步失败时恢复原提交和配置备份，输出失败原因并返回非零状态；备份保留供人工恢复。

`setup.sh` 改为调用 `dev.sh init`，保留交互式启动兼容性；`dev.sh` 继续承担统一依赖安装和启动入口，并增加非交互环境下可复用的参数。

## 安全与运维

- GitHub token 只从环境变量读取，不提交到仓库；公开仓库默认无需 token。
- API 仅允许 ROOT 执行升级，脚本路径和仓库路径固定为服务配置解析后的仓库根目录。
- 升级任务日志只保存 stdout/stderr 摘要和退出码，禁止记录环境变量、数据库 URL 和 token。
- 备份、迁移和回滚操作保持幂等；升级前应确保工作区无未提交生产改动。

## 验证

- 后端单元测试覆盖版本读取、Latest 响应解析、权限、缓存和升级命令参数。
- 前端执行类型检查和生产构建。
- Shell 使用 `bash -n`，以 mock git/依赖命令验证成功与失败回滚分支。
- 不在本地执行真实升级；通过 API/脚本 dry-run 验证，不触碰生产数据库。
