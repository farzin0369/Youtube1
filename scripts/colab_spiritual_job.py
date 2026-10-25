"""Run the ImamAli110 LTX-only pipeline on a fresh Colab GPU runtime."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import traceback
import zipfile
from datetime import datetime, timezone
from pathlib import Path

SECRETS_FILE = Path("/content/.imamali110-secrets.json")
STATE_ARCHIVE = Path("/content/.imamali110-state.zip")
REPO = Path("/content/Youtube1")
LOG_FILE = Path("/content/ImamAli110-pipeline.log")
RESULT_FILE = Path("/content/ImamAli110-result.json")
OUTPUT_ARCHIVE = Path("/content/ImamAli110-output.zip")
STATE_OUTPUT = Path("/content/ImamAli110-state.zip")


def _read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _run(command: list[str], *, cwd: Path | None = None, env=None, timeout: int = 1800):
    return subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True, timeout=timeout)


def _zip_output(run_id: str) -> None:
    root = REPO / "output" / "spiritual" / run_id
    with zipfile.ZipFile(OUTPUT_ARCHIVE, "w", zipfile.ZIP_DEFLATED) as archive:
        if root.exists():
            for path in root.rglob("*"):
                if path.is_file():
                    archive.write(path, path.relative_to(REPO / "output"))
        if LOG_FILE.exists():
            archive.write(LOG_FILE, "pipeline.log")
        if not root.exists():
            archive.writestr("NO_OUTPUT.txt", "No production output directory was created.")


def _zip_state() -> None:
    state = REPO / "state"
    with zipfile.ZipFile(STATE_OUTPUT, "w", zipfile.ZIP_DEFLATED) as archive:
        if state.exists():
            for path in state.rglob("*"):
                if path.is_file() and path.name in {"history.json", "comment_replies.json"}:
                    archive.write(path, path.relative_to(REPO))


def main() -> int:
    secrets = _read_json(SECRETS_FILE, {})
    SECRETS_FILE.unlink(missing_ok=True)
    kind = str(secrets.get("PRODUCTION_FORMAT") or "shorts").lower()
    if kind not in {"shorts", "long"}:
        raise ValueError("PRODUCTION_FORMAT must be 'shorts' or 'long'")
    upload_private = str(secrets.get("UPLOAD_PRIVATE", "false")).lower() in {"1", "true", "yes"}
    required = ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN")
    missing = [key for key in required if not secrets.get(key)]
    if upload_private and missing:
        raise RuntimeError("Private upload requested but YouTube OAuth settings are missing: " + ", ".join(missing))

    run_token = str(secrets.get("RUN_TOKEN") or secrets.get("GITHUB_RUN_ID") or datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S"))
    run_id = "".join(ch if ch.isalnum() or ch in "_-" else "_" for ch in f"{run_token}_{kind}")[:80]
    ref = str(secrets.get("GIT_REF") or "feat/youtube-agent-skill-integration")
    gpu = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"], text=True, capture_output=True)
    if gpu.returncode or not gpu.stdout.strip():
        raise RuntimeError("Colab runtime has no CUDA GPU; refusing CPU, stock-footage or CogVideoX fallback.")

    os.environ.update({
        "GITHUB_RUN_ID": run_id,
        "PRODUCTION_FORMAT": kind,
        "LOCAL_LLM_MODEL": str(secrets.get("LOCAL_LLM_MODEL") or "qwen2.5:7b"),
        "OLLAMA_BASE_URL": "http://127.0.0.1:11434",
        "OLLAMA_NUM_GPU": "0",
        "OLLAMA_NUM_PREDICT": "4096",
        "OLLAMA_NUM_CTX": "4096",
        "OLLAMA_KEEP_ALIVE": "0",
        "TTS_PROVIDER": "edge-tts",
        "TTS_VOICE": "fa-IR-FaridNeural",
        "VIDEO_ENGINE": "ltx",
        "LTX_MODEL": "Lightricks/LTX-Video",
        "LTX_GENERATION_FPS": "8",
        "LTX_VIDEO_STEPS": str(secrets.get("LTX_VIDEO_STEPS") or "20"),
        "YOUTUBE_CONTAINS_SYNTHETIC_MEDIA": "true",
        "CHANNEL_HISTORY_PATH": "state/history.json",
    })
    for key in required + ("YOUTUBE_ANALYTICS_REFRESH_TOKEN",):
        if secrets.get(key):
            os.environ[key] = str(secrets[key])
    for key in ("GROQ_API_KEY", "LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL", "PEXELS_API_KEY", "ELEVENLABS_API_KEY"):
        os.environ.pop(key, None)

    print(f"[colab-job] GPU={gpu.stdout.strip()} format={kind} upload_private={upload_private}", flush=True)
    print(f"[colab-job] Checking out repository ref {ref}", flush=True)
    if REPO.exists():
        shutil.rmtree(REPO)
    clone = _run(["git", "clone", "--depth", "1", "--branch", ref, "https://github.com/farzin0369/Youtube1.git", str(REPO)], timeout=600)
    if clone.returncode:
        raise RuntimeError("Could not clone requested repository ref: " + (clone.stderr or "")[-1200:])
    os.chdir(REPO)

    if STATE_ARCHIVE.exists():
        state_unpack = _run(["unzip", "-o", str(STATE_ARCHIVE), "-d", str(REPO)], timeout=120)
        STATE_ARCHIVE.unlink(missing_ok=True)
        if state_unpack.returncode:
            raise RuntimeError("Could not restore channel history: " + (state_unpack.stderr or "")[-800:])
    (REPO / "state").mkdir(parents=True, exist_ok=True)
    history = REPO / "state" / "history.json"
    if not history.exists():
        history.write_text('{"recent": []}\n', encoding="utf-8")
    comments = REPO / "state" / "comment_replies.json"
    if not comments.exists():
        comments.write_text('{"replied": {}}\n', encoding="utf-8")

    print("[colab-job] Installing LTX-compatible Python dependencies.", flush=True)
    install = _run([
        sys.executable, "-m", "pip", "install", "-q", "-r", "requirements.txt",
        "diffusers>=0.32,<0.42", "transformers>=4.46,<5", "accelerate>=1.0",
        "safetensors", "imageio-ffmpeg", "sentencepiece",
    ], cwd=REPO, timeout=1800)
    if install.returncode:
        raise RuntimeError("Dependency installation failed: " + (install.stderr or "")[-1800:])
    apt = _run(
        ["bash", "-lc", "apt-get update -qq && apt-get install -y -qq ffmpeg fonts-noto-core fonts-dejavu-core zstd"],
        timeout=600,
    )
    if apt.returncode:
        raise RuntimeError("FFmpeg/font/zstd installation failed: " + (apt.stderr or "")[-1200:])

    if upload_private:
        from app.youtube_client import probe_youtube_auth
        auth = probe_youtube_auth()
        if not auth.get("ok"):
            raise RuntimeError("YouTube OAuth preflight failed; private upload blocked before rendering.")
        print("[colab-job] YouTube OAuth preflight passed.", flush=True)

    if shutil.which("ollama") is None:
        print("[colab-job] Installing the free local Ollama runtime (zstd required for current installer).", flush=True)
        # Official installer needs zstd to unpack its Linux archive on current Colab images.
        install_ollama = _run(
            [
                "bash", "-lc",
                "curl -fL --connect-timeout 15 --max-time 120 https://ollama.com/install.sh -o /tmp/ollama-install.sh "
                "&& bash /tmp/ollama-install.sh",
            ],
            timeout=600,
        )
        if install_ollama.returncode or shutil.which("ollama") is None:
            detail = (install_ollama.stdout or "")[-800:] + "\n" + (install_ollama.stderr or "")[-800:]
            raise RuntimeError("Ollama installation failed: " + detail.strip()[-1200:])

    ollama_log = open("/content/ollama.log", "w", encoding="utf-8")
    ollama_env = os.environ.copy()
    ollama_env["OLLAMA_NUM_GPU"] = "0"
    ollama_env["CUDA_VISIBLE_DEVICES"] = ""
    ollama_env["OLLAMA_KEEP_ALIVE"] = "0"
    ollama = subprocess.Popen(["bash", "-lc", "ollama serve"], stdout=ollama_log, stderr=subprocess.STDOUT, env=ollama_env)
    try:
        ready = False
        for _ in range(60):
            try:
                import urllib.request
                with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=2) as response:
                    ready = response.status == 200
                if ready:
                    break
            except Exception:
                time.sleep(2)
        if not ready:
            raise RuntimeError("Local Ollama did not become ready.")
        model = os.environ["LOCAL_LLM_MODEL"]
        print("[colab-job] Preparing local text model:", model, flush=True)
        pull = _run(["ollama", "pull", model], timeout=1800)
        if pull.returncode:
            raise RuntimeError("Could not pull the local LLM: " + (pull.stderr or "")[-1200:])

        command = [sys.executable, "scripts/daily_run.py", "--format", kind]
        command.append("--upload-private" if upload_private else "--dry-run")
        print("[colab-job] Starting the real ImamAli110 LTX pipeline:", " ".join(command), flush=True)
        with LOG_FILE.open("w", encoding="utf-8") as log:
            process = subprocess.Popen(command, cwd=REPO, env=os.environ.copy(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            assert process.stdout is not None
            for line in process.stdout:
                # The application redacts OAuth values before reporting production errors.
                print(line, end="", flush=True)
                log.write(line)
            exit_code = process.wait()
        success = exit_code == 0
        result = {
            "success": success,
            "run_id": run_id,
            "format": kind,
            "upload_mode": "private" if upload_private else "dry-run",
            "gpu": gpu.stdout.strip(),
            "pipeline_exit_code": exit_code,
            "repository_ref": ref,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "log_path": str(LOG_FILE),
        }
        run_output = REPO / "output" / "spiritual" / run_id / "result.json"
        if run_output.exists():
            result["pipeline_result"] = _read_json(run_output, {})
        RESULT_FILE.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        _zip_output(run_id)
        _zip_state()
        print("[colab-job] Result:", json.dumps(result, ensure_ascii=False), flush=True)
        return 0 if success else (exit_code or 1)
    finally:
        try:
            ollama.terminate()
            ollama.wait(timeout=10)
        except Exception:
            try:
                ollama.kill()
            except Exception:
                pass
        ollama_log.close()


if __name__ == "__main__":
    try:
        exit_code = main()
    except Exception as exc:
        detail = {
            "success": False,
            "error_type": type(exc).__name__,
            "error": str(exc)[:1200],
            "traceback_tail": traceback.format_exc()[-3000:],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        RESULT_FILE.write_text(json.dumps(detail, ensure_ascii=False, indent=2), encoding="utf-8")
        try:
            _zip_output("failed")
            _zip_state()
        except Exception:
            pass
        print("[colab-job] FAILED:", json.dumps(detail, ensure_ascii=False), flush=True)
        raise SystemExit(1)
    raise SystemExit(exit_code)
