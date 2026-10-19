# جایگزین‌های اپن‌سورس HeyGen (پژوهش اکتبر ۲۰۲۶)

HeyGen سرویس **پولی** آواتار و ویدیو است. زیر یک مدل واحد «بهتر از HeyGen» که روی GPU رایگان Colab (T4 ~15GB) پایدار باشد وجود ندارد؛ ولی گزینه‌های اپن‌سورس جدی هست.

## رتبه‌بندی عملی برای پروژه ما

| پروژه | نوع | GitHub / HF | نسبت به HeyGen | VRAM تقریبی | مناسب کانال معنوی شورت؟ |
|-------|-----|-------------|----------------|-------------|-------------------------|
| **LongCat-Video-Avatar 1.5** (Meituan) | آواتار ویدیویی تجاری‌درجه | [meituan-longcat/LongCat-Video](https://github.com/meituan-longcat/LongCat-Video) | ادعای برتری در preference نسبت به HeyGen (~54%) | خیلی بالا (H100-class در بنچمارک‌ها) | اگر GPU قوی باشد، بله برای راوی |
| **Duix-Avatar / HeyGem** | کلون آواتار آفلاین کامل | [duixcom/Duix-Avatar](https://github.com/duixcom/Duix-Avatar) (~16k⭐) | نزدیک‌ترین «پکیج» شبیه HeyGen | RTX 4070-class معمولاً | برای راوی روی دوربین |
| **EchoMimic / MuseTalk / LiveAvatar** | لیپ‌سینک و نیم‌بدن | Ant Group / Tencent MuseTalk / LiveAvatar | قطعه از پایپ‌لاین HeyGen | متوسط تا بالا | فقط صحبت روی عکس/ویدیو |
| **HunyuanVideo 1.5** | متن/تصویر → فیلم واقعی | [Tencent-Hunyuan/HunyuanVideo-1.5](https://github.com/Tencent-Hunyuan/HunyuanVideo-1.5) | برای **فیلم سینمایی** نه آواتار | ~14GB با offload | بله برای صحنه‌های داستان |
| **Wan 2.2 / LTX** | متن→ویدیو عمومی | Alibaba Wan / Lightricks LTX | کیفیت فیلم کوتاه | متوسط تا خیلی بالا | بله |
| موتور فعلی ما `viral_short.py` | SDXL + TTS + زیرنویس | همین مخزن | استوری‌بورد فوتورئال، نه ویدیو ژنراتور کامل | Colab T4 OK | بله برای شورت روزانه رایگان |

## نکته مهم برای کانال تو

نمونه‌هایی که فرستادی (نهال، نان، بازار) **داستان سینمایی** هستند، نه آواتار صحبت‌کننده مثل تبلیغات HeyGen.

- اگر هدف **فیلم داستانی متحرک** است → Hunyuan / Wan / LTX + موتور صحنه
- اگر هدف **راوی انسانی که حرف می‌زند** است → Duix-Avatar یا LongCat-Avatar

## محدودیت Colab رایگان

مدل‌هایی که در بنچمارک‌ها از HeyGen بهتر گزارش شده‌اند (LongCat، LiveAvatar، Wan-S2V-14B) معمولاً **ده‌ها گیگابایت VRAM** می‌خواهند. روی T4 رایگان:
- پایدار: موتور فعلی SDXL + صدا
- آزمایشی: Hunyuan 1.5 با offload / I2V سبک
- غیرواقعی بدون GPU قوی: LongCat Avatar 1.5 با کیفیت کامل

## تصمیم پیشنهادی بعدی

1. **داستان سینمایی (اولویت کانال):** نگه داشتن `engine/viral_short.py` + افزودن I2V سبک روی هر فریم کلیدی
2. **راوی آواتار:** submodule یا Docker برای Duix-Avatar وقتی GPU قوی‌تر در دسترس باشد
3. **کیفیت نزدیک ادعا به HeyGen:** LongCat-Video-Avatar فقط با GPU ابری قوی (نه رایگان پایدار)

این فایل مرجع است؛ پیاده‌سازی هر backend جدا در `engine/backends/` اضافه می‌شود.
