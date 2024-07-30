#!/usr/bin/env python

import configparser
import kubernetes
import os
import sys

from os import path
from string import Template

CONFIG_FILE_NAME = 'config.ini'

def list_apps() -> list[str]:
  "List all the possible apps that can be installed in k8s"
  apps = [a for a in os.listdir('.') if path.isdir(a)]
  return apps


def list_manifests(app: str) -> list[str]:
  "List all the manifests from an existing app in the order they should be applied"
  manis = [m for m in os.listdir(app) if path.isfile(path.join(app, m)) and m.endswith('.yml')]
  return sorted(manis) # Sort alfaphetically


def render_app(app: str) -> str:
  "Render all the manifests of an app"
  app_config = parse_config(app)
  output = ''

  for manifest in list_manifests(app):
    rendered = render_manifest(app, manifest, app_config)
    output += f'### Render of {app}/{manifest}\n{rendered}\n\n'

  return output


def render_manifest(app: str, manifest: str, app_config: dict) -> str:
  "Render a single manifest, interpolating all its variables"
  with open(path.join(app, manifest), 'r') as f:
    template = Template(f.read())

  manifest_config = {}

  # All IMGTAG_* vars are docker tags that should be checked in the k8s cluster lively
  img_tags = [v for v in template.get_identifiers() if v.startswith('IMGTAG_')]
  for img_tag in img_tags:
    manifest_config[img_tag] = get_image_tag(img_tag)

  try:
    return template.substitute(**app_config, **manifest_config)
  except Exception as e:
    print(f'Error rendering {app}, {manifest}')
    raise e

def parse_config(app: str) -> dict:
  "Load from an INI file the config vars that will be interpolated in the manifests"
  config = configparser.RawConfigParser(interpolation=configparser.ExtendedInterpolation())
  config.optionxform = lambda option: option # type: ignore - We don't want to lowercase keys
  config.read(CONFIG_FILE_NAME)

  # The common config for all the apps is in the "default" section
  cfg = dict(config['default'].items())

  # Load the config for the specific app if it also exists
  if config.has_section(app):
    cfg.update(dict(config.items(app)))

  return cfg


def get_image_tag(img_var: str) -> str:
  """
  Tries to get from the k8s cluster the tag of a specific image to inject it later in
  the manifest. If the image is not live yet, we ask it as input.

  For locating the right tag, the `img_var` variable, which is the parameter that it's inside
  of the manifest and will be interpolated, should have the following format:

  IMGVAR_{OBJECT_NAMESPACE}_{DEPLOY|STS}_{OBJECT_NAME}_{CONTAINER_NUMBER}

  In the object name is missing, it defaults to the name of the namespace; if the container
  number is missing it defaults to 0.

  As k8s elements can have "-" in their names, but that's an invalid character in template
  variables, we first replace all "__" for "-" as a way of allowing the character
  """
  parts = img_var.replace("__", "-").split('_')

  try:
    _ = parts.pop(0)
    namespace = parts.pop(0).lower()
    obj_type = parts.pop(0).lower()
    obj_name = parts.pop(0).lower() if len(parts) else namespace
    container_no = int(parts.pop(0)) if len(parts) else 0
  except Exception as e:
    raise ValueError(f'Invalid var: {img_var}, check the docstring for more info', e)

  api = kubernetes.client.AppsV1Api() # type: ignore
  obj, tag = None, None

  try:
    if obj_type == 'deploy':
        obj = api.read_namespaced_deployment(namespace=namespace, name=obj_name)
    elif obj_type == 'sts':
        obj = api.read_namespaced_stateful_set(namespace=namespace, name=obj_name)
    else:
      raise ValueError(f'Invalid k8s object type: {obj_type}')
  except kubernetes.client.rest.ApiException as e: # type: ignore
    if e.status != 404:
      raise e

  if obj:
    image = obj.spec.template.spec.containers[int(container_no)].image
    tag = image.split(':')[1]

  if not tag:
    tag = input(f'Please, insert the value for {img_var}: ')

  return tag


if __name__ == '__main__':
  if len(sys.argv) != 2:
    print(f'Usage: {sys.argv[0]} [app_name|ALL]')
    sys.exit(1)

  app = sys.argv[1]

  # Load k8s config
  kubernetes.config.load_kube_config() # type: ignore

  if app == 'ALL':
    for app in list_apps():
      rendered_app = render_app(app)
      print(rendered_app)
  elif app in list_apps():
    rendered_app = render_app(app)
    print(rendered_app)
    sys.exit(0)
  else:
    print(f'Invalid app, "{app}" does not exist')
    sys.exit(2)
