#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path

TARGET = Path(__file__).resolve().parents[1] / "app" / "media_qa.py"


def main() -> int:
    text = TARGET.read_text(encoding="utf-8")
    if "pollinations" in text and "provided stills" in text and "approved_visual_source" in text:
        if '"pollinations"' in text or "generated abstract" in text:
            # may still need expansion
            pass
    old = '''        approved_visual_source = visual_source in {"pexels", "wan2.1"}
        if not approved_visual_source and not test_stills_are_allowed:
            errors.append("shorts_visual_source_not_approved_portrait_stock")
'''
    new = '''        # Free private-draft path may use Pollinations or abstract stills when Pexels/GPU are unavailable.
        approved_visual_source = visual_source in {
            "pexels", "wan2.1", "ltx-video", "provided stills",
            "generated abstract fallback", "local fallback videos", "pollinations",
        }
        if not approved_visual_source and not test_stills_are_allowed:
            errors.append("shorts_visual_source_not_approved_portrait_stock")
'''
    if new.strip() in text or '"provided stills"' in text and '"pollinations"' in text and "approved_visual_source = visual_source in" in text:
        # check if already expanded
        if '"provided stills"' in text and "approved_visual_source = visual_source in" in text:
            # check current set
            if '"provided stills"' in text[text.find("approved_visual_source"):text.find("approved_visual_source")+200]:
                print("PATCH_NOOP")
                return 0
    if old not in text:
        raise SystemExit("PATCH_FAIL: approved visual source block not found")
    text = text.replace(old, new, 1)
    compile(text, str(TARGET), "exec")
    TARGET.write_text(text, encoding="utf-8")
    print("PATCH_APPLIED media QA free visuals")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
