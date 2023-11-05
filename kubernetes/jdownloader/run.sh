#!/bin/bash

set -e

declare -a FILES=(
  "namespace.yml"
  "service.yml"
  "ingress.yml"
  "deployment.yml"
)

read -p "Domain Root (ex. example.com): " DOMAIN_ROOT

export DOMAIN_ROOT
export TZ="Asia/Tokyo"
export VOLUMES_PATH="/opt/k8s-volumes"
export MULTIMEDIA_PATH="/media/Multimedia/Downloads"

for f in ${FILES[@]}; do
  cat $f | envsubst | kubectl apply -f -
done
