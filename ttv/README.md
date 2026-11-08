# TTV — Text-to-Video Engine (BAMO)

موتور ماژولار تبدیل متن به ویدئو. فاز ۱: تحلیل متن و تولید پلان صحنه.

## ساختار هدف

```
ttv/
├── core/
│   ├── text_analyzer.py     ✅
│   ├── scene_generator.py   ✅
│   ├── asset_manager.py     (بعدی)
│   └── renderer.py          (بعدی)
├── effects/
├── audio/
├── utils/
├── styles/
└── render.py
```

## فاز ۱ — استفاده سریع

```python
from ttv.core import TextAnalyzer, SceneGenerator

text = """
شفق قطبی چیست؟
خورشید ذره‌های باردار را به فضا می‌فرستد.
میدان مغناطیسی زمین آن‌ها را به سوی قطب‌ها می‌کشاند.
"""

analysis = TextAnalyzer().analyze(text)
plan = SceneGenerator(aspect="portrait").from_analysis(analysis)

print(analysis.language, analysis.tone, analysis.keywords)
for s in plan.scenes:
    print(s.start_sec, s.duration_sec, s.caption, "|", s.visual_query)
```

## خروجی‌ها

- `TextAnalysis`: زبان، لحن، کلمات‌کلیدی، موضوعات، query بصری، mood موسیقی، زمان تخمینی گفتار
- `ScenePlan`: لیست `Scene` زمان‌بندی‌شده با narration، caption، motion، transition، visual_query

## قدم بعدی

1. `asset_manager.py` — دانلود استوک / کش
2. `audio/tts_engine.py` — Edge-TTS FA/EN + سینک
3. `renderer.py` + FFmpeg/HTML — رندر واقعی
