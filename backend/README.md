# svmbench backend

this directory contains the backend services and worker orchestration.

## build images

```bash
# base
docker build -t svmbench/base:latest -f docker/base/Dockerfile .

# worker
docker build -t svmbench/worker:latest -f docker/worker/Dockerfile .

# backend (api + instancer + secretsvc + resultsvc + oai_proxy + prunner)
docker build -t svmbench/backend:latest -f docker/backend/Dockerfile .
```

## local run (recommended)

```bash
cp .env.example .env
# for local dev, the placeholder secrets in .env.example are sufficient.
# for internet-exposed deployments, replace them with strong values.
docker compose up -d --build
```

proxy-token mode (optional):

```bash
# set BACKEND_OAI_KEY_MODE=proxy and OAI_PROXY_AES_KEY=... in .env
docker compose --profile proxy up -d --build
```

## k8s development
```bash
# install kind from https://kind.sigs.k8s.io/docs/user/quick-start/
kind create cluster --name svmbench --config kind-config.yaml
kind load --name svmbench docker-image svmbench/worker:latest

# after finishing development:
kind delete cluster --name svmbench
```
