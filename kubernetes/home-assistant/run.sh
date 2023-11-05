#!/bin/bash

set -e

declare -a FILES=(
  "namespace.yml"

  "ha.service.yml"
  "ha.ingress.yml"
  "ha.deployment.yml"

  "mosquitto.service.yml"
  "mosquitto.deployment.yml"
)

read -p "Domain Root (ex. example.com): " DOMAIN_ROOT

export DOMAIN_ROOT
export TZ="Asia/Tokyo"
export VOLUMES_PATH="/opt/k8s-volumes"

for f in ${FILES[@]}; do
  cat $f | envsubst | kubectl apply -f -
done

# Mosquitto
#kubectl apply -f mosquitto.volume.yml
#kubectl apply -f mosquitto.service.yml
#kubectl apply -f mosquitto.deployment.yml
#
## zigbee2mqtt
#kubectl apply -f zigbee2mqtt.volume.yml
#kubectl apply -f zigbee2mqtt.service.yml
#kubectl apply -f zigbee2mqtt.ingress.yml
#kubectl apply -f zigbee2mqtt.statefulset.yml
#
## node-red
#kubectl apply -f nodered.volume.yml
#kubectl apply -f nodered.service.yml
#kubectl apply -f nodered.ingress.yml
#kubectl apply -f nodered.deployment.yml
