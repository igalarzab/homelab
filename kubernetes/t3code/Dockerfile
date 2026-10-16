FROM node:24.21.0-bookworm-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash build-essential ca-certificates curl gh git \
        libasound2 libatk-bridge2.0-0 libatk1.0-0 libatspi2.0-0 \
        libcups2 libdbus-1-3 libdrm2 libgbm1 libglib2.0-0 libnspr4 libnss3 \
        libpango-1.0-0 libx11-6 libxcb1 libxcomposite1 libxdamage1 \
        libxext6 libxfixes3 libxkbcommon0 libxrandr2 openssh-client \
        python3 python3-venv ripgrep tini unzip fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

RUN corepack enable

COPY --from=ghcr.io/astral-sh/uv:0.13.1 /uv /uvx /usr/local/bin/

COPY codex.toml /etc/codex/config.toml
COPY --chmod=755 entrypoint.sh /usr/local/bin/workspace-entrypoint

ENV HOME=/home/node \
    SHELL=/bin/bash \
    T3CODE_HOME=/home/node/.t3 \
    CODEX_HOME=/home/node/.codex \
    T3CODE_CHANNEL=stable \
    T3CODE_UPDATE_ON_START=true \
    NPM_CONFIG_PREFIX=/home/node/.local \
    PATH=/home/node/.local/bin:${PATH}

RUN install -d -o node -g node /workspace

USER 1000:1000
WORKDIR /workspace

ENTRYPOINT ["/usr/bin/tini", "-g", "--", "/usr/local/bin/workspace-entrypoint"]
CMD ["t3", "serve", "--host", "127.0.0.1", "--port", "3773", "/workspace"]
