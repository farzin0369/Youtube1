"""Production pipeline: local AI first, with optional legacy OpenAI mode."""
from __future__ import annotations
import argparse
import subprocess
import traceback
from pathlib import Path
from app.research import build_research_brief, pick_topic
from app.script_gen import generate_script
from app.tts import synthesize
from app.local_ai import local_enabled
from app.local_video_engine import generate_film
from app.utils import OUTPUT_DIR, ensure_dirs, has_openai, has_youtube_creds, load_channel_config, run_id as make_run_id, save_json, utc_now_iso
from app.video_render import render_video, make_thumbnail, write_srt
from app.youtube_client import upload_video
from app.channel_ops import reply_to_comments

def _local_render(script:str,title:str,audio:Path,kind:str,rid:str)->dict:
    out=OUTPUT_DIR/rid; raw=out/"ai_video.mp4"; final=out/"video.mp4"
    meta=generate_film(script,title,raw,kind=kind,seed=110)
    subprocess.run(["ffmpeg","-y","-i",str(raw),"-i",str(audio),"-shortest","-c:v","copy","-c:a","aac","-b:a","192k",str(final)],check=True,capture_output=True)
    seconds=6.125*(meta.get("clips") or 1)
    srt=write_srt(script,out/"captions.srt",seconds)
    thumb=make_thumbnail(title,out/"thumbnail.jpg",kind)
    return {"video_path":str(final),"thumbnail_path":str(thumb),"captions_path":str(srt),"duration":seconds,**meta,"ok":True}

def main()->None:
    p=argparse.ArgumentParser(); p.add_argument("--kind",choices=["short","long"],required=True); p.add_argument("--publish-mode",choices=["private","unlisted","public"],default="private"); p.add_argument("--dry-run",action="store_true"); args=p.parse_args()
    ensure_dirs(); cfg=load_channel_config()
    configured=str((cfg.get("publishing") or {}).get("mode") or "private").lower(); publish_mode=configured if configured in ("private","unlisted","public") else args.publish_mode
    rid=make_run_id(args.kind); out=OUTPUT_DIR/rid; out.mkdir(parents=True,exist_ok=True)
    audit={"run_id":rid,"started_at":utc_now_iso(),"kind":args.kind,"publish_mode":publish_mode,"channel":cfg.get("channel",{}),"steps":{}}
    print(f"=== {rid} | {args.kind} | {publish_mode} | engine={'local' if local_enabled() else 'legacy'} ===")
    topic=pick_topic(args.kind,seed=rid); brief=build_research_brief(topic); audit["steps"]["research"]={"topic":topic}; save_json(out/"topic.json",topic)
    script_data=generate_script(topic,args.kind,brief); audit["steps"]["script"]={"title":script_data.get("title"),"generated_by":script_data.get("generated_by")}; save_json(out/"script.json",script_data); (out/"script.txt").write_text(script_data["script"],encoding="utf-8")
    print(f"[1] script={script_data.get('generated_by')}")
    audio=synthesize(script_data["script"],out/"narration",kind=args.kind); audit["steps"]["tts"]=audio; print(f"[2] tts={audio.get('provider')}")
    if local_enabled():
        render_meta=_local_render(script_data["script"],script_data["title"],Path(audio["path"]),args.kind,rid)
    else:
        render_meta=render_video(script=script_data["script"],audio_path=Path(audio["path"]),title=script_data["title"],kind=args.kind,run_id=rid)
    audit["steps"]["render"]=render_meta; print(f"[3] render={render_meta.get('provider',render_meta.get('style'))}")
    if args.dry_run: upload_meta={"skipped":True,"reason":"dry-run"}
    else:
        upload_meta=upload_video(video_path=Path(render_meta["video_path"]) if render_meta.get("video_path") else None,title=script_data["title"],description=script_data.get("description") or "",tags=list(script_data.get("tags") or []),privacy=publish_mode,thumbnail_path=Path(render_meta["thumbnail_path"]) if render_meta.get("thumbnail_path") else None)
    audit["steps"]["upload"]=upload_meta
    if upload_meta.get("ok") and upload_meta.get("video_id"):
        try: audit["steps"]["comments"]=reply_to_comments(str(upload_meta["video_id"]))
        except Exception as e: audit["steps"]["comments"]={"ok":False,"error":str(e)}
    audit["finished_at"]=utc_now_iso(); audit["success"]=bool(render_meta.get("ok")); save_json(out/"audit.json",audit); save_json(OUTPUT_DIR/"audit"/f"{rid}.json",audit)
    if not args.dry_run and not upload_meta.get("ok"): raise RuntimeError(f"YouTube upload failed: {upload_meta.get('error','unknown error')}")
    print(f"Done -> {out}")
    if upload_meta.get("url"): print(upload_meta["url"])

if __name__=="__main__":
    try: main()
    except Exception: traceback.print_exc(); raise
