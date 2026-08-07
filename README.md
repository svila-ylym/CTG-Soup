# 🐢 海龟汤社区平台

一个现代化的海龟汤解谜游戏社区平台，支持谜题发布、评分排行、比赛系统、社交互动等功能。

## 🚀 快速开始

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

- **前端**: http://localhost:3000
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

首次运行会自动生成 `.env` 文件，需要配置：

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
修改 `.env` 中的 `BACKEND_PORT` 或 `FRONTEND_PORT`

### 数据库连接失败
确保 PostgreSQL 服务已启动，并创建 `turtle_soup` 数据库
