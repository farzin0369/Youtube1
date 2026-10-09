# اتصال Qwen برای ساخت روزانه ویدیو

## نقش Qwen
- **اسکریپت فارسی روزانه** با مدل Qwen (مثلاً `qwen-plus`)
- زمان‌بندی GitHub Actions: صبح و شب (تهران)

## آنچه Qwen نیست
- Qwen به‌خودی‌خود **موتور ساخت فیلم سینمایی** مثل Sora نیست
- صدا و تدوین هنوز از مسیر pipeline (TTS + رندر) است

## گرفتن API Key
1. بروید به: https://dashscope.console.aliyun.com/
2. حساب بسازید / وارد شوید
3. API-KEY بسازید
4. در GitHub Secrets بگذارید:

| Secret | مقدار |
|--------|--------|
| `QWEN_API_KEY` یا `DASHSCOPE_API_KEY` | کلید شما |
| `QWEN_MODEL` (اختیاری) | `qwen-plus` یا `qwen-turbo` |
| `QWEN_API_BASE` (اختیاری) | پیش‌فرض بین‌المللی در workflow |

اگر در منطقهٔ چین هستید گاهی base این است:
`https://dashscope.aliyuncs.com/compatible-mode/v1`

## صدای گوینده
فعلاً اگر `OPENAI_API_KEY` باشد از TTS باکیفیت OpenAI استفاده می‌شود.
بدون آن، TTS کیفیت پایین‌تر یا خطا می‌دهد تا جایگزین رایگان وصل شود.

## تست
Actions → **ImamAli110 daily video (Qwen)** → Run workflow → dry_run=true
