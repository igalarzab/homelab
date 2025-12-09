#!/bin/bash

REMOTE_USER="${REMOTE_USER:-$USER}"

# Parse command line arguments
if [ -z "$1" ]; then
    echo "Error: Playbook parameter is required"
    echo "Usage: ./run.sh [jupyter|saturn]"
    exit 1
fi

if [ "$1" == "jupyter" ]; then
    PLAYBOOK="jupyter.yml"
elif [ "$1" == "saturn" ]; then
    PLAYBOOK="saturn.yml"
else
    echo "Error: Invalid playbook '$1'"
    exit 1
fi

ansible-playbook \
    --ask-become-pass \
    --inventory hosts.ini \
    --user "$REMOTE_USER" \
    --extra-vars "@vars.yaml" \
    "$PLAYBOOK"
