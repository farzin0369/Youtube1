#!/usr/bin/env python3
"""Male Piper (gyro/ganji) + stronger scene-keyword matching for Mixkit."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PIPER_NEW = '''"""Offline free Persian TTS via Piper male voices (rhasspy gyro/ganji)."""
from __future__ import annotations

from app.persian_tts_normalize import normalize_for_tts

import logging
import os
import wave
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Male Persian Piper voices (MIT/CC0 family via rhasspy/piper-voices) — no API key.
# Prefer gyro (male, high naturalness score), fallback ganji.
VOICE_CANDIDATES = [
    {
        "repo": "rhasspy/piper-voices",
        "onnx": "fa/fa_IR/gyro/medium/fa_IR-gyro-medium.onnx",
        "json": "fa/fa_IR/gyro/medium/fa_IR-gyro-medium.onnx.json",
        "local_onnx": "fa_IR-gyro-medium.onnx",
        "local_json": "fa_IR-gyro-medium.onnx.json",
        "name": "gyro-male",
    },
    {
        "repo": "rhasspy/piper-voices",
        "onnx": "fa/fa_IR/ganji/medium/fa_IR-ganji-medium.onnx",
        "json": "fa/fa_IR/ganji/medium/fa_IR-ganji-medium.onnx.json",
        "local_onnx": "fa_IR-ganji-medium.onnx",
        "local_json": "fa_IR-ganji-medium.onnx.json",
        "name": "ganji-male",
    },
    {
        "repo": "rhasspy/piper-voices",
        "onnx": "fa/fa_IR/amir/medium/fa_IR-amir-medium.onnx",
        "json": "fa/fa_IR/amir/medium/fa_IR-amir-medium.onnx.json",
        "local_onnx": "fa_IR-amir-medium.onnx",
        "local_json": "fa_IR-amir-medium.onnx.json",
        "name": "amir-male",
    },
]


def _model_dir() -> Path:
    root = Path(os.getenv("PIPER_MODEL_DIR") or "models/piper").resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def ensure_male_piper_model() -> tuple[Path, str]:
    """Download first available male Piper Persian voice (HF, free, no key)."""
    out = _model_dir()
    try:
        from huggingface_hub import hf_hub_download
    except ImportError as exc:
        raise RuntimeError(
            "piper backend needs huggingface_hub; pip install huggingface_hub piper-tts"
        ) from exc

    last_err: Exception | None = None
    for cand in VOICE_CANDIDATES:
        onnx = out / cand["local_onnx"]
        cfg = out / cand["local_json"]
        if onnx.is_file() and cfg.is_file() and onnx.stat().st_size > 1_000_000:
            return onnx, cand["name"]
        try:
            logger.info("downloading free male Piper voice %s …", cand["name"])
            hf_hub_download(
                repo_id=cand["repo"],
                filename=cand["onnx"],
                local_dir=str(out),
                local_dir_use_symlinks=False,
            )
            hf_hub_download(
                repo_id=cand["repo"],
                filename=cand["json"],
                local_dir=str(out),
                local_dir_use_symlinks=False,
            )
            # Flatten nested HF path into local flat names
            nested_onnx = out / cand["onnx"]
            nested_json = out / cand["json"]
            if nested_onnx.is_file() and nested_onnx.resolve() != onnx.resolve():
                onnx.write_bytes(nested_onnx.read_bytes())
            if nested_json.is_file() and nested_json.resolve() != cfg.resolve():
                cfg.write_bytes(nested_json.read_bytes())
            if onnx.is_file() and cfg.is_file():
                return onnx, cand["name"]
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            logger.warning("piper voice %s failed: %s", cand["name"], type(exc).__name__)
            continue
    raise RuntimeError(f"no male Piper Persian voice available: {last_err}")


def _length_scale_for_mood(mood: str, hint: dict[str, Any] | None = None) -> float:
    """Map scene mood to Piper speaking-rate (lower = slower / calmer)."""
    base = {
        "hook": 0.95,
        "calm": 0.82,
        "reassuring": 0.86,
        "motivational": 1.05,
        "sad": 0.80,
        "joyful": 1.08,
    }.get(str(mood or "").lower(), 0.90)
    hint = hint if isinstance(hint, dict) else {}
    emotion = str(hint.get("emotion") or "").lower()
    if emotion in {"calm", "reassuring", "sad"}:
        base = min(base, 0.85)
    if emotion in {"motivational", "joyful", "angry"}:
        base = max(base, 1.02)
    return max(0.75, min(1.20, float(base)))


def synthesize_piper(
    text: str,
    audio_path: Path,
    *,
    mood: str = "calm",
    hint: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Synthesize one utterance with offline male Piper; writes WAV/MP3 path."""
    from piper import PiperVoice  # type: ignore

    cleaned = normalize_for_tts(" ".join(str(text or "").split()).strip())
    if not cleaned:
        raise ValueError("empty text for piper tts")

    model_path, voice_name = ensure_male_piper_model()
    voice = PiperVoice.load(str(model_path))
    length_scale = _length_scale_for_mood(mood, hint)

    audio_path = Path(audio_path)
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    wav_path = audio_path.with_suffix(".wav")

    with wave.open(str(wav_path), "wb") as wav_file:
        try:
            voice.synthesize_wav(cleaned, wav_file, length_scale=length_scale)
        except TypeError:
            voice.synthesize_wav(cleaned, wav_file)

    # Optional mp3 target
    if audio_path.suffix.lower() == ".mp3":
        import subprocess

        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(wav_path),
                "-codec:a",
                "libmp3lame",
                "-q:a",
                "3",
                str(audio_path),
            ],
            check=True,
            capture_output=True,
            timeout=120,
        )
    else:
        if wav_path.resolve() != audio_path.resolve():
            audio_path.write_bytes(wav_path.read_bytes())

    return {
        "provider": "piper",
        "model": "rhasspy/piper-voices",
        "voice": voice_name,
        "gender": "male",
        "length_scale": length_scale,
        "path": str(audio_path),
    }
'''


def patch_piper() -> None:
    p = ROOT / "app" / "piper_tts.py"
    p.write_text(PIPER_NEW, encoding="utf-8")
    compile(PIPER_NEW, str(p), "exec")
    print("PIPER_MALE_OK")


def patch_tts_allow_male_piper() -> None:
    p = ROOT / "app" / "spiritual_tts.py"
    t = p.read_text(encoding="utf-8")
    # Remove force-switch away from piper (now male)
    old = '''    configured = env("TTS_PROVIDER")  # male-voice-v1
    # Mana-Persian-Piper is a female voice; channel requires male narration.
    if (configured or "").strip().lower() == "piper" and env("ALLOW_FEMALE_TTS", "").lower() not in {"1", "true", "yes"}:
        logging.getLogger(__name__).warning("piper Mana is female — switching to edge-tts Farid (male)")
        configured = "edge-tts"'''
    new = '''    configured = env("TTS_PROVIDER")  # male-piper-gyro-v1
    # Prefer piper male (gyro/ganji/amir). Edge Farid remains fallback if piper fails.'''
    if old in t:
        t = t.replace(old, new, 1)
    else:
        # softer match
        if "piper Mana is female" in t:
            import re

            t = re.sub(
                r"configured = env\(\"TTS_PROVIDER\"\).*?configured = \"edge-tts\"\n",
                'configured = env("TTS_PROVIDER")  # male-piper-gyro-v1\n',
                t,
                count=1,
                flags=re.S,
            )
    compile(t, str(p), "exec")
    p.write_text(t, encoding="utf-8")
    print("TTS_ALLOW_PIPER")


def patch_mixkit_keywords() -> None:
    p = ROOT / "app" / "spiritual_video.py"
    t = p.read_text(encoding="utf-8")
    if "scene-match-v1" in t:
        print("MIXKIT_NOOP")
        return

    helper = '''
# scene-match-v1: map Persian spiritual themes to distinct free Mixkit visual queries
_THEME_VISUALS = {
    "توکل": ["person walking path nature", "sunrise mountain silhouette", "calm open sky"],
    "نفس": ["deep breath nature forest", "peaceful lake reflection", "slow clouds sky"],
    "صبر": ["hourglass sand slow", "rain window calm", "candle flame close"],
    "شکر": ["sunrise golden field", "hands open sunlight", "birds flying sky"],
    "قدم": ["footsteps path forest", "walking trail nature", "bridge over river"],
    "نور": ["light rays through trees", "candle in dark room", "sunrise through window"],
    "آرام": ["calm ocean waves", "misty morning forest", "quiet empty mosque courtyard"],
    "دعا": ["hands prayer silhouette", "candle light spirituality", "moon night sky"],
    "امید": ["sunrise over hills", "light at end of tunnel", "green sprout soil"],
    "تلاش": ["person climbing hill", "hands working soil", "road journey mountains"],
}

def _visual_queries_for_scenes(keywords: list[str], count: int = 4) -> list[str]:
    """Build diversified English visual queries aligned to spiritual keywords."""
    import random
    joined = " ".join(str(k) for k in (keywords or []))
    picked: list[str] = []
    for theme, visuals in _THEME_VISUALS.items():
        if theme in joined:
            for v in visuals:
                if v not in picked:
                    picked.append(v)
    # Always enrich with generic spiritual-safe free stock
    extras = [
        "candle light darkness",
        "person silhouette sunrise",
        "forest path sunlight",
        "calm sea horizon",
        "desert dunes golden hour",
        "night sky stars timelapse",
        "rain drops leaf macro",
        "open book light window",
    ]
    for e in extras:
        if e not in picked:
            picked.append(e)
    # seed with original english-ish keywords if any ascii
    for k in keywords or []:
        ks = str(k).strip()
        if ks and all(ord(c) < 128 for c in ks) and ks not in picked:
            picked.insert(0, ks)
    random.shuffle(picked)
    return picked[: max(count * 3, 8)]

'''

    if "_THEME_VISUALS" not in t:
        # insert before fetch_mixkit_stock
        anchor = "def fetch_mixkit_stock("
        if anchor not in t:
            print("MIXKIT_ANCHOR_MISSING")
            return
        t = t.replace(anchor, helper + "\ndef fetch_mixkit_stock(", 1)

    # Use diversified queries inside fetch_mixkit_stock
    old_q = '    queries = (keywords or ["calm nature", "peaceful light", "sunrise", "ocean waves"])[: max(count * 2, 4)]'
    new_q = '    queries = _visual_queries_for_scenes(keywords or ["calm", "light", "path", "sunrise"], count)  # scene-match-v1'
    if old_q in t:
        t = t.replace(old_q, new_q, 1)

    compile(t, str(p), "exec")
    p.write_text(t, encoding="utf-8")
    print("MIXKIT_MATCH_OK")


def main() -> int:
    patch_piper()
    patch_tts_allow_male_piper()
    patch_mixkit_keywords()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
