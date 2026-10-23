# Worker runner assets

This folder contains the repo-owned assets that define the detect-only worker behavior.

The worker image copies this directory into the container at `/opt/evmbench/worker_runner/`.
For local no-Docker runs, point `EVM_BENCH_RUNNER_DIR` at this directory and select the
runner script via `EVM_BENCH_RUNNER_SCRIPT` (see `backend/scripts/local_dev.sh`).

## Files

- `detect.md`: the full instructions prompt copied to `$HOME/AGENTS.md` inside the worker container.
- `model_map.json`: maps UI model keys (sent as `AGENT_ID`) to agent model IDs (ZCode GLM models).
- `run_codex_detect.sh`: runs Codex once and ensures `submission/audit.md` was created.
- `run_zcode_detect.sh`: same contract for the ZCode CLI (headless, local no-Docker runs).
- `zcode_provider_config.py`: pins the requested model in a per-job copy of the ZCode
  personal provider config (the CLI has no `--model` flag).
- `zcode_watchdog.py`: portable hard-timeout wrapper (macOS has no GNU `timeout`);
  kills the whole zcode process group on expiry.

## Editing guidelines

- Prefer updating `detect.md` rather than hardcoding prompts in Python.
- Keep `model_map.json`, `api/core/const.py`, and `frontend/src/data/models.json` in sync. The backend tests verify that every UI model can be submitted and resolved by the worker.
- If you change where these files live in the image, update `backend/docker/worker/Dockerfile` and `backend/docker/worker/init.py`.
