# BAMO Autonomous Shorts Studio

**English YouTube Shorts production factory** powered by OpenMontage.

This branch (`feat/bamo-openmontage-autonomous-studio`) is the experimental workspace for a fully automated daily English Shorts pipeline.  
The `main` branch remains untouched and still contains the previous Persian spiritual pipeline. That brand and content direction have been **completely retired** on this experimental branch.

## Mission

Build a reliable, high-quality system that every day:

1. Selects the best English idea from a large validated idea bank
2. Writes a tight 20–30 second script with a strong hook
3. Generates or retrieves motion visuals matched to the topic
4. Produces natural English narration
5. Composes a vertical 9:16 video with accurate subtitles
6. Runs technical + content quality gates
7. Publishes to YouTube Shorts (only after full approval)
8. Learns from performance data

OpenMontage (`vendor/openmontage`) is the primary production engine.  
Legacy BAMO renderers are kept only until the OpenMontage path is proven and validated.

## Current Status (honest)

| Component                        | Status                          |
|----------------------------------|---------------------------------|
| OpenMontage submodule            | Pinned                          |
| English channel config           | Updating                        |
| 10,000 validated ideas           | 0 (scaffolding started)         |
| Content Intelligence             | Skeleton                        |
| Real English 9:16 sample render  | Not yet produced                |
| Natural English TTS verified     | Not yet tested                  |
| YouTube publish (public)         | Disabled / gated                |
| Daily autonomous schedule        | Not active                      |
| Legacy engines removed           | No (kept for safety)            |

## Key Directories

- `vendor/openmontage` — upstream OpenMontage (git submodule)
- `app/` — BAMO orchestration, content intelligence, adapters
- `config/` — channel, content policy, models
- `data/ideas/` — idea bank (JSONL / SQLite) — to be created
- `docs/` — architecture and migration reports
- `colab/` — Google Colab notebooks for heavy rendering

## Safety Rules

- Never publish without passing quality gates
- Never claim a video is ready without actual rendered MP4 + audio check
- Never touch `main` from this branch without explicit approval
- Prefer free / local / CPU tools first (Piper, FFmpeg, open stock)
- No paid APIs without explicit budget approval

## Next Concrete Steps

1. Finalize English `channel.yaml` and content pillars
2. Scaffold idea bank schema + first batch of high-quality ideas
3. Implement Content Intelligence selector
4. Produce and inspect one real English 20–30s Short
5. Wire OpenMontage pipeline for vertical Shorts
6. Add resumable daily runner + checkpointing

---

**Brand note:** Previous ImamAli110 / Persian spiritual identity is fully retired on this branch.  
Working internal name: **BAMO Autonomous Shorts Studio**. Final public channel brand will be decided later.
