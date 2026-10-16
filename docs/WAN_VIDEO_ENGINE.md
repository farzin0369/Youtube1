# Wan2.1 AI video backend

This integration uses the official [Wan2.1 source](https://github.com/Wan-Video/Wan2.1) and the [Wan-AI/Wan2.1-T2V-1.3B-Diffusers model](https://huggingface.co/Wan-AI/Wan2.1-T2V-1.3B-Diffusers), whose model card lists the Apache-2.0 license. The 1.3B model is the lower-memory text-to-video option; the upstream project reports approximately 8.19 GB VRAM as its minimum.

## How the API is used

The existing Cloudflare Workers AI text endpoint generates the Persian script and each scene's visual prompt. **That text endpoint does not itself generate video.** Wan2.1 renders the actual frames locally on a CUDA GPU. This keeps the video model open-source/open-weight and avoids assuming a paid video-generation API.

## Enable

Set repository variable `AI_VIDEO_ENGINE=wan` only when a CUDA GPU runner/session is available. Optional variables:

- `WAN_MODEL_ID`: defaults to `Wan-AI/Wan2.1-T2V-1.3B-Diffusers`
- `WAN_INFERENCE_STEPS`: defaults to `20` (valid 1–60)

The integration generates four scene-matched portrait clips at 480×832, 81 frames, 16 FPS, then passes them into the existing FFmpeg workflow for timing, Persian captions, narration/music mixing, thumbnail, and QA. Model weights download from Hugging Face at first run and need sufficient disk space and network access.

**Runtime constraint:** standard GitHub-hosted Actions runners do not include a CUDA GPU. If `AI_VIDEO_ENGINE=wan` is enabled on such a runner, the workflow stops with an explicit GPU error instead of silently substituting stock footage. A GPU-backed runner (or a connected Colab session) is required to prove an actual render. The production workflow remains on its existing stock-footage path unless this variable is explicitly set.
