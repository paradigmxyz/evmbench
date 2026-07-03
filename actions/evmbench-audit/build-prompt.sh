#!/usr/bin/env bash
set -euo pipefail

: "${FILES_FILE:?missing FILES_FILE}"

prompt_file="${RUNNER_TEMP}/evmbench-audit-prompt.md"

{
  cat "$GITHUB_ACTION_PATH/actions/evmbench-audit/prompt.md"
  echo
  echo "## Audit scope"
  echo
  echo "Prioritize these files. You may inspect surrounding code, interfaces, tests, configs, and docs as needed for context, but do not report issues outside the relevant Solidity scope unless they directly affect these files."
  echo
  sed 's/^/- `/' "$FILES_FILE" | sed 's/$/`/'
  if [[ -n "${EXTRA_PROMPT:-}" ]]; then
    echo
    echo "## Additional caller instructions"
    echo
    printf '%s\n' "$EXTRA_PROMPT"
  fi
} > "$prompt_file"

printf 'prompt-file=%s\n' "$prompt_file" >> "$GITHUB_OUTPUT"
echo "evmbench: wrote audit prompt to $prompt_file"
