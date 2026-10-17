#!/usr/bin/env python3
"""Render a vertical, original 'manifesting guru' comedy short with FFmpeg.

Optional laugh assets:
  comedy/manifesting-guru/assets/laugh1.mp3
  comedy/manifesting-guru/assets/laugh2.mp3

When absent, the render still completes with a short silence at the reaction beats;
it does not fabricate or merge laughter recordings.
"""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
OUT = Path("output/manifesting_guru_comedy_short.mp4")
ASSETS = ROOT / "assets"
OUT.parent.mkdir(parents=True, exist_ok=True)

def run(args):
    subprocess.run(args, check=True)

def have(cmd):
    return subprocess.run(["bash", "-lc", f"command -v {cmd} >/dev/null 2>&1"]).returncode == 0

def main():
    if not have("ffmpeg"):
        sys.exit("ffmpeg is required")
    if not have("espeak-ng") and not have("espeak"):
        sys.exit("espeak-ng or espeak is required")

    # Original script beats: calm affirmations -> absurd reality check -> reactions.
    voice_text = (
        "I am rich. Money flows to me effortlessly. I am a money magnet. "
        "I attract abundance. ... "
        "Hey! If you're not rich yet, at least get a fucking job! ... "
        "So, yeah. The universe is working for me."
    )
    voice = Path("/tmp/guru_voice.wav")
    speaker = "espeak-ng" if have("espeak-ng") else "espeak"
    run([speaker, "-v", "en-us+m3", "-s", "145", "-p", "38", "-w", str(voice), voice_text])

    # Create a polished graphic video with timed scene changes and legible captions.
    # FFmpeg drawtext is used instead of external image assets so the workflow is reproducible.
    font = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    if not Path(font).exists():
        font = "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"
    scenes = [
        (2.5, "I AM RICH", "calm"),
        (2.4, "MONEY FLOWS TO ME", "calm"),
        (2.3, "I AM A MONEY MAGNET", "calm"),
        (2.6, "HEY! GET A FUCKING JOB!", "punch"),
        (2.2, "[LAUGH REACTION]", "reaction1"),
        (2.6, "THE UNIVERSE IS WORKING FOR ME", "deadpan"),
        (1.8, "MANIFEST BETTER CHOICES", "end"),
    ]
    clips = []
    for i, (dur, caption, style) in enumerate(scenes):
        clip = Path(f"/tmp/guru_scene_{i}.mp4")
        if style == "calm":
            bg = "0x18251F"
            fg = "white"
        elif style == "punch":
            bg = "0x3A1717"
            fg = "0xFFE35B"
        elif style == "reaction1":
            bg = "0x2C2118"
            fg = "white"
        elif style == "deadpan":
            bg = "0x18202D"
            fg = "white"
        else:
            bg = "black"
            fg = "0xFFE35B"
        safe_caption = caption.replace("'", r"\\'").replace(":", r"\\:")
        vf = (
            f"drawtext=fontfile='{font}':text='{safe_caption}':"
            "fontcolor=" + fg + ":fontsize=42:borderw=3:bordercolor=black:"
            "x=(w-text_w)/2:y=(h-text_h)/2:line_spacing=12,"
            "drawtext=fontfile='" + font + "':text='MANIFESTING GURU':"
            "fontcolor=white@0.7:fontsize=22:x=(w-text_w)/2:y=110"
        )
        run([
            "ffmpeg", "-y", "-f", "lavfi", "-i",
            f"color=c={bg}:s=720x1280:r=30:d={dur}",
            "-vf", vf, "-an", "-c:v", "libx264", "-preset", "ultrafast",
            "-pix_fmt", "yuv420p", str(clip)
        ])
        clips.append(clip)

    concat = Path("/tmp/guru_concat.txt")
    concat.write_text("".join(f"file '{p}'\n" for p in clips))
    silent = Path("/tmp/guru_silent.mp4")
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat),
         "-c", "copy", str(silent)])

    # Keep laugh placements separate. User can add the two owned clips under assets/.
    laugh1 = ASSETS / "laugh1.mp3"
    laugh2 = ASSETS / "laugh2.mp3"
    inputs = ["-i", str(silent), "-i", str(voice)]
    filters = ["[1:a]volume=1.0[voice]"]
    labels = ["[voice]"]
    if laugh1.exists():
        inputs += ["-i", str(laugh1)]
        filters.append(f"[{len(inputs)//2}:a]atrim=0:2.2,volume=0.8,afade=t=in:st=0:d=0.08,afade=t=out:st=1.7:d=0.45,adelay=10100|10100[laughone]")
        labels.append("[laughone]")
    if laugh2.exists():
        inputs += ["-i", str(laugh2)]
        idx = len(inputs)//2
        filters.append(f"[{idx}:a]atrim=0:2.5,volume=0.72,afade=t=in:st=0:d=0.08,afade=t=out:st=2.0:d=0.45,adelay=12500|12500[laughtwo]")
        labels.append("[laughtwo]")
    filters.append("".join(labels) + f"amix=inputs={len(labels)}:duration=longest:dropout_transition=0,alimiter=limit=0.92[aout]")
    run(["ffmpeg", "-y"] + inputs + ["-filter_complex", ";".join(filters),
         "-map", "0:v", "-map", "[aout]", "-t", "18.5",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
         "-movflags", "+faststart", str(OUT)])
    print(f"Rendered: {OUT}")

if __name__ == "__main__":
    main()
