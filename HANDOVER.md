# 海龟汤社区平台 - 项目交接文档

## 📋 项目概况

**项目名称**: 海龟汤解谜社区平台  
**技术栈**: Python FastAPI + Vue 3 + PostgreSQL + Redis + Elasticsearch  
**开发阶段**: 后端 API 框架完成，数据模型定义完整，前端待开发  
**最后更新**: 2024 年 1 月 (本次更新)  

---

## 🏗️ 项目架构

```
/workspace
├── backend/                 # Python FastAPI 后端
│   ├── app/
│   │   ├── main.py         # 应用入口 (已配置 CORS、异常处理)
│   │   ├── db.py           # 数据库连接 (支持环境变量)
│   │   ├── utils.py        # 工具函数 (贝叶斯评分、JWT、密码哈希)
│   │   ├── core/
│   │   │   └── config.py   # 配置管理 (pydantic-settings)
│   │   ├── models/
│   │   │   └── models.py   # 所有 SQLModel 定义 (15+ 表完整)
│   │   ├── schemas/        # Pydantic Schema (待完善)
│   │   ├── api/            # API 路由 (10 个模块已完成框架)
│   │   │   ├── auth.py     # 认证
│   │   │   ├── users.py    # 用户
│   │   │   ├── posts.py    # 帖子
│   │   │   ├── turtle_soups.py  # 海龟汤
│   │   │   ├── competitions.py  # 比赛
│   │   │   ├── social.py   # 社交
│   │   │   ├── messages.py # 消息
│   │   │   ├── achievements.py # 成就
│   │   │   ├── admin.py    # 管理后台
│   │   │   └── search.py   # 搜索
│   │   └── core/           # 核心配置
│   ├── requirements.txt    # Python 依赖
│   ├── .env.example        # 环境变量模板
│   └── README.md           # 后端说明
├── frontend/              # Vue 3 前端
│   └── src/               # 源代码目录结构已创建 (components/views/router/store/api/assets)
├── setup.sh               # Linux/Mac一键启动脚本 ✓
├── setup.bat              # Windows一键启动脚本 ✓
└── HANDOVER.md            # 本交接文档
```

---

## ✅ 已完成功能

### 1. 基础设施
- [x] 项目目录结构搭建
- [x] Python 虚拟环境配置
- [x] 前后端分离架构
- [x] 一键启动脚本（Windows/Linux）
- [x] 环境变量配置文件模板 (.env.example)
- [x] 数据库连接模块 (支持从.env 读取)

### 2. 数据模型（完整定义 - 15 张表）
| 模块 | 表名 | 说明 |
|------|------|------|
| 用户系统 | users | 含角色、状态、积分、签到、通知偏好 |
| 处罚系统 | punishments | 支持撤销与审计，可逆操作 |
| 帖子系统 | posts | 支持分区、标签、投票类型 |
| 评论系统 | comments | 支持回复嵌套 (parent_id) |
| 海龟汤系统 | soups | 谜面/汤底、评分、贝叶斯平均分 |
| 评分系统 | ratings | 1-10 分 (0.5 步进), 唯一约束防重复 |
| 点赞系统 | likes | 统一表结构 (post/soup/comment) |
| 收藏系统 | favorites | 统一表结构 (post/soup) |
| 社交关系 | follows | 单向关注，互关即好友 |
| 黑名单 | blacklists | 实时生效，阻断交互 |
| 比赛系统 | competitions | 自定义页面配置 (JSON) |
| 比赛作品 | competition_entries | 自动参赛，结算快照 |
| 成就系统 | achievements + user_achievements | 条件类型 + 进度追踪 |
| 称号系统 | titles | 绑定成就 |
| 消息系统 | private_messages + notifications | 站内信 + 系统通知 |
| 举报系统 | reports | 多目标类型，处理流程 |
| 操作日志 | operation_logs | 审计追踪，支持回滚 |
| 签到记录 | signin_records | 每日签到，唯一约束 |

### 3. 核心算法与工具
- [x] 贝叶斯平均评分公式：`(C*m + R*v)/(C+v)`
- [x] JWT Token 生成与验证 (python-jose)
- [x] 密码哈希 (bcrypt via passlib)
- [x] 配置管理 (pydantic-settings)

### 4. API 路由框架（10 个模块）
- [x] `auth.py` - 注册/登录/JWT/刷新令牌
- [x] `users.py` - 个人信息/签到/主页
- [x] `posts.py` - 帖子 CRUD
- [x] `turtle_soups.py` - 海龟汤 CRUD/评分/排行
- [x] `competitions.py` - 比赛管理
- [x] `social.py` - 关注/拉黑
- [x] `messages.py` - 私信/通知
- [x] `achievements.py` - 成就进度
- [x] `admin.py` - 管理后台/处罚/举报
- [x] `search.py` - 全文搜索

### 5. 主应用配置
- [x] FastAPI 应用初始化
- [x] CORS 中间件配置 (允许前端跨域)
- [x] 全局异常处理 (验证错误/SQL 错误)
- [x] 日志配置
- [x] 生命周期事件 (startup/shutdown)

---

## 🚧 待完成功能

### 高优先级（P0）- 本周内完成
| 模块 | 任务 | 预计工时 | 状态 |
|------|------|----------|------|
| Schema | 完善所有 Pydantic Schema | 2h | ⏳ |
| API | 用户认证完整实现 | 2h | ⏳ |
| API | 海龟汤 CRUD 接口 | 3h | ⏳ |
| API | 评分接口 (含实时更新) | 2h | ⏳ |
| API | 排行榜接口 (Redis 缓存) | 2h | ⏳ |
| 数据库 | 迁移脚本 (Alembic) | 2h | ⏳ |
| 前端 | 项目初始化 (Vite+Vue3) | 1h | ⏳ |
| 前端 | 登录/注册页面 | 3h | ⏳ |

### 中优先级（P1）- 下周完成
| 模块 | 任务 | 预计工时 |
|------|------|----------|
| API | 帖子系统完整接口 | 3h |
| API | 评论系统接口 | 2h |
| API | 社交关系接口 | 2h |
| API | 私信接口 | 2h |
| API | 签到接口 | 1h |
| Redis | 排行榜缓存策略 | 2h |
| 定时任务 | 比赛自动结算 (Celery) | 3h |
| 前端 | 海龟汤发布/详情/列表页 | 6h |
| 前端 | 论坛页面 | 4h |

### 低优先级（P2）- 后续迭代
| 模块 | 任务 | 预计工时 |
|------|------|----------|
| API | 成就系统进度追踪 | 3h |
| API | 举报处理接口 | 2h |
| API | 管理后台完整接口 | 6h |
| Elasticsearch | 全文搜索集成 | 4h |
| WebSocket | 实时通知推送 | 4h |
| 邮件服务 | SMTP 验证与通知 | 2h |
| 前端 | 比赛页面 | 4h |
| 前端 | 管理后台界面 | 8h |
| 前端 | 个人中心/设置 | 4h |

---

## 🔑 核心运行逻辑

### 1. 启动流程
```
用户运行 setup.sh/setup.bat
    ↓
[1] 检查 Python/Node.js 环境
    ↓
[2] 创建虚拟环境 (backend/venv)
    ↓
[3] 安装依赖 (pip + npm)
    ↓
[4] 生成 .env 配置文件
    ↓
[5] 选择启动模式
    ├─ 仅后端 → uvicorn app.main:app --port 8000
    ├─ 仅前端 → npm run dev (Vite, port 5173)
    └─ 同时启动 → 两个进程并行
```

### 2. 请求处理流程
```
HTTP 请求
    ↓
FastAPI 路由匹配 (app/api/*.py)
    ↓
依赖注入 (Depends)
    ├─ 获取当前用户 (JWT 验证)
    └─ 权限检查 (角色/状态/黑名单)
    ↓
业务逻辑处理
    ↓
数据库操作 (SQLModel → PostgreSQL)
    ↓
[可选] 缓存更新 (Redis)
    ↓
返回 JSON 响应
```

### 3. 海龟汤评分流程
```
POST /api/soups/{soup_id}/rating
    ↓
验证:
    ├─ 用户是否已评过 (ratings 唯一约束)
    ├─ 用户状态是否正常 (非禁言/封号)
    └─ 分数范围 (1-10, 0.5 步进)
    ↓
写入 ratings 表
    ↓
重新计算该汤:
    ├─ avg_rating = SUM(score) / COUNT(*)
    └─ bayesian = (C*m + R*v) / (C+v)
    ↓
更新 soups 表
    ↓
更新 Redis 排行榜缓存 (ZSET)
    ↓
[异步] 发送通知给作者
```

### 4. 比赛自动参赛流程
```
发布海龟汤时:
    ↓
查询进行中的比赛 (status=ONGOING)
    ↓
检查汤的 tags 是否匹配 required_tags
    ↓
若匹配 → 创建 competition_entries 记录
    ↓
比赛结束 (定时任务):
    ├─ 查询所有参赛作品
    ├─ 按计分方式排序
    ├─ 生成排名写入 rank 字段
    ├─ 快照结果
    └─ 发送通知
```

### 5. 黑名单拦截逻辑
```
任何交互前检查:
    ↓
SELECT FROM blacklists 
WHERE (blocker=A AND blocked=B) OR (blocker=B AND blocked=A)
    ↓
结果判断:
    ├─ 单方拉黑 (A 拉黑 B) → A 无法对 B 操作
    ├─ 互相拉黑 → 双方完全不可见
    └─ 无记录 → 正常执行
    ↓
同时检查用户全局状态:
    ├─ status=BANNED → 禁止所有操作
    └─ status=SILENCED → 禁止发言类操作
```

---

## 📦 依赖清单

### 后端 (Python) - requirements.txt
```
fastapi>=0.100.0
uvicorn[standard]>=0.23.0
sqlmodel>=0.0.14          # SQLAlchemy + Pydantic
psycopg2-binary>=2.9.0    # PostgreSQL 驱动
redis>=4.5.0              # Redis 客户端
python-jose[cryptography] # JWT
passlib[bcrypt]           # 密码哈希
python-multipart          # 表单解析
httpx                     # HTTP 客户端
elasticsearch>=8.0.0      # 搜索引擎
python-dotenv             # 环境变量
pydantic-settings         # 配置管理
alembic                   # 数据库迁移
```

### 前端 (Node.js) - 待创建 package.json
```json
{
  "dependencies": {
    "vue": "^3.3.0",
    "vue-router": "^4.2.0",
    "pinia": "^2.1.0",
    "axios": "^1.4.0",
    "element-plus": "^2.3.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^4.0.0",
    "vite": "^5.0.0"
  }
}
```

### 外部服务
| 服务 | 版本 | 用途 |
|------|------|------|
| PostgreSQL | 14+ | 主数据库 |
| Redis | 6+ | 缓存/会话/任务锁 |
| Elasticsearch | 8+ | 全文搜索 |
| SMTP | - | 邮件验证/通知 |

---

## 🔐 权限体系

| 角色 | 权限范围 |
|------|----------|
| **根用户 (root)** | 全部权限：管理员管理、系统配置、任意内容管理、所有处罚撤销、全局成就定义 |
| **管理员 (admin)** | 内容管理 (删除/恢复)、处罚执行、举报处理、比赛创建；不可修改系统配置或其他管理员 |
| **普通用户 (user)** | 发帖、评论、评分、举报、社交互动 (关注/好友/黑名单/点赞/收藏/私信) |

**权限判定原则**: 
1. 执行管理操作时采用当前最高权限
2. 所有敏感操作记录：操作人 UID、身份集合、IP 地址、时间戳
3. 根用户可回滚任意历史操作
4. 黑名单即时生效，优先于权限判定

---

## 📝 快速开始

### 1. 环境准备
```bash
# 确保已安装
Python 3.8+
Node.js 16+
PostgreSQL 14+
Redis 6+
```

### 2. 配置数据库
```bash
# 创建数据库
createdb turtle_soup

# 或手动执行 SQL
# CREATE DATABASE turtle_soup;
```

### 3. 配置环境变量
```bash
cd backend
cp .env.example .env
# 编辑 .env 文件，配置 DATABASE_URL 等
```

### 4. 安装依赖并启动
```bash
# Linux/Mac
chmod +x setup.sh
./setup.sh

# Windows
setup.bat
```

### 5. 访问服务
- 后端 API: http://localhost:8000
- API 文档: http://localhost:8000/docs (Swagger UI)
- 前端 (开发中): http://localhost:5173

---

## 🆘 常见问题

### Q: 数据库连接失败？
**A**: 
1. 检查 `.env` 中 `DATABASE_URL` 配置
2. 确保 PostgreSQL 服务运行：`pg_isready`
3. 确认数据库已创建：`createdb turtle_soup`

### Q: Redis 缓存不生效？
**A**: 
1. 确认 Redis 服务运行：`redis-cli ping` → 应返回 PONG
2. 检查配置文件中 `REDIS_URL`

### Q: 前端跨域错误？
**A**: FastAPI 已在 `main.py` 配置 CORS，如需调整:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # 添加你的前端地址
    ...
)
```

### Q: 一键脚本执行失败？
**A**: 
- **Linux/Mac**: `chmod +x setup.sh` 赋予执行权限
- **Windows**: 以管理员身份运行 CMD/PowerShell

### Q: 如何创建根用户？
**A**: 首次启动后，手动在数据库设置:
```sql
UPDATE users SET role = 'root' WHERE username = 'your_username';
```

---

## 📞 维护指南

### 代码规范
- 后端：遵循 PEP 8，使用 Black 格式化
- 前端：遵循 ESLint + Prettier 配置
- 提交信息：使用 Conventional Commits 格式

### 数据库迁移
```bash
# 使用 Alembic
cd backend
alembic revision --autogenerate -m "描述变更"
alembic upgrade head
```

### 文档维护
- **每次重大修改后**更新本 `HANDOVER.md`
- 重点更新「待完成功能」章节
- 记录已知问题和解决方案

---

## 📅 开发计划

| 阶段 | 时间 | 目标 |
|------|------|------|
| Phase 1 | 第 1 周 | 用户认证 + 海龟汤核心功能 |
| Phase 2 | 第 2 周 | 论坛系统 + 社交功能 |
| Phase 3 | 第 3 周 | 比赛系统 + 成就系统 |
| Phase 4 | 第 4 周 | 管理后台 + 搜索优化 |
| Phase 5 | 第 5 周 | 测试 + 性能优化 + 部署 |

---

**重要提醒**: 每次代码提交前请更新本文档的「待完成功能」和「已完成功能」章节，保持信息同步。
