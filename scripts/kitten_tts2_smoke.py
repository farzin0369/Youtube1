from pathlib import Path
import json
import traceback

OUT = Path("output/kitten-tts-2")
OUT.mkdir(parents=True, exist_ok=True)
report = {
    "model_id": "KittenML/kitten-tts-2",
    "package": "kittenml",
    "status": "STARTED",
    "note": "This smoke test verifies model loading and audio generation. Persian pronunciation quality/language support is not assumed."
}
(OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
text = "سلام. این یک نمونه آزمایشی با مدل کیتن تی تی اس دو است. امروز می‌خواهیم کیفیت تولید صدا را بررسی کنیم."
(OUT / "sample-script-fa.txt").write_text(text + "\n", encoding="utf-8")

try:
    from kittenml import KittenTTS
    import soundfile as sf
    model = KittenTTS("KittenML/kitten-tts-2", weights="emb4")
    report["available_voices"] = [str(v) for v in model.available_voices]
    # Pick a stable built-in voice if present; otherwise use the first voice exposed by the model.
    voices = list(model.available_voices)
    voice = "Bruno" if "Bruno" in voices else voices[0]
    report["voice"] = voice
    audio = model.generate(text, voice=voice)
    wav = OUT / "kitten-tts-2-persian-sample.wav"
    sf.write(str(wav), audio, model.sample_rate)
    report["sample_rate"] = int(model.sample_rate)
    report["audio_samples"] = int(len(audio))
    report["duration_seconds"] = round(len(audio) / float(model.sample_rate), 3)
    report["status"] = "GENERATED_BUT_PERSIAN_UNVERIFIED"
except Exception as exc:
    report["status"] = "FAILED"
    report["error"] = repr(exc)
    report["traceback"] = traceback.format_exc()
    raise
finally:
    (OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
