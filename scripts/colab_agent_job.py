"""Remote Colab GPU job: local-model writing, CogVideoX rendering, YouTube publishing and bounded self-review."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

SECRETS_FILE = Path("/content/.imamali110-secrets.json")
MEMORY_FILE = Path("/content/.imamali110-agent-memory.json")
REPO = Path("/content/Youtube1")
RESULT_FILE = Path("/tmp/colab-result.json")
MEMORY_OUT = Path("/tmp/agent-memory.json")


def run(cmd, *, cwd=None, env=None, check=True, capture_output=False):
    return subprocess.run(
        cmd, cwd=cwd, env=env, check=check, text=True,
        stdout=subprocess.PIPE if capture_output else None,
        stderr=subprocess.PIPE if capture_output else None,
    )


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def clean_lessons(value):
    if not isinstance(value, list):
        return []
    result = []
    for item in value:
        if isinstance(item, str):
            item = " ".join(item.split())[:180]
            if item and item not in result:
                result.append(item)
    return result[-8:]


def main():
    secrets = load_json(SECRETS_FILE, {})
    required = ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN")
    missing = [key for key in required if not secrets.get(key)]
    if missing:
        raise RuntimeError("Missing required YouTube OAuth settings: " + ", ".join(missing))

    memory = load_json(MEMORY_FILE, {"schema_version": 1, "editorial_lessons": [], "runs": []})
    memory["editorial_lessons"] = clean_lessons(memory.get("editorial_lessons"))
    memory.setdefault("runs", [])
    rid = str(secrets.get("PIPELINE_RUN_ID") or ("short_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")))
    model = str(secrets.get("LOCAL_LLM_MODEL") or "llama3.2:3b")

    print("[agent] Checking Colab GPU runtime.")
    import torch
    if not torch.cuda.is_available():
        raise RuntimeError("Colab runtime has no CUDA GPU; refusing CPU fallback.")
    gpu_name = torch.cuda.get_device_name(0)
    print("[agent] GPU:", gpu_name)

    if not REPO.exists():
        run(["git", "clone", "--depth", "1", "https://github.com/farzin0369/Youtube1.git", str(REPO)])
    os.chdir(REPO)
    (REPO / "state").mkdir(parents=True, exist_ok=True)
    (REPO / "state" / "agent_memory.json").write_text(
        json.dumps(memory, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("[agent] Installing the repository's production stack.")
    run([sys.executable, "-m", "pip", "install", "-q", "-r", "requirements.txt",
         "diffusers>=0.32,<0.42", "transformers>=4.46", "accelerate>=1.0",
         "safetensors", "imageio-ffmpeg", "piper-tts"])

    print("[agent] Repairing only known incompatible TorchAO packages and validating CogVideoX.")
    run([sys.executable, "scripts/repair_colab_cogvideox.py"])

    if shutil.which("ollama") is None:
        run(["bash", "-lc", "curl -fsSL https://ollama.com/install.sh | sh"])
    ollama_log = open("/tmp/ollama.log", "w", encoding="utf-8")
    ollama = subprocess.Popen(["ollama", "serve"], stdout=ollama_log, stderr=subprocess.STDOUT)
    base = "http://127.0.0.1:11434"
    ready = False
    for _ in range(90):
        try:
            import urllib.request
            with urllib.request.urlopen(base + "/api/tags", timeout=2) as response:
                ready = response.status == 200
            if ready:
                break
        except Exception:
            time.sleep(2)
    if not ready:
        raise RuntimeError("Local Ollama service did not become ready; see /tmp/ollama.log")

    print("[agent] Ensuring local language model is available:", model)
    run(["ollama", "pull", model])

    env = os.environ.copy()
    env.update({
        "AI_ENGINE": "local",
        "LOCAL_LLM_MODEL": model,
        "OLLAMA_BASE_URL": base,
        "VIDEO_ENGINE": "cogvideox",
        "LOCAL_VIDEO_MODEL": "THUDM/CogVideoX-2b",
        "TTS_PROVIDER": "edge",
        "TTS_VOICE": "fa-IR-FaridNeural",
        "YOUTUBE_CONTAINS_SYNTHETIC_MEDIA": "true",
        "PIPELINE_RUN_ID": rid,
        "YOUTUBE_CLIENT_ID": str(secrets["YOUTUBE_CLIENT_ID"]),
        "YOUTUBE_CLIENT_SECRET": str(secrets["YOUTUBE_CLIENT_SECRET"]),
        "YOUTUBE_REFRESH_TOKEN": str(secrets["YOUTUBE_REFRESH_TOKEN"]),
        "YOUTUBE_PUBLISH_AT": str(secrets.get("YOUTUBE_PUBLISH_AT") or ""),
    })
    pipeline = run([sys.executable, "-m", "app.pipeline", "--kind", "short", "--publish-mode", "public"],
                   cwd=REPO, env=env, check=False, capture_output=True)
    # Keep logs useful without echoing any environment values.
    print("[pipeline stdout tail]\n" + (pipeline.stdout or "")[-7000:])
    if pipeline.returncode:
        print("[pipeline stderr tail]\n" + (pipeline.stderr or "")[-7000:])

    audit_path = REPO / "output" / "audit" / (rid + ".json")
    audit = load_json(audit_path, {})
    upload = ((audit.get("steps") or {}).get("upload") or {})
    topic = ((audit.get("steps") or {}).get("research") or {}).get("topic") or {}
    qa = ((audit.get("steps") or {}).get("media_quality") or {})
    run_record = {
        "run_id": rid,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "success": pipeline.returncode == 0 and bool(upload.get("ok")),
        "topic": str(topic.get("title_hint") or topic.get("title") or "")[:180],
        "title": str(((audit.get("steps") or {}).get("script") or {}).get("title") or "")[:180],
        "video_url": str(upload.get("url") or ""),
        "media_quality_ok": bool(qa.get("ok")),
        "errors": [str(e)[:180] for e in (qa.get("errors") or [])[:5]],
        "gpu": gpu_name,
    }
    memory["runs"] = (memory.get("runs") or [])[-19:] + [run_record]

    # Self-review is constrained to editorial lessons and reliability observations;
    # the model is never allowed to rewrite executable code or secrets.
    review = {}
    try:
        from app.local_ai import ollama_generate
        prompt = (
            "Review this video production result and recent memory. Return ONLY valid JSON with keys "
            "editorial_lessons (array of at most 8 short Persian strings) and observation (one short Persian string). "
            "Suggest only concrete improvements to future scripts, scene variety, source fidelity, or QA. "
            "Never request secrets, network access, code changes, or policy bypasses.\n"
            + json.dumps({"current_run": run_record, "recent_runs": memory["runs"][-5:],
                          "previous_lessons": memory["editorial_lessons"]}, ensure_ascii=False)
        )
        raw = ollama_generate(prompt, system="You are a cautious production-review agent. Output JSON only.", model=model)
        review = json.loads(raw.strip().strip("`"))
        memory["editorial_lessons"] = clean_lessons(review.get("editorial_lessons")) or memory["editorial_lessons"]
        memory["last_observation"] = " ".join(str(review.get("observation") or "").split())[:300]
        print("[agent] Daily self-review completed; memory contains editorial lessons only.")
    except Exception as exc:
        memory["last_observation"] = "Self-review unavailable: " + str(exc)[:240]
        print("[agent] Self-review fallback:", str(exc)[:240])

    memory["updated_at"] = datetime.now(timezone.utc).isoformat()
    MEMORY_OUT.write_text(json.dumps(memory, ensure_ascii=False, indent=2), encoding="utf-8")
    result = {
        **run_record,
        "pipeline_exit_code": pipeline.returncode,
        "self_review": memory.get("last_observation", ""),
        "editorial_lessons": memory["editorial_lessons"],
        "audit_path": str(audit_path),
    }
    RESULT_FILE.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        ollama.terminate()
    except Exception:
        pass
    ollama_log.close()
    if pipeline.returncode != 0 or not upload.get("ok"):
        raise RuntimeError("Pipeline failed or YouTube upload was not confirmed. See result JSON and workflow logs.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        RESULT_FILE.write_text(json.dumps({
            "success": False, "error": str(exc)[:1000],
            "traceback_tail": traceback.format_exc()[-3000:],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        raise
