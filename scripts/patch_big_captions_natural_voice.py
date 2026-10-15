#!/usr/bin/env python3
"""Bigger readable Shorts captions + slower clearer Edge TTS."""
from __future__ import annotations

from pathlib import Path

VIDEO = Path(__file__).resolve().parents[1] / "app" / "spiritual_video.py"
TTS = Path(__file__).resolve().parents[1] / "app" / "spiritual_tts.py"
CHANNEL = Path(__file__).resolve().parents[1] / "config" / "channel.yaml"


def main() -> int:
    video = VIDEO.read_text(encoding="utf-8")
    changed = False

    # Enlarge ASS styles for mobile readability (1080x1920).
    old_styles = (
        "Style: Default,Noto Naskh Arabic,48,&H00FFFFFF,&H0000FFFF,&H99000000,&HAA111924,"
        "-1,0,0,0,100,100,0,0,3,10,0,2,50,50,220,"
    )
    # Find actual lines more flexibly
    if "Style: Default,Noto Naskh Arabic,72," not in video:
        video2 = video.replace(
            "Style: Default,Noto Naskh Arabic,48,",
            "Style: Default,Noto Naskh Arabic,72,",
            1,
        )
        video2 = video2.replace(
            "Style: Hook,Noto Naskh Arabic,56,",
            "Style: Hook,Noto Naskh Arabic,92,",
            1,
        )
        # Thicker outline/shadow for contrast on busy footage
        video2 = video2.replace(
            "Style: Default,Noto Naskh Arabic,72,&H00FFFFFF,&H0000FFFF,&H99000000,&HAA111924,-1,0,0,0,100,100,0,0,3,10,0,2,50,50,220,",
            "Style: Default,Noto Naskh Arabic,72,&H00FFFFFF,&H0000FFFF,&HCC000000,&HCC000000,-1,0,0,0,100,100,0,0,4,12,0,2,40,40,280,",
            1,
        )
        video2 = video2.replace(
            "Style: Hook,Noto Naskh Arabic,92,&H003EC9FF,&H0000FFFF,&H99000000,&HAA111924,-1,0,0,0,100,100,0,0,3,10,0,8,46,46,300,1",
            "Style: Hook,Noto Naskh Arabic,92,&H003EC9FF,&H0000FFFF,&HCC000000,&HCC000000,-1,0,0,0,100,100,0,0,5,14,0,8,36,36,360,1",
            1,
        )
        if video2 == video:
            # partial only font size
            if "Style: Default,Noto Naskh Arabic,72," in video2:
                video = video2
                changed = True
            else:
                raise SystemExit("PATCH_FAIL: ASS style lines not found")
        else:
            video = video2
            changed = True

    if '"caption_font_size": 48 if video_format == "shorts" else 36' in video:
        video = video.replace(
            '"caption_font_size": 48 if video_format == "shorts" else 36',
            '"caption_font_size": 72 if video_format == "shorts" else 40',
            1,
        )
        changed = True

    if changed:
        compile(video, str(VIDEO), "exec")
        VIDEO.write_text(video, encoding="utf-8")
        print("PATCH_APPLIED big captions")
    else:
        print("CAPTIONS_NOOP")

    # Clearer TTS: slower base rates for Persian pronunciation
    tts = TTS.read_text(encoding="utf-8")
    if "clearer_v3" in tts:
        print("TTS_NOOP")
    else:
        old = '''    # natural_v2: milder rates sound less robotic on Edge neural voices.
    base_rate, base_pitch = {
        "hook": ("+2%", "+1Hz"),
        "calm": ("-4%", "-1Hz"),
        "reassuring": ("-2%", "+0Hz"),
        "motivational": ("+3%", "+1Hz"),
    }.get(str(mood or "").lower(), ("-2%", "+0Hz"))
'''
        new = '''    # clearer_v3: slightly slow delivery improves Persian pronunciation on Edge TTS.
    base_rate, base_pitch = {
        "hook": ("-2%", "+0Hz"),
        "calm": ("-8%", "-1Hz"),
        "reassuring": ("-6%", "+0Hz"),
        "motivational": ("-1%", "+0Hz"),
    }.get(str(mood or "").lower(), ("-5%", "+0Hz"))
'''
        if old not in tts:
            # maybe natural_v2 not present - try original
            old2 = '''    base_rate, base_pitch = {
        "hook": ("+2%", "+1Hz"),
        "calm": ("-4%", "-1Hz"),
        "reassuring": ("-2%", "+0Hz"),
        "motivational": ("+3%", "+1Hz"),
    }.get(str(mood or "").lower(), ("-2%", "+0Hz"))
'''
            if old2 in tts:
                tts = tts.replace(old2, new, 1)
            else:
                raise SystemExit("PATCH_FAIL: TTS rate block not found")
        else:
            tts = tts.replace(old, new, 1)

        # Default rate for non-scene path
        tts = tts.replace('rate: str = "-4%"', 'rate: str = "-6%"', 1)

        compile(tts, str(TTS), "exec")
        TTS.write_text(tts, encoding="utf-8")
        print("PATCH_APPLIED clearer TTS v3")

    # Keep male narrator but document; Farid is the only free male Edge Persian neural voice.
    if CHANNEL.is_file():
        ch = CHANNEL.read_text(encoding="utf-8")
        if "tts_voice: fa-IR-FaridNeural" in ch and "clearer slow delivery" not in ch:
            ch = ch.replace(
                "tts_voice: fa-IR-FaridNeural",
                "tts_voice: fa-IR-FaridNeural  # free Edge neural; slower rate improves clarity",
                1,
            )
            CHANNEL.write_text(ch, encoding="utf-8")
            print("CHANNEL_NOTE")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
