"""CPU-first Blender 3D motion renderer and FFmpeg compositor for BAMO.

Every generated scene is a real Blender 3D scene rendered on CPU. Missing Blender
or unsupported subject motifs are hard failures; there is no flat-shape fallback.
"""
from __future__ import annotations
import json, math, os, shutil, subprocess
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
    """Render a genuine animated Blender scene on CPU; never fall back to 2D primitives."""
    visual_plan = visual_plan or {}
    motif = str(visual_plan.get("motif") or "abstract")
    camera = str(visual_plan.get("camera") or "orbit")
    blender = shutil.which("blender")
    if not blender:
        raise RuntimeError("Blender is required for production 3D rendering; no procedural fallback is permitted.")

    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "bamo_blender_scene.py"
    if not script.is_file():
        raise FileNotFoundError("BAMO Blender scene builder is missing: " + str(script))

    frame_count = max(1, round(float(duration) * int(fps)))
    frames_dir = path.parent / f"frames_{index:03d}"
    if frames_dir.exists():
        shutil.rmtree(frames_dir)
    frames_dir.mkdir(parents=True, exist_ok=True)
    config_path = path.parent / f"blender_scene_{index:03d}.json"
    config = {
        "width": int(width), "height": int(height), "fps": int(fps),
        "frame_count": frame_count, "motif": motif, "camera": camera,
        "samples": int(os.getenv("BAMO_BLENDER_SAMPLES", "24")),
        "threads": int(os.getenv("BAMO_BLENDER_THREADS", "2")),
        "resolution_percentage": int(os.getenv("BAMO_BLENDER_RESOLUTION_PERCENTAGE", "100")),
    }
    config_path.write_text(json.dumps(config), encoding="utf-8")
    command = [
        blender, "--background", "--factory-startup", "--python", str(script),
        "--", str(config_path), str(frames_dir),
    ]
    result = subprocess.run(
        command, capture_output=True, text=True,
        timeout=max(900, int(float(duration) * int(fps) * 3.0)),
    )
    if result.returncode:
        raise RuntimeError("Blender CPU render failed: " + (result.stderr or result.stdout)[-5000:])
    first_frame = frames_dir / "frame_0001.png"
    if not first_frame.is_file():
        raise RuntimeError("Blender completed without producing the expected PNG frame sequence")

    fadeout = max(0.0, float(duration) - 0.3)
    _run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-framerate", str(fps), "-start_number", "1",
        "-i", str(frames_dir / "frame_%04d.png"),
        "-vf", f"scale={width}:{height}:flags=lanczos,fade=t=in:st=0:d=0.25,"
               f"fade=t=out:st={fadeout:.3f}:d=0.3,format=yuv420p",
        "-t", f"{float(duration):.3f}", "-an",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-pix_fmt", "yuv420p", str(path),
    ], timeout=max(900, int(float(duration) * 18)))

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
