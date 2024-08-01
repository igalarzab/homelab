#!/bin/bash

while getopts "hdr" opt; do
    case "$opt" in
    h|\?)
        echo "Usage: $0 [-d|--dry-run] [-r|--run]"
        exit 0
        ;;
    d)
      helmsman \
        --dry-run \
        --subst-env-values \
        -f helmsman.yml
        ;;
    r)
      helmsman \
        --apply \
        --subst-env-values \
        -f helmsman.yml
        ;;
    esac
done
