#!/usr/bin/env python3
"""Modern GPU story-short — CogVideoX-2B, Colab-T4 safe (fast settings).
Fewer frames/steps/beats so free Colab does not drop the connection.
"""
from __future__ import annotations

import argparse
import asyncio
import gc
import json
import subprocess
import sys
import traceback
from pathlib import Path
from typing import Any

# 3 beats only — reliable on free Colab; expand later once stable
DEFAULT_STORY: dict[str, Any] = {
    "id": "sapling_cogvideox_fast",
    "voice": "fa-IR-FaridNeural",
    "rate": "-10%",
    "beats": [
        {
            "line": "روزی مردی به کودکی گفت: این نهال کی سایه می‌ده؟",
            "prompt": (
                "Cinematic shot clear water pouring from metal watering can onto tiny green "
                "seedling dry earth golden sunrise photoreal nature documentary"
            ),
        },
        {
            "line": "کودک گفت: من هم زیر سایه‌ی درختی نشستم که کسی پیش از من کاشته بود.",
            "prompt": (
                "Camera slowly tilting up massive ancient oak tree sunlight through leaves "
                "peaceful park deep green canopy cinematic photoreal"
            ),
        },
        {
            "line": "خوبی کن؛ شاید روزی سایه‌اش به غریبه‌ای برسد.",
            "prompt": (
                "Cinematic wide shot people planting young tree golden hour soft wind "
                "hopeful warm color grade photoreal documentary"
            ),
        },
    ],
}

NEG = "blurry, distorted, jittery, deformed, text, watermark, logo, low quality, cartoon, anime"

# Fast settings for free Colab T4 stability
NUM_FRAMES = 25
NUM_STEPS = 20
GUIDANCE = 6.0
FPS = 8


def run(cmd: list[str], timeout: int = 300) -> None:
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout)[-2000:])


def media_duration(path: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True,
    )
    return float(r.stdout.strip() or "0")


def ensure_deps() -> None:
    print("[engine] deps", flush=True)
    subprocess.call([sys.executable, "-m", "pip", "uninstall", "-y", "torchao"], stdout=subprocess.DEVNULL)
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", "-q", "--upgrade",
        "torchao>=0.7.0",
        "diffusers==0.32.2",
        "transformers==4.46.3",
        "accelerate", "sentencepiece",
        "imageio", "imageio-ffmpeg", "edge-tts", "nest_asyncio", "protobuf",
    ])


def run_async(coro):
    import nest_asyncio
    nest_asyncio.apply()
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


async def tts(text: str, out: Path, voice: str, rate: str) -> None:
    import edge_tts
    await edge_tts.Communicate(text, voice, rate=rate, volume="+28%").save(str(out))


def load_story(path: str | None) -> dict[str, Any]:
    if path and Path(path).is_file():
        return json.loads(Path(path).read_text(encoding="utf-8"))
    return DEFAULT_STORY


def generate_clip(pipe, prompt: str, out: Path, seed: int) -> None:
    import torch
    from diffusers.utils import export_to_video
    print(f"[t2v] frames={NUM_FRAMES} steps={NUM_STEPS} | {prompt[:70]}...", flush=True)
    gc.collect()
    torch.cuda.empty_cache()
    video = pipe(
        prompt=prompt,
        negative_prompt=NEG,
        num_videos_per_prompt=1,
        num_inference_steps=NUM_STEPS,
        num_frames=NUM_FRAMES,
        guidance_scale=GUIDANCE,
        generator=torch.Generator(device="cpu").manual_seed(seed),
    ).frames[0]
    export_to_video(video, str(out), fps=FPS)
    print(f"[t2v] ok {out.stat().st_size // 1024}KB", flush=True)


def to_vertical(src: Path, dst: Path, duration: float) -> None:
    run([
        "ffmpeg", "-y", "-stream_loop", "-1", "-i", str(src),
        "-t", f"{duration:.3f}",
        "-vf", "scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,eq=contrast=1.06:saturation=1.05",
        "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "16", "-pix_fmt", "yuv420p", str(dst),
    ], timeout=120)


def render(story: dict[str, Any], out_path: Path, work: Path) -> dict[str, Any]:
    ensure_deps()
    work.mkdir(parents=True, exist_ok=True)
    clip_dir = work / "clips"
    audio_dir = work / "audio"
    clip_dir.mkdir(exist_ok=True)
    audio_dir.mkdir(exist_ok=True)

    import torch
    from diffusers import CogVideoXPipeline

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA GPU required")
    print("[engine] gpu", torch.cuda.get_device_name(0), flush=True)

    pipe = CogVideoXPipeline.from_pretrained("THUDM/CogVideoX-2b", torch_dtype=torch.float16)
    pipe.enable_model_cpu_offload()
    pipe.vae.enable_slicing()
    pipe.vae.enable_tiling()

    beats = story["beats"]
    voice = story.get("voice", "fa-IR-FaridNeural")
    rate = story.get("rate", "-10%")
    segs: list[Path] = []
    captions: list[tuple[float, float, str]] = []
    t0 = 0.0

    for i, beat in enumerate(beats):
        print(f"=== beat {i+1}/{len(beats)} ===", flush=True)
        raw = audio_dir / f"a{i:02d}_raw.mp3"
        ap = audio_dir / f"a{i:02d}.mp3"
        run_async(tts(beat["line"], raw, voice, rate))
        run(["ffmpeg", "-y", "-i", str(raw), "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000", "-ac", "1", str(ap)], timeout=60)
        dur = max(3.0, media_duration(ap))
        vis = dur + 0.15

        raw_vid = clip_dir / f"raw_{i:02d}.mp4"
        generate_clip(pipe, beat["prompt"], raw_vid, seed=42 + i * 11)
        # checkpoint after each scene
        print(f"[ckpt] scene {i+1} video ready", flush=True)

        vclip = clip_dir / f"v{i:02d}.mp4"
        to_vertical(raw_vid, vclip, vis)
        padded = audio_dir / f"a{i:02d}_pad.mp3"
        run(["ffmpeg", "-y", "-i", str(ap), "-af", "apad=pad_dur=0.15", "-t", f"{vis:.3f}", str(padded)])
        seg = clip_dir / f"s{i:02d}.mp4"
        run([
            "ffmpeg", "-y", "-i", str(vclip), "-i", str(padded),
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "libx264", "-preset", "fast", "-crf", "16",
            "-c:a", "aac", "-b:a", "192k", "-shortest", "-pix_fmt", "yuv420p", str(seg),
        ])
        segs.append(seg)
        captions.append((t0, t0 + vis, beat["line"]))
        t0 += vis
        gc.collect()
        torch.cuda.empty_cache()

    del pipe
    gc.collect()
    torch.cuda.empty_cache()

    clist = work / "concat.txt"
    clist.write_text("\n".join(f"file '{p.resolve()}'" for p in segs), encoding="utf-8")
    assembled = work / "assembled.mp4"
    run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(clist),
        "-c:v", "libx264", "-preset", "fast", "-crf", "16",
        "-c:a", "aac", "-b:a", "192k", "-pix_fmt", "yuv420p", str(assembled),
    ])

    def ts(t: float) -> str:
        h, rem = divmod(max(0.0, t), 3600)
        m, s = divmod(rem, 60)
        return f"{int(h)}:{int(m):02d}:{s:05.2f}"

    ass = work / "captions.ass"
    header = (
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 720\nPlayResY: 1280\n[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Body,Arial,52,&H00FFFFFF,&H000000FF,&H00000000,&H99000000,1,0,0,0,100,100,0,0,3,4,0,2,40,40,160,1\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    ev = []
    for a, b, line in captions:
        t = line.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}")
        ev.append(f"Dialogue: 0,{ts(a+0.05)},{ts(max(a+0.5,b-0.05))},Body,,0,0,0,,{t}")
    ass.write_text(header + "\n".join(ev) + "\n", encoding="utf-8")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    run([
        "ffmpeg", "-y", "-i", str(assembled), "-vf", f"ass={ass.as_posix()}",
        "-c:v", "libx264", "-preset", "fast", "-crf", "16", "-pix_fmt", "yuv420p",
        "-c:a", "copy", "-movflags", "+faststart", str(out_path),
    ])
    for name in ("final_story.mp4", "video_raw.mp4"):
        alt = out_path.parent / name
        if alt.resolve() != out_path.resolve():
            subprocess.check_call(["cp", str(out_path), str(alt)])
    meta = {
        "ok": True,
        "bytes": out_path.stat().st_size,
        "sec": media_duration(out_path),
        "beats": len(beats),
        "engine": "cogvideox-2b-fast",
        "frames": NUM_FRAMES,
        "steps": NUM_STEPS,
    }
    print(json.dumps(meta), flush=True)
    return meta


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--story", default=None)
    p.add_argument("--out", default="/content/final_story.mp4")
    p.add_argument("--work", default="/content/cog_work")
    args, _ = p.parse_known_args(argv)
    render(load_story(args.story), Path(args.out), Path(args.work))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        traceback.print_exc()
        raise SystemExit(1)
