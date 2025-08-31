# 🏠 Homelab

A comprehensive Kubernetes-based homelab setup that provides infrastructure automation, home
automation, and media services through containerized applications.

## 🚀 Overview

This homelab combines Kubernetes orchestration with home automation capabilities, featuring:

- **Infrastructure**: Kubernetes cluster with storage, networking, and security components
- **Home Automation**: Home Assistant ecosystem with ESPHome, Node-RED, and Zigbee2MQTT
- **Media Services**: Plex media server and JDownloader
- **Monitoring & Management**: Automated deployments, certificate management, and DNS

## 🏗️ Architecture

The setup consists of three main components:

### 1. 📦 Kubernetes Infrastructure
- **Container Runtime**: containerd with custom configuration
- **Storage**: Proxmox CSI driver for persistent volumes
- **Networking**: Multus CNI, Traefik ingress controller
- **Security**: cert-manager for TLS certificates, PocketID for authentication
- **Monitoring**: Metrics server, Keel for automated updates

### 2. 🏡 Home Automation Stack
- **Home Assistant**: Central home automation hub
- **ESPHome**: Custom firmware for ESP-based devices (AC controllers)
- **Node-RED**: Visual flow-based automation
- **Zigbee2MQTT**: Zigbee device integration
- **Mosquitto**: MQTT broker for IoT communication

### 3. 🎬 Media & Downloads
- **Plex**: Media streaming server
- **JDownloader**: Automated download management

## 📁 Project Structure

```
homelab/
├── ansible/                   # Server provisioning and K8s setup
│   ├── roles/
│   │   ├── base/              # Base system configuration
│   │   ├── containerd/        # Container runtime setup
│   │   └── kubeadm/           # Kubernetes cluster initialization
│   └── server.yml             # Main playbook
├── config/                    # Application configurations
│   ├── esphome/               # ESP device configs for AC control
│   ├── home-assistant/        # HA configuration and automations
│   ├── mosquitto/             # MQTT broker settings
│   ├── node-red/              # Node-RED flows and settings
│   └── zigbee2mqtt/           # Zigbee device mappings
└── kubernetes/                # Kubernetes manifests and Helm values
    ├── helmsman.yml           # Helm chart orchestration
    ├── run.py                 # Deployment automation script
    └── */values.yml           # Individual service configurations
```

## 🛠️ Prerequisites

- Python 3.13+
- Kubernetes cluster access
- Ansible for server provisioning
- Helm 3.x
- Helmsman for chart management

## 🚀 Quick Start

### 1. 📋 Setup Dependencies

```bash
# Install Python dependencies
uv sync
```

### 2. ⚙️ Configure Ansible Variables

```bash
cp ansible/vars.yaml.example ansible/vars.yaml
cp ansible/hosts.ini.example ansible/hosts.ini

# Edit vars.yaml with your specific configuration
vim ansible/vars.yaml
```

### 3. 🔧 Provision Servers

```bash
cd ansible
./run.sh
```

### 4. 🎯 Deploy Applications

```bash
cd kubernetes

# Dry run to check configuration
python run.py dry-run

# Apply all applications
python run.py apply

# Deploy specific application
python run.py apply -n home-assistant

# Check for outdated charts
python run.py outdated
```

## 🔧 Configuration

### 🏠 Home Assistant Setup

The Home Assistant configuration includes:

- **Dashboards**: Floor plan, main dashboard, and Lovelace UI
- **Automations**: Theme switching, pre-cooling schedules
- **Devices**: Input controls, sensors, media players, timers
- **Integrations**: ESPHome AC controllers, Zigbee devices, Spotify

### 🌡️ ESPHome Devices

Pre-configured templates for Mitsubishi AC units in:
- Bedroom
- Living room (left and right units)
- Office

### 📊 Monitoring & Updates

- **Keel**: Automated container image updates
- **External DNS**: Automatic DNS record management with Cloudflare
- **Metrics Server**: Resource monitoring for Kubernetes

## 📚 Usage Examples

### 🎯 Application Management

```bash
# Deploy only Home Assistant stack
python run.py apply -n home-assistant
python run.py apply -n zigbee2mqtt
python run.py apply -n node-red
python run.py apply -n esphome

# Update a specific service
python run.py apply -n plex

# Remove an application
python run.py destroy -n jdownloader
```

### 🏠 Home Assistant Features

- **Climate Control**: Automated AC management through ESPHome
- **Lighting**: Zigbee-based smart lighting with automation
- **Media**: Spotify integration with multi-room audio
- **Monitoring**: System sensors and device status tracking

## 🔧 Customization

### 🎨 Adding New Services

1. Create Helm values file in `kubernetes/{service}/values.yml`
2. Add entry to `kubernetes/helmsman.yml`
3. Deploy using `python run.py apply -n {service}`

### 🏡 Home Assistant Extensions

1. Add configuration files to `config/home-assistant/`
2. Update container volumes in `kubernetes/home-assistant/home-assistant.values.yml`
3. Redeploy Home Assistant

### 📱 ESPHome Devices

1. Create device config in `config/esphome/{device}.yaml`
2. Use existing templates from `config/esphome/templates/`
3. Deploy through ESPHome dashboard

## 🛡️ Security

- **TLS Certificates**: Automated Let's Encrypt certificates via cert-manager
- **Authentication**: PocketID for SSO across services
- **Network Policies**: Isolated namespaces for different service stacks
- **Secret Management**: Kubernetes secrets for sensitive configuration

## 📈 Monitoring

The homelab includes comprehensive monitoring through:

- **Kubernetes Metrics**: Resource usage and cluster health
- **Application Health**: Service availability and performance
- **Home Automation**: Device status and automation execution
- **Infrastructure**: Network, storage, and compute metrics

## 🤝 Contributing

This is a personal homelab configuration, but feel free to:

1. Fork the repository for your own homelab setup
2. Adapt configurations to your specific needs
3. Share improvements and optimizations

## 📄 License

This project is for personal use. Feel free to adapt and modify for your own homelab needs.
