# BAMO Motion Engine (Path B)

موتور هوشمند تبدیل متن به موشن‌گرافی سینمایی — نسخه HTML + Playwright

## ساختار

```
preview/bamo-engine/
├── director/          # مغز هوشمند
│   ├── mood.js        # تشخیص حس و پالت
│   ├── parser.js      # تجزیه متن فارسی/انگلیسی
│   ├── timeline.js    # ساخت timeline
│   └── index.js       # API: createProject(text)
├── presets/           # سبک‌های آماده
│   ├── epic-golden.json
│   └── spiritual-warm.json
└── README.md

preview/bamo-engine-pipeline.html   # موتور بصری اصلی (Canvas)
app/html_motion_renderer.py         # پل Python → Playwright → MP4
```

## نحوه کار در کارخانه

1. `spiritual_pipeline` سناریو و TTS را می‌سازد
2. `bamo_production_renderer` پروژه صحنه را آماده می‌کند
3. اگر `BAMO_PREFER_HTML_RENDERER=1` و Playwright موجود باشد:
   - موتور HTML با افکت نور/ذرات/جرقه رندر می‌شود
4. در غیر این صورت به موتور CPU 3D قبلی برمی‌گردد
5. صدا + زیرنویس + موسیقی میکس و خروجی نهایی ساخته می‌شود

## پیش‌نمایش محلی

فایل زیر را در مرورگر باز کنید:

```
preview/bamo-engine-pipeline.html
```

یا نسخه تعاملی کامل:

```
preview/bamo-engine.html
```

## Director API (آینده / Node)

```js
const { createProject } = require('./director');
const project = createProject("گاهی فقط باید صبر کنی...");
// project.scenes → آماده برای رندرر
```

## وضعیت فعلی

- ✅ Smart Director (mood + parser + timeline)
- ✅ موتور Canvas با نور، ذرات، جرقه، bloom
- ✅ اتصال به pipeline تولید روزانه
- ✅ Presetهای اولیه
- ⏳ صدای procedural
- ⏳ لایه Three.js اختیاری
- ⏳ CLI یک‌فرمانه کامل

## English summary

Intelligent HTML/Canvas text-to-motion engine for BAMO automated Shorts factory. Smart Director analyzes Persian/English text, chooses mood, palette, camera and motif. Pipeline renderer uses Playwright to capture frames and FFmpeg to produce final MP4 with existing TTS + captions.
