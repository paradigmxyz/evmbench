.PHONY: help backend-lint backend-typecheck frontend-install frontend-build docker-build-images local-up local-down local-status

help:
	@echo "evmbench common tasks"
	@echo ""
	@echo "  backend-lint            - ruff check (backend/)"
	@echo "  backend-typecheck       - python -m py_compile hot paths"
	@echo "  frontend-install        - bun install (frontend/)"
	@echo "  frontend-build          - bun run build (frontend/)"
	@echo "  docker-build-images     - build base/worker/backend/frontend images"
	@echo "  local-up                - start local no-Docker stack incl. frontend (ZCode agent)"
	@echo "  local-down              - stop the local stack"
	@echo "  local-restart           - restart the local stack"
	@echo "  local-status            - show local stack status"

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

local-up:
	./backend/scripts/local_dev.sh up

local-down:
	./backend/scripts/local_dev.sh down

local-restart:
	./backend/scripts/local_dev.sh restart

local-status:
	./backend/scripts/local_dev.sh status

