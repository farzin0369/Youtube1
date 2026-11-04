#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
parts_dir = ROOT / "scripts" / "director_parts"
chunks = []
for path in sorted(parts_dir.glob("part_*.txt"), key=lambda p: int(p.stem.split("_")[1])):
    chunks.append(path.read_text(encoding="utf-8"))
text = "".join(chunks)
if "def direct_scene" not in text or len(text) < 20000:
    raise SystemExit(f"assembled director invalid len={len(text)}")
compile(text, "bamo_ai_director.py", "exec")
target = ROOT / "app" / "bamo_ai_director.py"
target.write_text(text, encoding="utf-8")
print("assembled", len(text), "->", target)
