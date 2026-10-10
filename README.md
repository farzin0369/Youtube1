# ImamAli110 — Cloud-First YouTube Agent

تولید و انتشار خودکار محتوای ImamAli110 بدون نیاز به کامپیوتر شخصی.

## معماری رایگان

موضوع/منبع → فیلمنامه فارسی → گویندگی عصبی فارسی Edge TTS (صدای FaridNeural) با fallback رایگان Piper → رندر سینمایی CPU → FFmpeg → زیرنویس → Quality Gate → YouTube → پاسخ به کامنت‌ها

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

## گویندگی فارسی طبیعی

مسیر تولید از صدای عصبی فارسی `fa-IR-FaridNeural` در Edge TTS استفاده می‌کند تا لحن طبیعی‌تری داشته باشد و به اعتبار پولی OpenAI وابسته نباشد. اگر سرویس در دسترس نباشد، صدای محلی Piper (`fa_IR-amir-medium`) به‌عنوان fallback باقی می‌ماند.

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
## Scene plan, checkpointing and Colab recovery

The CogVideoX path now uses a versioned `scene_plan.json` as the shared contract for scene narration, visual prompts, on-screen text and estimated duration. Each generated scene clip and status is checkpointed atomically; retries with the same `PIPELINE_RUN_ID` can reuse completed clips when output storage persists. The Colab notebook mounts Google Drive and stores the output directory there.

For an initial validation run, keep YouTube privacy set to `private`. Colab GPU availability is not guaranteed, and GitHub-hosted CPU Actions are not a substitute for GPU-generated CogVideoX footage. Output is encoded at 1080x1920 and 24 output fps; this does not mean the underlying model natively generates 24 fps or 4K/8K video.

See [docs/PRODUCTION_ARCHITECTURE.md](docs/PRODUCTION_ARCHITECTURE.md) for checkpoint semantics, limitations, release gates and the remaining roadmap. Regression tests live in `tests/` and run in pull requests.
