# 🐢 海龟汤社区平台

一个现代化的海龟汤解谜游戏社区平台，支持谜题发布、评分排行、比赛系统、社交互动等功能。

## 🚀 快速开始

### Linux/macOS 一键初始化与运行

```bash
chmod +x dev.sh
./dev.sh init   # 创建虚拟环境、安装依赖、生成 backend/.env
./dev.sh dev    # 后端 8000 + 前端 10000
```

单独运行：`./dev.sh backend` 或 `./dev.sh frontend`。默认使用清华 PyPI 和 npm 镜像；可通过 `PYTHON_INDEX_URL`、`NPM_REGISTRY_URL` 覆盖。

### 版本与 OTA 更新

运行版本以仓库根目录 `VERSION` 为准，页脚和 `/api/version` 会显示实际版本。GitHub Release 使用 `v1.2.3` 或 `1.2.3` 形式的 tag；管理后台 ROOT 账号可检查仓库的 Latest Release，并在确认后启动受控升级。

手动迁移或升级时使用：

```bash
./dev.sh init
./dev.sh migrate
./Update.sh --tag v1.2.3
```

`Update.sh` 会在切换代码前保留数据库、环境文件、前端构建和运行时文件备份，升级失败时恢复原代码、依赖和前端资源。升级必须配置 `CTG_RESTART_COMMAND`，且该命令必须调用脱离 updater 所在控制组的 helper；脚本会重启服务并轮询 `CTG_HEALTH_URL`，直到 `/health` 返回与发行版 tag 匹配的版本号后才解除 `private-storage/.ota-maintenance`。已知的同控制组 `systemctl restart`、`supervisorctl restart` 和 `docker compose restart` 形式会被拒绝；systemd 应使用 `systemd-run --no-block` 启动独立 helper，Screen 应使用独立会话/控制命令。重启或健康检查失败时会保留维护标记，避免旧进程继续使用已迁移的数据库。若数据库迁移已经开始后失败，管理员从备份恢复数据库后再删除该标记。`GithubPAT.txt` 仅用于本地 Git 操作，不会被应用读取或提交；GitHub API 读取公开仓库时不需要 token。

### Windows 用户 (推荐 PowerShell)

1. **右键点击** `setup.ps1` 选择 "使用 PowerShell 运行"
   或在项目目录打开 PowerShell 执行：
   ```powershell
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   .\setup.ps1
   ```

2. 脚本将自动：
   - 检测 Python 和 Node.js 环境
   - 创建虚拟环境并安装依赖
   - 生成 `.env` 配置文件
   - 提供交互式启动菜单

### Linux/Mac 用户

```bash
chmod +x setup.sh
./setup.sh
```

## 📋 手动启动方式

### 后端
```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate
# Linux/Mac: source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 前端
```bash
cd frontend
npm install
npm run dev
```

## 🌐 访问地址

- **前端**: http://localhost:10000
- **后端 API 文档**: http://localhost:8000/docs

## 📦 技术栈

### 后端
- Python 3.9+
- FastAPI
- PostgreSQL
- Redis
- SQLAlchemy

### 前端
- Vue 3
- TypeScript
- Vite
- Pinia
- Vue Router
- Tailwind CSS

## 📝 配置说明

首次运行会自动生成 `backend/.env` 文件，需要配置：

```env
# 数据库
DATABASE_URL=postgresql://postgres:password@localhost:5432/turtle_soup

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
SECRET_KEY=your-secret-key-here
```

## 📖 详细文档

请查看 `HANDOVER.md` 获取完整的项目交接文档，包括：
- 项目架构说明
- 功能完成度清单
- 核心业务流程
- 开发计划

## 🔧 常见问题

### PowerShell 执行策略限制
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

### 端口被占用
当前端口由 `dev.sh` 和 `frontend/vite.config.ts` 配置。修改端口时需同步调整启动脚本、Vite 代理、后端 CORS 和 `APP_URL`。

### 数据库连接失败
确保 PostgreSQL 服务已启动。本机可设置 `AUTO_CREATE_DATABASE=true` 自动创建 `turtle_soup`；若账号没有建库权限，请手动运行 `sudo -u postgres createdb -O postgres turtle_soup`。
