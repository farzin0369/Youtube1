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
        clean.append({"duration":duration,"text":str(scene.get("on_screen_text") or scene.get("text") or "").strip(),"image":str(scene.get("image") or "").strip(),"background":str(scene.get("background") or "").strip(),"accent":str(scene.get("accent") or "").strip(),"visual_prompt":str(scene.get("visual_prompt") or "").strip(),"visual_plan":scene.get("visual_plan") if isinstance(scene.get("visual_plan"),dict) else None,"narration":str(scene.get("narration") or "").strip()})
    return {"format":fmt,"scenes":clean}

def _ass_time(seconds: float) -> str:
    total=max(0,int(round(seconds*100))); hours,rem=divmod(total,360000); minutes,rem=divmod(rem,6000); secs,centis=divmod(rem,100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"

def _ass_escape(value: str) -> str:
    return value.replace("\\",r"\\").replace("{",r"\{").replace("}",r"\}").replace("\n",r"\N")

def _write_ass(scenes: list[dict[str,Any]], path: Path, width: int, height: int, caption_events: list[dict[str,Any]]|None=None) -> None:
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
    events=[]
    if caption_events is not None:
        for caption in caption_events:
            start=float(caption["start"]); end=float(caption["end"]); text=str(caption["text"]).strip()
            if end<=start or not text: continue
            events.append(f"Dialogue: 0,{_ass_time(start)},{_ass_time(end)},Brand,,0,0,0,,BAMO  •  #12bamo")
            events.append(f"Dialogue: 1,{_ass_time(start)},{_ass_time(end)},Main,,0,0,0,,{{\\fad(90,110)}}{_ass_escape(text)}")
    else:
        cursor=0.0
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
        verts=[_project_3d(x*.82,y*.82,z*.82,ang+t*.28,zoom,sw,sh) for x,y,z in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
        faces=[((0,1,2,3),.4),((4,5,6,7),.72),((0,1,5,4),.58),((2,3,7,6),.82),((1,2,6,5),.95),((0,3,7,4),.3)]; items=[]
        for face,light in faces:
            pts=[(verts[q][0],verts[q][1]) for q in face]; shade=tuple(int(v*light) for v in glow)
            items.append((sum(verts[q][2] for q in face)/4,"poly",pts,(*shade,215)))
        for j in range(3):
            ph=t*(.85+j*.16)+j*2.1+index; sx,sy,dep,sc=_project_3d(1.65*math.cos(ph),.72*math.sin(ph*1.3),1.55*math.sin(ph),ang,zoom,sw,sh)
            r=max(5,int(sc*(.24 if j else .31))); col=(*glow,235) if j==0 else ((105,175,220,230) if j==1 else (225,170,95,230))
            items.append((dep,"sphere",(sx,sy,r),col))
        for _,kind,data,col in sorted(items,key=lambda a:a[0],reverse=True):
            if kind=="poly":
                d.polygon(data,fill=col); d.line(data+[data[0]],fill=(235,220,190,200),width=2)
            else:
                sx,sy,r=data
                for q in range(r,0,-1):
                    shade=tuple(int(min(255, v * (0.34 + 0.82 * (1 - q / r * 0.55)))) for v in col[:3])
                    d.ellipse((sx-q,sy-q,sx+q,sy+q),fill=(*shade,col[3]))
                d.ellipse((sx-r*.48,sy-r*.62,sx-r*.08,sy-r*.22),fill=(255,255,255,125))
        cx,cy,_,_=_project_3d(0,0,0,ang,zoom,sw,sh)
        for rr in (1.65,2):
            pts=[]
            for q in range(65):
                a=q*math.tau/64+t*.25; xx,yy,_,_=_project_3d(rr*math.cos(a),.25*math.sin(a),rr*math.sin(a),ang,zoom,sw,sh); pts.append((xx,yy))
            d.line(pts,fill=(*glow,110),width=2)
        if motif in ("choice_paths", "journey"):
            for branch in (-1, 1):
                pts=[]
                for q in range(30):
                    u=q/29; px,py,_,_=_project_3d(branch*(.12+1.9*u),-.75+1.15*u,.35*math.sin(u*math.pi),ang,zoom,sw,sh)
                    pts.append((px,py))
                d.line(pts,fill=(*glow,220 if branch==1 else 125),width=5)
                ex,ey=pts[-1]; d.ellipse((ex-7,ey-7,ex+7,ey+7),fill=(*glow,240))
        elif motif in ("growth_steps", "progress"):
            for q in range(6):
                x0=-1.8+q*.55; y0=-.8+q*.27
                corners=[(x0,y0,0),(x0+.48,y0,0),(x0+.48,y0+.22,0),(x0,y0+.22,0)]
                pts=[_project_3d(*v,ang,zoom,sw,sh)[:2] for v in corners]
                d.polygon(pts,fill=(*glow,95+q*22),outline=(*glow,230))
        elif motif == "astronomy":
            # Distinct planetary scene: luminous central star, orbit tracks and orbiting planets.
            star_r=25+int(4*math.sin(t*2.1))
            for ring in (1,2,3):
                rr=72+ring*57
                pts=[]
                for q in range(121):
                    a=q*math.tau/120+t*(.12+ring*.035)
                    x,y,_,_=_project_3d((rr/100)*math.cos(a),.10*math.sin(a*2),(rr/100)*math.sin(a),ang,zoom,sw,sh)
                    pts.append((x,y))
                d.line(pts,fill=(*glow,105+ring*22),width=2)
                a=t*(.55/ring)+ring*1.7
                px,py,_,ps=_project_3d((rr/100)*math.cos(a),.10*math.sin(a*2),(rr/100)*math.sin(a),ang,zoom,sw,sh)
                pr=max(5,int(ps*(.11+ring*.018)))
                d.ellipse((px-pr,py-pr,px+pr,py+pr),fill=(105+ring*35,170+ring*15,235,245),outline=(255,255,255,210),width=2)
            d.ellipse((cx-star_r,cy-star_r,cx+star_r,cy+star_r),fill=(255,205,105,250),outline=(255,245,205,255),width=3)
        elif motif == "science":
            # Animated wavefronts and field vectors, rather than decorative orbital rings.
            for ring in range(1,7):
                rr=ring*27+int((t*42)%27)
                d.arc((cx-rr,cy-rr,cx+rr,cy+rr),start=195,end=345,fill=(*glow,max(45,220-ring*25)),width=3)
            for q in range(13):
                x=35+q*34
                phase=t*3+q*.42
                pts=[(x,sh*.5+math.sin(k/8+phase)*38) for k in range(100)]
                d.line(pts,fill=(*glow,190),width=2)
            for q in range(9):
                x=45+q*48
                y=sh*.5+math.sin(t*2+q*.6)*35
                d.line((x,y-24,x,y+24),fill=(210,225,245,180),width=2)
                d.polygon([(x,y+30),(x-6,y+18),(x+6,y+18)],fill=(210,225,245,210))
        elif motif == "geometry":
            # Parametric construction: a moving curve over a perspective coordinate lattice.
            for q in range(-5,6):
                pts=[]
                for k in range(41):
                    u=k/40
                    x,y,_,_=_project_3d(q*.34,-1.65+u*3.3,0,ang,zoom,sw,sh)
                    pts.append((x,y))
                d.line(pts,fill=(*glow,95),width=1)
                pts=[]
                for k in range(41):
                    u=k/40
                    x,y,_,_=_project_3d(-1.7+u*3.4,q*.30,0,ang,zoom,sw,sh)
                    pts.append((x,y))
                d.line(pts,fill=(*glow,95),width=1)
            curve=[]
            for q in range(181):
                u=q/180*math.tau*1.5
                x,y,_,_=_project_3d(1.25*math.cos(u),.72*math.sin(2*u+t*.8),.45*math.sin(u),ang,zoom,sw,sh)
                curve.append((x,y))
            d.line(curve,fill=(245,225,170,245),width=4)
            for q in range(0,181,18):
                x,y=curve[q]
                d.ellipse((x-4,y-4,x+4,y+4),fill=(*glow,245))
        elif motif in ("atom",):
            for tilt in (0, math.pi/3, -math.pi/3):
                pts=[]
                for q in range(90):
                    a=q*math.tau/89+t*.35
                    x,y,_,_=_project_3d(2.05*math.cos(a),.72*math.sin(a)*math.cos(tilt),1.5*math.sin(a)*math.sin(tilt),ang,zoom,sw,sh)
                    pts.append((x,y))
                d.line(pts,fill=(*glow,190),width=3)
        elif motif in ("molecule", "chemistry"):
            nodes=[(-1.35,0,0),(-.45,.8,.3),(.55,.65,-.3),(1.35,-.1,.2),(.25,-.85,.4)]
            projected=[_project_3d(*v,ang,zoom,sw,sh) for v in nodes]
            for a,b in ((0,1),(1,2),(2,3),(2,4),(4,0)):
                d.line((projected[a][0:2],projected[b][0:2]),fill=(*glow,220),width=5)
            for x,y,dep,sc in projected:
                r=max(7,int(sc*.18)); d.ellipse((x-r,y-r,x+r,y+r),fill=(*glow,235),outline=(255,255,255,230),width=2)
        elif motif == "launch":
            for q in range(4):
                rr=65+q*38+int(10*math.sin(t*2+q))
                d.ellipse((cx-rr,cy-rr,cx+rr,cy+rr),outline=(*glow,max(65,210-q*35)),width=3)
            d.line((cx,cy+100,cx,cy-105),fill=(*glow,245),width=7)
            d.polygon([(cx,cy-125),(cx-20,cy-90),(cx+20,cy-90)],fill=(*glow,245))
        halo=Image.new("RGBA",(sw,sh),(0,0,0,0)); ImageDraw.Draw(halo).ellipse((cx-135,cy-135,cx+135,cy+135),fill=(*glow,30))
        im=Image.alpha_composite(im.convert("RGBA"),halo.filter(ImageFilter.GaussianBlur(42))).convert("RGB")
        im.save(frames/f"{frame:05d}.jpg",quality=88)
    _run(["ffmpeg","-y","-framerate",str(fps),"-i",str(frames/"%05d.jpg"),"-vf",f"scale={width}:{height}:flags=lanczos,fade=t=in:st=0:d=0.25,fade=t=out:st={max(0,duration-.3):.3f}:d=0.3,format=yuv420p","-t",f"{duration:.3f}","-an","-c:v","libx264","-preset","veryfast","-crf","22","-pix_fmt","yuv420p",str(path)])

def render_project(project: dict[str,Any], output: str|Path, audio: str|Path|None=None, timeline: dict[str,Any]|None=None) -> Path:
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
            visual_plan = scene.get("visual_plan") or plan_scene(scene.get('narration') or scene['text'], scene.get('visual_prompt', ''))
            _render_3d_scene(clip,duration,width,height,fps,index,bg,accent,visual_plan)
            clips.append(clip)
            continue

    concat=work/"concat.txt"; concat.write_text("".join(f"file '{p.as_posix()}'\n" for p in clips),encoding="utf-8")
    silent=work/"silent.mp4"; _run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(concat),"-c","copy","-an",str(silent)])
    ass=work/"captions.ass"; _write_ass(spec["scenes"],ass,width,height,(timeline or {}).get("captions"))
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

def render_omnivision_pipeline(pipeline: dict[str,Any], output: str|Path) -> Path:
    """Render a validated Omnivision graph/timeline with measured caption timecodes."""
    if not isinstance(pipeline,dict) or pipeline.get("schema")!="bamo.omnivision-pipeline/1.0":
        raise ValueError("A compiled BAMO Omnivision pipeline is required")
    graph=pipeline.get("graph") or {}; timeline=pipeline.get("timeline") or {}
    if not pipeline.get("validation",{}).get("ok") or not graph.get("scenes") or not timeline.get("validation",{}).get("ok"):
        raise ValueError("Omnivision graph and measured timeline must both be validated")
    scenes=[]; cursor=0.0
    motif_map={"planet":"astronomy","accretion-disc":"astronomy","star-cluster":"astronomy","nebula":"astronomy",
      "wavefront":"science","field-lines":"science","particle-stream":"science","force-vector":"science",
      "parametric-curve":"geometry","coordinate-lattice":"geometry","polyhedron":"geometry","equation-field":"geometry",
      "molecule":"molecule","orbital-cloud":"atom","reaction-vessel":"chemistry","crystal-lattice":"geometry",
      "monument":"journey","terrain-relief":"journey","artifact":"geometry","city-silhouette":"journey",
      "hero-character":"abstract","comic-prop":"abstract","reaction-pose":"abstract","stage-set":"abstract"}
    camera_map={"orbit":"orbit","push_in":"push_in","tracking":"tracking","sweep":"sweep"}
    for index,scene in enumerate(graph["scenes"]):
        start=float(scene["start"]); end=float(scene["end"])
        if start<cursor-.02 or end<=start: raise ValueError("Omnivision scene timecodes overlap or are invalid")
        if start>cursor+.02:
            scenes.append({"duration":start-cursor,"text":"","narration":"","visual_plan":{"motif":"abstract","camera":"orbit","description":"A quiet transition preserving the measured narration pause."}})
        subject=(scene.get("visual") or {}).get("subject","")
        camera_keys=((scene.get("animation") or {}).get("camera") or [])
        camera="push_in"
        if len(camera_keys)>1:
            first=camera_keys[0].get("position",[0,0,0]); last=camera_keys[-1].get("position",[0,0,0])
            delta=sum((float(last[i])-float(first[i]))**2 for i in range(min(len(first),len(last))))
            camera="sweep" if delta>8 else "tracking"
        visual_plan={"motif":motif_map.get(subject,"abstract"),"camera":camera_map.get(camera,camera),
          "description":(scene.get("visual") or {}).get("semanticPrompt","")}
        scenes.append({"duration":end-start,"text":"","narration":scene.get("narration",""),
          "visual_prompt":(scene.get("visual") or {}).get("semanticPrompt",""),"visual_plan":visual_plan})
        cursor=end
    project={"format":"short" if graph.get("aspect")=="9:16" else "long","fps":int(graph.get("fps",24)),"scenes":scenes}
    audio_path=(pipeline.get("audio") or {}).get("path")
    if not audio_path: raise ValueError("The pipeline must include the measured TTS audio path")
    return render_project(project,output,audio=audio_path,timeline=timeline)


def load_project(path: str|Path) -> dict[str,Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))
