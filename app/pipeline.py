"""Safe-mode pipeline: research → script → TTS → render → public upload → audit."""
from __future__ import annotations

import argparse
import traceback
from pathlib import Path

from app.research import build_research_brief, pick_topic
from app.script_gen import generate_script
from app.tts import synthesize
from app.utils import (
    OUTPUT_DIR,
    ensure_dirs,
    has_openai,
    has_youtube_creds,
    load_channel_config,
    run_id as make_run_id,
    save_json,
    utc_now_iso,
)
from app.video_render import render_video
from app.youtube_client import upload_video


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--kind", choices=["short", "long"], required=True)
    p.add_argument("--publish-mode", choices=["private", "unlisted", "public"], default="private")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    ensure_dirs()
    cfg = load_channel_config()
    

    rid = make_run_id(args.kind)
    out_dir = OUTPUT_DIR / rid
    out_dir.mkdir(parents=True, exist_ok=True)
    audit: dict = {
        "run_id": rid,
        "started_at": utc_now_iso(),
        "kind": args.kind,
        "publish_mode": args.publish_mode,
        "channel": cfg.get("channel", {}),
        "steps": {},
    }

    print(f"=== {rid} | {args.kind} | {args.publish_mode} ===")
    print(f"OpenAI: {'yes' if has_openai() else 'NO'} | YouTube: {'yes' if has_youtube_creds() else 'NO'}")

    topic = pick_topic(args.kind, seed=rid)
    brief = build_research_brief(topic)
    audit["steps"]["research"] = {"topic": topic}
    save_json(out_dir / "topic.json", topic)
    print(f"[1] {topic['title_hint']}")

    script_data = generate_script(topic, args.kind, brief)
    audit["steps"]["script"] = {
        "title": script_data.get("title"),
        "generated_by": script_data.get("generated_by"),
    }
    save_json(out_dir / "script.json", script_data)
    (out_dir / "script.txt").write_text(script_data["script"], encoding="utf-8")
    print(f"[2] {script_data.get('generated_by')}: {script_data.get('title')}")

    audio_meta = synthesize(script_data["script"], out_dir / "narration", kind=args.kind)
    audit["steps"]["tts"] = audio_meta
    print(f"[3] TTS {audio_meta.get('provider')}")

    render_meta = render_video(
        script=script_data["script"],
        audio_path=Path(audio_meta["path"]),
        title=script_data["title"],
        kind=args.kind,
        run_id=rid,
    )
    audit["steps"]["render"] = render_meta
    print(f"[4] render ok={render_meta.get('ok')}")

    if args.dry_run:
        upload_meta: dict = {"skipped": True, "reason": "dry-run"}
    else:
        upload_meta = upload_video(
            video_path=Path(render_meta["video_path"]) if render_meta.get("video_path") else None,
            title=script_data["title"],
            description=script_data.get("description") or "",
            tags=list(script_data.get("tags") or []),
            privacy=args.publish_mode,
            thumbnail_path=Path(render_meta["thumbnail_path"]) if render_meta.get("thumbnail_path") else None,
        )
    audit["steps"]["upload"] = upload_meta
    print(f"[5] upload: {upload_meta}")

    audit["finished_at"] = utc_now_iso()
    audit["success"] = bool(render_meta.get("ok"))
    save_json(out_dir / "audit.json", audit)
    save_json(OUTPUT_DIR / "audit" / f"{rid}.json", audit)
    if not args.dry_run and not upload_meta.get("ok"):
        raise RuntimeError(f"YouTube upload failed: {upload_meta.get('error', 'unknown error')}")

    print(f"Done → {out_dir}")
    if upload_meta.get("url"):
        print(upload_meta["url"])


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        raise
