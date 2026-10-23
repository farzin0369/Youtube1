# ادغام مهارت‌های YouTube Agent با کانال ImamAli110

## وضعیت شاخه

تمام ۱۱ دستور/مهارت بالادستی، شش ابزار Python و مجوز MIT در `.claude/skills/yt-*/` قرار دارند. فهرست مهارت‌ها در [README مهارت‌ها](../.claude/skills/README.md) است.

## مسیر تولید اصلی

`scripts/daily_run.py → app/spiritual_pipeline.py → app/ltx_spiritual_renderer.py → app/ltx_video_engine.py`

- LTX-Video تنها موتور تولید صحنهٔ ویدئو در مسیر اصلی است؛ fallback به Pexels، تصویر ثابت یا CogVideoX وجود ندارد.
- متن و گویندگی فارسی، زیرنویس، کاور، نسبت تصویر، QA و checkpoint صحنه‌ها حفظ شده‌اند.
- `app/youtube_growth_agent.py` یک بازبینی رایگان پیش از آپلود انجام می‌دهد و نتیجه را در `growth_review.json` ذخیره می‌کند.
- بارگذاری مسیر اصلی فقط `private` است. انتشار عمومی غیرفعال است.
- تست‌های جدید در `tests/test_ltx_video_engine.py` و `tests/test_youtube_growth_agent.py` بدون نیاز به GPU قواعد برنامه‌ریزی صحنه و گیت کیفیت را بررسی می‌کنند.

## وضعیت یازده قابلیت

| مهارت | اتصال فعلی |
|---|---|
| `yt-script` | تولید متن فارسی، کنترل هوک، تکرار و سیاست محتوا |
| `yt-package` | عنوان، کاور، توضیحات و تگ‌ها |
| `yt-edit` | تدوین FFmpeg و زیرنویس؛ ابزار dead-air مستقل نیز موجود است |
| `yt-comment` | پاسخ محدود و امن به نظرهای تازه |
| `yt-plan` | تاریخچهٔ موضوع و جلوگیری از تکرار |
| `yt-viral` | بازبینی هوک/بسته‌بندی؛ تحلیل رقبا زنده هنوز نیازمند دادهٔ تازه است |
| `yt-retention` | گیت ساختار/هوک؛ تحلیل واقعی retention نیازمند export از YouTube Analytics است |
| `yt-shorts` | تولید Short چهارصحنه‌ای با روایت دقیق |
| `yt-seo` | بررسی عنوان، توضیحات و تگ‌ها |
| `yt-chapters` | فصل‌بندی ویدئوی بلند در توضیحات |
| `yt-audit` | گزارش QA، رشد و نتیجهٔ هر اجرا |

فایل‌های `SKILL.md` به‌تنهایی توسط GitHub Actions اجرا نمی‌شوند. مسیر Python از YouTube Analytics برای آمار عملکرد و از جست‌وجوی عمومی YouTube برای نمونه‌های رقیب استفاده می‌کند، هرگاه OAuth/API در دسترس باشد؛ نمودارهای کامل retention همچنان به دادهٔ مناسب نیاز دارند. هیچ امتیازی تضمین‌کنندهٔ وایرال‌شدن نیست.

## GPU، زمان‌بندی و اجرا

زمان‌های هدف در `config/channel.yaml` ثبت شده‌اند: ویدئوی بلند ۱۴:۰۰ UTC و Shorts ساعت ۱۷:۰۰ UTC. workflow اصلی با Google Colab CLI یک نشست تازهٔ T4 می‌سازد، `scripts/colab_spiritual_job.py` را اجرا می‌کند، MP4 و گزارش QA را برمی‌گرداند و نشست خودش را می‌بندد. این مسیر به `COLAB_CLI_TOKEN_JSON` و دسترسی/سهمیهٔ واقعی Colab T4 وابسته است؛ دسترسی رایگان و تخصیص GPU تضمین‌شده نیست. نبود GPU باعث توقف امن می‌شود، نه تغییر موتور.

دفترچهٔ Colab: [Colab ImamAli110](../colab/ImamAli110_Cinematic_Production.ipynb). پیش‌فرض notebook، dry-run است؛ بارگذاری خصوصی تنها با تغییر صریح `UPLOAD_PRIVATE = True` انجام می‌شود. برای دسترسی به آمار واقعی YouTube Analytics، توکن OAuth باید مجوز `yt-analytics.readonly` هم داشته باشد؛ اگر مجوز موجود نباشد، تولید ادامه می‌یابد اما از آمار حدس زده نمی‌شود.



زمان‌های هدف در `config/channel.yaml` ثبت شده‌اند: ویدئوی بلند ۱۴:۰۰ UTC و Shorts ساعت ۱۷:۰۰ UTC. GitHub-hosted runner در این مخزن GPU ندارد و نشست رایگان Colab از راه GitHub قابل بیدارکردنِ قابل‌اعتماد نیست. بنابراین workflow زمان‌بندی‌شدهٔ CPU غیرفعال است تا مسیر stock جایگزین موتور LTX نشود و انتشار اشتباهی رخ ندهد.

دفترچهٔ اجرای GPU: [Colab ImamAli110](../colab/ImamAli110_Cinematic_Production.ipynb). پیش‌فرض notebook، dry-run است؛ بارگذاری خصوصی تنها با تغییر صریح `UPLOAD_PRIVATE = True` انجام می‌شود. تا قبل از CI سبز و رندر واقعی Colab، عملکرد واقعی مدل/VRAM تأییدشده محسوب نمی‌شود.
