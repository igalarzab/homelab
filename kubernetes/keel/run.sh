#!/bin/bash

set -e

declare -a FILES=(
  "namespace.yml"
  "rbac.yml"
  "service.yml"
  # TODO: Not expose for now: "ingress.yml"
  "deployment.yml"
)


read -p "Domain Root (ex. example.com): " DOMAIN_ROOT
read -sp "Admin password: " ADMIN_PASS

export DOMAIN_ROOT
export ADMIN_PASS

for f in ${FILES[@]}; do
  cat $f | envsubst | kubectl apply -f -
done
