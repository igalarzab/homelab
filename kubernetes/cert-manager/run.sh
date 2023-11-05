#!/bin/bash

set -e

declare -a FILES=(
  "secret.yaml" 
  "cluster-issuer.yaml" 
  "certificate.yaml"
)

read -p "Domain Root (ex. example.com): " DOMAIN_ROOT
read -p "Cloudflare Email (ex. john@example.com): " CLOUDFLARE_EMAIL
read -sp "Cloudflare API Token (ex. abcdef123): " CLOUDFLARE_TOKEN
echo

export CERT_NAME="cluster-wildcard"
export CERT_SECRET_NAME="${CERT_NAME}-tls"
export DOMAIN_ROOT
export CLOUDFLARE_EMAIL
export CLOUDFLARE_TOKEN

for f in ${FILES[@]}; do
  cat $f | envsubst | kubectl apply -f -
done

while ! kubectl -n traefik get secret/${CERT_SECRET_NAME} > /dev/null 2>&1;  do 
  echo "Waiting for the certificate generation..."; 
  sleep 1; 
done

cat default-certificate.yaml | envsubst | kubectl apply -f -
