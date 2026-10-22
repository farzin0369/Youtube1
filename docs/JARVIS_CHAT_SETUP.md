# Jarvis Chat در مخزن Youtube1

این شاخه رابط چت فارسی را به GitHub Actions و مدل‌های رایگان OpenRouter متصل می‌کند. کلید API در کد یا مرورگر قرار نمی‌گیرد.

## راه‌اندازی لازم
1. در Settings → Secrets and variables → Actions، یک Repository secret با نام دقیق OPENROUTER_API_KEY بسازید. کلید را فقط در فرم امن GitHub وارد کنید.
2. برای اجرای رابط، GitHub Pages را از این شاخه و پوشه root فعال کنید یا تغییرات را پس از بازبینی با PR ادغام کنید.
3. رابط برای dispatch و خواندن نتیجه، یک Fine-grained PAT لازم دارد که فقط به مخزن Youtube1 محدود باشد: Actions Read and write و Checks Read-only. توکن را در چت یا کد عمومی ننویسید.

## محدودیت‌ها
- فقط با ارسال پیام، workflow دستی اجرا می‌شود؛ هیچ ویدیویی منتشر نمی‌شود.
- سه مدل رایگان OpenRouter به ترتیب امتحان می‌شوند.
- اگر secret غایب باشد یا مدل‌ها شکست بخورند، workflow با خطا متوقف می‌شود و پاسخ جعلی/محلی تولید نمی‌شود.
- اجرای مدل روی GitHub-hosted CPU است، نه GPU.
