# ==============================================================================
# 海龟汤社区平台 - Windows PowerShell 启动脚本
# 功能：环境检测、依赖安装、配置生成、服务启动
# 用法：在 PowerShell 中运行 .\setup.ps1
# ==============================================================================

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
$BackendDir = Join-Path $ProjectRoot "backend"
$FrontendDir = Join-Path $ProjectRoot "frontend"
$EnvFile = Join-Path $ProjectRoot ".env"

# 颜色定义
function Write-Color {
    param([string]$Text, [string]$Color = "White")
    Write-Host $Text -ForegroundColor $Color
}

function Write-Header {
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "       海龟汤社区平台 - 自动化部署与启动脚本 (PS1)"           -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host ""
}

# 1. 检查 Python 环境
function Check-Python {
    Write-Host "[1/5] 检查 Python 环境..." -ForegroundColor Yellow
    try {
        $pythonVersion = python --version 2>&1
        Write-Color "  √ 已检测到 Python: $pythonVersion" "Green"
    } catch {
        Write-Color "  × 未检测到 Python，请先安装 Python 3.9+" "Red"
        Write-Host "  下载地址: https://www.python.org/downloads/"
        exit 1
    }
}

# 2. 检查 Node.js 环境
function Check-Node {
    Write-Host "[2/5] 检查 Node.js 环境..." -ForegroundColor Yellow
    try {
        $nodeVersion = node --version 2>&1
        Write-Color "  √ 已检测到 Node.js: $nodeVersion" "Green"
    } catch {
        Write-Color "  × 未检测到 Node.js，请先安装 Node.js 16+" "Red"
        Write-Host "  下载地址: https://nodejs.org/"
        exit 1
    }
}

# 3. 初始化后端环境
function Init-Backend {
    Write-Host "[3/5] 初始化后端环境..." -ForegroundColor Yellow
    
    # 创建虚拟环境
    $VenvDir = Join-Path $BackendDir "venv"
    if (!(Test-Path $VenvDir)) {
        Write-Host "  → 创建 Python 虚拟环境..." -ForegroundColor Gray
        python -m venv $VenvDir
    } else {
        Write-Host "  √ 虚拟环境已存在" -ForegroundColor Gray
    }

    # 激活虚拟环境并安装依赖
    Write-Host "  → 安装 Python 依赖..." -ForegroundColor Gray
    $ActivateScript = Join-Path $VenvDir "Scripts\Activate.ps1"
    
    # 在 PowerShell 中激活虚拟环境
    & $ActivateScript
    
    pip install -r (Join-Path $BackendDir "requirements.txt") -q
    Write-Color "  √ 后端依赖安装完成" "Green"
}

# 4. 初始化前端环境
function Init-Frontend {
    Write-Host "[4/5] 初始化前端环境..." -ForegroundColor Yellow
    
    if (!(Test-Path (Join-Path $FrontendDir "node_modules"))) {
        Write-Host "  → 首次运行，安装前端依赖 (这可能需要几分钟)..." -ForegroundColor Gray
        Set-Location $FrontendDir
        npm install
        Set-Location $ProjectRoot
    } else {
        Write-Host "  √ 前端依赖已存在" -ForegroundColor Gray
    }
    Write-Color "  √ 前端准备就绪" "Green"
}

# 5. 生成配置文件
function Generate-Env {
    Write-Host "[5/5] 检查配置文件..." -ForegroundColor Yellow
    
    if (!(Test-Path $EnvFile)) {
        Write-Host "  → 生成默认 .env 配置文件..." -ForegroundColor Gray
        $envContent = @"
# 数据库配置
DATABASE_URL=postgresql://postgres:password@localhost:5432/turtle_soup

# Redis 配置
REDIS_URL=redis://localhost:6379/0

# JWT 密钥 (生产环境请修改)
SECRET_KEY=change-this-to-a-random-secret-key-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# 邮件配置 (SMTP)
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=user@example.com
SMTP_PASSWORD=password
MAIL_FROM=noreply@example.com

# 服务端口
BACKEND_PORT=8000
FRONTEND_PORT=3000
"@
        Set-Content -Path $EnvFile -Value $envContent -Encoding UTF8
        Write-Color "  √ .env 文件已生成，请根据实际需求修改数据库密码" "Green"
    } else {
        Write-Host "  √ .env 文件已存在" -ForegroundColor Gray
    }
}

# 启动菜单
function Show-Menu {
    Write-Host ""
    Write-Header
    Write-Host "请选择启动模式:" -ForegroundColor Cyan
    Write-Host "  1. 仅启动后端 (FastAPI)"
    Write-Host "  2. 仅启动前端 (Vue/Vite)"
    Write-Host "  3. 同时启动前后端 (推荐)"
    Write-Host "  4. 打开 API 文档 (浏览器)"
    Write-Host "  0. 退出"
    Write-Host ""
    
    $choice = Read-Host "请输入选项 (1-4)"
    
    switch ($choice) {
        "1" { Start-Backend }
        "2" { Start-Frontend }
        "3" { Start-Both }
        "4" { Open-Docs }
        "0" { exit }
        default { 
            Write-Color "无效选项，请重试" "Red"
            Show-Menu 
        }
    }
}

function Start-Backend {
    Write-Host "正在启动后端服务..." -ForegroundColor Yellow
    $VenvDir = Join-Path $BackendDir "venv"
    $ActivateScript = Join-Path $VenvDir "Scripts\Activate.ps1"
    
    # 加载环境变量
    if (Test-Path $EnvFile) {
        Get-Content $EnvFile | ForEach-Object {
            if ($_ -match "^\s*([^#][^=]+)\s*=\s*(.+)\s*$") {
                $key = $matches[1].Trim()
                $value = $matches[2].Trim().Trim('"')
                [Environment]::SetEnvironmentVariable($key, $value, "Process")
            }
        }
    }

    & $ActivateScript
    Set-Location $BackendDir
    
    # 异步启动 uvicorn
    $port = if ($env:BACKEND_PORT) { $env:BACKEND_PORT } else { "8000" }
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "uvicorn app.main:app --reload --host 0.0.0.0 --port $port"
    
    Write-Color "后端服务已启动! 访问 http://localhost:$port/docs" "Green"
    Set-Location $ProjectRoot
}

function Start-Frontend {
    Write-Host "正在启动前端服务..." -ForegroundColor Yellow
    Set-Location $FrontendDir
    
    $port = if ($env:FRONTEND_PORT) { $env:FRONTEND_PORT } else { "3000" }
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "npm run dev -- --port $port"
    
    Write-Color "前端服务已启动! 访问 http://localhost:$port" "Green"
    Set-Location $ProjectRoot
}

function Start-Both {
    Start-Backend
    Start-Sleep -Seconds 2
    Start-Frontend
    Write-Host ""
    Write-Color "============================================================" "Cyan"
    Write-Color "  所有服务已启动!" "Green"
    Write-Color "  前端: http://localhost:3000" "White"
    Write-Color "  后端: http://localhost:8000/docs" "White"
    Write-Color "============================================================" "Cyan"
}

function Open-Docs {
    $port = if ($env:BACKEND_PORT) { $env:BACKEND_PORT } else { "8000" }
    Start-Process "http://localhost:$port/docs"
    Write-Color "已打开 API 文档页面" "Green"
}

# 主执行流程
try {
    Write-Header
    Check-Python
    Check-Node
    Init-Backend
    Init-Frontend
    Generate-Env
    
    Show-Menu
} catch {
    Write-Color "发生错误: $_" "Red"
    exit 1
}
