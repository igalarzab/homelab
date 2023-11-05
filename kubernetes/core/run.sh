#!/bin/bash

set -e

declare -a FILES=(
  "storage-class.yaml"
)

export VOLUMES_PATH="/opt/k8s-volumes"

for f in ${FILES[@]}; do
  cat $f | envsubst | kubectl apply -f -
done
