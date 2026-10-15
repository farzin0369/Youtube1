#!/usr/bin/env python3
"""Allow AI_VIDEO_ENGINE=cogvideo|local and use visual_prompts in local engine."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def patch_spiritual_video() -> None:
    p = ROOT / "app" / "spiritual_video.py"
    t = p.read_text(encoding="utf-8")
    if "cogvideo" in t and 'ai_engine == "cogvideo"' in t:
        print("SV_NOOP")
        return
    t = t.replace(
        'if ai_engine not in {"", "ltx", "wan"}:',
        'if ai_engine not in {"", "ltx", "wan", "cogvideo", "local", "cogvideox"}:',
        1,
    )
    t = t.replace(
        'if ai_engine in {"ltx", "wan"} and video_format != "shorts":',
        'if ai_engine in {"ltx", "wan", "cogvideo", "local", "cogvideox"} and video_format != "shorts":',
        1,
    )
    # Insert cogvideo branch before wan if missing
    if 'ai_engine == "cogvideo"' not in t and 'ai_engine == "wan"' in t:
        wan_block = '        if ai_engine == "wan":'
        inject = '''        if ai_engine in {"cogvideo", "local", "cogvideox"}:
            from app.local_video_engine import generate_film
            film = generate_film(
                script=" ".join(str(q) for q in queries),
                title=str(title or "ImamAli110"),
                out_path=out_dir / "ai_film.mp4",
                kind="short",
            )
            # Prefer per-scene clips if plan wrote them next to out_path
            plan_path = (out_dir / "ai_film_scene_plan.json")
            ai_clips = []
            stock, credits = [], [f"cogvideox:{film.get('model')}"]
            logging.getLogger(__name__).info("cogvideo film ok=%s model=%s", film.get("ok"), film.get("model"))
        el'''
        # careful: "elif" chain
        t = t.replace(
            '        if ai_engine == "wan":',
            inject + 'if ai_engine == "wan":',
            1,
        )
    compile(t, str(p), "exec")
    p.write_text(t, encoding="utf-8")
    print("SV_OK")


def patch_local_scene_prompt() -> None:
    p = ROOT / "app" / "local_video_engine.py"
    t = p.read_text(encoding="utf-8")
    if "visual_prompts import" in t or "cinematic_prompt_for_scene" in t:
        print("LOC_NOOP")
        return
    # Prefer spiritual cinematic mapper at start of _scene_prompt
    old = "def _scene_prompt(sentence: str, title: str, index: int) -> str:\n    text = f\"{title} {sentence}\".lower()"
    new = (
        "def _scene_prompt(sentence: str, title: str, index: int) -> str:\n"
        "    try:\n"
        "        from app.visual_prompts import cinematic_prompt_for_scene\n"
        "        return cinematic_prompt_for_scene(sentence, scene_index=index, topic=title)\n"
        "    except Exception:\n"
        "        pass\n"
        "    text = f\"{title} {sentence}\".lower()"
    )
    if old in t:
        t = t.replace(old, new, 1)
        compile(t, str(p), "exec")
        p.write_text(t, encoding="utf-8")
        print("LOC_OK")
    else:
        print("LOC_SKIP")


def main() -> int:
    patch_spiritual_video()
    patch_local_scene_prompt()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
