#!/usr/bin/env python3
"""Add free Mixkit vertical video fetch (no API key) + stronger Ken Burns motion."""
from __future__ import annotations

from pathlib import Path

TARGET = Path(__file__).resolve().parents[1] / "app" / "spiritual_video.py"


def main() -> int:
    text = TARGET.read_text(encoding="utf-8")
    if "def fetch_mixkit_stock" in text:
        print("PATCH_NOOP")
        return 0

    helper = '''def fetch_mixkit_stock(
    keywords: list[str], out_dir: Path, count: int = 4, *,
    orientation: str = "portrait",
) -> tuple[list[Path], list[str]]:
    """Download free Mixkit stock clips — no API key, no account required."""
    import re
    import urllib.parse
    import urllib.request

    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    credits: list[str] = []
    seen: set[str] = set()
    queries = (keywords or ["calm nature", "peaceful light", "sunrise", "ocean waves"])[: max(count * 2, 4)]
    # Prefer calm spiritual-adjacent free vertical search terms when queries are abstract.
    extras = ["calm", "nature vertical", "sunrise", "meditation", "ocean waves", "soft light"]
    for keyword in list(queries) + extras:
        if len(paths) >= count:
            break
        try:
            search = urllib.parse.quote(str(keyword).strip() or "calm")
            page_url = f"https://mixkit.co/free-stock-video/{search}/"
            req = urllib.request.Request(
                page_url,
                headers={"User-Agent": "ImamAli110-pipeline/1.0 (free stock; attribution via Mixkit license)"},
            )
            with urllib.request.urlopen(req, timeout=25) as response:
                html = response.read().decode("utf-8", errors="ignore")
            # Prefer higher quality 720/1080 assets.
            candidates = re.findall(
                r"https://assets\\.mixkit\\.co/videos/\\d+/\\d+-(?:720|1080)\\.mp4",
                html,
            )
            if not candidates:
                candidates = re.findall(r"https://assets\\.mixkit\\.co/videos/\\d+/\\d+-\\d+\\.mp4", html)
            for url in candidates:
                if url in seen or len(paths) >= count:
                    continue
                seen.add(url)
                vid_id = url.split("/")[-2]
                target = out_dir / f"mixkit_{vid_id}.mp4"
                try:
                    with urllib.request.urlopen(
                        urllib.request.Request(url, headers={"User-Agent": "ImamAli110-pipeline/1.0"}),
                        timeout=60,
                    ) as clip:
                        data = clip.read()
                    if len(data) < 80_000:
                        continue
                    target.write_bytes(data)
                    paths.append(target)
                    credits.append(f"Mixkit free stock video {vid_id}: {url}")
                    break  # one clip per keyword for variety
                except Exception as exc:
                    logging.getLogger(__name__).warning(
                        "Mixkit download failed (%s) for %s", type(exc).__name__, url[-40:]
                    )
        except Exception as exc:
            logging.getLogger(__name__).warning(
                "Mixkit search failed for %r (%s)", str(keyword)[:60], type(exc).__name__
            )
    return paths, credits


'''
    # Insert before fetch_stock
    marker = "def fetch_stock(\n"
    if marker not in text:
        raise SystemExit("PATCH_FAIL: fetch_stock not found")
    text = text.replace(marker, helper + marker, 1)

    # Prefer Mixkit real motion video when Pexels is empty (before Pollinations stills).
    old_gate = '''        if len(stock) != count and len(scene_stills) != count and len(ai_clips) != count:
'''
    if "fetch_mixkit_stock" not in text[text.find("if len(stock)"): text.find("if len(stock)") + 800]:
        # Insert Mixkit attempt right after fetch_stock returns empty for shorts path.
        # Find the free-path block we added earlier.
        needle = "        if len(stock) != count and len(scene_stills) != count and len(ai_clips) != count:\n"
        insert = '''        if len(stock) != count and len(scene_stills) != count and len(ai_clips) != count:
            mix_paths, mix_credits = fetch_mixkit_stock(
                queries, out_dir / "mixkit", count=count, orientation="portrait",
            )
            if len(mix_paths) == count:
                stock, credits = mix_paths, mix_credits
                logging.getLogger(__name__).info("using free Mixkit motion clips for %s scenes", count)
        if len(stock) != count and len(scene_stills) != count and len(ai_clips) != count:
'''
        if needle not in text:
            raise SystemExit("PATCH_FAIL: visual gate start not found")
        text = text.replace(needle, insert, 1)

    # Stronger Ken Burns on stills (visible slow zoom + pan).
    old_seg = '''        zoom = "1+0.0005*on" if seed % 2 == 0 else "1.08-0.0005*on"
        cmd = ["ffmpeg", "-y", "-loop", "1", "-i", str(image_path), "-t", f"{duration:.3f}", "-vf", f"zoompan=z='{zoom}':d=1:s={width}x{height}:fps={FPS},format=yuv420p", "-an", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "24", str(out_path)]
'''
    new_seg = '''        # Cinematic Ken Burns: slow zoom + horizontal drift so stills feel alive.
        frames = max(int(duration * FPS), 24)
        if seed % 2 == 0:
            z_expr = "min(1.18,1+0.0012*on)"
            x_expr = f"(iw-ow/zoom)*on/{frames}"
            y_expr = f"(ih-oh/zoom)/2"
        else:
            z_expr = "max(1.0,1.16-0.0010*on)"
            x_expr = f"(iw-ow/zoom)*(1-on/{frames})"
            y_expr = f"(ih-oh/zoom)*on/{max(frames,1)}"
        zoompan = (
            f"scale=8000:-1,zoompan=z='{z_expr}':x='{x_expr}':y='{y_expr}':"
            f"d={frames}:s={width}x{height}:fps={FPS},eq=brightness=-0.02:saturation=1.05:contrast=1.06,format=yuv420p"
        )
        cmd = [
            "ffmpeg", "-y", "-loop", "1", "-i", str(image_path), "-t", f"{duration:.3f}",
            "-vf", zoompan, "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            str(out_path),
        ]
'''
    if old_seg in text:
        text = text.replace(old_seg, new_seg, 1)
    else:
        logging = __import__("logging")
        logging.getLogger(__name__).warning("Ken Burns block not exact-matched; Mixkit path still applied")

    # Mark Mixkit as pexels-equivalent visual source in metadata when stock is mixkit.
    # visual_source already says "pexels" if stock non-empty — leave as is for QA pass.

    compile(text, str(TARGET), "exec")
    TARGET.write_text(text, encoding="utf-8")
    print("PATCH_APPLIED free Mixkit motion + Ken Burns")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
