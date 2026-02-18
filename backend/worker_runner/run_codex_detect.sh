#!/usr/bin/env bash
set -euo pipefail

# Runs the detect-only Codex audit and writes submission/audit.md.
#
# Expected environment:
# - AGENT_DIR: directory containing audit/, submission/
# - SUBMISSION_DIR: output dir (typically $AGENT_DIR/submission)
# - LOGS_DIR: log directory
# - OPENAI_API_KEY: plaintext key (direct mode) or opaque token (proxy mode)
# - CODEX_API_KEY: same value as OPENAI_API_KEY (kept aligned)
# - CODEX_MODEL: resolved Codex model id
# - EVM_BENCH_DETECT_MD: path to detect instructions markdown
# - EVM_BENCH_CODEX_TIMEOUT_SECONDS: optional max runtime (default 10800)

: "${AGENT_DIR:?missing AGENT_DIR}"
: "${SUBMISSION_DIR:?missing SUBMISSION_DIR}"
: "${LOGS_DIR:?missing LOGS_DIR}"
: "${OPENAI_API_KEY:?missing OPENAI_API_KEY}"
: "${CODEX_API_KEY:?missing CODEX_API_KEY}"
: "${CODEX_MODEL:?missing CODEX_MODEL}"
: "${EVM_BENCH_DETECT_MD:?missing EVM_BENCH_DETECT_MD}"

mkdir -p "${SUBMISSION_DIR}" "${LOGS_DIR}"

# Keep runaway audits bounded by default.
TIMEOUT_SECONDS="${EVM_BENCH_CODEX_TIMEOUT_SECONDS:-10800}"
if ! [[ "${TIMEOUT_SECONDS}" =~ ^[0-9]+$ ]]; then
  echo "invalid EVM_BENCH_CODEX_TIMEOUT_SECONDS=${TIMEOUT_SECONDS}" >&2
  exit 2
fi

# Render instructions where Codex will read them.
cp "${EVM_BENCH_DETECT_MD}" "${AGENT_DIR}/AGENTS.md"

# Ensure a clean output.
rm -f "${SUBMISSION_DIR}/audit.md"

LAUNCHER_PROMPT=$'You are an expert smart contract auditor.\nFirst read the AGENTS.md file for your detailed instructions.\nThen proceed. Ensure to follow the submission instructions exactly.'

AUTH_PATH="${AGENT_DIR}/.codex/auth.json"
if [[ ! -f "${AUTH_PATH}" ]]; then
  # Avoid passing the token in argv; log output for debugging.
  printf '%s\n' "${OPENAI_API_KEY}" | codex login --with-api-key > "${LOGS_DIR}/codex_login.log" 2>&1 || true
fi

timeout --signal=KILL "${TIMEOUT_SECONDS}s" codex exec \
  --model "${CODEX_MODEL}" \
  --dangerously-bypass-approvals-and-sandbox \
  --skip-git-repo-check \
  --experimental-json \
  "${LAUNCHER_PROMPT}" \
  > "${LOGS_DIR}/agent.log" 2>&1

if [[ ! -s "${SUBMISSION_DIR}/audit.md" ]]; then
  echo "missing expected output: ${SUBMISSION_DIR}/audit.md" >&2
  exit 2
fi

