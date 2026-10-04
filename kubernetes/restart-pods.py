#!/usr/bin/env python3

import argparse
import json
import shlex
import subprocess
import sys
from collections.abc import Sequence
from typing import Any


def run_kubectl(cluster: str, args: Sequence[str]) -> dict[str, Any]:
    cmd = ["kubectl", "--context", cluster, *args, "-o", "json"]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except OSError as exc:
        raise SystemExit(f"Unable to run kubectl: {exc}") from exc

    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "No error details returned"
        print(f"Command {shlex.join(cmd)} failed: {detail}", file=sys.stderr)
        raise SystemExit(result.returncode)

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Command {shlex.join(cmd)} returned invalid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise SystemExit(f"Command {shlex.join(cmd)} did not return a JSON object")

    return data


def get_all_namespaces(cluster: str) -> list[str]:
    ns_data = run_kubectl(cluster, ["get", "namespaces"])
    return [ns["metadata"]["name"] for ns in ns_data.get("items", [])]


def get_workloads_with_restarted_pods(cluster: str, namespace: str) -> set[str]:
    pods_data = run_kubectl(cluster, ["get", "pods", "-n", namespace])

    restarted_workloads: set[str] = set()

    for pod in pods_data.get("items", []):
        container_statuses = pod.get("status", {}).get("containerStatuses", [])
        if not any(status.get("restartCount", 0) > 0 for status in container_statuses):
            continue

        for owner in pod.get("metadata", {}).get("ownerReferences", []):
            owner_kind: str = owner.get("kind", "").lower()
            owner_name: str = owner.get("name", "")
            if not owner_name:
                continue

            if owner_kind == "replicaset":
                rs_data = run_kubectl(
                    cluster, ["get", "replicaset", owner_name, "-n", namespace]
                )
                for rs_owner in rs_data.get("metadata", {}).get("ownerReferences", []):
                    if rs_owner.get("kind", "").lower() == "deployment" and rs_owner.get("name"):
                        restarted_workloads.add(f"deployment/{rs_owner['name']}")
            elif owner_kind in {"deployment", "statefulset", "daemonset"}:
                restarted_workloads.add(f"{owner_kind}/{owner_name}")

    return restarted_workloads


def restart_workload(cluster: str, workload: str, namespace: str) -> None:
    print(f"Restarting {workload} in namespace {namespace}", flush=True)
    run_kubectl(cluster, ["rollout", "restart", workload, "-n", namespace])


def main() -> None:
    parser = argparse.ArgumentParser(description="Restart workloads with restarted pods cluster-wide")
    parser.add_argument("cluster", help="The Kubernetes context to use")
    args = parser.parse_args()

    print(f"Scanning cluster {args.cluster}", flush=True)
    namespaces: list[str] = get_all_namespaces(args.cluster)
    restart_count = 0

    for namespace in sorted(namespaces):
        workloads: set[str] = get_workloads_with_restarted_pods(args.cluster, namespace)

        for workload in sorted(workloads):
            restart_workload(args.cluster, workload, namespace)
            restart_count += 1

    print(f"Submitted restarts for {restart_count} workload(s) across {len(namespaces)} namespace(s).")


if __name__ == "__main__":
    main()
