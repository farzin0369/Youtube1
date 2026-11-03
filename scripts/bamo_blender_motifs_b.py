"""AI scene-graph interpreter for BAMO Blender renderer."""
from __future__ import annotations

import math

import bpy
from mathutils import Vector

from bamo_blender_primitives import (
    material, assign, smooth, sphere, cube, cylinder_between, curve, torus,
    key_scale, ground,
)

def hex_rgb(value):
    raw = str(value).lstrip("#")
    if len(raw) == 3:
        raw = "".join(ch * 2 for ch in raw)
    return tuple(int(raw[i:i+2], 16) / 255.0 for i in (0, 2, 4))

def scene_from_ai_graph(graph, frames):
    """Execute a validated semantic scene graph authored by the AI director."""
    palette = graph["palette"]
    world = bpy.context.scene.world
    world.use_nodes = True
    background = world.node_tree.nodes["Background"]
    background.inputs["Color"].default_value = (*hex_rgb(palette["background"]), 1)
    if "Strength" in background.inputs:
        background.inputs["Strength"].default_value = 0.45
    colors = {"key": hex_rgb(palette["key"]), "accent": hex_rgb(palette["accent"]),
              "neutral": (0.68, 0.73, 0.82), "dark": (0.025, 0.04, 0.07)}
    mats = {
        "key": material("AI Director key", colors["key"], 0.22, 0.2, 2.6),
        "accent": material("AI Director accent", colors["accent"], 0.18, 0.24, 2.2),
        "neutral": material("AI Director neutral", colors["neutral"], 0.12, 0.34, 0.45),
        "dark": material("AI Director dark", colors["dark"], 0.05, 0.5, 0.0),
    }
    objects = {}
    rest_locations = {}
    for item in graph["objects"]:
        kind, location, scale = item["kind"], tuple(item["position"]), tuple(item["scale"])
        name = "AI_" + item["id"]
        rest_locations[item["id"]] = Vector(location)
        if kind == "sphere": bpy.ops.mesh.primitive_uv_sphere_add(segments=40, ring_count=24, radius=1, location=location)
        elif kind == "cube": bpy.ops.mesh.primitive_cube_add(size=1, location=location)
        elif kind == "cylinder": bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=1, depth=2, location=location)
        elif kind in {"torus", "ring"}: bpy.ops.mesh.primitive_torus_add(major_segments=64, minor_segments=12, location=location)
        elif kind == "cone": bpy.ops.mesh.primitive_cone_add(vertices=48, radius1=1, radius2=0.05, depth=2, location=location)
        elif kind == "icosphere": bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=1, location=location)
        elif kind == "line":
            start = Vector(location); finish = start + Vector(scale)
            objects[item["id"]] = curve(name, [start, finish], 0.025, mats[item["material"]])
            continue
        else:
            bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=16, radius=1, location=location)
        obj = bpy.context.object
        obj.name = name
        obj.scale = scale
        obj.rotation_euler = tuple(item.get("rotation") or (0, 0, 0))
        assign(obj, mats[item["material"]])
        smooth(obj)
        objects[item["id"]] = obj
    for item in graph["objects"]:
        obj = objects.get(item["id"])
        if obj is None:
            continue
        action = item.get("action") or "none"
        amount = float(item.get("action_amount") or 0)
        base_loc = obj.location.copy()
        base_rot = obj.rotation_euler.copy()
        base_scale = obj.scale.copy()
        samples = max(2, min(frames, 8))
        for sample in range(samples):
            frame = 1 + int(sample * (frames - 1) / max(1, samples - 1))
            factor = sample / max(1, samples - 1)
            obj.location = base_loc.copy()
            obj.rotation_euler = base_rot.copy()
            obj.scale = base_scale.copy()
            if action == "rise": obj.location.z += amount * factor
            elif action == "fall": obj.location.z -= amount * factor
            elif action == "travel_x": obj.location.x += amount * factor
            elif action == "travel_y": obj.location.y += amount * factor
            elif action == "rotate": obj.rotation_euler.z += amount * factor
            elif action == "orbit":
                angle = amount * factor
                radius = max(0.8, abs(amount) if abs(amount) > 0.2 else 1.2)
                obj.location.x += math.cos(angle) * radius - radius
                obj.location.y += math.sin(angle) * radius
            elif action == "pulse":
                pulse = 1.0 + 0.18 * math.sin(factor * math.tau)
                obj.scale = tuple(component * pulse for component in base_scale)
            elif action == "reveal":
                reveal = 0.05 + 0.95 * factor
                obj.scale = tuple(max(0.001, component * reveal) for component in base_scale)
            obj.keyframe_insert(data_path="location", frame=frame)
            obj.keyframe_insert(data_path="rotation_euler", frame=frame)
            obj.keyframe_insert(data_path="scale", frame=frame)
        obj.location = base_loc.copy()
        obj.rotation_euler = base_rot.copy()
        obj.scale = base_scale.copy()
        if obj.animation_data and obj.animation_data.action:
            for fcurve in obj.animation_data.action.fcurves:
                for point in fcurve.keyframe_points:
                    point.interpolation = "LINEAR"
    for relation in graph.get("relationships", []):
        a_id, b_id = relation["from"], relation["to"]
        start, finish = rest_locations[a_id], rest_locations[b_id]
        if relation["kind"] == "orbit":
            mid = (start + finish) * 0.5
            radius = max(0.15, (finish - start).length * 0.5)
            points = [mid + Vector((math.cos(i * math.tau / 32) * radius, math.sin(i * math.tau / 32) * radius, 0.0)) for i in range(33)]
            curve("AI relationship orbit", points, 0.02, mats["accent"], cyclic=True)
        elif relation["kind"] == "connect" and (finish - start).length > 0.05:
            cylinder_between("AI bond " + a_id + " " + b_id, start, finish, 0.035, mats["accent"])
        else:
            curve("AI relationship " + relation["kind"], [start, finish], 0.02, mats["accent"])
    ground(mats["dark"])
    return graph.get("camera", {}).get("move", "push_in")
