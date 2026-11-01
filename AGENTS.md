# AGENTS

Home infrastructure. Talos runs the Kubernetes nodes, Helmsman deploys the cluster
applications and Ansible configures the machines. See `README.md` for the layout and
`ansible/README.md` for the development VM.

## Commands

CI runs these on every pull request. Run them from the repository root after `uv sync`.

```bash
uv run yamllint --strict .
uv run ansible-lint ansible
uv run ruff check .
uv run ruff format --check .
git ls-files -z '*.sh' | xargs -0 uv run shellcheck
uv run actionlint
```

To preview a cluster deployment, run `uv run python run.py <cluster> dry-run` from
`kubernetes/`.

## Rules

- These commands change live systems, so only run them when asked: `run.py <cluster> apply`,
  `restart-pods.py`, `talosctl apply-config` and `ansible/run.sh`.
- Applying `t3code.yml` upgrades every APT package and can restart T3, which ends any agent
  session running on that VM.
- Never print or commit `ansible/hosts.ini`, `ansible/vars.yaml`, `kubernetes/.env.*`,
  `talos/*/secrets.yaml` or `talos/*/generated/`. They hold credentials or live addresses.
- Shared application settings go in `kubernetes/.env`, which is tracked. Secrets and
  per-cluster overrides go in `kubernetes/.env.<cluster>`.
- The `t3code` role sets up the machine and T3. Shell config, language runtimes and personal
  tools don't belong in it, and neither do references to the repository that manages them.
