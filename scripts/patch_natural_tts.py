#!/usr/bin/env python3
"""Softer Edge TTS prosody for more natural Persian narration."""
from __future__ import annotations

from pathlib import Path

TARGET = Path(__file__).resolve().parents[1] / "app" / "spiritual_tts.py"


def main() -> int:
    text = TARGET.read_text(encoding="utf-8")
    if "natural_v2" in text:
        print("PATCH_NOOP")
        return 0

    old = '''    base_rate, base_pitch = {
        "hook": ("+5%", "+3Hz"),
        "calm": ("-8%", "-2Hz"),
        "reassuring": ("-3%", "+0Hz"),
        "motivational": ("+6%", "+2Hz"),
    }.get(str(mood or "").lower(), ("-4%", "+0Hz"))
'''
    new = '''    # natural_v2: milder rates sound less robotic on Edge neural voices.
    base_rate, base_pitch = {
        "hook": ("+2%", "+1Hz"),
        "calm": ("-4%", "-1Hz"),
        "reassuring": ("-2%", "+0Hz"),
        "motivational": ("+3%", "+1Hz"),
    }.get(str(mood or "").lower(), ("-2%", "+0Hz"))
'''
    if old not in text:
        raise SystemExit("PATCH_FAIL: base_rate block not found")
    text = text.replace(old, new, 1)

    # Reduce emotion exaggeration scale.
    text = text.replace(
        "scale = intensity * confidence * 0.5",
        "scale = intensity * confidence * 0.25  # natural_v2 softer",",",
        1,
    )
    # fix possible typo if double replace
    text = text.replace(
        "scale = intensity * confidence * 0.25  # natural_v2 softer",",",
        "scale = intensity * confidence * 0.25  # natural_v2 softer",
    )

    compile(text, str(TARGET), "exec")
    TARGET.write_text(text, encoding="utf-8")
    print("PATCH_APPLIED natural TTS v2")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
