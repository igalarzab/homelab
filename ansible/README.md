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
  language tools, Codex CLI, Claude Code, and T3, and installs T3's native
  systemd user service.
  Lingering keeps it running after logout and starts it at boot.

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
the Proxmox firewall instead. Allow SSH and TCP port 3773 from your workstation
or LAN and block everything else.

T3 listens on `t3code_host:3773`, with `t3code_host` defaulting to the VM's
primary IPv4 address detected by Ansible. This assumes the default route uses
the LAN interface. Override it with the LAN address if another interface owns
the default route. You can also use T3 Connect or an SSH tunnel.
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
192.0.2.20 ansible_user=igalarzab ansible_become_exe=sudo.ws
```

Ubuntu 25.10 and later use sudo-rs, whose password prompt Ansible does not
recognize. `ansible_become_exe=sudo.ws` switches to the original sudo, which is
still installed. Leave it out on 24.04.

Connect once over SSH to verify and accept the host key, then apply:

```bash
ssh igalarzab@192.0.2.20
./ansible/run.sh t3code
```

Arguments after the playbook name go to `ansible-playbook`, so add
`--ask-become-pass` if sudo needs a password. `ansible/ansible.cfg` disables
host-key checking for Saturn, but `run.sh` turns it back on for this playbook.
The first run downloads the tools and T3 and takes a few minutes. It
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
| `t3code_host` | Primary IPv4 address detected by Ansible | LAN address for `t3 serve` |
| `t3code_port` | `3773` | Listening port for `t3 serve` |
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
service environment restart T3. Both interrupt running work, so apply when the
VM is idle.

## Migrate the previous system service

Remove the previous system service manually before applying the updated
playbook. Run these commands as your administrator account on the VM while T3
is idle:

```bash
sudo systemctl disable --now t3code.service
sudo rm /etc/systemd/system/t3code.service
sudo systemctl daemon-reload
```

Remove only this system unit. Keep `/home/t3code/.local/share/t3`, which contains
T3 state and credentials. Do not run `t3 uninstall`.
The native service uses the same data directory and LAN address.

Then apply the updated playbook from your workstation:

```bash
./ansible/run.sh t3code
```

## Connect T3

Switch to the development account. When using `sudo -iu`, explicitly select its
user service bus because sudo does not create a full login session:

```bash
sudo -iu t3code
export XDG_RUNTIME_DIR="/run/user/$(id -u)"
export DBUS_SESSION_BUS_ADDRESS="unix:path=$XDG_RUNTIME_DIR/bus"
t3 status
t3 pair
```

Paste the printed pairing URL into **Settings > Environments > Add environment**
in the desktop app. The playbook configures the native service's LAN address
and port in `$T3CODE_HOME/service.env`. Pairing URLs contain access tokens, so
treat them as secrets.

For T3 Connect, run `t3 up --connect` as `t3code`, open the printed URL on your
laptop, and approve the code. Sign in to the same T3 Connect account on your
client and select this environment.

An SSH tunnel is another option when your Mac cannot reach port 3773 directly:

```bash
ssh -N -L 3773:192.0.2.20:3773 igalarzab@192.0.2.20
```

The playbook installs Codex CLI and Claude Code in `~/.local/bin` using their
native installers. It skips working installations and reinstalls missing or
broken binaries. It does not sign in or manage provider credentials.

As `t3code`, sign in to each CLI and follow its browser instructions:

```bash
codex login --device-auth
claude auth login
```

Alternatively, use **Connect with ChatGPT** in T3's provider settings for Codex.
Enable the providers and set their permissions there. Authenticate GitHub from
a T3 terminal:

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
`~/.local`. T3 keeps its state in `~/.local/share/t3` instead of `~/.t3`.
Login shells, interactive shells, and the native service set `T3CODE_HOME`.
Interactive shells also add `~/.local/bin` to `PATH`. The native service captures
the installation task's `PATH`, which includes the mise shims.
Ubuntu's `python3` stays in place for Ansible. `gh` comes from GitHub's APT
repository, so it stays current with OS upgrades.

The home and workspace are `0755`; the T3 data directory is private. The native
service uses the user manager's default umask. Containers must have permission
to read bind-mounted project files; run them as `t3code`'s UID when needed.

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
./ansible/run.sh t3code -e t3code_browser_setup=true
```

Run `t3 service restart` as `t3code` afterwards if it installed fonts.

## Updates

The playbook installs T3 only when `t3 --version` fails, for example after an
interrupted install. Use T3's native update and service commands for maintenance.
After finishing active work, run as the development user:

```bash
sudo -iu t3code
export XDG_RUNTIME_DIR="/run/user/$(id -u)"
export DBUS_SESSION_BUS_ADDRESS="unix:path=$XDG_RUNTIME_DIR/bus"
t3 update
t3 service status
```

Use `t3 service restart` to restart without updating. `t3 service status` prints
the service log location. Edit the Ansible-managed values in the inventory,
and keep any additional environment variables outside the managed block in
`$T3CODE_HOME/service.env`.

Other components:

- Codex and Claude Code: update them from T3's provider settings. Reapplying
  Ansible keeps working versions.
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
- [T3 native background service](https://github.com/pingdotgg/t3code/blob/main/docs/user/background-service.md)
- [T3 remote access and browser setup](https://github.com/pingdotgg/t3code/blob/main/docs/user/remote-access.md)
- [Docker Engine on Ubuntu](https://docs.docker.com/engine/install/ubuntu/)
- [mise installation](https://mise.jdx.dev/installing-mise.html)
