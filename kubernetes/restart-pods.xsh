#!/usr/bin/env xonsh

apps = [
    'cert-manager',
    'home-assistant',
    'jdownloader',
    'keel',
    'kube-system',
    'mosquitto',
    'plex',
    'pocket-id',
    'traefik',
    'transmission',
]

for app in apps:
    kubectl -n @(app) rollout restart daemonsets,deployments,statefulset
