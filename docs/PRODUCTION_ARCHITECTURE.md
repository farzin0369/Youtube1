# Production architecture and rollout plan

## Current facts

- `app/pipeline.py` runs research, script generation, TTS, rendering, private/unlisted/public YouTube upload, and a first-pass comment reply step.
- `app/local_video_engine.py` uses CogVideoX only when `VIDEO_ENGINE=cogvideox`; that path requires a live CUDA GPU.
- `colab/ImamAli110_Cinematic_Production.ipynb` is the available Colab GPU entrypoint.
- `.github/workflows/daily-youtube.yml` runs on a standard GitHub-hosted CPU runner. It is not a Colab GPU runner and should not be described as producing CogVideoX footage.
- Free Colab sessions are temporary and not guaranteed to be available at a particular time. GitHub Actions cannot guarantee that a free Colab session starts or remains connected.

## Scene contract and checkpoint behavior

`app/scene_plan.py` defines a versioned scene plan with `spoken_text`, `visual_prompt`, `on_screen_text`, duration hints, status, clip path, and error. Writes are atomic. A plan is reused only when its script fingerprint, title, and kind match; stale plans are preserved with a `.stale` suffix rather than silently reused.

The CogVideoX engine writes each scene clip into the run output folder and updates `scene_plan.json` after each scene. On retry with the same run ID and persistent output storage, completed clips can be reused. This does not make ephemeral `/content` durable by itself: mount Google Drive or another persistent storage before relying on cross-session recovery.

Set `PIPELINE_RUN_ID` to a stable safe identifier (letters, digits, underscore, hyphen; max 80 chars) when retrying the same job. Do not reuse the ID if the script/topic should be regenerated.

## Quality and publishing gates

1. Run CPU-safe tests and syntax checks before a pull request can be merged.
2. Run a GPU smoke test in Colab with `VIDEO_ENGINE=cogvideox`; verify `scene_plan.json`, all clip files, final MP4 duration, audio, SRT, and thumbnail.
3. Keep first uploads `private`. Review a real output in YouTube Studio before enabling public or scheduled release.
4. Never put OAuth tokens, model keys, or personal credentials in source files or notebook output.
5. Sensitive comment categories stay pending; automated replies must not be treated as a substitute for moderation.
6. Do not deploy self-modifying code automatically. A repair can create a patch and run tests, but production deployment requires a passing test suite and a reviewed change.

## Operational limitations

- CogVideoX 2B generation on a free Colab GPU may be slow, memory-constrained, or unavailable. Do not promise 4K/8K native generation or true 24 fps motion from an 8 fps source. Current export targets 1080x1920 at 24 output fps; this can repeat frames and is not equivalent to native 24 fps capture.
- Scene captions are proportionally timed from each scene's narration length. This is an estimate, not forced alignment at phoneme/word level.
- A clone of the repository is not a persistent job queue. Cross-session resume requires persistent storage and a stable `PIPELINE_RUN_ID`.
- Public uploads, deletion of comments, and automated replies are side effects. Keep them behind explicit config/policy gates and use private uploads while validating.

## Next phases

1. Validate this scene-plan/checkpoint change in CI.
2. Add Colab persistent-storage setup and confirm a same-run retry reuses generated clips.
3. Add media QA: ffprobe metadata, non-empty audio, subtitle bounds, thumbnail existence, scene completeness, and configurable duration thresholds.
4. Add a durable job ledger with lease/lock to prevent duplicate runs.
5. Add YouTube Analytics ingestion only after API scopes/permissions are verified; measure impressions CTR, retention and watch time with documented sample windows.
6. Add comment deduplication, reply audit trail, spam handling review queue, and a strict allowlist for safe auto-replies.
7. Add daily changelog/report artifacts and rollback-by-reverting a reviewed commit. Never let an untested agent edit and deploy production code without a gate.


## Channel operations and daily reporting

- `app/channel_ops.py` records successful reply IDs in `output/comment_reply_ledger.json`, checks for an existing channel reply, skips the channel's own comments, and preserves uncertain/spam-like cases in `output/pending_replies.json`.
- Suspected spam is queued for human review; this workflow does not automatically delete comments or report users because those actions can be irreversible and may misclassify legitimate comments.
- The daily `channel-health.yml` workflow runs syntax/unit tests, checks YouTube OAuth/API access, and uploads a health report plus the last-24-hour repository change list as an artifact.
- The health report is a diagnostic snapshot, not full YouTube Analytics ingestion. CTR and audience-retention analysis still needs Analytics API authorization and a separate data pipeline.


The daily health workflow now checks the most recent three uploads and considers up to ten top-level comments per public/unlisted video. It skips private videos, uses the configured text model, persists the reply ledger in GitHub Actions Cache, and uploads a pending-review index containing comment/video IDs and reasons only; raw comment text is not persisted in the public-repository artifact or cache. This is bounded sampling, not a complete scan of the entire channel history.


## Colab dependency repair

The Colab notebook keeps the runtime's CUDA-enabled PyTorch wheel. Before CogVideoX import, `scripts/repair_colab_cogvideox.py` checks whether TorchAO is missing the `FqnToConfig` symbol and removes only an incompatible TorchAO package directory when needed. It then verifies `CogVideoXPipeline` import. It does not blindly uninstall TorchAO or reinstall PyTorch/torchvision, and a failed import stops the GPU path rather than silently switching to CPU.
