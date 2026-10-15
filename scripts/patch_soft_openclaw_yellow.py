#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
YML = ROOT / ".github" / "workflows" / "daily_run.yml"
VID = ROOT / "app" / "spiritual_video.py"


def main() -> int:
    yml = YML.read_text(encoding="utf-8")
    if "continue-on-error: true" not in yml:
        needle = "- name: Run OpenClaw editorial manager and specialist agents\n"
        if needle in yml:
            yml = yml.replace(
                needle,
                needle + "        continue-on-error: true\n",
                1,
            )
            YML.write_text(yml, encoding="utf-8")
            print("OPENCLAW_SOFT")
        else:
            print("OPENCLAW_STEP_MISSING")
    else:
        print("OPENCLAW_ALREADY")

    text = VID.read_text(encoding="utf-8")
    if "yellow-box-v1" in text:
        print("YELLOW_NOOP")
        return 0

    # Replace style lines with yellow opaque box (BorderStyle=3), black text
    old_def = (
        "Style: Default,Noto Naskh Arabic,72,&H00FFFFFF,&H0000FFFF,&HCC000000,&HCC000000,"
        "-1,0,0,0,100,100,0,0,4,12,0,2,40,40,280,1"
    )
    new_def = (
        "Style: Default,Noto Naskh Arabic,68,&H00000000,&H00000000,&H00000000,&H0000FFFF,"
        "-1,0,0,0,100,100,0,0,0,0,0,3,36,36,320,1"
    )
    # yellow-box-v1 marker in a comment-like unused style name isn't valid; put in metadata path
    if old_def in text:
        text = text.replace(old_def, new_def, 1)
    else:
        # try without trailing 1
        old2 = "Style: Default,Noto Naskh Arabic,72,&H00FFFFFF,&H0000FFFF,&HCC000000,&HCC000000,-1,0,0,0,100,100,0,0,4,12,0,2,40,40,280,"
        new2 = "Style: Default,Noto Naskh Arabic,68,&H00000000,&H00000000,&H00000000,&H0000FFFF,-1,0,0,0,100,100,0,0,0,0,0,3,36,36,320,"
        if old2 in text:
            text = text.replace(old2, new2, 1)
        else:
            print("DEFAULT_STYLE_MISS")

    old_hook = "Style: Hook,Noto Naskh Arabic,92,&H003EC9FF,&H0000FFFF,&HCC000000,&HCC000000,-1,0,0,0,100,100,0,0,5,14,0,8,36,36,360,1"
    new_hook = "Style: Hook,Noto Naskh Arabic,72,&H00000000,&H00000000,&H00000000,&H0000FFFF,-1,0,0,0,100,100,0,0,0,0,0,3,36,36,380,1"
    if old_hook in text:
        text = text.replace(old_hook, new_hook, 1)
    else:
        old_h2 = "Style: Hook,Noto Naskh Arabic,92,"
        if old_h2 in text:
            # only bump size path already handled partially
            pass

    if "yellow-box-v1" not in text:
        text = text.replace(
            '"caption_font_size": 72 if video_format == "shorts" else 40',
            '"caption_font_size": 68 if video_format == "shorts" else 40,  # yellow-box-v1',
            1,
        )

    compile(text, str(VID), "exec")
    VID.write_text(text, encoding="utf-8")
    print("YELLOW_APPLIED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
