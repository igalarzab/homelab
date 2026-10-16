# T3 Code workspace

One persistent, single-user T3 environment on Saturn. T3 runs Codex, terminals,
and browser previews in the same container. Clients connect through T3 Connect.
The server listens on loopback; this release creates no Service or Ingress.

The release uses `bjw-s/app-template` 5.2.1, a single Deployment replica with
`Recreate`, and two `proxmox-retain` volumes:

- `/home/node`: 20 GiB for tool installations, T3 state, credentials, and caches.
- `/workspace`: 50 GiB for repository clones and worktrees.

The container runs as UID/GID 1000, with a read-only root filesystem, no Linux
capabilities, and no Kubernetes service-account token. `/tmp` and `/dev/shm` are
ephemeral. Requests are 2 CPU and 4 GiB RAM; limits are 4 CPU and 8 GiB RAM.

The pod explicitly uses outer `seccompProfile: Unconfined` because containerd's
default profile blocks namespace creation and mount syscalls needed by Chrome's
browser sandbox. The Codex CLI defaults to the container as its execution
boundary. The namespace has a Pod Security enforcement exception, with restricted
warnings and auditing retained. This increases the pod's syscall access; it does not
grant Linux capabilities or privileged-container access. A custom node-installed
seccomp profile can narrow this later.

## Build and publish

The image contains the development environment, with Node.js 24.21.0 and uv
0.13.1. Git, GitHub CLI, Python, build tools, Corepack, and Chrome's shared
libraries are included. Corepack uses each repository's package-manager version;
uv can fetch the Python version required by its project.

T3 and Codex are installed into the persistent home volume. Their updates do not
require rebuilding the base image. Rebuild it periodically for system and runtime
dependency updates, and publish a new base image tag for those changes.

Build from the repository root. Publish an amd64 image for Saturn, even when
building on an Apple Silicon Mac:

```bash
docker buildx build --platform linux/amd64 \
  --tag ghcr.io/igalarzab/t3code:base-1 \
  --push kubernetes/t3code
```

Authenticate Docker to GHCR before publishing. The repository and tag are set in
`kubernetes/.env`; override them in `.env.saturn` when using another registry.
Make the image package public for unauthenticated pulls, or configure an
image-pull Secret in the namespace and reference it through
`controllers.t3code.pod.imagePullSecrets` in the values file.

## Application updates

Before launching T3, the entrypoint runs its official installer against the
selected release channel. The installer verifies release checksums, stages the
new runtime, and updates `/home/node/.local/bin/t3`. Versioned releases live under
`/home/node/.t3/runtime/versions`. Both paths survive pod replacement.

Configure these environment variables in `values.yml`:

- `T3CODE_CHANNEL=stable`: follow stable releases. Use `nightly` when that matches
  your desktop app's channel.
- `T3CODE_UPDATE_ON_START=true`: check for updates at each pod start. Set `false`
  to use the installed runtime without checking. A fresh home still needs its
  initial installation.

The installer-script download has a 30-second limit, and installation has a
180-second limit. If either fails, startup uses the cached T3 installation. A
first installation failure exits with an error because no runtime is available.
An installed runtime that cannot execute also fails visibly. First startup needs
internet access to `t3.codes`, GitHub, and its release-download hosts.

Before launching a different T3 version, startup snapshots existing `userdata`
into `~/.t3/backups/before-upgrade.tar.gz`. It retains one snapshot, replacing it
at the next version change. The adjacent `.version` file records the previously
launched version when known. Snapshot failure stops startup before the new server
can modify state. `~/.t3/.workspace-version` and pod logs record the version
selected at launch.

T3 manages Codex installation through **Connect with ChatGPT** in Settings >
Providers. Its runtime and provider state are stored in the persistent home.
Use the provider update controls in T3 when updates are offered. There is no
background updater in this recipe that replaces tools during active work.

Finish active work before applying updates. To check for a new T3 release, restart
the pod while startup checks are enabled:

```bash
kubectl --context saturn -n t3code rollout restart deployment/t3code
kubectl --context saturn -n t3code rollout status deployment/t3code
```

T3's update controls can also update a writable installation. A foreground server
may require a pod restart to activate the selected version. To retain a specific
version selected through those controls, disable startup checks before restarting.
Keep the desktop app and server compatible; follow T3's version notice if their
orchestration protocols differ.

The snapshot is an offline copy of T3 state, not automatic rollback. Restore it
only while T3 is stopped, together with a compatible runtime. Returning to an
older base image does not roll back the application installed on the home volume.

## Deploy on Saturn

The release starts disabled because its image must be published first. After
publishing, set `apps.t3code.enabled` to `true` in `helmsman.saturn.yml`.

From `kubernetes/`:

```bash
uv run python run.py saturn dry-run -n t3code
uv run python run.py saturn apply -n t3code
kubectl --context saturn -n t3code rollout status deployment/t3code
```

## Connect your devices

Link the environment using a headless login. Open the printed browser URL on
your laptop and approve the matching code:

```bash
kubectl --context saturn -n t3code exec -it deployment/t3code -- \
  t3 connect link --headless
kubectl --context saturn -n t3code rollout restart deployment/t3code
kubectl --context saturn -n t3code rollout status deployment/t3code
```

In the T3 desktop or mobile app, sign in to the same T3 Connect account and select
the new environment. The link is stored on the home volume. Do not install a
system service in the pod; Kubernetes keeps the foreground `t3 serve` process
running.

For desktop access without T3 Connect, run these commands in separate terminals:

```bash
kubectl --context saturn -n t3code port-forward deployment/t3code 3773:3773
kubectl --context saturn -n t3code exec -it deployment/t3code -- t3 pair
```

Paste the loopback pairing URL into the desktop app's Add environment flow.
The port forward must stay running. A phone cannot reach your laptop's loopback
address. Hosted web access through `app.t3.codes` requires HTTPS.

Pairing URLs and login codes grant access. Do not commit them or share pod logs
containing them. T3 may print a bootstrap pairing URL at startup.

## Configure Codex and Git

In T3, select this environment in Settings > Providers, then connect with
ChatGPT. T3 installs and manages Codex for that connection.

If you also need a standalone Codex CLI, install it in the workspace terminal:

```bash
npm install --global @openai/codex@latest
codex login --device-auth
```

`NPM_CONFIG_PREFIX` points to `/home/node/.local`, whose `bin` directory is on
`PATH`, so the CLI stays writable and survives restarts. You can select that
installed CLI provider in T3 instead of its managed integration. Device-code login
must be enabled for your OpenAI account or workspace. Credentials and refreshed
tokens stay in the home volume. No API key is baked into the image or Helm values.

The entrypoint seeds `~/.codex/config.toml` only when it is absent, using
`danger-full-access`, on-request approvals, and file-based credential storage.
Existing configuration survives restarts and image updates.

The standalone Codex CLI's internal command sandbox is disabled. Its commands can
modify any writable path in the pod, including other repositories, T3 state, and stored
credentials. The pod's non-root user, dropped capabilities, read-only root
filesystem, and absence of host mounts or Kubernetes credentials define the
outer boundary. On-request approvals remain configured separately.

T3's thread permission mode overrides these settings. To use the container
as the execution boundary in T3, choose **Full access** in the thread's permission
mode. That mode also disables approval prompts. The **Auto** and **Auto accept
edits** modes use Codex's workspace sandbox. The recipe does not force a T3
permission mode; select Full access only for work you intend to run with that
access. Check the selected mode after application upgrades.

Open a workspace terminal, authenticate GitHub, and clone projects under
`/workspace`. Set your Git identity there. For example:

```bash
gh auth login --hostname github.com --git-protocol https --web
gh auth setup-git
git clone https://github.com/igalarzab/homelab.git /workspace/homelab
```

Register each checkout as a project in this T3 environment. The same repositories
on your Mac remain separate checkouts; their files and active threads are not
automatically migrated to Kubernetes.

## Verify the workspace and browser

Verify workspace access and the persisted Codex defaults before starting work:

```bash
kubectl --context saturn -n t3code exec deployment/t3code -- \
  sh -c 'touch /workspace/.write-check && rm /workspace/.write-check'
kubectl --context saturn -n t3code exec deployment/t3code -- \
  cat /home/node/.codex/config.toml
```

Open a browser preview in T3 to verify Chrome's sandbox and shared libraries.
T3 downloads its browser on first use and stores it under the persistent T3 home.
The image includes the Linux libraries; node kernel and runtime restrictions
still need to allow Chrome's sandbox and the pod's `hostUsers: false` setting.
`/dev/shm` has a 1 GiB limit and counts toward pod memory usage. Browser profiles
and sign-in cookies are sensitive data.

## Persistence and recovery

Back up both PVCs. The home volume contains credentials, pairing state, T3
history, and browser data. Protect backups accordingly. `Retain` preserves the
underlying storage after PVC deletion; it is not a backup or automatic restore.

Pod restarts interrupt agents, terminals, tests, and development servers. Saved
history and files survive. Reconnect and resume the saved thread after recovery.
The home and workspace paths must stay the same for existing worktrees.

The pod has no cluster credentials. Repository code can still access credentials
in its environment and network destinations available to the pod. Use this as a
trusted personal workspace; separate credentials and pods for unrelated users.

## Test startup behavior

The entrypoint tests cover initial installation, disabled update checks, offline
fallback, existing configuration, pre-upgrade snapshots, and installation errors.
They use a fake installer and run without network access:

```bash
docker build --tag t3code:test kubernetes/t3code
docker run --rm -i --network none --read-only \
  --cap-drop ALL --security-opt no-new-privileges \
  --tmpfs /home/node:uid=1000,gid=1000,mode=0700,exec --tmpfs /tmp \
  t3code:test python3 - < kubernetes/t3code/test_entrypoint.py
```

The executable home mount models the PVC, where installed tool binaries run.
`/tmp` can stay mounted with `noexec`.

## References

- [T3 installation and providers](https://github.com/pingdotgg/t3code/blob/main/docs/user/install.md)
- [T3 remote access](https://github.com/pingdotgg/t3code/blob/main/docs/user/remote-access.md)
- [T3 Codex setup](https://github.com/pingdotgg/t3code/blob/main/docs/user/providers-codex.md)
- [T3 updates](https://github.com/pingdotgg/t3code/blob/main/docs/user/updating.md)
- [Codex authentication](https://learn.chatgpt.com/docs/auth)
- [Codex sandbox requirements](https://learn.chatgpt.com/docs/sandboxing)
- [Containerd default seccomp profile](https://github.com/containerd/containerd/blob/main/contrib/seccomp/seccomp_default.go)
