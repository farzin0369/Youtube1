# YouTube Agent Skill — project-local skills

This folder vendors the 11 MIT-licensed YouTube workflow skills from
[Jakeschincariol/youtube-agent-skill](https://github.com/Jakeschincariol/youtube-agent-skill).
Original license: `docs/licenses/youtube-agent-skill-MIT.txt`.

## Eleven skills

| Skill | Purpose |
|---|---|
| `yt-script` | Generate five hooks from 21 formulas, score them, then outline the spoken script and retention beats. |
| `yt-package` | Review title + thumbnail text together for clarity, truncation and duplication. |
| `yt-edit` | Turn an SRT transcript into a time-coded edit decision list. |
| `yt-comment` | Triage comments and draft replies; it does not post them by itself. |
| `yt-plan` | Plan a realistic week of anchor videos and Shorts. |
| `yt-viral` | Rank public competitor videos against each channel's own median; requires collected public data. |
| `yt-retention` | Interpret a YouTube Studio retention CSV. |
| `yt-shorts` | Find potential Shorts in a long-video transcript and propose new opening lines. |
| `yt-seo` | Draft descriptions, useful tags and search queries. |
| `yt-chapters` | Generate and validate chapters from an SRT transcript. |
| `yt-audit` | Audit a channel's packaging, opening, consistency and priority fix. |

## Included dependency-free Python helpers

- `yt-script/hookscore.py`
- `yt-package/title.py`
- `yt-edit/deadair.py`
- `yt-chapters/chapters.py`
- `yt-retention/retention.py`
- `yt-viral/swipe.py`

Example commands:

```bash
python .claude/skills/yt-script/hookscore.py --hook "Why do people give up right before a change?"
python .claude/skills/yt-package/title.py --title "Why you should not quit yet" --thumb "ONE MORE STEP"
python .claude/skills/yt-chapters/chapters.py transcript.srt
python .claude/skills/yt-edit/deadair.py transcript.srt
python .claude/skills/yt-retention/retention.py retention.csv
python .claude/skills/yt-viral/swipe.py collected.json --min 2.0
```

Set up the channel voice profile by copying `.claude/youtube/voice.md.example` to the runtime's expected voice-profile location and editing it. Do not put secrets in this file.

## Important integration boundary

These are agent instructions plus six local analysis tools. They are not an autonomous daemon and they do not upload videos. Claude Code can discover project-local skills under `.claude/skills/`, but the repository's scheduled GitHub Actions workflow does not run Claude Code or automatically execute these skills. The current production pipeline remains unchanged. Connecting selected capabilities to `app/spiritual_pipeline.py` or its workflow requires a separate tested implementation and should not bypass its quality gates or upload safeguards.

The hook score is heuristic, not a view/virality predictor. `yt-viral` works from supplied public-listing data; it does not access private analytics. The skills draft recommendations; the existing YouTube OAuth publishing pipeline is separate.
