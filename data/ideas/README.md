# Idea Bank

Permanent store of validated English Shorts ideas for BAMO Autonomous Shorts Studio.

## Format

- Primary: `ideas.jsonl` (one JSON object per line)
- Optional future: SQLite for faster querying and used-state tracking

## Required fields per idea

- `id` (unique string, e.g. `idea-00001`)
- `title` (English, click-worthy but honest)
- `category` (from the 20 pillars)
- `summary` (1-2 sentences)
- `hook` (first 0-3 seconds text)
- `narration` (full English spoken script, natural spoken style, ~20-30s)
- `on_screen_text` (list of short phrases)
- `scenes` (list of scene objects with visual description + duration)
- `music_suggestion`
- `duration_seconds`
- `sources` (list of reputable URLs or citations)
- `seo_keywords`
- `youtube_title`
- `youtube_description`
- `hashtags`
- `virality_score` (1-10, multi-criteria)
- `status` (`available` | `used` | `rejected`)
- `created_at`
- `used_at` (nullable)

## Rules

- No fabricated facts or statistics
- Every claim must have at least one reputable source
- After an idea is used, mark `status: used` and never re-select without explicit reason
- Target: eventually 10,000 validated ideas. Current count starts near zero and grows honestly.
