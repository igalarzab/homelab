#!/bin/bash

set -e

declare -a FILES=(
  "namespace.yml"
  "rbac.yml"
  "service.yml"
  "ingress.yml"
  "statefulset.yml"
)


read -p "Domain Root (ex. example.com): " DOMAIN_ROOT
read -sp "Plex Claim (get it from https://www.plex.tv/claim/): " PLEX_CLAIM

export DOMAIN_ROOT
export PLEX_CLAIM
export TZ="Asia/Tokyo"
export VOLUMES_PATH="/opt/k8s-volumes"
export MULTIMEDIA_PATH="/media/Multimedia"

for f in ${FILES[@]}; do
  cat $f | envsubst | kubectl apply -f -
done
