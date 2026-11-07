#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TARGET="$ROOT/vendor/hyperframes"
REPO="https://github.com/heygen-com/hyperframes.git"

mkdir -p "$ROOT/vendor"
if [ -d "$TARGET/.git" ]; then
  echo "HyperFrames already at $TARGET"
  git -C "$TARGET" pull --ff-only || true
  exit 0
fi
rm -rf "$TARGET"
git clone --depth 1 "$REPO" "$TARGET"
echo "Cloned HyperFrames → $TARGET"
echo "Next: cd vendor/hyperframes && npm install  (Node 22+)"
