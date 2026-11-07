#!/usr/bin/env bash
# Clone MoneyPrinterTurbo into vendor/ for BAMO English Shorts production.
# Primary free engine (replaces OpenMontage as daily production path).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TARGET="$ROOT/vendor/moneyprinterturbo"
REPO="https://github.com/harry0703/MoneyPrinterTurbo.git"

if [ -d "$TARGET/.git" ]; then
  echo "MoneyPrinterTurbo already present at $TARGET"
  git -C "$TARGET" fetch --depth 1 origin main || true
  git -C "$TARGET" checkout main || true
  git -C "$TARGET" pull --ff-only || true
  exit 0
fi

mkdir -p "$ROOT/vendor"
rm -rf "$TARGET"
git clone --depth 1 "$REPO" "$TARGET"
echo "Cloned MoneyPrinterTurbo → $TARGET"
echo "Next: configure config.toml (Pexels free key + LLM free tier or Ollama)"
