#!/usr/bin/env python3
"""Build a BAMO vertical motion-graphics composition and render it with HyperFrames."""
from __future__ import annotations
import argparse, html, json, subprocess
from pathlib import Path

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--brief", required=True)
    p.add_argument("--output-dir", default="output/bamo/hyperframes")
    p.add_argument("--cli-version", default="0.8.225")
    args = p.parse_args()
    brief = json.loads(Path(args.brief).read_text(encoding="utf-8"))
    roles = brief.get("roles") or {}
    required_roles = {"discovery", "strategy", "script_hook", "packaging", "seo", "production", "editing", "shorts", "chapters", "community", "analytics"}
    if set(roles) != required_roles or not all(str(value).strip() for value in roles.values()):
        raise SystemExit("BAMO production requires all 11 documented agent-role hand-offs")
    scenes = brief.get("scenes") or []
    if len(scenes) != 4:
        raise SystemExit("BAMO HyperFrames short requires exactly four authored scenes")
    if not all(str(s.get("text", "")).strip() and str(s.get("visual_prompt", "")).strip() for s in scenes):
        raise SystemExit("Every scene needs text and a scene-specific visual_prompt")
    durations = [float(s["duration"]) for s in scenes]
    if any(d <= 0 for d in durations):
        raise SystemExit("Scene durations must be positive")
    total = sum(durations)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    blocks = []
    offset = 0.0
    for i, (scene, duration) in enumerate(zip(scenes, durations)):
        bg = str(scene.get("background", "0x080d1b")).replace("0x", "#")
        accent = str(scene.get("accent", "0xd5a64b")).replace("0x", "#")
        text = html.escape(str(scene["text"]))
        prompt = html.escape(str(scene["visual_prompt"]))
        blocks.append(f"""
        <section class="scene scene-{i+1}" data-start="{offset:.3f}" data-duration="{duration:.3f}" data-track-index="1">
          <div class="orb orb-a"></div><div class="orb orb-b"></div>
          <div class="gridlines"></div>
          <div class="visual" aria-hidden="true"><div class="ring"></div><div class="core"></div><div class="beam"></div></div>
          <div class="eyebrow">BAMO  /  {i+1:02d} — 04</div>
          <h1>{text}</h1>
          <p class="visual-note">{prompt}</p>
          <div class="progress"><i style="--accent:{accent}"></i></div>
        </section>""")
        offset += duration
    composition = f"""<!doctype html>
<html lang="fa" dir="rtl">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(brief.get("title","BAMO"))}</title>
<style>
*{{box-sizing:border-box}}html,body{{margin:0;width:1080px;height:1920px;overflow:hidden;background:#080d1b;color:#fff;font-family:Tahoma,Arial,sans-serif}}
#stage{{position:relative;width:1080px;height:1920px;overflow:hidden;background:#080d1b}}
.scene{{position:absolute;inset:0;width:1080px;height:1920px;overflow:hidden;padding:190px 92px;background:radial-gradient(ellipse at 50% 43%,var(--glow),transparent 48%),var(--bg);opacity:0;}}
.scene-1{{--bg:#080d1b;--glow:#172c4a}}.scene-2{{--bg:#111827;--glow:#174e50}}.scene-3{{--bg:#1b1424;--glow:#502c4c}}.scene-4{{--bg:#101d20;--glow:#45502b}}
.gridlines{{position:absolute;inset:0;background-image:linear-gradient(#ffffff0b 1px,transparent 1px),linear-gradient(90deg,#ffffff0b 1px,transparent 1px);background-size:90px 90px;mask-image:linear-gradient(transparent,black 25%,black 75%,transparent)}}
.eyebrow{{position:relative;z-index:3;color:#d5a64b;font-size:27px;letter-spacing:7px;font-weight:bold;margin-top:65px}}
h1{{position:relative;z-index:3;font-size:76px;line-height:1.55;font-weight:900;margin:140px 0 45px;text-shadow:0 8px 36px #0009;max-width:900px}}
.visual-note{{position:relative;z-index:3;color:#cbd5e1;font-size:24px;line-height:1.8;opacity:.78}}
.visual{{position:absolute;left:50%;top:56%;width:720px;height:720px;transform:translate(-50%,-50%);display:grid;place-items:center}}
.ring{{position:absolute;width:620px;height:620px;border:3px solid #d5a64b99;border-radius:50%;box-shadow:0 0 90px #d5a64b44,inset 0 0 80px #d5a64b22}}
.core{{width:250px;height:250px;border-radius:28%;transform:rotate(45deg);background:linear-gradient(135deg,#fff8,#d5a64b66 35%,#162b49);box-shadow:0 0 100px #d5a64b99, inset 0 0 45px #fff7}}
.beam{{position:absolute;width:950px;height:4px;background:linear-gradient(90deg,transparent,#fff,#d5a64b,transparent);transform:rotate(-32deg);filter:drop-shadow(0 0 20px #fff);}}
.orb{{position:absolute;width:24px;height:24px;border-radius:50%;background:#fff;box-shadow:0 0 38px 14px #d5a64b88}}
.orb-a{{left:140px;top:720px}}.orb-b{{right:120px;top:1250px;width:15px;height:15px}}
.progress{{position:absolute;bottom:145px;right:92px;left:92px;height:5px;background:#ffffff33}}.progress i{{display:block;height:100%;width:100%;background:var(--accent)}}
</style></head>
<body><div id="stage" data-composition-id="bamo-short" data-start="0" data-duration="{total:.3f}" data-fps="30" data-width="1080" data-height="1920">
{''.join(blocks)}
</div>
<script>
window.__timelines=window.__timelines||{{}};
const tl=gsap.timeline({{paused:true}});
document.querySelectorAll(".scene").forEach((el,i)=>{{
 const start=Number(el.dataset.start), dur=Number(el.dataset.duration);
 tl.fromTo(el,{{autoAlpha:0,scale:1.035}},{{autoAlpha:1,scale:1,duration:.65,ease:"power3.out"}},start);
 tl.to(el,{{autoAlpha:0,duration:.45,ease:"power2.in"}},start+dur-.45);
 const h=el.querySelector("h1"), v=el.querySelector(".visual");
 tl.fromTo(h,{{y:90,opacity:0}},{{y:0,opacity:1,duration:.8,ease:"power3.out"}},start+.25);
 tl.fromTo(v,{{scale:.65,rotation:-12,opacity:0}},{{scale:1,rotation:0,opacity:1,duration:1.2,ease:"back.out(1.5)"}},start+.15);
 tl.to(v,{{rotation:12,duration:dur-1.4,ease:"sine.inOut"}},start+1.1);
}});
window.__timelines["bamo-short"]=tl;
</script></body></html>"""
    project = out / "index.html"
    project.write_text(composition, encoding="utf-8")
    cli = f"hyperframes@{args.cli_version}"
    subprocess.run(["npx","--yes",cli,"lint",str(out),"--json"],check=True,timeout=180)
    subprocess.run(["npx","--yes",cli,"render",str(out),"--output",str(out/"BAMO-HyperFrames.mp4"),"--fps","30","--quality","standard"],check=True,timeout=900)
    manifest = {"title":brief.get("title"),"renderer":"HyperFrames","duration_seconds":total,"resolution":"1080x1920","fps":30,"scenes":len(scenes),"agent_roles_validated":sorted(roles),"youtube_upload":"not_performed"}
    (out/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
