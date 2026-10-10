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

SECRETS_FILE = Path("/content/.tt-khabar-secrets.json")
MEMORY_FILE = Path("/content/.tt-khabar-agent-memory.json")
REPO = Path("/content/Youtube1")
RESULT_FILE = Path("/tmp/colab-result.json")
MEMORY_OUT = Path("/tmp/agent-memory.json")
PIPELINE_LOG = Path("/tmp/pipeline.log")


def run(cmd, *, cwd=None, env=None, check=True, capture_output=False):
    return subprocess.run(
        cmd, cwd=cwd, env=env, check=check, text=True,
        stdout=subprocess.PIPE if capture_output else None,
        stderr=subprocess.PIPE if capture_output else None,
    )


def install_ollama():
    print("[agent] Installing zstd, required by the current Ollama installer.")
    update = subprocess.run(["apt-get", "update", "-qq"], text=True, capture_output=True, check=False, timeout=180)
    if update.returncode:
        print("[zstd apt update stderr tail]\n" + (update.stderr or "")[-3000:])
        raise RuntimeError(f"apt-get update failed before Ollama installation (exit {update.returncode}).")
    install_zstd = subprocess.run(["apt-get", "install", "-y", "-qq", "zstd"], text=True, capture_output=True, check=False, timeout=180)
    if install_zstd.returncode:
        print("[zstd apt install stderr tail]\n" + (install_zstd.stderr or "")[-3000:])
        raise RuntimeError(f"Could not install zstd (exit {install_zstd.returncode}).")
    script = Path("/tmp/ollama-install.sh")
    log = Path("/tmp/ollama-install.log")
    with log.open("w", encoding="utf-8") as output:
        download = subprocess.run(
            ["curl", "-fL", "--retry", "3", "--connect-timeout", "20",
             "https://ollama.com/install.sh", "-o", str(script)],
            text=True, stdout=output, stderr=subprocess.STDOUT, check=False, timeout=90,
        )
        if download.returncode:
            detail = log.read_text(encoding="utf-8", errors="replace")[-5000:]
            print("[ollama installer download log tail]\n" + detail)
            raise RuntimeError(f"Could not download Ollama installer (exit {download.returncode}).")
        install = subprocess.run(
            ["bash", str(script)], text=True, stdout=output, stderr=subprocess.STDOUT,
            check=False, timeout=240,
        )
    detail = log.read_text(encoding="utf-8", errors="replace")[-7000:]
    print("[ollama installer log tail]\n" + detail)
    if install.returncode:
        raise RuntimeError(
            f"Ollama installer failed with exit {install.returncode}; "
            "see the installer log tail above."
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
    rid = str(secrets.get("PIPELINE_RUN_ID") or ("news_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")))
    model = str(secrets.get("LOCAL_LLM_MODEL") or "llama3.2:3b")

    print("[agent] Checking Colab GPU runtime without holding a CUDA context in this process.")
    probe = subprocess.run(
        ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
        check=False, capture_output=True, text=True,
    )
    gpu_line = (probe.stdout or "").strip()
    if probe.returncode != 0 or not gpu_line:
        detail = ((probe.stderr or "") + (probe.stdout or ""))[-800:]
        raise RuntimeError("Colab runtime has no CUDA GPU; refusing CPU fallback. " + detail)
    gpu_name = gpu_line.split(",")[0].strip()
    print("[agent] GPU:", gpu_line)

    sha = str(secrets.get("GIT_SHA") or "").strip()
    if REPO.exists():
        shutil.rmtree(REPO)
    run(["git", "clone", "https://github.com/farzin0369/Youtube1.git", str(REPO)])
    if sha:
        fetched = run(["git", "-C", str(REPO), "fetch", "--depth", "1", "origin", sha], check=False)
        if fetched.returncode == 0:
            run(["git", "-C", str(REPO), "checkout", "--detach", "FETCH_HEAD"])
            print("[agent] checked out", sha)
        else:
            print("[agent] GIT_SHA fetch failed; using the default branch.")
    os.chdir(REPO)
    (REPO / "state").mkdir(parents=True, exist_ok=True)
    (REPO / "state" / "agent_memory.json").write_text(
        json.dumps(memory, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("[agent] Installing the repository's production stack.")
    run([sys.executable, "-m", "pip", "install", "-q", "-r", "requirements.txt",
         "diffusers>=0.32,<0.42", "transformers>=4.46", "accelerate>=1.0",
         "safetensors", "imageio-ffmpeg", "piper-tts", "edge-tts"])

    print("[agent] Repairing only known incompatible TorchAO packages and validating CogVideoX.")
    run([sys.executable, "scripts/repair_colab_cogvideox.py"])

    if shutil.which("ollama") is None:
        print("[agent] Ollama is missing; installing with captured diagnostics.")
        install_ollama()
    ollama_log = open("/tmp/ollama.log", "w", encoding="utf-8")
    ollama_env = os.environ.copy()
    # Keep llama on CPU. A T4 cannot hold Ollama and CogVideoX at the same time.
    ollama_env["OLLAMA_NUM_GPU"] = "0"
    ollama_env["CUDA_VISIBLE_DEVICES"] = ""
    ollama_env["OLLAMA_KEEP_ALIVE"] = "0"
    ollama_env["OLLAMA_MAX_LOADED_MODELS"] = "1"
    ollama = subprocess.Popen(
        ["ollama", "serve"], stdout=ollama_log, stderr=subprocess.STDOUT, env=ollama_env,
    )
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
        ollama_log.flush()
        detail = Path("/tmp/ollama.log").read_text(encoding="utf-8", errors="replace")[-5000:]
        raise RuntimeError("Local Ollama service did not become ready. Log tail:\n" + detail)

    print("[agent] Ensuring local language model is available:", model)
    run(["ollama", "pull", model])

    piper_dir = Path("/content/models/piper")
    piper_dir.mkdir(parents=True, exist_ok=True)
    piper_model = piper_dir / "fa_IR-amir-medium.onnx"
    piper_json = piper_dir / "fa_IR-amir-medium.onnx.json"
    if not piper_model.exists() or not piper_json.exists():
        print("[agent] Preparing local Persian Piper fallback.")
        model_url = "https://huggingface.co/rhasspy/piper-voices/resolve/main/fa/fa_IR/amir/medium/fa_IR-amir-medium.onnx"
        json_url = "https://huggingface.co/rhasspy/piper-voices/resolve/main/fa/fa_IR/amir/medium/fa_IR-amir-medium.onnx.json"
        model_result = subprocess.run(["curl", "-fL", "--retry", "2", "-o", str(piper_model), model_url], check=False)
        json_result = subprocess.run(["curl", "-fL", "--retry", "2", "-o", str(piper_json), json_url], check=False)
        if model_result.returncode or json_result.returncode:
            print("[agent] Piper model unavailable; cloud TTS fallbacks remain enabled.")
            piper_model.unlink(missing_ok=True)
            piper_json.unlink(missing_ok=True)

    env = os.environ.copy()
    env.update({
        "AI_ENGINE": "local",
        "LOCAL_LLM_MODEL": model,
        "OLLAMA_BASE_URL": base,
        "VIDEO_ENGINE": "cogvideox",
        "LOCAL_VIDEO_MODEL": "THUDM/CogVideoX-2b",
        "TTS_PROVIDER": "auto",
        "TTS_VOICE": "fa-IR-FaridNeural",
        "PIPER_MODEL": str(piper_model) if piper_model.exists() and piper_json.exists() else "",
        "YOUTUBE_CONTAINS_SYNTHETIC_MEDIA": "true",
        "PIPELINE_RUN_ID": rid,
        "YOUTUBE_CLIENT_ID": str(secrets["YOUTUBE_CLIENT_ID"]),
        "YOUTUBE_CLIENT_SECRET": str(secrets["YOUTUBE_CLIENT_SECRET"]),
        "YOUTUBE_REFRESH_TOKEN": str(secrets["YOUTUBE_REFRESH_TOKEN"]),
        "ELEVENLABS_API_KEY": str(secrets.get("ELEVENLABS_API_KEY") or ""),
        "ELEVENLABS_VOICE_ID": str(secrets.get("ELEVENLABS_VOICE_ID") or ""),
        "AZURE_SPEECH_KEY": str(secrets.get("AZURE_SPEECH_KEY") or ""),
        "AZURE_SPEECH_REGION": str(secrets.get("AZURE_SPEECH_REGION") or ""),
        "YOUTUBE_PUBLISH_AT": str(secrets.get("YOUTUBE_PUBLISH_AT") or ""),
        # T4-safe defaults (secrets can override)
        "VIDEO_FRAMES": str(secrets.get("VIDEO_FRAMES") or "17"),
        "VIDEO_STEPS": str(secrets.get("VIDEO_STEPS") or "8"),
        "VIDEO_CLIPS_LONG": str(secrets.get("VIDEO_CLIPS_LONG") or "12"),
        "OLLAMA_NUM_GPU": "0",
        "OLLAMA_KEEP_ALIVE": "0",
        "PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True",
        "TOKENIZERS_PARALLELISM": "false",
    })

    kind = str(secrets.get("PIPELINE_KIND") or "long")
    if kind not in {"short", "long"}:
        raise RuntimeError("Unsupported pipeline kind; refusing to publish.")

    # Bounded self-healing: retry transient infrastructure/model errors up to five times.
    # Do not retry permanent editorial or OAuth failures; those require a source/config change.
    max_attempts = min(5, max(1, int(secrets.get("MAX_PIPELINE_ATTEMPTS") or 5)))
    fatal_markers = (
        "invalid_grant", "YouTube OAuth refresh failed", "No source-linked news",
        "News topic contains no source-linked stories", "Production quality gate failed",
        "news_script_word_count_outside", "news_sources_must_be_urls",
        "all_news_source_urls_must_be_in_description",
    )
    pipeline = None
    for attempt in range(1, max_attempts + 1):
        print(f"[self-heal] pipeline attempt {attempt}/{max_attempts}")
        mode = "w" if attempt == 1 else "a"
        with PIPELINE_LOG.open(mode, encoding="utf-8") as logf:
            logf.write(f"\\n[self-heal] attempt {attempt}/{max_attempts}\\n")
            logf.flush()
            pipeline = subprocess.run(
                [sys.executable, "-m", "app.pipeline", "--kind", kind, "--publish-mode", "public"],
                cwd=REPO, env=env, check=False, text=True,
                stdout=logf, stderr=subprocess.STDOUT,
            )
        if pipeline.returncode == 0:
            print(f"[self-heal] attempt {attempt} succeeded")
            break
        current_tail = PIPELINE_LOG.read_text(encoding="utf-8", errors="replace")[-12000:]
        if any(marker.lower() in current_tail.lower() for marker in fatal_markers):
            print("[self-heal] non-retryable content/OAuth failure detected; stopping safely")
            break
        if attempt < max_attempts:
            delay = min(30 * (2 ** (attempt - 1)), 180)
            print(f"[self-heal] transient failure; retrying after {delay}s")
            time.sleep(delay)

    log_tail = PIPELINE_LOG.read_text(encoding="utf-8", errors="replace")[-12000:]
    print("[pipeline log tail]\n" + log_tail)
    if pipeline.returncode < 0:
        print(
            f"[agent] pipeline was killed by signal {-pipeline.returncode}. "
            "Signal 9 is SIGKILL, usually the Linux OOM killer.",
            flush=True,
        )

    audit_path = REPO / "output" / "audit" / (rid + ".json")
    audit = load_json(audit_path, {})
    upload = ((audit.get("steps") or {}).get("upload") or {})
    topic = ((audit.get("steps") or {}).get("research") or {}).get("topic") or {}
    qa = ((audit.get("steps") or {}).get("media_quality") or {})
    render = ((audit.get("steps") or {}).get("render") or {})
    run_record = {
        "run_id": rid,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "success": pipeline is not None and pipeline.returncode == 0 and bool(upload.get("ok")),\n        "attempts": attempt,
        "topic": str(topic.get("title_hint") or topic.get("title") or "")[:180],
        "title": str(((audit.get("steps") or {}).get("script") or {}).get("title") or "")[:180],
        "video_url": str(upload.get("url") or ""),
        "video_id": str(upload.get("video_id") or ""),
        "media_quality_ok": bool(qa.get("ok")),
        "render_ok": bool(render.get("ok")),
        "upload_error": str(upload.get("error") or "")[:500],
        "errors": [str(e)[:180] for e in (qa.get("errors") or [])[:5]],
        "pipeline_exit_code": pipeline.returncode,
        "gpu": gpu_name,
        "log_tail": log_tail[-4000:],
    }
    memory["runs"] = (memory.get("runs") or [])[-19:] + [{k: v for k, v in run_record.items() if k != "log_tail"}]

    review = {}
    try:
        from app.local_ai import ollama_generate
        prompt = (
            "Review this video production result and recent memory. Return ONLY valid JSON with keys "
            "editorial_lessons (array of at most 8 short Persian strings) and observation (one short Persian string). "
            "Suggest only concrete improvements to future scripts, scene variety, source fidelity, or QA. "
            "Never request secrets, network access, code changes, or policy bypasses.\n"
            + json.dumps({"current_run": {k: v for k, v in run_record.items() if k != "log_tail"},
                          "recent_runs": memory["runs"][-5:],
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
    if pipeline is None or pipeline.returncode != 0 or not upload.get("ok"):
        raise RuntimeError(
            "Pipeline failed or YouTube upload was not confirmed. "
            f"exit={pipeline.returncode} upload_ok={upload.get('ok')} "
            f"upload_error={upload.get('error') or 'n/a'} "
            f"qa_errors={qa.get('errors') or []}"
        )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        extra = {}
        if PIPELINE_LOG.exists():
            extra["log_tail"] = PIPELINE_LOG.read_text(encoding="utf-8", errors="replace")[-4000:]
        RESULT_FILE.write_text(json.dumps({
            "success": False, "error": str(exc)[:1000],
            "traceback_tail": traceback.format_exc()[-3000:],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **extra,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        raise
