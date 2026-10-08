# MetaMCP

## Dashboard access

MetaMCP reuses the cluster's `POCKETID_CLIENT_ID` and `POCKETID_CLIENT_SECRET`.
The credentials are provided through the MetaMCP Kubernetes Secret.

Add this callback to the existing Pocket ID client's allowed callback URLs,
replacing `<domain-root>` with the cluster's `COMMON_DOMAIN_ROOT`:

```text
https://metamcp.<domain-root>/api/auth/oauth2/callback/oidc
```

MetaMCP uses `https://auth.<domain-root>` for OIDC discovery and authorization,
with the `openid email profile` scopes and PKCE enabled. `BETTER_AUTH_SECRET`
is still required for MetaMCP's sessions. The Traefik OIDC middleware remains
enabled on the ingress.

After verifying **Sign in with OIDC**, configure **Settings > Authentication
Settings** as needed:

- **Disable UI Registration**: on to prevent local account registration.
- **Disable SSO Registration**: off to allow first-time Pocket ID logins.
- **Disable Basic Authentication**: on to remove email/password login after
  confirming Pocket ID works. This removes the password fallback.

These switches are stored in MetaMCP's database, separately from Helm values.

## Endpoints access

All `/metamcp/<endpoint-name>` routes use a separate ingress without the Pocket
ID middleware, including endpoints created later through the UI. MetaMCP
enforces each endpoint's configured API key or OAuth authentication. Keep at
least one authentication method enabled on endpoints that require protection.
Disabling both makes that endpoint anonymous. The UI remains behind Pocket ID.
