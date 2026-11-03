"""Headless Blender CPU capability probe for the BAMO renderer migration.

This is an isolated engine qualification test. It does not replace the current
production renderer or open the YouTube publishing gate.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import bpy
from mathutils import Vector

OUT = Path(os.environ.get("BAMO_BLENDER_OUT", "output/bamo-blender-probe")).resolve()
OUT.mkdir(parents=True, exist_ok=True)

# Deterministic clean scene.
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items.keys() else "BLENDER_EEVEE"
scene.render.resolution_x = 480
scene.render.resolution_y = 854
scene.render.resolution_percentage = 100
scene.render.fps = 24
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False
scene.world.color = (0.008, 0.012, 0.025)

# Actual mesh geometry: a metallic central nucleus, orbiting bodies and a
# procedural curve, with area lighting and a perspective camera.
def material(name, color, metallic=0.0, emission=0.0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1.0)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = 0.24
    if emission:
        bsdf.inputs["Emission Color"].default_value = (*color, 1.0)
        bsdf.inputs["Emission Strength"].default_value = emission
    return mat

gold = material("BAMO luminous gold", (0.95, 0.48, 0.10), 0.65, 0.25)
cyan = material("BAMO ion blue", (0.04, 0.48, 0.95), 0.45, 0.55)
dark = material("BAMO midnight", (0.012, 0.025, 0.055), 0.2)
bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=0.72)
core = bpy.context.object
core.name = "3D nucleus"
core.data.materials.append(gold)
for poly in core.data.polygons:
    poly.use_smooth = True

for idx, radius in enumerate((1.55, 2.05, 2.55)):
    bpy.ops.curve.primitive_bezier_circle_add(radius=radius)
    orbit = bpy.context.object
    orbit.name = f"Orbital path {idx+1}"
    orbit.data.bevel_depth = 0.012
    orbit.data.bevel_resolution = 3
    orbit.data.materials.append(cyan if idx % 2 == 0 else gold)
    orbit.rotation_euler[0] = 0.55 + idx * 0.34
    orbit.rotation_euler[1] = idx * 0.42
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=0.13 + idx * 0.025, location=(radius, 0, 0))
    body = bpy.context.object
    body.name = f"Orbiting 3D body {idx+1}"
    body.data.materials.append(cyan if idx % 2 == 0 else gold)
    for poly in body.data.polygons:
        poly.use_smooth = True
    body.parent = orbit
    body.location = (radius, 0, 0)
    orbit.rotation_euler[2] = 0
    orbit.keyframe_insert(data_path="rotation_euler", index=2, frame=1)
    orbit.rotation_euler[2] = 2.8 + idx * 0.6
    orbit.keyframe_insert(data_path="rotation_euler", index=2, frame=49)

# Camera and cinematic light rig.
bpy.ops.object.camera_add(location=(5.4, -8.4, 5.2))
camera = bpy.context.object
camera.name = "Animated cinematic camera"
camera.data.lens = 52
scene.camera = camera
target = Vector((0, 0, 0))
camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
camera.keyframe_insert(data_path="location", frame=1)
camera.location = (4.2, -7.0, 3.8)
camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
camera.keyframe_insert(data_path="location", frame=49)
camera.keyframe_insert(data_path="rotation_euler", frame=1)
camera.keyframe_insert(data_path="rotation_euler", frame=49)

for name, location, energy, size, color in (
    ("Key softbox", (3, -4, 6), 950, 4.0, (1.0, 0.72, 0.42)),
    ("Cool rim", (-4, 1, 3), 1250, 3.0, (0.12, 0.42, 1.0)),
    ("Top fill", (0, 4, 5), 700, 3.5, (0.45, 0.72, 1.0)),
):
    bpy.ops.object.light_add(type="AREA", location=location)
    light = bpy.context.object
    light.name = name
    light.data.energy = energy
    light.data.shape = "DISK"
    light.data.size = size
    light.data.color = color
    light.rotation_euler = (Vector((0, 0, 0)) - light.location).to_track_quat("-Z", "Y").to_euler()

# Ground plane for depth and soft shadows.
bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -1.15))
plane = bpy.context.object
plane.name = "Midnight stage"
plane.data.materials.append(dark)

scene.render.image_settings.color_mode = "RGBA"
scene.render.filepath = str(OUT / "frame_")
scene.frame_start = 1
scene.frame_end = 49
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False
scene.view_settings.view_transform = "Standard"
scene.render.engine = "BLENDER_EEVEE_NEXT" if scene.render.engine == "BLENDER_EEVEE_NEXT" else scene.render.engine
scene.render.image_settings.color_depth = "8"
scene.render.use_file_extension = True

# CPU mode is explicit for Cycles; Eevee is the intended fast raster engine.
if scene.render.engine == "CYCLES":
    scene.cycles.device = "CPU"
    scene.cycles.samples = 16

bpy.ops.render.render(animation=True)
frames = sorted(OUT.glob("frame_*.png"))
if len(frames) != 49:
    raise RuntimeError(f"Expected 49 rendered frames, found {len(frames)}")

report = {
    "ok": True,
    "engine": scene.render.engine,
    "frames": len(frames),
    "resolution": [scene.render.resolution_x * scene.render.resolution_percentage // 100,
                   scene.render.resolution_y * scene.render.resolution_percentage // 100],
    "objects": len(scene.objects),
    "camera_keyframes": 4,
    "output": str(OUT),
    "note": "Isolated Blender CPU qualification only; not yet the production renderer.",
}
(OUT / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print("BAMO_BLENDER_PROBE=" + json.dumps(report))
