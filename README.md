# ImamAli110 — تولید ویدئوی فارسی با LTX-Video

این مخزن برای کانال فارسی **ImamAli110** دربارهٔ معنویت روزمره، توکل، امید، رشد فردی و عادت‌های سالم مالی است. برچسب دوم کانال **#The110Path** است: [@imamali.110](https://www.youtube.com/@imamali.110).

## مسیر اصلی در این شاخه

`scripts/daily_run.py → app/spiritual_pipeline.py → app/ltx_spiritual_renderer.py → app/ltx_video_engine.py`

- متن فارسی: Shorts چهارصحنه‌ای با هوک فوری و ویدئوی بلند با ساختار چندبخشی؛ گیت‌های کیفیت و جلوگیری از تکرار حفظ شده‌اند.
- گویندگی: Edge TTS با صدای `fa-IR-FaridNeural` و زیرنویس زمان‌بندی‌شده؛ متن می‌تواند با Ollama محلی تولید شود و کلید API پولی الزامی نیست.
- تصویر: **LTX-Video تنها موتور تولید صحنه است**؛ مسیر اصلی به Pexels، تصویر ثابت یا CogVideoX fallback نمی‌کند.
- مونتاژ: FFmpeg، زیرنویس فارسی و کاور؛ Shorts خروجی 1080×1920 و Long خروجی 1920×1080 می‌گیرد.
- کیفیت: کنترل مدت و ابعاد، زیرنویس، کاور و تطابق متن روایت با صحنه‌ها. `app/youtube_growth_agent.py` بازبینی رایگان hook، عنوان/کاور، SEO، تکرار و کیفیت پیش از آپلود را به گزارش اجرا اضافه می‌کند.
- تعامل کانال: پاسخ محدود به نظرهای بی‌خطر و روشن پس از آپلود؛ موارد حساس برای پاسخ خودکار کنار گذاشته می‌شوند. آمار واقعی YouTube Analytics و جست‌وجوی عمومی ویدئوهای رقیب نیز به‌صورت اختیاری به برنامه‌ریزی متن بعدی کمک می‌کند؛ اگر مجوز/داده در دسترس نباشد، سیستم عددی جعل نمی‌کند.
- انتشار: مسیر اصلی **فقط Private** است. انتشار عمومی غیرفعال است.

## اجرای GPU و زمان‌بندی

`.github/workflows/daily_run.yml` هر روز ساعت 14:00 UTC مسیر Long و ساعت 17:00 UTC مسیر Shorts را از طریق Google Colab CLI و یک نشست تازهٔ T4 اجرا می‌کند. workflow خروجی MP4، گزارش QA و تاریخچهٔ کانال را به‌عنوان artifact برمی‌گرداند و فقط همان نشست Colab را می‌بندد. زمان‌بندی در صورت نبود GPU/سهمیهٔ Colab یا Secret لازم تضمین نمی‌شود.

برای این مسیر، در GitHub → Settings → Secrets and variables → Actions باید `COLAB_CLI_TOKEN_JSON` تنظیم شده باشد. برای آپلود خصوصی زمان‌بندی‌شده، این سه Secret نیز لازم‌اند: `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN`. اگر Colab T4 در دسترس نباشد، job fail-closed می‌شود و هیچ موتور جایگزین یا انتشار عمومی انجام نمی‌شود.



LTX-Video به GPU CUDA سازگار و VRAM کافی نیاز دارد. GitHub-hosted `ubuntu-latest` در این مخزن GPU ندارد و نشست رایگان Colab را نمی‌توان از GitHub به‌شکل قابل‌اعتماد هر روز بیدار کرد. به همین علت workflow زمان‌بندی‌شدهٔ CPU غیرفعال است؛ این کار از جایگزین‌شدن ناخواستهٔ LTX با stock footage و انتشار خروجی ناقص جلوگیری می‌کند.

دفترچهٔ Colab: [`colab/ImamAli110_Cinematic_Production.ipynb`](colab/ImamAli110_Cinematic_Production.ipynb). پیش‌فرض `UPLOAD_PRIVATE = False` است و فقط dry-run می‌کند. برای بارگذاری خصوصی، پس از بررسی خروجی باید `UPLOAD_PRIVATE = True` را صریحاً تنظیم کرد و سه Secret رسمی YouTube را در پنل Secrets کولب فراهم کرد:
`YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN`.

زمان‌های هدف در `config/channel.yaml` ثبت شده‌اند: Long ساعت 14:00 UTC و Shorts ساعت 17:00 UTC. فعال‌سازی زمان‌بندی خودکار کامل به یک GPU runner همیشه‌در‌دسترس نیاز دارد؛ صرفاً داشتن GitHub Secrets یا Colab رایگان این محدودیت را برطرف نمی‌کند.

## مهارت‌های YouTube Agent

هر ۱۱ مهارت بالادستی، شش ابزار Python و مجوز MIT در [`.claude/skills/yt-*/`](.claude/skills/README.md) قرار دارند. قابلیت‌های متن/SEO/بسته‌بندی، QA، تاریخچهٔ موضوع، فصل‌بندی و پاسخ محدود به نظرها به مسیر Python متصل شده‌اند. تحلیل واقعی retention و رقبا به دادهٔ تازهٔ YouTube Analytics/رقبا نیاز دارد؛ فایل‌های `SKILL.md` به‌تنهایی توسط GitHub Actions اجرا نمی‌شوند.

## اعتبارسنجی

برای اجرای تست‌های CPU-only در محیط Python:

```bash
python -m pip install -r requirements.txt pytest
python -m pytest -q
```

تست‌ها قواعد صحنه/مدت LTX و گیت رشد را بررسی می‌کنند، اما جایگزین رندر واقعی نیستند. تا زمان اجرای GPU و بررسی خروجی MP4، سازگاری API مدل، VRAM، زمان تولید و کیفیت بصری تأییدشده نیستند. این شاخه هنوز در `main` ادغام نشده است.
