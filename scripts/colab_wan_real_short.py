#!/usr/bin/env python3
"""Real vertical Short on a Colab T4.

Engine: Wan-AI/Wan2.1-T2V-1.3B-Diffusers (open weights, actual motion).
Text: hosted instruct model first. The local Ollama model is not used.
A black frame or a still with a caption is rejected.
"""
from __future__ import annotations

import gc
import json
import os
import re
import shutil
import subprocess
import sys
import traceback
import urllib.request
from pathlib import Path

MODEL_ID = os.getenv("WAN_MODEL", "Wan-AI/Wan2.1-T2V-1.3B-Diffusers")
MIN_SCENE_BYTES = 80_000
MIN_FINAL_BYTES = 250_000
ROOT = Path("/content")

FALLBACK = {
    "phrases": [
        "نیمه‌شب بیدار مانده‌ای و سقف از فکرت شلوغ‌تر است؟",
        "لازم نیست همین حالا همه‌چیز را حل کنی.",
        "فقط یک کار کوچک را تمام کن و چراغ را کم کن.",
        "فردا همان راه، آرام‌تر ادامه پیدا می‌کند.",
    ],
    "visuals": [
        "photorealistic vertical night interior, a tired young man sitting by a rainy window, one warm lamp, shallow depth of field, slow gentle camera push in, natural skin, film grain, no text",
        "photorealistic vertical close-up of hands resting on a closed notebook, warm lamp light, quiet bedroom, slow drift, natural motion, no text",
        "photorealistic vertical shot, a person turning a bedside lamp dimmer, soft amber light fading, calm realistic room, slow camera, no text",
        "photorealistic vertical dawn street, one person walking toward soft sunrise, wet pavement, gentle wind in a coat, natural motion, no text",
    ],
}


def run(cmd: list[str], timeout: int = 180) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout)[-1600:])


def word_count(text: str) -> int:
    return sum(bool(re.search(r"[\u0600-\u06FFA-Za-z0-9]", token)) for token in str(text).split())


def ensure_deps() -> None:
    # GitHub Actions installs dependencies with `colab install` before executing
    # this script. Avoid running pip inside the live Jupyter kernel: replacing
    # packages during an active kernel session can break the remote connection.
    if os.getenv("COLAB_DEPS_READY") != "1":
        try:
            import diffusers  # noqa: F401
            import transformers  # noqa: F401
            import accelerate  # noqa: F401
            import safetensors  # noqa: F401
            import sentencepiece  # noqa: F401
            import ftfy  # noqa: F401
            import imageio  # noqa: F401
            import edge_tts  # noqa: F401
        except ImportError:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", "-q",
                "diffusers>=0.33.0", "transformers", "accelerate", "safetensors",
                "sentencepiece", "ftfy", "imageio", "imageio-ffmpeg", "edge-tts",
            ])
    if shutil.which("ffmpeg") is None:
        subprocess.check_call(["apt-get", "update", "-qq"])
        subprocess.check_call(["apt-get", "install", "-y", "-qq", "ffmpeg"])


def hosted_script() -> dict | None:
    system = (
        "تو نویسندهٔ شورت فارسی هستی. فقط JSON بده. "
        "چهار جملهٔ گفتاری طبیعی، بدون شعار لیستی، بدون آیه و حدیث جعلی. "
        "جملهٔ اول سؤال کوتاه باشد."
    )
    user = (
        "یک شورت معنویِ روزمره بساز، ۳۲ تا ۴۲ واژه در مجموع. "
        "خروجی فقط JSON: {\"phrases\":[\"...\",\"...\",\"...\",\"...\"],"
        "\"visuals\":[\"english photoreal vertical prompt\",\"...\",\"...\",\"...\"]} "
        "هر visual یک نمای واقعی سینمایی عمودی باشد، بدون متن داخل تصویر."
    )
    body = json.dumps({
        "model": "openai",
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": 0.7,
        "max_tokens": 700,
    }).encode()
    request = urllib.request.Request(
        "https://text.pollinations.ai/openai/chat/completions",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            payload = json.loads(response.read().decode())
        content = payload["choices"][0]["message"]["content"]
    except Exception as exc:
        print(f"[script] hosted model failed: {type(exc).__name__}", flush=True)
        return None
    return parse_package(content)


def parse_package(raw: str) -> dict | None:
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I)
    try:
        item = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.S)
        if not match:
            return None
        try:
            item = json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    phrases = [re.sub(r"\s+", " ", str(line)).strip() for line in item.get("phrases") or []]
    visuals = [re.sub(r"\s+", " ", str(line)).strip() for line in item.get("visuals") or []]
    if len(phrases) != 4 or len(visuals) != 4:
        return None
    if not (28 <= word_count(" ".join(phrases)) <= 44):
        return None
    if "؟" not in phrases[0] or not (4 <= word_count(phrases[0]) <= 14):
        return None
    if any(len(v.split()) < 6 for v in visuals):
        return None
    return {"phrases": phrases, "visuals": visuals}


def load_script() -> tuple[dict, str]:
    package = hosted_script()
    if package:
        print("[script] hosted model accepted", flush=True)
        return package, "pollinations"
    print("[script] using authored fallback, not the local model", flush=True)
    return FALLBACK, "authored-fallback"


def ensure_font() -> Path:
    fonts = ROOT / "fonts"
    fonts.mkdir(parents=True, exist_ok=True)
    bold = fonts / "Vazirmatn-Bold.ttf"
    if bold.is_file() and bold.stat().st_size > 50_000:
        return fonts
    url = "https://github.com/rastikerdar/vazirmatn/raw/v33.003/fonts/ttf/Vazirmatn-Bold.ttf"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as resp, bold.open("wb") as handle:
        handle.write(resp.read())
    return fonts


def render_scenes(visuals: list[str]) -> list[Path]:
    import torch
    from diffusers import AutoencoderKLWan, WanPipeline
    from diffusers.utils import export_to_video

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required; this is not a stills renderer")
    print("[wan] GPU", torch.cuda.get_device_name(0), flush=True)
    dtype = torch.float16
    print(f"[wan] loading {MODEL_ID}", flush=True)
    vae = AutoencoderKLWan.from_pretrained(MODEL_ID, subfolder="vae", torch_dtype=torch.float32)
    pipe = WanPipeline.from_pretrained(MODEL_ID, vae=vae, torch_dtype=dtype)
    pipe.enable_model_cpu_offload()

    height = int(os.getenv("VIDEO_H", "832"))
    width = int(os.getenv("VIDEO_W", "480"))
    frames_n = int(os.getenv("VIDEO_FRAMES", "33"))
    steps = int(os.getenv("VIDEO_STEPS", "30"))
    clips: list[Path] = []
    negative = (
        "text, subtitles, watermark, logo, cartoon, anime, blurry, static image, "
        "deformed hands, extra fingers, low quality, overexposed, black frame"
    )
    for index, visual in enumerate(visuals):
        prompt = (
            "cinematic vertical 9:16 video, photorealistic, natural human motion, "
            + visual
            + ", 24fps look, no on-screen text"
        )
        print(f"[wan] scene {index + 1}/4", flush=True)
        gc.collect()
        torch.cuda.empty_cache()
        result = pipe(
            prompt=prompt,
            negative_prompt=negative,
            height=height,
            width=width,
            num_frames=frames_n,
            num_inference_steps=steps,
            guidance_scale=5.0,
        )
        frames = result.frames[0]
        clip = ROOT / f"scene_{index:02d}.mp4"
        export_to_video(frames, str(clip), fps=16)
        size = clip.stat().st_size
        print(f"[wan] {clip.name} bytes={size}", flush=True)
        if size < MIN_SCENE_BYTES:
            raise RuntimeError(f"scene {index + 1} is not a real video ({size} bytes)")
        clips.append(clip)
        del result, frames
        gc.collect()
        torch.cuda.empty_cache()
    del pipe, vae
    gc.collect()
    torch.cuda.empty_cache()
    return clips


def synth_voice(phrases: list[str], dest: Path) -> None:
    import asyncio
    import edge_tts

    async def _save() -> None:
        await edge_tts.Communicate(" ".join(phrases), "fa-IR-FaridNeural", rate="-8%", pitch="-2Hz").save(str(dest))

    asyncio.run(_save())


def write_ass(path: Path, phrases: list[str], duration: float) -> None:
    def ts(value: float) -> str:
        minutes, seconds = divmod(max(0.0, value), 60)
        return f"0:{int(minutes):02d}:{seconds:05.2f}"

    header = """[Script Info]
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
PlayResX: 720
PlayResY: 1280

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,Vazirmatn,58,&H00FFFFFF,&H000000FF,&H00000000,&H99000000,-1,0,0,0,100,100,0,0,1,4,0,2,48,48,150,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    for index, phrase in enumerate(phrases):
        start = duration * index / len(phrases)
        end = duration * (index + 1) / len(phrases)
        safe = phrase.replace("{", r"\{").replace("}", r"\}")
        lines.append(f"Dialogue: 0,{ts(start)},{ts(end)},Caption,,0,0,0,,{safe}")
    path.write_text(header + "\n".join(lines) + "\n", encoding="utf-8")


def assemble(clips: list[Path], phrases: list[str], fonts: Path) -> Path:
    concat = ROOT / "concat.txt"
    concat.write_text("\n".join(f"file '{clip.resolve()}'" for clip in clips), encoding="utf-8")
    raw = ROOT / "video_raw.mp4"
    run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat),
        "-vf", "scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,fps=24",
        "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        str(raw),
    ], timeout=180)
    audio = ROOT / "narration.mp3"
    synth_voice(phrases, audio)
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(audio)],
        capture_output=True, text=True,
    )
    duration = float(probe.stdout.strip() or "12")
    ass = ROOT / "captions.ass"
    write_ass(ass, phrases, duration)
    final = ROOT / "final_short.mp4"
    run([
        "ffmpeg", "-y", "-i", str(raw), "-i", str(audio),
        "-vf", f"ass={ass.resolve().as_posix()}:fontsdir={fonts.resolve().as_posix()}",
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart",
        str(final),
    ], timeout=180)
    if final.stat().st_size < MIN_FINAL_BYTES:
        raise RuntimeError("final file is too small to be a real short")
    meta = ROOT / "package.json"
    meta.write_text(json.dumps({"phrases": phrases, "engine": MODEL_ID}, ensure_ascii=False, indent=2), encoding="utf-8")
    return final


def main() -> int:
    print("[wan] real video start", flush=True)
    ensure_deps()
    package, source = load_script()
    (ROOT / "script_source.txt").write_text(source + "\n" + "\n".join(package["phrases"]), encoding="utf-8")
    fonts = ensure_font()
    clips = render_scenes(package["visuals"])
    final = assemble(clips, package["phrases"], fonts)
    print(f"[SUCCESS] {final} bytes={final.stat().st_size} script={source}", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:
        traceback.print_exc()
        raise SystemExit(1)
