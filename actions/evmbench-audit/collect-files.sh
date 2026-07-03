#!/usr/bin/env bash
set -euo pipefail

truthy() {
  value="$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')"
  case "$value" in
    1 | true | yes | y | on) return 0 ;;
    *) return 1 ;;
  esac
}

write_output() {
  printf '%s=%s\n' "$1" "$2" >> "$GITHUB_OUTPUT"
}

pathspec_file="${RUNNER_TEMP}/evmbench-pathspecs.txt"
files_file="${RUNNER_TEMP}/evmbench-files.txt"
: > "$pathspec_file"
: > "$files_file"

while IFS= read -r pathspec; do
  pathspec="${pathspec#"${pathspec%%[![:space:]]*}"}"
  pathspec="${pathspec%"${pathspec##*[![:space:]]}"}"
  if [[ -n "$pathspec" ]]; then
    printf '%s\n' "$pathspec" >> "$pathspec_file"
  fi
done <<< "${INPUT_PATHS:-:(glob)**/*.sol}"

if [[ ! -s "$pathspec_file" ]]; then
  printf '%s\n' ':(glob)**/*.sol' > "$pathspec_file"
fi
pathspecs=()
while IFS= read -r pathspec; do
  pathspecs+=("$pathspec")
done < "$pathspec_file"

base_ref="${INPUT_BASE_REF:-}"
head_ref="${INPUT_HEAD_REF:-}"

if [[ -z "$base_ref" && "${EVENT_NAME:-}" == "pull_request" ]]; then
  base_ref="${PR_BASE_SHA:-}"
fi
if [[ -z "$head_ref" && "${EVENT_NAME:-}" == "pull_request" ]]; then
  head_ref="${PR_HEAD_SHA:-${CURRENT_SHA:-HEAD}}"
fi
if [[ -z "$base_ref" && -n "${BEFORE_SHA:-}" && ! "${BEFORE_SHA:-}" =~ ^0+$ ]]; then
  base_ref="$BEFORE_SHA"
fi
if [[ -z "$head_ref" ]]; then
  head_ref="${CURRENT_SHA:-HEAD}"
fi

use_diff=false
if truthy "${INPUT_CHANGED_ONLY:-true}" && [[ -n "$base_ref" && -n "$head_ref" ]]; then
  if git cat-file -e "${base_ref}^{commit}" 2>/dev/null && git cat-file -e "${head_ref}^{commit}" 2>/dev/null; then
    use_diff=true
  else
    echo "evmbench: base/head commits are not available locally; auditing all matching files." >&2
  fi
fi

if [[ "$use_diff" == true ]]; then
  git diff --name-only "$base_ref" "$head_ref" -- "${pathspecs[@]}" > "$files_file"
else
  git ls-files -- "${pathspecs[@]}" > "$files_file"
fi

sort -u "$files_file" -o "$files_file"
files_count="$(wc -l < "$files_file" | tr -d '[:space:]')"

if [[ "$files_count" == "0" ]]; then
  write_output "has-files" "false"
else
  write_output "has-files" "true"
fi
write_output "files-count" "$files_count"
write_output "files-file" "$files_file"

echo "evmbench: selected $files_count file(s) for audit"
if [[ "$files_count" != "0" ]]; then
  sed 's/^/  - /' "$files_file"
fi
