#!/usr/bin/env python3
"""Build a BAMO vertical motion-graphics composition and render it with HyperFrames.

Uses the pinned HyperFrames CLI package version declared by the CPU workflow.
"""
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
        if i == 0:
            world_markup = ''.join(f'<div class="stair" style="--n:{n}"></div>' for n in range(12))
        elif i == 1:
            world_markup = '<div class="fork fork-left"></div><div class="fork fork-right"></div><div class="choice-orb"></div><div class="camera-marker"></div>'
        elif i == 2:
            world_markup = ''.join(f'<div class="orbit orbit-{n}"></div>' for n in range(1, 8)) + ''.join(f'<i class="waypoint" style="--n:{n}"></i>' for n in range(9))
        else:
            world_markup = '<div class="portal-outer"></div><div class="portal-inner"></div><div class="portal-floor"></div><div class="rise-arrow">↑</div>'
        blocks.append(f"""
        <section id="scene-{i+1}" class="scene clip scene-{i+1}" data-start="{offset:.3f}" data-duration="{duration:.3f}" data-track-index="1">
          <div class="orb orb-a"></div><div class="orb orb-b"></div>
          <div class="gridlines"></div>
          <div class="visual" aria-hidden="true"><div class="ring"></div><div class="core"></div><div class="beam"></div></div>
          <div class="eyebrow">BAMO  /  {i+1:02d} — 04</div>
          <h1>{text}</h1>
          <div class="camera-rig"><div class="world world-{i+1}">{world_markup}</div></div>
          <div class="progress"><i style="--accent:{accent}"></i></div>
        </section>""")
        offset += duration
    composition = f"""<!doctype html>
<html lang="fa" dir="rtl">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script><title>{html.escape(brief.get("title","BAMO"))}</title>
<style>
*{{box-sizing:border-box}}html,body{{margin:0;width:1080px;height:1920px;overflow:hidden;background:#080d1b;color:#fff;font-family:Tahoma,Arial,sans-serif}}
#stage{{position:relative;width:1080px;height:1920px;overflow:hidden;background:#080d1b}}
.scene{{position:absolute;inset:0;width:1080px;height:1920px;overflow:hidden;padding:190px 92px;background:radial-gradient(ellipse at 50% 43%,var(--glow),transparent 48%),var(--bg);opacity:0;}}
.scene-1{{--bg:#080d1b;--glow:#172c4a}}.scene-2{{--bg:#111827;--glow:#174e50}}.scene-3{{--bg:#1b1424;--glow:#502c4c}}.scene-4{{--bg:#101d20;--glow:#45502b}}
.gridlines{{position:absolute;inset:0;background-image:linear-gradient(#ffffff0b 1px,transparent 1px),linear-gradient(90deg,#ffffff0b 1px,transparent 1px);background-size:90px 90px;mask-image:linear-gradient(transparent,black 25%,black 75%,transparent)}}
.eyebrow{{position:relative;z-index:3;color:#d5a64b;font-size:27px;letter-spacing:7px;font-weight:bold;margin-top:65px}}
h1{{position:relative;z-index:3;font-size:76px;line-height:1.55;font-weight:900;margin:140px 0 45px;text-shadow:0 8px 36px #0009;max-width:900px}}
.camera-rig{{position:absolute;inset:0;perspective:1050px;transform-style:preserve-3d;pointer-events:none;z-index:1;overflow:hidden}}
.world{{position:absolute;left:50%;top:58%;width:900px;height:900px;transform:translate(-50%,-50%);transform-style:preserve-3d}}
.stair{{position:absolute;left:50%;bottom:8%;width:360px;height:42px;margin-left:-180px;background:linear-gradient(180deg,#e9c978,#8e642b 55%,#342719);border:1px solid #f7df9a;box-shadow:0 14px 28px #0009,0 0 28px #d5a64b66;transform:translate3d(0,calc(var(--n)*-55px),calc(var(--n)*-76px)) rotateX(58deg) scale(calc(1 - var(--n)*.035));opacity:calc(1 - var(--n)*.045)}}
.fork{{position:absolute;left:50%;top:52%;width:18px;height:520px;border-radius:20px;transform-origin:50% 0;background:linear-gradient(90deg,#b68a42,#fff0b2,#765124);box-shadow:0 0 36px #d5a64b88}}
.fork-left{{transform:translateX(-50%) rotate(-34deg) translateZ(30px)}}
.fork-right{{transform:translateX(-50%) rotate(34deg) translateZ(-30px);opacity:.35;filter:grayscale(1)}}
.choice-orb{{position:absolute;left:50%;top:45%;width:105px;height:105px;border-radius:50%;transform:translate(-50%,-50%) translateZ(110px);background:radial-gradient(circle at 30% 25%,#fff,#70e4d2 30%,#087b7b 75%);box-shadow:0 0 90px #4db6ac}}
.camera-marker{{position:absolute;left:50%;top:78%;width:32px;height:32px;border-radius:50%;background:#fff;box-shadow:0 0 45px #4db6ac;transform:translateZ(160px)}}
.orbit{{position:absolute;left:50%;top:50%;width:calc(240px + var(--n)*75px);height:calc(240px + var(--n)*75px);border:2px solid #d36b59aa;border-radius:50%;transform:translate(-50%,-50%) rotateX(68deg) rotateZ(calc(var(--n)*13deg));box-shadow:0 0 24px #d36b5944}}
.orbit-1{{--n:1}}.orbit-2{{--n:2}}.orbit-3{{--n:3}}.orbit-4{{--n:4}}.orbit-5{{--n:5}}.orbit-6{{--n:6}}.orbit-7{{--n:7}}
.waypoint{{position:absolute;left:50%;top:50%;width:13px;height:13px;border-radius:50%;background:#ffe5b0;box-shadow:0 0 26px 9px #d36b59;transform:rotate(calc(var(--n)*40deg)) translateY(calc(-130px - var(--n)*32px)) translateZ(90px)}}
.portal-outer,.portal-inner{{position:absolute;left:50%;top:43%;border-radius:50%;transform:translate(-50%,-50%) rotateY(-18deg) rotateX(8deg);border:18px solid #e4c16f;box-shadow:0 0 70px #e4c16f99,inset 0 0 55px #e4c16f44}}
.portal-outer{{width:520px;height:700px}}
.portal-inner{{width:420px;height:600px;border-width:5px;border-color:#fff3b0}}
.portal-floor{{position:absolute;left:50%;top:75%;width:800px;height:240px;transform:translate(-50%,-50%) rotateX(72deg);background:radial-gradient(ellipse,#e4c16f66,transparent 68%);border-radius:50%}}
.rise-arrow{{position:absolute;left:50%;top:45%;font-size:190px;color:#fff4c7;text-shadow:0 0 50px #e4c16f;transform:translate(-50%,-50%) translateZ(120px)}}

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
 const h=el.querySelector("h1"), v=el.querySelector(".visual"), camera=el.querySelector(".camera-rig");
 tl.fromTo(camera,{{z:-260,rotationX:8,rotationY:-10,scale:.82}},{{z:0,rotationX:0,rotationY:0,scale:1,duration:1.6,ease:"power3.out"}},start);
 tl.to(camera,{{rotationY:i%2===0?12:-12,rotationX:i%2===0?-5:5,z:65,duration:Math.max(1,dur-1.7),ease:"sine.inOut"}},start+1.2);
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
