# Jarvis Chat integration (OpenRouter)

این پوشه نسخهٔ جداشدهٔ رابط چت Jarvis و عامل OpenRouter را برای مخزن Youtube1 نگه می‌دارد؛ فایل‌های خط تولید ویدیوی موجود دست‌نخورده می‌مانند.

## راه‌اندازی
1. در Settings → Secrets and variables → Actions، secret با نام `OPENROUTER_API_KEY` را تعریف کنید.
2. از Actions، workflow با نام **Jarvis Agent** را اجرا کنید یا رابط `chat.html` را از GitHub Pages منتشر کنید.
3. برای استفاده از رابط، یک GitHub fine-grained token را فقط در مرورگر خود وارد کنید. مجوزهای لازم: Actions **Read and write**، Checks **Read-only** و Metadata **Read-only**. توکن در مرورگر ذخیره می‌شود؛ هرگز آن را در فایل‌های مخزن قرار ندهید.

## نکتهٔ امنیتی
- کلید OpenRouter فقط در GitHub Actions secret قرار می‌گیرد و به مرورگر فرستاده نمی‌شود.
- رابط چت از workflow dispatch و Check Run دارای `external_id` دقیقاً برابر شناسهٔ اجرای workflow استفاده می‌کند.
- مدل‌ها فقط از فهرست رایگان `:free` امتحان می‌شوند؛ دسترسی و سهمیهٔ رایگان تابع شرایط روز OpenRouter است.
- برای انتشار رابط از پوشهٔ `jarvis` در GitHub Pages استفاده کنید، یا `chat.html` را در مسیر ریشهٔ شاخهٔ انتشار قرار دهید.
