# LTX-Video engine for ImamAli110

This branch uses the official open-source **LTX-Video** model from
[Lightricks/LTX-Video](https://github.com/Lightricks/LTX-Video) as the GPU scene renderer instead of treating Money Printer Turbo as the renderer itself.

## Where it runs

- Rendering runs on a Google Colab GPU session allocated by the existing `Colab CLI GPU cinematic render` workflow.
- GitHub Actions' standard `ubuntu-latest` runner is only the controller; it does not have a GPU.
- A free Colab GPU is quota/capacity dependent and cannot be promised as a permanent, guaranteed daily service.
- The model and its weights are downloaded at runtime from Hugging Face. They are not copied into Git because the checkpoints are large.

## Scene alignment

The renderer accepts a JSON scene plan via `--scene-plan` or `LTX_SCENE_PLAN`. It expects a top-level JSON list or an object with a `scenes` list. Each scene must provide a visual prompt in one of these fields:

- `visual_prompt`
- `video_prompt`
- `visual_query`
- `prompt`

Example:

```json
{
  "scenes": [
    {
      "narration": "مردی آخرین سکه‌اش را به نیازمندی داد.",
      "visual_prompt": "Cinematic close-up of a weary traveler offering his last coin to a person in need, warm dawn light, restrained emotion, slow camera push-in, photorealistic, no text, no watermark."
    }
  ]
}
```

If no scene plan is supplied, the script uses clearly labelled demo prompts so the workflow can smoke-test the model path. Demo output is explicitly marked `approved_for_publishing: false`. For a story production run, supply the real scene plan and use `--strict-scene-plan` so missing visual prompts fail closed instead of silently substituting unrelated visuals.

## Quality and safety

The script checks that every scene MP4 and the final MP4 exist and exceed minimum size, and verifies the final 720x1280 dimensions. It does **not** claim these checks prove semantic image quality, correct Persian narration, or publication readiness. It never uploads to YouTube. Keep the existing scene-level semantic review and final media quality gates before any upload.

## Manual run

On a Colab GPU session after the repository and dependencies are available:

```bash
python scripts/colab_render_minimal.py --scene-plan output/script_scene_plan.json --strict-scene-plan
```

Useful controls: `VIDEO_FRAMES` (default 49), `VIDEO_STEPS` (default 30), `VIDEO_H` (default 768), `VIDEO_W` (default 512), and `LTX_MODEL` (default `Lightricks/LTX-Video`).

This integration is a GPU-renderer replacement path, not a claim that the whole autonomous production-and-publishing system has already passed end-to-end testing.
