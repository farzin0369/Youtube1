# Jarvis Chat integration (OpenRouter)

این پوشه نسخهٔ جداشدهٔ رابط چت Jarvis و عامل OpenRouter را برای مخزن Youtube1 نگه می‌دارد؛ فایل‌های خط تولید ویدیوی موجود دست‌نخورده می‌مانند.

## راه‌اندازی
1. مطمئن شوید در Settings → Secrets and variables → Actions secret با نام `OPENROUTER_API_KEY` موجود است؛ مقدار آن نباید در کد یا workflow input وارد شود.
2. رابط `chat.html` را فقط پس از پیکربندی و تأیید واقعی GitHub Pages منتشر کنید. در زمان این بررسی Pages برای `Youtube1` فعال نبود.
3. رابط به Fine-grained token محدود به همین مخزن نیاز دارد: Actions **Read and write** و Checks **Read-only**. توکن فقط در `sessionStorage` نشست مرورگر می‌ماند و برای GitHub API ارسال می‌شود؛ هرگز آن را در فایل مخزن نگذارید.

## نکتهٔ امنیتی
- کلید OpenRouter فقط در GitHub Actions secret قرار می‌گیرد و به مرورگر فرستاده نمی‌شود.
- رابط برای هر dispatch شناسهٔ یکتا می‌فرستد و فقط workflow run و Check Run همان درخواست را می‌خواند.
- مدل ثابت `minimax/minimax-m3.1-flash:free` انتخاب شده است؛ نبود مدل، quota یا rate limit خطای واقعی می‌دهد و به مدل محلی یا پولی fallback نمی‌شود.
- پیام‌ها و پاسخ‌ها در Actions و Check Run مخزن عمومی قابل مشاهده‌اند؛ اطلاعات حساس نفرستید.
