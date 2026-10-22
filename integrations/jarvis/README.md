# Jarvis response retrieval integration

این پوشه نسخهٔ مستقل رابط Jarvis برای ادغام/مقایسه است؛ فایل اصلی مخزن Youtube1 دست‌کاری نشده است.

## اصلاح
- خواندن پاسخ فقط از Check Run دارای `name=Jarvis response` و `external_id=run.id` انجام می‌شود تا پاسخ اجرای قبلی اشتباهاً نمایش داده نشود.
- بررسی Check تا شش مرتبه با فاصلهٔ افزایشی تکرار می‌شود تا تأخیر انتشار Check Summary باعث پاسخ خالی نشود.
- اگر دریافت پاسخ شکست بخورد، خطای واقعیِ در دسترس به کاربر نشان داده می‌شود.

## تنظیمات دسترسی رابط
توکن GitHub فقط در مرورگر کاربر نگه‌داری شود؛ هرگز داخل فایل یا مخزن نوشته نشود. Fine-grained PAT باید برای مخزن Jarvis حداقل Actions: Read and write و Checks: Read-only داشته باشد. اگر UI را از این مخزن میزبانی می‌کنید، مقادیر OWNER/REPO/WORKFLOW را برای مخزن مقصد تنظیم کنید.

## OpenRouter
کلید `OPENROUTER_API_KEY` باید فقط در GitHub Actions Secrets مخزن Jarvis باشد. این کد کلید را چاپ یا ذخیره نمی‌کند. اجرای واقعی مدل نیازمند وجود Secret و dispatch مجاز workflow است؛ اضافه‌کردن کد به‌تنهایی اثبات اجرای مدل نیست.
