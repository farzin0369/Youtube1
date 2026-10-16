# اتصال خودکار GitHub → Colab CLI (GPU)

Kaggle لازم نیست. فقط **یک‌بار** توکن Colab CLI را بساز و در Secrets بگذار.

## قدم ۱ — روی کامپیوتر خودت (یک‌بار)

```bash
pip install google-colab-cli

# ورود (لینک را در مرورگر باز کن و کد را بچسبان)
colab --auth=oauth2 whoami
```

بعد از موفقیت، فایل توکن اینجاست:

```
~/.config/colab-cli/token.json
```

محتوای **کامل** این فایل را کپی کن.

## قدم ۲ — در گیتهاب مخزن Youtube1

1. **Settings → Secrets and variables → Actions**
2. **New repository secret**
3. Name: `COLAB_CLI_TOKEN_JSON`
4. Value: کل متن `token.json` (از `{` تا `}`)

## قدم ۳ — اجرا

- دستی: Actions → **Colab CLI GPU cinematic render** → Run workflow
- یا بعداً به daily_run وصل می‌شود

خروجی موفق: artifact به نام `colab-cli-render` شامل `video_raw.mp4`

## نکته‌ها

- GPU رایگان سهمیه دارد؛ گاهی T4 در صف است.
- اگر توکن منقضی شد، قدم ۱ را تکرار کن و Secret را عوض کن.
- بدون این Secret، پروژه همان Mixkit روزانه را ادامه می‌دهد.

## دستور واقعی که Actions می‌زند

```bash
colab run --gpu T4 scripts/colab_render_minimal.py
```
