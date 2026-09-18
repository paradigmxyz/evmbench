FROM ubuntu:24.04
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ENV WORKSPACE_BASE=/home \
    AGENT_DIR=/home/agent \
    AUDIT_DIR=/home/agent/audit \
    SUBMISSION_DIR=/home/agent/submission \
    LOGS_DIR=/home/logs \
    NVM_DIR=/home/agent/.nvm \
    FOUNDRY_DIR=/home/agent/.foundry

ENV PATH=$FOUNDRY_DIR/bin:$PATH
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

# install the pinned Codex release and its platform-specific runtime helpers
# Override at build time: docker build --build-arg CODEX_VERSION=X.Y.Z ...
ARG CODEX_VERSION=0.155.1
RUN npm install --global "@openai/codex@${CODEX_VERSION}" && codex --version

# install ripgrep
RUN apt-get update && apt-get install -y --no-install-recommends ripgrep && rm -rf /var/lib/apt/lists/*

WORKDIR "$AGENT_DIR"

# install foundry
RUN curl -L https://foundry.paradigm.xyz | bash
RUN foundryup

# install slither (static analysis). This is "best effort": solc versioning
# varies across codebases; users/agents can install/use solc-select as needed.
RUN python3 -m pip install --no-cache-dir slither-analyzer solc-select

# set the git config up
RUN git config --global --add safe.directory $AGENT_DIR && \
    git config --global --add safe.directory $AUDIT_DIR && \
    git config --global user.email "agent@evmbench.local" && \
    git config --global user.name "agent"
