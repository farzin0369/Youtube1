#!/usr/bin/env python3
from pathlib import Path

TTS = Path(__file__).resolve().parents[1] / "app" / "spiritual_tts.py"
PIPER = Path(__file__).resolve().parents[1] / "app" / "piper_tts.py"


def wire_file(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "normalize_for_tts" in text:
        print(path.name, "NOOP")
        return
    # import
    if "from app.persian_tts_normalize" not in text:
        if "from __future__" in text:
            # after future import block
            lines = text.splitlines(keepends=True)
            out = []
            inserted = False
            for i, line in enumerate(lines):
                out.append(line)
                if not inserted and line.startswith("from __future__"):
                    # insert after blank following future
                    pass
            text = "".join(lines)
            text = text.replace(
                "from __future__ import annotations\n",
                "from __future__ import annotations\n\nfrom app.persian_tts_normalize import normalize_for_tts\n",
                1,
            )
        else:
            text = "from app.persian_tts_normalize import normalize_for_tts\n" + text

    # spiritual_tts: normalize script early
    if path.name == "spiritual_tts.py":
        old = '    normalized_script = re.sub(r"\\s+", " ", str(text or "")).strip()'
        new = '    normalized_script = normalize_for_tts(re.sub(r"\\s+", " ", str(text or "")).strip())'
        if old in text:
            text = text.replace(old, new, 1)
        # also normalize each scene_text in loop if present
        if "scene_text = str(scene.get" in text and "normalize_for_tts(scene_text)" not in text:
            text = text.replace(
                "scene_text = str(scene.get(\"spoken_text\") or scene.get(\"text\") or \"\").strip()",
                "scene_text = normalize_for_tts(str(scene.get(\"spoken_text\") or scene.get(\"text\") or \"\").strip())",
                1,
            )

    if path.name == "piper_tts.py":
        old = '    cleaned = " ".join(str(text or "").split()).strip()'
        new = '    cleaned = normalize_for_tts(" ".join(str(text or "").split()).strip())'
        if old in text:
            text = text.replace(old, new, 1)

    compile(text, str(path), "exec")
    path.write_text(text, encoding="utf-8")
    print(path.name, "APPLIED")


def main() -> int:
    wire_file(TTS)
    if PIPER.is_file():
        wire_file(PIPER)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
