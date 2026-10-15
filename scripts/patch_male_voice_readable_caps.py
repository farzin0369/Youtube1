#!/usr/bin/env python3
"""Male voice only + readable captions + oral spelling fixes."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def patch_tts() -> None:
    p = ROOT / "app" / "spiritual_tts.py"
    t = p.read_text(encoding="utf-8")
    if "male-voice-v1" in t:
        print("TTS_NOOP")
        return
    # Force male Edge when Piper Mana (female) would be used
    old = '''    configured = env("TTS_PROVIDER")
'''
    # Find provider resolution block
    if 'configured = env("TTS_PROVIDER")' in t and "male-voice-v1" not in t:
        t = t.replace(
            'configured = env("TTS_PROVIDER")',
            'configured = env("TTS_PROVIDER")  # male-voice-v1\n'
            '    # Mana-Persian-Piper is a female voice; channel requires male narration.\n'
            '    if (configured or "").strip().lower() == "piper" and env("ALLOW_FEMALE_TTS", "").lower() not in {"1", "true", "yes"}:\n'
            '        logger.warning("piper Mana is female — switching to edge-tts Farid (male)")\n'
            '        configured = "edge-tts"',
            1,
        )
    compile(t, str(p), "exec")
    p.write_text(t, encoding="utf-8")
    print("TTS_MALE")


def patch_video() -> None:
    p = ROOT / "app" / "spiritual_video.py"
    t = p.read_text(encoding="utf-8")
    if "readable-caps-v2" in t:
        print("VID_NOOP")
        return
    # White text + thick black outline + dark translucent box, bottom safe zone
    old_def = (
        "Style: Default,Noto Naskh Arabic,68,&H00000000,&H00000000,&H00000000,&H0000FFFF,"
        "-1,0,0,0,100,100,0,0,0,0,0,3,36,36,320,1"
    )
    new_def = (
        "Style: Default,Noto Naskh Arabic,64,&H00FFFFFF,&H000000FF,&H00000000,&H99000000,"
        "-1,0,0,0,100,100,0,0,1,4,2,3,48,48,220,1"  # readable-caps-v2
    )
    # BorderStyle=3 box, Outline=4 as pad, white primary, black outline, dark back
    # Actually ASS BGR: white=&H00FFFFFF, outline black=&H00000000, back semi black=&H99000000
    new_def = (
        "Style: Default,Noto Naskh Arabic,64,&H00FFFFFF,&H000000FF,&H00000000,&H99000000,"
        "-1,0,0,0,100,100,0,0,1,5,2,3,40,40,200,1"
    )
    if old_def in t:
        t = t.replace(old_def, new_def, 1)
    else:
        # try current yellow style line as single string
        for old in [
            "Style: Default,Noto Naskh Arabic,68,&H00000000,&H00000000,&H00000000,&H0000FFFF,-1,0,0,0,100,100,0,0,0,0,0,3,36,36,320,1",
            "Style: Default,Noto Naskh Arabic,72,&H00FFFFFF,&H0000FFFF,&HCC000000,&HCC000000,-1,0,0,0,100,100,0,0,4,12,0,2,40,40,280,1",
        ]:
            if old in t:
                t = t.replace(
                    old,
                    "Style: Default,Noto Naskh Arabic,64,&H00FFFFFF,&H000000FF,&H00000000,&H99000000,-1,0,0,0,100,100,0,0,1,5,2,3,40,40,200,1",
                    1,
                )
                break

    old_hook = "Style: Hook,Noto Naskh Arabic,72,&H00000000,&H00000000,&H00000000,&H0000FFFF,-1,0,0,0,100,100,0,0,0,0,0,3,36,36,380,1"
    new_hook = "Style: Hook,Noto Naskh Arabic,70,&H00FFFFFF,&H000000FF,&H00000000,&H99000000,-1,0,0,0,100,100,0,0,1,6,2,3,36,36,240,1"
    if old_hook in t:
        t = t.replace(old_hook, new_hook, 1)
    else:
        for old in [
            "Style: Hook,Noto Naskh Arabic,92,&H003EC9FF,&H0000FFFF,&HCC000000,&HCC000000,-1,0,0,0,100,100,0,0,5,14,0,8,36,36,360,1",
        ]:
            if old in t:
                t = t.replace(old, new_hook, 1)
                break

    if "readable-caps-v2" not in t:
        t = t.replace(
            '"caption_font_size": 68 if video_format == "shorts" else 40,  # yellow-box-v1',
            '"caption_font_size": 64 if video_format == "shorts" else 40,  # readable-caps-v2',
            1,
        )
        if "readable-caps-v2" not in t:
            t = t.replace(
                '"caption_font_size": 72 if video_format == "shorts" else 40',
                '"caption_font_size": 64 if video_format == "shorts" else 40,  # readable-caps-v2',
                1,
            )

    compile(t, str(p), "exec")
    p.write_text(t, encoding="utf-8")
    print("VID_READABLE")


def patch_normalize() -> None:
    p = ROOT / "app" / "persian_tts_normalize.py"
    t = p.read_text(encoding="utf-8")
    if "oral-disambig-v1" in t:
        print("NORM_NOOP")
        return
    extra = '''
    # oral-disambig-v1: avoid homograph misreads (کارِت vs کارت)
    ("کارت را", "کار تو را"),
    ("کارت ", "کار تو "),
    ("کارِت", "کار تو"),
    ("بی معنا", "بی معنی"),
    ("دل سپاری", "سپردن دل"),
'''
    if "_REPLACEMENTS" in t and "oral-disambig-v1" not in t:
        t = t.replace(
            "_REPLACEMENTS: list[tuple[str, str]] = [",
            "_REPLACEMENTS: list[tuple[str, str]] = [\n    # oral-disambig-v1\n"
            "    (\"کارت را\", \"کار تو را\"),\n"
            "    (\"کارت \", \"کار تو \"),\n"
            "    (\"کارِت\", \"کار تو\"),\n"
            "    (\"بی معنا\", \"بی معنی\"),\n"
            "    (\"دل سپاری\", \"سپردن دل\"),",
            1,
        )
    compile(t, str(p), "exec")
    p.write_text(t, encoding="utf-8")
    print("NORM_OK")


def patch_bank() -> None:
    p = ROOT / "data" / "shorts_idea_bank.json"
    t = p.read_text(encoding="utf-8")
    # Clear oral forms already mostly good; fix residual ambiguous phrases
    reps = {
        "بی معنا بوده": "بی معنی بوده",
        "دل سپاری همراه تلاش": "سپردن دل همراه تلاش",
        "دل سپاری": "سپردن دل",
    }
    for a, b in reps.items():
        t = t.replace(a, b)
    p.write_text(t, encoding="utf-8")
    print("BANK_OK")


def main() -> int:
    patch_tts()
    patch_video()
    patch_normalize()
    patch_bank()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
