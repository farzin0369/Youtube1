#!/usr/bin/env python3
"""Cinematic Persian Short Engine v3.3 — quality-first scene generation.

Uses SDXL base rather than Turbo, with deliberate composition and stricter anatomy prompts.
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

try:
    from PIL import Image, ImageStat
except Exception:  # pragma: no cover
    Image = None  # type: ignore
    ImageStat = None  # type: ignore

# Keep style SHORT — CLIP 77 token limit
STYLE = (
    "cinematic photoreal vertical photo, golden hour, sharp face, natural skin, "
    "shallow depth of field, no text no watermark"
)
NEG = (
    "cartoon, anime, illustration, 3d render, blurry, deformed anatomy, malformed face, "
    "extra head, two heads, duplicate person, duplicate face, extra face, extra limbs, "
    "long neck, stretched neck, disfigured, fused bodies, fused faces, bad proportions, "
    "deformed hands, extra fingers, text, watermark, logo, lowres, plastic skin"
)

DEFAULT_STORY: dict[str, Any] = {
    "id": "sapling_shade_v31",
    "voice": "fa-IR-FaridNeural",
    "rate": "-12%",
    "pitch": "-2Hz",
    "style": STYLE,
    "negative": NEG,
    # Short identity tags (expanded carefully)
    "characters": {
        "boy": "same 6yo Middle Eastern boy dark hair beige kurta brown suspenders",
        "elder": "same elderly Middle Eastern man white beard beige scarf brown vest",
    },
    "beats": [
        {
            "line": "روزی مردی به کودکی گفت: این نهال کی سایه می‌ده؟",
            "prompt": "cinematic macro close-up, one small green sapling in dry soil, metal watering can pouring water, no people visible, golden sunrise, realistic photography",
        },
        {
            "line": "کودک به نهال نگاه کرد و چیزی نگفت.",
            "prompt": "single boy only, medium shot, the same boy kneels beside a tiny sapling and looks at it, one head, natural neck and shoulders, empty simple background, golden backlight",
        },
        {
            "line": "پیرمرد خم شد و با مهربانی پرسید.",
            "prompt": "exactly two people only: one elderly man and one young boy, both shown in a clean medium-wide side view, each with one head and natural neck, both looking down at one sapling, clear space between their bodies, simple uncluttered field, warm sunset",
        },
        {
            "line": "کودک سر بلند کرد و گفت: من هم زیر سایه‌ی درختی نشستم",
            "prompt": "single boy only in close-up, looking slightly upward while speaking, one head, natural neck, realistic child proportions, oak tree bokeh, golden hour; do not show another person",
        },
        {
            "line": "که کسی پیش از من کاشته بود.",
            "prompt": "single boy only, natural close-up portrait, soft smile, one head, normal neck proportions, warm light, oak tree background, emotional realism; no other people",
        },
        {
            "line": "خوبی کن؛ شاید روزی سایه‌اش به غریبه‌ای برسد.",
            "prompt": "exactly two people only: one elderly man and one young boy, both standing naturally side by side watering one small sapling, full upper bodies visible, one head each, normal neck proportions, clear separation between faces, large oak in distant background, hopeful golden hour",
        },
    ],
}


def ensure_deps() -> None:
    print("[engine] deps", flush=True)
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", "-q", "--upgrade",
        "transformers==4.46.3", "diffusers==0.31.0", "accelerate",
        "safetensors", "edge-tts", "nest_asyncio", "huggingface_hub", "Pillow",
    ])


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


def run_async(coro):
    import nest_asyncio
    nest_asyncio.apply()
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


def expand_prompt(template: str, characters: dict[str, str], style: str) -> str:
    """Scene first (CLIP attention), then identity, then short style."""
    out = template
    for key, desc in characters.items():
        out = out.replace("{" + key + "}", desc)
    # Important visual content FIRST so truncation hurts less
    return f"{out}, {style}"


def qc_image(path: Path, min_bytes: int = 40_000) -> tuple[bool, str]:
    if not path.is_file():
        return False, "missing"
    size = path.stat().st_size
    if size < min_bytes:
        return False, f"too_small:{size}"
    if Image is None:
        return True, "no_pil"
    try:
        im = Image.open(path).convert("RGB")
        w, h = im.size
        if w < 400 or h < 400:
            return False, f"low_res:{w}x{h}"
        if h < int(w * 1.1):
            return False, f"not_vertical:{w}x{h}"
        stat = ImageStat.Stat(im)
        mean = sum(stat.mean) / 3.0
        # Use the actual per-channel standard deviation. The old RMS-minus-mean
        # proxy could reject legitimate SDXL images and did not explain the QC.
        detail = sum(stat.stddev) / 3.0
        if mean < 12:
            return False, f"too_dark:{mean:.1f}"
        if mean > 250:
            return False, f"too_bright:{mean:.1f}"
        if detail < 3.0:
            return False, f"low_detail:{detail:.1f}"
        return True, f"ok:mean={mean:.0f},detail={detail:.1f}"
    except Exception as e:
        return False, f"pil_err:{e}"


async def tts_line(text: str, out: Path, voice: str, rate: str, pitch: str) -> None:
    import edge_tts
    await edge_tts.Communicate(
        text, voice, rate=rate, pitch=pitch, volume="+30%"
    ).save(str(out))


def process_audio(src: Path, dst: Path) -> None:
    run([
        "ffmpeg", "-y", "-i", str(src),
        "-af",
        "highpass=f=70,lowpass=f=11000,acompressor=threshold=-18dB:ratio=2.2:attack=15:release=180,"
        "loudnorm=I=-14:TP=-1.5:LRA=11",
        "-ar", "48000", "-ac", "1", str(dst),
    ], timeout=60)


def qc_audio(path: Path, min_sec: float = 1.0) -> tuple[bool, str]:
    if not path.is_file() or path.stat().st_size < 3000:
        return False, "audio_missing"
    d = media_duration(path)
    if d < min_sec:
        return False, f"audio_short:{d:.2f}"
    return True, f"audio_ok:{d:.2f}s"


def load_story(path: str | None) -> dict[str, Any]:
    if path and Path(path).is_file():
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        print(f"[engine] story file {path}", flush=True)
        return data
    print("[engine] default embedded story v3.2", flush=True)
    return DEFAULT_STORY


def render(story: dict[str, Any], out_path: Path, work: Path) -> dict[str, Any]:
    ensure_deps()
    work.mkdir(parents=True, exist_ok=True)
    img_dir = work / "scenes"
    img_dir.mkdir(exist_ok=True)
    audio_dir = work / "audio"
    audio_dir.mkdir(exist_ok=True)
    qc_log: list[dict[str, Any]] = []

    style = story.get("style", STYLE)
    neg = story.get("negative", NEG)
    characters = story.get("characters", {})
    beats = story["beats"]
    voice = story.get("voice", "fa-IR-FaridNeural")
    rate = story.get("rate", "-12%")
    pitch = story.get("pitch", "-2Hz")

    import torch
    from diffusers import StableDiffusionXLPipeline

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA required for this engine")
    print("[engine] gpu", torch.cuda.get_device_name(0), flush=True)

    pipe = StableDiffusionXLPipeline.from_pretrained(
        "stabilityai/stable-diffusion-xl-base-1.0",
        torch_dtype=torch.float16,
        variant="fp16",
    )
    pipe.set_progress_bar_config(disable=True)
    pipe.to("cuda")

    images: list[Path] = []
    max_tries = 3
    for i, beat in enumerate(beats):
        prompt = expand_prompt(beat["prompt"], characters, style)
        print(f"[prompt] {i+1}: {prompt[:120]}...", flush=True)
        ok = False
        last_reason = ""
        best_path = None
        for attempt in range(max_tries):
            print(f"[img] {i+1}/{len(beats)} try {attempt+1}", flush=True)
            gc.collect()
            torch.cuda.empty_cache()
            seed = 12000 + i * 97 + attempt * 1009
            # On retries, vary the composition request as well as the seed;
            # repeating the identical prompt often reproduces the same failure.
            retry_prompt = prompt
            if attempt == 1:
                retry_prompt += ", editorial cinematic photography, natural human anatomy, anatomically correct faces, balanced composition"
            elif attempt >= 2:
                retry_prompt += ", simple composition, anatomically correct single subjects, natural proportions, no duplicate heads or faces, documentary realism"
            image = pipe(
                prompt=retry_prompt,
                negative_prompt=neg,
                width=768,
                height=1344,
                num_inference_steps=28,
                guidance_scale=5.5,
                generator=torch.Generator("cuda").manual_seed(seed),
            ).images[0]
            p = img_dir / f"scene_{i:02d}_a{attempt}.jpg"
            image.save(str(p), quality=95)
            del image
            passed, reason = qc_image(p)
            qc_log.append({"scene": i, "attempt": attempt, "pass": passed, "reason": reason, "seed": seed})
            print(f"[qc-img] scene {i+1} {reason}", flush=True)
            if passed:
                final_p = img_dir / f"scene_{i:02d}.jpg"
                subprocess.check_call(["cp", str(p), str(final_p)])
                images.append(final_p)
                ok = True
                break
            best_path = p
            last_reason = reason
        if not ok:
            # Image QC is advisory after bounded retries: preserve the best
            # generated image instead of aborting the entire story. Fail only
            # if no image was generated at all.
            if best_path is None or not best_path.is_file():
                raise RuntimeError(f"Image generation produced no file for scene {i+1}")
            print(f"[qc-img] WARN soft-accept scene {i+1} after {max_tries} attempts: {last_reason}", flush=True)
            final_p = img_dir / f"scene_{i:02d}.jpg"
            subprocess.check_call(["cp", str(best_path), str(final_p)])
            images.append(final_p)

    del pipe
    gc.collect()
    torch.cuda.empty_cache()

    line_audios: list[Path] = []
    for i, beat in enumerate(beats):
        raw = audio_dir / f"l{i:02d}_raw.mp3"
        ap = audio_dir / f"l{i:02d}.mp3"
        run_async(tts_line(beat["line"], raw, voice, rate, pitch))
        process_audio(raw, ap)
        passed, reason = qc_audio(ap)
        qc_log.append({"scene": i, "audio": reason, "pass": passed})
        print(f"[qc-audio] {i+1} {reason}", flush=True)
        if not passed:
            raise RuntimeError(f"QC audio failed line {i}: {reason}")
        line_audios.append(ap)

    segs: list[Path] = []
    captions: list[tuple[float, float, str]] = []
    t0 = 0.0
    for i, (beat, img, ap) in enumerate(zip(beats, images, line_audios)):
        dur = max(2.2, media_duration(ap))
        vis = dur + 0.3
        frames = max(54, int(vis * 24))
        z = "min(1.13,1+0.00022*on)" if i % 2 == 0 else "if(eq(on,1),1.11,max(1.0,1.11-0.0002*on))"
        vonly = work / f"v{i:02d}.mp4"
        run([
            "ffmpeg", "-y", "-loop", "1", "-i", str(img),
            "-t", f"{vis:.3f}",
            "-vf",
            f"scale=960:1700:force_original_aspect_ratio=increase,"
            f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=720x1280:fps=24,"
            f"eq=contrast=1.07:saturation=1.1:brightness=0.015,unsharp=3:3:0.6",
            "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "12", "-pix_fmt", "yuv420p",
            str(vonly),
        ], timeout=120)
        padded = audio_dir / f"l{i:02d}_pad.mp3"
        run(["ffmpeg", "-y", "-i", str(ap), "-af", "apad=pad_dur=0.3", "-t", f"{vis:.3f}", str(padded)])
        seg = work / f"s{i:02d}.mp4"
        run([
            "ffmpeg", "-y", "-i", str(vonly), "-i", str(padded),
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(seg),
        ])
        segs.append(seg)
        captions.append((t0, t0 + vis, beat["line"]))
        t0 += vis

    clist = work / "concat.txt"
    clist.write_text("\n".join(f"file '{p.resolve()}'" for p in segs), encoding="utf-8")
    assembled = work / "assembled.mp4"
    run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(clist),
        "-c:v", "libx264", "-preset", "medium", "-crf", "12",
        "-c:a", "aac", "-b:a", "192k", "-pix_fmt", "yuv420p", str(assembled),
    ])

    def ts(t: float) -> str:
        h, rem = divmod(max(0.0, t), 3600)
        m, s = divmod(rem, 60)
        return f"{int(h)}:{int(m):02d}:{s:05.2f}"

    ass = work / "captions.ass"
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 720
PlayResY: 1280
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Body,Arial,50,&H00000000,&H000000FF,&H00000000,&H0000E5FF,1,0,0,0,100,100,0,0,3,0,0,2,36,36,150,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = []
    for a, b, line in captions:
        t = line.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}")
        ev.append(f"Dialogue: 0,{ts(a+0.06)},{ts(max(a+0.55,b-0.06))},Body,,0,0,0,,{t}")
    ass.write_text(header + "\n".join(ev) + "\n", encoding="utf-8")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    run([
        "ffmpeg", "-y", "-i", str(assembled),
        "-vf", f"ass={ass.as_posix()}",
        "-c:v", "libx264", "-preset", "medium", "-crf", "12", "-pix_fmt", "yuv420p",
        "-c:a", "copy", "-movflags", "+faststart", str(out_path),
    ])

    final_dur = media_duration(out_path)
    final_bytes = out_path.stat().st_size
    if final_dur < 10:
        raise RuntimeError(f"final too short: {final_dur:.2f}s")
    if final_bytes < 1_000_000:
        raise RuntimeError(f"final too small: {final_bytes}")
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=codec_type",
         "-of", "csv=p=0", str(out_path)],
        capture_output=True, text=True,
    )
    if "audio" not in (r.stdout or ""):
        raise RuntimeError("final missing audio")

    alt = out_path.parent / "final_story.mp4"
    if alt.resolve() != out_path.resolve():
        subprocess.check_call(["cp", str(out_path), str(alt)])
    subprocess.check_call(["cp", str(out_path), str(out_path.parent / "video_raw.mp4")])

    (work / "qc_log.json").write_text(json.dumps(qc_log, ensure_ascii=False, indent=2), encoding="utf-8")
    meta = {
        "ok": True,
        "bytes": final_bytes,
        "sec": final_dur,
        "beats": len(beats),
        "qc_events": len(qc_log),
        "version": "v3.3-quality-first-sdxl-base",
    }
    print(json.dumps(meta), flush=True)
    return meta


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Cinematic Persian short engine v3.3")
    p.add_argument("--story", default=None)
    p.add_argument("--out", default="/content/final_story.mp4")
    p.add_argument("--work", default="/content/engine_work")
    args, _unknown = p.parse_known_args(argv)
    story = load_story(args.story)
    render(story, Path(args.out), Path(args.work))
    return 0


if __name__ == "__main__":
    # Let the original exception propagate. Wrapping it in SystemExit inside
    # Colab's IPython runner caused a second, misleading traceback (TypeError).
    main()
