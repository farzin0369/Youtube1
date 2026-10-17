#!/usr/bin/env python3
"""ImamAli viral short — beautiful Persian typography + strong hook.

- Font: Vazirmatn Bold (free OFL) — clean modern Persian
- Large captions, high contrast, lower-third
- Hook → promise → steps → warm close
"""
from __future__ import annotations

import asyncio
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

PHRASES = [
    "اگه شب‌ها به‌خاطر پول نمی‌خوابی…",
    "این سه قدم مالِ توست.",
    "قدم اول: فقط امروز را ببین.",
    "قدم دوم: یک کار کوچکِ شدنی انجام بده.",
    "قدم سوم: بقیه را با آرامش بسپار.",
    "تو از این نگرانی قوی‌تری.",
]

VISUALS = [
    "cinematic vertical close-up anxious person night window single warm lamp deep blue shadows photorealistic film grain no text no watermark",
    "cinematic vertical golden light rays breaking through dark clouds hope atmosphere photorealistic vertical no text",
    "cinematic vertical soft morning sunlight on simple desk calendar coffee calm focus photorealistic no text",
    "cinematic vertical hands writing one line in notebook warm lamp determined calm photorealistic no text",
    "cinematic vertical open palms under soft golden beam dark peaceful room photorealistic no text",
    "cinematic vertical silhouette walking toward warm sunrise open path hopeful spiritual photorealistic no text",
]

VOICE = "fa-IR-FaridNeural"
ROOT = Path(__file__).resolve().parents[1]
FONTS_DIR = ROOT / "assets" / "fonts"


def run(cmd: list[str], timeout: int = 180) -> None:
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout)[-1400:])


def media_duration(path: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True,
    )
    return float(r.stdout.strip() or "0")


def ensure_vazirmatn() -> Path:
    FONTS_DIR.mkdir(parents=True, exist_ok=True)
    bold = FONTS_DIR / "Vazirmatn-Bold.ttf"
    if bold.is_file() and bold.stat().st_size > 50_000:
        return bold
    urls = [
        "https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/fonts/ttf/Vazirmatn-Bold.ttf",
        "https://github.com/rastikerdar/vazirmatn/raw/v33.003/fonts/ttf/Vazirmatn-Bold.ttf",
    ]
    for url in urls:
        try:
            print("[font] downloading Vazirmatn-Bold…", flush=True)
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as resp, bold.open("wb") as f:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
            if bold.stat().st_size > 50_000:
                print(f"[font] ok {bold}", flush=True)
                return bold
        except Exception as e:
            print(f"[font] {type(e).__name__}", flush=True)
            bold.unlink(missing_ok=True)
    raise RuntimeError("Could not download Vazirmatn-Bold.ttf")


async def tts(text: str, out: Path) -> None:
    import edge_tts
    await edge_tts.Communicate(text, VOICE, rate="-12%", pitch="-3Hz").save(str(out))


def fetch_image(prompt: str, dest: Path) -> bool:
    q = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{q}?width=768&height=1344&nologo=true&model=flux"
    for attempt in range(3):
        try:
            print(f"[img] {dest.name} try {attempt + 1}", flush=True)
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=80) as resp, dest.open("wb") as f:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
            if dest.stat().st_size > 20_000:
                return True
        except Exception as e:
            print(f"[img] {type(e).__name__}", flush=True)
            time.sleep(10 + attempt * 8)
        dest.unlink(missing_ok=True)
    return False


def ken_burns(image: Path, duration: float, out: Path, seed: int) -> None:
    frames = max(24, int(duration * 24))
    z = "min(1.14,1+0.0003*on)" if seed % 2 == 0 else "if(eq(on,1),1.12,max(1.0,1.12-0.0003*on))"
    vf = (
        f"scale=840:1493:force_original_aspect_ratio=increase,"
        f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s=720x1280:fps=24,"
        f"eq=contrast=1.1:brightness=-0.02:saturation=1.12,"
        f"vignette=PI/6"
    )
    run([
        "ffmpeg", "-y", "-loop", "1", "-i", str(image),
        "-t", f"{duration:.3f}",
        "-vf", "".join(vf),
        "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "17", "-pix_fmt", "yuv420p",
        str(out),
    ], timeout=120)


def write_ass(path: Path, phrases: list[str], duration: float) -> None:
    def ts(t: float) -> str:
        h, rem = divmod(max(0.0, t), 3600)
        m, s = divmod(rem, 60)
        return f"{int(h)}:{int(m):02d}:{s:05.2f}"

    n = max(len(phrases), 1)
    header = """[Script Info]
Title: ImamAli Vazirmatn captions
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
PlayResX: 720
PlayResY: 1280

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Hook,Vazirmatn,68,&H00FFFFFF,&H000000FF,&H00000000,&HCC000000,0,0,0,0,100,100,0,0,1,6,3,2,28,28,210,1
Style: Body,Vazirmatn,60,&H00FFFFFF,&H000000FF,&H00000000,&HBB000000,0,0,0,0,100,100,0,0,1,5,3,2,28,28,200,1
Style: Soft,Vazirmatn,56,&H00F0F4FF,&H000000FF,&H00000000,&HAA000000,0,0,0,0,100,100,0,0,1,5,2,2,28,28,190,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines: list[str] = []
    for i, phrase in enumerate(phrases):
        start = duration * i / n
        end = duration * (i + 1) / n
        text = phrase.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}")
        if i == 0:
            style = "Hook"
            anim = r"{\fad(140,100)\t(0,200,\fscx110\fscy110)\t(200,360,\fscx100\fscy100)}"
        elif i == n - 1:
            style = "Soft"
            anim = r"{\fad(120,160)}"
        else:
            style = "Body"
            anim = r"{\fad(100,90)\t(0,160,\fscx105\fscy105)\t(160,280,\fscx100\fscy100)}"
        lines.append(
            f"Dialogue: 0,{ts(start)},{ts(end)},{style},,0,0,0,,{anim}{text}"
        )
    path.write_text(header + "\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "output/imamali_style")
    out.mkdir(parents=True, exist_ok=True)
    imgs = out / "images"
    imgs.mkdir(exist_ok=True)

    font_file = ensure_vazirmatn()
    fonts_dir = font_file.parent.resolve()

    try:
        import edge_tts  # noqa: F401
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "edge-tts"])

    phrases = list(PHRASES)
    visuals = (VISUALS * ((len(phrases) // max(1, len(VISUALS))) + 1))[: len(phrases)]

    audio = out / "narration.mp3"
    asyncio.run(tts(" ".join(phrases), audio))
    adur = media_duration(audio)
    print(f"[ok] audio {adur:.2f}s | font={font_file.name}", flush=True)

    weights = [1.4] + [1.0] * (len(phrases) - 2) + [1.15]
    total_w = sum(weights)
    durations = [adur * (w / total_w) for w in weights]

    segs: list[Path] = []
    for i, (phrase, prompt, seg_dur) in enumerate(zip(phrases, visuals, durations)):
        img = imgs / f"p_{i:02d}.jpg"
        if not img.is_file() or img.stat().st_size < 20_000:
            if not fetch_image(prompt, img):
                # Never silently ship a blank-color scene as if it were finished.
                # Reuse the closest previously generated valid visual instead.
                prior = [
                    p for p in sorted(imgs.glob("p_*.jpg"))
                    if p != img and p.stat().st_size > 20_000
                ]
                if not prior:
                    raise RuntimeError(
                        f"Image provider failed for {img.name}; no valid image exists "
                        "for a safe fallback. Refusing to render a low-quality blank scene."
                    )
                import shutil
                fallback = prior[-1]
                shutil.copyfile(fallback, img)
                print(
                    f"[warn] image provider failed for {img.name}; reused "
                    f"{fallback.name} instead of blank-color fallback",
                    flush=True,
                )
            time.sleep(2)
        seg = out / f"seg_{i:02d}.mp4"
        ken_burns(img, seg_dur, seg, seed=i)
        segs.append(seg)
        print(f"[ok] {i + 1}/{len(phrases)}: {phrase}", flush=True)

    concat = out / "concat.txt"
    concat.write_text("\n".join(f"file '{p.resolve()}'" for p in segs), encoding="utf-8")
    raw = out / "video_raw.mp4"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-c:v", "copy", "-an", str(raw)])

    ass = out / "captions.ass"
    write_ass(ass, phrases, adur)

    final = out / "final_short.mp4"
    vf = f"ass={ass.resolve().as_posix()}:fontsdir={fonts_dir.as_posix()}"
    run([
        "ffmpeg", "-y", "-i", str(raw), "-i", str(audio),
        "-vf", vf,
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "libx264", "-preset", "fast", "-crf", "15", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest", "-movflags", "+faststart",
        str(final),
    ])
    print(f"[SUCCESS] {final} bytes={final.stat().st_size} ~{adur:.1f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
