FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_NO_DEV=1
ENV UV_TOOL_BIN_DIR=/usr/local/bin

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

WORKDIR /app

COPY pyproject.toml uv.lock alembic.ini ./

COPY api api
COPY instancer instancer
COPY migrations migrations
COPY oai_proxy oai_proxy
COPY prunner prunner
COPY secretsvc secretsvc
COPY resultsvc resultsvc

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app"
ENTRYPOINT []
