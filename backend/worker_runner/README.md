# Worker runner assets

This folder contains the repo-owned assets that define the detect-only worker behavior.

The worker image copies this directory into the container at `/opt/evmbench/worker_runner/`.

## Files

- `detect.md`: the full instructions prompt copied to `$HOME/AGENTS.md` inside the worker container.
- `run_codex_detect.sh`: runs Codex once and ensures `submission/audit.md` was created.

## Editing guidelines

- Prefer updating `detect.md` rather than hardcoding prompts in Python.
- Model options live in `backend/model_catalog.json`. The backend API, frontend integration config, and worker image all consume that catalog.
- If you change where these files live in the image, update `backend/docker/worker/Dockerfile` and `backend/docker/worker/init.py`.
