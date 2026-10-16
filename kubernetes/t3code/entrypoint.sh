#!/bin/sh
set -eu

umask 077
mkdir -p "$T3CODE_HOME" "$CODEX_HOME" "$HOME/.cache" "$HOME/.config"

if [ ! -e "$CODEX_HOME/config.toml" ]; then
    cp /etc/codex/config.toml "$CODEX_HOME/config.toml"
fi

if [ "${1:-}" = t3 ]; then
    export T3CODE_CHANNEL="${T3CODE_CHANNEL:-stable}"
    export T3CODE_INSTALL_BIN_DIR="$HOME/.local/bin"
    export PATH="$T3CODE_INSTALL_BIN_DIR:$PATH"
    launcher="$T3CODE_INSTALL_BIN_DIR/t3"

    case "$T3CODE_CHANNEL" in
        stable|nightly) ;;
        *) echo "T3CODE_CHANNEL must be stable or nightly" >&2; exit 1 ;;
    esac
    case "${T3CODE_UPDATE_ON_START:-true}" in
        true|false) ;;
        *) echo "T3CODE_UPDATE_ON_START must be true or false" >&2; exit 1 ;;
    esac

    if [ ! -x "$launcher" ] || [ "${T3CODE_UPDATE_ON_START:-true}" = true ]; then
        installer="$(mktemp)"
        trap 'rm -f "$installer"' EXIT
        if curl -fsSL --connect-timeout 10 --max-time 30 \
            https://t3.codes/install.sh -o "$installer" \
            && timeout --kill-after=5s 180s sh "$installer"; then
            echo "workspace: T3 installation check complete"
        elif [ -x "$launcher" ]; then
            echo "workspace: T3 update failed; using the cached installation" >&2
        else
            echo "workspace: T3 installation failed and no cached runtime exists; check network access and restart" >&2
            exit 1
        fi
        rm -f "$installer"
        trap - EXIT
    fi

    if ! version="$("$launcher" --version)"; then
        echo "workspace: cached T3 runtime does not run; check its dependencies or reinstall the release under $T3CODE_HOME/runtime/versions" >&2
        exit 1
    fi

    if [ "${2:-}" = serve ]; then
        version_file="$T3CODE_HOME/.workspace-version"
        previous_version=""
        if [ -f "$version_file" ]; then
            previous_version="$(cat "$version_file")"
        fi
        if [ "$version" != "$previous_version" ] && [ -d "$T3CODE_HOME/userdata" ]; then
            backup="$T3CODE_HOME/backups/before-upgrade.tar.gz"
            mkdir -p "$T3CODE_HOME/backups"
            echo "workspace: saving T3 state before launching $version"
            if ! tar -czf "$backup.tmp" -C "$T3CODE_HOME" userdata; then
                rm -f "$backup.tmp"
                echo "workspace: cannot snapshot T3 state; check free space and volume permissions before restarting" >&2
                exit 1
            fi
            mv "$backup.tmp" "$backup"
            printf '%s\n' "$previous_version" > "$backup.version"
        fi
        printf '%s\n' "$version" > "$version_file.tmp"
        mv "$version_file.tmp" "$version_file"
    fi
    echo "workspace: launching $version; channel=$T3CODE_CHANNEL"
fi

exec "$@"
