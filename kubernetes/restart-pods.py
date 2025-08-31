#!/usr/bin/env python3

import json
import subprocess
from typing import Any, Sequence


def run_kubectl(cmd: Sequence[str]) -> dict[str, Any]:
    cmd = list(cmd) + ["-o", "json"]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise ValueError(f"Command {' '.join(cmd)} failed with error: {result.stderr}")

    return json.loads(result.stdout)


def get_all_namespaces() -> list[str]:
    ns_data = run_kubectl("kubectl get namespaces".split())
    return [ns["metadata"]["name"] for ns in ns_data.get("items", [])]


def get_workloads_with_restarted_pods(namespace: str) -> set[str]:
    pods_data = run_kubectl(f"kubectl get pods -n {namespace}".split())

    if not pods_data:
        return set()

    restarted_workloads: set[str] = set()

    for pod in pods_data.get("items", []):
        restart_count = 0

        for container_status in pod.get("status", {}).get("containerStatuses", []):
            restart_count += container_status.get("restartCount", 0)

        if restart_count > 0:
            owner_refs = pod.get("metadata", {}).get("ownerReferences", [])

            for owner in owner_refs:
                owner_kind: str = owner.get("kind", "").lower()
                owner_name: str = owner.get("name", "")

                if owner_kind == "replicaset":
                    rs_data = run_kubectl(
                        f"kubectl get replicaset {owner_name} -n {namespace}".split()
                    )

                    if rs_data:
                        rs_owners = rs_data.get("metadata", {}).get("ownerReferences", [])

                        for rs_owner in rs_owners:
                            if rs_owner.get("kind", "").lower() == "deployment":
                                restarted_workloads.add(f"deployment/{rs_owner.get('name', '')}")
                elif owner_kind in ["deployment", "statefulset", "daemonset"]:
                    restarted_workloads.add(f"{owner_kind}/{owner_name}")

    return restarted_workloads


def restart_workload(workload: str, namespace: str) -> None:
    print(f"Restarting {workload} in namespace {namespace}")
    run_kubectl(f"kubectl rollout restart {workload} -n {namespace}".split())


def main() -> None:
    namespaces: list[str] = get_all_namespaces()

    for namespace in namespaces:
        workloads: set[str] = get_workloads_with_restarted_pods(namespace)

        for workload in workloads:
            restart_workload(workload, namespace)


if __name__ == "__main__":
    main()
