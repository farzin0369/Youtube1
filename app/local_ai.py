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

def ollama_generate(
    prompt: str,
    system: str = "",
    model: str | None = None,
    *,
    format_json: bool = False,
    num_predict: int | None = None,
    temperature: float | None = None,
    timeout: float | None = None,
) -> str:
    if not ollama_available():
        raise RuntimeError("Local Ollama is not running on 127.0.0.1:11434")
    try:
        configured_timeout = max(30, min(900, int(env("OLLAMA_TIMEOUT_SECONDS") or "300")))
        effective_timeout = configured_timeout if timeout is None else max(30, min(900, int(timeout)))
        default_predict = "4096" if format_json else "2200"
        requested_predict = num_predict if num_predict is not None else int(env("OLLAMA_NUM_PREDICT") or default_predict)
        effective_predict = max(256, min(4096, int(requested_predict)))
        num_ctx = max(2048, min(8192, int(env("OLLAMA_NUM_CTX") or "4096")))
    except ValueError:
        effective_timeout, effective_predict, num_ctx = 300, 4096 if format_json else 2200, 4096
    raw_keep_alive = env("OLLAMA_KEEP_ALIVE")
    try:
        keep_alive = 0 if raw_keep_alive is None else int(raw_keep_alive)
    except ValueError:
        keep_alive = 0
    effective_temperature = (0.35 if format_json else 0.55) if temperature is None else max(0.0, min(1.5, float(temperature)))
    payload = {
        "model": model or env("LOCAL_LLM_MODEL") or "llama3.2:1b",
        "prompt": prompt,
        "system": system,
        "stream": False,
        "keep_alive": keep_alive,
        "options": {"temperature": effective_temperature, "num_predict": effective_predict, "num_ctx": num_ctx},
    }
    if format_json:
        payload["format"] = "json"
    payload = json.dumps(payload).encode()
    req = urllib.request.Request((env("OLLAMA_BASE_URL") or "http://127.0.0.1:11434").rstrip("/") + "/api/generate", data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=effective_timeout) as r:
        data = json.loads(r.read().decode())
    return str(data.get("response") or "").strip()

def release_ollama_model(model: str | None = None) -> None:
    """Unload Ollama weights so CogVideoX can use RAM and the T4."""
    model = model or env("LOCAL_LLM_MODEL") or "qwen2.5:3b"
    try:
        subprocess.run(["ollama", "stop", model], check=False, capture_output=True, text=True, timeout=30)
    except Exception:
        return

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
