"""Prefab-aware wrapper around the AI scene-graph interpreter (runs inside Blender).

Prefab objects are built as hidden placeholder spheres by the original interpreter
(so animation, relationships and camera logic keep working unchanged); their
primitive parts are then parented to the placeholder and inherit its motion/scale.
"""
from __future__ import annotations

import bpy

from bamo_blender_motifs_b import scene_from_ai_graph
from bamo_blender_primitives import smooth
from bamo_prefabs import PREFAB_KINDS, build_parts

_ROLE_MATERIAL = {
    "key": "AI Director key", "accent": "AI Director accent",
    "neutral": "AI Director neutral", "dark": "AI Director dark",
}


def _find_material(name):
    mat = bpy.data.materials.get(name)
    if mat is not None:
        return mat
    for candidate in bpy.data.materials:
        if candidate.name.startswith(name):
            return candidate
    return None


def _spawn_part(part, name, light):
    shape = part["shape"]
    if shape == "sphere":
        bpy.ops.mesh.primitive_uv_sphere_add(segments=16 if light else 32, ring_count=8 if light else 16, radius=1)
    elif shape == "cube":
        bpy.ops.mesh.primitive_cube_add(size=1)
    elif shape == "cylinder":
        bpy.ops.mesh.primitive_cylinder_add(vertices=12 if light else 32, radius=1, depth=2)
    elif shape == "cone":
        bpy.ops.mesh.primitive_cone_add(vertices=int(part.get("vertices") or 32), radius1=1, radius2=0.0, depth=2)
    elif shape == "torus":
        bpy.ops.mesh.primitive_torus_add(major_segments=48, minor_segments=12)
    elif shape == "icosphere":
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1 if light else 2, radius=1)
    else:
        raise RuntimeError("Unsupported prefab part shape: " + str(shape))
    obj = bpy.context.object
    obj.name = name
    obj.scale = part["scale"]
    obj.rotation_euler = part["rot"]
    if shape in {"sphere", "cylinder", "cone", "torus", "icosphere"}:
        smooth(obj)
    return obj


def scene_from_ai_graph_v2(graph, frames):
    prefab_items = {}
    objects = []
    for item in graph["objects"]:
        if item["kind"] in PREFAB_KINDS:
            prefab_items[item["id"]] = item
            item = {**item, "kind": "sphere"}
        objects.append(item)
    camera_move = scene_from_ai_graph({**graph, "objects": objects}, frames)

    for object_id, item in prefab_items.items():
        anchor = bpy.data.objects.get("AI_" + object_id)
        if anchor is None:
            continue
        anchor.hide_render = True
        anchor.hide_viewport = True
        parts = build_parts(item["kind"], object_id)
        light = len(parts) > 60
        primary = _find_material(_ROLE_MATERIAL.get(item.get("material"), "AI Director key"))
        for index, part in enumerate(parts):
            role = part["role"]
            mat = primary if role == "primary" else _find_material(_ROLE_MATERIAL[role])
            obj = _spawn_part(part, f"AI_{object_id}_part{index:03d}", light)
            obj.parent = anchor
            obj.location = part["pos"]
            if mat is not None:
                obj.data.materials.append(mat)
    return camera_move
