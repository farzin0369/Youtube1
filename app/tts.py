"""Fixed narrator voice with a local Piper path; OpenAI is optional."""
from __future__ import annotations
from pathlib import Path
from app.local_ai import local_enabled, piper_synthesize
from app.utils import env, has_openai, load_channel_config

def _fixed_voice()->tuple[str,str]:
    try:
        ch=load_channel_config().get("channel") or {}
        return str(env("TTS_VOICE") or ch.get("tts_voice") or "local"), str(env("TTS_MODEL") or ch.get("tts_model") or "local")
    except Exception:
        return str(env("TTS_VOICE") or "local"), str(env("TTS_MODEL") or "local")

def synthesize(text:str,out_path:Path,kind:str="short")->dict:
    out_path=Path(out_path); out_path.parent.mkdir(parents=True,exist_ok=True)
    if local_enabled():
        return piper_synthesize(text,out_path)
    if has_openai():
        from openai import OpenAI
        voice,model=_fixed_voice()
        try:
            client=OpenAI(api_key=env("OPENAI_API_KEY"),base_url=env("OPENAI_API_BASE") or "https://api.openai.com/v1")
            resp=client.audio.speech.create(model=model,voice=voice,input=text[:4000],response_format="mp3")
            out_path=out_path.with_suffix(".mp3"); resp.stream_to_file(str(out_path))
            return {"path":str(out_path),"provider":"openai","voice":voice,"model":model,"narrator_locked":True,"ok":True}
        except Exception as e:
            raise RuntimeError(f"OpenAI TTS failed: {e}") from e
    raise RuntimeError("No local Piper engine or OpenAI TTS is configured.")
