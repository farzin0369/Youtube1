# Production architecture and rollout plan

## Current facts

- `app/pipeline.py` runs research, local-model script generation, TTS, rendering, quality checks, scheduled YouTube upload, and a first-pass comment reply step.
- `app/local_video_engine.py` uses CogVideoX only when `VIDEO_ENGINE=cogvideox`; that path requires a live CUDA GPU.
- `colab/ImamAli110_Cinematic_Production.ipynb` is the available Colab GPU entrypoint.
- `.github/workflows/colab-gpu-publishing.yml` requests a Colab T4 runtime through Colab CLI, then runs local Ollama + CogVideoX and asks YouTube to publish at **06:00 and 18:00 Asia/Tehran only**.
- The old CPU workflow is manual diagnostic only; the legacy Kaggle workflow is no longer scheduled.
- Colab CLI requires a previously authenticated OAuth token, and GPU allocation can still fail because Google controls account access and quotas.

## Scene contract and checkpoint behavior

`app/scene_plan.py` defines a versioned scene plan with `spoken_text`, `visual_prompt`, `on_screen_text`, duration hints, status, clip path, and error. Writes are atomic. A plan is reused only when its script fingerprint, title, and kind match; stale plans are preserved with a `.stale` suffix rather than silently reused.

The CogVideoX engine writes each scene clip into the run output folder and updates `scene_plan.json` after each scene. On retry with the same run ID and persistent output storage, completed clips can be reused. This does not make ephemeral `/content` durable by itself: mount Google Drive or another persistent storage before relying on cross-session recovery.

Set `PIPELINE_RUN_ID` to a stable safe identifier (letters, digits, underscore, hyphen; max 80 chars) when retrying the same job. Do not reuse the ID if the script/topic should be regenerated.

## Quality and publishing gates

1. Run CPU-safe tests and syntax checks before a pull request can be merged.
2. Run a GPU smoke test in Colab with `VIDEO_ENGINE=cogvideox`; verify `scene_plan.json`, all clip files, final MP4 duration, audio, SRT, and thumbnail.
3. Production workflow uses YouTube scheduled publishing (`publishAt`); a run is considered successful only when the upload API confirms the video ID. Public publication must still obey the channel's source and media QA gates.
4. Never put OAuth tokens, model keys, or personal credentials in source files or notebook output.
5. Sensitive comment categories stay pending; automated replies must not be treated as a substitute for moderation.
6. Do not deploy self-modifying code automatically. A repair can create a patch and run tests, but production deployment requires a passing test suite and a reviewed change.

## Operational limitations

- CogVideoX 2B generation on a free Colab GPU may be slow, memory-constrained, or unavailable. Do not promise 4K/8K native generation or true 24 fps motion from an 8 fps source. Current export targets 1080x1920 at 24 output fps; this can repeat frames and is not equivalent to native 24 fps capture.
- Scene captions are proportionally timed from each scene's narration length. This is an estimate, not forced alignment at phoneme/word level.
- A clone of the repository is not a persistent job queue. Cross-session resume requires persistent storage and a stable `PIPELINE_RUN_ID`.
- Public uploads and automated replies are side effects. The production schedule is explicitly enabled by the owner; uncertain comments stay pending, and the self-review agent may update only bounded editorial memory, never executable code or credentials.

## Current autonomous loop

1. Two daily GitHub schedule triggers request a Colab T4 runtime about six hours before each target publication slot (06:00 and 18:00 Tehran).
2. A local Ollama model generates scripts using a bounded cache of editorial lessons; no hosted LLM API is used.
3. CogVideoX runs only after a CUDA check and media QA blocks an invalid render from upload.
4. YouTube receives a private upload with a `publishAt` timestamp so it can release the video at the requested Tehran time.
5. After each run, a local model reviews the audit and may update only short editorial lessons and run summaries. It is not permitted to rewrite code or secrets.
6. GitHub Actions retains bounded memory and evidence artifacts. A failed Colab auth, unavailable GPU, failed test, invalid render, or failed upload must surface as a failed run rather than silently switching to CPU.

T4-safe defaults in production: `VIDEO_FRAMES=17`, `VIDEO_STEPS=8`, `VIDEO_CLIPS_SHORT=3`.

## Remaining external dependency

The workflow requires `COLAB_CLI_TOKEN_JSON` plus the existing YouTube OAuth secrets. The repository tools cannot read or create GitHub Actions secrets, and the first Colab OAuth authorization cannot be bypassed safely. After this one-time credential setup, scheduled execution is automated subject to Colab quota and availability.

## Channel operations and daily reporting

- `app/channel_ops.py` records successful reply IDs in `output/comment_reply_ledger.json`, checks for an existing channel reply, skips the channel's own comments, and preserves uncertain/spam-like cases in `output/pending_replies.json`.
- Suspected spam is queued for human review; this workflow does not automatically delete comments or report users because those actions can be irreversible and may misclassify legitimate comments.
- The daily `channel-health.yml` workflow runs syntax/unit tests, checks YouTube OAuth/API access, and uploads a health report plus the last-24-hour repository change list as an artifact.
- The health report is a diagnostic snapshot, not full YouTube Analytics ingestion. CTR and audience-retention analysis still needs Analytics API authorization and a separate data pipeline.

The daily health workflow now checks the most recent three uploads and considers up to ten top-level comments per public/unlisted video. It skips private videos, uses the configured text model, persists the reply ledger in GitHub Actions Cache, and uploads a pending-review index containing comment/video IDs and reasons only; raw comment text is not persisted in the public-repository artifact or cache. This is bounded sampling, not a complete scan of the entire channel history.

## Colab dependency repair

The Colab notebook keeps the runtime's CUDA-enabled PyTorch wheel. Before CogVideoX import, `scripts/repair_colab_cogvideox.py` checks whether TorchAO is missing the `FqnToConfig` symbol and removes only an incompatible TorchAO package directory when needed. It then verifies `CogVideoXPipeline` import. It does not blindly uninstall TorchAO or reinstall PyTorch/torchvision, and a failed import stops the GPU path rather than silently switching to CPU.
