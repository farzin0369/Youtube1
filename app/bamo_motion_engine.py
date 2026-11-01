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
        clean.append({"duration":duration,"text":str(scene.get("on_screen_text") or scene.get("text") or "").strip(),"image":str(scene.get("image") or "").strip(),"background":str(scene.get("background") or "").strip(),"accent":str(scene.get("accent") or "").strip()})
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

def _render_3d_scene(path,duration,width,height,fps,index,bg,accent):
    """CPU software 3D scene: shaded cube, orbiting spheres, rings and animated camera."""
    from PIL import Image,ImageDraw,ImageFilter
    def rgb(v):
        v=v.replace("0x","").replace("#","")
        return tuple(int(v[i:i+2],16) for i in (0,2,4))
    base,glow=rgb(bg),rgb(accent); sw,sh=480,854
    frames=path.parent/f"frames_{index:03d}"; frames.mkdir(parents=True,exist_ok=True)
    for frame in range(max(1,round(duration*fps))):
        t=frame/fps; ang=t*.42+index*.7; zoom=1+.1*math.sin(t*.65)+.045*math.sin(t*1.4+index)
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
        halo=Image.new("RGBA",(sw,sh),(0,0,0,0)); ImageDraw.Draw(halo).ellipse((cx-135,cy-135,cx+135,cy+135),fill=(*glow,30))
        im=Image.alpha_composite(im.convert("RGBA"),halo.filter(ImageFilter.GaussianBlur(42))).convert("RGB")
        im.save(frames/f"{frame:05d}.jpg",quality=88)
    _run(["ffmpeg","-y","-framerate",str(fps),"-i",str(frames/"%05d.jpg"),"-vf",f"scale={width}:{height}:flags=lanczos,fade=t=in:st=0:d=0.25,fade=t=out:st={max(0,duration-.3):.3f}:d=0.3,format=yuv420p","-t",f"{duration:.3f}","-an","-c:v","libx264","-preset","veryfast","-crf","22","-pix_fmt","yuv420p",str(path)])
\ndef render_project(project: dict[str,Any], output: str|Path, audio: str|Path|None=None) -> Path:
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
            _render_3d_scene(clip,duration,width,height,fps,index,bg,accent)
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
