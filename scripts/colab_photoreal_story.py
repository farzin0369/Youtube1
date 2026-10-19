#!/usr/bin/env python3
"""Colab GPU photoreal story: SDXL-Turbo + paced Edge TTS.

v2: tighter per-line prompts (character lock), better TTS pauses.
"""
from __future__ import annotations

import asyncio
import gc
import json
import subprocess
import sys
import traceback
from pathlib import Path

# Character locks for visual consistency across scenes
HAMZEH = (
    "same young Middle Eastern man named Hamzeh, short neat beard, warm brown eyes, "
    "simple beige linen shirt, kind face, photoreal"
)
BOY = (
    "same small hungry Middle Eastern boy about 7 years old, thin face, dark messy hair, "
    "worn brown shirt, bare feet, photoreal"
)
NARGES = (
    "same young Middle Eastern woman Narges, mustard-yellow headscarf, gentle eyes, "
    "modest dark dress, photoreal"
)
HAJ = (
    "same elderly Middle Eastern baker Haj Reza, white full beard, wire glasses, "
    "prayer beads, flour-dusted apron, wise calm face, photoreal"
)
STYLE = (
    "cinematic photoreal, natural skin texture, golden-hour soft light, shallow depth of field, "
    "35mm film look, high detail, vertical 9:16 composition, no text, no watermark, no logo"
)
NEG = (
    "cartoon, anime, illustration, drawing, 3d render, blurry, deformed hands, extra fingers, "
    "text, watermark, logo, low quality, duplicate faces, wrong age"
)

BEATS = [
    {
        # Hook – question only; show the moment of choice with bread
        "line": "اگر فقط یک نانِ اضافه داشته باشی… آن را برای خودت نگه می‌داری، یا با کسی قسمت می‌کنی؟",
        "prompt": (
            f"{STYLE}, close-up of two warm round Iranian sangak breads in weathered hands, "
            f"cobblestone bakery alley at sunrise, soft steam rising, decision moment, emotional"
        ),
    },
    {
        "line": "صبحِ زود، یک نانِ تازه از کیسه‌ی حمزه افتاد و روی سنگ‌فرشِ خیس غلتید.",
        "prompt": (
            f"{STYLE}, {HAMZEH}, paper bag slipping from his hand, one round bread loaf mid-roll "
            f"on wet cobblestones, bakery doorway behind, morning light, motion freeze"
        ),
    },
    {
        "line": "حمزه خم شد و نان را برداشت. کنار دیوار، کودکی از گرسنگی نشسته بود.",
        "prompt": (
            f"{STYLE}, {HAMZEH} kneeling, picking up bread with both hands, soft concerned look, "
            f"{BOY} sitting against stone wall in soft background, hunger, documentary emotion"
        ),
    },
    {
        "line": "نرگس بی‌صدا نانِ دوم را از کیفش بیرون آورد و پیش آورد.",
        "prompt": (
            f"{STYLE}, {NARGES} offering a warm flatbread forward with both hands, "
            f"market stall soft bokeh, compassionate expression, natural sunlight on scarf"
        ),
    },
    {
        "line": "حاج‌رضا گفت: برکت، وقتی تقسیم می‌شود کم نمی‌شود؛ راهش را پیدا می‌کند.",
        "prompt": (
            f"{STYLE}, {HAJ} speaking gently at bread stall, blue-tiled mosque dome soft behind, "
            f"flour on hands, warm sunset light, wisdom and peace"
        ),
    },
    {
        "line": "حمزه نان را به کودک داد. لبخندِ کودک که نشست، انگار کوچه روشن‌تر شد.",
        "prompt": (
            f"{STYLE}, {HAMZEH} kneeling, placing bread into hands of {BOY}, boy smiling softly, "
            f"golden backlight, emotional heartwarming moment, eye contact"
        ),
    },
    {
        "line": "ایثار از زیادی شروع نمی‌شود؛ از دلِ راضی شروع می‌شود.",
        "prompt": (
            f"{STYLE}, close-up antique brass key on blue string against woven brown vest, "
            f"warm bokeh of alley and distant mosque at dusk, symbolic hope, shallow focus"
        ),
    },
    {
        "line": "اگر می‌خواهی رازِ آن را بفهمی، قسمتِ بعد را از دست نده. سابسکرایب کن و لایک یادت نرود.",
        "prompt": (
            f"{STYLE}, three silhouettes walking into golden sunset alley toward mosque, "
            f"hopeful ending, film grain, warm orange sky, peaceful"
        ),
    },
]


def ensure_deps() -> None:
    print("[deps] upgrading stack", flush=True)
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
    # Slightly slower + lower pitch for calmer, less robotic Persian male
    await edge_tts.Communicate(
        text, "fa-IR-FaridNeural", rate="-18%", pitch="-4Hz", volume="+35%"
    ).save(str(out))


def process_audio(src: Path, dst: Path) -> None:
    # Gentle denoise-ish eq + loudnorm for broadcast feel
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

    print("[boot] photoreal SDXL-Turbo v2", flush=True)
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
        # 6 steps + tiny guidance often cleaner on turbo than pure 4-step
        image = pipe(
            prompt=beat["prompt"],
            negative_prompt=NEG,
            width=768,
            height=1344,
            num_inference_steps=6,
            guidance_scale=1.0,
            generator=torch.Generator("cuda").manual_seed(9100 + i * 31),
        ).images[0]
        p = img_dir / f"scene_{i:02d}.jpg"
        image.save(str(p), quality=94)
        print(f"[img] {p.stat().st_size} bytes", flush=True)
        images.append(p)
        del image

    del pipe
    gc.collect()
    torch.cuda.empty_cache()
    print("[img] all scenes done", flush=True)

    line_audios = []
    for i, beat in enumerate(BEATS):
        raw = audio_dir / f"l{i:02d}_raw.mp3"
        ap = audio_dir / f"l{i:02d}.mp3"
        run_async(tts_line(beat["line"], raw))
        process_audio(raw, ap)
        line_audios.append(ap)
        print(f"[tts] line {i+1}", flush=True)

    segs = []
    captions = []
    t0 = 0.0
    for i, (beat, img, ap) in enumerate(zip(BEATS, images, line_audios)):
        dur = max(2.2, media_duration(ap))
        vis = dur + 0.35
        frames = max(54, int(vis * 24))
        z = "min(1.14,1+0.00028*on)" if i % 2 == 0 else "if(eq(on,1),1.12,max(1.0,1.12-0.00026*on))"
        vonly = content / f"v{i:02d}.mp4"
        run([
            "ffmpeg", "-y", "-loop", "1", "-i", str(img),
            "-t", f"{vis:.3f}",
            "-vf",
            f"scale=900:1600:force_original_aspect_ratio=increase,"
            f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=720x1280:fps=24,"
            f"eq=contrast=1.06:saturation=1.1:brightness=0.02",
            "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "13", "-pix_fmt", "yuv420p",
            str(vonly),
        ], timeout=90)
        padded = audio_dir / f"l{i:02d}_pad.mp3"
        run(["ffmpeg", "-y", "-i", str(ap), "-af", "apad=pad_dur=0.35", "-t", f"{vis:.3f}", str(padded)])
        seg = content / f"s{i:02d}.mp4"
        run([
            "ffmpeg", "-y", "-i", str(vonly), "-i", str(padded),
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(seg),
        ])
        segs.append(seg)
        captions.append((t0, t0 + vis, beat["line"]))
        t0 += vis
        print(f"[mux] scene {i+1}", flush=True)

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

    ass = content / "captions.ass"
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 720
PlayResY: 1280
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Body,Arial,52,&H00FFFFFF,&H000000FF,&H00000000,&HCC000000,0,0,0,0,100,100,0,0,1,5,2,2,30,30,150,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = []
    for a, b, line in captions:
        t = line.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}")
        ev.append(f"Dialogue: 0,{ts(a+0.08)},{ts(max(a+0.6,b-0.08))},Body,,0,0,0,,{t}")
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
