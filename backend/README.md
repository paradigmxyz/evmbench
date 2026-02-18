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

## k8s development
```bash
# install kind from https://kind.sigs.k8s.io/docs/user/quick-start/
kind create cluster --name evmbench --config kind-config.yaml
kind load --name evmbench docker-image evmbench/worker:latest

# after finishing development:
kind delete cluster --name evmbench
```
