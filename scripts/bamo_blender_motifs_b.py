"""AI scene-graph interpreter for BAMO Blender renderer — cinematic quality path."""
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


def _emission_mat(name, color, strength=4.0, roughness=0.22):
    """Bright emissive material for hero accents that read on CPU Cycles."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    emission = nodes.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value = (*color, 1.0)
    emission.inputs["Strength"].default_value = strength
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = 0.15
    if "Emission Color" in bsdf.inputs:
        bsdf.inputs["Emission Color"].default_value = (*color, 1.0)
    if "Emission Strength" in bsdf.inputs:
        bsdf.inputs["Emission Strength"].default_value = strength * 0.55
    mix = nodes.new("ShaderNodeMixShader")
    mix.inputs["Fac"].default_value = 0.35
    links.new(bsdf.outputs["BSDF"], mix.inputs[1])
    links.new(emission.outputs["Emission"], mix.inputs[2])
    links.new(mix.outputs["Shader"], out.inputs["Surface"])
    return mat


def _cinematic_lights(key_rgb, accent_rgb):
    """Three-point + rim lighting tuned for neon science shorts on CPU."""
    bpy.ops.object.light_add(type="AREA", location=(5.2, -6.2, 9.0))
    key = bpy.context.object
    key.name = "AI_Key"
    key.data.energy = 1600
    key.data.shape = "DISK"
    key.data.size = 8.5
    key.data.color = key_rgb
    key.rotation_euler = (math.radians(32), 0, math.radians(35))

    bpy.ops.object.light_add(type="AREA", location=(-6.0, 2.0, 6.5))
    rim = bpy.context.object
    rim.name = "AI_Rim"
    rim.data.energy = 1100
    rim.data.size = 7.0
    rim.data.color = accent_rgb
    rim.rotation_euler = (math.radians(18), 0, math.radians(-40))

    bpy.ops.object.light_add(type="POINT", location=(0.0, 0.0, 5.5))
    fill = bpy.context.object
    fill.name = "AI_Fill"
    fill.data.energy = 380
    fill.data.color = (0.85, 0.9, 1.0)
    fill.data.shadow_soft_size = 2.4

    bpy.ops.object.light_add(type="AREA", location=(0.0, 8.0, 3.0))
    back = bpy.context.object
    back.name = "AI_Back"
    back.data.energy = 700
    back.data.size = 10.0
    back.data.color = accent_rgb
    back.rotation_euler = (math.radians(90), 0, 0)


def _subdivide(obj, levels=1):
    if obj.type != "MESH" or levels < 1:
        return
    mod = obj.modifiers.new("AI_Subsurf", "SUBSURF")
    mod.levels = levels
    mod.render_levels = levels


def scene_from_ai_graph(graph, frames):
    """Execute a validated semantic scene graph authored by the AI director."""
    palette = graph["palette"]
    world = bpy.context.scene.world
    world.use_nodes = True
    background = world.node_tree.nodes["Background"]
    background.inputs["Color"].default_value = (*hex_rgb(palette["background"]), 1)
    if "Strength" in background.inputs:
        background.inputs["Strength"].default_value = 0.18

    colors = {
        "key": hex_rgb(palette["key"]),
        "accent": hex_rgb(palette["accent"]),
        "neutral": (0.72, 0.76, 0.84),
        "dark": (0.02, 0.03, 0.06),
    }
    mats = {
        "key": material("AI Director key", colors["key"], 0.55, 0.18, 1.8),
        "accent": _emission_mat("AI Director accent", colors["accent"], strength=5.5),
        "neutral": material("AI Director neutral", colors["neutral"], 0.2, 0.32, 0.15),
        "dark": material("AI Director dark", colors["dark"], 0.08, 0.55, 0.0),
    }

    # Override default stage lights with cinematic set matched to palette.
    _cinematic_lights(colors["key"], colors["accent"])

    objects = {}
    rest_locations = {}
    for item in graph["objects"]:
        kind, location, scale = item["kind"], tuple(item["position"]), tuple(item["scale"])
        name = "AI_" + item["id"]
        rest_locations[item["id"]] = Vector(location)
        if kind == "sphere":
            bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=1, location=location)
        elif kind == "cube":
            bpy.ops.mesh.primitive_cube_add(size=1, location=location)
        elif kind == "cylinder":
            bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=1, depth=2, location=location)
        elif kind in {"torus", "ring"}:
            bpy.ops.mesh.primitive_torus_add(major_segments=96, minor_segments=24, location=location)
        elif kind == "cone":
            bpy.ops.mesh.primitive_cone_add(vertices=64, radius1=1, radius2=0.04, depth=2, location=location)
        elif kind == "icosphere":
            bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=4, radius=1, location=location)
        elif kind == "line":
            start = Vector(location)
            finish = start + Vector(scale)
            objects[item["id"]] = curve(name, [start, finish], 0.04, mats[item["material"]])
            continue
        else:
            bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=1, location=location)
        obj = bpy.context.object
        obj.name = name
        obj.scale = scale
        obj.rotation_euler = tuple(item.get("rotation") or (0, 0, 0))
        assign(obj, mats[item["material"]])
        smooth(obj)
        if kind in {"sphere", "icosphere", "torus", "ring"}:
            _subdivide(obj, 1)
        if kind == "cube":
            bevel = obj.modifiers.new("SoftEdge", "BEVEL")
            bevel.width = 0.06
            bevel.segments = 4
        objects[item["id"]] = obj

    # Dense keyframes for smoother motion (was max 8 — looked stepped).
    samples = max(12, min(frames, 48))
    for item in graph["objects"]:
        obj = objects.get(item["id"])
        if obj is None:
            continue
        action = item.get("action") or "none"
        amount = float(item.get("action_amount") or 0)
        base_loc = obj.location.copy()
        base_rot = obj.rotation_euler.copy()
        base_scale = obj.scale.copy()
        for sample in range(samples):
            frame = 1 + int(sample * (frames - 1) / max(1, samples - 1))
            factor = sample / max(1, samples - 1)
            # Ease in-out for less mechanical motion.
            eased = factor * factor * (3.0 - 2.0 * factor)
            obj.location = base_loc.copy()
            obj.rotation_euler = base_rot.copy()
            obj.scale = base_scale.copy()
            if action == "rise":
                obj.location.z += amount * eased
            elif action == "fall":
                obj.location.z -= amount * eased
            elif action == "travel_x":
                obj.location.x += amount * eased
            elif action == "travel_y":
                obj.location.y += amount * eased
            elif action == "rotate":
                obj.rotation_euler.z += amount * factor * math.tau * 0.35
            elif action == "orbit":
                angle = amount * factor * math.tau * 0.5
                radius = max(0.9, abs(amount) if abs(amount) > 0.25 else 1.4)
                obj.location.x = base_loc.x + math.cos(angle) * radius
                obj.location.y = base_loc.y + math.sin(angle) * radius
            elif action == "pulse":
                pulse = 1.0 + 0.22 * math.sin(factor * math.tau * 2.0)
                obj.scale = tuple(component * pulse for component in base_scale)
            elif action == "reveal":
                reveal = 0.02 + 0.98 * eased
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
                    point.interpolation = "BEZIER"
                    point.easing = "EASE_IN_OUT"

    for relation in graph.get("relationships", []):
        a_id, b_id = relation["from"], relation["to"]
        if a_id not in rest_locations or b_id not in rest_locations:
            continue
        start, finish = rest_locations[a_id], rest_locations[b_id]
        if relation["kind"] == "orbit":
            mid = (start + finish) * 0.5
            radius = max(0.2, (finish - start).length * 0.55)
            points = [
                mid + Vector((
                    math.cos(i * math.tau / 48) * radius,
                    math.sin(i * math.tau / 48) * radius,
                    0.05 * math.sin(i * math.tau / 12),
                ))
                for i in range(49)
            ]
            curve("AI relationship orbit", points, 0.035, mats["accent"], cyclic=True)
        elif relation["kind"] == "connect" and (finish - start).length > 0.05:
            cylinder_between("AI bond " + a_id + " " + b_id, start, finish, 0.045, mats["accent"])
        else:
            curve("AI relationship " + relation["kind"], [start, finish], 0.03, mats["accent"])

    ground(mats["dark"])

    # Stronger compositor glow for neon readability.
    scene = bpy.context.scene
    if scene.use_nodes and scene.node_tree:
        for node in scene.node_tree.nodes:
            if node.type == "GLARE":
                node.threshold = 0.55
                try:
                    node.size = 8
                except Exception:
                    pass
                node.quality = "HIGH"

    return graph.get("camera", {}).get("move", "push_in")
