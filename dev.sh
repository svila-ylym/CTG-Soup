#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
VENV_DIR="${BACKEND_VENV:-$BACKEND_DIR/venv}"
PYTHON_INDEX="${PYTHON_INDEX_URL:-https://pypi.tuna.tsinghua.edu.cn/simple}"
NPM_REGISTRY="${NPM_REGISTRY_URL:-https://registry.npmmirror.com}"

log() { printf '\n[%s] %s\n' "$(date +%H:%M:%S)" "$*"; }
die() { printf '错误：%s\n' "$*" >&2; exit 1; }

require_cmd() { command -v "$1" >/dev/null 2>&1 || die "缺少命令 $1，请先安装"; }

init() {
  require_cmd python3
  require_cmd node
  require_cmd npm
  log "创建 Python 虚拟环境: $VENV_DIR"
  [[ -x "$VENV_DIR/bin/python" ]] || python3 -m venv "$VENV_DIR"
  log "安装后端依赖"
  "$VENV_DIR/bin/python" -m pip install --upgrade pip -i "$PYTHON_INDEX"
  "$VENV_DIR/bin/pip" install -r "$BACKEND_DIR/requirements.txt" -i "$PYTHON_INDEX"
  log "安装前端依赖"
  if [[ -f "$FRONTEND_DIR/package-lock.json" ]]; then
    (cd "$FRONTEND_DIR" && npm ci --registry "$NPM_REGISTRY")
  else
    (cd "$FRONTEND_DIR" && npm install --registry "$NPM_REGISTRY")
  fi
  if [[ ! -f "$BACKEND_DIR/.env" ]]; then
    cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
    "$VENV_DIR/bin/python" - "$BACKEND_DIR/.env" <<'PY'
from pathlib import Path
import secrets
import sys

path = Path(sys.argv[1])
content = path.read_text(encoding="utf-8")
content = content.replace(
    "SECRET_KEY=replace-with-a-random-secret-at-least-32-characters-long",
    f"SECRET_KEY={secrets.token_urlsafe(48)}",
)
path.write_text(content, encoding="utf-8")
PY
    log "已创建 backend/.env 并生成本地密钥，请按需填写 PostgreSQL、Redis、SMTP 配置"
  else
    log "保留现有 backend/.env"
  fi
  chmod 600 "$BACKEND_DIR/.env"
  log "初始化完成。前端端口: 10000，后端端口: 10001"
}

backend() {
  [[ -x "$VENV_DIR/bin/uvicorn" ]] || die "请先运行: $0 init"
  (cd "$BACKEND_DIR" && PYTHONPATH=. "$VENV_DIR/bin/uvicorn" app.main:app --reload --host 0.0.0.0 --port 10001)
}

frontend() {
  [[ -x "$FRONTEND_DIR/node_modules/.bin/vite" ]] || die "请先运行: $0 init"
  (cd "$FRONTEND_DIR" && npm run dev -- --host 0.0.0.0 --port 10000)
}

dev() {
  [[ -x "$VENV_DIR/bin/uvicorn" ]] || die "请先运行: $0 init"
  [[ -x "$FRONTEND_DIR/node_modules/.bin/vite" ]] || die "请先运行: $0 init"
  local backend_pid frontend_pid
  trap 'kill "$backend_pid" "$frontend_pid" 2>/dev/null || true' EXIT INT TERM
  (cd "$BACKEND_DIR" && PYTHONPATH=. "$VENV_DIR/bin/uvicorn" app.main:app --reload --host 0.0.0.0 --port 10001) & backend_pid=$!
  (cd "$FRONTEND_DIR" && npm run dev -- --host 0.0.0.0 --port 10000) & frontend_pid=$!
  log "后端监听: http://0.0.0.0:10001"
  log "前端监听: http://0.0.0.0:10000"
  wait
}

test() {
  [[ -x "$VENV_DIR/bin/python" ]] || die "请先运行: $0 init"
  (cd "$ROOT_DIR" && PYTHONPATH=backend "$VENV_DIR/bin/python" -m pytest -q backend/tests)
}

build() {
  [[ -x "$FRONTEND_DIR/node_modules/.bin/vite" ]] || die "请先运行: $0 init"
  (cd "$FRONTEND_DIR" && npm run build)
}

migrate() {
  [[ -x "$VENV_DIR/bin/python" ]] || die "请先运行: $0 init"
  [[ -f "$BACKEND_DIR/.env" ]] || die "缺少 backend/.env"
  (cd "$BACKEND_DIR" && PYTHONPATH=. "$VENV_DIR/bin/python" -m app.migrations.social_platform --phase all)
}

case "${1:-help}" in
  init) init ;;
  backend) backend ;;
  frontend) frontend ;;
  dev|run) dev ;;
  test) test ;;
  build) build ;;
  migrate) migrate ;;
  help|*)
    cat <<EOF
用法:
  ./dev.sh init       创建虚拟环境并安装依赖（清华/PyPI 与 npm 镜像）
  ./dev.sh dev        同时启动后端 10001 和前端 10000
  ./dev.sh backend    仅启动后端
  ./dev.sh frontend   仅启动前端
  ./dev.sh test       运行后端测试
  ./dev.sh build      构建前端生产资源
  ./dev.sh migrate    执行可重复数据库迁移

可覆盖镜像:
  PYTHON_INDEX_URL=https://pypi.org/simple NPM_REGISTRY_URL=https://registry.npmjs.org ./dev.sh init
EOF
    ;;
esac
