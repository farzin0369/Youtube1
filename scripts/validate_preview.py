#!/usr/bin/env python3
"""Hard technical quality gate for the no-key preview; never publishes."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "no_key_preview"
VIDEO = OUT / "imamali110_no_key_preview.mp4"
AUDIO = OUT / "narration_fa.mp3"
SCRIPT = OUT / "script_fa.txt"
REPORT = OUT / "technical_qc.json"

def probe(path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "format=duration,size:stream=codec_type,codec_name,width,height,sample_rate",
         "-of", "json", str(path)],
        capture_output=True, text=True, check=True, timeout=30,
    )
    return json.loads(result.stdout)

def main():
    checks = []
    errors = []
    for path, label in [(VIDEO, "video"), (AUDIO, "audio"), (SCRIPT, "script")]:
        ok = path.is_file() and path.stat().st_size > 0
        checks.append({"check": f"{label}_exists_and_nonempty", "passed": ok})
        if not ok:
            errors.append(f"{label} missing or empty: {path.name}")
    if errors:
        result = {"status": "FAIL", "passed": False, "errors": errors, "checks": checks}
        OUT.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1

    data = probe(VIDEO)
    streams = data.get("streams", [])
    v = next((s for s in streams if s.get("codec_type") == "video"), {})
    a = next((s for s in streams if s.get("codec_type") == "audio"), {})
    duration = float(data.get("format", {}).get("duration", 0))
    size = int(data.get("format", {}).get("size", 0))
    script_text = SCRIPT.read_text(encoding="utf-8").strip()
    tests = [
        ("video_codec_h264", v.get("codec_name") == "h264"),
        ("vertical_resolution_720x1280", v.get("width") == 720 and v.get("height") == 1280),
        ("audio_stream_present", bool(a)),
        ("audio_codec_aac", a.get("codec_name") == "aac"),
        ("duration_15_to_90_seconds", 15 <= duration <= 90),
        ("file_size_over_100kb", size > 100_000),
        ("persian_script_has_content", len(script_text) >= 100 and any("\u0600" <= ch <= "\u06ff" for ch in script_text)),
        ("manifest_explicitly_unpublished", json.loads((OUT / "preview_manifest.json").read_text(encoding="utf-8")).get("published") is False),
    ]
    for name, ok in tests:
        checks.append({"check": name, "passed": bool(ok)})
        if not ok:
            errors.append(name)
    result = {"status": "PASS_TECHNICAL_ONLY" if not errors else "FAIL", "passed": not errors,
              "duration_seconds": round(duration, 2), "size_bytes": size,
              "resolution": f'{v.get("width")}x{v.get("height")}', "errors": errors,
              "checks": checks,
              "warning": "Technical validation does not verify story quality, semantic image relevance, Persian pronunciation, or human-perceived aesthetics."}
    REPORT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1

if __name__ == "__main__":
    sys.exit(main())
