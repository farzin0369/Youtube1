#!/usr/bin/env python3
"""Colab GPU: photoreal SDXL-Turbo scenes + natural XTTS Persian narration.

Target quality bar: cinematic stills like professional spiritual shorts
(warm Middle-Eastern light, coherent characters), NOT Pollinations cartoons.
Runs on free Colab T4.
"""
from __future__ import annotations

import gc
import json
import subprocess
import sys
import traceback
from pathlib import Path

# Persian lines with clearer orthography for TTS (short, natural pauses)
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
            "golden hour, highly detailed crust texture, vertical 9:16, no text no watermark"
        ),
    },
    {
        "line": "حمزه نان را برداشت. همان نزدیکی کودکی را دید که از گرسنگی به دیوار تکیه داده بود.",
        "prompt": (
            "cinematic photoreal, kind bearded young Middle Eastern man kneeling on wet street "
            "picking up bread loaf with both hands, soft smile, stone bakery behind, "
            "natural daylight, emotional documentary style, vertical 9:16, no text"
        ),
    },
    {
        "line": "نرگس بی‌صدا نان دوم را از کیفش بیرون آورد.",
        "prompt": (
            "cinematic photoreal, young Middle Eastern girl in mustard yellow headscarf offering "
            "warm flatbread to seated man, small hungry boy watching in background, "
            "old city market, soft sunlight, compassionate expression, vertical 9:16, no text"
        ),
    },
    {
        "line": "حاج رضا گفت: برکت وقتی تقسیم می‌شود کم نمی‌شود؛ راهش را پیدا می‌کند.",
        "prompt": (
            "cinematic photoreal, elderly white-bearded baker with glasses and prayer beads "
            "speaking warmly to family at bread stall, blue-tiled mosque dome behind, "
            "golden sunset light, peaceful wisdom, vertical 9:16, no text no watermark"
        ),
    },
    {
        "line": "حمزه نان را به کودک داد. لبخند کودک که نشست، انگار کوچه روشن‌تر شد.",
        "prompt": (
            "cinematic photoreal, kind man kneeling handing bread to smiling ragged little boy, "
            "village courtyard, older couple watching warmly, golden hour backlight, "
            "emotional heartwarming moment, vertical 9:16, no text"
        ),
    },
    {
        "line": "ایثار از زیادی شروع نمی‌شود؛ از دلِ راضی شروع می‌شود.",
        "prompt": (
            "cinematic photoreal close-up, antique brass key hanging from blue string on brown "
            "woven vest pocket, soft bread emblem stitched nearby, blurred alley and sunset mosque, "
            "symbolic hope, warm bokeh, vertical 9:16, no text no watermark"
        ),
    },
    {
        "line": "اگر می‌خواهی راز آن را بفهمی، قسمت بعد را از دست نده. سابسکرایب و لایک یادت نرود.",
        "prompt": (
            "cinematic photoreal, same brass key on vest in foreground, three people walking "
            "into golden sunset alley toward mosque, hopeful ending frame, film grain, "
            "vertical 9:16, no text no watermark"
        ),
    },
]

MIN_IMG = 40_000


def run(cmd: list[str], timeout: int = 180) -> None:
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


def load_sdxl_turbo():
    import torch
    from diffusers import AutoPipelineForText2Image

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA required for photoreal engine")
    print("[img] load SDXL-Turbo on", torch.cuda.get_device_name(0), flush=True)
    pipe = AutoPipelineForText2Image.from_pretrained(
        "stabilityai/sdxl-turbo",
        torch_dtype=torch.float16,
        variant="fp16",
    )
    pipe.to("cuda")
    return pipe


def gen_images(pipe, out_dir: Path) -> list[Path]:
    import torch

    paths = []
    for i, beat in enumerate(BEATS):
        print(f"[img] scene {i+1}/{len(BEATS)}", flush=True)
        gc.collect()
        torch.cuda.empty_cache()
        # vertical-ish: SDXL turbo likes multiples of 8; 576x1024 ≈ 9:16
        image = pipe(
            prompt=beat["prompt"],
            negative_prompt=(
                "cartoon, anime, illustration, drawing, painting, blurry, low quality, "
                "deformed, text, watermark, logo, extra limbs, bad anatomy"
            ),
            width=576,
            height=1024,
            num_inference_steps=4,
            guidance_scale=0.0,
            generator=torch.Generator("cuda").manual_seed(4200 + i * 17),
        ).images[0]
        p = out_dir / f"scene_{i:02d}.jpg"
        image.save(str(p), quality=92)
        size = p.stat().st_size
        print(f"[img] wrote {p} bytes={size}", flush=True)
        if size < MIN_IMG:
            raise RuntimeError(f"scene {i} too small")
        paths.append(p)
        del image
    return paths


def synth_tts(text: str, out_mp3: Path) -> None:
    """Prefer XTTS natural clone; fallback Edge Farid."""
    try:
        r = subprocess.run(
            [sys.executable, "scripts/natural_tts_persian.py", str(out_mp3.parent), text],
            capture_output=True, text=True, timeout=600,
        )
        if r.returncode == 0 and out_mp3.is_file() and out_mp3.stat().st_size > 3000:
            print("[tts] XTTS OK", flush=True)
            return
        print("[tts] XTTS fail:", (r.stderr or r.stdout)[-400:], flush=True)
    except Exception as e:
        print("[tts] XTTS exception", e, flush=True)

    import asyncio
    import edge_tts

    raw = out_mp3.with_suffix(".raw.mp3")

    async def _run():
        await edge_tts.Communicate(
            text, "fa-IR-FaridNeural", rate="-10%", pitch="-2Hz", volume="+35%"
        ).save(str(raw))

    asyncio.run(_run())
    run([
        "ffmpeg", "-y", "-i", str(raw),
        "-af", "highpass=f=70,lowpass=f=10500,loudnorm=I=-14:TP=-1.5:LRA=9",
        "-ar", "48000", str(out_mp3),
    ], timeout=60)
    print("[tts] Edge fallback OK", flush=True)


def ken_burns(image: Path, duration: float, out: Path, seed: int) -> None:
    frames = max(48, int(duration * 24))
    z = (
        "min(1.18,1+0.00038*on)"
        if seed % 2 == 0
        else "if(eq(on,1),1.16,max(1.0,1.16-0.00036*on))"
    )
    run([
        "ffmpeg", "-y", "-loop", "1", "-i", str(image),
        "-t", f"{duration:.3f}",
        "-vf",
        f"scale=900:1600:force_original_aspect_ratio=increase,"
        f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=720x1280:fps=24,"
        f"eq=contrast=1.05:saturation=1.08",
        "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "14", "-pix_fmt", "yuv420p",
        str(out),
    ], timeout=90)


def write_ass(path: Path, segments: list[tuple[float, float, str]]) -> None:
    def ts(t: float) -> str:
        h, rem = divmod(max(0.0, t), 3600)
        m, s = divmod(rem, 60)
        return f"{int(h)}:{int(m):02d}:{s:05.2f}"

    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 720
PlayResY: 1280

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Body,Arial,52,&H00FFFFFF,&H000000FF,&H00000000,&HCC000000,0,0,0,0,100,100,0,0,1,5,2,2,28,28,160,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for start, end, line in segments:
        t = line.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}")
        events.append(
            f"Dialogue: 0,{ts(start+0.05)},{ts(max(start+0.5, end-0.05))},Body,,0,0,0,,{t}"
        )
    path.write_text(header + "\n".join(events) + "\n", encoding="utf-8")


def main() -> int:
    content = Path("/content")
    content.mkdir(parents=True, exist_ok=True)
    img_dir = content / "scenes"
    img_dir.mkdir(exist_ok=True)

    print("[boot] photoreal story engine", flush=True)
    try:
        import torch  # noqa: F401
        from diffusers import AutoPipelineForText2Image  # noqa: F401
    except Exception:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-q",
            "diffusers>=0.30.0", "transformers", "accelerate", "safetensors", "edge-tts",
        ])

    pipe = load_sdxl_turbo()
    images = gen_images(pipe, img_dir)
    del pipe
    gc.collect()
    try:
        import torch
        torch.cuda.empty_cache()
    except Exception:
        pass

    full_text = " ".join(b["line"] for b in BEATS)
    narration = content / "narration.mp3"
    # natural_tts expects out_dir then writes narration.mp3 inside
    synth_tts(full_text, narration)
    if not narration.is_file():
        # natural_tts writes to out_dir/narration.mp3
        alt = content / "narration.mp3"
        if not alt.is_file():
            raise RuntimeError("narration missing")

    adur = media_duration(narration)
    n = len(BEATS)
    per = max(2.5, adur / n)

    segs = []
    captions = []
    t0 = 0.0
    for i, (beat, img) in enumerate(zip(BEATS, images)):
        vonly = content / f"v_{i:02d}.mp4"
        ken_burns(img, per, vonly, seed=i)
        segs.append(vonly)
        captions.append((t0, t0 + per, beat["line"]))
        t0 += per

    clist = content / "concat.txt"
    clist.write_text("\n".join(f"file '{p.resolve()}'" for p in segs), encoding="utf-8")
    video_raw = content / "video_raw.mp4"
    run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(clist),
        "-c:v", "libx264", "-preset", "fast", "-crf", "14", "-pix_fmt", "yuv420p",
        "-an", str(video_raw),
    ])

    ass = content / "captions.ass"
    write_ass(ass, captions)
    final = content / "final_story.mp4"
    # stretch video to audio if needed
    vdur = media_duration(video_raw)
    stretch = min(max(adur / max(vdur, 0.1), 0.9), 1.15)
    vf = f"setpts={stretch}*PTS,ass={ass.as_posix()}"
    run([
        "ffmpeg", "-y", "-i", str(video_raw), "-i", str(narration),
        "-vf", vf,
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "libx264", "-preset", "fast", "-crf", "14", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest", "-movflags", "+faststart", str(final),
    ])

    # also copy as video_raw for finish pipeline compatibility
    if final.is_file():
        subprocess.check_call(["cp", str(final), str(content / "video_raw.mp4")])

    print(json.dumps({
        "ok": True,
        "engine": "sdxl-turbo+xtts",
        "final": str(final),
        "bytes": final.stat().st_size,
        "seconds": media_duration(final),
        "scenes": len(BEATS),
    }), flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        traceback.print_exc()
        raise SystemExit(1)
