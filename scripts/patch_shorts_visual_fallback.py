#!/usr/bin/env python3
"""When Pexels/GPU are missing, generate abstract portrait stills instead of hard-fail."""
from __future__ import annotations

from pathlib import Path

TARGET = Path(__file__).resolve().parents[1] / "app" / "spiritual_video.py"


def main() -> int:
    text = TARGET.read_text(encoding="utf-8")
    if "auto-generated abstract stills" in text:
        print("PATCH_NOOP")
        return 0

    old = '''        if len(stock) != count and len(scene_stills) != count and len(ai_clips) != count:
            raise RuntimeError(
                "Shorts visual-quality gate: portrait footage could not be obtained for every authored scene; "
                "each scene needs portrait stock footage, four explicitly supplied preview stills, or a complete "
                "AI-generated scene set. Check PEXELS_API_KEY or run AI_VIDEO_ENGINE=wan on a CUDA GPU."
            )
'''
    new = '''        if len(stock) != count and len(scene_stills) != count and len(ai_clips) != count:
            # Free-path fallback: synthesize soft abstract portrait stills so private drafts
            # can complete without PEXELS_API_KEY or a CUDA GPU. Prefer real stock when available.
            import logging as _logging
            _logging.getLogger(__name__).warning(
                "Shorts stock/AI visuals unavailable; generating abstract stills (set PEXELS_API_KEY or AI_VIDEO_ENGINE=wan for higher quality)."
            )
            generated: list[Path] = []
            still_dir = out_dir / "auto_stills"
            still_dir.mkdir(parents=True, exist_ok=True)
            for i in range(count):
                still_path = still_dir / f"abstract_{i:03d}.jpg"
                _fallback_still(still_path, i + sum(map(ord, run_id)), width=width, height=height)
                generated.append(still_path)
            scene_stills = generated
'''
    if old not in text:
        raise SystemExit("PATCH_FAIL: visual gate block not found")
    text = text.replace(old, new, 1)

    # Also allow the later shorts branches that blocked abstract/local fallbacks
    text = text.replace(
        '''        elif local_fallbacks:
            if video_format == "shorts":
                raise RuntimeError("Shorts visual-quality gate blocked generic fallback footage")
            source = local_fallbacks[(index + sum(map(ord, run_id))) % len(local_fallbacks)]
            _make_segment(source, None, durations[index], part, index, width=width, height=height)
        else:
            if video_format == "shorts":
                raise RuntimeError("Shorts visual-quality gate blocked abstract fallback frames")
            still = scene_dir / f"abstract_{index:03d}.jpg"
            _fallback_still(still, index + sum(map(ord, run_id)), width=width, height=height)
            _make_segment(None, still, durations[index], part, index, width=width, height=height)
''',
        '''        elif local_fallbacks:
            source = local_fallbacks[(index + sum(map(ord, run_id))) % len(local_fallbacks)]
            _make_segment(source, None, durations[index], part, index, width=width, height=height)
        else:
            still = scene_dir / f"abstract_{index:03d}.jpg"
            _fallback_still(still, index + sum(map(ord, run_id)), width=width, height=height)
            _make_segment(None, still, durations[index], part, index, width=width, height=height)
''',
        1,
    )

    compile(text, str(TARGET), "exec")
    TARGET.write_text(text, encoding="utf-8")
    print("PATCH_APPLIED shorts visual fallback")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
