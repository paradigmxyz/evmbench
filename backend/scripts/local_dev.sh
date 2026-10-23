#!/usr/bin/env bash
set -euo pipefail

# Local no-Docker runner for evmbench with the ZCode agent.
#
# Starts the full local stack as plain processes:
#   secretsvc (8081), resultsvc (8083), api (1337), frontend (3000)
# backed by SQLite and an in-process job dispatcher (no Postgres, RabbitMQ,
# instancer or Docker). Workers run the ZCode CLI headless using the desktop
# app login.
#
# Usage: local_dev.sh up|down|status|logs [service]
#   up       - install deps if needed, then start the whole stack
#   down     - stop the whole stack
#   status   - show service pids / health
#   logs svc - follow a service log (api|secretsvc|resultsvc|frontend)
#
# Optional environment (export before `up`):
#   FRONTEND_PORT                     - frontend port (default 3000)
#   ZCODE_MODE                        - zcode permission mode (default yolo; plan = read-only audits)
#   EVM_BENCH_ZCODE_TIMEOUT_SECONDS   - max audit runtime (default 10800)
#   BACKEND_LOCAL_MAX_CONCURRENT_JOBS - parallel audits (default 1)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
FRONTEND_DIR="$(cd "${BACKEND_DIR}/../frontend" && pwd)"
DATA_DIR="${BACKEND_DIR}/.data"
LOGS_DIR="${DATA_DIR}/logs"
RUN_DIR="${DATA_DIR}/run"
DB_PATH="${DATA_DIR}/evmbench.db"

BACKEND_SERVICES=(secretsvc resultsvc api)
export API_PORT="${BACKEND_WEB_PORT:-1337}"
export SECRETSVC_PORT="${SECRETSVC_PORT:-8081}"
export RESULTSVC_PORT="${RESULTSVC_PORT:-8083}"
export FRONTEND_PORT="${FRONTEND_PORT:-3000}"

service_port() {
  case "$1" in
    secretsvc) echo "${SECRETSVC_PORT}" ;;
    resultsvc) echo "${RESULTSVC_PORT}" ;;
    api) echo "${API_PORT}" ;;
    frontend) echo "${FRONTEND_PORT}" ;;
    *) echo "" ;;
  esac
}

log() { printf '\033[1;34m[local_dev]\033[0m %s\n' "$*"; }
err() { printf '\033[1;31m[local_dev]\033[0m %s\n' "$*" >&2; }

pid_alive() { [[ -f "${RUN_DIR}/$1.pid" ]] && kill -0 "$(cat "${RUN_DIR}/$1.pid")" 2>/dev/null; }

check_prereqs() {
  command -v uv >/dev/null 2>&1 || { err "uv is required (https://docs.astral.sh/uv/)"; exit 1; }
  command -v zcode >/dev/null 2>&1 || { err "zcode CLI not found on PATH (it ships with ZCode.app)"; exit 1; }
  command -v node >/dev/null 2>&1 || err "warning: node not found; the zcode wrapper needs Node.js"
  command -v forge >/dev/null 2>&1 || err "warning: foundry (forge) not found; audits will be static-only"
  command -v slither >/dev/null 2>&1 || err "warning: slither not found; audits will not use it"
  true
}

service_env() {
  # The worker inherits the API environment, so the API must see the zcode
  # CLI, foundry and homebrew tools.
  export PATH="${HOME}/.local/bin:${HOME}/.foundry/bin:/opt/homebrew/bin:${PATH}"

  export BACKEND_DEV=true
  export BACKEND_WEB_HOST=127.0.0.1
  export BACKEND_WEB_PORT="${API_PORT}"
  # The local dispatcher runs inside the API process: exactly one worker.
  export BACKEND_WEB_WORKERS=1

  export DATABASE_DSN="sqlite+aiosqlite:///${DB_PATH}"
  export DATABASE_AUTO_CREATE_TABLES=true
  export BACKEND_JWT_SECRET="${BACKEND_JWT_SECRET:-local-dev-secret}"

  export BACKEND_QUEUE_BACKEND=local
  export SECRETS_TOKEN_RO="${SECRETS_TOKEN_RO:-local-dev-secret-ro}"
  export SECRETS_TOKEN_WO="${SECRETS_TOKEN_WO:-local-dev-secret-wo}"
  export SECRETSVC_SECRETS_DIR="${DATA_DIR}/secrets"

  # The API stores job bundles in secretsvc over HTTP (write token); the
  # local dispatcher points workers at the same two services.
  export BACKEND_SECRETS_BACKEND=http
  export BACKEND_SECRETS_BACKEND_ARGUMENTS="{\"url\":\"http://127.0.0.1:${SECRETSVC_PORT}\",\"token\":\"${SECRETS_TOKEN_WO}\"}"
  export BACKEND_LOCAL_SECRETSVC_PORT="${SECRETSVC_PORT}"
  export BACKEND_LOCAL_RESULTSVC_PORT="${RESULTSVC_PORT}"

  # Strip shell proxy settings (e.g. Clash on 127.0.0.1:7897): every call in
  # the local stack is loopback (api <-> secretsvc <-> resultsvc <-> worker)
  # and the ZCode CLI reaches bigmodel directly. Proxied loopback traffic
  # breaks bundle storage with ConnectError when the proxy is down, and
  # all_proxy=socks5:// even crashes httpx client construction (no socksio).
  unset http_proxy https_proxy all_proxy HTTP_PROXY HTTPS_PROXY ALL_PROXY
  export NO_PROXY="127.0.0.1,localhost,::1"
  export no_proxy="127.0.0.1,localhost,::1"

  # Placeholder key: hides the API key field in the UI and skips OpenAI key
  # validation. ZCode workers authenticate through the desktop app login and
  # ignore this value.
  export OAI_SHARED_KEY_ENABLED=true
  export BACKEND_STATIC_OAI_KEY=local-zcode-ambient
}

port_pids() {
  # Listeners only: a bare `lsof -ti :port` also returns client connections
  # (e.g. the browser polling the API), which must never be treated as the
  # port owner.
  lsof -nP -ti ":$1" -sTCP:LISTEN 2>/dev/null || true
}

reclaim_port_if_ours() {
  # Kill leftover listeners from a previous (possibly crashed) run of THIS
  # stack. Ownership = executable under our venv / frontend node_modules, or
  # process cwd inside the repo (next-server renames itself, hiding the path).
  # Foreign processes are left alone.
  local port="$1" pid cmd cwd
  for pid in $(port_pids "${port}"); do
    cmd="$(ps -p "${pid}" -o command= 2>/dev/null || true)"
    cwd="$(lsof -p "${pid}" 2>/dev/null | awk '$4=="cwd" {print $NF}' | head -1)"
    if [[ "${cmd}" == *"${BACKEND_DIR}/.venv"* || "${cmd}" == *"${FRONTEND_DIR}/node_modules"* \
      || "${cwd}" == "${FRONTEND_DIR}"* || "${cwd}" == "${BACKEND_DIR}"* ]]; then
      log "reclaiming port ${port} from leftover process ${pid}"
      kill "${pid}" 2>/dev/null || true
    else
      return 1
    fi
  done
  sleep 1
  for pid in $(port_pids "${port}"); do
    kill -9 "${pid}" 2>/dev/null || true
  done
  return 0
}

start_backend_service() {
  local name="$1" port
  port="$(service_port "${name}")"
  if pid_alive "${name}"; then
    log "${name} already running (pid $(cat "${RUN_DIR}/${name}.pid"))"
    return
  fi
  if [[ -n "$(port_pids "${port}")" ]]; then
    reclaim_port_if_ours "${port}" || { err "port ${port} (${name}) is occupied by a foreign process; stop it or change the port"; return 0; }
  fi
  log "starting ${name}..."
  # Run the venv interpreter directly: `uv run` would add a wrapper process,
  # and stopping the wrapper later leaves the real server orphaned on the port.
  (cd "${BACKEND_DIR}" && nohup "${BACKEND_DIR}/.venv/bin/python" -m "${name}" >"${LOGS_DIR}/${name}.log" 2>&1 &
  echo $! >"${RUN_DIR}/${name}.pid")
}

stop_pid() {
  # Terminate a pid and (best effort) anything still holding its port.
  local pid="$1" port="${2:-}" i
  [[ -z "${pid}" ]] && return 0
  kill "${pid}" 2>/dev/null || true
  for i in $(seq 1 20); do
    kill -0 "${pid}" 2>/dev/null || break
    sleep 0.5
  done
  kill -9 "${pid}" 2>/dev/null || true
  if [[ -n "${port}" ]]; then
    # Server implementations spawn children that outlive their parent.
    local stragglers
    stragglers="$(port_pids "${port}")"
    [[ -n "${stragglers}" ]] && kill ${stragglers} 2>/dev/null || true
    sleep 1
    stragglers="$(port_pids "${port}")"
    [[ -n "${stragglers}" ]] && kill -9 ${stragglers} 2>/dev/null || true
  fi
}

wait_for_http() {
  local url="$1" name="$2" i
  for i in $(seq 1 60); do
    if curl -fsS -o /dev/null "${url}" 2>/dev/null; then
      log "${name} is up (${url})"
      return 0
    fi
    sleep 0.5
  done
  err "${name} did not become healthy; last log lines:"
  tail -20 "${LOGS_DIR}/${name}.log" >&2 || true
  return 1
}

start_frontend() {
  command -v npm >/dev/null 2>&1 || { err "npm not found; start the frontend manually with bun"; return 0; }

  if pid_alive frontend; then
    log "frontend already running (pid $(cat "${RUN_DIR}/frontend.pid"))"
    return
  fi
  if [[ -n "$(port_pids "${FRONTEND_PORT}")" ]]; then
    reclaim_port_if_ours "${FRONTEND_PORT}" || {
      err "port ${FRONTEND_PORT} is served by a non-evmbench process; stop it or set FRONTEND_PORT"
      return 0
    }
  fi

  if [[ ! -x "${FRONTEND_DIR}/node_modules/.bin/next" ]]; then
    log "installing frontend dependencies (npm install)..."
    (cd "${FRONTEND_DIR}" && npm install --no-audit --no-fund)
  fi
  # A stale lock from a crashed dev server would abort the new one.
  if [[ -f "${FRONTEND_DIR}/.next/dev/lock" ]]; then
    rm -f "${FRONTEND_DIR}/.next/dev/lock"
  fi

  log "starting frontend..."
  (cd "${FRONTEND_DIR}" && nohup ./node_modules/.bin/next dev -p "${FRONTEND_PORT}" >"${LOGS_DIR}/frontend.log" 2>&1 &
  echo $! >"${RUN_DIR}/frontend.pid")
  wait_for_http "http://127.0.0.1:${FRONTEND_PORT}" frontend || true
}

cmd_up() {
  check_prereqs
  mkdir -p "${DATA_DIR}" "${LOGS_DIR}" "${RUN_DIR}" "${DATA_DIR}/secrets" "${DATA_DIR}/local_workers"

  if [[ ! -d "${BACKEND_DIR}/.venv" ]]; then
    log "installing backend dependencies (uv sync)..."
    (cd "${BACKEND_DIR}" && uv sync --python 3.12)
  fi

  service_env

  for svc in "${BACKEND_SERVICES[@]}"; do start_backend_service "${svc}"; done

  # secretsvc/resultsvc expose no health endpoint (docs disabled); the API
  # health check below exercises the full dependency chain anyway.
  wait_for_http "http://127.0.0.1:${API_PORT}/v1/integration/frontend" api || exit 1

  start_frontend

  log "stack ready:"
  log "  frontend  http://127.0.0.1:${FRONTEND_PORT}"
  log "  api       http://127.0.0.1:${API_PORT}"
  log "worker job dirs: ${DATA_DIR}/local_workers/<job_id>/"
}

stop_service() {
  local name="$1"
  if pid_alive "${name}"; then
    log "stopping ${name} (pid $(cat "${RUN_DIR}/${name}.pid"))..."
    stop_pid "$(cat "${RUN_DIR}/${name}.pid")" "$(service_port "${name}")"
  else
    log "${name} is not running"
  fi
  # Always sweep the port: a crashed or orphaned listener must not survive us.
  local stragglers
  stragglers="$(port_pids "$(service_port "${name}")")"
  if [[ -n "${stragglers}" ]]; then
    reclaim_port_if_ours "$(service_port "${name}")" || true
  fi
  rm -f "${RUN_DIR}/${name}.pid"
}

cmd_down() {
  # Frontend first so the UI stops polling a dying backend.
  local svc
  stop_service frontend
  for svc in "${BACKEND_SERVICES[@]}"; do stop_service "${svc}"; done
}

cmd_status() {
  local svc
  for svc in frontend "${BACKEND_SERVICES[@]}"; do
    if pid_alive "${svc}"; then
      log "${svc}: running (pid $(cat "${RUN_DIR}/${svc}.pid"))"
    elif [[ "${svc}" == frontend ]] && lsof -ti ":${FRONTEND_PORT}" >/dev/null 2>&1; then
      log "frontend: external (port ${FRONTEND_PORT} served by another process)"
    else
      log "${svc}: stopped"
    fi
  done
}

cmd_logs() {
  local svc="${1:-api}"
  [[ -f "${LOGS_DIR}/${svc}.log" ]] || { err "no log for ${svc}"; exit 1; }
  tail -f "${LOGS_DIR}/${svc}.log"
}

case "${1:-help}" in
  up) cmd_up ;;
  down) cmd_down ;;
  status) cmd_status ;;
  logs) shift; cmd_logs "$@" ;;
  restart)
    cmd_down
    cmd_up
    ;;
  *)
    cat <<EOF
Usage: $0 {up|down|restart|status|logs [api|secretsvc|resultsvc|frontend]}
EOF
    exit 1
    ;;
esac
