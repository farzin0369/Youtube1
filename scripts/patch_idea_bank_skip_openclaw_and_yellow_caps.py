#!/usr/bin/env python3
"""1) Skip OpenClaw hard-fail when USE_IDEA_BANK=1
2) Yellow-box caption style matching user reference Shorts.
"""
from __future__ import annotations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DAILY = ROOT / ".github" / "workflows" / "daily_run.yml"
VIDEO = ROOT / "app" / "spiritual_video.py"


def main() -> int:
    # --- workflow: make OpenClaw non-blocking when idea bank is on ---
    if DAILY.is_file():
        yml = DAILY.read_text(encoding="utf-8")
        if "continue-on-error: true" not in yml or "OpenClaw editorial" not in yml:
            yml2 = yml.replace(
                "- name: Run OpenClaw editorial manager and specialist agents\n",
                "- name: Run OpenClaw editorial manager and specialist agents\n"
                "        continue-on-error: true  # idea-bank path does not need OpenClaw\n",
                1,
            )
            if yml2 != yml:
                DAILY.write_text(yml2, encoding="utf-8")
                print("WORKFLOW_OPENCLAW_SOFT")
            else:
                print("WORKFLOW_NO_MATCH")
        else:
            print("WORKFLOW_NOOP")

    # --- ASS styles: yellow box captions like reference ---
    if not VIDEO.is_file():
        print("NO_VIDEO")
        return 0
    text = VIDEO.read_text(encoding="utf-8")
    if "yellow-box-v1" in text:
        print("CAPS_NOOP")
        return 0

    # Replace Default / Hook styles with high-contrast yellow boxes
    # ASS: PrimaryColour=&H00BBGGRR, BackColour box, BorderStyle=3 = opaque box
    if "Style: Default,Noto Naskh Arabic,72," in text:
        text = text.replace(
            "Style: Default,Noto Naskh Arabic,72,&H00FFFFFF,&H0000FFFF,&HCC000000,&HCC000000,-1,0,0,0,100,100,0,0,4,12,0,2,40,40,280,",
            # yellow-box-v1: black text on bright yellow opaque box
            "Style: Default,Noto Naskh Arabic,68,&H00000000,&H00000000,&H00000000,&H0000FFFF,-1,0,0,0,100,100,0,0,0,0,0,3,36,36,320,",
            1,
        )
    elif "Style: Default,Noto Naskh Arabic,48," in text:
        text = text.replace(
            "Style: Default,Noto Naskh Arabic,48,",
            "Style: Default,Noto Naskh Arabic,68,&H00000000,&H00000000,&H00000000,&H0000FFFF,-1,0,0,0,100,100,0,0,0,0,0,3,36,36,320,;yellow-box-v1\nStyle: DefaultOld,Noto Naskh Arabic,48,",
            1,
        )

    if "Style: Hook,Noto Naskh Arabic,92," in text:
        text = text.replace(
            "Style: Hook,Noto Naskh Arabic,92,&H003EC9FF,&H0000FFFF,&HCC000000,&HCC000000,-1,0,0,0,100,100,0,0,5,14,0,8,36,36,360,1",
            "Style: Hook,Noto Naskh Arabic,72,&H00000000,&H00000000,&H00000000,&H0000FFFF,-1,0,0,0,100,100,0,0,0,0,0,3,36,36,380,1",
            1,
        )

    if "yellow-box-v1" not in text:
        # tag in metadata comment near caption_font_size
        text = text.replace(
            '"caption_font_size": 72 if video_format == "shorts" else 40',
            '"caption_font_size": 68 if video_format == "shorts" else 40,  # yellow-box-v1',
            1,
        )

    compile(text, str(VIDEO), "exec")
    VIDEO.write_text(text, encoding="utf-8")
    print("CAPS_YELLOW_APPLIED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
