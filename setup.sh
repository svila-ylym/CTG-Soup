#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

printf '%s\n' '==========================================' '  汤吧社区 - 安装与启动' '=========================================='
"$ROOT_DIR/dev.sh" init

if [[ "${1:-}" == "--no-start" ]]; then
  exit 0
fi

printf '\n%s\n' '选择启动方式:' '  1) 仅启动后端 API' '  2) 仅启动前端' '  3) 同时启动前后端' '  4) 退出'
read -r -p '请输入选项 (1-4): ' choice
case "$choice" in
  1) exec "$ROOT_DIR/dev.sh" backend ;;
  2) exec "$ROOT_DIR/dev.sh" frontend ;;
  3) exec "$ROOT_DIR/dev.sh" dev ;;
  4) exit 0 ;;
  *) printf '无效选项\n' >&2; exit 1 ;;
esac
