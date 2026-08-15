# ==============================================================================
# Turtle Soup Community Platform - Windows PowerShell Setup Script
# Usage: Run .\setup.ps1 in PowerShell
# Note: If execution fails, run: Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
# ==============================================================================

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
$BackendDir = Join-Path $ProjectRoot "backend"
$FrontendDir = Join-Path $ProjectRoot "frontend"
$EnvFile = Join-Path $BackendDir ".env"

function Write-Color {
    param([string]$Text, [string]$Color = "White")
    Write-Host $Text -ForegroundColor $Color
}

function Write-Header {
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "   Turtle Soup Community - Setup & Launch Script (PS1)"     -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host ""
}

function Check-Python {
    Write-Host "[1/5] Checking Python environment..." -ForegroundColor Yellow
    try {
        $pythonVersion = python --version 2>&1
        Write-Color "  OK Python detected: $pythonVersion" "Green"
    } catch {
        Write-Color "  ERROR Python not found. Please install Python 3.9+" "Red"
        Write-Host "  Download: https://www.python.org/downloads/"
        exit 1
    }
}

function Check-Node {
    Write-Host "[2/5] Checking Node.js environment..." -ForegroundColor Yellow
    try {
        $nodeVersion = node --version 2>&1
        Write-Color "  OK Node.js detected: $nodeVersion" "Green"
    } catch {
        Write-Color "  ERROR Node.js not found. Please install Node.js 16+" "Red"
        Write-Host "  Download: https://nodejs.org/"
        exit 1
    }
}

function Init-Backend {
    Write-Host "[3/5] Initializing backend environment..." -ForegroundColor Yellow
    $VenvDir = Join-Path $BackendDir "venv"
    if (!(Test-Path $VenvDir)) {
        Write-Host "  -> Creating Python virtual environment..." -ForegroundColor Gray
        python -m venv $VenvDir
    } else {
        Write-Host "  OK Virtual environment already exists" -ForegroundColor Gray
    }
    Write-Host "  -> Installing Python dependencies..." -ForegroundColor Gray
    $ActivateScript = Join-Path $VenvDir "Scripts\Activate.ps1"
    $PipCmd = Join-Path $VenvDir "Scripts\pip.exe"
    if (Test-Path $PipCmd) {
        & $PipCmd install --upgrade pip -q
        & $PipCmd install -r (Join-Path $BackendDir "requirements.txt") -q
        Write-Color "  OK Backend dependencies installed" "Green"
    } else {
        Write-Color "  ERROR pip not found in venv" "Red"
    }
}

function Init-Frontend {
    Write-Host "[4/5] Initializing frontend environment..." -ForegroundColor Yellow
    if (!(Test-Path (Join-Path $FrontendDir "node_modules"))) {
        Write-Host "  -> First run, installing frontend dependencies..." -ForegroundColor Gray
        Push-Location $FrontendDir
        npm install
        Pop-Location
    } else {
        Write-Host "  OK Frontend dependencies already exist" -ForegroundColor Gray
    }
    Write-Color "  OK Frontend ready" "Green"
}

function Generate-Env {
    Write-Host "[5/5] Checking configuration file..." -ForegroundColor Yellow
    if (!(Test-Path $EnvFile)) {
        Write-Host "  -> Generating default .env configuration file..." -ForegroundColor Gray
        Copy-Item (Join-Path $BackendDir ".env.example") $EnvFile
        $SecretBytes = New-Object byte[] 48
        $SecretGenerator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
        $SecretGenerator.GetBytes($SecretBytes)
        $SecretGenerator.Dispose()
        $GeneratedSecret = [Convert]::ToBase64String($SecretBytes).TrimEnd('=').Replace('+', '-').Replace('/', '_')
        $EnvContent = [IO.File]::ReadAllText($EnvFile).Replace(
            "SECRET_KEY=replace-with-a-random-secret-at-least-32-characters-long",
            "SECRET_KEY=$GeneratedSecret"
        )
        $Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
        [IO.File]::WriteAllText($EnvFile, $EnvContent, $Utf8NoBom)
        Write-Color "  OK .env file generated" "Green"
    } else {
        Write-Host "  OK .env file already exists" -ForegroundColor Gray
    }
}

function Show-Menu {
    Write-Host ""
    Write-Header
    Write-Host "Please select launch mode:" -ForegroundColor Cyan
    Write-Host "  1. Start Backend Only (FastAPI)"
    Write-Host "  2. Start Frontend Only (Vue/Vite)"
    Write-Host "  3. Start Both (Recommended)"
    Write-Host "  4. Open API Docs (Browser)"
    Write-Host "  0. Exit"
    Write-Host ""
    $choice = Read-Host "Enter option (0-4)"
    switch ($choice) {
        "1" { Start-Backend }
        "2" { Start-Frontend }
        "3" { Start-Both }
        "4" { Open-Docs }
        "0" { exit }
        default { 
            Write-Color "Invalid option, please try again" "Red"
            Show-Menu 
        }
    }
}

function Start-Backend {
    Write-Host "Starting backend service..." -ForegroundColor Yellow
    $VenvDir = Join-Path $BackendDir "venv"
    $PythonCmd = Join-Path $VenvDir "Scripts\python.exe"
    if (Test-Path $EnvFile) {
        Get-Content $EnvFile | ForEach-Object {
            if ($_ -match "^\s*([^#][^=]+)\s*=\s*(.+)\s*$") {
                $key = $matches[1].Trim()
                $value = $matches[2].Trim().Trim('"')
                [Environment]::SetEnvironmentVariable($key, $value, "Process")
            }
        }
    }
    Push-Location $BackendDir
    $port = if ($env:BACKEND_PORT) { $env:BACKEND_PORT } else { "10001" }
    if (Test-Path $PythonCmd) {
        Start-Process powershell -ArgumentList "-NoExit", "-Command", "& '$PythonCmd' -m uvicorn app.main:app --reload --host 0.0.0.0 --port $port"
    } else {
        Start-Process powershell -ArgumentList "-NoExit", "-Command", "uvicorn app.main:app --reload --host 0.0.0.0 --port $port"
    }
    Write-Color "Backend service started! Access http://localhost:$port/docs" "Green"
    Pop-Location
}

function Start-Frontend {
    Write-Host "Starting frontend service..." -ForegroundColor Yellow
    Push-Location $FrontendDir
    $port = if ($env:FRONTEND_PORT) { $env:FRONTEND_PORT } else { "10000" }
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "npm run dev -- --host 0.0.0.0 --port $port"
    Write-Color "Frontend service started! Access http://localhost:$port" "Green"
    Pop-Location
}

function Start-Both {
    Start-Backend
    Start-Sleep -Seconds 2
    Start-Frontend
    Write-Host ""
    Write-Color "============================================================" "Cyan"
    Write-Color "  All services started successfully!" "Green"
    Write-Color "  Frontend: http://localhost:10000" "White"
    Write-Color "  Backend:  http://localhost:10001/docs" "White"
    Write-Color "============================================================" "Cyan"
}

function Open-Docs {
    $port = if ($env:BACKEND_PORT) { $env:BACKEND_PORT } else { "10001" }
    Start-Process "http://localhost:$port/docs"
    Write-Color "API documentation opened in browser" "Green"
}

try {
    Write-Header
    Check-Python
    Check-Node
    Init-Backend
    Init-Frontend
    Generate-Env
    Show-Menu
} catch {
    Write-Color "Error occurred: $_" "Red"
    exit 1
}
