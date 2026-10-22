"""CLI adapter used by the isolated Jarvis chat workflow."""

import json
import os
import sys
from pathlib import Path

# Scripts are launched by filename; add repository root for the shared module.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from jarvis.main import ask_jarvis


def run(prompt: str, history) -> str:
    return ask_jarvis(prompt, history)


if __name__ == "__main__":
    try:
        history = json.loads(os.getenv("HISTORY", "[]"))
    except (json.JSONDecodeError, TypeError):
        history = []
    try:
        print(run(os.getenv("PROMPT", "سلام جارویس"), history))
    except Exception as exc:
        print(f"خطای Jarvis: {exc}", file=sys.stderr)
        raise SystemExit(1)
