#!/bin/bash

REMOTE_USER="${REMOTE_USER:-$USER}"

ansible-playbook \
    --ask-become-pass \
    --inventory-file hosts.ini \
    --user "$REMOTE_USER" \
    --extra-vars "@vars.yaml" \
    server.yml
