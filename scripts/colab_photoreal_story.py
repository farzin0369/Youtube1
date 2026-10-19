#!/usr/bin/env python3
"""Self-contained Colab GPU photoreal story: SDXL-Turbo + paced Edge TTS."""
from __future__ import annotations

import asyncio
import gc
import json
import subprocess
import sys
import traceback
from pathlib import Path

BEATS = [
    {
        "line": "اگر فقط یک نان اضافه داشته باشی، آن را برای خودت نگه می‌داری، یا با کسی قسمت می‌کنی؟",
        "prompt": (
            "cinematic photoreal vertical frame, teenage Middle Eastern boy leaving stone bakery "
            "with paper bag of fresh round bread loaves, one loaf falling mid-air, cobblestone street, "
            "mosque dome soft focus background, golden morning sunlight, shallow depth of field, "
            "natural skin texture, 35mm film look, no text no watermark"
        ),
    },
    {
        "line": "صبح، یک نان تازه از کیسه‌ی حمزه افتاد و به سمت جوی آب غلتید.",
        "prompt": (
            "cinematic photoreal close-up, round artisan bread loaf rolling on wet cobblestones, "
            "reflection in puddle, bakery doorway warm light, beige sneaker at edge of frame, "
            "golden hour, highly detailed crust texture, vertical composition, no text no watermark"
        ),
    },
    {
        "line": "حمزه نان را برداشت. همان نزدیکی کودکی را دید که از گرسنگی به دیوار تکیه داده بود.",
        "prompt": (
            "cinematic photoreal, kind bearded young Middle Eastern man kneeling on wet street "
            "picking up bread loaf with both hands, soft smile, stone bakery behind, "
            "natural daylight, emotional documentary style, vertical, no text"
        ),
    },
    {
        "line": "نرگس بی‌صدا نان دوم را از کیفش بیرون آورد.",
        "prompt": (
            "cinematic photoreal, young Middle Eastern girl in mustard yellow headscarf offering "
            "warm flatbread to seated man, small hungry boy watching in background, "
            "old city market, soft sunlight, compassionate expression, vertical, no text"
        ),
    },
    {
        "line": "حاج رضا گفت: برکت وقتی تقسیم می‌شود کم نمی‌شود؛ راهش را پیدا می‌کند.",
        "prompt": (
            "cinematic photoreal, elderly white-bearded baker with glasses and prayer beads "
            "speaking warmly to family at bread stall, blue-tiled mosque dome behind, "
            "golden sunset light, peaceful wisdom, vertical, no text no watermark"
        ),
    },
    {
        "line": "حمزه نان را به کودک داد. لبخند کودک که نشست، انگار کوچه روشن‌تر شد.",
        "prompt": (
            "cinematic photoreal, kind man kneeling handing bread to smiling ragged little boy, "
            "village courtyard, older couple watching warmly, golden hour backlight, "
            "emotional heartwarming moment, vertical, no text"
        ),
    },
    {
        "line": "ایثار از زیادی شروع نمی‌شود؛ از دلِ راضی شروع می‌شود.",
        "prompt": (
            "cinematic photoreal close-up, antique brass key hanging from blue string on brown "
            "woven vest pocket, soft bread emblem stitched nearby, blurred alley and sunset mosque, "
            "symbolic hope, warm bokeh, vertical, no text no watermark"
        ),
    },
    {
        "line": "اگر می‌خواهی راز آن را بفهمی، قسمت بعد را از دست نده. سابسکرایب و لایک یادت نرود.",
        "prompt": (
            "cinematic photoreal, same brass key on vest in foreground, three people walking "
            "into golden sunset alley toward mosque, hopeful ending frame, film grain, "
            "vertical, no text no watermark"
        ),
    },
]


def ensure_deps() -> None:
    need = []
    for mod, pkg in [
        ("diffusers", "diffusers==0.32.2"),
        ("transformers", "transformers"),
        ("accelerate", "accelerate"),
        ("edge_tts", "edge-tts"),
        ("nest_asyncio", "nest_asyncio"),
    ]:
        try:
            __import__(mod)
        except Exception:
            need.append(pkg)
    if need:
        print("[deps] installing", need, flush=True)
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", *need])


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
        text, "fa-IR-FaridNeural", rate="-12%", pitch="-2Hz", volume="+40%"
    ).save(str(out))


def process_audio(src: Path, dst: Path) -> None:
    run([
        "ffmpeg", "-y", "-i", str(src),
        "-af", "highpass=f=70,lowpass=f=10500,loudnorm=I=-14:TP=-1.5:LRA=9",
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

    print("[boot] photoreal SDXL-Turbo", flush=True)
    import torch
    from diffusers import AutoPipelineForText2Image

    if not torch.cuda.is_available():
        print("NO CUDA", flush=True)
        return 1
    print("[gpu]", torch.cuda.get_device_name(0), flush=True)

    pipe = AutoPipelineForText2Image.from_pretrained(
        "stabilityai/sdxl-turbo",
        torch_dtype=torch.float16,
        variant="fp16",
    )
    pipe.to("cuda")

    images = []
    for i, beat in enumerate(BEATS):
        print(f"[img] {i+1}/{len(BEATS)}", flush=True)
        gc.collect()
        torch.cuda.empty_cache()
        image = pipe(
            prompt=beat["prompt"],
            negative_prompt="cartoon, anime, illustration, drawing, blurry, text, watermark, logo, deformed",
            width=576,
            height=1024,
            num_inference_steps=4,
            guidance_scale=0.0,
            generator=torch.Generator("cuda").manual_seed(4200 + i * 17),
        ).images[0]
        p = img_dir / f"scene_{i:02d}.jpg"
        image.save(str(p), quality=92)
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
        dur = max(2.0, media_duration(ap))
        vis = dur + 0.3
        frames = max(48, int(vis * 24))
        z = "min(1.16,1+0.00035*on)" if i % 2 == 0 else "if(eq(on,1),1.14,max(1.0,1.14-0.00032*on))"
        vonly = content / f"v{i:02d}.mp4"
        run([
            "ffmpeg", "-y", "-loop", "1", "-i", str(img),
            "-t", f"{vis:.3f}",
            "-vf",
            f"scale=900:1600:force_original_aspect_ratio=increase,"
            f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=720x1280:fps=24,"
            f"eq=contrast=1.05:saturation=1.08",
            "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "14", "-pix_fmt", "yuv420p",
            str(vonly),
        ], timeout=90)
        padded = audio_dir / f"l{i:02d}_pad.mp3"
        run(["ffmpeg", "-y", "-i", str(ap), "-af", "apad=pad_dur=0.3", "-t", f"{vis:.3f}", str(padded)])
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
        "-c:v", "libx264", "-preset", "fast", "-crf", "14",
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
Style: Body,Arial,50,&H00FFFFFF,&H000000FF,&H00000000,&HCC000000,0,0,0,0,100,100,0,0,1,5,2,2,28,28,160,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = []
    for a, b, line in captions:
        t = line.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}")
        ev.append(f"Dialogue: 0,{ts(a+0.05)},{ts(max(a+0.5,b-0.05))},Body,,0,0,0,,{t}")
    ass.write_text(header + "\n".join(ev) + "\n", encoding="utf-8")

    final = content / "final_story.mp4"
    run([
        "ffmpeg", "-y", "-i", str(assembled),
        "-vf", f"ass={ass.as_posix()}",
        "-c:v", "libx264", "-preset", "fast", "-crf", "14", "-pix_fmt", "yuv420p",
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
