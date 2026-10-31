# T3 Code development VM

Configure an existing Ubuntu 24.04 VM on Proxmox as a persistent, single-user
development machine. T3 and its agents run directly in the VM. Docker Engine,
Compose, and Buildx are available for project services and builds.

The playbook creates a `t3code` user and `/home/t3code/workspace`, installs
development and browser dependencies, and starts `t3code.service` on boot. Node 24, pnpm 10,
Python 3, and uv are bootstrapped through mise in the development user's home.
Mise itself is installed through its APT repository using `extrepo`; language
runtimes remain user-owned. Interactive Bash uses `mise activate bash`; login
profiles use `mise activate bash --shims`. The service has its own explicit
`PATH`, independent of shell startup files. The
account uses `users` as its primary group and joins `docker` for container access.

Development Python uses mise. Base keeps Ubuntu-managed `python3` for Ansible.
Base also provides Git and ripgrep. The Docker role installs `python3-debian`
for APT repository configuration. T3 installs `acl` for switching to the
development user.

After installing T3, Ansible runs `t3 browser setup` as root, pointing it at the
development user's T3 home. T3 manages the browser's AppArmor profile, missing
libraries, and system fonts. Chrome's sandbox stays enabled.

Browser setup reports changed whenever it runs because T3 does not expose
structured change status. It does not trigger a service restart. If it installs
fonts while T3 is already running, restart T3 manually to refresh browser tabs.

T3 downloads Chrome when the first browser tab opens. Its setup command can only
detect missing browser libraries after that download. If the first preview reports
missing libraries, rerun this playbook or run:

```bash
sudo /home/t3code/.local/bin/t3 browser setup --base-dir /home/t3code/.t3
```

The playbook runs `base`, `docker`, and `t3code` in that order. Base installs common
system packages, upgrades APT packages, configures locales and SSH hardening,
disables swap, and changes the SSH login account's primary group to `users`.
It also enables the guest agent on QEMU guests. The Docker role installs Engine,
Compose, and Buildx. T3 adds development tools, browser dependencies, and the
workspace service. Kubernetes provisioning remains
in the separate `saturn.yml` playbook.

## Prepare the VM

Create the VM in Proxmox first. A reasonable starting allocation is 4 vCPU,
16 GiB RAM, and a 100 GiB SSD-backed disk. Use Ubuntu Server 24.04, enable the
QEMU guest agent in Proxmox, and configure a stable DHCP lease or address.
Both amd64 and arm64 Ubuntu guests are accepted by the role.

Use the Ubuntu installer or your VM provisioning tool to create your administrator
account with an SSH public key and sudo access. Python 3 must be installed for
Ansible. This recipe assumes a fresh VM without a competing
Docker or containerd installation.

Allow SSH from your workstation or private network. The T3 server listens only
on `127.0.0.1:3773`, and the recipe does not open firewall ports. Use T3 Connect
or an SSH tunnel for access. Proxmox firewall rules should also cover any ports
published by project containers; Docker-published ports can bypass UFW rules.

## Configure and apply

Run these commands from the repository root:

```bash
uv sync
cp ansible/hosts.ini.example ansible/hosts.ini
```

Edit the ignored `ansible/hosts.ini` with the VM address and your existing
administrator username. Keep it in the `t3code` inventory group. Verify the VM's
SSH host key on the first connection:

```bash
ssh igalarzab@192.0.2.20
```

Then validate and configure it:

```bash
uv run ansible-playbook -i ansible/hosts.ini ansible/t3code.yml --syntax-check
uv run ansible-playbook -i ansible/hosts.ini ansible/t3code.yml
```

Add `--ask-become-pass` if your administrator account needs a sudo password.
Running from the repository root avoids the legacy `ansible/ansible.cfg`, which
disables SSH host-key checking. First installation downloads tools and T3 and can
take several minutes. A successful play ends with an HTTP readiness check.

The role exposes these defaults in `roles/t3code/defaults/main.yml`:

```yaml
t3code_user: t3code
t3code_workspace: "/home/{{ t3code_user }}/workspace"
t3code_channel: stable
```

The mise tool list is configured through `t3code_tools` in the same defaults file.
Each entry has a `tool` version request, such as `node@24`, and its shim `command`,
such as `node`. Change the list to select your development tools; an empty list
skips runtime bootstrapping. Existing shims are preserved on reapplication.

Override these defaults in inventory or with `--extra-vars`. Choose `stable` or `nightly`
for the initial T3 installation. Ansible installs T3 only when the launcher is
absent; changing the channel does not replace an existing installation.

Reapplying preserves user tool selections. Changed
service settings restart T3, interrupting active work. Keep the
user and workspace path unchanged once projects and worktrees exist. This recipe
does not migrate data when those values change.

## Connect T3 and Codex

SSH into the VM as your administrator and switch to the development account:

```bash
sudo -iu t3code
t3 connect link --headless
```

Open the printed sign-in URL on your laptop and approve the matching code. Exit
the development shell and restart the Ansible-managed service:

```bash
exit
sudo systemctl restart t3code
```

Sign into the same T3 Connect account on your client and select this environment.
Do not run `t3 service install`: Ansible owns the system service, and a second
service would compete for the same T3 home and port.

For a desktop connection without T3 Connect, keep this tunnel open on your Mac:

```bash
ssh -N -L 3773:127.0.0.1:3773 igalarzab@192.0.2.20
```

In another SSH session, run `sudo -iu t3code` and `t3 pair`. Paste the pairing URL
into the desktop app. The tunnel's local port must be free. Pairing links and
service logs can contain access tokens; keep them private.

In the remote environment's provider settings, use **Connect with ChatGPT** for
T3-managed Codex. Authenticate GitHub and clone repositories from a T3 terminal:

```bash
gh auth login --hostname github.com --git-protocol https --web
gh auth setup-git
git clone https://github.com/igalarzab/homelab.git /home/t3code/workspace/homelab
```

Set your Git name and email, then add each checkout as a project. Credentials are
entered interactively and stored under `/home/t3code`; none belong in inventory.

Configure provider permissions and authentication through T3 after provisioning.

The development user belongs to `docker`, which effectively grants root access
inside this VM. Treat the entire VM as the agent's execution boundary. Its network
access and credentials still determine which outside systems it can reach.

## Updates and recovery

Systemd runs `t3 serve` directly. Service restarts use the installed version;
they do not download updates or create pre-upgrade snapshots.

To update T3, finish active work and stop the service. Run the official installer
as the development user, choosing your release channel:

```bash
sudo systemctl stop t3code
sudo -iu t3code
curl -fsSL https://t3.codes/install.sh -o ~/.cache/t3-install.sh
T3CODE_CHANNEL=stable T3CODE_INSTALL_BIN_DIR="$HOME/.local/bin" sh ~/.cache/t3-install.sh
exit
sudo systemctl start t3code
sudo systemctl status t3code
sudo journalctl -u t3code -n 50
curl -fsS -o /dev/null http://127.0.0.1:3773/
```

Update T3-managed Codex through provider settings. To update language tools, run
`mise upgrade` as `t3code` when builds are idle. Update mise itself through APT. Project
configuration can select different runtime versions. The shared base role upgrades
OS packages on reapplication; the Docker role installs missing packages and leaves
existing versions alone.

Back up the VM through Proxmox, including `/home/t3code` and
`/var/lib/docker`. Enable the guest agent in the VM configuration for filesystem
freeze support. Stop T3 and project databases before an offline backup, or use
their application-consistent backup procedures. Protect backups as credentials.
Restoring an older T3 runtime alone does not undo database migrations; restore
compatible application state with it.

Reboots and service restarts interrupt running processes. Files and saved T3
history survive, but background commands may need to be restarted. Test restore
procedures before relying on the VM for unpushed work.

## References

- [T3 installation](https://github.com/pingdotgg/t3code/blob/main/docs/user/install.md)
- [T3 remote access and browser setup](https://github.com/pingdotgg/t3code/blob/main/docs/user/remote-access.md)
- [Docker Engine on Ubuntu](https://docs.docker.com/engine/install/ubuntu/)
- [mise installation](https://mise.jdx.dev/installing-mise.html)
