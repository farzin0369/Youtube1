# Hamrah mobile assistant backend (Cloudflare Worker)

This is a restricted backend scaffold for the mobile PWA. It is not deployed automatically.

## Security model

- Keep `GITHUB_TOKEN` and AI credentials in Cloudflare Worker Secrets, never in Git or the PWA.
- Create a fine-grained GitHub PAT limited to **only** `farzin0369/Youtube1`, with Contents: Read and write and Pull requests: Read and write. Do not grant administration, workflows, Actions, secrets, or organization permissions.
- `/github/tree` and `/github/file` are read-only.
- `/github/propose-change` requires the explicit `X-Confirm-Action: I_APPROVE_WRITE` header, restricts editable paths, creates a new branch, and opens a **draft PR**. It never writes to `main` or merges.
- The AI endpoint does not get GitHub credentials or tool access automatically. Model output must not be treated as trusted code.
- Configure `ALLOWED_ORIGIN` to the exact HTTPS origin serving the PWA. Do not use wildcard origins in production.

## Deploy (free tier may be sufficient; provider limits apply)

1. Create a Cloudflare account and a Worker named `hamrah-mobile-backend`.
2. Deploy this directory using Wrangler from a trusted development environment, or paste `src/index.js` into the Worker editor.
3. Add Worker secrets:
   - `GITHUB_TOKEN` (fine-grained PAT with the minimum permissions above)
   - `APP_ACCESS_SECRET` (long random secret; required as a Bearer token for all endpoints except health)
   - `AI_API_URL` (base URL for an OpenAI-compatible provider)
   - `AI_MODEL` (provider's exact model ID)
   - `AI_API_KEY` (provider key)
4. Set `ALLOWED_ORIGIN` as a Worker variable to the exact deployed PWA origin.
5. Test `GET /health`, then `GET /github/tree?branch=main`.

## API

- `GET /health`
- `GET /github/tree?branch=main`
- `GET /github/file?path=mobile-assistant/README.md&ref=main`
- `POST /github/propose-change` JSON: `{"path":"docs/example.md","content":"...","message":"Propose documentation update"}`; must include explicit confirmation header.
- `POST /chat` JSON: `{"messages":[{"role":"user","content":"..."}]}`

## Important limitations

This scaffold has not been deployed or live-tested. No GitHub token, access secret, or model key is included. The PWA UI has not yet been connected to these endpoints. GitHub write actions only propose draft PRs, and every change still requires review. This is not device-wide control of Android apps or an unrestricted autonomous agent.
