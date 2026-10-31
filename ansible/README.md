# T3 Code development VM

`t3code.yml` turns an existing Ubuntu 24.04 VM on Proxmox into a persistent,
single-user development machine. T3 and its agents run directly in the VM, and
Docker Engine with Compose and Buildx is available for project services.

The playbook applies three roles in order:

- `base`: upgrades APT packages, installs common tools (Git, ripgrep, jq, tmux),
  and configures locales, fail2ban, and SSH hardening. It also changes your
  administrator account's primary group to `users` and starts the QEMU guest
  agent when Proxmox provides its channel. Saturn uses this role too, with
  swap disabled for Kubernetes. This playbook sets `base_disable_swap: false`
  so builds can use swap.
- `docker`: installs Docker from the official repository. It refuses to run if
  Ubuntu's Docker, containerd, or runc packages, or `podman-docker`, are
  already installed.
- `t3code`: creates the `t3code` user and its workspace, installs mise and the
  language tools, installs T3, and runs it as `t3code.service`.

Kubernetes provisioning stays in the separate `saturn.yml` playbook.

## Prepare the VM

Create the VM in Proxmox. 4 vCPU, 16 GiB RAM, and a 100 GiB SSD-backed disk are a
reasonable start. Install Ubuntu Server 24.04 (amd64 or arm64), enable the QEMU
guest agent in the VM options, and give it a stable address.

During installation, create an administrator account with your SSH public key
and sudo access. Start from a fresh VM: the Docker role stops on existing
container runtimes.

## Network access

The playbook does not enable a host firewall: UFW stays off unless you set
`base_enable_ufw: true`, which also opens ports 80 and 443. Filter traffic with
the Proxmox firewall instead. Allow SSH from your workstation or LAN and block
everything else.

T3 listens on `127.0.0.1:3773` and is reached through T3 Connect or an SSH tunnel.
Ports published by project containers listen on all interfaces by default, so
either bind them to `127.0.0.1` in Compose or cover them in the Proxmox firewall.

## Configure and apply

From the repository root:

```bash
uv sync
cp ansible/hosts.ini.example ansible/hosts.ini
```

Edit `ansible/hosts.ini` (ignored by Git) and set the VM address and your
administrator username in the `t3code` group:

```ini
[t3code]
192.0.2.20 ansible_user=igalarzab
```

Connect once over SSH to verify and accept the host key, then apply:

```bash
ssh igalarzab@192.0.2.20
uv run ansible-playbook -i ansible/hosts.ini ansible/t3code.yml
```

Add `--ask-become-pass` if sudo needs a password. Run from the repository root:
`ansible/ansible.cfg` disables host-key checking and is only meant for the legacy
`run.sh`. The first run downloads the tools and T3 and takes a few minutes. It
ends by waiting up to three minutes for T3 to answer HTTP requests.

### Variables

Override these in the inventory or with `--extra-vars`:

| Variable | Default | Purpose |
| --- | --- | --- |
| `t3code_user` | `t3code` | Development account |
| `t3code_home` | `/home/{{ t3code_user }}` | Its home directory |
| `t3code_workspace` | `{{ t3code_home }}/workspace` | Directory for repositories |
| `t3code_data_dir` | `{{ t3code_home }}/.local/share/t3` | T3 state, exported as `T3CODE_HOME` |
| `t3code_channel` | `stable` | `stable` or `nightly`, used for the first install only |
| `t3code_port` | `3773` | Loopback port for `t3 serve` |
| `t3code_tools` | Latest Node LTS, pnpm, Python, and uv | mise tools to bootstrap |
| `t3code_browser_setup` | `false` | Rerun T3's browser setup on an existing install |

Each `t3code_tools` entry has a mise `tool` request, such as `node@lts`, and the
`command` its shim provides, such as `node`. A tool is skipped once its shim
exists, so later version changes made with mise are kept. Use `[]` to skip the
bootstrap.

Choose the user, home, workspace, and data directory before the first run. The
playbook does not move existing data when they change.

Reapplying keeps your tools, credentials, and T3 state, but it is not a no-op.
The base role upgrades every APT package, including Docker, and changes to the
service file restart T3. Both interrupt running work, so apply when the VM is
idle.

## Connect T3

Switch to the development account and link it to T3 Connect:

```bash
sudo -iu t3code
t3 connect link --headless
```

Open the printed URL on your laptop and approve the code. Then leave the
development shell and restart the service:

```bash
exit
sudo systemctl restart t3code
```

Sign in to the same T3 Connect account on your client and select this
environment. Do not run `t3 service install`. Ansible owns the service, and a
second one would fight over the same T3 home and port.

To connect without T3 Connect, open a tunnel from your Mac:

```bash
ssh -N -L 3773:127.0.0.1:3773 igalarzab@192.0.2.20
```

In another SSH session, run `sudo -iu t3code` and `t3 pair`, then paste the
pairing URL into the desktop app. Pairing URLs and service logs can contain
access tokens, so treat them as secrets.

Inside T3, use **Connect with ChatGPT** in the provider settings for Codex, and
set provider permissions there. Authenticate GitHub from a T3 terminal:

```bash
gh auth login --hostname github.com --git-protocol https --web
gh auth setup-git
git clone https://github.com/igalarzab/homelab.git ~/workspace/homelab
```

Set your Git name and email, then add each checkout as a project. Credentials
live under `/home/t3code`, never in the inventory.

## Development environment

mise is installed from its APT repository through `extrepo`. Language tools are
installed in the development user's home. Login shells get the mise shims,
interactive shells run `mise activate bash`, and `npm install -g` writes to
`~/.local`. T3 keeps its state in `~/.local/share/t3` instead of `~/.t3`: login
shells and the service both set `T3CODE_HOME`. The service sets its own `PATH`,
which includes the mise shims.
Ubuntu's `python3` stays in place for Ansible. `gh` comes from GitHub's APT
repository, so it stays current with OS upgrades.

T3 runs with `UMask=0077`, and the home and workspace are `0700`. Files created
by agents can only be read by `t3code`. Containers that run as a different
non-root user cannot read bind-mounted project files. Run them as `t3code`'s UID
or relax permissions for that project.

The `t3code` user is in the `docker` group, which gives it root access inside
the VM. Treat the whole VM as the agent's sandbox. Its network access and stored
credentials decide what else it can reach.

## Browser previews

The playbook runs `t3 browser setup` as root until it succeeds once, then
records that in `/var/lib/t3code-browser-setup.done`. The command installs the
Chrome sandbox AppArmor profile, missing libraries, and fonts, and leaves the
sandbox enabled. Afterwards the playbook gives any root-owned files in the T3
data directory back to `t3code`.

T3 downloads Chrome when the first browser tab opens, so some missing libraries
can only be detected after that. If the first preview reports missing libraries,
run the setup again:

```bash
uv run ansible-playbook -i ansible/hosts.ini ansible/t3code.yml -e t3code_browser_setup=true
```

Restart `t3code` afterwards if it installed fonts.

## Updates

The service runs `t3 serve` from the installed launcher. Restarts never update
T3, and the playbook reinstalls it only when `t3 --version` fails, for example
after an interrupted install. To update it, finish active work, then run the
official installer as the development user:

```bash
sudo systemctl stop t3code
sudo -iu t3code
curl -fsSL https://t3.codes/install.sh -o ~/.cache/t3-install.sh
T3CODE_CHANNEL=stable T3CODE_INSTALL_BIN_DIR="$HOME/.local/bin" sh ~/.cache/t3-install.sh
rm ~/.cache/t3-install.sh
exit
sudo systemctl start t3code
sudo journalctl -u t3code -n 50
```

Other components:

- Codex: update it from T3's provider settings.
- Language tools: run `mise upgrade` as `t3code` while builds are idle.
  Projects can pin their own versions in their mise config.
- mise, Docker, and OS packages: updated through APT, either by hand or by
  reapplying the playbook. A Docker upgrade restarts the daemon, which stops
  containers that have no restart policy.

## Backups and recovery

Back up the VM through Proxmox, including `/home/t3code` and `/var/lib/docker`.
The guest agent lets Proxmox freeze the filesystem during snapshots. For a
consistent copy, stop T3 and project databases first, or use their own backup
tools. Backups contain credentials, so protect them accordingly.

Restoring an older T3 version does not undo its database migrations. Restore
the T3 state from the same backup.

Reboots and restarts stop running processes. Files and T3 history survive, but
background commands need to be started again. Test a restore before relying on
the VM for unpushed work.

## References

- [T3 installation](https://github.com/pingdotgg/t3code/blob/main/docs/user/install.md)
- [T3 remote access and browser setup](https://github.com/pingdotgg/t3code/blob/main/docs/user/remote-access.md)
- [Docker Engine on Ubuntu](https://docs.docker.com/engine/install/ubuntu/)
- [mise installation](https://mise.jdx.dev/installing-mise.html)
