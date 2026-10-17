# Manifesting Guru — original comedy short

This is an isolated experiment for an original English-language satire series about manifestation gurus, meditation clichés, affirmations, and get-rich-quick advice. It does not modify the main YouTube automation pipeline.

## Render inside GitHub

1. Open **Actions** in the repository.
2. Select **Render Manifesting Guru Comedy Short**.
3. Tap **Run workflow**.
4. When it finishes, open the run and download the `manifesting-guru-comedy-short` artifact.

The workflow renders a vertical 9:16 MP4 on GitHub Actions. It uses FFmpeg and a basic local English TTS voice, so it is a prototype, not final professional production.

## Separate laugh timing

Put the two laugh recordings in this folder, named:
- `assets/laugh1.mp3` — first reaction, after the main punchline
- `assets/laugh2.mp3` — second reaction, after a short pause

They are scheduled at separate moments; they are not blended into one laugh track. If the files are not present, the workflow still renders a video without those recorded laughs.

## Current short script

“I am rich. Money flows to me effortlessly. I am a money magnet. I attract abundance. … Hey! If you're not rich yet, at least get a fucking job! … So, yeah. The universe is working for me.”

This is a first pipeline smoke test. The next iteration should use better visuals, more natural English voice acting, and timing adjusted to the actual joke performance.
