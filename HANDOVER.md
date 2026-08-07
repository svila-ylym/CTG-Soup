# 海龟汤社区平台 - 项目交接文档

## 📋 项目状况

### 项目名称
海龟汤社区平台 (Turtle Soup Community)

### 技术栈
- **后端**: Python FastAPI + SQLAlchemy + PostgreSQL + Redis + Elasticsearch
- **前端**: Vue 3 + TypeScript + Vite + Pinia + Vue Router + Tailwind CSS
- **部署**: Docker 容器化

### 当前状态
✅ 基础框架已完成  
✅ 前后端分离架构已建立  
✅ 核心数据模型已定义  
✅ 主要 API 路由框架已创建  
✅ 前端 UI 组件和页面框架已搭建  

---

## ✅ 已完成功能

### 后端 (FastAPI)

#### 1. 核心配置
- [x] 数据库连接配置 (PostgreSQL)
- [x] Redis 缓存配置
- [x] JWT 认证配置
- [x] 邮件服务配置
- [x] 环境变量管理 (.env)

#### 2. 数据模型 (15+ 张表) - `backend/app/models/models.py`
- [x] 用户表 (users) - 含角色、状态、积分
- [x] 处罚表 (punishments) - 支持撤销与审计
- [x] 帖子表 (posts)
- [x] 评论表 (comments)
- [x] 海龟汤表 (turtle_soups) - 含贝叶斯评分字段
- [x] 评分表 (soup_scores) - 唯一约束防重复
- [x] 点赞表 (likes) - 统一目标类型
- [x] 收藏表 (favorites)
- [x] 关注表 (follows)
- [x] 黑名单表 (blacklists)
- [x] 比赛表 (competitions)
- [x] 比赛作品表 (competition_entries)
- [x] 成就表 (achievements)
- [x] 用户成就进度表 (user_achievements)
- [x] 私信表 (messages)
- [x] 通知表 (notifications)
- [x] 举报表 (reports)
- [x] 操作日志表 (audit_logs)
- [x] 签到表 (daily_signins)

#### 3. API 路由模块 - `backend/app/api/`
| 文件 | 大小 | 功能 |
|------|------|------|
| `auth.py` | 9.1KB | 注册/登录/JWT/刷新令牌 |
| `users.py` | 10.5KB | 用户信息/签到/主页 |
| `posts.py` | 3.6KB | 帖子 CRUD/评论/点赞/收藏 |
| `turtle_soups.py` | 15.5KB | 海龟汤发布/评分/排行榜 |
| `competitions.py` | 3.3KB | 比赛创建/作品收录/排名 |
| `social.py` | 5.6KB | 关注/拉黑 |
| `messages.py` | 5.4KB | 私信收发 |
| `achievements.py` | 4.2KB | 成就定义/进度追踪 |
| `admin.py` | 9.4KB | 用户管理/处罚/举报处理 |
| `search.py` | 3.7KB | 全文搜索 |

#### 4. 工具函数 - `backend/app/utils.py`
- [x] 贝叶斯平均评分算法
- [x] JWT 令牌生成与验证
- [x] 密码哈希与验证
- [x] 权限装饰器

### 前端 (Vue 3)

#### 1. 项目结构
```
frontend/
├── src/
│   ├── api/           # API 调用封装 (3 个文件)
│   │   ├── http.ts    # Axios 实例与拦截器
│   │   ├── auth.ts    # 认证相关 API
│   │   └── soup.ts    # 海龟汤相关 API
│   ├── assets/        # 静态资源
│   │   └── main.css   # Tailwind + 自定义样式
│   ├── components/    # 可复用组件 (3 个)
│   │   ├── NavBar.vue       # 导航栏 (8KB)
│   │   ├── Footer.vue       # 页脚
│   │   └── ToastContainer.vue # 全局提示
│   ├── router/        # 路由配置
│   │   └── index.ts   # 路由守卫与权限 (3.6KB)
│   ├── stores/        # Pinia 状态管理 (2 个)
│   │   ├── auth.ts    # 认证状态
│   │   └── soup.ts    # 海龟汤状态
│   ├── types/         # TypeScript 类型定义
│   │   └── index.ts   # 完整接口定义
│   ├── utils/         # 工具函数
│   └── views/         # 页面组件
│       ├── HomeView.vue         # 首页 (7.4KB) ✅
│       ├── LoginView.vue        # 登录页 (7.1KB) ✅
│       ├── RegisterView.vue     # 注册页 (6KB) ✅
│       ├── LeaderboardView.vue  # 排行榜 (4.7KB) ✅
│       ├── soup/                # 海龟汤模块
│       │   ├── SoupListView.vue ✅ (10KB)
│       │   ├── SoupCreateView.vue ⏳ (待实现)
│       │   └── SoupDetailView.vue ⏳ (待实现)
│       ├── post/                # 论坛模块 ⏳ (目录已建)
│       ├── competition/         # 比赛模块 ⏳ (目录已建)
│       └── admin/               # 管理后台 ⏳ (目录已建)
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
└── tailwind.config.js
```

#### 2. 已实现页面 (详细)
| 页面 | 文件 | 大小 | 状态 | 功能 |
|------|------|------|------|------|
| 首页 | HomeView.vue | 7.4KB | ✅ | Hero 区域/特色展示/热门海龟汤 |
| 登录 | LoginView.vue | 7.1KB | ✅ | 表单验证/错误提示/记住我 |
| 注册 | RegisterView.vue | 6KB | ✅ | 密码强度验证/邮箱格式 |
| 排行榜 | LeaderboardView.vue | 4.7KB | ✅ | 贝叶斯/平均分切换/前 100 名 |
| 海龟汤列表 | SoupListView.vue | 10KB | ✅ | 筛选/排序/分页/标签 |
| 海龟汤详情 | SoupDetailView.vue | - | ⏳ | 待实现 (汤底隐藏逻辑) |
| 海龟汤发布 | SoupCreateView.vue | - | ⏳ | 待实现 (富文本编辑器) |
| 个人主页 | ProfileView.vue | - | ⏳ | 待实现 |
| 消息中心 | MessageView.vue | - | ⏳ | 待实现 |
| 通知中心 | NotificationView.vue | - | ⏳ | 待实现 |
| 论坛列表 | PostListView.vue | - | ⏳ | 待实现 |
| 比赛列表 | CompetitionListView.vue | - | ⏳ | 待实现 |
| 搜索 | SearchView.vue | - | ⏳ | 待实现 |
| 设置 | SettingsView.vue | - | ⏳ | 待实现 |

#### 3. 核心功能
- [x] 路由守卫与权限控制
- [x] JWT 认证与自动刷新
- [x] Pinia 状态管理
- [x] Axios 请求/响应拦截器
- [x] Tailwind CSS 响应式设计
- [x] 暗黑模式切换
- [x] 全局 Toast 通知系统
- [x] 模块化 API 封装

---

## ⏳ 未完成功能 (按优先级)

### P0 - 核心功能 (必须完成)

#### 后端
- [ ] 数据库迁移脚本 (Alembic)
- [ ] Elasticsearch 索引同步
- [ ] WebSocket 实时通知
- [ ] 定时任务 (比赛结算/成就检测)
- [ ] 文件上传 (图片/附件)
- [ ] 邮件发送服务实现

#### 前端
- [ ] 海龟汤详情页 (汤底隐藏逻辑)
- [ ] 海龟汤发布页 (富文本编辑器)
- [ ] 评分组件 (0.5 步进)
- [ ] 个人主页
- [ ] 用户设置页
- [ ] 消息中心
- [ ] 通知中心

### P1 - 重要功能

#### 后端
- [ ] 比赛自动参赛逻辑完善
- [ ] 成就系统事件监听
- [ ] 举报处理流程
- [ ] 操作日志回滚机制
- [ ] Redis 缓存优化 (排行榜/热点数据)

#### 前端
- [ ] 论坛模块完整实现
- [ ] 比赛模块完整实现
- [ ] 社交功能 (关注/拉黑界面)
- [ ] 搜索页面
- [ ] 管理后台界面

### P2 - 增强功能

- [ ] 第三方登录 (GitHub/微信)
- [ ] 移动端适配优化
- [ ] SEO 优化
- [ ] 性能监控
- [ ] 单元测试覆盖
- [ ] E2E 测试

---

## 🔄 运行逻辑

### 1. 启动流程 (PowerShell/Shell)

```bash
# 一键启动脚本 (setup.ps1 / setup.sh)
1. 检查环境 (Python/Node.js)
2. 创建虚拟环境并安装依赖
3. 生成.env 配置文件
4. 选择启动模式:
   - 仅后端 (FastAPI :8000)
   - 仅前端 (Vite :3000)
   - 同时启动 (推荐)
   - 打开 API 文档
```

### Windows PowerShell 使用说明

1. **首次运行需要解除执行策略限制**:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\setup.ps1
```

2. **或者右键点击** `setup.ps1` 选择 "使用 PowerShell 运行"

3. 脚本功能:
   - ✅ 自动检测 Python 和 Node.js 版本
   - ✅ 创建 Python 虚拟环境 (backend/venv)
   - ✅ 安装前后端所有依赖
   - ✅ 生成 .env 配置文件
   - ✅ 提供交互式启动菜单
   - ✅ 支持独立启动前后端服务

### 2. 请求处理流程

```
用户请求
  ↓
Nginx (可选反向代理)
  ↓
前端 Vite Dev Server (:3000) 或 静态文件
  ↓
API 请求 (/api/*)
  ↓
FastAPI 路由
  ↓
权限验证 (JWT)
  ↓
业务逻辑处理
  ↓
数据库操作 (SQLAlchemy)
  ↓
Redis 缓存 (可选)
  ↓
返回 JSON 响应
```

### 3. 海龟汤评分流程

```
用户提交评分 (1-10, 0.5 步进)
  ↓
验证：是否已评分/分数范围
  ↓
插入/更新评分记录
  ↓
计算新平均分:
  - 简单平均 = SUM(score) / COUNT
  - 贝叶斯平均 = (C * m + ΣR) / (C + N)
    C: 置信度常数
    m: 全局平均分
    R: 各评分
    N: 评分人数
  ↓
更新海龟汤表 avg_score 字段
  ↓
Redis 缓存失效/更新
  ↓
触发通知 (可选)
```

### 4. 比赛结算流程

```
定时任务扫描 (每分钟)
  ↓
查找已结束未结算的比赛
  ↓
对每个比赛:
  - 查询所有参赛作品 (通过标签匹配)
  - 计算每篇作品的最终得分
  - 按计分方式排序 (平均制/高分制)
  - 取前 N 名生成排名
  - 快照至 competition_entries 表
  ↓
发送通知给参赛者
  ↓
标记比赛为"已结算"
```

### 5. 黑名单限制逻辑

```
用户 A 拉黑用户 B
  ↓
插入 blacklist 记录
  ↓
后续所有交互检查:
  - B 无法关注 A
  - B 无法私信 A
  - B 无法@A
  - B 无法评论 A 的内容
  - B 无法点赞/收藏 A 的内容
  
双向拉黑:
  - 彼此内容完全不可见
  - 搜索结果过滤
```

### 6. 权限判定逻辑

```
请求到达 → 提取 JWT → 解析用户身份
  ↓
权限层级:
  root > admin > user
  ↓
执行操作时:
  - 检查用户角色
  - 检查处罚状态 (禁言/封号)
  - 检查黑名单关系
  - 检查资源所有权
  ↓
记录操作日志 (敏感操作)
```

---

## 📦 依赖清单

### 后端依赖
```
fastapi>=0.100.0
uvicorn[standard]>=0.23.0
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.0
redis>=4.5.0
pydantic>=2.0.0
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
python-multipart>=0.0.6
elasticsearch>=8.0.0
aiohttp>=3.8.0
```

### 前端依赖
```json
{
  "vue": "^3.5.x",
  "vue-router": "^5.2.x",
  "pinia": "^4.0.x",
  "axios": "^1.19.x",
  "vite": "^6.3.x",
  "typescript": "^5.8.x",
  "tailwindcss": "^4.3.x",
  "@headlessui/vue": "^1.7.x",
  "@heroicons/vue": "^2.2.x"
}
```

### 外部服务
- PostgreSQL 14+
- Redis 6+
- Elasticsearch 8+
- SMTP 邮件服务器

---

## 🚀 快速开始

### 1. 环境准备
```bash
# 安装 Python 3.10+
# 安装 Node.js 18+
# 安装 PostgreSQL
# 安装 Redis
# 安装 Elasticsearch
```

### 2. 后端启动
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 配置 .env
cp .env.example .env
# 编辑.env 填写数据库连接等信息

# 创建数据库
createdb turtle_soup

# 启动服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. 前端启动
```bash
cd frontend
npm install
npm run dev
```

### 4. 访问
- 前端：http://localhost:3000
- 后端 API: http://localhost:8000
- API 文档：http://localhost:8000/docs

---

## 📝 常见问题

### Q1: 数据库连接失败
```bash
# 检查 PostgreSQL 是否运行
pg_isready -h localhost -p 5432

# 检查.env 配置
DATABASE_URL=postgresql://user:password@localhost:5432/turtle_soup
```

### Q2: 前端跨域问题
```typescript
// vite.config.ts 已配置代理
proxy: {
  '/api': {
    target: 'http://localhost:8000',
    changeOrigin: true,
  }
}
```

### Q3: Redis 连接失败
```bash
# 检查 Redis 是否运行
redis-cli ping
# 应返回 PONG
```

### Q4: JWT 令牌过期
- Access Token: 30 分钟
- Refresh Token: 7 天
- 过期后需重新登录或使用 refresh_token 刷新

---

## 📅 开发计划

### 第 1 周 - 核心功能完善
- [ ] 完成海龟汤详情/发布页
- [ ] 实现评分组件
- [ ] 完善个人主页
- [ ] 数据库迁移脚本

### 第 2 周 - 社交与消息
- [ ] 私信系统前端
- [ ] 通知中心
- [ ] 关注/拉黑界面
- [ ] WebSocket 实时推送

### 第 3 周 - 比赛系统
- [ ] 比赛创建页 (富文本)
- [ ] 比赛详情页
- [ ] 自动参赛逻辑
- [ ] 定时任务结算

### 第 4 周 - 管理后台
- [ ] 管理员 Dashboard
- [ ] 举报处理界面
- [ ] 处罚管理
- [ ] 操作日志查看

### 第 5 周 - 测试与优化
- [ ] 单元测试
- [ ] 性能优化
- [ ] 安全加固
- [ ] 文档完善

---

## 🔐 安全注意事项

1. **密码安全**: bcrypt 加密，长度≥8 位，含大小写数字
2. **JWT 安全**: HTTPS 传输，短有效期，支持刷新
3. **SQL 注入**: SQLAlchemy ORM 参数化查询
4. **XSS 防护**: Vue 自动转义，富文本白名单过滤
5. **CSRF 防护**: SameSite Cookie 策略
6. **速率限制**: 关键接口限流 (登录/注册/评分)

---

## 📞 联系方式

- 项目仓库：[待添加]
- 文档地址：[待添加]
- 问题反馈：[待添加]

---

**最后更新时间**: 2024-01-XX  
**文档版本**: v1.1.0 (新增 PowerShell 启动脚本)  
**维护者**: [待填写]

## 📝 更新日志

### v1.1.0 - 2024-01-XX
- ✅ 新增 Windows PowerShell 启动脚本 (setup.ps1)
- ✅ 修复 BAT 脚本编码问题
- ✅ 完善启动脚本交互菜单
- ✅ 更新 README 和交接文档
- ✅ 前端 Vue 3 模块化架构完成
- ✅ 后端 15+ 数据表模型定义完成
- ✅ 10 个 API 路由模块框架完成

### v1.0.0 - 2024-01-XX
- ✅ 项目初始化
- ✅ 基础架构搭建
- ✅ 核心数据模型设计
