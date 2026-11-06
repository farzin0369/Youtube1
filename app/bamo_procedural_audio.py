"""
BAMO procedural ambient audio
Generates a soft cinematic pad / drone based on mood.
Uses only stdlib + numpy (already in requirements).
Output: 16-bit mono WAV suitable for FFmpeg ducking mix.
"""
from __future__ import annotations

import math
import struct
import wave
from pathlib import Path
from typing import Any

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


# Mood → base frequencies / character
MOOD_AUDIO = {
    "calm":       {"freqs": [110.0, 165.0, 220.0], "brightness": 0.3, "motion": 0.15},
    "epic":       {"freqs": [82.5, 123.5, 185.0, 247.0], "brightness": 0.55, "motion": 0.35},
    "mysterious": {"freqs": [98.0, 147.0, 196.0], "brightness": 0.25, "motion": 0.2},
    "energetic":  {"freqs": [130.8, 196.0, 261.6], "brightness": 0.6, "motion": 0.55},
    "sad":        {"freqs": [87.3, 130.8, 174.6], "brightness": 0.2, "motion": 0.1},
    "futuristic": {"freqs": [100.0, 150.0, 225.0, 300.0], "brightness": 0.5, "motion": 0.4},
    "hopeful":    {"freqs": [123.5, 185.0, 246.9], "brightness": 0.4, "motion": 0.25},
    "spiritual":  {"freqs": [110.0, 164.8, 220.0], "brightness": 0.35, "motion": 0.2},
}


def _synth_numpy(duration: float, mood: str, sample_rate: int = 44100) -> bytes:
    cfg = MOOD_AUDIO.get(mood, MOOD_AUDIO["spiritual"])
    n = int(duration * sample_rate)
    t = np.linspace(0, duration, n, endpoint=False)
    sig = np.zeros(n, dtype=np.float64)
    for i, f in enumerate(cfg["freqs"]):
        amp = 0.18 / (1 + i * 0.35)
        # slow amplitude motion
        lfo = 0.7 + 0.3 * np.sin(2 * math.pi * (0.05 + cfg["motion"] * 0.08) * t + i)
        sig += amp * lfo * np.sin(2 * math.pi * f * t)
        # soft harmonic
        if cfg["brightness"] > 0.3:
            sig += amp * 0.25 * cfg["brightness"] * np.sin(2 * math.pi * f * 2 * t)
    # gentle fade in/out
    fade = int(0.8 * sample_rate)
    if fade * 2 < n:
        sig[:fade] *= np.linspace(0, 1, fade)
        sig[-fade:] *= np.linspace(1, 0, fade)
    # normalize soft
    peak = np.max(np.abs(sig)) or 1.0
    sig = sig / peak * 0.35
    pcm = (sig * 32767).astype(np.int16)
    return pcm.tobytes()


def _synth_stdlib(duration: float, mood: str, sample_rate: int = 44100) -> bytes:
    cfg = MOOD_AUDIO.get(mood, MOOD_AUDIO["spiritual"])
    n = int(duration * sample_rate)
    frames = []
    for i in range(n):
        t = i / sample_rate
        s = 0.0
        for j, f in enumerate(cfg["freqs"]):
            amp = 0.18 / (1 + j * 0.35)
            lfo = 0.7 + 0.3 * math.sin(2 * math.pi * (0.05 + cfg["motion"] * 0.08) * t + j)
            s += amp * lfo * math.sin(2 * math.pi * f * t)
        # fade
        fade = 0.8
        if t < fade:
            s *= t / fade
        elif t > duration - fade:
            s *= max(0.0, (duration - t) / fade)
        s = max(-0.35, min(0.35, s))
        frames.append(struct.pack("<h", int(s * 32767)))
    return b"".join(frames)


def generate_ambient(
    path: str | Path,
    duration: float,
    mood: str = "spiritual",
    sample_rate: int = 44100,
) -> Path:
    """Write a mono 16-bit WAV ambient bed for the given mood and duration."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    duration = max(1.0, float(duration))
    mood = (mood or "spiritual").lower()
    if mood not in MOOD_AUDIO:
        mood = "spiritual"

    data = _synth_numpy(duration, mood, sample_rate) if HAS_NUMPY else _synth_stdlib(duration, mood, sample_rate)

    with wave.open(str(out), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(data)
    return out


def mood_from_project(project: dict[str, Any]) -> str:
    return str(project.get("globalMood") or "spiritual")
