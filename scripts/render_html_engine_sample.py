"""Render a four-scene Persian science short about the structure of an atom."""
from pathlib import Path
import asyncio
import subprocess
import edge_tts
from app.html_motion_renderer import render_html_project

PROJECT = {
    "format": "short",
    "fps": 24,
    "title": "درون یک اتم چه می‌گذرد؟",
    "scenes": [
        {
            "duration": 4.0,
            "motif": "ellipse",
            "text": "در مرکز اتم، هسته‌ای بسیار کوچک قرار دارد.",
            "narration": "در مرکز هر اتم، هسته‌ای بسیار کوچک و فشرده قرار دارد.",
            "visual_prompt": "نمای نزدیک سینمایی از هسته درخشان اتم با ذره‌ای در حال گردش و حلقه پرسپکتیو",
            "palette": {"bg": "#050817", "primary": "#fbbf24", "secondary": "#fb7185", "accent": "#38bdf8", "glow": "rgba(251,191,36,0.25)"},
        },
        {
            "duration": 4.0,
            "motif": "cosmic",
            "text": "هسته از پروتون‌ها و نوترون‌ها ساخته شده است.",
            "narration": "این هسته از پروتون‌ها و نوترون‌ها ساخته شده؛ ذراتی که کنار هم نگه داشته می‌شوند.",
            "visual_prompt": "ذرات هسته‌ای و حلقه‌های انرژی در یک ساختار سه‌بعدی انتزاعی",
            "palette": {"bg": "#10091b", "primary": "#fb7185", "secondary": "#fbbf24", "accent": "#c084fc", "glow": "rgba(251,113,133,0.23)"},
        },
        {
            "duration": 4.0,
            "motif": "path",
            "text": "الکترون‌ها اطراف هسته حضور دارند.",
            "narration": "الکترون‌ها در ناحیه‌ای پیرامون هسته حضور دارند؛ اما مثل سیاره‌ها روی مدار ثابت نمی‌چرخند.",
            "visual_prompt": "مسیرهای نورانی پویا در فضای سه‌بعدی اطراف مرکز اتم، با حرکت دوربین",
            "palette": {"bg": "#07130f", "primary": "#4ade80", "secondary": "#2dd4bf", "accent": "#facc15", "glow": "rgba(74,222,128,0.22)"},
        },
        {
            "duration": 4.0,
            "motif": "light",
            "text": "ابر احتمال، جای حضور الکترون را نشان می‌دهد.",
            "narration": "در مدل کوانتومی، ابر احتمال نشان می‌دهد الکترون را در کدام ناحیه‌ها محتمل‌تر است پیدا کنیم.",
            "visual_prompt": "کره نورانی و هاله حجمی نرم به‌عنوان نمایش مفهومی ابر احتمال الکترون",
            "palette": {"bg": "#090b1d", "primary": "#c084fc", "secondary": "#22d3ee", "accent": "#fbbf24", "glow": "rgba(192,132,252,0.28)"},
        },
    ],
}

if __name__ == "__main__":
    out = Path("artifacts/bamo-atom-structure-full-quality.mp4")
    out.parent.mkdir(parents=True, exist_ok=True)
    silent = out.with_name("bamo-atom-structure-silent.mp4")
    render_html_project(PROJECT, silent, fps=24, width=720, height=1280)
    narration = "در مرکز هر اتم، هسته‌ای بسیار کوچک و فشرده قرار دارد. این هسته از پروتون‌ها و نوترون‌ها ساخته شده؛ ذراتی که کنار هم نگه داشته می‌شوند. الکترون‌ها در ناحیه‌ای پیرامون هسته حضور دارند؛ اما مثل سیاره‌ها روی مدار ثابت نمی‌چرخند. در مدل کوانتومی، ابر احتمال نشان می‌دهد الکترون را در کدام ناحیه‌ها محتمل‌تر است پیدا کنیم."
    voice = out.with_name("bamo-atom-structure-narration.mp3")

    async def make_voice():
        communicate = edge_tts.Communicate(narration, "fa-IR-FaridNeural", rate="+0%", volume="+0%")
        await communicate.save(str(voice))

    asyncio.run(make_voice())
    subprocess.run([
        "ffmpeg", "-y", "-i", str(silent), "-i", str(voice),
        "-filter_complex", "[1:a]apad,atrim=duration=16,asetpts=PTS-STARTPTS[a]",
        "-map", "0:v:0", "-map", "[a]", "-c:v", "copy", "-c:a", "aac",
        "-b:a", "160k", "-movflags", "+faststart", str(out)
    ], check=True, capture_output=True, text=True)
    print(f"HTML_ENGINE_SAMPLE={out.resolve()}")
    print(f"SIZE_BYTES={out.stat().st_size}")
