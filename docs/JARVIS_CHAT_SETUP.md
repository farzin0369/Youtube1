# Jarvis Chat در مخزن Youtube1

این شاخه رابط چت فارسی را به GitHub Actions و یک مدل رایگان OpenRouter متصل می‌کند. کلید OpenRouter فقط در GitHub Actions Secret استفاده می‌شود. GitHub Pages از ریشهٔ همین شاخه منتشر می‌شود و رابط در `https://farzin0369.github.io/Youtube1/jarvis/chat.html` قرار دارد.

## راه‌اندازی لازم
1. وجود Repository secret با نام دقیق `OPENROUTER_API_KEY` را در Settings → Secrets and variables → Actions بررسی کنید؛ مقدار آن را هیچ‌گاه در کد، workflow input یا پیام وارد نکنید.
2. Pages از شاخهٔ `feat/jarvis-chat-openrouter-integration` و مسیر `/` ساخته می‌شود. صفحات ایستا نمی‌توانند Secret سروری را مخفی کنند.
3. رابط برای dispatch و خواندن پاسخ به Fine-grained PAT محدود به `Youtube1` نیاز دارد: Actions Read and write و Checks Read-only. توکن در کد/مخزن ذخیره نمی‌شود؛ فقط در `sessionStorage` تب فعلی می‌ماند و به API گیت‌هاب فرستاده می‌شود. برای استفادهٔ دوباره، آن را در Android/Chrome Password Manager ذخیره و با تکمیل خودکار وارد کنید؛ داخل مرورگر درون‌برنامه‌ای ممکن است لازم باشد صفحه را در Chrome باز کنید.
4. پیام و پاسخ روی مخزن عمومی در Actions و Check Run قابل مشاهده‌اند؛ اطلاعات حساس نفرستید.

## محدودیت‌ها
- فقط با ارسال پیام، workflow دستی اجرا می‌شود؛ هیچ ویدیویی منتشر نمی‌شود.
- مدل ثابت `minimax/minimax-m3.1-flash:free` استفاده می‌شود؛ در صورت نبود دسترسی یا سهمیه، خطا نمایش داده می‌شود و مدل محلی یا پولی جایگزین نمی‌شود.
- هر پیام شناسهٔ درخواست یکتا دارد؛ UI فقط اجرای دارای همان شناسه و Check Run دارای `external_id` دقیقاً برابر شناسهٔ همان اجرا را می‌پذیرد.
- اگر Secret غایب باشد یا درخواست شکست بخورد، workflow با خطا متوقف می‌شود و پاسخ جعلی/محلی تولید نمی‌شود.
- اجرای مدل روی GitHub-hosted CPU است، نه GPU.
