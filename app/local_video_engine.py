"""Local text-to-video film engine using CogVideoX text-to-video.
All generation happens on the self-hosted GPU; no hosted AI generation API.
"""
from __future__ import annotations
import subprocess
import tempfile
from pathlib import Path
from typing import Any
from app.utils import env, split_sentences

def _load():
    import torch
    from diffusers import CogVideoXPipeline
    if not torch.cuda.is_available():
        raise RuntimeError("Local text-to-video requires a CUDA GPU on the self-hosted runner.")
    model_id=env("LOCAL_VIDEO_MODEL") or "THUDM/CogVideoX-2b"
    pipe=CogVideoXPipeline.from_pretrained(model_id,torch_dtype=torch.float16)
    pipe.enable_model_cpu_offload()
    if hasattr(pipe,"vae") and hasattr(pipe.vae,"enable_tiling"): pipe.vae.enable_tiling()
    return pipe,torch,model_id

def generate_film(script:str,title:str,out_path:Path,kind:str="short",seed:int=110)->dict[str,Any]:
    from diffusers.utils import export_to_video
    pipe,torch,model_id=_load()
    count=int(env("VIDEO_CLIPS_SHORT") or "8") if kind=="short" else int(env("VIDEO_CLIPS_LONG") or "60")
    sentences=split_sentences(script) or [title]
    base=("cinematic spiritual documentary, photorealistic film, ancient Middle Eastern architecture and landscapes, "
          "warm golden volumetric light, deep shadows, slow deliberate camera movement, realistic materials, "
          "no sacred face, no prophet depiction, no text, no watermark, coherent visual language")
    with tempfile.TemporaryDirectory(prefix="imamali110_") as td:
        clips=[]
        for i in range(count):
            sentence=sentences[i % len(sentences)]
            prompt=f"{base}. Scene {i+1}: {sentence}. Title theme: {title}. "
            result=pipe(prompt=prompt,num_videos_per_prompt=1,
                num_inference_steps=int(env("VIDEO_STEPS") or "30"),
                num_frames=int(env("VIDEO_FRAMES") or "49"),
                guidance_scale=float(env("VIDEO_GUIDANCE") or "6"),
                generator=torch.Generator(device="cuda").manual_seed(seed+i))
            clip=Path(td)/f"clip_{i:03d}.mp4"
            export_to_video(result.frames[0],str(clip),fps=8)
            clips.append(clip)
        concat=Path(td)/"concat.txt"
        concat.write_text("\n".join(f"file '{p.as_posix()}'" for p in clips),encoding="utf-8")
        out_path=Path(out_path); out_path.parent.mkdir(parents=True,exist_ok=True)
        subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(concat),"-vf","scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920","-an","-c:v","libx264","-preset","medium","-crf","18",str(out_path)],check=True,capture_output=True)
    return {"video_path":str(out_path),"provider":"cogvideox-local","model":model_id,"clips":count,"ok":True}
