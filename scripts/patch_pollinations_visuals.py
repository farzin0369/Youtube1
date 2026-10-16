#!/usr/bin/env python3
"""Add free no-key Pollinations image fetch before abstract stills."""
from __future__ import annotations

from pathlib import Path

TARGET = Path(__file__).resolve().parents[1] / "app" / "spiritual_video.py"


def main() -> int:
    text = TARGET.read_text(encoding="utf-8")
    if "def fetch_pollinations_stills" in text:
        print("PATCH_NOOP")
        return 0

    insert_after = "def fetch_stock(\n"
    if insert_after not in text:
        raise SystemExit("PATCH_FAIL: fetch_stock not found")

    helper = '''def fetch_pollinations_stills(
    keywords: list[str], out_dir: Path, count: int = 4, *,
    width: int = 1080, height: int = 1920,
) -> tuple[list[Path], list[str]]:
    """Download free AI stills from Pollinations (no API key required)."""
    import urllib.parse
    import urllib.request

    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    credits: list[str] = []
    queries = (keywords or ["peaceful abstract light"])[: max(count, 1)]
    while len(queries) < count:
        queries.append(queries[len(queries) % max(len(queries), 1)])
    for index, query in enumerate(queries[:count]):
        prompt = f"cinematic vertical portrait photo, {query}, soft natural light, realistic, no text, no watermark"
        url = (
            "https://image.pollinations.ai/prompt/"
            + urllib.parse.quote(prompt)
            + f"?width={width}&height={height}&nologo=true&seed={1000 + index}"
        )
        target = out_dir / f"pollinations_{index:03d}.jpg"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ImamAli110-pipeline/1.0"})
            with urllib.request.urlopen(req, timeout=45) as response:
                data = response.read()
            if len(data) < 8_000:
                raise ValueError("image too small")
            target.write_bytes(data)
            paths.append(target)
            credits.append(f"Visual generated via Pollinations (free): {query}")
        except Exception as exc:
            logging.getLogger(__name__).warning(
                "Pollinations still failed for %r (%s)", query[:80], type(exc).__name__
            )
    return paths, credits


'''
    text = text.replace(insert_after, helper + insert_after, 1)

    # Prefer Pollinations stills before abstract fallback when stock/AI missing.
    old = '''        if len(stock) != count and len(scene_stills) != count and len(ai_clips) != count:
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
    new = '''        if len(stock) != count and len(scene_stills) != count and len(ai_clips) != count:
            # Free path (no Pexels account needed): Pollinations images, then abstract stills.
            free_stills, free_credits = fetch_pollinations_stills(
                queries, out_dir / "pollinations", count=count, width=width, height=height,
            )
            if len(free_stills) == count:
                scene_stills = free_stills
                credits = free_credits
                logging.getLogger(__name__).info("using free Pollinations stills for %s scenes", count)
            else:
                logging.getLogger(__name__).warning(
                    "Pollinations incomplete; generating abstract stills (optional: set PEXELS_API_KEY later)."
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
        # try already-patched abstract-only variant
        if "fetch_pollinations_stills" in text:
            print("PATCH_PARTIAL")
        else:
            raise SystemExit("PATCH_FAIL: shorts free fallback block not found")
    else:
        text = text.replace(old, new, 1)

    compile(text, str(TARGET), "exec")
    TARGET.write_text(text, encoding="utf-8")
    print("PATCH_APPLIED pollinations free visuals")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
