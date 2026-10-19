#!/usr/bin/env python3
"""Colab entrypoint — runs viral short engine with default / uploaded story."""
from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

# Minimal bootstrap: engine code is inlined via import path when repo is checked out,
# or we fall back to executing the engine module content.

def main() -> int:
    # On Colab Actions we only upload this file — keep engine self-contained import by path
    root_candidates = [
        Path("/content"),
        Path("/home/runner/work/Youtube1/Youtube1"),
        Path.cwd(),
    ]
    engine = None
    for root in root_candidates:
        cand = root / "engine" / "viral_short.py"
        if cand.is_file():
            sys.path.insert(0, str(root))
            break
    try:
        from engine.viral_short import load_story, render  # type: ignore
    except Exception:
        # Self-run: execute sibling if present
        here = Path(__file__).resolve().parent
        eng = here.parent / "engine" / "viral_short.py"
        if eng.is_file():
            import importlib.util
            spec = importlib.util.spec_from_file_location("viral_short", eng)
            mod = importlib.util.module_from_spec(spec)
            assert spec.loader
            spec.loader.exec_module(mod)
            load_story = mod.load_story
            render = mod.render
        else:
            raise RuntimeError("engine/viral_short.py not found")

    story_path = None
    for p in [
        Path("/content/story.json"),
        Path("stories/sapling.json"),
        Path("/home/runner/work/Youtube1/Youtube1/stories/sapling.json"),
    ]:
        if p.is_file():
            story_path = str(p)
            break

    story = load_story(story_path)
    out = Path("/content/final_story.mp4")
    work = Path("/content/engine_work")
    meta = render(story, out, work)
    print(json.dumps(meta), flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        traceback.print_exc()
        raise SystemExit(1)
