#!/bin/bash
# 海龟汤社区平台 - Linux/Mac 一键启动脚本
# 使用方法：./setup.sh 或 bash setup.sh

set -e

echo "=========================================="
echo "  海龟汤社区平台 - 安装与启动脚本 (Linux/Mac)"
echo "=========================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查 Python 版本
check_python() {
    echo -e "${YELLOW}[1/6] 检查 Python 环境...${NC}"
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version)
        echo -e "${GREEN}✓ 已安装: $PYTHON_VERSION${NC}"
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_VERSION=$(python --version)
        echo -e "${GREEN}✓ 已安装: $PYTHON_VERSION${NC}"
        PYTHON_CMD="python"
    else
        echo -e "${RED}✗ 错误：未找到 Python，请先安装 Python 3.8+${NC}"
        exit 1
    fi
}

# 检查 Node.js
check_node() {
    echo -e "${YELLOW}[2/6] 检查 Node.js 环境...${NC}"
    if command -v node &> /dev/null; then
        NODE_VERSION=$(node --version)
        echo -e "${GREEN}✓ 已安装: $NODE_VERSION${NC}"
    else
        echo -e "${RED}✗ 错误：未找到 Node.js，请先安装 Node.js 16+${NC}"
        exit 1
    fi
}

# 创建虚拟环境
setup_venv() {
    echo -e "${YELLOW}[3/6] 创建 Python 虚拟环境...${NC}"
    if [ ! -d "backend/venv" ]; then
        $PYTHON_CMD -m venv backend/venv
        echo -e "${GREEN}✓ 虚拟环境创建成功${NC}"
    else
        echo -e "${GREEN}✓ 虚拟环境已存在${NC}"
    fi
    
    # 激活虚拟环境
    source backend/venv/bin/activate
    echo -e "${GREEN}✓ 虚拟环境已激活${NC}"
}

# 安装后端依赖
install_backend() {
    echo -e "${YELLOW}[4/6] 安装后端依赖...${NC}"
    cd backend
    pip install --upgrade pip
    pip install -r requirements.txt
    cd ..
    echo -e "${GREEN}✓ 后端依赖安装完成${NC}"
}

# 安装前端依赖
install_frontend() {
    echo -e "${YELLOW}[5/6] 安装前端依赖...${NC}"
    cd frontend
    npm install
    cd ..
    echo -e "${GREEN}✓ 前端依赖安装完成${NC}"
}

# 初始化数据库
init_database() {
    echo -e "${YELLOW}[6/6] 初始化数据库配置...${NC}"
    
    # 创建 .env 文件
    if [ ! -f "backend/.env" ]; then
        cat > backend/.env << EOF
# 数据库配置
DATABASE_URL=postgresql://user:password@localhost:5432/turtle_soup

# Redis 配置
REDIS_HOST=localhost
REDIS_PORT=6379

# JWT 配置
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# 邮件配置
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=your-email@example.com
SMTP_PASSWORD=your-password

# Elasticsearch 配置
ELASTICSEARCH_HOST=localhost
ELASTICSEARCH_PORT=9200
EOF
        echo -e "${GREEN}✓ 配置文件 backend/.env 已创建${NC}"
        echo -e "${YELLOW}⚠ 请编辑 backend/.env 文件配置数据库和其他服务${NC}"
    else
        echo -e "${GREEN}✓ 配置文件已存在${NC}"
    fi
}

# 启动服务
start_services() {
    echo ""
    echo "=========================================="
    echo "  安装完成！"
    echo "=========================================="
    echo ""
    echo "请选择启动方式:"
    echo "  1) 仅启动后端 API"
    echo "  2) 仅启动前端"
    echo "  3) 同时启动前后端"
    echo "  4) 退出"
    echo ""
    read -p "请输入选项 (1-4): " choice
    
    case $choice in
        1)
            echo -e "${GREEN}启动后端服务...${NC}"
            cd backend
            source venv/bin/activate
            uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
            ;;
        2)
            echo -e "${GREEN}启动前端服务...${NC}"
            cd frontend
            npm run dev
            ;;
        3)
            echo -e "${GREEN}同时启动前后端服务...${NC}"
            echo "后端将在 http://localhost:8000 运行"
            echo "前端将在 http://localhost:5173 运行"
            echo ""
            echo "按 Ctrl+C 停止所有服务"
            
            # 启动后端（后台）
            cd backend
            source venv/bin/activate
            uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
            BACKEND_PID=$!
            cd ..
            
            # 启动前端
            cd frontend
            npm run dev &
            FRONTEND_PID=$!
            cd ..
            
            # 等待用户中断
            wait
            ;;
        4)
            echo "退出"
            exit 0
            ;;
        *)
            echo "无效选项"
            exit 1
            ;;
    esac
}

# 主流程
main() {
    check_python
    check_node
    setup_venv
    install_backend
    install_frontend
    init_database
    start_services
}

# 执行主流程
main
