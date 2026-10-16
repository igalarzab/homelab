#!/bin/sh
set -eu

umask 077
mkdir -p "$T3CODE_HOME" "$CODEX_HOME" "$HOME/.cache" "$HOME/.config"

if [ ! -e "$CODEX_HOME/config.toml" ]; then
    cp /etc/codex/config.toml "$CODEX_HOME/config.toml"
fi

exec "$@"
