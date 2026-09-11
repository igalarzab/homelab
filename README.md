# Homelab

Kubernetes infrastructure, home automation, and media services, with Talos managing
the operating system and Kubernetes components. Helmsman manages the applications.

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

Each cluster has its own Talos inputs, credentials, and Helm release manifest.
Storage drivers and applications are selected in that cluster's manifest. Servers
and VMs are provisioned outside this repository.

## Project structure

```text
homelab/
  talos/
    generate.sh                   # Generate and validate machine configuration
    <cluster>/
      cluster.env                 # Endpoints, disk, image, and pinned versions
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
  ansible/                        # Legacy Ubuntu and kubeadm provisioning
```

## Prerequisites

- Python and `uv`
- `talosctl`, `kubectl`, Helm, and Helmsman

## Set up a new workstation

These steps restore access to an existing cluster after cloning the repository.
Run commands from the repository root. Replace `your-cluster-name` with a directory
name under `talos/` and use the same shell for the following commands:

```bash
CLUSTER=your-cluster-name
uv sync
```

### Restore credentials and generate configuration

Restore the original cluster secrets from your secure backup:

```bash
install -m 600 /path/to/backup/secrets.yaml "talos/$CLUSTER/secrets.yaml"
./talos/generate.sh "$CLUSTER"
```

The script recreates `talos/<cluster>/generated/controlplane.yaml` and
`talos/<cluster>/generated/talosconfig`, configures the local Talos client, and
validates the machine configuration. Generation only writes local files.

### Restore Kubernetes access

Fetch the admin kubeconfig from the running cluster and name its context to match
the deployment configuration:

```bash
talosctl --talosconfig "talos/$CLUSTER/generated/talosconfig" \
  --context "$CLUSTER" kubeconfig --force-context-name "$CLUSTER"

kubectl --context "$CLUSTER" get nodes
```

This merges the context into `~/.kube/config`. There is no need to apply machine
configuration or bootstrap an existing cluster when setting up a workstation.

### Restore application settings

Restore the cluster's environment file, which contains application credentials and
overrides for the shared settings in `kubernetes/.env`:

```bash
install -m 600 /path/to/backup/cluster.env "kubernetes/.env.$CLUSTER"
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

## Change Talos configuration

Edit the selected cluster's inputs or patches, regenerate the configuration, and
review the diff before applying it. The [Talos guide](talos/README.md) describes the
commands and how to add another cluster.

Talos and Kubernetes upgrades are separate lifecycle operations. Recovering a lost
server also requires infrastructure provisioning and backups of Kubernetes state
and application data; generating machine configuration does not restore that data.

## Customize services

To add an application:

1. Create its Helm values under `kubernetes/<service>/`.
2. Add a release to `kubernetes/helmsman.<cluster>.yml`.
3. Review and apply it with `run.py`, using `-n <release-name>` to select the release.

Application settings live in `config/`. Home Assistant includes dashboards,
automations, scripts, and device definitions. ESPHome includes Mitsubishi AC
controller configurations and shared templates. Update the relevant configuration
and redeploy the application when needed.
