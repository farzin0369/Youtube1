#!/usr/bin/env bash
# Optional hook: if COLAB_CLI_TOKEN_JSON present in env, prefer GPU clip folder.
set -euo pipefail
if [[ -n "${COLAB_CLI_TOKEN_JSON:-}" ]]; then
  echo "COLAB_CLI token in env — GPU path configured"
  exit 0
fi
echo "no COLAB_CLI token"
exit 1
