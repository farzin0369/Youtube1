#!/usr/bin/env python3
"""
BAMO OpenMontage Autonomous Runner (experimental)
-------------------------------------------------
Stage-oriented runner for English vertical Shorts.

This is the first autonomous layer on top of OpenMontage structure:
1. Select idea (Content Intelligence)
2. Write OpenMontage-compatible project (adapter)
3. Synthesize English narration (edge-tts / future Piper)
4. Compose provisional vertical 9:16 video (FFmpeg)
5. Write checkpoint + QC summary

It does NOT yet fully execute every OpenMontage stage-director skill
interactively. That remains the next hardening step. This runner exists so
we have a real, resumable, English-first path that is aligned with
OpenMontage as the central system (not Wan).
"""
from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "bamo_om_runs"


def run(cmd: list[str], timeout: int = 300) -> None:
    print("+" , " ".join(cmd), flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout)[-2000:])


def stage_select_idea() -> dict[str, Any]:
    sys.path.insert(0, str(ROOT))
    from app.content_intelligence import daily_brief
    brief = daily_brief()
    if "error" in brief:
        raise RuntimeError(brief["error"])
    return brief


def stage_adapter(idea_id: str) -> Path:
    from scripts.bamo_openmontage_adapter import load_idea, write_project
    idea = load_idea(idea_id)
    project_dir = write_project(idea, out_dir=OUT / "projects")
    return project_dir


def stage_tts(narration: str, audio_path: Path) -> float:
    import edge_tts

    async def _save() -> None:
        communicate = edge_tts.Communicate(narration.strip(), voice="en-US-GuyNeural", rate="+3%")
        await communicate.save(str(audio_path))

    asyncio.run(_save())
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)],
        capture_output=True, text=True,
    )
    return float(probe.stdout.strip() or "25")


def stage_compose(audio_path: Path, duration: float, title: str, out_mp4: Path) -> None:
    """Provisional kinetic vertical compose. Replace with full OpenMontage compose later."""
    # Four simple scenes with brand lock
    d1, d2, d3, d4 = 5.5, 8.0, 8.0, max(6.0, duration - 21.5)
    run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c=0x050510:s=1080x1920:d={d1}",
        "-f", "lavfi", "-i", f"color=c=0x0a1228:s=1080x1920:d={d2}",
        "-f", "lavfi", "-i", f"color=c=0x121008:s=1080x1920:d={d3}",
        "-f", "lavfi", "-i", f"color=c=0x0a1a14:s=1080x1920:d={d4}",
        "-i", str(audio_path),
        "-filter_complex",
        "[0:v]drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:text='BAMO':fontsize=40:fontcolor=white@0.45:x=48:y=72,"
        "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='@12bamo':fontsize=28:fontcolor=white@0.35:x=48:y=125,"
        f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:text='{title[:40]}':fontsize=44:fontcolor=white:x=(w-text_w)/2:y=720,"
        "fade=t=out:st=4.7:d=0.8[v0];"
        "[1:v]drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:text='English Shorts':fontsize=48:fontcolor=white:x=(w-text_w)/2:y=700,"
        "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='OpenMontage path':fontsize=36:fontcolor=0xaaccff:x=(w-text_w)/2:y=800,"
        "fade=t=in:st=0:d=0.5,fade=t=out:st=7.2:d=0.8[v1];"
        "[2:v]drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:text='BAMO':fontsize=56:fontcolor=0xffaa33:x=(w-text_w)/2:y=720,"
        "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='@12bamo':fontsize=40:fontcolor=white:x=(w-text_w)/2:y=820,"
        "fade=t=in:st=0:d=0.5,fade=t=out:st=7.2:d=0.8[v2];"
        "[3:v]drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:text='Autonomous Studio':fontsize=48:fontcolor=0x55ff99:x=(w-text_w)/2:y=700,"
        "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='BAMO  ·  @12bamo':fontsize=30:fontcolor=white@0.45:x=(w-text_w)/2:y=h-130,"
        "fade=t=in:st=0:d=0.5[v3];"
        "[v0][v1][v2][v3]concat=n=4:v=1:a=0[vout]",
        "-map", "[vout]", "-map", "4:a",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart",
        str(out_mp4),
    ], timeout=180)


def stage_qc(mp4: Path) -> dict[str, Any]:
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "stream=codec_type,codec_name,width,height:format=duration,size",
         "-of", "json", str(mp4)],
        capture_output=True, text=True,
    )
    data = json.loads(probe.stdout or "{}")
    streams = data.get("streams") or []
    video = next((s for s in streams if s.get("codec_type") == "video"), {})
    audio = next((s for s in streams if s.get("codec_type") == "audio"), {})
    duration = float((data.get("format") or {}).get("duration") or 0)
    size = int((data.get("format") or {}).get("size") or 0)
    ok = (
        video.get("width") == 1080
        and video.get("height") == 1920
        and audio.get("codec_name") in {"aac", "mp3"}
        and 18 <= duration <= 35
        and size > 100_000
    )
    return {
        "ok": ok,
        "width": video.get("width"),
        "height": video.get("height"),
        "duration": duration,
        "size": size,
        "video_codec": video.get("codec_name"),
        "audio_codec": audio.get("codec_name"),
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_dir = OUT / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    print("[1/5] select idea", flush=True)
    brief = stage_select_idea()
    idea_id = brief["selected_idea_id"]
    (run_dir / "brief.json").write_text(json.dumps(brief, indent=2, ensure_ascii=False), encoding="utf-8")

    print("[2/5] adapter project", flush=True)
    project_dir = stage_adapter(idea_id)

    print("[3/5] English TTS", flush=True)
    audio = run_dir / "narration.mp3"
    duration = stage_tts(brief.get("narration") or "", audio)

    print("[4/5] compose vertical short", flush=True)
    out_mp4 = run_dir / "final_short.mp4"
    stage_compose(audio, duration, brief.get("title") or "BAMO Short", out_mp4)

    print("[5/5] QC", flush=True)
    qc = stage_qc(out_mp4)
    (run_dir / "qc.json").write_text(json.dumps(qc, indent=2), encoding="utf-8")

    result = {
        "run_id": run_id,
        "idea_id": idea_id,
        "title": brief.get("title"),
        "project_dir": str(project_dir),
        "output": str(out_mp4),
        "qc": qc,
        "engine": "bamo-openmontage-runner-v0 (provisional compose)",
        "note": "Full OpenMontage stage-director execution still pending",
    }
    (run_dir / "result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if qc.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
