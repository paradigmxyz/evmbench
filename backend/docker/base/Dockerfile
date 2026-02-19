FROM ubuntu:24.04
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ENV WORKSPACE_BASE=/home \
    AGENT_DIR=/home/agent \
    AUDIT_DIR=/home/agent/audit \
    SUBMISSION_DIR=/home/agent/submission \
    LOGS_DIR=/home/logs \
    NVM_DIR=/home/agent/.nvm

ENV PATH=$AGENT_DIR/.local/bin:$PATH
ENV HOME=$AGENT_DIR

ENV DEBIAN_FRONTEND=noninteractive
ENV PIP_BREAK_SYSTEM_PACKAGES=1
RUN find /usr/lib -name EXTERNALLY-MANAGED -delete

# dependencies for all the stuff we'll be using
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl unzip ca-certificates gnupg \
    zip unzip git nano vim jq bc lsof xxd \
    build-essential pkg-config libssl-dev \
    linux-libc-dev libstdc++6 \
    python3 python3-pip python3-venv python-is-python3 \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && corepack enable \
    && rm -rf /var/lib/apt/lists/*

# setup the folders
RUN mkdir -p "$AUDIT_DIR" "$SUBMISSION_DIR" "$LOGS_DIR"

# install codex
# Default to the latest known stable release tag; can be overridden at build time:
#   docker build --build-arg CODEX_VERSION=rust-vX.Y.Z ...
ARG CODEX_VERSION=rust-v0.104.0
ARG TARGETARCH
RUN set -eux; \
    arch="${TARGETARCH:-$(dpkg --print-architecture)}"; \
    case "$arch" in \
      amd64) CODEX_ARCH="x86_64" ;; \
      arm64) CODEX_ARCH="aarch64" ;; \
      *) echo "Unsupported arch: $arch" >&2; exit 1 ;; \
    esac; \
    CODEX_URL="https://github.com/openai/codex/releases/download/${CODEX_VERSION}/codex-${CODEX_ARCH}-unknown-linux-gnu.tar.gz"; \
    mkdir -p /usr/local/src/codex; cd /usr/local/src/codex; \
    curl -L -o codex.tgz "$CODEX_URL"; \
    ENTRY="$(tar -tzf codex.tgz | grep -v '/$' | head -n1)"; \
    test -n "$ENTRY"; \
    tar -xzf codex.tgz -O "$ENTRY" > /usr/local/bin/codex; \
    chmod 0755 /usr/local/bin/codex; \
    cd /; rm -rf /usr/local/src/codex; \
    codex --version

# install ripgrep
RUN apt-get update && apt-get install -y --no-install-recommends ripgrep && rm -rf /var/lib/apt/lists/*

WORKDIR "$AGENT_DIR"

# install rust and cargo
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/home/agent/.cargo/bin:$PATH"

# install solana cli tools
RUN sh -c "$(curl -sSfL https://release.anza.xyz/stable/install)"
ENV PATH="/home/agent/.local/share/solana/install/active_release/bin:$PATH"

# install anchor cli
RUN cargo install --git https://github.com/coral-xyz/anchor avm --force && \
    avm install latest && \
    avm use latest

# set the git config up
RUN git config --global --add safe.directory $AGENT_DIR && \
    git config --global --add safe.directory $AUDIT_DIR && \
    git config --global user.email "agent@svmbench.local" && \
    git config --global user.name "agent"
