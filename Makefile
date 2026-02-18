.PHONY: help backend-lint backend-typecheck frontend-install frontend-build docker-build-images

help:
	@echo "evmbench common tasks"
	@echo ""
	@echo "  backend-lint            - ruff check (backend/)"
	@echo "  backend-typecheck       - python -m py_compile hot paths"
	@echo "  frontend-install        - bun install (frontend/)"
	@echo "  frontend-build          - bun run build (frontend/)"
	@echo "  docker-build-images     - build base/worker/backend/frontend images"

backend-lint:
	cd backend && uv sync --locked --dev
	cd backend && uv run ruff check .

backend-typecheck:
	cd backend && python -m py_compile \
		api/app.py \
		docker/worker/init.py \
		instancer/backends/docker.py \
		instancer/backends/k8s.py

frontend-install:
	cd frontend && bun install

frontend-build:
	cd frontend && bun run build

docker-build-images:
	cd backend && docker build -t evmbench/base:latest -f docker/base/Dockerfile .
	cd backend && docker build -t evmbench/worker:latest -f docker/worker/Dockerfile .
	cd backend && docker build -t evmbench/backend:latest -f docker/backend/Dockerfile .
	cd frontend && docker build -t evmbench/frontend:latest -f Dockerfile .

