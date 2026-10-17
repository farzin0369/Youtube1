#!/usr/bin/env python3
"""Create a one-image Persian rude comedy test Short using the existing mascot image design.

Test-only output; never uploads to YouTube.
"""
from __future__ import annotations

import asyncio
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 720, 1280
BG_TOP = (18, 14, 38)
BG_BOTTOM = (83, 23, 60)
VOICE = "fa-IR-FaridNeural"
LINES = [
    "صبح گوه‌تون بخیر!",
    "از طرف واحد رسمی بدبختی و امور ریدن...",
    "برای تک‌تک شما عزیزان، روزی پر از ریدن و اعصابی داغون آرزو داریم!",
    "و مشکلاتی که با هیچ ذکر و دعایی حل نمی‌شن!",
    "یادتون نره؛ اگه امروز همه‌چی به گا رفت...",
    "یعنی بالاخره دارید طبق برنامه پیش می‌رید!",
    "برای شکایت، گزینهٔ یک؛ برای بدبختیِ بیشتر، گزینهٔ دو رو فشار بدید!",
    "ها... ها... ها... هااااا! خندهٔ سیستمی به پایان رسید!",
]
FULL_SCRIPT = (
    "صبح گوه‌تون بخیر! ... "
    "از طرف واحد رسمی بدبختی و امور ریدن، ... "
    "برای تک‌تک شما عزیزان، روزی پر از ریدن و اعصابی داغون آرزو داریم! ... "
    "و مشکلاتی که با هیچ ذکر و دعایی حل نمی‌شن! ... "
    "یادتون نره؛ اگه امروز همه‌چی به گا رفت... "
    "یعنی بالاخره دارید طبق برنامه پیش می‌رید! ... "
    "برای شکایت، گزینهٔ یک؛ برای بدبختیِ بیشتر، گزینهٔ دو رو فشار بدید!"
)
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "output/maslahati_test")
OUT.mkdir(parents=True, exist_ok=True)


def run(cmd: list[str], timeout: int = 180) -> None:
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if p.returncode:
        raise RuntimeError((p.stderr or p.stdout)[-2500:])


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf" if bold else "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ]
    for p in candidates:
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size, layout_engine=ImageFont.Layout.RAQM)
            except Exception:
                continue
    return ImageFont.load_default()


def centered(draw: ImageDraw.ImageDraw, y: int, text: str, fnt, fill, stroke_width=0, stroke_fill=(0, 0, 0)):
    draw.text((W // 2, y), text, font=fnt, fill=fill, anchor="mm",
              direction="rtl", language="fa", stroke_width=stroke_width, stroke_fill=stroke_fill)


def make_image(path: Path) -> None:
    im = Image.new("RGB", (W, H))
    pix = im.load()
    for y in range(H):
        t = y / (H - 1)
        c = tuple(int(BG_TOP[i] * (1-t) + BG_BOTTOM[i] * t) for i in range(3))
        for x in range(W):
            pix[x, y] = c
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((28, 26, W-28, H-26), radius=34, outline=(255, 207, 82), width=5)
    centered(d, 92, "مشاوره انگیزشی", font(34, True), (255, 221, 108))
    centered(d, 150, "واحد رسمی بدبختی 💀", font(27, True), (255, 255, 255))

    # A frazzled cartoon potato-cat therapist, all drawn locally.
    d.ellipse((164, 320, 556, 790), fill=(255, 183, 67), outline=(30, 19, 42), width=9)
    d.polygon([(220, 390), (224, 275), (315, 352)], fill=(255, 183, 67), outline=(30, 19, 42))
    d.polygon([(405, 352), (500, 275), (498, 410)], fill=(255, 183, 67), outline=(30, 19, 42))
    d.polygon([(242, 355), (242, 315), (283, 365)], fill=(255, 112, 133))
    d.polygon([(435, 365), (480, 315), (475, 370)], fill=(255, 112, 133))
    d.arc((230, 425, 345, 535), 190, 345, fill=(30, 19, 42), width=13)
    d.arc((370, 425, 485, 535), 195, 350, fill=(30, 19, 42), width=13)
    d.ellipse((253, 455, 323, 520), outline=(30, 19, 42), width=9)
    d.ellipse((391, 455, 461, 520), outline=(30, 19, 42), width=9)
    d.line((323, 483, 391, 483), fill=(30, 19, 42), width=9)
    d.ellipse((282, 477, 297, 501), fill=(30, 19, 42))
    d.ellipse((416, 477, 431, 501), fill=(30, 19, 42))
    d.arc((302, 535, 420, 625), 15, 165, fill=(30, 19, 42), width=11)
    d.ellipse((463, 545, 495, 590), fill=(92, 204, 255), outline=(255,255,255), width=3)
    for yy in (570, 602):
        d.line((176, yy, 255, yy-12), fill=(30, 19, 42), width=5)
        d.line((465, yy-12, 544, yy), fill=(30, 19, 42), width=5)
    d.polygon([(335, 650), (385, 650), (370, 710), (350, 710)], fill=(238, 61, 111), outline=(30, 19, 42))
    d.rounded_rectangle((422, 660, 535, 790), radius=10, fill=(245, 240, 214), outline=(30, 19, 42), width=5)
    d.line((442, 694, 515, 694), fill=(40, 35, 55), width=4)
    d.line((442, 720, 505, 720), fill=(40, 35, 55), width=4)
    d.line((442, 746, 511, 746), fill=(40, 35, 55), width=4)

    centered(d, 855, "صبح گوه‌تون بخیر!", font(34, True), (255, 255, 255), 2, (15, 10, 28))
    centered(d, 923, "واحد رسمی بدبختی پاسخ‌گو نیست!", font(25, True), (255, 95, 132), 2, (15, 10, 28))
    centered(d, 991, "برای بدبختی بیشتر، گزینهٔ دو 😂", font(25, True), (255, 221, 108), 2, (15, 10, 28))
    centered(d, 1122, "نسخهٔ آزمایشی — مشاوره انگیزشی", font(22, True), (238, 225, 255))
    im.save(path, quality=95)


async def synthesize(path: Path) -> None:
    import edge_tts
    # Keep narration separate so the brand laugh can have its own unmistakable sound design.
    await edge_tts.Communicate(FULL_SCRIPT, VOICE, rate="-8%", pitch="-8Hz", volume="+0%").save(str(path))


async def synthesize_signature_laugh(path: Path) -> None:
    import edge_tts
    # Playful, deliberately non-verbal-ish robotic syllables; processed separately below.
    await edge_tts.Communicate("هِ! هَ! هِ! هِ! هاااا!", VOICE, rate="-18%", pitch="+18Hz", volume="+0%").save(str(path))


def build_signature_audio(narration: Path, laugh_raw: Path, output: Path) -> None:
    # Distinctive signature: tiny pause, pitch-shifted synthetic laugh, short digital echo tail.
    # This is an intentionally designed TTS effect, not a claim of real human laughter.
    run([
        "ffmpeg", "-y", "-i", str(narration), "-i", str(laugh_raw),
        "-filter_complex",
        "[0:a]aresample=44100,apad=pad_dur=0.32[n];"
        "[1:a]asetrate=44100*1.14,aresample=44100,atempo=0.87719,"
        "aecho=0.8:0.55:55|110:0.28|0.12,volume=1.15[l];"
        "[n][l]concat=n=2:v=0:a=1[out]",
        "-map", "[out]", "-c:a", "libmp3lame", "-b:a", "192k", str(output)
    ])


def duration(path: Path) -> float:
    p = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
                       capture_output=True, text=True, check=True)
    return float(p.stdout.strip())


def main() -> int:
    still = OUT / "maslahati_existing_mascot_style.png"
    audio = OUT / "maslahati_robotic_voice.mp3"
    narration = OUT / "maslahati_narration_tmp.mp3"
    laugh_raw = OUT / "maslahati_laugh_raw_tmp.mp3"
    video = OUT / "maslahati_rude_test_short.mp4"
    make_image(still)
    asyncio.run(synthesize(narration))
    asyncio.run(synthesize_signature_laugh(laugh_raw))
    build_signature_audio(narration, laugh_raw, audio)
    narration.unlink(missing_ok=True)
    laugh_raw.unlink(missing_ok=True)
    secs = duration(audio) + 0.6
    run([
        "ffmpeg", "-y", "-loop", "1", "-framerate", "30", "-i", str(still),
        "-i", str(audio), "-t", f"{secs:.3f}",
        "-vf", "scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
        "-map", "0:v:0", "-map", "1:a:0", "-c:v", "libx264", "-preset", "ultrafast",
        "-tune", "stillimage", "-crf", "20", "-c:a", "aac", "-b:a", "160k",
        "-shortest", "-movflags", "+faststart", str(video)
    ])
    run(["ffmpeg", "-v", "error", "-i", str(video), "-f", "null", "-"])
    print(f"SUCCESS video={video} bytes={video.stat().st_size} duration={duration(video):.2f}s")
    print(f"IMAGE={still}")
    print(f"AUDIO={audio}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
