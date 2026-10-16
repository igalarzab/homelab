FROM node:24.21.0-bookworm-slim

ARG T3CODE_VERSION=0.1.0
ARG CODEX_VERSION=0.163.0
ARG TARGETARCH

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash build-essential ca-certificates curl gh git \
        libasound2 libatk-bridge2.0-0 libatk1.0-0 libatspi2.0-0 \
        libcups2 libdbus-1-3 libdrm2 libgbm1 libglib2.0-0 libnspr4 libnss3 \
        libpango-1.0-0 libx11-6 libxcb1 libxcomposite1 libxdamage1 \
        libxext6 libxfixes3 libxkbcommon0 libxrandr2 openssh-client \
        python3 python3-venv ripgrep tini unzip fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

RUN set -eu; \
    case "$TARGETARCH" in \
        amd64) t3_arch=x64 ;; \
        arm64) t3_arch=arm64 ;; \
        *) echo "Unsupported architecture: $TARGETARCH" >&2; exit 1 ;; \
    esac; \
    archive="t3-${T3CODE_VERSION}-linux-${t3_arch}.tar.gz"; \
    release_url="https://github.com/pingdotgg/t3code/releases/download/v${T3CODE_VERSION}"; \
    curl -fsSL "${release_url}/SHA256SUMS" -o /tmp/SHA256SUMS; \
    curl -fsSL "${release_url}/${archive}" -o "/tmp/${archive}"; \
    cd /tmp; \
    grep " ${archive}\$" SHA256SUMS | sha256sum --check --strict -; \
    mkdir -p /opt/t3; \
    tar -xzf "$archive" -C /opt/t3 --strip-components=1; \
    ln -s /opt/t3/t3 /usr/local/bin/t3; \
    rm "$archive" SHA256SUMS; \
    t3 --version

RUN npm install --global "@openai/codex@${CODEX_VERSION}" \
    && corepack enable \
    && npm cache clean --force \
    && codex --version

COPY --from=ghcr.io/astral-sh/uv:0.13.1 /uv /uvx /usr/local/bin/

COPY codex.toml /etc/codex/config.toml
COPY --chmod=755 entrypoint.sh /usr/local/bin/workspace-entrypoint

ENV HOME=/home/node \
    SHELL=/bin/bash \
    T3CODE_HOME=/home/node/.t3 \
    CODEX_HOME=/home/node/.codex

RUN install -d -o node -g node /workspace

USER 1000:1000
WORKDIR /workspace

ENTRYPOINT ["/usr/bin/tini", "-g", "--", "/usr/local/bin/workspace-entrypoint"]
CMD ["t3", "serve", "--host", "127.0.0.1", "--port", "3773", "/workspace"]
