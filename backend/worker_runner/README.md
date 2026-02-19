# worker runner assets

this folder contains the repo-owned assets that define the detect-only worker behavior.

the worker image copies this directory into the container at `/opt/svmbench/worker_runner/`.

## files

- `detect.md`: the full instructions prompt copied to `$HOME/AGENTS.md` inside the worker container.
- `model_map.json`: maps ui model keys (sent as `AGENT_ID`) to codex model ids.
- `run_codex_detect.sh`: runs codex once and ensures `submission/audit.md` was created.

## editing guidelines

- prefer updating `detect.md` rather than hardcoding prompts in python.
- keep `model_map.json` in sync with the model options in the frontend.
- if you change where these files live in the image, update `backend/docker/worker/Dockerfile` and `backend/docker/worker/init.py`.
