"""Cloud-free smoke test for TTS, CPU render, captions, thumbnail, and media QA; never uploads."""
from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.media_qa import validate_render_package
from app.tts import synthesize
from app.utils import OUTPUT_DIR, ensure_dirs, save_json
from app.video_render import render_video

def main() -> None:
    ensure_dirs()
    run_id = "tt_khabar_smoke_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out = OUTPUT_DIR / run_id
    out.mkdir(parents=True, exist_ok=True)
    narration = (
        "سلام، به آزمون فنی کانال تی‌تی خبر خوش آمدید. "
        "این فایل فقط برای بررسی صدا، زیرنویس و رندر ساخته شده است و خبر واقعی نیست. "
        "در انتشار واقعی، هر خبر با منبع و پیوند قابل بررسی ارائه خواهد شد."
    )
    audio = synthesize(narration, out / "narration", kind="short")
    render = render_video(
        script=narration,
        audio_path=Path(audio["path"]),
        title="TT خبر | آزمون فنی رندر",
        kind="short",
        run_id=run_id,
        scene_plan_path=out / "scene_plan.json",
    )
    qa = validate_render_package(render, Path(audio["path"]))
    report = {
        "brand": "TT خبر",
        "run_id": run_id,
        "success": bool(qa.get("ok")),
        "tts_provider": audio.get("provider"),
        "render": render,
        "quality": qa,
        "uploaded": False,
    }
    save_json(out / "smoke_report.json", report)
    print("TT_KHABAR_SMOKE_OK" if qa.get("ok") else "TT_KHABAR_SMOKE_FAILED")
    if not qa.get("ok"):
        raise RuntimeError("Smoke render quality gate failed: " + ", ".join(qa.get("errors") or []))

if __name__ == "__main__":
    main()
