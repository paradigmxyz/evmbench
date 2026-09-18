# Worker runner assets

This folder contains the repo-owned assets that define the detect-only worker behavior.

The worker image copies this directory into the container at `/opt/evmbench/worker_runner/`.

## Files

- `detect.md`: the full instructions prompt copied to `$HOME/AGENTS.md` inside the worker container.
- `model_map.json`: maps UI model keys (sent as `AGENT_ID`) to Codex model IDs.
- `run_codex_detect.sh`: runs Codex once and ensures `submission/audit.md` was created.

## Editing guidelines

- Prefer updating `detect.md` rather than hardcoding prompts in Python.
- Keep `model_map.json`, `api/core/const.py`, and `frontend/src/data/models.json` in sync. The backend tests verify that every UI model can be submitted and resolved by the worker.
- If you change where these files live in the image, update `backend/docker/worker/Dockerfile` and `backend/docker/worker/init.py`.
