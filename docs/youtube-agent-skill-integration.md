# ادغام YouTube Agent Skill در مخزن ImamAli110

## وضعیت فعلی این شاخه
نسخهٔ کامل ۱۱ دستور/مهارت بالادستی به همراه شش ابزار Python و فایل مجوز MIT در `.claude/skills/yt-*/` قرار گرفته است. فهرست و مثال اجرا: [`.claude/skills/README.md`](../.claude/skills/README.md). بررسی موتور موجود: [`docs/YOUTUBE_ENGINE_AUDIT.md`](YOUTUBE_ENGINE_AUDIT.md).

## یازده مهارت
`yt-script`, `yt-package`, `yt-edit`, `yt-comment`, `yt-plan`, `yt-viral`, `yt-retention`, `yt-shorts`, `yt-seo`, `yt-chapters`, `yt-audit`.

این‌ها برای تولید/بازبینی متن، بسته‌بندی عنوان و کاور، تدوین مبتنی بر transcript، دسته‌بندی کامنت و پیش‌نویس پاسخ، برنامه‌ریزی، بررسی ویدئوهای عمومی رقبا، تحلیل retention، پیشنهاد Shorts، SEO، فصل‌بندی و ممیزی کانال هستند.

## موتور ساخت ویدئوی فعلی
مسیر زمان‌بندی روزانه `daily_run.yml → scripts/daily_run.py → app/spiritual_pipeline.py` است. این مسیر در حال حاضر از Pexels footage عمودی، Edge TTS پیش‌فرض، FFmpeg، زیرنویس و QA استفاده می‌کند؛ CogVideoX در این workflow روزانه اجرا نمی‌شود. موتور CogVideoX جداگانه در `app/local_video_engine.py` قرار دارد و از مسیر قدیمی‌تر `app/pipeline.py` با انتخاب صریح `VIDEO_ENGINE=cogvideox` قابل انتخاب است. جزئیات، محدودیت‌ها و پیش‌نیازها در گزارش معماری آمده‌اند.

## مرز مهم
این تغییرها تمام ۱۱ مهارت را به مخزن اضافه می‌کند، اما به‌تنهایی باعث اجرای خودکار مهارت‌ها در GitHub Actions نمی‌شود؛ Actions فایل‌های `SKILL.md` را اجرا نمی‌کند و عامل Claude Code نیز در workflow فعلی نصب/فراخوانی نشده است. مهارت‌ها هم خودشان MP4 نمی‌سازند یا ویدئو منتشر نمی‌کنند. برای اتصال خودکار، باید بعداً قابلیت‌های مشخص را با تست به pipeline متصل کرد و quality gateها و OAuth موجود را حفظ کرد.

## آزمون
`tests/test_youtube_agent_skills.py` وجود هر ۱۱ مهارت، قابل‌کامپایل بودن شش ابزار Python و معتبر بودن `hooks.json` را بررسی می‌کند. این فایل به مجموعه آزمون موجود افزوده شده است، اما تا زمانی که CI اجرا نشده، نتیجهٔ سبز اعلام نمی‌شود.
