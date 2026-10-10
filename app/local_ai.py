"""Cloud-safe local adapters. No paid hosted AI API is required.
Ollama is optional; Piper is used for free Persian narration on GitHub runners.
"""
from __future__ import annotations
import json
import subprocess
import urllib.request
from pathlib import Path
from typing import Any
from app.utils import env

def local_enabled() -> bool:
    return (env("AI_ENGINE") or "local").lower() == "local"

def text_ai_available() -> bool:
    return ollama_available()

def ollama_available() -> bool:
    try:
        with urllib.request.urlopen(((env("OLLAMA_BASE_URL") or "http://127.0.0.1:11434").rstrip("/") + "/api/tags"), timeout=3) as r:
            return r.status == 200
    except Exception:
        return False

def ollama_generate(prompt: str, system: str = "", model: str | None = None) -> str:
    if not ollama_available():
        raise RuntimeError("Local Ollama is not running on 127.0.0.1:11434")
    payload = json.dumps({"model": model or env("LOCAL_LLM_MODEL") or "llama3.2:3b","prompt": prompt,"system": system,"stream": False,"keep_alive": 0,"options": {"temperature": 0.35}}).encode()
    req = urllib.request.Request((env("OLLAMA_BASE_URL") or "http://127.0.0.1:11434").rstrip("/") + "/api/generate", data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        data = json.loads(r.read().decode())
    return str(data.get("response") or "").strip()

def piper_synthesize(text: str, out_path: Path) -> dict[str, Any]:
    exe = env("PIPER_BIN") or "piper"
    model = env("PIPER_MODEL")
    if not model:
        raise RuntimeError("PIPER_MODEL is required for local narration")
    out_path = Path(out_path).with_suffix(".wav")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run([exe, "--model", model, "--output_file", str(out_path)], input=text[:5000], text=True, capture_output=True, timeout=300)
    if proc.returncode != 0 or not out_path.exists() or out_path.stat().st_size < 1000:
        raise RuntimeError(f"Piper TTS failed: {proc.stderr[-1000:]}")
    return {"path": str(out_path), "provider": "piper-local", "model": model, "narrator_locked": True, "ok": True}
