"""CPU-only Blender scene builder for BAMO's cinematic 3D motion engine.

Invoked by Blender's bundled Python, not the repository's system Python.
"""
from __future__ import annotations

import json
import math
import os
import sys

import bpy
from mathutils import Vector

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from bamo_blender_primitives import material, add_camera, lighting, ground
from bamo_blender_motifs_a import scene_choice, scene_journey, scene_growth, scene_atom, scene_neural, scene_molecule, scene_geometry, scene_launch, scene_notebook, scene_sunrise, scene_starfield, scene_cosmic_shells
from bamo_blender_motifs_b import scene_expanding_spacetime, scene_cosmic_web, scene_neon_ellipse, scene_wave_interference, scene_from_ai_graph

def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    config_path, output_dir = args[0], args[1]
    cfg = json.load(open(config_path, encoding="utf-8"))
    os.makedirs(output_dir, exist_ok=True)

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    width, height = int(cfg["width"]), int(cfg["height"])
    fps = int(cfg["fps"])
    frames = max(1, int(cfg["frame_count"]))
    motif = str(cfg["motif"])
    camera_style = str(cfg["camera"])
    scene_graph = cfg.get("scene_graph")
    camera_angle = "eye"

    # Premium dark-stage palette with warm metallic highlights and cool rim light.
    gold = material("BAMO warm gold", (0.82, 0.48, 0.12), 0.72, 0.22, 0.55)
    blue = material("BAMO electric blue", (0.055, 0.34, 0.72), 0.55, 0.24, 0.35)
    dark = material("BAMO midnight stage", (0.012, 0.022, 0.045), 0.25, 0.36, 0.0)

    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = int(cfg.get("samples", 24))
    # Denoise only when the installed Blender build actually ships OpenImageDenoise.
    # Ubuntu/GitHub Actions packages often omit it; enabling denoise then aborts the render.
    want_denoise = bool(cfg.get("denoise", True))
    denoise_ok = False
    if want_denoise:
        try:
            scene.cycles.denoiser = "OPENIMAGEDENOISE"
            scene.cycles.use_denoising = True
            denoise_ok = True
        except (AttributeError, TypeError, ValueError, RuntimeError):
            denoise_ok = False
    if not denoise_ok:
        try:
            scene.cycles.use_denoising = False
        except Exception:
            pass
    scene.render.threads_mode = "FIXED"
    scene.render.threads = int(cfg.get("threads", 2))
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = int(cfg.get("resolution_percentage", 100))
    scene.render.fps = fps
    scene.frame_start = 1
    scene.frame_end = frames
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.filepath = os.path.join(output_dir, "frame_")
    scene.render.film_transparent = False
    try:
        scene.view_settings.view_transform = "AgX"
    except TypeError:
        scene.view_settings.view_transform = "Filmic"
    scene.use_nodes = True
    compositor = scene.node_tree
    compositor.nodes.clear()
    render_layers = compositor.nodes.new("CompositorNodeRLayers")
    glow = compositor.nodes.new("CompositorNodeGlare")
    glow.glare_type = "FOG_GLOW"
    glow.threshold = 1.25
    glow.quality = "HIGH"
    composite = compositor.nodes.new("CompositorNodeComposite")
    compositor.links.new(render_layers.outputs["Image"], glow.inputs["Image"])
    compositor.links.new(glow.outputs["Image"], composite.inputs["Image"])
    scene.render.image_settings.color_depth = "8"
    scene.render.use_file_extension = True

    lighting((1.0, 0.68, 0.32), (0.18, 0.48, 1.0))
    if motif == "ai_scene":
        if not isinstance(scene_graph, dict): raise RuntimeError("AI scene graph missing from Blender render config")
        camera_style = scene_from_ai_graph(scene_graph, frames)
        camera_angle = scene_graph.get("camera", {}).get("angle", "eye")
    elif motif == "choice_paths":
        scene_choice(gold, blue, dark, frames)
    elif motif == "journey":
        scene_journey(gold, blue, dark, frames)
    elif motif == "growth_steps":
        scene_growth(gold, blue, dark, frames)
    elif motif == "notebook":
        scene_notebook(gold, blue, dark, frames)
    elif motif == "atom":
        scene_atom(gold, blue, dark, frames)
    elif motif == "neural_network":
        scene_neural(gold, blue, dark, frames)
    elif motif == "molecule":
        scene_molecule(gold, blue, dark, frames)
    elif motif == "geometry":
        scene_geometry(gold, blue, dark, frames)
    elif motif == "launch":
        scene_launch(gold, blue, dark, frames)
    elif motif == "sunrise":
        scene_sunrise(gold, blue, dark, frames)
    elif motif == "starfield":
        scene_starfield(gold, blue, dark, frames)
    elif motif == "cosmic_shells":
        scene_cosmic_shells(gold, blue, dark, frames)
    elif motif == "expanding_spacetime":
        scene_expanding_spacetime(gold, blue, dark, frames)
    elif motif == "neon_ellipse_mesh":
        scene_neon_ellipse(gold, blue, dark, frames)
    elif motif == "wave_interference":
        scene_wave_interference(gold, blue, dark, frames)
    elif motif == "cosmic_web":
        scene_cosmic_web(gold, blue, dark, frames)
    else:
        raise RuntimeError("No cinematic Blender scene builder exists for motif: " + motif)

    add_camera(frames, camera_style, camera_angle)
    scene.frame_set(1)
    bpy.ops.render.render(animation=True)


if __name__ == "__main__":
    main()
