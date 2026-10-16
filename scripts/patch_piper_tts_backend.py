#!/usr/bin/env python3
"""Wire free offline Piper Persian TTS into spiritual_tts with edge fallback."""
from __future__ import annotations

from pathlib import Path

TARGET = Path(__file__).resolve().parents[1] / "app" / "spiritual_tts.py"
CHANNEL = Path(__file__).resolve().parents[1] / "config" / "channel.yaml"
REQ = Path(__file__).resolve().parents[1] / "requirements.txt"


def main() -> int:
    text = TARGET.read_text(encoding="utf-8")
    if "piper" in text and "synthesize_piper" in text:
        print("PATCH_NOOP spiritual_tts")
    else:
        # Expand provider allow-list
        old = '    if provider not in {"edge-tts", "elevenlabs"}:\n        raise ValueError(f"unsupported TTS_PROVIDER: {provider}")'
        new = '    if provider not in {"edge-tts", "elevenlabs", "piper"}:\n        raise ValueError(f"unsupported TTS_PROVIDER: {provider}")'
        if old not in text:
            raise SystemExit("PATCH_FAIL: provider allow-list")
        text = text.replace(old, new, 1)

        # Default provider prefers piper when available via env TTS_PROVIDER
        # In scene loop, when provider==piper use synthesize_piper instead of edge.

        old_loop = '''                if provider == "elevenlabs":
                    events = _render_elevenlabs(
                        scene_text, part, hint=hint,
                        previous_text=scene_texts[index - 1] if index > 0 else "",
                        next_text=scene_texts[index + 1] if index + 1 < len(scene_texts) else "",
                    )
                else:
                    events = asyncio.run(_render(scene_text, part, rate=rate, pitch=pitch))
'''
        new_loop = '''                if provider == "elevenlabs":
                    events = _render_elevenlabs(
                        scene_text, part, hint=hint,
                        previous_text=scene_texts[index - 1] if index > 0 else "",
                        next_text=scene_texts[index + 1] if index + 1 < len(scene_texts) else "",
                    )
                elif provider == "piper":
                    from app.piper_tts import synthesize_piper
                    synthesize_piper(
                        scene_text, part,
                        mood=str(scene.get("mood") or ""),
                        hint=hint if isinstance(hint, dict) else {},
                    )
                    # Approximate word timings for captions (even split).
                    import wave as _wave
                    dur = _duration(part)
                    words = scene_text.split()
                    events = []
                    if words:
                        slot = dur / max(len(words), 1)
                        for wi, w in enumerate(words):
                            events.append({
                                "type": "WordBoundary",
                                "text": w,
                                "offset": int(round(wi * slot * 10_000_000)),
                                "duration": max(1, int(round(slot * 10_000_000))),
                            })
                else:
                    events = asyncio.run(_render(scene_text, part, rate=rate, pitch=pitch))
'''
        if old_loop not in text:
            raise SystemExit("PATCH_FAIL: scene TTS loop not found")
        text = text.replace(old_loop, new_loop, 1)

        compile(text, str(TARGET), "exec")
        TARGET.write_text(text, encoding="utf-8")
        print("PATCH_APPLIED piper backend")

    if CHANNEL.is_file():
        ch = CHANNEL.read_text(encoding="utf-8")
        if "tts_model: piper" not in ch:
            ch = ch.replace("tts_model: edge-tts", "tts_model: piper", 1)
            CHANNEL.write_text(ch, encoding="utf-8")
            print("CHANNEL_SET piper")

    if REQ.is_file():
        req = REQ.read_text(encoding="utf-8")
        add = []
        if "piper-tts" not in req:
            add.append("piper-tts>=1.2.0")
        if "huggingface_hub" not in req:
            add.append("huggingface_hub>=0.23.0")
        if add:
            REQ.write_text(req.rstrip() + "\n" + "\n".join(add) + "\n", encoding="utf-8")
            print("REQUIREMENTS_UPDATED")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
