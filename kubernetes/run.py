#!/usr/bin/env python

import argparse
import glob
import os
import pathlib
import re
import subprocess
from typing import Literal

from kubernetes import client as k8s_client
from kubernetes import config as k8s_config

SELF_PATH = pathlib.Path(__file__).parent.resolve()

#
# Helpers
#


def helmsman_run(cluster_name: str, *args, env=None):
    helmsman_file = SELF_PATH.joinpath(f"helmsman.{cluster_name}.yml")

    if not helmsman_file.exists():
        raise SystemExit(f"Error: Helmsman file not found: {helmsman_file}")

    base_cmd = ["helmsman", "--no-banner"]
    base_cmd += ["-f", helmsman_file]
    base_cmd += ["-e", SELF_PATH.joinpath(".env")]
    base_cmd += ["-e", SELF_PATH.joinpath(f".env.{cluster_name}")]

    if not env:
        env = os.environ.copy()

    subprocess.run(base_cmd + list(args), env=env)


def get_all_docker_tags() -> dict[str, str]:
    running_tags: dict[str, str] = {}

    for fpath in glob.glob(str(SELF_PATH.joinpath("**")), recursive=True):
        if os.path.isfile(fpath):
            with open(SELF_PATH.joinpath(fpath), "r") as f:
                env_names = re.findall(r"DOCKER_TAG__[\w_-]+", f.read())

            for env_name in env_names:
                try:
                    running_tags[env_name] = get_docker_tag(env_name)
                except Exception as e:
                    print(type(e).__name__, " - ", e)
                    running_tags[env_name] = input(
                        f"Error retrieving tag {env_name}, input manually: "
                    ).strip()

    return running_tags


def get_docker_tag(env_name: str) -> str:
    k8s_apps_api = k8s_client.AppsV1Api()

    try:
        ns, type, name, container_no = [
            v.lower().replace("_", "-") for v in env_name.split("__")[1:]
        ]
    except Exception:
        raise ValueError("Invalid format of tag: " + env_name)

    match type:
        case "deployment":
            deploy: k8s_client.V1Deployment = k8s_apps_api.read_namespaced_deployment(name, ns)
            image = deploy.spec.template.spec.containers[int(container_no)].image
        case "statefulset":
            sts: k8s_client.V1StatefulSet = k8s_apps_api.read_namespaced_stateful_set(name, ns)
            image = sts.spec.template.spec.containers[int(container_no)].image
        case _:
            raise ValueError("Unconfigured k8s type: " + type)

    try:
        tag = image.split(":")[1]
    except Exception:
        raise ValueError("No tag value in image: " + image)

    return tag


def configure_env() -> dict[str, str]:
    tags = get_all_docker_tags()

    my_env = os.environ.copy()
    my_env.update(tags)

    return my_env


#
# Commands
#


def run_charts(mode: Literal["dry-run", "apply"], cluster_name, *, app_name=None):
    try:
        k8s_config.load_kube_config(context=cluster_name)
    except k8s_config.ConfigException as e:
        raise SystemExit(f"Error: Kubernetes context '{cluster_name}' not found: {e}")

    my_env = configure_env()

    base_command = [f"--{mode}", "--subst-env-values", "--show-diff"]

    if app_name:
        base_command += ["--target", app_name]

    helmsman_run(cluster_name, *base_command, env=my_env)


def show_outdated_charts(cluster_name):
    helmsman_run(cluster_name, "--check-for-chart-updates")


#
# Entrypoint
#

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="Helmsman Runner")
    parser.add_argument("cluster", help="The Kubernetes cluster to use")

    commands = parser.add_subparsers(dest="command")

    apply = commands.add_parser("apply", help="Apply changes to the charts")
    apply.add_argument("-n", "--name", help="Filter an app by name")

    dry_run = commands.add_parser("dry-run", help="Dry Run changes to the charts")
    dry_run.add_argument("-n", "--name", help="Filter an app by name")

    destroy = commands.add_parser("destroy", help="Destroy the chart")
    destroy.add_argument("-n", "--name", help="Filter an app by name", required=True)

    outdated = commands.add_parser("outdated", help="Show outdated charts")

    args = parser.parse_args()

    match args.command:
        case "apply":
            run_charts("apply", cluster_name=args.cluster, app_name=args.name)
        case "dry-run":
            run_charts("dry-run", cluster_name=args.cluster, app_name=args.name)
        case "destroy":
            run_charts("destroy", cluster_name=args.cluster, app_name=args.name)
        case "outdated":
            show_outdated_charts(cluster_name=args.cluster)
        case _:
            parser.print_help()
