#!/usr/bin/env python3
"""Studio proof: three different topics (math, physics, comedy) rendered end to end.

Reuses the audited pipeline in scripts/render_ai_domain_proof.py (Persian TTS ->
AI scene director -> Blender CPU render -> burned word-timed captions -> frame
samples) with a different topic set, then reports which prefab kinds the director
actually used. Never uploads or publishes; never falls back to canned motifs.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

OUT = Path("output/bamo-studio-proof")

SCENES = [
    {
        "domain": "mathematics",
        "slug": "ellipse-foci",
        "title": "بیضی و کانون‌های آن",
        "spoken_text": (
            "بیضی فقط یک دایرهٔ کشیده نیست. دو نقطهٔ ثابت به نام کانون دارد. "
            "هر نقطه روی بیضی را انتخاب کن و فاصله‌اش را تا هر کانون اندازه بگیر. "
            "جمع این دو فاصله همیشه ثابت می‌ماند؛ همین قانون، شکل بیضی را تعریف می‌کند."
        ),
        "visual_query": "A 3D ellipse construction with two fixed foci, a moving point on the curve, and two changing distance lines whose sum remains constant",
        "on_screen_text": "بیضی: مجموع فاصله تا دو کانون ثابت است",
    },
    {
        "domain": "physics",
        "slug": "wave-interference",
        "title": "تداخل دو موج",
        "spoken_text": (
            "وقتی دو موج همدام در یک فاز به هم می‌رسند، دامنه‌هایشان روی هم جمع می‌شود. "
            "در این نقاط، تداخل سازنده موجی قوی‌تر می‌سازد. "
            "اگر اختلاف مسیر نیم‌طول‌موج باشد، تداخل ویرانگر موج را تضعیف می‌کند."
        ),
        "visual_query": "A wave_field of bars showing two coherent in-phase wave sources: tall bars where constructive interference peaks and short bars along destructive nodes, with a slow orbiting camera",
        "on_screen_text": "دو موج: تداخل سازنده و ویرانگر",
    },
    {
        "domain": "comedy",
        "slug": "robot-chef",
        "title": "ربات آشپز و املت صبور",
        "spoken_text": (
            "ربات کوچکی تصمیم گرفت آشپز شود. اولین کارش پختن یک املت بود. "
            "تخم‌مرغ را با دقت اندازه گرفت، با احتیاط شکست، و بعد ده دقیقه منتظر ماند تا خودش پخته شود. "
            "املت پخته نشد؛ ولی ربات مطمئن بود آشپزی یعنی صبر."
        ),
        "visual_query": "A small stylized figure robot character in a kitchen set with a table, a pan and an egg; it carefully cracks the egg, then stands waiting beside the pan with exaggerated comic timing",
        "on_screen_text": "ربات آشپز و املت صبور",
    },
]


def _load_base():
    path = ROOT / "scripts" / "render_ai_domain_proof.py"
    spec = importlib.util.spec_from_file_location("render_ai_domain_proof", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    base = _load_base()
    base.OUT = OUT
    base.SCENES = SCENES
    import app.bamo_ai_director as director
    prefab_active = bool(getattr(director, "_BAMO_SCENE_KIT", False))
    base.main()
    evidence = json.loads((OUT / "ai-domain-evidence.json").read_text(encoding="utf-8"))
    prefab_file = ROOT / "scripts" / "bamo_prefabs.py"
    spec = importlib.util.spec_from_file_location("bamo_prefabs_proof", prefab_file)
    prefabs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(prefabs)
    rows = []
    for video in evidence["videos"]:
        used = sorted({k for k in video["object_kinds"] if k in prefabs.PREFAB_KINDS})
        rows.append({"domain": video["domain"], "object_kinds": video["object_kinds"],
                     "prefab_kinds_used": used, "uses_prefabs": bool(used)})
    summary = {
        "prefab_director_installed": prefab_active,
        "videos": rows,
        "note": "Technical preview. Frame review by a human is still required before any publication.",
    }
    (OUT / "studio-proof-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "studio-proof-failure.txt").write_text(traceback.format_exc(), encoding="utf-8")
        raise
