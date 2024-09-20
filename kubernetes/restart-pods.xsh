#!/usr/bin/env xonsh

apps = [
    'authentik',
    'cert-manager',
    'home-assistant',
    'jdownloader',
    'keel',
    'kube-system',
    'mosquitto',
    'plex',
    'traefik',
    'transmission',
]

for app in apps:
    kubectl -n @(app) rollout restart daemonsets,deployments,statefulset
