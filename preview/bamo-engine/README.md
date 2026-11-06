# BAMO Motion Engine (Path B)

موتور هوشمند تبدیل متن به موشن‌گرافی سینمایی برای کارخانه محتوای BAMO

## ساختار

```
preview/bamo-engine/
├── director/                 # مغز هوشمند (JS)
│   ├── mood.js
│   ├── parser.js
│   ├── timeline.js
│   └── index.js
├── presets/
│   ├── epic-golden.json
│   ├── spiritual-warm.json
│   ├── dark-mystery.json
│   ├── hopeful-growth.json
│   └── cyberpunk-neon.json
└── README.md

preview/bamo-engine-pipeline.html   # موتور بصری Canvas
app/bamo_director.py                # Director پایتون (pipeline)
app/bamo_procedural_audio.py        # موسیقی ambient بر اساس حس
app/html_motion_renderer.py         # Playwright → MP4
app/bamo_production_renderer.py     # اتصال به کارخانه روزانه
scripts/bamo_engine_selftest.py     # تست سریع
```

## قابلیت‌های فعلی

- Smart Director: تشخیص حس (۸ حالت) + پالت + موتیف + دوربین
- موتور Canvas: نور، ذرات، جرقه، bloom، film grain، transition، تایپوگرافی kinetic
- موسیقی procedural متناسب با mood
- اتصال کامل به pipeline روزانه Shorts
- Fallback به موتور CPU 3D در صورت نبود Playwright

## تست سریع (بدون مرورگر)

```bash
python scripts/bamo_engine_selftest.py
```

## متغیرهای محیطی

| متغیر | پیش‌فرض | معنی |
|--------|---------|------|
| `BAMO_PREFER_HTML_RENDERER` | `1` | استفاده از موتور HTML |
| `BAMO_PROCEDURAL_AUDIO` | `1` | موسیقی ambient بر اساس حس |

## پیش‌نمایش بصری

فایل زیر را در مرورگر باز کنید:

```
preview/bamo-engine-pipeline.html
```

## English

Intelligent HTML/Canvas text-to-motion engine for the BAMO automated Shorts factory. Smart Director analyzes Persian/English text for mood, palette and motif. Pipeline uses Playwright frame capture + FFmpeg, with mood-driven procedural ambient audio and safe fallback to the CPU 3D engine.
