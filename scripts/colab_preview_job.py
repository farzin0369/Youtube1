"""Colab GPU quality preview: cinematic render only, no YouTube upload.
Copies final MP4 + thumbnail + script to /tmp for GitHub artifact download.
"""
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
REPO = Path("/content/Youtube1")
RESULT_FILE = Path("/tmp/colab-result.json")
PIPELINE_LOG = Path("/tmp/pipeline.log")
PREVIEW_DIR = Path("/tmp/preview")


def run(cmd, *, cwd=None, env=None, check=True, capture_output=False):
    return subprocess.run(
        cmd, cwd=cwd, env=env, check=check, text=True,
        stdout=subprocess.PIPE if capture_output else None,
        stderr=subprocess.PIPE if capture_output else None,
    )


def install_ollama():
    print("[preview] Installing zstd for Ollama installer.")
    subprocess.run(["apt-get", "update", "-qq"], check=False, timeout=180)
    subprocess.run(["apt-get", "install", "-y", "-qq", "zstd"], check=False, timeout=180)
    script = Path("/tmp/ollama-install.sh")
    log = Path("/tmp/ollama-install.log")
    with log.open("w", encoding="utf-8") as output:
        download = subprocess.run(
            ["curl", "-fL", "--retry", "3", "--connect-timeout", "20",
             "https://ollama.com/install.sh", "-o", str(script)],
            text=True, stdout=output, stderr=subprocess.STDOUT, check=False, timeout=90,
        )
        if download.returncode:
            raise RuntimeError("Could not download Ollama installer.")
        install = subprocess.run(
            ["bash", str(script)], text=True, stdout=output, stderr=subprocess.STDOUT,
            check=False, timeout=240,
        )
    if install.returncode:
        detail = log.read_text(encoding="utf-8", errors="replace")[-5000:]
        raise RuntimeError("Ollama installer failed:\n" + detail)


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def main():
    secrets = load_json(SECRETS_FILE, {})
    rid = str(secrets.get("PIPELINE_RUN_ID") or ("preview_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")))
    model = str(secrets.get("LOCAL_LLM_MODEL") or "llama3.2:3b")

    print("[preview] Checking GPU.")
    probe = subprocess.run(
        ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
        check=False, capture_output=True, text=True,
    )
    gpu_line = (probe.stdout or "").strip()
    if probe.returncode != 0 or not gpu_line:
        raise RuntimeError("No CUDA GPU; refusing CPU fallback.")
    gpu_name = gpu_line.split(",")[0].strip()
    print("[preview] GPU:", gpu_line)

    sha = str(secrets.get("GIT_SHA") or "").strip()
    if REPO.exists():
        shutil.rmtree(REPO)
    run(["git", "clone", "https://github.com/farzin0369/Youtube1.git", str(REPO)])
    if sha:
        fetched = run(["git", "-C", str(REPO), "fetch", "--depth", "1", "origin", sha], check=False)
        if fetched.returncode == 0:
            run(["git", "-C", str(REPO), "checkout", "--detach", "FETCH_HEAD"])
            print("[preview] checked out", sha)
    os.chdir(REPO)

    print("[preview] Installing production stack.")
    run([sys.executable, "-m", "pip", "install", "-q", "-r", "requirements.txt",
         "diffusers>=0.32,<0.42", "transformers>=4.46", "accelerate>=1.0",
         "safetensors", "imageio-ffmpeg", "piper-tts", "edge-tts"])
    run([sys.executable, "scripts/repair_colab_cogvideox.py"])

    if shutil.which("ollama") is None:
        install_ollama()
    ollama_log = open("/tmp/ollama.log", "w", encoding="utf-8")
    ollama_env = os.environ.copy()
    ollama_env["OLLAMA_NUM_GPU"] = "0"
    ollama_env["CUDA_VISIBLE_DEVICES"] = ""
    ollama_env["OLLAMA_KEEP_ALIVE"] = "0"
    ollama_env["OLLAMA_MAX_LOADED_MODELS"] = "1"
    ollama = subprocess.Popen(["ollama", "serve"], stdout=ollama_log, stderr=subprocess.STDOUT, env=ollama_env)
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
        raise RuntimeError("Ollama did not become ready.")
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
        "VIDEO_FRAMES": str(secrets.get("VIDEO_FRAMES") or "17"),
        "VIDEO_STEPS": str(secrets.get("VIDEO_STEPS") or "8"),
        "VIDEO_CLIPS_SHORT": str(secrets.get("VIDEO_CLIPS_SHORT") or "3"),
        "OLLAMA_NUM_GPU": "0",
        "OLLAMA_KEEP_ALIVE": "0",
        "PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True",
        "TOKENIZERS_PARALLELISM": "false",
    })

    print("[preview] Starting pipeline with --dry-run (no YouTube upload).")
    with PIPELINE_LOG.open("w", encoding="utf-8") as logf:
        pipeline = subprocess.run(
            [sys.executable, "-m", "app.pipeline", "--kind", "short", "--publish-mode", "private", "--dry-run"],
            cwd=REPO, env=env, check=False, text=True,
            stdout=logf, stderr=subprocess.STDOUT,
        )
    log_tail = PIPELINE_LOG.read_text(encoding="utf-8", errors="replace")[-12000:]
    print("[pipeline log tail]\n" + log_tail)

    audit_path = REPO / "output" / "audit" / (rid + ".json")
    audit = load_json(audit_path, {})
    qa = ((audit.get("steps") or {}).get("media_quality") or {})
    render = ((audit.get("steps") or {}).get("render") or {})
    script_step = ((audit.get("steps") or {}).get("script") or {})

    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    video_src = Path(render.get("video_path") or "")
    thumb_src = Path(render.get("thumbnail_path") or "")
    out_run = REPO / "output" / rid
    copied = []
    if video_src.exists() and video_src.stat().st_size > 1024:
        dest = PREVIEW_DIR / "video.mp4"
        shutil.copy2(video_src, dest)
        copied.append(str(dest))
        print("[preview] video copied:", dest, dest.stat().st_size, "bytes")
    if thumb_src.exists():
        dest = PREVIEW_DIR / "thumbnail.jpg"
        shutil.copy2(thumb_src, dest)
        copied.append(str(dest))
    script_txt = out_run / "script.txt"
    if script_txt.exists():
        shutil.copy2(script_txt, PREVIEW_DIR / "script.txt")
        copied.append(str(PREVIEW_DIR / "script.txt"))
    scene_plan = out_run / "scene_plan.json"
    if not scene_plan.exists():
        scene_plan = out_run / "ai_video_scene_plan.json"
    # also try under video parent
    if video_src.exists():
        sp = video_src.with_name("scene_plan.json")
        if sp.exists():
            shutil.copy2(sp, PREVIEW_DIR / "scene_plan.json")
            copied.append(str(PREVIEW_DIR / "scene_plan.json"))

    success = pipeline.returncode == 0 and bool(render.get("ok")) and bool(qa.get("ok"))
    result = {
        "success": success,
        "mode": "quality_preview_dry_run",
        "run_id": rid,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "title": str(script_step.get("title") or "")[:180],
        "render_ok": bool(render.get("ok")),
        "media_quality_ok": bool(qa.get("ok")),
        "pipeline_exit_code": pipeline.returncode,
        "gpu": gpu_name,
        "video_path": str(PREVIEW_DIR / "video.mp4") if (PREVIEW_DIR / "video.mp4").exists() else "",
        "video_bytes": (PREVIEW_DIR / "video.mp4").stat().st_size if (PREVIEW_DIR / "video.mp4").exists() else 0,
        "copied_files": copied,
        "duration": render.get("duration"),
        "provider": render.get("provider"),
        "errors": [str(e)[:180] for e in (qa.get("errors") or [])[:5]],
        "log_tail": log_tail[-3000:],
    }
    RESULT_FILE.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        ollama.terminate()
    except Exception:
        pass
    ollama_log.close()

    if not success:
        raise RuntimeError(
            f"Preview render failed. exit={pipeline.returncode} "
            f"render_ok={render.get('ok')} qa_ok={qa.get('ok')} "
            f"errors={qa.get('errors') or []}"
        )
    print("[preview] SUCCESS — video ready at /tmp/preview/video.mp4")


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
