#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
TAG=""
DRY_RUN=false
CURRENT_COMMIT=""
CURRENT_BRANCH=""
SWITCHED=false
BACKUP_DIR=""
LOCK_DIR="$ROOT_DIR/private-storage/.ota-update.lock"
MAINTENANCE_FILE="$ROOT_DIR/private-storage/.ota-maintenance"
STATE_FILE="${CTG_UPDATE_STATE_FILE:-}"
LOCK_ACQUIRED=false
MAINTENANCE_ACTIVE=false
MIGRATION_STARTED=false
MIGRATION_COMPLETED=false

log() { printf '\n[%s] %s\n' "$(date +%H:%M:%S)" "$*"; }
die() { printf '错误：%s\n' "$*" >&2; return 1; }
require_cmd() { command -v "$1" >/dev/null 2>&1 || die "缺少命令 $1"; }

write_state() {
  local status="$1" exit_code="${2:-null}" error="${3:-}"
  [[ -n "$STATE_FILE" ]] || return 0
  mkdir -p "$(dirname "$STATE_FILE")"
  chmod 700 "$(dirname "$STATE_FILE")"
  printf '{"task_id":"%s","status":"%s","tag_name":"%s","started_at":%s,"finished_at":"%s","exit_code":%s,"log_path":%s,"error":%s}\n' \
    "${CTG_UPDATE_TASK_ID:-manual}" "$status" "$TAG" \
    "$(if [[ -n "${CTG_UPDATE_STARTED_AT:-}" ]]; then printf '"%s"' "$CTG_UPDATE_STARTED_AT"; else printf 'null'; fi)" \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$exit_code" \
    "$(if [[ -n "${CTG_UPDATE_LOG_PATH:-}" ]]; then printf '"%s"' "$CTG_UPDATE_LOG_PATH"; else printf 'null'; fi)" \
    "$(if [[ -n "$error" ]]; then printf '"%s"' "$error"; else printf 'null'; fi)" > "$STATE_FILE.tmp"
  chmod 600 "$STATE_FILE.tmp"
  mv "$STATE_FILE.tmp" "$STATE_FILE"
}

enter_maintenance() {
  mkdir -p "$(dirname "$MAINTENANCE_FILE")"
  chmod 700 "$(dirname "$MAINTENANCE_FILE")"
  printf 'OTA update to %s started at %s\n' "$TAG" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$MAINTENANCE_FILE.tmp"
  chmod 600 "$MAINTENANCE_FILE.tmp"
  mv "$MAINTENANCE_FILE.tmp" "$MAINTENANCE_FILE"
  MAINTENANCE_ACTIVE=true
}

leave_maintenance() {
  if [[ "$MAINTENANCE_ACTIVE" == true ]]; then
    rm -f "$MAINTENANCE_FILE"
    MAINTENANCE_ACTIVE=false
  fi
}

usage() {
  cat <<'EOF'
用法: ./Update.sh --tag v1.2.3 [--dry-run]

环境变量:
  CTG_RESTART_COMMAND   成功升级后执行的重启命令（必填）
  CTG_HEALTH_URL        重启后健康检查地址（默认 127.0.0.1:10001/health）
  CTG_UPDATE_BACKUP_DIR 备份目录根路径（默认 backend/backups/ota）
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --tag) [[ $# -ge 2 ]] || die "--tag 缺少值"; TAG="$2"; shift 2 ;;
    --dry-run) DRY_RUN=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "未知参数: $1" ;;
  esac
done

[[ "$TAG" =~ ^[vV]?[0-9]+(\.[0-9]+){0,2}(-[0-9A-Za-z.-]+)?(\+[0-9A-Za-z.-]+)?$ ]] || die "发行版 tag 格式无效"
require_cmd git
require_cmd python3
require_cmd node
require_cmd npm
require_cmd curl
git -C "$ROOT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1 || die "当前目录不是 git 工作区"
[[ "$(git -C "$ROOT_DIR" rev-parse --show-toplevel)" == "$ROOT_DIR" ]] || die "Update.sh 必须位于 git 仓库根目录"

CURRENT_COMMIT="$(git -C "$ROOT_DIR" rev-parse HEAD)"
CURRENT_BRANCH="$(git -C "$ROOT_DIR" symbolic-ref --quiet --short HEAD || true)"

restore_previous_release() {
  local failed=0
  if [[ -n "$CURRENT_BRANCH" ]]; then
    git -C "$ROOT_DIR" checkout "$CURRENT_BRANCH" || failed=1
  else
    git -C "$ROOT_DIR" checkout --detach "$CURRENT_COMMIT" || failed=1
  fi
  if [[ "$failed" -eq 0 && -x "$BACKEND_DIR/venv/bin/pip" ]]; then
    "$BACKEND_DIR/venv/bin/pip" install -r "$BACKEND_DIR/requirements.txt" \
      -i "${PYTHON_INDEX_URL:-https://pypi.tuna.tsinghua.edu.cn/simple}" || failed=1
  fi
  if [[ "$failed" -eq 0 ]]; then
    if [[ -f "$FRONTEND_DIR/package-lock.json" ]]; then
      (cd "$FRONTEND_DIR" && npm ci --registry "${NPM_REGISTRY_URL:-https://registry.npmmirror.com}") || failed=1
    else
      (cd "$FRONTEND_DIR" && npm install --registry "${NPM_REGISTRY_URL:-https://registry.npmmirror.com}") || failed=1
    fi
  fi
  if [[ -f "$BACKUP_DIR/frontend-dist.tar.gz" ]]; then
    tar -C "$FRONTEND_DIR" -xzf "$BACKUP_DIR/frontend-dist.tar.gz" || failed=1
  elif [[ "$failed" -eq 0 ]]; then
    (cd "$FRONTEND_DIR" && npm run build) || failed=1
  fi
  return "$failed"
}

verify_health() {
  local health_url="${CTG_HEALTH_URL:-http://127.0.0.1:10001/health}"
  local attempts="${CTG_HEALTH_ATTEMPTS:-30}"
  [[ "$attempts" =~ ^[1-9][0-9]*$ ]] || attempts=30
  log "等待新服务健康检查: $health_url"
  for ((attempt = 1; attempt <= attempts; attempt++)); do
    local payload=""
    if payload="$(curl -fsS --max-time 5 "$health_url" 2>/dev/null)" \
      && CTG_HEALTH_PAYLOAD="$payload" CTG_EXPECTED_VERSION="$TARGET_VERSION" \
      python3 -c 'import json, os, sys; payload=json.loads(os.environ["CTG_HEALTH_PAYLOAD"]); actual=str(payload.get("version", "")).lstrip("vV"); expected=os.environ.get("CTG_EXPECTED_VERSION", "").lstrip("vV"); sys.exit(0 if actual == expected else 1)' 2>/dev/null
    then
      return 0
    fi
    sleep 2
  done
  die "新版本健康检查失败，服务保持维护模式"
}

rollback() {
  local exit_code="${1:-$?}" state_error="Update.sh 执行失败"
  trap - ERR INT TERM
  if [[ "$SWITCHED" == true && "$MIGRATION_COMPLETED" != true ]]; then
    log "升级失败，恢复代码、依赖和前端资源到 $CURRENT_COMMIT"
    if ! restore_previous_release; then
      state_error="Update.sh 执行失败；旧版依赖或前端资源恢复不完整"
      printf '警告：旧版运行资源恢复不完整，请使用保留的备份人工恢复。\n' >&2
    fi
  fi
  if [[ "$MIGRATION_STARTED" == true ]]; then
    state_error="数据库迁移失败；服务保持维护模式，请从备份人工恢复数据库"
    printf '数据库迁移可能已部分提交；完成数据库恢复后删除维护标记: %s\n' "$MAINTENANCE_FILE" >&2
  elif [[ "$MIGRATION_COMPLETED" == true ]]; then
    state_error="新版本服务重启或健康检查失败；服务保持维护模式，请检查新版本服务"
    printf '新版本已完成数据库迁移；修复服务后再删除维护标记: %s\n' "$MAINTENANCE_FILE" >&2
  else
    leave_maintenance || true
  fi
  write_state "failed" "$exit_code" "$state_error" || true
  if [[ "$LOCK_ACQUIRED" == true ]]; then rmdir "$LOCK_DIR" 2>/dev/null || true; fi
  [[ -n "$BACKUP_DIR" ]] && printf '备份保留在: %s\n' "$BACKUP_DIR" >&2
  exit "$exit_code"
}
trap 'rollback "$?"' ERR
trap 'rollback 130' INT
trap 'rollback 143' TERM
cleanup() {
  if [[ "$LOCK_ACQUIRED" == true ]]; then rmdir "$LOCK_DIR" 2>/dev/null || true; fi
}
trap cleanup EXIT

if [[ "$DRY_RUN" == true ]]; then
  log "dry-run：将检查 $TAG、创建备份、切换发行版、安装依赖、构建、迁移并重启检查"
  git -C "$ROOT_DIR" check-ref-format "refs/tags/$TAG" >/dev/null
  exit 0
fi

[[ -n "${CTG_RESTART_COMMAND:-}" ]] || die "必须配置 CTG_RESTART_COMMAND，升级后才能安全重启并检查新服务"
case "$CTG_RESTART_COMMAND" in
  *"systemctl restart"*|*"supervisorctl restart"*|*"docker compose restart"*)
    die "CTG_RESTART_COMMAND 不能在当前服务控制组内直接重启 updater，请使用脱离控制组的 helper"
    ;;
esac

mkdir -p "$(dirname "$LOCK_DIR")"
mkdir "$LOCK_DIR" 2>/dev/null || die "已有升级任务正在执行"
LOCK_ACQUIRED=true
[[ ! -e "$MAINTENANCE_FILE" ]] || die "检测到未清理的 OTA 维护标记，请先完成数据库恢复并明确删除该标记"

[[ -z "$(git -C "$ROOT_DIR" status --porcelain --untracked-files=no)" ]] || die "存在未提交的已跟踪文件，拒绝升级"
[[ -f "$BACKEND_DIR/.env" ]] || die "缺少 backend/.env"

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP_DIR="${CTG_UPDATE_BACKUP_DIR:-$BACKEND_DIR/backups/ota}/$timestamp"
mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"
cp -p "$BACKEND_DIR/.env" "$BACKUP_DIR/backend.env"

runtime_paths=()
for path in "$ROOT_DIR/storage" "$ROOT_DIR/private-storage" "$BACKEND_DIR/storage" "$BACKEND_DIR/private-storage"; do
  [[ -d "$path" ]] && runtime_paths+=("${path#$ROOT_DIR/}")
done
if [[ ${#runtime_paths[@]} -gt 0 ]]; then
  tar -C "$ROOT_DIR" -czf "$BACKUP_DIR/runtime-files.tar.gz" "${runtime_paths[@]}"
fi
if [[ -d "$FRONTEND_DIR/dist" ]]; then
  tar -C "$FRONTEND_DIR" -czf "$BACKUP_DIR/frontend-dist.tar.gz" dist
fi

if [[ -x "$BACKEND_DIR/venv/bin/python" ]]; then
  log "创建数据库备份"
  (cd "$BACKEND_DIR" && PYTHONPATH=. "$BACKEND_DIR/venv/bin/python" -m app.services.database_backup --output-dir "$BACKUP_DIR")
else
  die "缺少后端虚拟环境，无法在升级前备份数据库"
fi

log "获取发行版 $TAG"
git -C "$ROOT_DIR" fetch --force origin "refs/tags/$TAG:refs/tags/$TAG"
TARGET_COMMIT="$(git -C "$ROOT_DIR" rev-list -n 1 "$TAG")"
[[ -n "$TARGET_COMMIT" ]] || die "发行版 tag 不存在"
TARGET_VERSION="${TAG#v}"
TARGET_VERSION="${TARGET_VERSION#V}"
enter_maintenance
git -C "$ROOT_DIR" checkout --detach "$TARGET_COMMIT"
SWITCHED=true

log "安装依赖并构建前端"
"$ROOT_DIR/dev.sh" init
"$ROOT_DIR/dev.sh" build
log "执行数据库迁移"
MIGRATION_STARTED=true
"$ROOT_DIR/dev.sh" migrate
MIGRATION_COMPLETED=true
MIGRATION_STARTED=false

log "执行已配置的服务重启命令"
bash -lc "$CTG_RESTART_COMMAND"
verify_health

SWITCHED=false
trap - ERR
write_state "succeeded" 0 ""
leave_maintenance
rmdir "$LOCK_DIR" 2>/dev/null || true
LOCK_ACQUIRED=false
log "升级到 $TAG 完成"
