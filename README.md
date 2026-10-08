# ImamAli110 — Cloud-First YouTube Agent

تولید و انتشار خودکار محتوای ImamAli110 بدون نیاز به کامپیوتر شخصی.

## معماری رایگان

موضوع/منبع → فیلمنامه فارسی → Piper TTS محلی → رندر سینمایی CPU → FFmpeg → زیرنویس → Quality Gate → YouTube → پاسخ به کامنت‌ها

نسخه فعلی برای اجرای روزانه از GitHub-hosted standard runner استفاده می‌کند و به self-hosted GPU وابسته نیست.

GitHub می‌گوید standard runner برای repository عمومی رایگان و نامحدود است؛ runner استاندارد GPU ندارد، بنابراین موتور ویدئو در این مسیر از رندر سینمایی procedural/animated روی CPU استفاده می‌کند.

## زمان‌بندی تهران

- **05:35 — Short**
- **20:30 — Long**

## موتور محتوا

- تحقیق و انتخاب موضوع از منابع مجاز پروژه
- فیلمنامه فارسی با کنترل منبع
- عنوان با پیشوند ثابت **Imam Ali ✨**
- Piper با صدای فارسی محلی
- ویدئوی متحرک سینمایی، نه اسلایدشو ثابت
- زیرنویس SRT
- thumbnail
- quality gate
- انتشار مستقیم در YouTube
- پاسخ خودکار به کامنت‌های امن و انتقال موارد حساس به pending

## Piper فارسی

Workflow در هر اجرای تازه، صدای فارسی Piper را از مخزن open-source آن دریافت می‌کند. صدای fa_IR-amir-medium در مجموعه Piper موجود است.

## Secrets موردنیاز YouTube

فقط این سه Secret را در GitHub Actions قرار بده:

- YOUTUBE_CLIENT_ID
- YOUTUBE_CLIENT_SECRET
- YOUTUBE_REFRESH_TOKEN

رمز عبور Google هرگز داخل Repository ذخیره نمی‌شود.

## اجرای دستی

از GitHub: Actions → ImamAli110 cloud-free production → Run workflow

می‌توانی short یا long و همچنین dry_run را انتخاب کنی.

## مسیر GPU اختیاری

اگر در آینده GPU رایگان/اختصاصی پیدا شد، موتور CogVideoX هنوز در کد باقی مانده و می‌تواند با VIDEO_ENGINE=cogvideox فعال شود؛ اما تولید روزانه فعلی به GPU پولی GitHub وابسته نیست.

## اصل طراحی

**Serve the message first. Let the algorithm follow.**

این Agent برای ImamAli110 طراحی شده و YouTube مقصد انتشار است.