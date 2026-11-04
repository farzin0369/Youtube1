#!/usr/bin/env python3
"""Apply quality patches to Blender/render stack (idempotent)."""
from __future__ import annotations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def patch_motion_engine() -> None:
    path = ROOT / "app" / "bamo_motion_engine.py"
    t = path.read_text(encoding="utf-8")
    t = t.replace(
        "Style: Main,Noto Naskh Arabic,{hero_size},&H00FFFFFF,&H000000FF,&HCC080C16,&H88000000,1,0,0,0,100,100,0,0,1,4,2,5,{margin},{margin},{int(height*.10)},1\n"
        "Style: Brand,Noto Naskh Arabic,{brand_size},&H00D5A64B,&H000000FF,&HCC080C16,&H88000000,1,0,0,0,100,100,0,0,1,2,1,8,{margin},{margin},{int(height*.06)},1",
        "Style: Main,Noto Naskh Arabic,{hero_size},&H00FFFFFF,&H000000FF,&HAA0A0F1A,&H99000000,1,0,0,0,100,100,0,0,1,2,3,2,{margin},{margin},{int(height*.12)},1\n"
        "Style: Brand,Noto Naskh Arabic,{brand_size},&H00D5A64B,&H000000FF,&HAA0A0F1A,&H99000000,1,0,0,0,100,100,0,0,1,1,2,8,{margin},{margin},{int(height*.05)},1",
    )
    t = t.replace('"samples": int(os.getenv("BAMO_BLENDER_SAMPLES", "24"))', '"samples": int(os.getenv("BAMO_BLENDER_SAMPLES", "48"))')
    t = t.replace('"film_grain": float(os.getenv("BAMO_BLENDER_FILM_GRAIN", "0.035"))', '"film_grain": float(os.getenv("BAMO_BLENDER_FILM_GRAIN", "0.0"))')
    if '"seed"' not in t:
        t = t.replace(
            '"cinematic_effects": os.getenv("BAMO_CINEMATIC_EFFECTS", "true").lower() == "true",',
            '"cinematic_effects": os.getenv("BAMO_CINEMATIC_EFFECTS", "true").lower() == "true",\n'
            '        "seed": int(os.getenv("BAMO_BLENDER_SEED", "17")),\n'
            '        "exposure": float(os.getenv("BAMO_BLENDER_EXPOSURE", "-0.35")),\n'
            '        "clamp_indirect": float(os.getenv("BAMO_BLENDER_CLAMP_INDIRECT", "3.0")),',
        )
    if "loudnorm=I=-14" not in t:
        old = (
            '        command += ["-i",str(audio_path),"-vf",f"ass={ass.as_posix()}","-map","0:v:0","-map","1:a:0","-c:a","aac","-b:a","192k","-shortest"]\n'
            '    else: command += ["-vf",f"ass={ass.as_posix()}","-an"]\n'
            '    command += ["-c:v","libx264","-preset","veryfast","-crf","19","-pix_fmt","yuv420p","-movflags","+faststart",str(out)]\n'
        )
        new = (
            '        af = (\n'
            '            "silenceremove=start_periods=1:start_silence=0.05:start_threshold=-40dB,"\n'
            '            "aformat=channel_layouts=stereo,"\n'
            '            "loudnorm=I=-14:TP=-1.5:LRA=11,"\n'
            '            "afade=t=in:st=0:d=0.15,afade=t=out:d=0.2"\n'
            '        )\n'
            '        command += ["-i",str(audio_path),"-vf",f"ass={ass.as_posix()}","-af",af,"-map","0:v:0","-map","1:a:0","-c:a","aac","-b:a","192k","-ac","2","-shortest"]\n'
            '    else: command += ["-vf",f"ass={ass.as_posix()}","-an"]\n'
            '    command += ["-c:v","libx264","-preset","medium","-crf","17","-pix_fmt","yuv420p","-colorspace","bt709","-color_primaries","bt709","-color_trc","bt709","-movflags","+faststart",str(out)]\n'
        )
        if old in t:
            t = t.replace(old, new, 1)
    path.write_text(t, encoding="utf-8")
    compile(t, str(path), "exec")
    print("motion_engine patched")


def patch_motifs() -> None:
    path = ROOT / "scripts" / "bamo_blender_motifs_b.py"
    t = path.read_text(encoding="utf-8")
    t = t.replace("key.data.energy = 1600", "key.data.energy = 950")
    t = t.replace(
        '"key": material("AI Director key", colors["key"], 0.55, 0.18, 1.8),\n'
        '        "accent": _emission_mat("AI Director accent", colors["accent"], strength=5.5),\n'
        '        "neutral": material("AI Director neutral", colors["neutral"], 0.2, 0.32, 0.15),\n'
        '        "dark": material("AI Director dark", colors["dark"], 0.08, 0.55, 0.0),',
        '"key": material("AI Director key", colors["key"], 0.35, 0.22, 0.35),\n'
        '        "accent": material("AI Director accent", colors["accent"], 0.15, 0.28, 0.55),\n'
        '        "neutral": material("AI Director neutral", colors["neutral"], 0.15, 0.38, 0.05),\n'
        '        "dark": material("AI Director dark", colors["dark"], 0.05, 0.62, 0.0),',
    )
    t = t.replace("samples = max(12, min(frames, 48))", "samples = max(24, min(frames, 96))")
    t = t.replace("node.threshold = 0.55", "node.threshold = 0.92")
    if "glass_" not in t:
        needle = '        assign(obj, mats[item["material"]])\n        smooth(obj)\n'
        insert = (
            '        oid = str(item.get("id") or "").lower()\n'
            '        role = str(item.get("role") or "").lower()\n'
            '        mat = mats[item["material"]]\n'
            '        if "oxygen" in oid or "oxygen" in role:\n'
            '            mat = material(f"glass_{oid}", (0.55, 0.12, 0.12), 0.0, 0.08, 0.15)\n'
            '        elif "hydrogen" in oid or "hydrogen" in role:\n'
            '            mat = material(f"h_{oid}", (0.92, 0.94, 0.98), 0.0, 0.45, 0.08)\n'
            '        elif "bond" in oid or "bond" in role:\n'
            '            mat = material(f"metal_{oid}", (0.75, 0.78, 0.82), 0.85, 0.22, 0.0)\n'
            '        elif "focus" in oid or "source" in oid:\n'
            '            mat = material(f"focus_{oid}", (0.95, 0.72, 0.22), 0.4, 0.25, 0.45)\n'
            '        assign(obj, mat)\n'
            '        smooth(obj)\n'
        )
        if needle in t:
            t = t.replace(needle, insert, 1)
    path.write_text(t, encoding="utf-8")
    compile(t, str(path), "exec")
    print("motifs patched")


def patch_primitives() -> None:
    path = ROOT / "scripts" / "bamo_blender_primitives.py"
    t = path.read_text(encoding="utf-8")
    t = t.replace("camera.data.dof.aperture_fstop = 3.6", "camera.data.dof.aperture_fstop = 5.6")
    t = t.replace("key.data.energy = 1250", "key.data.energy = 900")
    t = t.replace("fill.data.energy = 900", "fill.data.energy = 550")
    if "min(float(emission)" not in t:
        t = t.replace(
            '    if "Emission Strength" in bsdf.inputs:\n        bsdf.inputs["Emission Strength"].default_value = emission\n',
            '    if "Emission Strength" in bsdf.inputs:\n        bsdf.inputs["Emission Strength"].default_value = min(float(emission), 1.2)\n',
        )
    path.write_text(t, encoding="utf-8")
    compile(t, str(path), "exec")
    print("primitives patched")


def main() -> int:
    patch_motion_engine()
    patch_motifs()
    patch_primitives()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
