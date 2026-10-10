# یک‌بار گرفتن توکن یوتیوب

## پیش‌نیاز (۲ دقیقه در Google Cloud)

1. https://console.cloud.google.com/apis/library/youtube.googleapis.com → **Enable**
2. https://console.cloud.google.com/apis/credentials/consent
   - Audience/User type را متناسب با حساب انتخاب کنید.
   - اگر External است، ایمیل خودتان را به Test users اضافه کنید تا بتوانید مجوز بدهید.
   - **برای اتوماسیون بلندمدت، وضعیت انتشار OAuth را بررسی کنید:** در حالت Testing، refresh tokenهای دارای YouTube scopes ممکن است پس از ۷ روز منقضی شوند. انتقال به In production ممکن است به مراحل تأیید Google نیاز داشته باشد.
3. https://console.cloud.google.com/apis/credentials
   - Create credentials → **OAuth client ID**
   - Type: **Desktop app**
   - Create → Client ID و Client secret را نگه دارید.

اگر قبلاً Web client ساختید یا پیام `deleted_client` دیدید، یک OAuth client جدید از نوع Desktop app بسازید.

## رفع خطای `invalid_grant`

این خطا معمولاً یعنی Google توکن را رد کرده یا توکن با همان OAuth client جفت نیست:

1. مطمئن شوید YouTube Data API فعال است و OAuth client از نوع **Desktop app** است.
2. در https://myaccount.google.com/permissions دسترسی برنامه را لغو کنید تا مجوز قبلی باقی نماند.
3. روی کامپیوتر خودتان اسکریپت زیر را اجرا کنید و در مرورگر با همان حساب Google که مالک کانال YouTube است وارد شوید.
4. هر سه مقدار را از **همان اجرای جدید** بردارید؛ Client ID، Client secret و refresh token قدیمی/جدید را بین اجراهای مختلف مخلوط نکنید.
5. سه GitHub Actions Secret را به‌روزرسانی کنید. مقدارها را در Issue، چت، کامیت یا لاگ قرار ندهید.

## اجرا روی کامپیوتر خودتان

```bash
git clone https://github.com/farzin0369/Youtube1.git
cd Youtube1
pip install google-auth-oauthlib google-auth-httplib2
python scripts/get_youtube_token.py
```

مرورگر باز می‌شود → با حساب صاحب کانال وارد شوید → Allow.

سه مقدار چاپ‌شده را در:
GitHub → Youtube1 → Settings → Secrets and variables → Actions
بگذارید (اگر از قبل هستند، مقدارشان را Update کنید).

## مهم

- رمز عبور Google را هیچ‌جا وارد Repository نکنید.
- فقط این سه Secret برای YouTube OAuth لازم‌اند: `YOUTUBE_CLIENT_ID` / `YOUTUBE_CLIENT_SECRET` / `YOUTUBE_REFRESH_TOKEN`.
- برای مسیر GPU، Secret جداگانهٔ `COLAB_CLI_TOKEN_JSON` نیز لازم است؛ آن را با توکن YouTube اشتباه نگیرید.
- هرگز توکن‌ها، پیشوند آن‌ها یا طولشان را در لاگ‌های GitHub چاپ نکنید.
