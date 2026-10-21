# Hamrah mobile assistant backend (Cloudflare Worker)

This is a restricted backend scaffold for the mobile PWA. It is **not deployed automatically**. The chat route is configured to use the user's own OpenClaw Gateway; this repository does not run or host OpenClaw itself.

## Security model

- Keep `GITHUB_TOKEN`, `APP_ACCESS_SECRET`, and `OPENCLAW_GATEWAY_TOKEN` in Cloudflare Worker Secrets, never in Git or the PWA.
- Create a fine-grained GitHub PAT limited to **only** `farzin0369/Youtube1`, with Contents: Read and write and Pull requests: Read and write. Do not grant administration, workflows, Actions, secrets, or organization permissions.
- `/github/tree` and `/github/file` are read-only. Writes are limited to `mobile-assistant/`, `docs/`, and `scripts/`; GitHub workflow files cannot be changed by the assistant.
- `/github/propose-change` requires the explicit `X-Confirm-Action: I_APPROVE_WRITE` header, restricts editable paths, creates a new branch, and opens a **draft PR**. It never writes to `main` or merges.
- OpenClaw receives chat messages only through the configured Gateway URL. Never expose the Gateway token to the PWA or return it to the client.
- Configure `ALLOWED_ORIGIN` to the exact HTTPS origin serving the PWA. Do not use wildcard origins in production.

## Configure OpenClaw chat

Set these as **Cloudflare Worker secrets/variables**, not repository files:

- Secret `OPENCLAW_GATEWAY_TOKEN`: token required by your OpenClaw Gateway.
- Variable `OPENCLAW_CHAT_URL`: full reachable chat-completions endpoint URL exposed by your OpenClaw Gateway (must be reachable from Cloudflare Worker over HTTPS).
- Optional variable `OPENCLAW_MODEL`: model/agent identifier accepted by that Gateway; defaults to `openclaw` in this backend.
- Secret `APP_ACCESS_SECRET`: long random secret used as the Bearer token by the app.
- Secret `GITHUB_TOKEN`: fine-grained PAT with the minimum repository permissions above.

The Gateway must already be running on a persistent host and securely reachable from Cloudflare. A URL on localhost, a private LAN, or a sleeping Colab runtime will not be reachable by a deployed Worker. This repo does not provision an OpenClaw host or create a Gateway token.

## Deploy (not yet verified)

1. Deploy this directory as the Cloudflare Worker `hamrah-mobile-backend` using the repository workflow or Wrangler.
2. Add the secrets/variables above in the Worker settings. Do not commit credentials to GitHub.
3. Set `ALLOWED_ORIGIN` to the exact HTTPS origin serving the PWA.
4. Test `GET /health`, then authenticated `GET /github/tree?branch=main` and `POST /chat`.
5. Confirm Cloudflare logs contain no tokens and verify the chat response comes from your OpenClaw Gateway.

## API

- `GET /health`
- `GET /github/tree?branch=main`
- `GET /github/file?path=mobile-assistant/README.md&ref=main`
- `POST /github/propose-change` JSON: `{"path":"docs/example.md","content":"...","message":"Propose documentation update"}`; must include explicit confirmation header.
- `POST /chat` JSON: `{"messages":[{"role":"user","content":"..."}]}`

## Current limitations

The Worker and OpenClaw connection have **not been live-tested or confirmed deployed**. No credentials are included. The PWA must be configured with the deployed Worker URL and app access secret. GitHub write actions only propose draft PRs, and every change still requires review. This is not device-wide control of Android apps or an unrestricted autonomous agent.
