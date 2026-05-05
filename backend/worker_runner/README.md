# Worker runner assets

This folder contains the repo-owned assets that define the detect-only worker behavior.

The worker image copies this directory into the container at `/opt/evmbench/worker_runner/`.

## Files

- `detect.md`: the full instructions prompt embedded in the first Codex prompt and copied to `$HOME/AGENTS.md`.
- `model_map.json`: maps UI model keys (sent as `AGENT_ID`) to Codex model IDs.
- `run_codex_detect.sh`: runs Codex once and ensures `submission/audit.md` was created.

## Editing guidelines

- Prefer updating `detect.md` rather than hardcoding prompts in Python or shell.
- Keep the launcher prompt stable and put variable audit content behind tool/file access so vLLM prefix caching can reuse the shared instruction prefix across jobs.
- Keep `model_map.json` in sync with the model options in the frontend.
- If you change where these files live in the image, update `backend/docker/worker/Dockerfile` and `backend/docker/worker/init.py`.
