# 海龟汤社区平台 - 后端服务

基于 FastAPI + PostgreSQL + Redis 的海龟汤解谜社区平台后端。

## 功能特性

- **用户系统**：注册、登录、JWT 认证、邮箱验证、每日签到
- **帖子系统**：发帖、评论、点赞、收藏、投票帖
- **海龟汤系统**：发布谜题、评分（贝叶斯平均）、排行榜、汤底隐藏机制
- **比赛系统**：创建比赛、自动收录作品、计分排名
- **社交系统**：关注、拉黑、私信
- **成就系统**：可配置的成就条件、进度追踪
- **管理系统**：用户管理、处罚系统、举报处理、操作日志
- **搜索功能**：用户、帖子、海龟汤搜索

## 技术栈

- **框架**: FastAPI
- **数据库**: PostgreSQL + SQLAlchemy ORM
- **缓存**: Redis (排行榜、会话)
- **认证**: JWT (python-jose)
- **密码加密**: bcrypt

## 快速开始

### 1. 环境准备

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，配置数据库连接等
```

### 3. 启动服务

```bash
# 开发模式
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 生产模式
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 4. 访问 API 文档

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 项目结构

```
backend/
├── app/
│   ├── api/           # API 路由
│   │   ├── auth.py    # 认证相关
│   │   ├── users.py   # 用户相关
│   │   ├── posts.py   # 帖子相关
│   │   ├── turtle_soups.py  # 海龟汤相关
│   │   ├── competitions.py  # 比赛相关
│   │   ├── social.py  # 社交功能
│   │   ├── messages.py # 私信
│   │   ├── achievements.py # 成就
│   │   ├── admin.py   # 管理后台
│   │   └── search.py  # 搜索
│   ├── core/          # 核心配置
│   │   ├── config.py  # 配置管理
│   │   └── enums.py   # 枚举定义
│   ├── models/        # 数据模型
│   │   └── database.py # SQLAlchemy 模型
│   ├── schemas/       # Pydantic Schema
│   │   └── __init__.py
│   └── main.py        # 应用入口
├── tests/             # 测试文件
├── requirements.txt   # Python 依赖
├── .env.example       # 环境变量示例
└── README.md
```

## API 端点概览

### 认证
- `POST /api/auth/register` - 用户注册
- `POST /api/auth/login` - 用户登录
- `POST /api/auth/refresh` - 刷新令牌
- `GET /api/auth/me` - 获取当前用户
- `POST /api/auth/logout` - 登出

### 用户
- `GET /api/users/{user_id}` - 获取用户信息
- `PUT /api/users/me` - 更新个人信息
- `POST /api/users/signin` - 每日签到
- `GET /api/users/{user_id}/profile` - 用户主页

### 海龟汤
- `GET /api/turtle-soups/ranking` - 排行榜
- `POST /api/turtle-soups` - 发布海龟汤
- `GET /api/turtle-soups/{id}` - 获取详情
- `POST /api/turtle-soups/{id}/rate` - 评分
- `POST /api/turtle-soups/{id}/like` - 点赞
- `POST /api/turtle-soups/{id}/collect` - 收藏

### 社交
- `POST /api/social/follow` - 关注
- `DELETE /api/social/follow/{id}` - 取消关注
- `POST /api/social/blacklist` - 拉黑
- `DELETE /api/social/blacklist/{id}` - 解除拉黑

### 私信
- `POST /api/messages` - 发送私信
- `GET /api/messages/inbox` - 收件箱
- `GET /api/messages/sent` - 已发送

### 管理
- `GET /api/admin/users` - 用户列表
- `POST /api/admin/punish` - 执行处罚
- `GET /api/admin/reports` - 举报列表
- `GET /api/admin/logs` - 操作日志

## 许可证

MIT License
