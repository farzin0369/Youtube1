# YouTube Automation — امام علی

ویدیوی **سینمایی** (نه اسلاید خشک) + **یک گوینده ثابت** + **منابع معتبر**.

## ویژگی‌ها
- پس‌زمینه متحرک سینمایی (نور طلایی، وینیت، حرکت آرام)
- زیر‌نویس نرم پایین تصویر
- صدای ثابت: `onyx` / `tts-1-hd` (از `config/channel.yaml`)
- موضوعات فقط از لیست تأییدشده (نهج‌البلاغه / قرآن با ارجاع)
- آپلود فقط private تا بازبینی شما

## زمان‌بندی (تهران)
| 06:00 | Short |
| 20:30 | Long |

## Secrets
`OPENAI_API_KEY` · `YOUTUBE_CLIENT_ID` · `YOUTUBE_CLIENT_SECRET` · `YOUTUBE_REFRESH_TOKEN`

اختیاری: `TTS_VOICE=onyx` (پیش‌فرض قفل است)

## اجرا
```bash
python -m app.pipeline --kind short --publish-mode private
```
