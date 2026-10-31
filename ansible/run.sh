#!/bin/bash

set -euo pipefail

cd "$(dirname "$0")"

REMOTE_USER="${REMOTE_USER:-$USER}"
USAGE="Usage: ./run.sh saturn|t3code [ansible-playbook options]"

# Parse command line arguments
if [ -z "${1:-}" ]; then
    echo "Error: Playbook parameter is required"
    echo "$USAGE"
    exit 1
fi

EXTRA_ARGS=()

if [ "$1" == "jupyter" ]; then
    echo "Error: Jupyter now uses Talos. See ../README.md."
    exit 1
elif [ "$1" == "saturn" ]; then
    PLAYBOOK="saturn.yml"
    EXTRA_ARGS+=(--extra-vars "@vars.yaml")
elif [ "$1" == "t3code" ]; then
    PLAYBOOK="t3code.yml"
    # ansible.cfg skips host key checks for Saturn; verify the T3 VM's key
    export ANSIBLE_HOST_KEY_CHECKING=True
else
    echo "Error: Invalid playbook '$1'"
    echo "$USAGE"
    exit 1
fi

shift

# An ansible_user in hosts.ini takes precedence over --user
uv run ansible-playbook \
    --inventory hosts.ini \
    --user "$REMOTE_USER" \
    ${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"} \
    "$PLAYBOOK" \
    "$@"
