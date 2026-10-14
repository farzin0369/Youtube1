# LTX-Video AI generation backend

The optional `AI_VIDEO_ENGINE=ltx` backend uses the open-source LTX-Video Diffusers pipeline to render one original clip per authored Shorts scene. Official source/model: https://github.com/Lightricks/LTX-Video and https://huggingface.co/Lightricks/LTX-Video.

## Cloud API and video model responsibilities

The configured cloud LLM API (including Cloudflare Workers AI) generates the Persian script and scene prompts. **The existing Llama text endpoint does not generate video.** LTX-Video generates the actual video frames on a CUDA GPU; this is a separate model/runtime, not a hidden feature of the text API. No additional paid video API is assumed.

## Enable it

Set repository variable `AI_VIDEO_ENGINE=ltx` only for a GPU-backed runner/session. Optional variables:

- `LTX_MODEL_ID`: defaults to `Lightricks/LTX-Video`
- `LTX_INFERENCE_STEPS`: defaults to `20` (valid 1–60)

Install the GPU-compatible PyTorch build and `requirements-local.txt`, then run the normal pipeline. The backend generates four scene clips at 512×896 and 49 frames, then the existing FFmpeg pipeline crops, times, captions, mixes audio, and performs media QA. A CUDA GPU is required; GitHub-hosted standard runners are CPU-only and will fail clearly instead of silently falling back to stock footage. Model weights are downloaded from Hugging Face on first use and require compliance with the model's license and available disk/network bandwidth.

This does not claim that a production YouTube upload has succeeded. Keep `AI_VIDEO_ENGINE` unset until a GPU-backed test produces a valid MP4 and the complete pipeline passes QA.
