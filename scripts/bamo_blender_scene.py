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
from bamo_blender_motifs_a import (
    scene_choice, scene_journey, scene_growth, scene_atom, scene_neural,
    scene_molecule, scene_geometry, scene_launch, scene_notebook, scene_sunrise,
    scene_starfield, scene_cosmic_shells,
)
from bamo_blender_motifs_b import scene_from_ai_graph

def _setup_cinematic_compositor(scene, cfg):
    """Bloom + mild chromatic aberration. Avoid Texture nodes (fragile on headless)."""
    scene.use_nodes = True
    tree = scene.node_tree
    tree.nodes.clear()
    render_layers = tree.nodes.new("CompositorNodeRLayers")
    render_layers.location = (-500, 0)

    last = render_layers.outputs["Image"]

    glare = tree.nodes.new("CompositorNodeGlare")
    glare.glare_type = "FOG_GLOW"
    glare.threshold = 0.7
    glare.quality = "MEDIUM"
    try:
        glare.size = 7
    except Exception:
        pass
    glare.location = (-250, 40)
    tree.links.new(last, glare.inputs["Image"])
    last = glare.outputs["Image"]

    if cfg.get("cinematic_effects", True):
        ca = float(cfg.get("chromatic_aberration") or 0.0)
        if ca > 0.0:
            try:
                sep = tree.nodes.new("CompositorNodeSepRGBA")
                sep.location = (-50, 100)
                tree.links.new(last, sep.inputs["Image"])
                blur_r = tree.nodes.new("CompositorNodeBlur")
                blur_r.filter_type = "FAST_GAUSS"
                blur_r.size_x = max(1, int(ca * 600))
                blur_r.size_y = 0
                blur_r.location = (150, 180)
                tree.links.new(sep.outputs["R"], blur_r.inputs["Image"])
                blur_b = tree.nodes.new("CompositorNodeBlur")
                blur_b.filter_type = "FAST_GAUSS"
                blur_b.size_x = max(1, int(ca * 600))
                blur_b.size_y = 0
                blur_b.location = (150, 20)
                tree.links.new(sep.outputs["B"], blur_b.inputs["Image"])
                comb = tree.nodes.new("CompositorNodeCombRGBA")
                comb.location = (350, 100)
                tree.links.new(blur_r.outputs["Image"], comb.inputs["R"])
                tree.links.new(sep.outputs["G"], comb.inputs["G"])
                tree.links.new(blur_b.outputs["Image"], comb.inputs["B"])
                tree.links.new(sep.outputs["A"], comb.inputs["A"])
                last = comb.outputs["Image"]
            except Exception:
                # Keep bloom-only path if CA nodes are unavailable on this Blender build.
                pass

        grain_amt = float(cfg.get("film_grain") or 0.0)
        if grain_amt > 0.0:
            try:
                # Soft contrast lift as a deterministic grain substitute on CPU builds
                # without reliable procedural texture compositing.
                bright = tree.nodes.new("CompositorNodeBrightContrast")
                bright.inputs["Bright"].default_value = 0.0
                bright.inputs["Contrast"].default_value = min(0.12, grain_amt * 2.0)
                bright.location = (520, 40)
                tree.links.new(last, bright.inputs["Image"])
                last = bright.outputs["Image"]
            except Exception:
                pass

    composite = tree.nodes.new("CompositorNodeComposite")
    composite.location = (740, 0)
    tree.links.new(last, composite.inputs["Image"])


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

    gold = material("BAMO warm gold", (0.82, 0.48, 0.12), 0.72, 0.22, 0.55)
    blue = material("BAMO electric blue", (0.055, 0.34, 0.72), 0.55, 0.24, 0.35)
    dark = material("BAMO midnight stage", (0.012, 0.022, 0.045), 0.25, 0.36, 0.0)

    scene = bpy.context.scene
    render_engine = str(cfg.get("render_engine", "BLENDER_WORKBENCH")).upper()
    if render_engine not in {"BLENDER_WORKBENCH", "CYCLES"}:
        raise RuntimeError("Unsupported BAMO render engine: " + render_engine)
    scene.render.engine = render_engine
    if render_engine == "CYCLES":
        scene.cycles.device = "CPU"
        scene.cycles.samples = int(cfg.get("samples", 24))
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
            scene.cycles.use_denoising = False
    else:
        # Workbench is Blender's real 3D raster renderer: fast, deterministic,
        # CPU-friendly, and suitable for the neon motion-graphics scene grammar.
        # It preserves meshes, materials, camera animation, shadows, cavity and
        # compositor bloom without the path-tracing cost that timed out CI.
        shading = scene.display.shading
        shading.light = "STUDIO"
        shading.studio_light = "paint.sl"
        shading.color_type = "MATERIAL"
        shading.show_shadows = True
        shading.show_cavity = True
        shading.cavity_type = "BOTH"
        shading.cavity_ridge_factor = 1.35
        shading.cavity_valley_factor = 1.1
        shading.show_specular_highlight = True

    use_mb = bool(cfg.get("motion_blur", False))
    scene.render.use_motion_blur = use_mb
    if use_mb:
        scene.render.motion_blur_shutter = 0.45
        try:
            scene.cycles.motion_blur_position = "CENTER"
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
    scene.render.filepath = os.path.join(output_dir, "frame_0001")
    scene.render.film_transparent = False
    try:
        scene.view_settings.view_transform = "AgX"
    except TypeError:
        scene.view_settings.view_transform = "Filmic"
    scene.render.image_settings.color_depth = "8"
    scene.render.use_file_extension = True

    try:
        _setup_cinematic_compositor(scene, cfg)
    except Exception as exc:
        # Never hard-fail the render on compositor setup; fall back to direct composite.
        scene.use_nodes = True
        tree = scene.node_tree
        tree.nodes.clear()
        rl = tree.nodes.new("CompositorNodeRLayers")
        comp = tree.nodes.new("CompositorNodeComposite")
        tree.links.new(rl.outputs["Image"], comp.inputs["Image"])
        print("compositor fallback:", exc)

    lighting((1.0, 0.68, 0.32), (0.18, 0.48, 1.0))
    if motif == "ai_scene":
        if not isinstance(scene_graph, dict):
            raise RuntimeError("AI scene graph missing from Blender render config")
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
    else:
        ground(dark)
        from bamo_blender_primitives import sphere, torus
        sphere("Focus sphere", (0, 0, 1.2), 0.8, gold)
        torus("Accent ring", (0, 0, 1.2), 1.6, 0.04, blue, (math.pi / 2, 0, 0))

    add_camera(frames, camera_style, camera_angle)
    scene.frame_set(1)
    # Frame checkpoints make a timed-out runner resumable: valid frames are kept,
    # corrupt/empty frames are rendered again, and the process never starts over
    # from frame 1 after a transient failure.
    for frame in range(1, frames + 1):
        frame_path = os.path.join(output_dir, f"frame_{frame:04d}.png")
        if os.path.isfile(frame_path) and os.path.getsize(frame_path) > 1000:
            continue
        scene.frame_set(frame)
        bpy.context.scene.render.filepath = os.path.join(output_dir, f"frame_{frame:04d}")
        bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
