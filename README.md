# Homelab

Kubernetes clusters, a development VM, home automation and media services. Talos runs
the Kubernetes nodes, Helmsman deploys the cluster applications and Ansible configures
the VM.

## Architecture

| Layer                           | Tools and configuration                                       |
| ------------------------------- | ------------------------------------------------------------- |
| Operating system and Kubernetes | Talos machine configuration and `talosctl`                    |
| Persistent storage              | Local volumes and Hetzner, Proxmox, or SMB CSI drivers        |
| Networking                      | Traefik ingress and Multus for additional pod networks        |
| Certificates and DNS            | cert-manager, External DNS, and Cloudflare                    |
| Authentication                  | Pocket ID                                                     |
| Monitoring and updates          | Metrics Server and Keel                                       |
| Home automation                 | Home Assistant, ESPHome, Node-RED, Zigbee2MQTT, and Mosquitto |
| Media and downloads             | Plex and JDownloader                                          |

Each cluster has its own Talos inputs, credentials and Helm release manifest, and that
manifest picks its storage drivers and applications. Servers and VMs are created outside
this repository.

## Project structure

```text
homelab/
  talos/
    generate.sh                   # Generate, validate, and register the Talos context
    <cluster>/
      cluster.env                 # Pinned versions, installation disk, and image
      schematic.yml               # Talos Image Factory customizations
      patches/
        common.yml                # Cluster-wide machine configuration
        controlplane.yml          # Control-plane configuration
      secrets.yaml                # Local credentials, ignored by Git
      generated/                  # Generated configuration, ignored by Git
  kubernetes/
    helmsman.<cluster>.yml        # Helm releases for each cluster
    .env                          # Shared application settings
    .env.<cluster>                # Local overrides and secrets, ignored by Git
    run.py                        # Application deployment commands
    <service>/                    # Helm values and supporting manifests
  config/
    esphome/                      # Device firmware configuration
    home-assistant/               # Dashboards, automations, and integrations
    mosquitto/                    # MQTT configuration
    node-red/                     # Flows and settings
    zigbee2mqtt/                  # Zigbee configuration and device mappings
  ansible/                        # T3 development VM and legacy kubeadm provisioning
```

## Prerequisites

- Python and `uv`
- `talosctl`, `kubectl`, Helm, and Helmsman

## Set up a new workstation

These steps restore access to an existing cluster. Run them from the repository root, all
in the same shell. `CLUSTER` is a directory name under `talos/`, and the addresses below are
examples:

```bash
CLUSTER=your-cluster-name
NODE_IP=192.0.2.10
API_DOMAIN=kubernetes.example.com
uv sync
```

### Restore credentials and generate configuration

Restore the original cluster secrets from your secure backup:

```bash
cp /path/to/backup/secrets.yaml "talos/$CLUSTER/secrets.yaml"
./talos/generate.sh "$CLUSTER" "$NODE_IP" "$API_DOMAIN"
```

The script recreates `talos/<cluster>/generated/controlplane.yaml` and
`talos/<cluster>/generated/talosconfig`, validates the machine configuration, and
registers the cluster in `~/.talos/config`, or the file specified by `TALOSCONFIG`.

You can then use `talosctl` directly:

```bash
talosctl version
```

List saved contexts with `talosctl config contexts` and switch between them with
`talosctl config context <context-name>`.

### Restore Kubernetes access

Fetch the admin kubeconfig from the running cluster and name its context to match
the deployment configuration:

```bash
talosctl kubeconfig --force-context-name "$CLUSTER"
kubectl --context "$CLUSTER" get nodes
```

This merges the context into `~/.kube/config`. A new workstation doesn't need to apply
machine configuration or bootstrap the cluster.

### Restore application settings

Restore the cluster's environment file, which contains application credentials and
overrides for the shared settings in `kubernetes/.env`:

```bash
cp /path/to/backup/cluster.env "kubernetes/.env.$CLUSTER"
```

## Deploy applications

From the repository root, enter the Kubernetes directory. The first argument to
`run.py` selects the Kubernetes context, Helm release manifest, and environment file:

```bash
cd kubernetes

# Review the deployment plan
uv run python run.py "$CLUSTER" dry-run

# Apply the configured releases
uv run python run.py "$CLUSTER" apply

# Deploy one configured application
uv run python run.py "$CLUSTER" apply -n home-assistant

# Check for chart updates
uv run python run.py "$CLUSTER" outdated
```

### Restart workloads with restarted pods

From `kubernetes/`:

```bash
uv run python restart-pods.py "$CLUSTER"
```

The script scans every namespace in that context. If a pod has a container with a
`restartCount` above zero, it restarts the owning Deployment, StatefulSet or DaemonSet
once. That rolls out every pod in the workload, and the script doesn't wait for the
rollouts to finish.

## Change Talos configuration

Edit the cluster's inputs or patches, regenerate the configuration and review the diff
before applying it. These commands pass the generated client configuration explicitly, so
they target this cluster whatever your active Talos context is. Run them from the
repository root:

```bash
./talos/generate.sh "$CLUSTER" "$NODE_IP" "$API_DOMAIN"
talosctl --talosconfig "talos/$CLUSTER/generated/talosconfig" --context "$CLUSTER" \
  apply-config --file "talos/$CLUSTER/generated/controlplane.yaml" --dry-run
```

After reviewing the diff, apply the intended change:

```bash
talosctl --talosconfig "talos/$CLUSTER/generated/talosconfig" --context "$CLUSTER" \
  apply-config --file "talos/$CLUSTER/generated/controlplane.yaml"
```

To add a cluster, create a directory under `talos/` with its own `cluster.env`, schematic
and patches. Add its Helm manifest and environment file under `kubernetes/`. The generator
supports one control-plane node per cluster, and doesn't provision servers or bootstrap
the cluster.

Generating machine configuration doesn't restore data. Recovering a lost server also needs
a new server and backups of Kubernetes state and application data. Talos and Kubernetes
upgrades are separate operations too.

## Customize services

To add an application:

1. Create its Helm values under `kubernetes/<service>/`.
2. Add a release to `kubernetes/helmsman.<cluster>.yml`.
3. Review and apply it with `run.py`, using `-n <release-name>` to select the release.

Application and provider configuration goes in the values files. Use small Helmsman
overrides for settings that differ per cluster, such as storage classes and volume access
modes. Network definitions and hardware configuration stay with the service that uses them.

Application settings live in `config/`. After changing them, redeploy the application if
it needs it.

## Development VM

[`ansible/README.md`](ansible/README.md) covers the playbook that sets up an Ubuntu VM on
Proxmox with T3 and Docker.

## Lint

GitHub Actions runs these checks on every pull request and on pushes to `main`. `uv sync`
installs the same versions, so you can run them from the repository root:

```bash
uv run yamllint --strict .
uv run ansible-lint ansible
uv run ruff check .
uv run ruff format --check .
git ls-files -z '*.sh' | xargs -0 uv run shellcheck
uv run actionlint
```
