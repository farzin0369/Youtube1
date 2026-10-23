# صدای طبیعی فارسی (رایگان / اپن‌سورس)

## واقعیت فنی (بدون اغراق)

| پروژه | نقش واقعی | فارسی؟ |
|--------|-----------|--------|
| **Parler-TTS** | TTS با کنترل سبک | ❌ فقط انگلیسی + چند زبان اروپایی |
| **Open Swara** | کتابخانهٔ ۴۰۶۵ نمونهٔ صوتی انسانی‌شده | ✅ نمونهٔ مرجع فارسی مرد/زن دارد |
| **Kitten-TTS 2** | CPU-capable, expressive TTS for its listed languages | ❌ Persian/Farsi is not listed; do not use for Persian narration |
| **Coqui XTTS v2** | کلون صدا از چند ثانیه مرجع | ✅ چندزبانه شامل فارسی |
| **Piper fa_IR** | TTS سبک CPU | ✅ سریع‌تر، کمی مصنوعی‌تر |

**مسیر پروژه:**
1. دانلود نمونهٔ `persian/male` از Open Swara (مرجع طبیعی)
2. ساخت گفتار با **XTTS v2** روی همان مرجع (GPU Colab)
3. اگر XTTS شکست خورد → Piper fa_IR / Edge Farid

لایسنس Open Swara: CC-BY-SA 4.0 — attribution در `ATTRIBUTION_VOICES.md`


## Kitten-TTS 2 — optional demo backend, not for Persian narration

The repository includes an **opt-in** adapter via `TTS_PROVIDER=kitten` and a standalone sample script:

```bash
# Install CPU-only PyTorch first; plain PyPI install can pull multi-GB CUDA wheels.
python -m pip install --index-url https://download.pytorch.org/whl/cpu torch torchaudio
python -m pip install -r requirements-kitten.txt
python scripts/kittentts2_sample.py --output output/kitten_tts2_sample.wav
```

The demo defaults to English and uses the smaller `emb4` weights to reduce the download. The model chooses CPU/GPU automatically. Set `KITTEN_TTS_VOICE`, `KITTEN_TTS_PRESET`, `KITTEN_TTS_WEIGHTS`, or `KITTEN_TTS_MODEL` to adjust it. It is intentionally **not** the default provider: the published Kitten-TTS 2 voice list does not include Persian/Farsi, and the adapter rejects Persian-script text rather than quietly generating unsuitable narration. Keep `TTS_PROVIDER=edge-tts` for the existing Persian pipeline.

**Important license note for a monetized YouTube channel:** the Python package's code license is Apache 2.0, but the Kitten-TTS 2 weights are under the separate Stellon Labs Community License. That license says commercial use requires registration/contact with Stellon Labs and includes eligibility and attribution requirements. Check the current model license before using Kitten-generated audio commercially or distributing a product that includes it.

References:
- Kitten-TTS code and language/model documentation: https://github.com/KittenML/KittenTTS
- Kitten-TTS 2 model card and supported voices/languages: https://huggingface.co/KittenML/kitten-tts-2
- Kitten-TTS 2 model license: https://huggingface.co/KittenML/kitten-tts-2/blob/main/LICENSE.md
