"""CPU-first hybrid motion-graphics renderer for BAMO.

FFmpeg is the dependable daily renderer. Optional local images are animated
with zoom/pan; scenes without assets use procedural animated backgrounds.
Remotion, Manim and Blender are optional specialist adapters, not requirements.
"""
from __future__ import annotations
import json, math, shutil, subprocess
from pathlib import Path
from typing import Any

FORMATS = {"short": (720,1280), "vertical": (720,1280), "long": (1280,720), "landscape": (1280,720), "square": (1080,1080)}
PALETTES = [("0x10172a","0xb98b43"),("0x111827","0x3b82a0"),("0x1c1424","0xbd5964"),("0x101d20","0xb6a36a"),("0x191624","0x7d76b8")]

def validate_project(project: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(project, dict): raise ValueError("Project must be a JSON object")
    scenes = project.get("scenes")
    if not isinstance(scenes, list) or not scenes: raise ValueError("Project must contain a non-empty scenes array")
    fmt = str(project.get("format","short")).lower()
    if fmt not in FORMATS: raise ValueError(f"Unsupported format: {fmt}")
    clean = []
    for index, scene in enumerate(scenes,1):
        if not isinstance(scene,dict): raise ValueError(f"Scene {index} must be an object")
        duration = float(scene.get("duration",4))
        if not math.isfinite(duration) or duration < .5 or duration > 60: raise ValueError(f"Scene {index} duration must be between 0.5 and 60 seconds")
        clean.append({"duration":duration,"text":str(scene.get("on_screen_text") or scene.get("text") or "").strip(),"image":str(scene.get("image") or "").strip(),"background":str(scene.get("background") or "").strip(),"accent":str(scene.get("accent") or "").strip(),"visual_prompt":str(scene.get("visual_prompt") or "").strip(),"narration":str(scene.get("narration") or "").strip()})
    return {"format":fmt,"scenes":clean}

def _ass_time(seconds: float) -> str:
    total=max(0,int(round(seconds*100))); hours,rem=divmod(total,360000); minutes,rem=divmod(rem,6000); secs,centis=divmod(rem,100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"

def _ass_escape(value: str) -> str:
    return value.replace("\\",r"\\").replace("{",r"\{").replace("}",r"\}").replace("\n",r"\N")

def _write_ass(scenes: list[dict[str,Any]], path: Path, width: int, height: int) -> None:
    hero_size=max(38,int(width*.066)); brand_size=max(22,int(width*.032)); margin=max(42,int(width*.08))
    header=f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Main,Noto Naskh Arabic,{hero_size},&H00FFFFFF,&H000000FF,&HCC080C16,&H88000000,1,0,0,0,100,100,0,0,1,4,2,5,{margin},{margin},{int(height*.10)},1
Style: Brand,Noto Naskh Arabic,{brand_size},&H00D5A64B,&H000000FF,&HCC080C16,&H88000000,1,0,0,0,100,100,0,0,1,2,1,8,{margin},{margin},{int(height*.06)},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events=[]; cursor=0.0
    for scene in scenes:
        duration=scene["duration"]
        if scene["text"]:
            events.append(f"Dialogue: 0,{_ass_time(cursor+.12)},{_ass_time(cursor+duration-.12)},Brand,,0,0,0,,BAMO  •  #12bamo")
            events.append(f"Dialogue: 1,{_ass_time(cursor+.18)},{_ass_time(cursor+duration-.12)},Main,,0,0,0,,{{\\fad(220,220)}}{_ass_escape(scene['text'])}")
        cursor += duration
    path.write_text(header+"\n".join(events)+"\n",encoding="utf-8")

def _run(command: list[str], timeout: int=900) -> None:
    result=subprocess.run(command,capture_output=True,text=True,timeout=timeout)
    if result.returncode: raise RuntimeError(f"FFmpeg failed ({result.returncode}): {result.stderr[-3000:]}")


def _project_3d(x,y,z,angle,zoom,w,h):
    ca,sa=math.cos(angle),math.sin(angle); xr,zr=x*ca-z*sa,x*sa+z*ca
    dep=5.8-zr; scale=min(w,h)*.48*zoom/max(1.2,dep)
    return w*.5+xr*scale,h*.5-y*scale,dep,scale

def _render_3d_scene(path,duration,width,height,fps,index,bg,accent,visual_plan=None):
    visual_plan = visual_plan or {}
    motif = visual_plan.get('motif', 'abstract')
    camera = visual_plan.get('camera', 'orbit')
    """CPU software 3D scene: shaded cube, orbiting spheres, rings and animated camera."""
    from PIL import Image,ImageDraw,ImageFilter
    def rgb(v):
        v=v.replace("0x","").replace("#","")
        return tuple(int(v[i:i+2],16) for i in (0,2,4))
    base,glow=rgb(bg),rgb(accent); sw,sh=480,854
    frames=path.parent/f"frames_{index:03d}"; frames.mkdir(parents=True,exist_ok=True)
    for frame in range(max(1,round(duration*fps))):
        t=frame/fps; ang=t*({'orbit':.42,'push_in':.12,'tracking':.28,'sweep':.62}.get(camera,.42))+index*.7
        zoom=(1+.1*math.sin(t*.65)+.045*math.sin(t*1.4+index)) if camera=='orbit' else (1+.24*t/max(duration,.5) if camera=='push_in' else 1+.12*math.sin(t*1.2))
        im=Image.new("RGB",(sw,sh),tuple(int(v*.72) for v in base))
        d=ImageDraw.Draw(im,"RGBA")
        for p in range(42):
            x=(p*83+t*(12+p%5)*(-1 if p%2 else 1))%sw; y=(p*137+t*(8+p%7))%sh; r=1+p%3
            d.ellipse((x-r,y-r,x+r,y+r),fill=(*glow,75))
        cx,cy,_,center_scale=_project_3d(0,0,0,ang,zoom,sw,sh)
        if motif == "choice_paths":
            # A forked road in perspective; no generic cube or decorative orbit.
            for branch in (-1, 1):
                pts=[]
                for q in range(45):
                    u=q/44
                    x=branch*(.10+2.25*u)
                    y=-1.55+1.55*u
                    z=.15*math.sin(u*math.pi+t*.25)
                    pts.append(_project_3d(x,y,z,ang*.35,zoom,sw,sh)[:2])
                d.line(pts,fill=(*glow,235 if branch > 0 else 145),width=7)
                for q in range(5,42,9):
                    px,py=pts[q]
                    d.ellipse((px-5,py-5,px+5,py+5),fill=(*glow,230))
            d.ellipse((cx-13,cy-13,cx+13,cy+13),fill=(255,245,220,245))
        elif motif == "journey":
            # A winding road leading through a cinematic mountain horizon.
            horizon=int(sh*.48)
            d.polygon([(0,horizon+70),(sw*.22,horizon-80),(sw*.43,horizon+35),
                       (sw*.68,horizon-110),(sw,horizon+55),(sw,sh),(0,sh)],
                      fill=(*glow,48))
            road=[]
            for q in range(42):
                u=q/41
                x=sw*.5+math.sin(u*math.pi*1.6+t*.18)*sw*.22*(1-u)
                y=horizon+u*(sh-horizon+30)
                road.append((x,y))
            d.line(road,fill=(12,17,28,255),width=150)
            d.line(road,fill=(*glow,220),width=5)
            for side in (-1,1):
                edge=[(x+side*(28+u*110),y) for u,(x,y) in enumerate(road)]
                d.line(edge,fill=(235,220,185,190),width=4)
        elif motif == "growth_steps":
            # Perspective staircase built from individually shaded 3D blocks.
            for q in range(7):
                x0=-1.75+q*.52
                y0=-1.10+q*.31
                z0=q*.12
                corners=[(x0,y0,z0),(x0+.48,y0,z0),(x0+.48,y0+.22,z0),
                         (x0,y0+.22,z0),(x0,y0,z0+.22),(x0+.48,y0,z0+.22),
                         (x0+.48,y0+.22,z0+.22),(x0,y0+.22,z0+.22)]
                pts=[_project_3d(*v,ang,zoom,sw,sh)[:2] for v in corners]
                d.polygon([pts[i] for i in (4,5,6,7)],fill=(*glow,min(255,110+q*18)))
                d.polygon([pts[i] for i in (1,2,6,5)],fill=(*glow,min(255,75+q*16)))
                d.polygon([pts[i] for i in (0,1,5,4)],fill=(*glow,min(255,150+q*14)),
                          outline=(255,235,190,220))
        elif motif == "atom":
            # Nucleus and three tilted electron shells with moving electrons.
            for tilt in (0, math.pi/3, -math.pi/3):
                pts=[]
                for q in range(100):
                    a=q*math.tau/99+t*.22
                    x,y,_,_=_project_3d(1.75*math.cos(a),.22*math.sin(a)*math.cos(tilt),
                                       1.35*math.sin(a)*math.sin(tilt),ang,zoom,sw,sh)
                    pts.append((x,y))
                d.line(pts,fill=(*glow,205),width=4)
                a=t*(1.0+tilt*.12)+tilt
                ex,ey,_,_=_project_3d(1.75*math.cos(a),.22*math.sin(a)*math.cos(tilt),
                                       1.35*math.sin(a)*math.sin(tilt),ang,zoom,sw,sh)
                d.ellipse((ex-11,ey-11,ex+11,ey+11),fill=(235,245,255,255))
            d.ellipse((cx-32,cy-32,cx+32,cy+32),fill=(*glow,245),outline=(255,255,255,230),width=4)
        elif motif == "neural_network":
            # Branching synapses and axon links; nodes pulse along the connections.
            nodes=[(-1.8,-.8,-.2),(-1.1,.5,.2),(-.45,-.15,.45),(.25,.8,-.25),
                   (.65,-.65,.3),(1.45,.25,-.15),(1.9,-.55,.4),(-.1,1.35,.1)]
            links=[(0,1),(1,2),(2,3),(2,4),(4,5),(5,6),(3,7),(1,7),(4,7)]
            projected=[_project_3d(*v,ang,zoom,sw,sh) for v in nodes]
            for a,b in links:
                d.line((projected[a][:2],projected[b][:2]),fill=(*glow,185),width=5)
            for n,(x,y,dep,scale) in enumerate(projected):
                pulse=.75+.25*math.sin(t*3+n)
                r=max(8,int(scale*.12*pulse))
                d.ellipse((x-r*2,y-r*2,x+r*2,y+r*2),fill=(*glow,28))
                d.ellipse((x-r,y-r,x+r,y+r),fill=(*glow,245),
                          outline=(245,250,255,235),width=2)
        elif motif == "molecule":
            # Distinct atoms and bonds with depth ordering.
            nodes=[(-1.35,0,0),(-.45,.8,.3),(.55,.65,-.3),(1.35,-.1,.2),(.25,-.85,.4)]
            projected=[_project_3d(*v,ang,zoom,sw,sh) for v in nodes]
            for a,b in ((0,1),(1,2),(2,3),(2,4),(4,0)):
                d.line((projected[a][0:2],projected[b][0:2]),fill=(*glow,225),width=9)
            for n,(x,y,dep,scale) in enumerate(projected):
                r=max(12,int(scale*(.16 if n == 0 else .12)))
                atom_color=(*glow,245) if n == 0 else ((110,190,235,245) if n % 2 else (238,185,105,245))
                d.ellipse((x-r,y-r,x+r,y+r),fill=atom_color,
                          outline=(255,255,255,235),width=3)
        elif motif == "geometry":
            # Rotating wireframe polyhedron and a measured geometric construction.
            verts=[(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),
                   (0,0,1.55),(0,0,-1.55)]
            projected=[_project_3d(*v,ang,zoom,sw,sh) for v in verts]
            edges=[(0,1),(1,2),(2,3),(3,0),(0,4),(1,4),(2,4),(3,4),
                   (0,5),(1,5),(2,5),(3,5)]
            for a,b in edges:
                d.line((projected[a][:2],projected[b][:2]),fill=(*glow,220),width=4)
            for rr in (95,145,195):
                d.ellipse((cx-rr,cy-rr,cx+rr,cy+rr),outline=(*glow,85),width=2)
            d.line((cx-210,cy,cx+210,cy),fill=(240,225,190,135),width=2)
            d.line((cx,cy-260,cx,cy+260),fill=(240,225,190,135),width=2)
        elif motif == "launch":
            # Volumetric portal, rising beam and directional arrow.
            for q in range(5):
                rr=72+q*34+int(9*math.sin(t*2.2+q))
                d.ellipse((cx-rr,cy-rr,cx+rr,cy+rr),
                          outline=(*glow,max(70,230-q*32)),width=4)
            beam_top=cy-210-int(25*math.sin(t*2))
            d.polygon([(cx-13,cy+145),(cx+13,cy+145),(cx+8,beam_top),(cx-8,beam_top)],
                      fill=(*glow,165))
            d.polygon([(cx,beam_top-35),(cx-25,beam_top+8),(cx+25,beam_top+8)],
                      fill=(255,245,215,245))
        else:
            raise ValueError(f"No publishable topic-specific 3D motif for scene: {motif}")
        halo=Image.new("RGBA",(sw,sh),(0,0,0,0)); ImageDraw.Draw(halo).ellipse((cx-135,cy-135,cx+135,cy+135),fill=(*glow,30))
        im=Image.alpha_composite(im.convert("RGBA"),halo.filter(ImageFilter.GaussianBlur(42))).convert("RGB")
        im.save(frames/f"{frame:05d}.jpg",quality=88)
    _run(["ffmpeg","-y","-framerate",str(fps),"-i",str(frames/"%05d.jpg"),"-vf",f"scale={width}:{height}:flags=lanczos,fade=t=in:st=0:d=0.25,fade=t=out:st={max(0,duration-.3):.3f}:d=0.3,format=yuv420p","-t",f"{duration:.3f}","-an","-c:v","libx264","-preset","veryfast","-crf","22","-pix_fmt","yuv420p",str(path)])

def render_project(project: dict[str,Any], output: str|Path, audio: str|Path|None=None) -> Path:
    """Render an MP4 on CPU. No GPU, API key, or network access is used."""
    spec=validate_project(project)
    if not shutil.which("ffmpeg"): raise RuntimeError("FFmpeg is required on the runner")
    out=Path(output).resolve(); out.parent.mkdir(parents=True,exist_ok=True)
    width,height=FORMATS[spec["format"]]; fps=int(project.get("fps",24))
    if fps not in (24,25,30): raise ValueError("fps must be 24, 25, or 30")
    work=out.parent/f".{out.stem}_render"; work.mkdir(parents=True,exist_ok=True); clips=[]
    for index,scene in enumerate(spec["scenes"]):
        duration=scene["duration"]; clip=work/f"scene_{index:03d}.mp4"; bg,accent=PALETTES[index%len(PALETTES)]
        bg=scene["background"] or bg; accent=scene["accent"] or accent
        fadeout=max(0,duration-.3)
        if scene["image"]:
            image_path=Path(scene["image"]).expanduser().resolve()
            if not image_path.is_file(): raise FileNotFoundError(f"Scene image not found: {image_path}")
            vf=(f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},"
                f"zoompan=z='min(zoom+0.0007,1.08)':d={max(1,round(duration*fps))}:s={width}x{height}:fps={fps},"
                f"fade=t=in:st=0:d=0.25,fade=t=out:st={fadeout:.3f}:d=0.3,format=yuv420p")
            cmd=["ffmpeg","-y","-loop","1","-i",str(image_path),"-t",f"{duration:.3f}","-vf",vf,"-an","-c:v","libx264","-preset","veryfast","-crf","23","-pix_fmt","yuv420p",str(clip)]
            _run(cmd)
            clips.append(clip)
            continue
        else:
            from app.bamo_scene_director import plan_scene
            visual_plan = plan_scene(scene.get('narration') or scene['text'], scene.get('visual_prompt', ''))
            _render_3d_scene(clip,duration,width,height,fps,index,bg,accent,visual_plan)
            clips.append(clip)
            continue

    concat=work/"concat.txt"; concat.write_text("".join(f"file '{p.as_posix()}'\n" for p in clips),encoding="utf-8")
    silent=work/"silent.mp4"; _run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(concat),"-c","copy","-an",str(silent)])
    ass=work/"captions.ass"; _write_ass(spec["scenes"],ass,width,height)
    command=["ffmpeg","-y","-i",str(silent)]
    audio_path=Path(audio).expanduser().resolve() if audio else None
    if audio_path:
        if not audio_path.is_file(): raise FileNotFoundError(f"Audio file not found: {audio_path}")
        command += ["-i",str(audio_path),"-vf",f"ass={ass.as_posix()}","-map","0:v:0","-map","1:a:0","-c:a","aac","-b:a","192k","-shortest"]
    else: command += ["-vf",f"ass={ass.as_posix()}","-an"]
    command += ["-c:v","libx264","-preset","veryfast","-crf","21","-pix_fmt","yuv420p","-movflags","+faststart",str(out)]
    _run(command)
    if not out.is_file() or out.stat().st_size<10000: raise RuntimeError("Rendered MP4 is missing or unexpectedly small")
    return out

def load_project(path: str|Path) -> dict[str,Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))
