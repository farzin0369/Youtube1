# Wan2.1 AI video backend

This integration uses the official [Wan2.1 source](https://github.com/Wan-Video/Wan2.1). The default `cinematic` profile uses the Apache-2.0 [Wan-AI/Wan2.1-T2V-14B-Diffusers model](https://huggingface.co/Wan-AI/Wan2.1-T2V-14B-Diffusers) for higher visual quality. `low_memory` explicitly selects the Apache-2.0 1.3B model and the upstream approximately 8.19 GB VRAM path.

## How the API is used

The existing Cloudflare Workers AI text endpoint generates the Persian script and each scene's visual prompt. **That text endpoint does not itself generate video.** Wan2.1 renders the actual frames locally on a CUDA GPU. This keeps the video model open-source/open-weight and avoids assuming a paid video-generation API.

## Enable

Set repository variable `AI_VIDEO_ENGINE=wan` only when a CUDA GPU runner/session is available. Optional variables:

- `WAN_QUALITY_PROFILE`: defaults to `cinematic`; use `low_memory` for the 1.3B model.
- `WAN_MODEL_ID`: overrides the profile's default model.
- `WAN_INFERENCE_STEPS`: defaults to `32` for `cinematic` and `20` for `low_memory` (valid 1–60).
- `WAN_SEED`: defaults to `110`; each scene uses a deterministic offset for repeatable style and camera behavior.
- `WAN_STYLE_PROFILE`: defaults to `reference_dark_fantasy`, matching the supplied gothic hall, blue-black shadows and golden light. Set `default` for the generic cinematic profile.

The integration generates four scene-matched portrait clips at 480×832, 81 frames, 16 FPS, with shot-specific prompts: macro floor/boots, rear tracking shot, frontal light-tree reveal, and a contemplative close-up. A deterministic seed is used per scene. The clips then pass into the existing FFmpeg workflow for timing, Persian captions, narration/music mixing, thumbnail, and QA. Model weights download from Hugging Face at first run and need sufficient disk space and network access.

**Runtime constraint:** standard GitHub-hosted Actions runners do not include a CUDA GPU. The `cinematic` profile refuses to start below 24 GiB of free VRAM; the `low_memory` profile refuses to start below the 1.3B threshold. If `AI_VIDEO_ENGINE=wan` is enabled without a suitable GPU, the workflow stops with an explicit error instead of silently substituting stock footage. A GPU-backed runner (or a connected Colab session) is required to prove an actual render. The production workflow remains on its existing stock-footage path unless this variable is explicitly set.
