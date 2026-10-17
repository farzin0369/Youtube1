#!/usr/bin/env python3
"""Create a one-image Persian absurdist meme Short with deliberately synthetic TTS."""
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
    "مشاور انگیزشی می‌گه:",
    "ناامید نشو عزیزم!",
    "تو قطعاً به گا رفتی...",
    "ولی با اعتمادبه‌نفس ادامه بده! 😂",
]
FULL_SCRIPT = "مشاور انگیزشی می‌گه... ناامید نشو عزیزم! تو قطعاً به گا رفتی... ولی با اعتمادبه‌نفس ادامه بده!"
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "output/diego_meme")
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
    # Meme-card framing and comic accents
    d.rounded_rectangle((28, 26, W-28, H-26), radius=34, outline=(255, 207, 82), width=5)
    centered(d, 92, "دانشگاه انگیزشِ الکی", font(34, True), (255, 221, 108))
    centered(d, 150, "جلسهٔ مشاوره — جلسهٔ آخر 😭", font(25, True), (255, 255, 255))

    # A frazzled cartoon potato-cat therapist, all drawn locally; one image only
    # body
    d.ellipse((164, 320, 556, 790), fill=(255, 183, 67), outline=(30, 19, 42), width=9)
    # ears
    d.polygon([(220, 390), (224, 275), (315, 352)], fill=(255, 183, 67), outline=(30, 19, 42))
    d.polygon([(405, 352), (500, 275), (498, 410)], fill=(255, 183, 67), outline=(30, 19, 42))
    d.polygon([(242, 355), (242, 315), (283, 365)], fill=(255, 112, 133))
    d.polygon([(435, 365), (480, 315), (475, 370)], fill=(255, 112, 133))
    # glasses, eyes and brows
    d.arc((230, 425, 345, 535), 190, 345, fill=(30, 19, 42), width=13)
    d.arc((370, 425, 485, 535), 195, 350, fill=(30, 19, 42), width=13)
    d.ellipse((253, 455, 323, 520), outline=(30, 19, 42), width=9)
    d.ellipse((391, 455, 461, 520), outline=(30, 19, 42), width=9)
    d.line((323, 483, 391, 483), fill=(30, 19, 42), width=9)
    d.ellipse((282, 477, 297, 501), fill=(30, 19, 42))
    d.ellipse((416, 477, 431, 501), fill=(30, 19, 42))
    # deadpan mouth, sweat and whiskers
    d.arc((302, 535, 420, 625), 15, 165, fill=(30, 19, 42), width=11)
    d.ellipse((463, 545, 495, 590), fill=(92, 204, 255), outline=(255,255,255), width=3)
    for yy in (570, 602):
        d.line((176, yy, 255, yy-12), fill=(30, 19, 42), width=5)
        d.line((465, yy-12, 544, yy), fill=(30, 19, 42), width=5)
    # tiny tie and therapist clipboard
    d.polygon([(335, 650), (385, 650), (370, 710), (350, 710)], fill=(238, 61, 111), outline=(30, 19, 42))
    d.rounded_rectangle((422, 660, 535, 790), radius=10, fill=(245, 240, 214), outline=(30, 19, 42), width=5)
    d.line((442, 694, 515, 694), fill=(40, 35, 55), width=4)
    d.line((442, 720, 505, 720), fill=(40, 35, 55), width=4)
    d.line((442, 746, 511, 746), fill=(40, 35, 55), width=4)

    centered(d, 855, "«ناامید نشو عزیزم!»", font(38, True), (255, 255, 255), 2, (15, 10, 28))
    centered(d, 923, "تو قطعاً به گا رفتی…", font(42, True), (255, 95, 132), 2, (15, 10, 28))
    centered(d, 991, "ولی با اعتمادبه‌نفس ادامه بده 😂", font(28, True), (255, 221, 108), 2, (15, 10, 28))
    centered(d, 1122, "دیگو | مشاورهٔ رایگان، نتیجهٔ تضمینی؟", font(22, True), (238, 225, 255))
    im.save(path, quality=95)


async def synthesize(path: Path) -> None:
    import edge_tts
    # Slightly brisker and higher-pitched to make the synthetic delivery part of the joke.
    await edge_tts.Communicate(FULL_SCRIPT, VOICE, rate="+18%", pitch="+8Hz", volume="+0%").save(str(path))


def duration(path: Path) -> float:
    p = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
                       capture_output=True, text=True, check=True)
    return float(p.stdout.strip())


def main() -> int:
    still = OUT / "diego_funny_single_image.png"
    audio = OUT / "diego_robotic_voice.mp3"
    video = OUT / "diego_funny_short.mp4"
    make_image(still)
    asyncio.run(synthesize(audio))
    secs = duration(audio) + 0.6
    run([
        "ffmpeg", "-y", "-loop", "1", "-framerate", "30", "-i", str(still),
        "-i", str(audio), "-t", f"{secs:.3f}",
        "-vf", "scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2,format=yuv420p",
        "-map", "0:v:0", "-map", "1:a:0", "-c:v", "libx264", "-preset", "ultrafast",
        "-tune", "stillimage", "-crf", "20", "-c:a", "aac", "-b:a", "160k",
        "-shortest", "-movflags", "+faststart", str(video)
    ])
    # Verify it is a decodable vertical MP4 with audio.
    run(["ffmpeg", "-v", "error", "-i", str(video), "-f", "null", "-"])
    print(f"SUCCESS video={video} bytes={video.stat().st_size} duration={duration(video):.2f}s")
    print(f"IMAGE={still}")
    print(f"AUDIO={audio}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
