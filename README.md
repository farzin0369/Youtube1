# BAMO — Persian multi-topic YouTube production

مخزن فعال پروژه: [farzin0369/Youtube1](https://github.com/farzin0369/Youtube1)
شاخهٔ کاری این مرحله: `feat/bamo-hyperframes-engine`

**وضعیت مهم:** این شاخه شامل نمونهٔ رندر واقعی HyperFrames روی CPU و اتصال آزمایشی گویندگی فارسی است. این موتور هنوز جایگزین کامل رندرر خط تولید اصلی `app/spiritual_pipeline.py` نشده است؛ اتصال نهایی باید پس از گذراندن آزمون‌های رسانه‌ای و بررسی انسانی انجام شود.

## برند و سیاست انتشار

- برند: **BAMO**
- هندل پیکربندی‌شده: [@12bamo](https://www.youtube.com/@12bamo)
- هشتگ برند: `#12bamo`
- زبان: فارسی؛ منطقهٔ زمانی: تهران
- موضوعات: معنویت و اخلاق، علم و ریاضیات، فلسفه و روان‌شناسی، تاریخ، هنر و موسیقی، ورزش، سرگرمی، اخبار راستی‌آزمایی‌شده و رشد فردی.
- **انتشار عمومی خودکار خاموش است.** اجرای زمان‌بندی‌شده فقط پیش‌نمایش می‌سازد. انتشار عمومی فقط با انتخاب صریح `publish=true` در اجرای دستی ممکن است؛ آپلود خصوصی نیز انتخاب جداگانه دارد.

## موتور موشن‌گرافیک HyperFrames

- upstream: [heygen-com/hyperframes](https://github.com/heygen-com/hyperframes)
- نسخهٔ CLI در workflow به‌صورت ثابت pin شده است.
- رندر CPU با Node.js، مرورگر headless و FFmpeg؛ بدون الزام GPU.
- خروجی هدف: عمودی 1080×1920، 30fps.
- ساختار نمونه: چهار صحنهٔ authored، حرکت دوربین، لایه‌های هندسی، تایپوگرافی فارسی و ترنزیشن.
- اسکریپت: `scripts/render_bamo_hyperframes.py`
- brief نمونه: `examples/bamo_first_film.json`
- افزودن صدا و زیرنویس زمان‌بندی‌شده: `scripts/add_bamo_audio.py`
- workflow: `.github/workflows/bamo_hyperframes_cpu_render.yml`
- مستند فنی: `docs/BAMO_HYPERFRAMES_INTEGRATION.md`

HyperFrames در این معماری یک backend تخصصی رندر است، نه جایگزین لایهٔ تحریریه. ۱۱ نقش تعریف‌شده در brief فعلی به‌عنوان قرارداد تحویل و کنترل ساختاری بررسی می‌شوند؛ اجرای کامل و مستقل همهٔ agentها و اتصال خودکار خروجی هرکدام به موتور، هنوز کار باقی‌مانده است. Manim برای ریاضیات و Blender برای صحنه‌های سه‌بعدی سنگین می‌توانند backendهای تخصصی اختیاری باشند؛ وابستگی اجباری رندر روزانه به GPU یا Blender ایجاد نکنید.

## آزمون و دریافت خروجی

1. وارد GitHub Actions مخزن شوید.
2. workflow با نام **BAMO HyperFrames CPU render** را باز کنید.
3. اجرای موفق را انتخاب کنید.
4. در بخش Artifacts فایل `BAMO-HyperFrames-CPU-preview-<run_id>` را دریافت کنید.
5. فایل MP4، صدای AAC، زیرنویس VTT و manifest را بررسی کنید.

workflow باید این کنترل‌ها را بگذراند:
- clone و آزمون پروژهٔ upstream که در submodule pin شده است؛
- رندر واقعی 600 فریم برای نمونهٔ 20 ثانیه‌ای؛
- گویندگی فارسی Edge TTS؛
- تولید زیرنویس VTT؛
- بررسی وجود stream ویدئو و صدای AAC، وضوح، مدت و اندازهٔ فایل؛
- ذخیرهٔ artifact فقط برای بازبینی، بدون آپلود به YouTube.

## خط تولید اصلی و ایمنی

خط تولید قدیمی در `app/spiritual_pipeline.py` نگه داشته شده است و هنوز backend مجزای خود را دارد. تا وقتی پل رسمی بین خروجی ۱۱ نقش، موتور HyperFrames و کنترل کیفیت خط تولید اصلی ساخته و تست نشده، نباید ادعا کرد که کل چرخهٔ تولید به HyperFrames منتقل شده است.

workflow روزانهٔ `.github/workflows/daily_run.yml` در این شاخه فقط dry-run و artifact بازبینی انجام می‌دهد. برای انتشار عمومی باید اجرای دستی و تأیید صریح انتخاب شود. هیچ workflow آزمایشی HyperFrames مجوز انتشار ندارد.

## منابع و پیش‌نیازها

- Node.js 22+
- Python 3.11+ برای ابزارهای کمکی
- FFmpeg و ffprobe
- دسترسی شبکه برای دریافت بسته‌های npm و Edge TTS
- GitHub Actions runner با CPU

هیچ کلید YouTube، API token یا فایل OAuth را داخل مخزن commit نکنید. رندر preview به OAuth یوتیوب احتیاج ندارد.
