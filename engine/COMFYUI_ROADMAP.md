# قدم ۳ — مسیر ComfyUI (وقتی GPU قوی‌تر داری)

این مسیر برای **کیفیت حرفه‌ای** است؛ روی Colab رایگان T4 پایدار نیست.

## حداقل سخت‌افزار
- NVIDIA **۱۲–۲۴GB VRAM** (ترجیحاً 24GB)
- یا Colab Pro / RunPod / vast.ai با کارت مشابه

## زنجیره پیشنهادی Story-to-Video

```
متن فارسی
  → فیلمنامه/ضرباهنگ (LLM محلی یا API رایگان)
  → تصویر صحنه: Flux.1-dev یا SDXL (با IP-Adapter برای قفل چهره)
  → حرکت: HunyuanVideo-1.5 I2V یا Wan 2.2 TI2V یا AnimateDiff
  → صدا: CosyVoice / ChatTTS / XTTS (فارسی)
  → لیپ‌سینک اختیاری: MuseTalk
  → مونتاژ + زیرنویس: FFmpeg / ComfyUI nodes
```

## Workflowهای آماده برای جستجو
- `ComfyUI story to video voiceover`
- `ComfyUI HunyuanVideo I2V`
- `ComfyUI Flux IPAdapter character consistency`

## ارتباط با موتور فعلی
- `engine/viral_short.py` = مسیر **رایگان روزانه روی T4**
- این فایل = مسیر **ارتقای کیفیت** وقتی سخت‌افزار اجازه دهد
- خروجی هر دو باید `final_story.mp4` عمودی 9:16 باشد تا آپلود یوتیوب یکسان بماند

## اولویت پیاده‌سازی بعدی (بعد از درآمد/GPU)
1. نصب ComfyUI + workflow Flux → Hunyuan I2V
2. تعویض Edge-TTS با CosyVoice فارسی
3. اتصال workflow به GitHub Actions روی رانر GPU اجاره‌ای
