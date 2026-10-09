# یک‌بار گرفتن توکن یوتیوب

## پیش‌نیاز (۲ دقیقه در Google Cloud)

1. https://console.cloud.google.com/apis/library/youtube.googleapis.com → **Enable**
2. https://console.cloud.google.com/apis/credentials/consent
   - External → ایمیل خودتان → Test user = همان ایمیل
3. https://console.cloud.google.com/apis/credentials
   - Create credentials → **OAuth client ID**
   - Type: **Desktop app**
   - Create → Client ID و Client secret را نگه دارید

اگر قبلاً Web client ساختید و `deleted_client` دیدید، **client جدید Desktop** بسازید.

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
بگذارید (اگر از قبل هست، مقدار را Update کنید).

## مهم

- رمز گوگل را nowhere نگذارید
- فقط این سه Secret: `YOUTUBE_CLIENT_ID` / `YOUTUBE_CLIENT_SECRET` / `YOUTUBE_REFRESH_TOKEN`
