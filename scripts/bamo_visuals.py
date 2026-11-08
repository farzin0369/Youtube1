#!/usr/bin/env python3
"""Fetch topic-relevant free visuals (NASA Images + Wikimedia) for BAMO Shorts.

No paid API keys. Used as A-roll under kinetic captions + TTS.
"""
from __future__ import annotations

import json
import re
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path

UA = "BAMOShortsBot/1.0 (educational; contact @12bamo)"

# category / title keywords → search queries (English)
TOPIC_QUERIES: dict[str, list[str]] = {
    "physics": ["black hole", "nebula space", "particle physics", "galaxy"],
    "astrophysics": ["black hole accretion", "galaxy", "nebula", "cosmos"],
    "space": ["milky way", "saturn", "nebula", "astronaut space"],
    "astronomy": ["telescope stars", "milky way night", "planet", "aurora"],
    "math": ["geometry pattern", "fractal", "mathematics chalkboard"],
    "geometry": ["sacred geometry", "architecture pattern", "symmetry"],
    "biology": ["cells microscope", "dna double helix", "nature forest"],
    "chemistry": ["laboratory science", "molecules", "chemical reaction"],
    "psychology": ["brain neuroscience", "human mind abstract", "focus"],
    "ai": ["artificial intelligence network", "circuit board lights", "data center"],
    "history": ["ancient ruins", "library books", "historic architecture"],
    "nature": ["forest canopy", "ocean waves", "wildlife"],
    "success": ["mountain sunrise", "athlete training", "city skyline dawn"],
    "default": ["cosmos stars", "abstract light", "science laboratory"],
}


def _queries_for(title: str, category: str, hook: str = "") -> list[str]:
    blob = f"{title} {category} {hook}".lower()
    out: list[str] = []
    for key, qs in TOPIC_QUERIES.items():
        if key != "default" and key in blob:
            out.extend(qs)
    # title words as queries
    words = re.findall(r"[a-zA-Z]{4,}", title)
    if words:
        out.append(" ".join(words[:4]))
    if not out:
        out = list(TOPIC_QUERIES["default"])
    # dedupe preserve order
    seen = set()
    clean = []
    for q in out:
        k = q.lower()
        if k not in seen:
            seen.add(k)
            clean.append(q)
    return clean[:4]


def _http_json(url: str, timeout: int = 30) -> dict | list | None:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except Exception as exc:
        print(f"http_json fail {url}: {exc}", flush=True)
        return None


def _download(url: str, dest: Path, timeout: int = 90) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp, dest.open("wb") as f:
            while True:
                chunk = resp.read(1024 * 256)
                if not chunk:
                    break
                f.write(chunk)
        return dest.exists() and dest.stat().st_size > 20_000
    except Exception as exc:
        print(f"download fail {url}: {exc}", flush=True)
        if dest.exists():
            dest.unlink(missing_ok=True)
        return False


def nasa_image_urls(query: str, limit: int = 4) -> list[str]:
    q = urllib.parse.quote(query)
    data = _http_json(f"https://images-api.nasa.gov/search?q={q}&media_type=image&page_size={limit}")
    if not data:
        return []
    items = (data.get("collection") or {}).get("items") or []
    urls: list[str] = []
    for it in items:
        links = it.get("links") or []
        for link in links:
            href = link.get("href") or ""
            if href and link.get("render") == "image":
                # prefer larger jpg
                if href.endswith(".jpg") or href.endswith(".png") or "~orig" in href or "~large" in href:
                    urls.append(href)
                    break
                if href and not urls:
                    urls.append(href)
        if len(urls) >= limit:
            break
    return urls[:limit]


def wikimedia_image_urls(query: str, limit: int = 3) -> list[str]:
    q = urllib.parse.quote(query)
    # generator search for files
    url = (
        "https://commons.wikimedia.org/w/api.php?action=query&format=json"
        f"&generator=search&gsrsearch={q}&gsrnamespace=6&gsrlimit={limit}"
        "&prop=imageinfo&iiprop=url|mime&iiurlwidth=1280"
    )
    data = _http_json(url)
    if not data:
        return []
    pages = (data.get("query") or {}).get("pages") or {}
    urls: list[str] = []
    for page in pages.values():
        infos = page.get("imageinfo") or []
        for info in infos:
            mime = (info.get("mime") or "").lower()
            if not mime.startswith("image/"):
                continue
            # thumburl is resized; url is original
            href = info.get("thumburl") or info.get("url")
            if href:
                urls.append(href)
    return urls[:limit]


def collect_visuals(
    title: str,
    category: str,
    dest_dir: Path,
    *,
    hook: str = "",
    max_assets: int = 4,
) -> list[Path]:
    """Download stills relevant to the idea. Returns local file paths."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    queries = _queries_for(title, category, hook)
    print(f"visual queries: {queries}", flush=True)
    paths: list[Path] = []
    seen_urls: set[str] = set()
    idx = 0
    for q in queries:
        for url in nasa_image_urls(q, limit=2) + wikimedia_image_urls(q, limit=2):
            if url in seen_urls:
                continue
            seen_urls.add(url)
            ext = ".jpg"
            if ".png" in url.lower():
                ext = ".png"
            dest = dest_dir / f"vis_{idx:02d}{ext}"
            if _download(url, dest):
                paths.append(dest)
                idx += 1
                print(f"visual ok {dest.name} <- {url[:80]}", flush=True)
            if len(paths) >= max_assets:
                return paths
    return paths


def images_to_kenburns_clip(
    images: list[Path],
    out_mp4: Path,
    *,
    duration: float,
    width: int = 1080,
    height: int = 1920,
) -> Path:
    """Build a vertical motion clip from stills (slow zoom/pan via zoompan)."""
    if not images:
        raise ValueError("no images for ken burns")
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    per = max(3.0, duration / len(images))
    # scale each image to cover vertical frame, mild zoom
    parts: list[Path] = []
    tmp = out_mp4.parent / "_kb_parts"
    tmp.mkdir(parents=True, exist_ok=True)
    for i, img in enumerate(images):
        part = tmp / f"part_{i:02d}.mp4"
        frames = max(30, int(per * 30))
        # zoompan: slow zoom in
        vf = (
            f"scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},"
            f"zoompan=z='min(zoom+0.0015,1.15)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"d={frames}:s={width}x{height}:fps=30,"
            f"eq=brightness=-0.05:saturation=1.05"
        )
        cmd = [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-i",
            str(img),
            "-vf",
            vf,
            "-t",
            f"{per:.2f}",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-an",
            str(part),
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        parts.append(part)
    # concat
    lst = tmp / "list.txt"
    lst.write_text("".join(f"file '{p.resolve()}'\n" for p in parts), encoding="utf-8")
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(lst),
            "-c",
            "copy",
            str(out_mp4),
        ],
        check=True,
        capture_output=True,
    )
    # trim/pad to exact duration
    trimmed = out_mp4.with_name(out_mp4.stem + "_t.mp4")
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(out_mp4),
            "-t",
            f"{duration:.2f}",
            "-c",
            "copy",
            str(trimmed),
        ],
        check=True,
        capture_output=True,
    )
    trimmed.replace(out_mp4)
    print(f"kenburns -> {out_mp4}", flush=True)
    return out_mp4
