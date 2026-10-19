# Viral Short Engine

موتور ساخت شورت عمودی از روی فایل داستان JSON.

## ورودی

فایل JSON در `stories/` مثل `sapling.json`:

```json
{
  "voice": "fa-IR-FaridNeural",
  "rate": "-15%",
  "characters": {
    "boy": "same 6-year-old ...",
    "elder": "same elderly man ..."
  },
  "beats": [
    { "line": "متن فارسی گوینده",
      "prompt": "English visual prompt with {boy} {elder} placeholders" }
  ]
}
```

## اجرا روی Colab (GitHub Actions)

Workflow: `colab_photoreal.yml`  
Secret لازم: `COLAB_CLI_TOKEN_JSON`

```
engine/viral_short.py  →  /content/final_story.mp4
```

## محدودیت صادقانه (رایگان)

- تصویر: SDXL-Turbo روی GPU رایگان Colab (هنوز فریم ثابت + حرکت Ken Burns است، نه ویدیو ژنراتور سینمایی تجاری)
- صدا: Edge TTS فارسی (طبیعی‌تر از ربات ساده، ولی هنوز سطح استودیو انسانی کامل نیست)
- برای نزدیک شدن به نمونه وایرال: شخصیت ثابت در prompt + داستان کوتاه + زیرنویس زرد

## داستان جدید

1. یک فایل در `stories/my_story.json` بساز
2. Workflow را با همان مسیر story اجرا کن (یا پیش‌فرض sapling)
3. آرتیفکت `final_story.mp4` را دانلود کن
