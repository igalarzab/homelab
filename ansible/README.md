# T3 Code development VM

`t3code.yml` turns an Ubuntu 24.04 or later VM on Proxmox into a single-user development
machine. T3 and its agents run directly in the VM, with Docker Engine, Compose and Buildx
for project services. `saturn.yml` is the separate kubeadm playbook.

The playbook applies three roles in order:

- `base` upgrades APT packages, installs common tools such as Git, ripgrep, jq and tmux,
  and configures locales, fail2ban and SSH. SSH logins then need a key, and root can't log
  in. It changes your account's primary group to `users` and starts the QEMU guest agent
  when Proxmox provides its channel. Saturn uses this role too. This playbook sets
  `base_disable_swap: false` so builds can use swap.
- `docker` installs Docker from its official repository. It stops if Ubuntu's Docker,
  containerd or runc packages, or `podman-docker`, are already installed.
- `t3code` creates the workspace, installs Codex CLI, Claude Code and T3, and installs T3's
  systemd user service. Lingering keeps the service running after logout and starts it at
  boot. Everything runs under your administrator account.

## Prepare the VM

Create the VM in Proxmox. 4 vCPU, 16 GiB RAM and a 100 GiB SSD-backed disk are a reasonable
start. Install Ubuntu Server, enable the QEMU guest agent in the VM options and give the VM
a stable address.

During installation, create an administrator account with your SSH public key and sudo
access. Start from a fresh VM, because the Docker role stops on existing container runtimes.

## Network access

The playbook doesn't enable a host firewall. UFW stays off unless you set
`base_enable_ufw: true`, which also opens ports 80 and 443. Use the Proxmox firewall
instead, and allow SSH and TCP port 3773 only from your workstation or LAN.

T3 listens on `t3code_host:3773`. `t3code_host` defaults to the VM's primary IPv4 address,
so set it yourself if the default route doesn't use the LAN interface. You can also reach T3
through T3 Connect or an SSH tunnel.

Ports published by project containers listen on all interfaces by default. Bind them to
`127.0.0.1` in Compose or cover them in the Proxmox firewall.

## Configure and apply

From the repository root:

```bash
uv sync
cp ansible/hosts.ini.example ansible/hosts.ini
```

Set the VM address and your administrator username in the `t3code` group of
`ansible/hosts.ini`, which Git ignores:

```ini
[t3code]
192.0.2.20 ansible_user=USERNAME ansible_become_exe=sudo.ws
```

Ubuntu 25.10 and later use sudo-rs, and Ansible doesn't recognize its password prompt.
`ansible_become_exe=sudo.ws` switches to the original sudo. Leave it out on 24.04.

Connect once over SSH to verify and accept the host key, then apply:

```bash
ssh USERNAME@192.0.2.20
./ansible/run.sh t3code
```

Arguments after the playbook name go to `ansible-playbook`, so add `--ask-become-pass` if
sudo needs a password. `ansible/ansible.cfg` disables host-key checking for Saturn, and
`run.sh` turns it back on for this playbook. The last task waits up to three minutes for T3
to answer HTTP requests.

Apply when the VM is idle. Every run upgrades all APT packages, including Docker, and a
change to the service environment restarts T3. Both interrupt running work. Your tools,
credentials and T3 state are kept.

### Variables

Override these in the inventory or with `--extra-vars`:

| Variable | Default | Purpose |
| --- | --- | --- |
| `t3code_user` | Ansible login account | Development account |
| `t3code_home` | `/home/{{ t3code_user }}` | Its home directory |
| `t3code_workspace` | `{{ t3code_home }}/workspace` | Directory for repositories |
| `t3code_data_dir` | `{{ t3code_home }}/.local/share/t3` | T3 state, exported as `T3CODE_HOME` |
| `t3code_channel` | `stable` | `stable` or `nightly`, used for the first install only |
| `t3code_host` | Primary IPv4 address | LAN address for `t3 serve` |
| `t3code_port` | `3773` | Listening port for `t3 serve` |
| `t3code_browser_setup` | `false` | Rerun T3's browser setup on an existing install |

Choose the user, home, workspace and data directory before the first run. The playbook
doesn't move existing data when they change.

## Connect T3

Log in over SSH as your administrator account, then pair:

```bash
t3 status
t3 pair
```

Paste the printed URL into **Settings > Environments > Add environment** in the desktop app.
Pairing URLs contain access tokens, so treat them as secrets.

For T3 Connect, run `t3 up --connect`, open the printed URL on your laptop and approve the
code. Then sign in to the same T3 Connect account on your client and select this environment.

If your laptop can't reach port 3773, use an SSH tunnel:

```bash
ssh -N -L 3773:192.0.2.20:3773 USERNAME@192.0.2.20
```

## Sign in to the tools

The playbook installs Codex CLI and Claude Code in `~/.local/bin`, and reinstalls them only
if they're missing or broken. It doesn't handle credentials, which stay in your home
directory. Sign in on the VM:

```bash
codex login --device-auth
claude auth login
gh auth login --hostname github.com --git-protocol https --web
gh auth setup-git
```

Enable the providers and set their permissions in T3's provider settings. Clone your
repositories into `~/workspace` and add each one as a project.

## Development environment

The playbook sets up the machine and T3. Your shell config, language runtimes and personal
tools are yours to install afterwards. Two things connect them to T3:

- T3 reads `PATH` for its agents by running `$SHELL -ilc`, so agents find whatever your login
  shell's startup files activate. The service gets `$SHELL` from the user service manager,
  which only reads your login shell when it starts. Reboot after changing it.
- The playbook manages one block in `~/.config/local.sh`, which exports `T3CODE_HOME`. Load
  that file from your shell so the `t3` command finds its data. Keep your own settings
  outside the block.

The account is in the `docker` group, which gives it root access inside the VM. Treat the
whole VM as the agent's sandbox. Its network access and stored credentials decide what else
it can reach.

The home and workspace are `0755`, and the T3 data directory is private. Containers need
permission to read bind-mounted project files, so run them as your account's UID when needed.

## Browser previews

The playbook runs `t3 browser setup` as root until it succeeds once, and records that in
`/var/lib/t3code-browser-setup.done`. This installs the Chrome sandbox AppArmor profile,
missing libraries and fonts, and leaves the sandbox on. The playbook then gives any root-owned
files in the T3 data directory back to your account.

T3 downloads Chrome when the first browser tab opens, so some missing libraries only show up
then. If the first preview reports any, run the setup again:

```bash
./ansible/run.sh t3code -e t3code_browser_setup=true
```

If it installed fonts, run `t3 service restart` on the VM afterwards.

## Updates

The playbook only installs T3 when `t3 --version` fails, so update it yourself once work has
finished:

```bash
t3 update
t3 service status
```

`t3 service restart` restarts without updating, and `t3 service status` prints the log
location. Set the managed values in the inventory, and keep any other environment variables
outside the managed block in `$T3CODE_HOME/service.env`.

Update Codex and Claude Code from T3's provider settings. Reapplying the playbook keeps
working versions.

APT updates Docker and the OS packages, either by hand or when you reapply the playbook. A
Docker upgrade restarts the daemon, which stops containers that have no restart policy.

## Backups and recovery

Back up the VM through Proxmox, including your home directory and `/var/lib/docker`. The
guest agent lets Proxmox freeze the filesystem during snapshots. For a consistent copy, stop
T3 and project databases first, or use their own backup tools. Backups contain credentials,
so protect them.

Restoring an older T3 version doesn't undo its database migrations, so restore the T3 state
from the same backup.

Reboots stop running processes. Files and T3 history survive, but background commands need
starting again. Test a restore before relying on the VM for unpushed work.

## References

- [T3 installation](https://github.com/pingdotgg/t3code/blob/main/docs/user/install.md)
- [T3 background service](https://github.com/pingdotgg/t3code/blob/main/docs/user/background-service.md)
- [T3 remote access and browser setup](https://github.com/pingdotgg/t3code/blob/main/docs/user/remote-access.md)
- [Docker Engine on Ubuntu](https://docs.docker.com/engine/install/ubuntu/)
