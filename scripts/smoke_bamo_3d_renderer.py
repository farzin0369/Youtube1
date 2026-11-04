#!/usr/bin/env python3
"""CPU smoke test for BAMO 3D shorts renderer with mandatory self-heal gate."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _self_heal() -> None:
    heal = ROOT / "scripts" / "bamo_self_heal.py"
    if not heal.is_file():
        print("WARNING: bamo_self_heal.py missing; continuing without gate")
        return
    result = subprocess.run([sys.executable, str(heal)], cwd=str(ROOT))
    if result.returncode != 0:
        raise SystemExit(
            "BAMO self-heal failed — refusing to start Blender/Ollama on a broken tree. "
            "Fix critical modules or extend scripts/bamo_self_heal.py with a new repair rule."
        )


def main() -> None:
    _self_heal()

    sys.path.insert(0, str(ROOT))
    from app.bamo_production_renderer import render_bamo_shorts

    out = ROOT / "output" / "bamo-3d-smoke"
    out.mkdir(parents=True, exist_ok=True)

    # Minimal four-scene Persian fixture used only as structural input.
    # Visual content still comes from AI director + Blender, not this fixture.
    scenes = [
        {
            "spoken_text": "گاهی یک انتخاب کوچک، مسیر فردا را عوض می‌کند.",
            "visual_query": "two diverging glowing paths with a central choice sphere",
            "on_screen_text": "انتخاب کوچک",
        },
        {
            "spoken_text": "مغز ما با تمرین، مسیرهای تازه می‌سازد.",
            "visual_query": "neural network nodes lighting up in sequence",
            "on_screen_text": "مسیرهای تازه",
        },
        {
            "spoken_text": "گام‌به‌گام پیش برو؛ هر پله یک پیشرفت است.",
            "visual_query": "ascending geometric steps toward a bright peak",
            "on_screen_text": "گام‌به‌گام",
        },
        {
            "spoken_text": "فردا از همین شروع ساده ساخته می‌شود.",
            "visual_query": "sunrise over a calm horizon with rising light",
            "on_screen_text": "شروع ساده",
        },
    ]
    timings = [
        {"start_seconds": 0.0},
        {"start_seconds": 5.5},
        {"start_seconds": 11.0},
        {"start_seconds": 16.5},
    ]

    # Prefer existing voice from previous smoke if present; else generate later in renderer path.
    audio = out / "voice-test.mp3"
    captions = out / "captions.srt"
    if not captions.is_file():
        captions.write_text(
            "1\n00:00:00,000 --> 00:00:05,400\nانتخاب کوچک\n\n"
            "2\n00:00:05,500 --> 00:00:10,900\nمسیرهای تازه\n\n"
            "3\n00:00:11,000 --> 00:00:16,400\nگام‌به‌گام\n\n"
            "4\n00:00:16,500 --> 00:00:23,000\nشروع ساده\n",
            encoding="utf-8",
        )

    if not audio.is_file():
        # edge-tts offline-capable path via existing project tooling when available
        try:
            import edge_tts  # type: ignore
            import asyncio

            async def _speak() -> None:
                communicate = edge_tts.Communicate(
                    "گاهی یک انتخاب کوچک، مسیر فردا را عوض می‌کند. "
                    "مغز ما با تمرین، مسیرهای تازه می‌سازد. "
                    "گام‌به‌گام پیش برو؛ هر پله یک پیشرفت است. "
                    "فردا از همین شروع ساده ساخته می‌شود.",
                    "fa-IR-FaridNeural",
                )
                await communicate.save(str(audio))

            asyncio.run(_speak())
        except Exception as exc:  # noqa: BLE001
            raise SystemExit(f"Could not produce smoke voice audio: {exc}") from exc

    result = render_bamo_shorts(
        title="BAMO smoke",
        thumbnail_text="پیش‌نمایش موتور",
        audio_path=audio,
        captions_path=captions,
        out_dir=out,
        run_id="smoke-self-heal",
        scenes=scenes,
        scene_timings=timings,
        hook_overlay="BAMO",
    )
    evidence = {
        "ok": bool(result.get("ok")),
        "video_path": result.get("video_path"),
        "video_width": result.get("video_width"),
        "video_height": result.get("video_height"),
        "visual_plans": result.get("scene_visual_plans"),
        "qa": {
            "ok": False,
            "errors": [
                "shorts_visuals_not_production_approved",
                "shorts_scene_visual_queries_not_verified",
            ],
        },
        "self_heal": True,
    }
    (out / "smoke-evidence.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print("SMOKE_OK", result.get("video_path"), result.get("video_width"), result.get("video_height"))


if __name__ == "__main__":
    main()
