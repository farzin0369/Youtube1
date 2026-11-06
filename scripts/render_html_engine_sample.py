"""Render a standalone four-scene Persian HTML-engine proof video."""
from pathlib import Path
from app.html_motion_renderer import render_html_project

PROJECT = {
    "format": "short",
    "fps": 24,
    "scenes": [
        {
            "duration": 4.0,
            "motif": "wave",
            "text": "وقتی دو موج به هم می‌رسند، چه اتفاقی می‌افتد؟",
            "narration": "وقتی دو موج به هم می‌رسند، چه اتفاقی می‌افتد؟",
            "visual_prompt": "دو موج نئونی متحرک که در فضا با هم تداخل می‌کنند",
            "palette": {"bg": "#050817", "primary": "#22d3ee", "secondary": "#a78bfa", "accent": "#f472b6", "glow": "rgba(34,211,238,0.22)"},
        },
        {
            "duration": 4.0,
            "motif": "ellipse",
            "text": "گاهی موج‌ها همدیگر را تقویت می‌کنند.",
            "narration": "گاهی موج‌ها همدیگر را تقویت می‌کنند.",
            "visual_prompt": "مسیر بیضوی نورانی با دو کانون و ذره‌ای در حال گردش",
            "palette": {"bg": "#10091b", "primary": "#fbbf24", "secondary": "#fb7185", "accent": "#38bdf8", "glow": "rgba(251,191,36,0.22)"},
        },
        {
            "duration": 4.0,
            "motif": "path",
            "text": "و گاهی یکدیگر را خنثی می‌کنند.",
            "narration": "و گاهی یکدیگر را خنثی می‌کنند.",
            "visual_prompt": "دو مسیر نورانی متقابل با نقاط درخشان متحرک",
            "palette": {"bg": "#07130f", "primary": "#4ade80", "secondary": "#2dd4bf", "accent": "#facc15", "glow": "rgba(74,222,128,0.2)"},
        },
        {
            "duration": 4.0,
            "motif": "light",
            "text": "این همان تداخل سازنده و ویرانگر است.",
            "narration": "این همان تداخل سازنده و ویرانگر است.",
            "visual_prompt": "انفجار کنترل‌شده نور و حلقه‌های درخشان موجی",
            "palette": {"bg": "#090b1d", "primary": "#c084fc", "secondary": "#22d3ee", "accent": "#fbbf24", "glow": "rgba(192,132,252,0.24)"},
        },
    ],
}

if __name__ == "__main__":
    out = Path("artifacts/bamo-html-engine-sample.mp4")
    render_html_project(PROJECT, out, fps=24, width=720, height=1280)
    print(f"HTML_ENGINE_SAMPLE={out.resolve()}")
    print(f"SIZE_BYTES={out.stat().st_size}")
