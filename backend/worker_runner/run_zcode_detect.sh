#!/usr/bin/env bash
set -euo pipefail

# Runs the detect-only audit with the ZCode CLI (headless) and writes
# submission/audit.md. Local no-Docker counterpart of run_codex_detect.sh.
#
# Expected environment:
# - AGENT_DIR: workspace containing audit/, submission/ and AGENTS.md
# - SUBMISSION_DIR: output dir (typically $AGENT_DIR/submission)
# - LOGS_DIR: log directory
# - AGENT_MODEL: resolved ZCode model id (e.g. GLM-5.3); CODEX_MODEL honored as fallback
# - CODEX_REASONING_EFFORT: advisory effort level (low|medium|high, default medium)
# - EVM_BENCH_DETECT_MD: path to detect instructions markdown
# - EVM_BENCH_ZCODE_TIMEOUT_SECONDS: optional max runtime (default 10800)
# - ZCODE_BIN: zcode executable (default: zcode)
# - ZCODE_MODE: permission mode (default: yolo; plan = read-only audits)
#
# Notes:
# - The zcode CLI has no --model flag; the model is pinned through a per-job
#   copy of the personal provider config (see zcode_provider_config.py).
# - The worker sets HOME=$AGENT_DIR for agent isolation, but the zcode CLI
#   needs the real home for its credentials, so we restore it here.
# - ZCode reuses the desktop app login; OPENAI_API_KEY is not used.

: "${AGENT_DIR:?missing AGENT_DIR}"
: "${SUBMISSION_DIR:?missing SUBMISSION_DIR}"
: "${LOGS_DIR:?missing LOGS_DIR}"
: "${EVM_BENCH_DETECT_MD:?missing EVM_BENCH_DETECT_MD}"

if [[ -n "${OAI_PROXY_BASE_URL:-}" ]]; then
  echo "proxy key mode is not supported with the zcode runner" >&2
  exit 2
fi

MODEL="${AGENT_MODEL:-${CODEX_MODEL:-GLM-5.3}}"
ZCODE_BIN="${ZCODE_BIN:-zcode}"
ZCODE_MODE="${ZCODE_MODE:-yolo}"
RUNNER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

REASONING_EFFORT="${CODEX_REASONING_EFFORT:-medium}"
case "${REASONING_EFFORT}" in
  low) EFFORT_DIRECTIVE='Work efficiently and keep the analysis focused.' ;;
  medium) EFFORT_DIRECTIVE='Balance thoroughness and efficiency.' ;;
  high) EFFORT_DIRECTIVE='Be maximally thorough: reason step by step, cover every attack surface, and verify each conclusion before reporting.' ;;
  max) EFFORT_DIRECTIVE='Spare no effort: reason exhaustively step by step, enumerate every attack surface, verify each conclusion against the code, and re-review the finished report for completeness and accuracy before submitting.' ;;
  *) echo "invalid CODEX_REASONING_EFFORT" >&2; exit 2 ;;
esac

TIMEOUT_SECONDS="${EVM_BENCH_ZCODE_TIMEOUT_SECONDS:-10800}"
if ! [[ "${TIMEOUT_SECONDS}" =~ ^[0-9]+$ ]]; then
  echo "invalid EVM_BENCH_ZCODE_TIMEOUT_SECONDS=${TIMEOUT_SECONDS}" >&2
  exit 2
fi

command -v "${ZCODE_BIN}" >/dev/null 2>&1 || {
  echo "zcode CLI not found on PATH (ZCODE_BIN=${ZCODE_BIN})" >&2
  exit 2
}
command -v python3 >/dev/null 2>&1 || { echo "python3 not found on PATH" >&2; exit 2; }

mkdir -p "${SUBMISSION_DIR}" "${LOGS_DIR}"

# The worker points HOME at the agent dir; the zcode CLI resolves credentials
# and provider config from the real home, so restore it via the passwd entry.
# EVM_BENCH_ZCODE_HOME overrides the lookup (tests / unusual setups).
REAL_HOME="${EVM_BENCH_ZCODE_HOME:-$(python3 -c 'import os,pwd; print(pwd.getpwuid(os.getuid()).pw_dir)')}" || {
  echo "unable to resolve real home directory" >&2
  exit 2
}

# Pin the requested model in a per-job provider config copy. The bundled
# zcode wrapper honors a pre-set ZCODE_PERSONAL_PROVIDER_CONFIG_FILE.
PROVIDER_CONFIG="${AGENT_DIR}/.zcode_provider_config.json"
if python3 "${RUNNER_DIR}/zcode_provider_config.py" \
    "${REAL_HOME}/.zcode/v2/provider_config.json" \
    "${PROVIDER_CONFIG}" \
    "${MODEL}" 2>>"${LOGS_DIR}/runner_config.log"; then
  export ZCODE_PERSONAL_PROVIDER_CONFIG_FILE="${PROVIDER_CONFIG}"
else
  echo "warning: unable to pin model ${MODEL}; continuing with the ambient default model" | tee -a "${LOGS_DIR}/runner_config.log" >&2
fi

# Render instructions where the agent will read them.
cp "${EVM_BENCH_DETECT_MD}" "${AGENT_DIR}/AGENTS.md"

# Ensure a clean output.
rm -f "${SUBMISSION_DIR}/audit.md"

LAUNCHER_PROMPT="You are an expert smart contract auditor.
First read the AGENTS.md file for your detailed instructions.
Then proceed. Ensure to follow the submission instructions exactly.
${EFFORT_DIRECTIVE}"

export HOME="${REAL_HOME}"

# --mode must be passed explicitly: the bundled zcode wrapper downgrades
# headless prompts without an explicit mode to read-only plan mode, while
# audits may need to build and test (foundry) alongside reading sources.
status=0
python3 "${RUNNER_DIR}/zcode_watchdog.py" \
  "${TIMEOUT_SECONDS}" \
  "${LOGS_DIR}/agent.log" \
  -- "${ZCODE_BIN}" --cwd "${AGENT_DIR}" --mode "${ZCODE_MODE}" -p "${LAUNCHER_PROMPT}" || status=$?

if [[ "${status}" -ne 0 ]]; then
  echo "zcode agent exited with code=${status} (see ${LOGS_DIR}/agent.log)" >&2
  exit "${status}"
fi

if [[ ! -s "${SUBMISSION_DIR}/audit.md" ]]; then
  echo "missing expected output: ${SUBMISSION_DIR}/audit.md" >&2
  exit 2
fi
