#!/bin/bash

set -euo pipefail
umask 077

if [[ $# -ne 3 || ! "$1" =~ ^[a-z0-9][a-z0-9-]*$ || -z "$2" || -z "$3" ]]; then
  echo "Usage: $0 <cluster> <node-ip> <api-domain>" >&2
  exit 1
fi

cluster_name="$1"
node_ip="$2"
api_domain="$3"

if [[ "$api_domain" == *[/:[:space:]]* ]]; then
  echo "Error: Pass the Kubernetes API domain without a scheme, port, or path." >&2
  exit 1
fi

cluster_endpoint="https://$api_domain:6443"
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cluster_dir="$script_dir/$cluster_name"

if [[ ! -f "$cluster_dir/cluster.env" ]]; then
  echo "Error: No Talos configuration for '$cluster_name'." >&2
  exit 1
fi

source "$cluster_dir/cluster.env"

: "${TALOSCTL_VERSION:?Set TALOSCTL_VERSION in cluster.env}"
: "${TALOS_VERSION:?Set TALOS_VERSION in cluster.env}"
: "${KUBERNETES_VERSION:?Set KUBERNETES_VERSION in cluster.env}"
: "${VALIDATION_MODE:?Set VALIDATION_MODE in cluster.env}"
: "${INSTALL_DISK:?Set INSTALL_DISK in cluster.env}"
: "${INSTALL_IMAGE:?Set INSTALL_IMAGE in cluster.env}"

if ! command -v talosctl >/dev/null 2>&1; then
  echo "Error: Install talosctl $TALOSCTL_VERSION before generating configuration." >&2
  exit 1
fi

client_version="$(talosctl version --client | awk '/Tag:/ {print $2}')"
if [[ "$client_version" != "$TALOSCTL_VERSION" ]]; then
  echo "Error: Expected talosctl $TALOSCTL_VERSION, found $client_version." >&2
  exit 1
fi

if [[ ! -f "$cluster_dir/secrets.yaml" ]]; then
  echo "Error: Restore $cluster_dir/secrets.yaml from the existing cluster. See README.md." >&2
  exit 1
fi

output_dir="$cluster_dir/generated"
mkdir -p "$output_dir"
chmod 700 "$output_dir"

talosctl gen config "$cluster_name" "$cluster_endpoint" \
  --talos-version "$TALOS_VERSION" \
  --kubernetes-version "$KUBERNETES_VERSION" \
  --install-disk "$INSTALL_DISK" \
  --install-image "$INSTALL_IMAGE" \
  --with-secrets "$cluster_dir/secrets.yaml" \
  --config-patch "@$cluster_dir/patches/common.yml" \
  --config-patch-control-plane "@$cluster_dir/patches/controlplane.yml" \
  --with-docs=false \
  --with-examples=false \
  --output-types controlplane,talosconfig \
  --output "$output_dir" \
  --force

talosctl --talosconfig "$output_dir/talosconfig" --context "$cluster_name" \
  config endpoint "$node_ip"
talosctl --talosconfig "$output_dir/talosconfig" --context "$cluster_name" \
  config node "$node_ip"
talosctl validate --config "$output_dir/controlplane.yaml" --mode "$VALIDATION_MODE" --strict

talosctl --talosconfig "${TALOSCONFIG:-$HOME/.talos/config}" config merge "$output_dir/talosconfig"

echo "Generated and validated $output_dir/controlplane.yaml. No cluster changes applied."
