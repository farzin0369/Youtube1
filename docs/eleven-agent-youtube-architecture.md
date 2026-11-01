# طرح ادغام ۱۱ نقش تخصصی YouTube برای BAMO

این شاخه، ۱۱ مهارت مستقل YouTube را از شاخهٔ قبلی مخزن به مسیر اصلی توسعه منتقل می‌کند و پروژهٔ متن‌باز YouTube Automation Agent را به‌صورت submodule و با commit ثابت نگه می‌دارد.

## ۱۱ نقش عملیاتی

این‌ها ۱۱ قابلیت/نقش تخصصی‌اند؛ نباید آن‌ها را با ۱۱ فرایند مستقلِ دارای مدل و هزینهٔ جداگانه اشتباه گرفت.

| # | نقش | مهارت/ماژول |
|---|---|---|
| 1 | کشف موضوع و بررسی نمونه‌های پربازدید | `yt-viral` + جست‌وجوی عمومی YouTube |
| 2 | استراتژی و تقویم محتوا | `yt-plan` |
| 3 | نویسنده و طراح هوک | `yt-script` |
| 4 | عنوان و تامبنیل | `yt-package` |
| 5 | سئو و بستهٔ انتشار | `yt-seo` |
| 6 | مدیر تولید و کنترل رسانه | خط تولید Wan 2.1 در Colab + FFmpeg |
| 7 | تدوین و حذف مکث‌های اضافه | `yt-edit` |
| 8 | بازتولید ویدئوی بلند به Shorts | `yt-shorts` |
| 9 | فصل‌بندی ویدئوی بلند | `yt-chapters` |
| 10 | مدیریت و پاسخ‌نویسی نظرها | `yt-comment` |
| 11 | تحلیل عملکرد، نگهداشت و ممیزی کانال | `yt-retention` + `yt-audit` + `app/youtube_analytics.py` |

## پروژهٔ مرجع متن‌باز

پروژهٔ [darkzOGx/youtube-automation-agent](https://github.com/darkzOGx/youtube-automation-agent) در مسیر `integrations/youtube-automation-agent` به‌صورت Git submodule ثبت شده است. مجوز upstream، MIT است و متن مجوز مهارت‌های منتقل‌شده نیز در `docs/licenses/youtube-agent-skill-MIT.txt` نگه‌داری می‌شود.

نسخهٔ upstream در این شاخه روی commit ثابت `e973d515aef90c467da2289144df737a3bd03859` قفل شده تا تغییرات آیندهٔ upstream بی‌اجازه وارد تولید نشوند. برای دریافت کد submodule هنگام clone از `git clone --recurse-submodules` استفاده شود.

کد upstream هفت فایل agent اجرایی JavaScript دارد (strategy, script, thumbnail, SEO, production, publishing, analytics) و قابلیت‌های تکمیلی engagement، retention و Shorts repurposing را در سرویس‌های جداگانه ارائه می‌کند. بنابراین آن را به‌اشتباه «۱۱ ایجنت مستقل» معرفی نمی‌کنیم؛ ۱۱ مورد جدول بالا نقش‌های کاری سیستم ترکیبی BAMO هستند.

## مرزهای سازگاری و هزینه

- خط تولید اصلی این مخزن Python و Colab است؛ submodule یک برنامهٔ Node.js جداگانه است و در Colab خودکار اجرا نمی‌شود.
- upstream به Node.js 18.17+، OAuth دسکتاپ YouTube و دست‌کم یک provider متنی نیاز دارد. مسیر ویدئوی واقعی آن می‌تواند providerهای پولی داشته باشد؛ پس از آن به‌عنوان موتور ویدئوی رایگان BAMO استفاده نمی‌کنیم.
- تولید تصویر متحرک BAMO از اسکریپت Colab موجود با Wan 2.1 استفاده می‌کند. هیچ‌یک از providerهای پولی upstream به‌طور پیش‌فرض فعال نمی‌شود.
- ماژول Analytics فقط با OAuth دارای مجوز `yt-analytics.readonly` دادهٔ واقعی می‌خواند. نبود توکن به معنی «داده در دسترس نیست» است، نه صفر بازدید یا حدس‌زدن آمار.
- هر نوع انتشار خودکار عمومی خاموش می‌ماند. خروجی باید ابتدا تولید، از نظر رسانه/روایت بررسی و توسط صاحب کانال تأیید شود.

## وضعیت رندر Colab در زمان ایجاد این شاخه

آخرین اجرای `Colab CLI GPU cinematic render` در ۳۱ اکتبر ۲۰۲۶ به Colab متصل شد، اما هنگام اجرای کد روی کرنل با `RuntimeError: Connection was lost` متوقف شد. artifact خروجی فقط ۱٬۸۰۵ بایت بود و فایل MP4 نهایی در آن وجود نداشت. بنابراین تا اجرای موفق و بررسی واقعی فایل MP4، تولید ویدئو «تکمیل‌شده» محسوب نمی‌شود.

## آزمون‌ها

`tests/test_youtube_agent_skills.py` وجود هر ۱۱ مهارت، کامپایل شش ابزار Python و معتبر بودن JSON فرمول‌های هوک را بررسی می‌کند. `tests/test_youtube_analytics.py` رفتار محافظه‌کارانهٔ تحلیل آمار و عدم جعل داده را بررسی می‌کند.
