# BAMO Voice + Text Lock

## موتور صدا در کارخانه (GitHub Actions)

صدای گوینده روی Actions از زنجیرهٔ `app/tts.py` می‌آید:

1. ElevenLabs (اگر `ELEVENLABS_API_KEY` باشد)
2. Azure Speech (اگر کلید Azure باشد)
3. **Edge TTS** — پیش‌فرض تولید: `fa-IR-FaridNeural` (فارسی طبیعی مردانه)
4. Piper محلی (اختیاری)

در `daily_run.yml` قفل شده:

```yaml
TTS_PROVIDER: edge-tts
TTS_VOICE: fa-IR-FaridNeural
```

> نکته: صدای Grok Voice (مثل Orion) فقط داخل محیط Grok در دسترس است و قابل نصب روی GitHub Actions نیست. معادل تولیدی کارخانه، Edge TTS با صدای FaridNeural است.

## قانون Text Lock

ماژول: `app/bamo_text_lock.py`

- `on_screen_text` **باید برابر** `spoken_text` / narration باشد
- `visual_query` از همان متن ساخته می‌شود (نه تصویر نامرتبط)
- `bamo_production_renderer` قبل از رندر این قفل را اعمال می‌کند

## اجرای روزانه

Workflow: `.github/workflows/daily_run.yml`

- زمان‌بندی تهران: ۰۷، ۱۰، ۱۲، ۱۵، ۱۸، ۲۱
- HTML renderer اولویت دارد (`BAMO_PREFER_HTML_RENDERER=1`)
- تا تأیید بصری، فقط `--dry-run` و بدون آپلود عمومی
