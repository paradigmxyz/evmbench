# evmbench backend

This directory contains the backend services and worker orchestration.

## Build images

```bash
# base
docker build -t evmbench/base:latest -f docker/base/Dockerfile .

# worker
docker build -t evmbench/worker:latest -f docker/worker/Dockerfile .

# backend (api + instancer + secretsvc + resultsvc + oai_proxy + prunner)
docker build -t evmbench/backend:latest -f docker/backend/Dockerfile .
```

## Local run (recommended)

```bash
cp .env.example .env
# For local dev, the placeholder secrets in .env.example are sufficient.
# For internet-exposed deployments, replace them with strong values.
docker compose up -d --build
```

Proxy-token mode (optional):

```bash
# set BACKEND_OAI_KEY_MODE=proxy and OAI_PROXY_AES_KEY=... in .env
docker compose --profile proxy up -d --build
```

ChatGPT/Codex subscription mode (optional):

```bash
# Authenticate Codex once on the host
codex login --device-auth

# Put the base64-encoded auth file into backend/.env
# BACKEND_CODEX_AUTH_JSON_B64=$(base64 -w0 ~/.codex/auth.json)

docker compose up -d --build
```

## k8s development
```bash
# install kind from https://kind.sigs.k8s.io/docs/user/quick-start/
kind create cluster --name evmbench --config kind-config.yaml
kind load --name evmbench docker-image evmbench/worker:latest

# after finishing development:
kind delete cluster --name evmbench
```
