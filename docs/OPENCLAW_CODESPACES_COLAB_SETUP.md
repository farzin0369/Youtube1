# OpenClaw setup for Youtube1 (Codespaces / Colab)

OpenClaw is MIT-licensed open-source software maintained upstream at https://github.com/openclaw/openclaw. Keep its source upstream rather than copying the entire monorepo into this YouTube repository. This file documents a lightweight installation path.

## GitHub Codespaces (preferred for an interactive test)

1. Open https://github.com/farzin0369/Youtube1
2. Tap **Code → Codespaces → Create codespace on main** (if available for your account).
3. In the Codespaces terminal, run:

```bash
node --version
npm --version
npm install -g openclaw@latest --allow-scripts=openclaw
openclaw onboard
openclaw gateway status
```

If npm is older than 11.16, use `npm install -g openclaw@latest` without `--allow-scripts`.
During onboarding, choose a model provider you have access to and configure credentials through the onboarding prompt or the environment's secret manager. Never commit API keys, OAuth tokens, or OpenClaw state into this repository.

## Google Colab (temporary experiment only)

Colab runtimes are temporary and can disconnect. They are not a reliable always-on OpenClaw Gateway host. In a fresh Colab runtime, run:

```bash
!node --version
!npm install -g openclaw@latest --allow-scripts=openclaw
!openclaw --help
```

Complete onboarding interactively only if the runtime supports the required prompts and securely provide model credentials. Do not paste secrets into notebook cells that will be saved or shared.

## Important deployment limits

- Installing OpenClaw is not the same as connecting it to YouTube or MoneyPrinterTurbo.
- A Gateway running in Codespaces/Colab stops or becomes unreachable when that environment stops or disconnects.
- For unattended daily operation, use a persistent host or keep the scheduled GitHub Actions workflow as the scheduler and let a configured agent monitor it.
- First test generation and YouTube upload privately. Do not enable public publishing until the logs and resulting video ID confirm success.
- GitHub Actions secrets are not automatically available inside Codespaces or Colab; configure only the minimum required credentials separately and securely.

## Related project files

- [OpenClaw integration plan](OPENCLAW_INTEGRATION.md)
- [MoneyPrinterTurbo private test workflow](../.github/workflows/mpt-private-video-test.yml)
- [Official OpenClaw source](https://github.com/openclaw/openclaw)
- [Official installation guide](https://docs.openclaw.ai/install)
