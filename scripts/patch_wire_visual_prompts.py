#!/usr/bin/env python3
"""Wire visual_prompts into spiritual_video Mixkit/AI query selection."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
p = ROOT / "app" / "spiritual_video.py"
t = p.read_text(encoding="utf-8")

if "visual_prompts" in t and "cinematic_prompts_for_scenes" in t:
    print("ALREADY_WIRED")
else:
    # ensure import
    if "from app.visual_prompts" not in t:
        # after other app imports
        anchor = "from __future__ import annotations\n"
        if anchor in t:
            t = t.replace(
                anchor,
                anchor + "\nfrom app.visual_prompts import cinematic_prompts_for_scenes, mixkit_keywords_from_scenes\n",
                1,
            )

    # Prefer cinematic keywords when building queries for shorts
    old = "            queries = keywords[:max(count, 4)] if keywords else [\"calm\", \"light\", \"path\", \"sunrise\"]"
    # find typical queries assignment near shorts branch
    if "mixkit_keywords_from_scenes" not in t:
        # inject after count is known in shorts branch
        marker = "    if video_format == \"shorts\":"
        idx = t.find(marker)
        if idx != -1:
            # insert helper after ai_engine block start — safer: replace _visual_queries usage
            pass
        # Replace scene-match query builder call if present
        t2 = t.replace(
            "queries = _visual_queries_for_scenes(keywords or [\"calm\", \"light\", \"path\", \"sunrise\"], count)  # scene-match-v1",
            "queries = mixkit_keywords_from_scenes(keywords or [\"آرام\"], topic=\" \".join(keywords or []), count=count)  # visual-prompts-v1",
            1,
        )
        if t2 != t:
            t = t2
        else:
            # fallback: after "if video_format == shorts" set queries from visual prompts when keywords look Persian
            needle = "    if video_format == \"shorts\":\n"
            if needle in t and "mixkit_keywords_from_scenes" not in t:
                t = t.replace(
                    needle,
                    needle
                    + "        # visual-prompts-v1: map narration themes to search/AI prompts\n"
                    + "        try:\n"
                    + "            if keywords:\n"
                    + "                queries = mixkit_keywords_from_scenes(keywords, topic=str(title or \"\"), count=count)\n"
                    + "        except Exception:\n"
                    + "            pass\n",
                    1,
                )

    # AI engines: use cinematic full prompts instead of raw keywords
    for eng, fn in [("wan", "generate_wan_clips"), ("ltx", "generate_ltx_clips")]:
        old_call = f"ai_clips = {fn}(\n                queries,"
        new_call = (
            f"ai_prompts = cinematic_prompts_for_scenes(queries, topic=str(title or \"\"))\n"
            f"            ai_clips = {fn}(\n                ai_prompts,"
        )
        if old_call in t and "ai_prompts = cinematic_prompts" not in t:
            t = t.replace(old_call, new_call, 1)

    compile(t, str(p), "exec")
    p.write_text(t, encoding="utf-8")
    print("WIRED")

# soft-fail missing LTX already provided by new module
print("DONE")
