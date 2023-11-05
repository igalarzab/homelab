#!/bin/bash

set -e

declare -a FILES=(
  "namespace.yml"

  "ha.service.yml"
  "ha.ingress.yml"
  "ha.deployment.yml"

  "mosquitto.service.yml"
  "mosquitto.deployment.yml"

  "zigbee2mqtt.service.yml"
  "zigbee2mqtt.ingress.yml"
  "zigbee2mqtt.statefulset.yml"

  "nodered.service.yml"
  "nodered.ingress.yml"
  "nodered.deployment.yml"
)

read -p "Domain Root (ex. example.com): " DOMAIN_ROOT

export DOMAIN_ROOT
export TZ="Asia/Tokyo"
export VOLUMES_PATH="/opt/k8s-volumes"

for f in ${FILES[@]}; do
  cat $f | envsubst | kubectl apply -f -
done
