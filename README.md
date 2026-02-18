# evmbench

[![Apache-2.0 License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](/LICENSE)
[![Actions Status](https://github.com/paradigmxyz/evmbench/workflows/CI/badge.svg)](https://github.com/paradigmxyz/evmbench/actions)

**evmbench is a benchmark and agent harness for finding and exploiting smart contract bugs.**

<p align="center">
    <picture align="center">
        <img alt="evmbench cover" src="assets/cover-dark.png">
    </picture>
</p>

<a href="#how-it-works"><b><u>How it works</u></b></a> | <a href="#security"><b><u>Security</u></b></a> | <a href="#key-services"><b><u>Key services</u></b></a> | <a href="#repo-layout"><b><u>Repo layout</u></b></a> | <a href="#quickstart-local-dev"><b><u>Quickstart (local dev)</u></b></a>

This repository contains a companion interface to the `evmbench` detect evaluation ([code](https://github.com/openai/frontier-evals)).

Upload contract source code, select an agent, and receive a structured vulnerability report rendered in the UI.


## How it works

### Architecture

```
Frontend (Next.js)
    │
    ├─ POST /v1/jobs/start ───► Backend API (FastAPI, port 1337)
    │                               ├─► PostgreSQL (job state)
    ├─ GET  /v1/jobs/{id}           ├─► Secrets Service (port 8081)
    │                               └─► RabbitMQ (job queue)
    └─ GET  /v1/jobs/history                │
                                             ▼
                                        Instancer (consumer)
                                              │
                                    ┌─────────┴──────────┐
                                    ▼                    ▼
                              Docker backend       K8s backend (optional)
                                    │                    │
                                    └────────┬───────────┘
                                             ▼
                                      Worker container
                                        ├─► Secrets Service (fetch bundle)
                                        ├─► (optional) OAI Proxy (port 8084) ──► OpenAI API
                                        └─► Results Service (port 8083)
```

### End-to-end flow

1. User uploads a zip of contract files via the frontend. The UI sends the archive, selected model key, and (optionally) an OpenAI API key to `/v1/jobs/start`.
2. The backend creates a job record in Postgres, stores a secret bundle in the Secrets Service, and publishes a message to RabbitMQ.
3. The Instancer consumes the job and starts a worker (Docker locally; Kubernetes backend is optional).
4. The worker fetches its bundle from the Secrets Service, unpacks the uploaded zip to `audit/`, then runs Codex in "detect-only" mode:
   - prompt: `backend/worker_runner/detect.md` (copied to `$HOME/AGENTS.md` inside the container)
   - model map: `backend/worker_runner/model_map.json` (maps UI model keys to Codex model IDs)
   - command wrapper: `backend/worker_runner/run_codex_detect.sh`
5. The agent writes `submission/audit.md`. The worker validates that the output contains parseable JSON with `{"vulnerabilities": [...]}` and then uploads it to the Results Service.
6. The frontend polls job status and renders the report with file navigation and annotations.

## Security

`evmbench` runs an LLM-driven agent against uploaded, untrusted code. Treat the worker runtime (filesystem, logs, outputs) as an untrusted environment.

See `SECURITY.md` for the full trust model and operational guidance.

OpenAI credential handling:

- **Direct BYOK (default)**: worker receives a plaintext OpenAI key (`OPENAI_API_KEY` / `CODEX_API_KEY`).
- **Proxy-token mode (optional)**: worker receives an opaque token and routes requests through `oai_proxy` (plaintext key stays outside the worker).

Enabling proxy-token mode:

```bash
cd backend
cp .env.example .env
# set BACKEND_OAI_KEY_MODE=proxy and OAI_PROXY_AES_KEY=...
docker compose --profile proxy up -d --build
```

Operational note: worker runtime is bounded by default; override the max audit runtime with `EVM_BENCH_CODEX_TIMEOUT_SECONDS` (default: 10800 seconds).

## Key services

| Service | Default port | Role |
|---|---:|---|
| `backend` | 1337 | Main API: job submission, status, history, auth |
| `secretsvc` | 8081 | Stores and serves per-job secret bundles (zip + key material) |
| `resultsvc` | 8083 | Receives worker results, validates/parses, persists to DB |
| `oai_proxy` | 8084 | Optional OpenAI proxy for proxy-token mode |
| `instancer` | (n/a) | RabbitMQ consumer that starts worker containers/pods |
| `worker` | (n/a) | Executes the detect-only agent and uploads results |
| Postgres | 5432 | Job state persistence |
| RabbitMQ | 5672 | Job queue |

## Repo layout

```
.
├── README.md
├── SECURITY.md
├── LICENSE
├── frontend/                 Next.js UI (upload zip, select model, view results)
├── backend/
│   ├── api/                  Main FastAPI API (jobs, auth, integration)
│   ├── instancer/            RabbitMQ consumer; starts workers (Docker/K8s)
│   ├── secretsvc/            Bundle storage service
│   ├── resultsvc/            Results ingestion + persistence
│   ├── oai_proxy/            Optional OpenAI proxy (proxy-token mode)
│   ├── prunner/              Optional cleanup of stale workers
│   ├── worker_runner/        Detect prompt + model map + Codex runner script
│   ├── docker/
│   │   ├── base/             Base image: codex, foundry, slither, node, tools
│   │   ├── backend/          Backend services image
│   │   └── worker/           Worker image + entrypoint
│   └── compose.yml           Full stack (DB/MQ + services)
└── deploy/                   Optional deployment scripts/examples
```

## Quickstart (local dev)

Ensure Docker and Bun are available.

Build the base and worker images first (required before starting the stack):

```bash
cd backend
docker build -t evmbench/base:latest -f docker/base/Dockerfile .
docker build -t evmbench/worker:latest -f docker/worker/Dockerfile .
```

Start backend stack (API + dependencies):

```bash
cp .env.example .env
# For local dev, the placeholder secrets in .env.example are sufficient.
# For internet-exposed deployments, replace them with strong values.
docker compose up -d --build
```

Start frontend dev server:

```bash
cd frontend
bun install
bun dev
```

Open:

- `http://127.0.0.1:3000` (frontend)
- `http://127.0.0.1:1337/v1/integration/frontend` (backend config endpoint)
