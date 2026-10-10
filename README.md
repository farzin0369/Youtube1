# ImamAli110 — Scene-Grounded YouTube Agent

تولید و انتشار خودکار محتوای ImamAli110 بدون نیاز به کامپیوتر شخصی.

## معماری فعلی

**مسیر GPU سینمایی:** مدل زبانی محلی Ollama → فیلمنامهٔ صحنه‌محور → گویندگی فارسی → کلیپ‌های CogVideoX روی GPU در Google Colab → تدوین/صدا/زیرنویس → Quality Gate → انتشار عمومی در YouTube.

**مسیر جایگزین CPU:** برای آزمون ساختار، تولید پیش‌نمایش و اجرای smoke test در GitHub Actions؛ این مسیر جایگزین کیفیت تصویری CogVideoX نیست.

گردش‌کار `colab-gpu-publishing.yml` از Colab CLI برای درخواست GPU استفاده می‌کند و روزانه ساعت **۰۶:۰۰ و ۱۸:۰۰** به وقت تهران اجرا می‌شود. دسترسی GPU تابع احراز هویت و سهمیه‌های Google Colab است.

GitHub می‌گوید standard runner برای repository عمومی رایگان و نامحدود است؛ runner استاندارد GPU ندارد، بنابراین موتور ویدئو در این مسیر از رندر سینمایی procedural/animated روی CPU استفاده می‌کند.

## وابستگی‌های سیستم

برای اجرای محلی یا مسیر CPU، باید `ffmpeg` و `ffprobe` در `PATH` باشند. مسیر Colab GPU این وابستگی‌ها را در مرحلهٔ آماده‌سازی نصب می‌کند؛ تست CPU در GitHub Actions نیز آن‌ها را نصب می‌کند. فونت‌های `Noto` برای زیرنویس فارسی توصیه می‌شوند.

## زمان‌بندی تهران

- **۰۶:۰۰ و ۱۸:۰۰ تهران — تولید شورت سینمایی و انتشار عمومی از طریق Colab GPU**
- مسیر CPU فقط برای آزمون دستی است و به‌عنوان تولید سینمایی زمان‌بندی نمی‌شود.

## موتور محتوا

- تحقیق و انتخاب موضوع از منابع مجاز پروژه (نهج‌البلاغه + قرآن با ارجاع دقیق)
- فیلمنامه فارسی با کنترل منبع
- عنوان با پیشوند ثابت **Imam Ali ✨**
- صدای مردانه طبیعی `fa-IR-FaridNeural` (Edge TTS) با fallback Piper
- ویدئوی متحرک سینمایی مفهومی، نه اسلایدشو ثابت؛ بدون چهره مقدس
- زیرنویس SRT
- thumbnail
- quality gate
- انتشار مستقیم در YouTube با `publishAt`
- پاسخ خودکار به کامنت‌های امن و انتقال موارد حساس به pending

## گویندگی فارسی طبیعی

مسیر تولید از صدای عصبی فارسی `fa-IR-FaridNeural` در Edge TTS استفاده می‌کند تا لحن طبیعی‌تری داشته باشد و به اعتبار پولی OpenAI وابسته نباشد. اگر سرویس در دسترس نباشد، صدای محلی Piper (`fa_IR-amir-medium`) به‌عنوان fallback باقی می‌ماند.

## Secrets موردنیاز

در GitHub Actions این Secretها لازم است:

- `YOUTUBE_CLIENT_ID`
- `YOUTUBE_CLIENT_SECRET`
- `YOUTUBE_REFRESH_TOKEN`
- `COLAB_CLI_TOKEN_JSON` (برای درخواست GPU از Colab CLI)

رمز عبور Google هرگز داخل Repository ذخیره نمی‌شود.

## اجرای دستی

برای انتشار زمان‌بندی‌شده، workflow با نام **ImamAli110 autonomous Colab GPU publishing** فعال است. می‌توانی آن را دستی (workflow_dispatch) هم اجرا کنی.

پیش‌نمایش CPU فقط برای عیب‌یابی دستی باقی می‌ماند.

## مسیر GPU

تولید اصلی از `google-colab-cli` برای درخواست T4 GPU استفاده می‌کند. کلید API مدل زبانی لازم نیست؛ مدل `llama3.2:3b` روی محیط Colab اجرا می‌شود. احراز هویت Colab CLI باید به‌صورت امن در GitHub Secret با نام `COLAB_CLI_TOKEN_JSON` قرار گیرد. Google همچنان سهمیه و دسترسی GPU را کنترل می‌کند.

تنظیمات محافظه‌کارانه T4 فعلی: ۱۷ فریم، ۸ گام، ۳ صحنه برای شورت.

## اصل طراحی

**Serve the message first. Let the algorithm follow.**

این Agent برای ImamAli110 طراحی شده و YouTube مقصد انتشار است.

## Scene plan, checkpointing and Colab recovery

The CogVideoX path now uses a versioned `scene_plan.json` as the shared contract for scene narration, visual prompts, on-screen text and estimated duration. Each generated scene clip and status is checkpointed atomically; retries with the same `PIPELINE_RUN_ID` can reuse completed clips when output storage persists. The Colab notebook mounts Google Drive and stores the output directory there.

Scheduled videos are uploaded privately with YouTube `publishAt` metadata, then released publicly by YouTube at the requested time. Colab GPU availability is not guaranteed, and GitHub-hosted CPU Actions are not a substitute for GPU-generated CogVideoX footage. Output is encoded at 1080x1920 and 24 output fps; this does not mean the underlying model natively generates 24 fps or 4K/8K video.

See [docs/PRODUCTION_ARCHITECTURE.md](docs/PRODUCTION_ARCHITECTURE.md) for checkpoint semantics, limitations, release gates and the remaining roadmap. Regression tests live in `tests/` and run in pull requests.

## مدیریت کامنت و گزارش روزانه

- پاسخ‌های موفق با شناسهٔ کامنت ثبت می‌شوند تا اجرای دوباره تا حد امکان پاسخ تکراری نفرستد.
- موارد مشکوک به اسپم یا حساس به `output/pending_replies.json` می‌روند؛ حذف و گزارش خودکار کامنت‌ها عمداً فعال نیست تا اشتباه برگشت‌ناپذیر رخ ندهد.
- workflow روزانهٔ `Channel health and daily report` تست‌ها و وضعیت دسترسی YouTube را بررسی می‌کند، روی چند ویدئوی اخیرِ عمومی/غیرفهرست‌شده پاسخ‌گویی محافظه‌کارانه را اجرا می‌کند و گزارش سلامت، لاگ تست، فهرست تغییرات ۲۴ ساعت اخیر و صف بررسی انسانی را به‌صورت Artifact نگه می‌دارد.
- شناسهٔ پاسخ‌ها در GitHub Actions Cache نگه‌داری می‌شود؛ ویدئوهای خصوصی نادیده گرفته می‌شوند و موارد حساس یا مشکوک به اسپم برای بررسی انسانی باقی می‌مانند.
