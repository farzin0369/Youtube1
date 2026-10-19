#!/usr/bin/env python3
"""Colab GPU photoreal short — style locked to user's viral sample.

Same boy + same elder, golden hour, sapling story, yellow captions.
"""
from __future__ import annotations

import asyncio
import gc
import json
import subprocess
import sys
import traceback
from pathlib import Path

# Strict character locks (same faces every scene)
BOY = (
    "same 6-year-old Middle Eastern boy, soft dark brown hair, large dark eyes, "
    "beige kurta with brown suspenders, barefoot or sandals, photoreal natural skin"
)
ELDER = (
    "same elderly Middle Eastern man, silver-white hair and full white beard, "
    "kind wrinkled eyes, beige scarf, brown vest over cream shirt, photoreal"
)
STYLE = (
    "cinematic photoreal vertical 9:16, golden hour warm sunlight, soft shallow depth of field, "
    "natural skin texture, film grain subtle, emotional storytelling still, "
    "no text no watermark no logo no subtitle burn-in"
)
NEG = (
    "cartoon, anime, illustration, 3d, blurry, deformed hands, extra fingers, "
    "different face, different age, text, watermark, logo, lowres, oversaturated"
)

# Short viral parable — matches user's sample structure
BEATS = [
    {
        "line": "روزی مردی به کودکی گفت: این نهال کی سایه می‌ده؟",
        "prompt": (
            f"{STYLE}, close-up metal watering can pouring clear water onto small green sapling "
            f"in dry brown soil, hands of adult blurred, morning golden light, high detail water splash"
        ),
    },
    {
        "line": "کودک به نهال نگاه کرد و چیزی نگفت.",
        "prompt": (
            f"{STYLE}, {BOY} kneeling beside tiny green sapling, looking down thoughtfully, "
            f"small metal bucket nearby, dry field, soft golden backlight, emotional quiet moment"
        ),
    },
    {
        "line": "پیرمرد خم شد و با مهربانی پرسید.",
        "prompt": (
            f"{STYLE}, {ELDER} crouching beside {BOY}, both looking at small sapling between them, "
            f"elder gesturing gently with open hand, warm sunset field, intimate two-shot"
        ),
    },
    {
        "line": "کودک سر بلند کرد و گفت: من هم زیر سایه‌ی درختی نشستم",
        "prompt": (
            f"{STYLE}, {BOY} looking up at {ELDER}, speaking with open expression, "
            f"elder listening warmly, large oak tree soft bokeh in background, golden hour"
        ),
    },
    {
        "line": "که کسی پیش از من کاشته بود.",
        "prompt": (
            f"{STYLE}, close-up of {BOY} face smiling softly while speaking, "
            f"huge green oak tree blurred behind, warm sunlight on cheeks, emotional portrait"
        ),
    },
    {
        "line": "خوبی کن؛ شاید روزی سایه‌اش به غریبه‌ای برسد.",
        "prompt": (
            f"{STYLE}, {BOY} and {ELDER} both kneeling, hands near sapling, watering together, "
            f"large mature oak tree filling background, hopeful smiles, golden hour cinematic"
        ),
    },
]


def ensure_deps() -> None:
    print("[deps] stack", flush=True)
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", "-q", "--upgrade",
        "transformers==4.46.3", "diffusers==0.31.0", "accelerate",
        "safetensors", "edge-tts", "nest_asyncio", "huggingface_hub",
    ])


def run(cmd, timeout=180):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout)[-1800:])


def media_duration(path: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True,
    )
    return float(r.stdout.strip() or "0")


def run_async(coro):
    import nest_asyncio
    nest_asyncio.apply()
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


async def tts_line(text: str, out: Path) -> None:
    import edge_tts
    await edge_tts.Communicate(
        text, "fa-IR-FaridNeural", rate="-15%", pitch="-3Hz", volume="+35%"
    ).save(str(out))


def process_audio(src: Path, dst: Path) -> None:
    run([
        "ffmpeg", "-y", "-i", str(src),
        "-af",
        "highpass=f=80,lowpass=f=10000,acompressor=threshold=-18dB:ratio=2:attack=20:release=200,"
        "loudnorm=I=-14:TP=-1.5:LRA=11",
        "-ar", "48000", "-ac", "1", str(dst),
    ], timeout=60)


def main() -> int:
    ensure_deps()
    content = Path("/content")
    content.mkdir(parents=True, exist_ok=True)
    img_dir = content / "scenes"
    img_dir.mkdir(exist_ok=True)
    audio_dir = content / "audio"
    audio_dir.mkdir(exist_ok=True)

    print("[boot] sapling viral style", flush=True)
    import torch
    from diffusers import StableDiffusionXLPipeline

    if not torch.cuda.is_available():
        print("NO CUDA", flush=True)
        return 1
    print("[gpu]", torch.cuda.get_device_name(0), flush=True)

    pipe = StableDiffusionXLPipeline.from_pretrained(
        "stabilityai/sdxl-turbo",
        torch_dtype=torch.float16,
        variant="fp16",
    )
    pipe.set_progress_bar_config(disable=True)
    pipe.to("cuda")

    images = []
    for i, beat in enumerate(BEATS):
        print(f"[img] {i+1}/{len(BEATS)}", flush=True)
        gc.collect()
        torch.cuda.empty_cache()
        image = pipe(
            prompt=beat["prompt"],
            negative_prompt=NEG,
            width=768,
            height=1344,
            num_inference_steps=6,
            guidance_scale=1.2,
            generator=torch.Generator("cuda").manual_seed(7700 + i * 41),
        ).images[0]
        p = img_dir / f"scene_{i:02d}.jpg"
        image.save(str(p), quality=94)
        print(f"[img] {p.stat().st_size} bytes", flush=True)
        images.append(p)
        del image

    del pipe
    gc.collect()
    torch.cuda.empty_cache()
    print("[img] done", flush=True)

    line_audios = []
    for i, beat in enumerate(BEATS):
        raw = audio_dir / f"l{i:02d}_raw.mp3"
        ap = audio_dir / f"l{i:02d}.mp3"
        run_async(tts_line(beat["line"], raw))
        process_audio(raw, ap)
        line_audios.append(ap)
        print(f"[tts] {i+1}", flush=True)

    segs = []
    captions = []
    t0 = 0.0
    for i, (beat, img, ap) in enumerate(zip(BEATS, images, line_audios)):
        dur = max(2.0, media_duration(ap))
        vis = dur + 0.25
        frames = max(48, int(vis * 24))
        z = "min(1.12,1+0.00025*on)" if i % 2 == 0 else "if(eq(on,1),1.10,max(1.0,1.10-0.00022*on))"
        vonly = content / f"v{i:02d}.mp4"
        run([
            "ffmpeg", "-y", "-loop", "1", "-i", str(img),
            "-t", f"{vis:.3f}",
            "-vf",
            f"scale=900:1600:force_original_aspect_ratio=increase,"
            f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=720x1280:fps=24,"
            f"eq=contrast=1.05:saturation=1.08:brightness=0.01",
            "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "13", "-pix_fmt", "yuv420p",
            str(vonly),
        ], timeout=90)
        padded = audio_dir / f"l{i:02d}_pad.mp3"
        run(["ffmpeg", "-y", "-i", str(ap), "-af", "apad=pad_dur=0.25", "-t", f"{vis:.3f}", str(padded)])
        seg = content / f"s{i:02d}.mp4"
        run([
            "ffmpeg", "-y", "-i", str(vonly), "-i", str(padded),
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(seg),
        ])
        segs.append(seg)
        captions.append((t0, t0 + vis, beat["line"]))
        t0 += vis
        print(f"[mux] {i+1}", flush=True)

    clist = content / "concat.txt"
    clist.write_text("\n".join(f"file '{p.resolve()}'" for p in segs), encoding="utf-8")
    assembled = content / "assembled.mp4"
    run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(clist),
        "-c:v", "libx264", "-preset", "fast", "-crf", "13",
        "-c:a", "aac", "-b:a", "192k", "-pix_fmt", "yuv420p", str(assembled),
    ])

    def ts(t):
        h, rem = divmod(max(0.0, t), 3600)
        m, s = divmod(rem, 60)
        return f"{int(h)}:{int(m):02d}:{s:05.2f}"

    # Yellow box captions like the sample
    ass = content / "captions.ass"
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 720
PlayResY: 1280
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Body,Arial,48,&H00000000,&H000000FF,&H00000000,&H0000E5FF,0,0,0,0,100,100,0,0,3,0,0,2,40,40,140,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    # BorderStyle 3 = opaque box; BackColour &H0000E5FF = yellow (AA BB GG RR)
    ev = []
    for a, b, line in captions:
        t = line.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}")
        ev.append(f"Dialogue: 0,{ts(a+0.05)},{ts(max(a+0.5,b-0.05))},Body,,0,0,0,,{t}")
    ass.write_text(header + "\n".join(ev) + "\n", encoding="utf-8")

    final = content / "final_story.mp4"
    run([
        "ffmpeg", "-y", "-i", str(assembled),
        "-vf", f"ass={ass.as_posix()}",
        "-c:v", "libx264", "-preset", "fast", "-crf", "13", "-pix_fmt", "yuv420p",
        "-c:a", "copy", "-movflags", "+faststart", str(final),
    ])
    subprocess.check_call(["cp", str(final), str(content / "video_raw.mp4")])
    print(json.dumps({"ok": True, "bytes": final.stat().st_size, "sec": media_duration(final)}), flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        traceback.print_exc()
        raise SystemExit(1)
