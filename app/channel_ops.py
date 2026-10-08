"""YouTube operations with local AI comment moderation/replies."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from app.local_ai import local_enabled, ollama_generate
from app.utils import env, has_openai, load_content_policy, load_channel_config, utc_now_iso

def _youtube():
    from googleapiclient.discovery import build
    from app.youtube_client import _build_credentials
    return build("youtube","v3",credentials=_build_credentials())

def reply_to_comments(video_id:str,max_comments:int=10)->dict[str,Any]:
    if not video_id: return {"ok":False,"error":"Missing video id"}
    if not local_enabled() and not has_openai(): return {"ok":False,"error":"No local AI or OpenAI configured"}
    youtube=_youtube(); policy=load_content_policy(); pending=[]; replied=0
    items=youtube.commentThreads().list(part="snippet",videoId=video_id,maxResults=max_comments,textFormat="plainText").execute().get("items",[])
    for item in items:
        top=item.get("snippet",{}).get("topLevelComment",{}).get("snippet",{}); cid=item.get("id"); text=str(top.get("textDisplay","")).strip()
        if not cid or not text: continue
        prompt=("پاسخ کوتاه و محترمانه فارسی برای کامنت یوتیوب بنویس. اگر تهدید، خودآسیبی، محتوای جنسی، آزار هدفمند، نفرت‌پراکنی، سیاسی یا نامرتبط است فقط PENDING بنویس. "
                f"سیاست: {json.dumps(policy,ensure_ascii=False)}\nکامنت: {text}")
        try:
            if local_enabled():
                reply=ollama_generate(prompt,"تو مدیر محترمانه کانال ImamAli110 هستی.",env("LOCAL_LLM_MODEL") or "qwen2.5:7b")
            else:
                from openai import OpenAI
                resp=OpenAI(api_key=env("OPENAI_API_KEY"),base_url=env("OPENAI_API_BASE") or "https://api.openai.com/v1").responses.create(model=env("OPENAI_MODEL") or "gpt-4o-mini",input=prompt)
                reply=(resp.output_text or "").strip()
        except Exception as e:
            pending.append({"comment_id":cid,"comment":text,"reason":str(e)}); continue
        if not reply or reply.upper()=="PENDING":
            pending.append({"comment_id":cid,"comment":text,"reason":"policy review"}); continue
        youtube.comments().insert(part="snippet",body={"snippet":{"parentId":cid,"textOriginal":reply[:1000]}}).execute(); replied+=1
    out=Path("output")/"pending_replies.json"; out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps({"created_at":utc_now_iso(),"pending":pending},ensure_ascii=False,indent=2),encoding="utf-8")
    return {"ok":True,"replied":replied,"pending":len(pending)}

def channel_health()->dict[str,Any]:
    cfg=load_channel_config(); checks={"local_ai":local_enabled(),"youtube":False,"channel":cfg.get("channel",{}).get("url")}
    try:
        y=_youtube(); y.channels().list(part="snippet,statistics",mine=True).execute(); checks["youtube"]=True
    except Exception as e: checks["youtube_error"]=str(e)
    return checks
