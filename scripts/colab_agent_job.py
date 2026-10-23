"""Compatibility wrapper: route legacy Colab agent launches to ImamAli110 LTX-only private production."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

SECRETS_FILE = Path("/content/.tt-khabar-secrets.json")
IMAMALI_SECRETS = Path("/content/.imamali110-secrets.json")
REPO = Path("/content/Youtube1")
RESULT_FILE = Path("/tmp/colab-result.json")
MEMORY_FILE = Path("/content/.tt-khabar-agent-memory.json")
MEMORY_OUT = Path("/tmp/agent-memory.json")


def _load(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def main() -> int:
    legacy = _load(SECRETS_FILE, {})
    SECRETS_FILE.unlink(missing_ok=True)
    required = ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN")
    missing = [key for key in required if not legacy.get(key)]
    if missing:
        raise RuntimeError("Missing YouTube OAuth settings: " + ", ".join(missing))

    old_kind = str(legacy.get("PRODUCTION_FORMAT") or legacy.get("PIPELINE_KIND") or "shorts").lower()
    kind = {"short": "shorts"}.get(old_kind, old_kind)
    if kind not in {"shorts", "long"}:
        raise RuntimeError("Unsupported format; only shorts or long is allowed.")
    run_token = str(legacy.get("RUN_TOKEN") or legacy.get("PIPELINE_RUN_ID") or datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S"))
    config = {
        key: str(legacy[key]) for key in required
    }
    config.update({
        "PRODUCTION_FORMAT": kind,
        "UPLOAD_PRIVATE": "true",  # This wrapper never permits public publishing.
        "GIT_REF": str(legacy.get("GIT_REF") or "feat/youtube-agent-skill-integration"),
        "RUN_TOKEN": run_token,
        "LOCAL_LLM_MODEL": str(legacy.get("LOCAL_LLM_MODEL") or "qwen2.5:7b"),
        "LTX_VIDEO_STEPS": str(legacy.get("LTX_VIDEO_STEPS") or "20"),
    })
    IMAMALI_SECRETS.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")
    IMAMALI_SECRETS.chmod(0o600)

    ref = config["GIT_REF"]
    if REPO.exists():
        shutil.rmtree(REPO)
    clone = subprocess.run(
        ["git", "clone", "--depth", "1", "--branch", ref,
         "https://github.com/farzin0369/Youtube1.git", str(REPO)],
        text=True, capture_output=True, check=False, timeout=600,
    )
    if clone.returncode:
        raise RuntimeError("Could not load the LTX production code: " + (clone.stderr or "")[-1000:])
    sys.path.insert(0, str(REPO))
    from scripts.colab_spiritual_job import main as run_ltx_private_job

    code = run_ltx_private_job()
    result = _load(Path("/content/ImamAli110-result.json"), {"success": code == 0})
    RESULT_FILE.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    memory = _load(MEMORY_FILE, {"schema_version": 1, "editorial_lessons": [], "runs": []})
    memory.setdefault("runs", [])
    memory["runs"] = (memory["runs"] or [])[-19:] + [{
        "run_id": result.get("run_id", run_token),
        "success": bool(result.get("success")),
        "format": kind,
        "upload_mode": "private",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }]
    memory["updated_at"] = datetime.now(timezone.utc).isoformat()
    MEMORY_OUT.write_text(json.dumps(memory, ensure_ascii=False, indent=2), encoding="utf-8")
    if code != 0 or not result.get("success"):
        raise RuntimeError("LTX production failed or the private upload was not confirmed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        payload = {
            "success": False,
            "error_type": type(exc).__name__,
            "error": str(exc)[:1000],
            "traceback_tail": traceback.format_exc()[-3000:],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        RESULT_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        raise
