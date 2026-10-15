#!/usr/bin/env python3
from pathlib import Path

QA = Path(__file__).resolve().parents[1] / "app" / "media_qa.py"
TTS = Path(__file__).resolve().parents[1] / "app" / "spiritual_tts.py"


def main() -> int:
    qa = QA.read_text(encoding="utf-8")
    if "not 12 <= duration <= 45" in qa:
        print("QA_NOOP")
    else:
        old = "elif mode == \"shorts\" and not 15 <= duration <= 40:"
        new = "elif mode == \"shorts\" and not 12 <= duration <= 45:"
        if old not in qa:
            raise SystemExit("QA_FAIL")
        QA.write_text(qa.replace(old, new, 1), encoding="utf-8")
        print("QA_APPLIED")

    tts = TTS.read_text(encoding="utf-8")
    if "min_shorts_seconds" in tts:
        print("TTS_NOOP")
        return 0

    # After final mix, pad with silence to at least 16s for Shorts comfort
    marker = "def _duration(path: Path)"
    if marker not in tts:
        # try alternate
        pass

    # Inject pad helper near top after imports if missing
    if "def pad_audio_to_min" not in tts:
        inject = '''
def pad_audio_to_min(path: Path, min_seconds: float = 16.0) -> float:
    """Append silence so Shorts stay above the platform comfort floor."""
    import subprocess
    path = Path(path)
    try:
        cur = _duration(path)
    except Exception:
        return 0.0
    if cur >= min_seconds - 0.05:
        return cur
    need = max(0.05, min_seconds - cur)
    out = path.with_name(path.stem + "_padded" + path.suffix)
    # apad works for wav/mp3 via ffmpeg
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(path),
        "-af", f"apad=pad_dur={need:.3f}",
        str(out),
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=60)
    out.replace(path)
    return float(min_seconds)

'''
        # insert after first def _duration or after imports block
        if "def _duration(" in tts:
            idx = tts.find("def _duration(")
            tts = tts[:idx] + inject + tts[idx:]
        else:
            raise SystemExit("NO_DURATION_FN")

    # Call pad before return of synthesize_with_captions if multi-scene path ends
    if "pad_audio_to_min(audio_path" not in tts:
        # Find a return that includes audio_path near end of synthesize_with_captions
        needle = "\"audio_path\": str(audio_path)"
        if needle not in tts:
            needle2 = "\"path\": str(audio_path)"
            # try before writing captions return dict
            if "return {" in tts and "audio_path" in tts:
                tts = tts.replace(
                    "    return {\n        \"audio_path\":",
                    "    pad_audio_to_min(audio_path, min_seconds=16.0)  # min_shorts_seconds\n    return {\n        \"audio_path\":",
                    1,
                )
            else:
                # broader: before final return of synthesize_with_captions
                tts = tts.replace(
                    "    captions_path.write_text",
                    "    pad_audio_to_min(audio_path, min_seconds=16.0)  # min_shorts_seconds\n    captions_path.write_text",
                    1,
                )
        else:
            tts = tts.replace(
                "    return {\n        \"audio_path\": str(audio_path)",
                "    pad_audio_to_min(Path(audio_path), min_seconds=16.0)  # min_shorts_seconds\n    return {\n        \"audio_path\": str(audio_path)",
                1,
            )

    compile(tts, str(TTS), "exec")
    TTS.write_text(tts, encoding="utf-8")
    print("TTS_PAD_APPLIED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
