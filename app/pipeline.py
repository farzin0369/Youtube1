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
from app.agent_guard import enforce
from app.media_qa import validate_render_package

def _probe_duration(path:Path)->float:
    result=subprocess.run(
        ["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(path)],
        check=True,capture_output=True,text=True,
    )
    duration=float(result.stdout.strip())
    if duration <= 0:
        raise RuntimeError(f"Invalid media duration for {path}")
    return duration


def _local_render(scene_plan:list[dict],script:str,title:str,audio:Path,kind:str,rid:str)->dict:
    out=OUTPUT_DIR/rid; raw=out/"ai_video.mp4"; muxed=out/"video_muxed.mp4"; final=out/"video.mp4"
    meta=generate_film(script,title,raw,kind=kind,seed=110,scene_plan=scene_plan)
    audio_seconds=_probe_duration(audio)
    video_seconds=_probe_duration(raw)
    scene_plan_path=Path(meta["scene_plan_path"]) if meta.get("scene_plan_path") else None
    srt=write_srt(script,out/"captions.srt",audio_seconds,scene_plan_path=scene_plan_path)
    pad=max(0.0,audio_seconds-video_seconds)
    video_filter=f"tpad=stop_mode=clone:stop_duration={pad:.3f},fps=24,format=yuv420p"
    subprocess.run([
        "ffmpeg","-y","-i",str(raw),"-i",str(audio),"-vf",video_filter,"-t",f"{audio_seconds:.3f}",
        "-c:v","libx264","-preset","medium","-crf","18","-c:a","aac","-b:a","192k","-ar","48000",
        "-movflags","+faststart",str(muxed)
    ],check=True,capture_output=True)
    # Burn the scene-aligned Persian captions into the picture while keeping the SRT sidecar.
    escaped_srt=str(srt).replace("\\","/").replace(":","\\:").replace("'","\\'")
    subtitle_filter=f"subtitles='{escaped_srt}':force_style='FontName=Noto Sans Arabic,FontSize=42,Outline=2,Shadow=1,MarginV=140,Alignment=2'"
    subprocess.run([
        "ffmpeg","-y","-i",str(muxed),"-vf",subtitle_filter,"-c:v","libx264","-preset","medium","-crf","18",
        "-c:a","copy","-movflags","+faststart",str(final)
    ],check=True,capture_output=True)
    seconds=_probe_duration(final)
    thumb=make_thumbnail(title,out/"thumbnail.jpg",kind)
    return {**meta,"video_path":str(final),"thumbnail_path":str(thumb),"captions_path":str(srt),"duration":seconds,"audio_duration":audio_seconds,"source_video_duration":video_seconds,"on_screen_captions":True,"ok":True}

def main()->None:
    p=argparse.ArgumentParser(); p.add_argument("--kind",choices=["short","long"],required=True); p.add_argument("--publish-mode",choices=["private","unlisted","public"],default="private"); p.add_argument("--dry-run",action="store_true"); args=p.parse_args()
    ensure_dirs(); cfg=load_channel_config()
    configured=str((cfg.get("publishing") or {}).get("mode") or "private").lower(); publish_mode=configured if configured in ("private","unlisted","public") else args.publish_mode
    rid=make_run_id(args.kind); out=OUTPUT_DIR/rid; out.mkdir(parents=True,exist_ok=True)
    audit={"run_id":rid,"started_at":utc_now_iso(),"kind":args.kind,"publish_mode":publish_mode,"channel":cfg.get("channel",{}),"steps":{}}
    print(f"=== {rid} | {args.kind} | {publish_mode} | engine={'local' if local_enabled() else 'legacy'} ===")
    topic=pick_topic(args.kind,seed=rid); brief=build_research_brief(topic); audit["steps"]["research"]={"topic":topic}; save_json(out/"topic.json",topic)
    script_data=generate_script(topic,args.kind,brief); script_data=enforce(script_data,args.kind); audit["steps"]["script"]={"title":script_data.get("title"),"generated_by":script_data.get("generated_by"),"quality_gate":script_data.get("quality_gate")}; save_json(out/"script.json",script_data); (out/"script.txt").write_text(script_data["script"],encoding="utf-8")
    print(f"[1] script={script_data.get('generated_by')}")
    audio=synthesize(script_data["script"],out/"narration",kind=args.kind); audit["steps"]["tts"]=audio; print(f"[2] tts={audio.get('provider')}")
    if __import__("os").environ.get("VIDEO_ENGINE", "cpu").lower() == "cogvideox":
        render_meta=_local_render(scene_plan,script_data["script"],script_data["title"],Path(audio["path"]),args.kind,rid)
    else:
        render_meta=render_video(script=script_data["script"],audio_path=Path(audio["path"]),title=script_data["title"],kind=args.kind,run_id=rid,scene_plan_path=out/"script_scene_plan.json")
    audit["steps"]["render"]=render_meta; print(f"[3] render={render_meta.get('provider',render_meta.get('style'))}")
    media_qa=validate_render_package(render_meta,Path(audio["path"]) if audio.get("path") else None)
    audit["steps"]["media_quality"]=media_qa
    if not media_qa["ok"]:
        audit["finished_at"]=utc_now_iso(); audit["success"]=False
        save_json(out/"audit.json",audit); save_json(OUTPUT_DIR/"audit"/f"{rid}.json",audit)
        raise RuntimeError("Media quality gate failed; upload blocked: " + ", ".join(media_qa["errors"]))
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
