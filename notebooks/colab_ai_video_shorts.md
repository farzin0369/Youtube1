# Colab: AI cinematic shorts (free GPU path)

GitHub Actions has **no GPU**. For Wan / CogVideoX / Hunyuan quality, run this on **Google Colab** (Runtime → GPU).

## Recommended order on free Colab T4 (~15GB)

1. **CogVideoX-2B** (`app/local_video_engine.py`) — already wired, T4-friendly with offload  
2. **HunyuanVideo 1.5** — good quality, ~14GB with offload  
3. **Wan 2.2 TI2V-5B** — best quality; use 480p + offload; may OOM on free T4  
4. **LTX-2** — needs more VRAM; use only if Colab gives a larger GPU  

## Minimal flow

```python
# 1) Clone your repo
!git clone -b feat/openclaw-autonomous-manager-v2 https://github.com/farzin0369/Youtube1.git
%cd Youtube1
!pip install -q -r requirements.txt  # plus GPU deps from requirements-local.txt if present

# 2) Build English cinematic prompts from Persian scenes
from app.visual_prompts import cinematic_prompts_for_scenes, negative_prompt
scenes = [
    "اگر نتیجه دیر آمد، آیا تلاشت بی معنی بوده؟",
    "گاهی عجله، آرامش را از کار خوب می گیرد.",
    "امروز کار درست را انجام بده.",
    "توکل، عجله نیست.",
]
prompts = cinematic_prompts_for_scenes(scenes, topic="توکل")
print(prompts)

# 3a) CogVideoX path (most reliable on free T4)
import os
os.environ["LOCAL_VIDEO_MODEL"] = "THUDM/CogVideoX-2b"
from app.local_video_engine import generate_local_clips  # if exported
# OR use the functions already in local_video_engine.py

# 3b) Wan path (needs more VRAM)
os.environ["AI_VIDEO_ENGINE"] = "wan"
from app.wan_video_engine import generate_wan_clips
clips = generate_wan_clips(prompts, out_dir=Path("/content/out"), width=480, height=832, num_frames=33)
```

## After clips are ready

Copy the MP4 scene files back into the pipeline `output/spiritual/<run_id>/scenes/`  
or set env and re-run the audio+caption+upload stages on Actions with prebuilt scenes.

## Daily free path (no Colab)

Leave `AI_VIDEO_ENGINE` empty. Pipeline uses **Mixkit** + visual_prompts keywords automatically.
