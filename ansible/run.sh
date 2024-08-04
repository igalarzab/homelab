#!/bin/bash

COMMAND=$1
REMOTE_USER="${REMOTE_USER:-$USER}"

ansible-playbook \
    --ask-become-pass \
    --inventory-file hosts.ini \
    --user "$REMOTE_USER" \
    server.yml
