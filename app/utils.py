"""Shared helpers."""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output"
ASSETS_DIR = ROOT / "assets"


def ensure_dirs() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "audit").mkdir(parents=True, exist_ok=True)


def load_yaml(path: Path) -> dict[str, Any]:
    import yaml

    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_channel_config() -> dict[str, Any]:
    return load_yaml(ROOT / "config" / "channel.yaml")


def load_content_policy() -> dict[str, Any]:
    return load_yaml(ROOT / "config" / "content-policy.yaml")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_id(kind: str) -> str:
    """Use a validated caller-supplied id for retries; otherwise create a unique UTC id."""
    requested = str(env("PIPELINE_RUN_ID") or "").strip()
    if requested:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", requested):
            raise ValueError("PIPELINE_RUN_ID may contain only letters, digits, '_' and '-' (max 80 chars)")
        return requested
    return f"{kind}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def env(name: str, default: str | None = None) -> str | None:
    v = os.environ.get(name, default)
    if v is not None and str(v).strip() == "":
        return default
    return v


def has_youtube_creds() -> bool:
    return all(
        env(k)
        for k in ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN")
    )


def clean_persian(text: str) -> str:
    text = text.strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?؟۔])(?:\s+|(?=[آ-یA-Za-z0-9]))", text.strip())
    return [p.strip() for p in parts if p.strip()]
