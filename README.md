# ImamAli110 — Self-Hosted YouTube AI

تولید ویدئوی **واقعاً سینمایی و text-to-video** برای ImamAli110 با موتور هوش مصنوعی محلی؛ بدون وابستگی به OpenAI، OpenArt یا Runway برای تولید محتوا.

## معماری

موضوع/منبع → LLM محلی → فیلمنامه فارسی → Piper TTS محلی → CogVideoX text-to-video روی GPU → مونتاژ FFmpeg → زیرنویس → YouTube

### اجزای محلی
- **LLM:** Ollama + مدل محلی مثل Qwen
- **TTS:** Piper با صدای فارسی محلی
- **Video:** CogVideoX-2B از پروژه متن‌باز CogVideoX
- **Render/Mux:** FFmpeg
- **Automation:** GitHub Actions روی **self-hosted GPU runner**
- **YouTube:** فقط API انتشار؛ هیچ مدل هوش مصنوعی از YouTube گرفته نمی‌شود.

## زمان‌بندی تهران

- **05:35 — Short**
- **20:30 — Long**

## نکته مهم

GitHub-hosted runner معمولی GPU لازم برای تولید ویدئو ندارد. بنابراین Workflow اصلی عمداً روی runner با برچسب‌های:

`self-hosted, linux, x64, gpu`

اجرا می‌شود.

مدل فقط یک بار روی ماشین محلی/سرور دانلود و cache می‌شود و سپس تولیدها محلی انجام می‌شوند.

## راه‌اندازی

1. یک کامپیوتر/سرور Linux با NVIDIA CUDA به عنوان GitHub self-hosted runner اضافه کن.
2. Ollama را روی همان ماشین اجرا کن و یک مدل فارسی/چندزبانه محلی نصب کن.
3. Piper را نصب کن و مسیر مدل صدای فارسی را در GitHub Actions Variable با نام `PIPER_MODEL` قرار بده.
4. در همان ماشین:

```bash
bash scripts/bootstrap_local_ai.sh
```

5. در GitHub repository secrets فقط اطلاعات YouTube را قرار بده:
- `YOUTUBE_CLIENT_ID`
- `YOUTUBE_CLIENT_SECRET`
- `YOUTUBE_REFRESH_TOKEN`

برای موتور تولید AI دیگر `OPENAI_API_KEY` لازم نیست.

## Preview

Workflow زیر فقط روی GPU محلی اجرا می‌شود و چیزی را به YouTube منتشر نمی‌کند:

`.github/workflows/preview.yml`

## مدل ویدئو

پیش‌فرض:

`THUDM/CogVideoX-2b`

برای ارتقای کیفیت بعداً می‌توانیم مدل قوی‌تر را با تغییر `LOCAL_VIDEO_MODEL` اضافه کنیم.

## اصل طراحی

این پروژه «API wrapper» برای یک سرویس هوش مصنوعی نیست؛ **AI Engine متعلق به خودت و قابل اجرای محلی است.**

YouTube فقط مقصد انتشار است.
