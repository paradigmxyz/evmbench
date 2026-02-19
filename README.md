<p align="center">
    <picture align="center">
        <img alt="svmbench cover" src="assets/cover-dark.png">
    </picture>
</p>

**svmbench is a benchmark and agent harness for finding and exploiting solana program bugs.**

<a href="#how-it-works"><b><u>how it works</u></b></a> | <a href="#security"><b><u>security</u></b></a> | <a href="#key-services"><b><u>key services</u></b></a> | <a href="#repo-layout"><b><u>repo layout</u></b></a> | <a href="#quickstart-local-dev"><b><u>quickstart (local dev)</u></b></a>

this repository contains a companion interface to the `svmbench` detect evaluation ([code](https://github.com/openai/frontier-evals)).

upload anchor/solana program source code, select an agent, and receive a structured vulnerability report rendered in the ui.


## how it works

### architecture

```
frontend (next.js)
    │
    ├─ POST /v1/jobs/start ───► backend api (fastapi, port 1337)
    │                               ├─► postgresql (job state)
    ├─ GET  /v1/jobs/{id}           ├─► secrets service (port 8081)
    │                               └─► rabbitmq (job queue)
    └─ GET  /v1/jobs/history                │
                                             ▼
                                        instancer (consumer)
                                              │
                                    ┌─────────┴──────────┐
                                    ▼                    ▼
                              docker backend       k8s backend (optional)
                                    │                    │
                                    └────────┬───────────┘
                                             ▼
                                      worker container
                                        ├─► secrets service (fetch bundle)
                                        ├─► (optional) oai proxy (port 8084) ──► openai api
                                        └─► results service (port 8083)
```

### end-to-end flow

1. user uploads a zip of program files via the frontend. the ui sends the archive, selected model key, and (optionally) an openai api key to `/v1/jobs/start`.
2. the backend creates a job record in postgres, stores a secret bundle in the secrets service, and publishes a message to rabbitmq.
3. the instancer consumes the job and starts a worker (docker locally; kubernetes backend is optional).
4. the worker fetches its bundle from the secrets service, unpacks the uploaded zip to `audit/`, then runs codex in "detect-only" mode:
   - prompt: `backend/worker_runner/detect.md` (copied to `$HOME/AGENTS.md` inside the container)
   - model map: `backend/worker_runner/model_map.json` (maps ui model keys to codex model ids)
   - command wrapper: `backend/worker_runner/run_codex_detect.sh`
5. the agent writes `submission/audit.md`. the worker validates that the output contains parseable json with `{"vulnerabilities": [...]}` and then uploads it to the results service.
6. the frontend polls job status and renders the report with file navigation and annotations.

## security

`svmbench` runs an llm-driven agent against uploaded, untrusted code. treat the worker runtime (filesystem, logs, outputs) as an untrusted environment.

see `SECURITY.md` for the full trust model and operational guidance.

openai credential handling:

- **direct byok (default)**: worker receives a plaintext openai key (`OPENAI_API_KEY` / `CODEX_API_KEY`).
- **proxy-token mode (optional)**: worker receives an opaque token and routes requests through `oai_proxy` (plaintext key stays outside the worker).

enabling proxy-token mode:

```bash
cd backend
cp .env.example .env
# set BACKEND_OAI_KEY_MODE=proxy and OAI_PROXY_AES_KEY=...
docker compose --profile proxy up -d --build
```

operational note: worker runtime is bounded by default; override the max audit runtime with `SVM_BENCH_CODEX_TIMEOUT_SECONDS` (default: 10800 seconds).

## key services

| service | default port | role |
|---|---:|---|
| `backend` | 1337 | main api: job submission, status, history, auth |
| `secretsvc` | 8081 | stores and serves per-job secret bundles (zip + key material) |
| `resultsvc` | 8083 | receives worker results, validates/parses, persists to db |
| `oai_proxy` | 8084 | optional openai proxy for proxy-token mode |
| `instancer` | (n/a) | rabbitmq consumer that starts worker containers/pods |
| `worker` | (n/a) | executes the detect-only agent and uploads results |
| postgres | 5432 | job state persistence |
| rabbitmq | 5672 | job queue |

## repo layout

```
.
├── README.md
├── SECURITY.md
├── LICENSE
├── frontend/                 next.js ui (upload zip, select model, view results)
├── backend/
│   ├── api/                  main fastapi api (jobs, auth, integration)
│   ├── instancer/            rabbitmq consumer; starts workers (docker/k8s)
│   ├── secretsvc/            bundle storage service
│   ├── resultsvc/            results ingestion + persistence
│   ├── oai_proxy/            optional openai proxy (proxy-token mode)
│   ├── prunner/              optional cleanup of stale workers
│   ├── worker_runner/        detect prompt + model map + codex runner script
│   ├── docker/
│   │   ├── base/             base image: codex, rust, anchor cli, solana tools, node
│   │   ├── backend/          backend services image
│   │   └── worker/           worker image + entrypoint
│   └── compose.yml           full stack (db/mq + services)
└── deploy/                   optional deployment scripts/examples
```

## quickstart (local dev)

ensure docker and bun are available.

build the base and worker images first (required before starting the stack):

```bash
cd backend
docker build -t svmbench/base:latest -f docker/base/Dockerfile .
docker build -t svmbench/worker:latest -f docker/worker/Dockerfile .
```

start backend stack (api + dependencies):

```bash
cp .env.example .env
# for local dev, the placeholder secrets in .env.example are sufficient.
# for internet-exposed deployments, replace them with strong values.
docker compose up -d --build
```

start frontend dev server:

```bash
cd frontend
bun install
bun dev
```

open:

- `http://127.0.0.1:3000` (frontend)
- `http://127.0.0.1:1337/v1/integration/frontend` (backend config endpoint)

## acknowledgments
this is a fork of [evmbench](https://github.com/paradigmxyz/evmbench).

[![apache-2.0 license](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](/LICENSE)
