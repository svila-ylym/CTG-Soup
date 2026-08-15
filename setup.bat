@echo off
REM 海龟汤社区平台 - Windows 一键启动脚本
REM 使用方法：双击 setup.bat 或在命令行运行 setup.bat

setlocal enabledelayedexpansion

echo ==========================================
echo   海龟汤社区平台 - 安装与启动脚本 (Windows)
echo ==========================================
echo.

REM 检查 Python
echo [1/6] 检查 Python 环境...
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
) else (
    python --version
    echo [成功] Python 已安装
)
echo.

REM 检查 Node.js
echo [2/6] 检查 Node.js 环境...
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 Node.js，请先安装 Node.js 16+
    pause
    exit /b 1
) else (
    node --version
    echo [成功] Node.js 已安装
)
echo.

REM 创建虚拟环境
echo [3/6] 创建 Python 虚拟环境...
if not exist "backend\venv" (
    python -m venv backend\venv
    echo [成功] 虚拟环境创建成功
) else (
    echo [成功] 虚拟环境已存在
)
echo.

REM 安装后端依赖
echo [4/6] 安装后端依赖...
cd backend
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
cd ..
echo [成功] 后端依赖安装完成
echo.

REM 安装前端依赖
echo [5/6] 安装前端依赖...
cd frontend
call npm install
cd ..
echo [成功] 前端依赖安装完成
echo.

REM 创建配置文件
echo [6/6] 初始化数据库配置...
if not exist "backend\.env" (
    copy /Y backend\.env.example backend\.env >nul
    backend\venv\Scripts\python.exe -c "from pathlib import Path; import secrets; p=Path(r'backend/.env'); s=p.read_text(encoding='utf-8'); p.write_text(s.replace('SECRET_KEY=replace-with-a-random-secret-at-least-32-characters-long', 'SECRET_KEY='+secrets.token_urlsafe(48)), encoding='utf-8')"
    echo [成功] 配置文件 backend\.env 已创建
    echo [提示] 请编辑 backend\.env 文件配置数据库和其他服务
) else (
    echo [成功] 配置文件已存在
)
echo.

echo ==========================================
echo   安装完成！
echo ==========================================
echo.
echo 请选择启动方式:
echo   1) 仅启动后端 API
echo   2) 仅启动前端
echo   3) 同时启动前后端
echo   4) 退出
echo.
set /p choice="请输入选项 (1-4): "

if "%choice%"=="1" goto START_BACKEND
if "%choice%"=="2" goto START_FRONTEND
if "%choice%"=="3" goto START_BOTH
if "%choice%"=="4" goto EXIT_SCRIPT
echo 无效选项
pause
exit /b 1

:START_BACKEND
echo 启动后端服务...
cd backend
call venv\Scripts\activate.bat
uvicorn app.main:app --reload --host 0.0.0.0 --port 10001
goto END

:START_FRONTEND
echo 启动前端服务...
cd frontend
npm run dev -- --host 0.0.0.0 --port 10000
goto END

:START_BOTH
echo 同时启动前后端服务...
echo 后端将在 http://localhost:10001 运行
echo 前端将在 http://localhost:10000 运行
echo.
echo 按 Ctrl+C 停止所有服务
echo.

REM 启动后端（后台）
cd backend
call venv\Scripts\activate.bat
start "" cmd /k "uvicorn app.main:app --reload --host 0.0.0.0 --port 10001"
cd ..

REM 启动前端
cd frontend
start "" cmd /k "npm run dev -- --host 0.0.0.0 --port 10000"
cd ..

echo 服务已启动，关闭此窗口不会停止服务
echo 要停止服务，请关闭弹出的命令行窗口
pause
goto END

:EXIT_SCRIPT
echo 退出
exit /b 0

:END
endlocal
