#!/bin/bash

helmsman \
  --apply \
  --subst-env-values \
  -f helmsman.yml
