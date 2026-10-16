# T3 Code workspace

One persistent, single-user T3 environment on Saturn. T3 runs Codex, terminals,
and browser previews in the same container. Clients connect through T3 Connect.
The server listens on loopback; this release creates no Service or Ingress.

The release uses `bjw-s/app-template` 5.2.1, a single Deployment replica with
`Recreate`, and two `proxmox-retain` volumes:

- `/home/node`: 20 GiB for T3 state, Codex credentials, settings, and caches.
- `/workspace`: 50 GiB for repository clones and worktrees.

The container runs as UID/GID 1000, with a read-only root filesystem, no Linux
capabilities, and no Kubernetes service-account token. `/tmp` and `/dev/shm` are
ephemeral. Requests are 2 CPU and 4 GiB RAM; limits are 4 CPU and 8 GiB RAM.

The pod explicitly uses outer `seccompProfile: Unconfined` because containerd's
default profile blocks namespace creation and mount syscalls needed by Chrome's
browser sandbox. The Codex CLI defaults to the container as its execution
boundary. The
namespace has a Pod Security enforcement exception, with restricted warnings
and auditing retained. This increases the pod's syscall access; it does not
grant Linux capabilities or privileged-container access. A custom node-installed
seccomp profile can narrow this later.

## Build and publish

The Dockerfile pins T3 0.1.0, Codex 0.163.0, Node.js 24.21.0, and uv 0.13.1.
It verifies the T3 archive against the release's SHA256SUMS. Git, GitHub CLI,
Python, build tools, Corepack, and Chrome's shared libraries are
included. Corepack uses each repository's package-manager version; uv can fetch
the Python version required by its project.

Build from the repository root. Publish an amd64 image for Saturn, even when
building on an Apple Silicon Mac:

```bash
docker buildx build --platform linux/amd64 \
  --tag ghcr.io/igalarzab/homelab-t3code:0.1.0-codex0.163.0-1 \
  --push kubernetes/t3code
```

Authenticate Docker to GHCR before publishing. The repository and tag are set in
`kubernetes/.env`; override them in `.env.saturn` when using another registry.
Make the image package public for unauthenticated pulls, or configure an
image-pull Secret in the namespace and reference it through
`controllers.t3code.pod.imagePullSecrets` in the values file.

Keep image updates reproducible: change the pinned versions, build a new tag,
and update `T3CODE_IMAGE_TAG`. Finish active agent work before rolling out.
Use the versions recommended by T3's provider settings when upgrading Codex.

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
ChatGPT. The image also includes a standalone Codex CLI. To use that login:

```bash
kubectl --context saturn -n t3code exec -it deployment/t3code -- \
  codex login --device-auth
```

Select the installed CLI provider in T3. Device-code login must be enabled for
your OpenAI account or workspace. Credentials and their refreshed tokens stay in
the writable home volume. No API key is baked into the image or Helm values.

The entrypoint seeds `~/.codex/config.toml` only when it is absent, using
`danger-full-access`, on-request approvals, and file-based credential storage.
Existing configuration survives restarts and image updates.

The standalone Codex CLI's internal command sandbox is disabled. Its commands can
modify any writable path in the pod, including other repositories, T3 state, and stored
credentials. The pod's non-root user, dropped capabilities, read-only root
filesystem, and absence of host mounts or Kubernetes credentials define the
outer boundary. On-request approvals remain configured separately.

T3 0.1.0 explicitly overrides these settings for each turn. To use the container
as the execution boundary in T3, choose **Full access** in the thread's permission
mode. That mode also disables approval prompts. The **Auto** and **Auto accept
edits** modes use Codex's workspace sandbox. The recipe does not force a T3
permission mode; select Full access only for work you intend to run with that
access. See the [version-pinned T3 mode mapping](https://github.com/pingdotgg/t3code/blob/v0.1.0/apps/server/src/orchestration-v2/Adapters/CodexAdapterV2.ts#L679).

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

## References

- [T3 installation and providers](https://github.com/pingdotgg/t3code/blob/main/docs/user/install.md)
- [T3 remote access](https://github.com/pingdotgg/t3code/blob/main/docs/user/remote-access.md)
- [T3 Codex setup](https://github.com/pingdotgg/t3code/blob/main/docs/user/providers-codex.md)
- [Codex authentication](https://learn.chatgpt.com/docs/auth)
- [Codex sandbox requirements](https://learn.chatgpt.com/docs/sandboxing)
- [Containerd default seccomp profile](https://github.com/containerd/containerd/blob/main/contrib/seccomp/seccomp_default.go)
