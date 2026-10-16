# اتومات واقعی: GitHub → GPU رایگان

## مشکل
GitHub Actions خودش GPU ندارد. Colab هم بدون ورود گوگل از راه دور پایدار نیست.

## راه‌حل پروژه (رایگان و خودکار)

```
GitHub Actions (مغز)
    │
    ├─ اگر KAGGLE_USERNAME + KAGGLE_KEY در Secrets باشد
    │     → کرنل GPU روی Kaggle اجرا می‌شود
    │     → ویدئوی خام برمی‌گردد
    │     → صدا + زیرنویس + آپلود یوتیوب
    │
    └─ وگرنه
          → Mixkit (همان مسیر فعلی، پایدار و رایگان)
```

## یک‌بار تنظیم (تو فقط این را انجام بده)

### گزینه پیشنهادی: Kaggle (پایدارترین برای اتومات)

1. برو [kaggle.com](https://www.kaggle.com) و حساب بساز (رایگان)
2. Settings → API → Create New Token → فایل `kaggle.json`
3. داخل گیتهاب مخزن Youtube1:
   - Settings → Secrets and variables → Actions → New repository secret
   - `KAGGLE_USERNAME` = نام کاربری
   - `KAGGLE_KEY` = کلید داخل kaggle.json

بعد از این، **هر روز بدون کلیک** اگر GPU در دسترس باشد رندر سینمایی امتحان می‌شود.

### گزینه ۲: Colab CLI (اگر Colab Pro / auth غیرتعاملی داشته باشی)

Secret:
- `COLAB_AUTH_TOKEN` یا فایل احراز هویت Colab CLI

Workflow اگر این secret را ببیند سعی می‌کند:
```
colab run --gpu T4 scripts/colab_render_minimal.py
```

## وضعیت فعلی کد

| فایل | نقش |
|------|-----|
| `.github/workflows/gpu_kaggle_render.yml` | اجرای اختیاری GPU روی Kaggle |
| `kaggle/render_short_kernel.py` | اسکریپت رندر روی GPU Kaggle |
| `scripts/try_gpu_render.sh` | تشخیص secret و انتخاب موتور |
| روزانه `daily_run.yml` | اگر GPU خروجی داد از آن استفاده؛ وگرنه Mixkit |

## صداقت
بدون حداقل **یک** secret رایگان (Kaggle یا Colab)، اتومات GPU ممکن نیست.
با Kaggle secrets، خط تولید واقعاً بدون دخالت تو کار می‌کند.
