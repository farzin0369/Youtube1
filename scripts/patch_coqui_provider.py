#!/usr/bin/env python3
"""Wire Coqui as preferred natural male TTS with piper/edge fallback."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def patch_spiritual_tts() -> None:
    p = ROOT / "app" / "spiritual_tts.py"
    t = p.read_text(encoding="utf-8")
    if "coqui-vits-v1" in t:
        print("TTS_NOOP")
        return

    # expand allowed providers
    t = t.replace(
        'if provider not in {"edge-tts", "elevenlabs", "piper"}:',
        'if provider not in {"edge-tts", "elevenlabs", "piper", "coqui", "vits"}:  # coqui-vits-v1',
        1,
    )
    t = t.replace(
        'aliases = {"edge": "edge-tts", "eleven": "elevenlabs", "eleven-v4": "elevenlabs"}',
        'aliases = {"edge": "edge-tts", "eleven": "elevenlabs", "eleven-v4": "elevenlabs", "vits": "coqui", "coqui-tts": "coqui"}',
        1,
    )

    # Prefer coqui when TTS_PROVIDER unset or piper (upgrade path)
    old_prov = '''    configured = env("TTS_PROVIDER")  # male-piper-gyro-v1
    # Prefer piper male (gyro/ganji/amir). Edge Farid remains fallback if piper fails.
    if configured:
        provider = str(configured).strip().lower()
    else:
        try:
            provider = str((load_channel_config().get("channel") or {}).get("tts_model") or "edge-tts").strip().lower()
        except Exception:
            provider = "edge-tts"'''
    new_prov = '''    configured = env("TTS_PROVIDER")  # coqui-vits-v1
    # Natural male: coqui VITS > piper gyro > edge Farid
    if configured:
        provider = str(configured).strip().lower()
    else:
        provider = "coqui"  # default to natural male VITS'''
    if old_prov in t:
        t = t.replace(old_prov, new_prov, 1)
    elif 'configured = env("TTS_PROVIDER")' in t and "coqui-vits-v1" not in t:
        # softer
        t = t.replace(
            'provider = "edge-tts"\n    aliases',
            'provider = "coqui"\n    aliases',
            1,
        )

    # synthesis branch: try coqui before piper
    if 'provider == "coqui"' not in t:
        needle = '                elif provider == "piper":'
        inject = '''                elif provider in {"coqui", "vits"}:
                    from app.coqui_tts import synthesize_coqui
                    try:
                        synthesize_coqui(chunk_text, chunk_wav, mood=str(mood or "calm"))
                    except Exception as coqui_exc:
                        logger.warning("coqui failed (%s); falling back to piper", type(coqui_exc).__name__)
                        from app.piper_tts import synthesize_piper
                        try:
                            synthesize_piper(chunk_text, chunk_wav, mood=str(mood or "calm"))
                        except Exception:
                            logger.warning("piper also failed; edge-tts fallback")
                            # force edge path by reassign — handled below if we raise
                            raise
                elif provider == "piper":'''
        if needle in t:
            t = t.replace(needle, inject, 1)

    compile(t, str(p), "exec")
    p.write_text(t, encoding="utf-8")
    print("TTS_OK")


def patch_requirements() -> None:
    p = ROOT / "requirements.txt"
    t = p.read_text(encoding="utf-8")
    if "TTS" in t or "coqui" in t.lower():
        print("REQ_NOOP")
        return
    t = t.rstrip() + "\nTTS>=0.22.0\n"
    p.write_text(t + "\n", encoding="utf-8")
    print("REQ_OK")


def main() -> int:
    patch_spiritual_tts()
    patch_requirements()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
