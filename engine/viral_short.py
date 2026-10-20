#!/usr/bin/env python3
"""Viral Short Engine v4 — SDXL keyframes + optional SVD image-to-video + QC.

Step1 quality: short CLIP-safe prompts, QC, better encode/TTS
Step2 motion: Stable Video Diffusion img2vid (T4-friendly settings)
Fallback: Ken Burns if I2V OOM/fails
"""
from __future__ import annotations

import argparse
import asyncio
import gc
import json
import os
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

STYLE = (
    "cinematic photoreal vertical photo, golden hour, sharp face, natural skin, "
    "shallow depth of field, no text no watermark"
)
NEG = (
    "cartoon, anime, illustration, 3d, blurry, deformed hands, extra fingers, "
    "text, watermark, logo, lowres, bad anatomy, duplicate face"
)

DEFAULT_STORY: dict[str, Any] = {
    "id": "sapling_shade_v4",
    "voice": "fa-IR-FaridNeural",
    "rate": "-12%",
    "pitch": "-2Hz",
    "style": STYLE,
    "negative": NEG,
    "characters": {
        "boy": "same 6yo Middle Eastern boy dark hair beige kurta brown suspenders",
        "elder": "same elderly Middle Eastern man white beard beige scarf brown vest",
    },
    "beats": [
        {
            "line": "روزی مردی به کودکی گفت: این نهال کی سایه می‌ده؟",
            "prompt": "metal watering can pouring water on tiny green sapling dry soil golden sunrise close-up",
        },
        {
            "line": "کودک به نهال نگاه کرد و چیزی نگفت.",
            "prompt": "{boy} kneeling looking at tiny sapling metal bucket dry field golden backlight",
        },
        {
            "line": "پیرمرد خم شد و با مهربانی پرسید.",
            "prompt": "{elder} crouching beside {boy} both looking at sapling warm sunset field",
        },
        {
            "line": "کودک سر بلند کرد و گفت: من هم زیر سایه‌ی درختی نشستم",
            "prompt": "{boy} looking up speaking to {elder} oak tree bokeh golden hour eye contact",
        },
        {
            "line": "که کسی پیش از من کاشته بود.",
            "prompt": "close-up {boy} soft smile speaking warm light oak tree background emotional",
        },
        {
            "line": "خوبی کن؛ شاید روزی سایه‌اش به غریبه‌ای برسد.",
            "prompt": "{boy} and {elder} watering sapling together large oak behind hopeful golden hour",
        },
    ],
}


def ensure_deps(need_svd: bool) -> None:
    print("[engine] deps", flush=True)
    pkgs = [
        "transformers==4.46.3", "diffusers==0.31.0", "accelerate",
        "safetensors", "edge-tts", "nest_asyncio", "huggingface_hub", "Pillow",
        "imageio", "imageio-ffmpeg",
    ]
    if need_svd:
        pkgs += ["opencv-python-headless"]
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "--upgrade", *pkgs])


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
    out = template
    for key, desc in characters.items():
        out = out.replace("{" + key + "}", desc)
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
        rms = sum(stat.rms) / 3.0
        variance_proxy = abs(rms - mean)
        if mean < 12:
            return False, f"too_dark:{mean:.1f}"
        if mean > 250:
            return False, f"too_bright:{mean:.1f}"
        if variance_proxy < 4:
            return False, f"flat:{variance_proxy:.1f}"
        return True, f"ok:mean={mean:.0f}"
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
    print("[engine] default embedded story v4", flush=True)
    return DEFAULT_STORY


def prepare_svd_frame(src: Path, dst: Path) -> None:
    """Fit vertical 9:16 still into SVD landscape 1024x576 (letterbox)."""
    if Image is None:
        raise RuntimeError("PIL required for SVD")
    im = Image.open(src).convert("RGB")
    tw, th = 1024, 576
    scale = min(tw / im.width, th / im.height)
    nw, nh = max(1, int(im.width * scale)), max(1, int(im.height * scale))
    im = im.resize((nw, nh), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (tw, th), (12, 12, 12))
    canvas.paste(im, ((tw - nw) // 2, (th - nh) // 2))
    canvas.save(str(dst), quality=95)


def frames_to_vertical_mp4(frames, out: Path, fps: int = 7) -> None:
    """Crop center vertical from landscape SVD frames → 720x1280 mp4."""
    import numpy as np
    import imageio

    if not frames:
        raise RuntimeError("no frames")
    tmp = out.with_suffix(".tmp.mp4")
    writer = imageio.get_writer(str(tmp), fps=fps, codec="libx264", quality=8, pixelformat="yuv420p")
    for fr in frames:
        if hasattr(fr, "convert"):
            arr = np.array(fr.convert("RGB"))
        else:
            arr = fr
            if arr.dtype != np.uint8:
                arr = (arr * 255).clip(0, 255).astype("uint8")
        h, w = arr.shape[:2]
        # center crop 9:16
        target_w = int(h * 9 / 16)
        if target_w > w:
            target_w = w
            target_h = int(w * 16 / 9)
            y0 = max(0, (h - target_h) // 2)
            crop = arr[y0:y0 + target_h, :, :]
        else:
            x0 = max(0, (w - target_w) // 2)
            crop = arr[:, x0:x0 + target_w, :]
        # resize to 720x1280
        pil = Image.fromarray(crop).resize((720, 1280), Image.Resampling.LANCZOS)
        writer.append_data(np.array(pil))
    writer.close()
    subprocess.check_call(["mv", str(tmp), str(out)])


def animate_svd(image_path: Path, out_mp4: Path, seed: int = 42) -> bool:
    """Run SVD img2vid; return True on success."""
    import torch
    from diffusers import StableVideoDiffusionPipeline
    from diffusers.utils import load_image

    print(f"[i2v] SVD {image_path.name}", flush=True)
    gc.collect()
    torch.cuda.empty_cache()

    pipe = StableVideoDiffusionPipeline.from_pretrained(
        "stabilityai/stable-video-diffusion-img2vid",
        torch_dtype=torch.float16,
        variant="fp16",
    )
    pipe.enable_model_cpu_offload()
    pipe.set_progress_bar_config(disable=True)

    svd_in = image_path.parent / f"svd_in_{image_path.stem}.jpg"
    prepare_svd_frame(image_path, svd_in)
    image = load_image(str(svd_in))

    try:
        frames = pipe(
            image,
            decode_chunk_size=2,
            num_frames=14,
            num_inference_steps=18,
            motion_bucket_id=110,
            fps=7,
            noise_aug_strength=0.02,
            generator=torch.Generator("cpu").manual_seed(seed),
        ).frames[0]
        frames_to_vertical_mp4(frames, out_mp4, fps=7)
        ok = out_mp4.is_file() and out_mp4.stat().st_size > 50_000
        print(f"[i2v] {'ok' if ok else 'fail'} {out_mp4}", flush=True)
        return ok
    except Exception as e:
        print(f"[i2v] error: {e}", flush=True)
        return False
    finally:
        del pipe
        gc.collect()
        torch.cuda.empty_cache()


def ken_burns(img: Path, out: Path, vis: float) -> None:
    frames = max(54, int(vis * 24))
    z = "min(1.13,1+0.00022*on)"
    run([
        "ffmpeg", "-y", "-loop", "1", "-i", str(img),
        "-t", f"{vis:.3f}",
        "-vf",
        f"scale=960:1700:force_original_aspect_ratio=increase,"
        f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=720x1280:fps=24,"
        f"eq=contrast=1.07:saturation=1.1:brightness=0.015,unsharp=3:3:0.6",
        "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "12", "-pix_fmt", "yuv420p",
        str(out),
    ], timeout=120)


def stretch_video(src: Path, dst: Path, vis: float) -> None:
    """Loop/trim clip to exact duration."""
    run([
        "ffmpeg", "-y", "-stream_loop", "-1", "-i", str(src),
        "-t", f"{vis:.3f}",
        "-vf", "scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,"
        "eq=contrast=1.05:saturation=1.08",
        "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "12", "-pix_fmt", "yuv420p",
        str(dst),
    ], timeout=120)


def render(story: dict[str, Any], out_path: Path, work: Path, use_i2v: bool = True) -> dict[str, Any]:
    ensure_deps(need_svd=use_i2v)
    work.mkdir(parents=True, exist_ok=True)
    img_dir = work / "scenes"
    img_dir.mkdir(exist_ok=True)
    audio_dir = work / "audio"
    audio_dir.mkdir(exist_ok=True)
    vid_dir = work / "clips"
    vid_dir.mkdir(exist_ok=True)
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
    print("[engine] gpu", torch.cuda.get_device_name(0), "i2v", use_i2v, flush=True)

    pipe = StableDiffusionXLPipeline.from_pretrained(
        "stabilityai/sdxl-turbo",
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
            image = pipe(
                prompt=prompt,
                negative_prompt=neg,
                width=768,
                height=1344,
                num_inference_steps=6,
                guidance_scale=1.2,
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
            print(f"[qc-img] WARN soft-accept scene {i+1}: {last_reason}", flush=True)
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
    i2v_ok_count = 0
    for i, (beat, img, ap) in enumerate(zip(beats, images, line_audios)):
        dur = max(2.2, media_duration(ap))
        vis = dur + 0.3
        vonly = vid_dir / f"v{i:02d}.mp4"
        motion_ok = False
        if use_i2v:
            raw_i2v = vid_dir / f"i2v_{i:02d}.mp4"
            motion_ok = animate_svd(img, raw_i2v, seed=8800 + i * 17)
            if motion_ok:
                stretch_video(raw_i2v, vonly, vis)
                i2v_ok_count += 1
                qc_log.append({"scene": i, "motion": "svd"})
        if not motion_ok:
            ken_burns(img, vonly, vis)
            qc_log.append({"scene": i, "motion": "kenburns"})

        padded = audio_dir / f"l{i:02d}_pad.mp3"
        run(["ffmpeg", "-y", "-i", str(ap), "-af", "apad=pad_dur=0.3", "-t", f"{vis:.3f}", str(padded)])
        seg = vid_dir / f"s{i:02d}.mp4"
        run([
            "ffmpeg", "-y", "-i", str(vonly), "-i", str(padded),
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "libx264", "-preset", "medium", "-crf", "12",
            "-c:a", "aac", "-b:a", "192k", "-shortest", "-pix_fmt", "yuv420p", str(seg),
        ])
        segs.append(seg)
        captions.append((t0, t0 + vis, beat["line"]))
        t0 += vis
        print(f"[mux] scene {i+1} motion={'svd' if motion_ok else 'kb'}", flush=True)

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
        "i2v_scenes": i2v_ok_count,
        "version": "v4-svd",
    }
    print(json.dumps(meta), flush=True)
    return meta


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Viral short engine v4")
    p.add_argument("--story", default=None)
    p.add_argument("--out", default="/content/final_story.mp4")
    p.add_argument("--work", default="/content/engine_work")
    p.add_argument("--no-i2v", action="store_true", help="Disable SVD motion")
    args, _unknown = p.parse_known_args(argv)
    use_i2v = not args.no_i2v and os.environ.get("DISABLE_I2V", "") != "1"
    story = load_story(args.story)
    render(story, Path(args.out), Path(args.work), use_i2v=use_i2v)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        traceback.print_exc()
        raise SystemExit(1)
