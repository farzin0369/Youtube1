#!/usr/bin/env python3
"""Topic-relevant animated A-roll for BAMO Shorts (NASA + Wikimedia).

Priority:
1) NASA video clips when available for the query
2) Multi-image Ken Burns with crossfades (continuous motion, not static slides)
"""
from __future__ import annotations

import json
import re
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path

UA = "BAMOShortsBot/1.0 (educational; contact @12bamo)"

TOPIC_QUERIES: dict[str, list[str]] = {
    "physics": ["black hole", "nebula", "galaxy", "particle accelerator"],
    "astrophysics": ["black hole", "galaxy", "nebula", "supernova"],
    "space": ["milky way", "saturn", "nebula", "earth from space"],
    "astronomy": ["milky way", "telescope stars", "planet", "aurora"],
    "math": ["geometry pattern", "fractal", "mathematics"],
    "geometry": ["architecture pattern", "symmetry", "geometry"],
    "biology": ["cells microscope", "dna", "nature forest"],
    "chemistry": ["laboratory science", "molecules", "chemical"],
    "psychology": ["brain neuroscience", "human mind", "focus"],
    "ai": ["circuit board", "data center", "artificial intelligence"],
    "history": ["ancient ruins", "library books", "historic architecture"],
    "philosophy": ["ocean horizon", "library books", "abstract light"],
    "metaphysics": ["cosmos stars", "ocean horizon", "nebula"],
    "nature": ["forest canopy", "ocean waves", "wildlife"],
    "success": ["mountain sunrise", "city skyline", "athlete"],
    "default": ["cosmos stars", "nebula", "earth from space", "aurora"],
}


def _queries_for(title: str, category: str, hook: str = "") -> list[str]:
    blob = f"{title} {category} {hook}".lower()
    out: list[str] = []
    for key, qs in TOPIC_QUERIES.items():
        if key != "default" and key in blob:
            out.extend(qs)
    words = re.findall(r"[a-zA-Z]{4,}", title)
    if words:
        out.append(" ".join(words[:4]))
    if not out:
        out = list(TOPIC_QUERIES["default"])
    seen, clean = set(), []
    for q in out:
        k = q.lower()
        if k not in seen:
            seen.add(k)
            clean.append(q)
    return clean[:5]


def _http_json(url: str, timeout: int = 30):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except Exception as exc:
        print(f"http_json fail: {exc}", flush=True)
        return None


def _download(url: str, dest: Path, timeout: int = 120) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp, dest.open("wb") as f:
            while True:
                chunk = resp.read(1024 * 256)
                if not chunk:
                    break
                f.write(chunk)
        ok = dest.exists() and dest.stat().st_size > 30_000
        if not ok and dest.exists():
            dest.unlink(missing_ok=True)
        return ok
    except Exception as exc:
        print(f"download fail: {exc}", flush=True)
        dest.unlink(missing_ok=True)
        return False


def nasa_media(query: str, *, images: int = 4, videos: int = 2) -> tuple[list[str], list[str]]:
    """Return (image_urls, video_urls) from NASA Images API."""
    q = urllib.parse.quote(query)
    img_urls: list[str] = []
    vid_urls: list[str] = []

    data = _http_json(
        f"https://images-api.nasa.gov/search?q={q}&media_type=image&page_size={images}"
    )
    if data:
        for it in (data.get("collection") or {}).get("items") or []:
            for link in it.get("links") or []:
                href = link.get("href") or ""
                if href and link.get("render") == "image":
                    img_urls.append(href)
                    break

    data_v = _http_json(
        f"https://images-api.nasa.gov/search?q={q}&media_type=video&page_size={videos}"
    )
    if data_v:
        for it in (data_v.get("collection") or {}).get("items") or []:
            # collection JSON often has href to asset manifest
            href_col = it.get("href") or ""
            if not href_col:
                continue
            manifest = _http_json(href_col)
            if not isinstance(manifest, list):
                continue
            # prefer mp4 mid size
            mp4s = [u for u in manifest if isinstance(u, str) and u.lower().endswith(".mp4")]
            # skip previews if possible
            prefer = [u for u in mp4s if "mobile" in u.lower() or "medium" in u.lower() or "large" in u.lower()]
            pick = (prefer or mp4s)
            if pick:
                # shortest-ish URL often mid quality
                pick.sort(key=len)
                vid_urls.append(pick[min(1, len(pick) - 1)] if len(pick) > 1 else pick[0])

    return img_urls[:images], vid_urls[:videos]


def wikimedia_image_urls(query: str, limit: int = 3) -> list[str]:
    q = urllib.parse.quote(query)
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
        for info in page.get("imageinfo") or []:
            mime = (info.get("mime") or "").lower()
            if not mime.startswith("image/"):
                continue
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
    max_images: int = 5,
    max_videos: int = 2,
) -> tuple[list[Path], list[Path]]:
    dest_dir.mkdir(parents=True, exist_ok=True)
    queries = _queries_for(title, category, hook)
    print(f"visual queries: {queries}", flush=True)
    images: list[Path] = []
    videos: list[Path] = []
    seen: set[str] = set()
    ii = vi = 0
    for q in queries:
        imgs, vids = nasa_media(q, images=3, videos=2)
        imgs += wikimedia_image_urls(q, limit=2)
        for url in vids:
            if url in seen:
                continue
            seen.add(url)
            dest = dest_dir / f"vid_{vi:02d}.mp4"
            if _download(url, dest):
                videos.append(dest)
                vi += 1
                print(f"video ok {dest.name}", flush=True)
            if len(videos) >= max_videos:
                break
        for url in imgs:
            if url in seen:
                continue
            seen.add(url)
            ext = ".png" if ".png" in url.lower() else ".jpg"
            dest = dest_dir / f"img_{ii:02d}{ext}"
            if _download(url, dest):
                images.append(dest)
                ii += 1
                print(f"image ok {dest.name}", flush=True)
            if len(images) >= max_images:
                break
        if len(images) >= max_images and len(videos) >= max_videos:
            break
    return images, videos


def _probe_dur(path: Path) -> float:
    try:
        out = subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=nw=1:nk=1",
                str(path),
            ],
            text=True,
        ).strip()
        return float(out)
    except Exception:
        return 5.0


def build_animated_aroll(
    images: list[Path],
    videos: list[Path],
    out_mp4: Path,
    *,
    duration: float,
    width: int = 1080,
    height: int = 1920,
) -> Path:
    """Build continuous motion A-roll: prefer real video, else animated stills with crossfade."""
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_mp4.parent / "_aroll_work"
    if tmp.exists():
        subprocess.run(["rm", "-rf", str(tmp)], check=False)
    tmp.mkdir(parents=True)

    segments: list[Path] = []

    # 1) Use real video clips stretched/cropped to vertical
    for i, vid in enumerate(videos[:2]):
        seg = tmp / f"vseg_{i}.mp4"
        # loop short clips to fill ~duration/2 each
        target = max(4.0, duration / max(1, min(2, len(videos))))
        cmd = [
            "ffmpeg",
            "-y",
            "-stream_loop",
            "-1",
            "-i",
            str(vid),
            "-t",
            f"{target:.2f}",
            "-vf",
            f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},fps=30",
            "-an",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-preset",
            "veryfast",
            str(seg),
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            segments.append(seg)
        except Exception as exc:
            print(f"video seg fail: {exc}", flush=True)

    # 2) Animated stills with stronger zoom + pan (Ken Burns)
    if images and (not segments or sum(_probe_dur(s) for s in segments) < duration * 0.7):
        n = max(1, len(images))
        per = max(3.5, duration / n)
        for i, img in enumerate(images):
            seg = tmp / f"iseg_{i}.mp4"
            frames = max(45, int(per * 30))
            # alternate zoom direction for motion variety
            if i % 2 == 0:
                zexpr = "min(zoom+0.0018,1.18)"
                xexpr = "iw/2-(iw/zoom/2)"
                yexpr = "ih/2-(ih/zoom/2)"
            else:
                zexpr = "if(eq(on,1),1.18,max(zoom-0.0018,1.0))"
                xexpr = "iw/2-(iw/zoom/2)+on*0.15"
                yexpr = "ih/2-(ih/zoom/2)"
            vf = (
                f"scale={width * 2}:{height * 2}:force_original_aspect_ratio=increase,"
                f"crop={width * 2}:{height * 2},"
                f"zoompan=z='{zexpr}':x='{xexpr}':y='{yexpr}':d={frames}:s={width}x{height}:fps=30,"
                f"eq=brightness=-0.04:saturation=1.08"
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
                "-preset",
                "veryfast",
                "-an",
                str(seg),
            ]
            try:
                subprocess.run(cmd, check=True, capture_output=True)
                segments.append(seg)
            except Exception as exc:
                print(f"image seg fail: {exc}", flush=True)

    if not segments:
        raise RuntimeError("no A-roll segments built")

    # 3) Concat with crossfade when multiple segments
    if len(segments) == 1:
        raw = segments[0]
    else:
        # xfade chain
        # limit to 4 segments for filter complexity
        segs = segments[:4]
        inputs = []
        for s in segs:
            inputs.extend(["-i", str(s)])
        durs = [_probe_dur(s) for s in segs]
        fade = 0.6
        filter_parts = []
        prev = "[0:v]"
        out_label = "[0:v]"
        acc = durs[0]
        for i in range(1, len(segs)):
            out_label = f"[xf{i}]"
            offset = max(0.1, acc - fade)
            filter_parts.append(
                f"{prev}[{i}:v]xfade=transition=fade:duration={fade}:offset={offset:.2f}{out_label}"
            )
            prev = out_label
            acc = acc + durs[i] - fade
        fc = ";".join(filter_parts)
        raw = tmp / "xfade.mp4"
        cmd = [
            "ffmpeg",
            "-y",
            *inputs,
            "-filter_complex",
            fc,
            "-map",
            out_label,
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-preset",
            "veryfast",
            "-an",
            str(raw),
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True)
        except Exception:
            # fallback concat demuxer
            lst = tmp / "list.txt"
            lst.write_text("".join(f"file '{p.resolve()}'\n" for p in segs), encoding="utf-8")
            subprocess.run(
                ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(raw)],
                check=True,
                capture_output=True,
            )

    # 4) Fit exact duration (trim or loop)
    raw_dur = _probe_dur(raw)
    if raw_dur < duration - 0.3:
        # loop pad
        cmd = [
            "ffmpeg",
            "-y",
            "-stream_loop",
            "-1",
            "-i",
            str(raw),
            "-t",
            f"{duration:.2f}",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-preset",
            "veryfast",
            "-an",
            str(out_mp4),
        ]
    else:
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(raw),
            "-t",
            f"{duration:.2f}",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-preset",
            "veryfast",
            "-an",
            str(out_mp4),
        ]
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"animated aroll -> {out_mp4} ({out_mp4.stat().st_size} bytes)", flush=True)
    return out_mp4
