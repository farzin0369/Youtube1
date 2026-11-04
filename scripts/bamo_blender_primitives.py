"""Shared Blender primitives for BAMO CPU scene builder."""
from __future__ import annotations

import math

import bpy
from mathutils import Vector

def material(name, color, metallic=0.35, roughness=0.28, emission=0.0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1.0)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    for key in ("Emission Color", "Emission"):
        if key in bsdf.inputs:
            bsdf.inputs[key].default_value = (*color, 1.0)
            break
    if "Emission Strength" in bsdf.inputs:
        bsdf.inputs["Emission Strength"].default_value = emission
    return mat


def assign(obj, mat):
    if mat:
        obj.data.materials.append(mat)
    return obj


def smooth(obj):
    if obj.type == "MESH":
        for poly in obj.data.polygons:
            poly.use_smooth = True
    return obj


def sphere(name, location, radius, mat):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=20, radius=radius, location=location)
    obj = bpy.context.object
    obj.name = name
    assign(obj, mat)
    smooth(obj)
    return obj


def cube(name, location, scale, mat, bevel=0.08):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        mod = obj.modifiers.new("Soft machined edges", "BEVEL")
        mod.width = bevel
        mod.segments = 3
        obj.modifiers.new("Weighted corner normals", "WEIGHTED_NORMAL")
    assign(obj, mat)
    return obj


def cylinder_between(name, a, b, radius, mat):
    direction = Vector(b) - Vector(a)
    midpoint = (Vector(a) + Vector(b)) * 0.5
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=radius, depth=direction.length, location=midpoint)
    obj = bpy.context.object
    obj.name = name
    obj.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()
    assign(obj, mat)
    smooth(obj)
    return obj


def curve(name, points, bevel, mat, cyclic=False):
    data = bpy.data.curves.new(name, "CURVE")
    data.dimensions = "3D"
    data.resolution_u = 24
    data.bevel_depth = bevel
    data.bevel_resolution = 5
    spline = data.splines.new("BEZIER")
    spline.bezier_points.add(len(points) - 1)
    for point, coordinate in zip(spline.bezier_points, points):
        point.co = coordinate
        point.handle_left_type = "AUTO"
        point.handle_right_type = "AUTO"
    spline.use_cyclic_u = cyclic
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    assign(obj, mat)
    return obj


def torus(name, location, major, minor, mat, rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_torus_add(
        major_segments=96, minor_segments=16,
        location=location, major_radius=major, minor_radius=minor,
    )
    obj = bpy.context.object
    obj.name = name
    obj.rotation_euler = rotation
    assign(obj, mat)
    smooth(obj)
    return obj


def key_scale(obj, frames, values):
    for frame, value in zip(frames, values):
        obj.scale = (value, value, value)
        obj.keyframe_insert(data_path="scale", frame=frame)


def _ease_smoothstep(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def _catmull_rom(p0, p1, p2, p3, t: float):
    """Interpolate between p1 and p2 with Catmull-Rom; t in [0, 1]."""
    t2 = t * t
    t3 = t2 * t
    return 0.5 * (
        (2.0 * p1)
        + (-p0 + p2) * t
        + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t2
        + (-p0 + 3.0 * p1 - 3.0 * p2 + p3) * t3
    )


def _sample_path(control_points, samples: int):
    """Dense samples along a Catmull-Rom path through control_points."""
    pts = [Vector(p) for p in control_points]
    if len(pts) == 1:
        return [pts[0].copy() for _ in range(max(2, samples))]
    if len(pts) == 2:
        out = []
        for i in range(max(2, samples)):
            t = _ease_smoothstep(i / max(1, samples - 1))
            out.append(pts[0].lerp(pts[1], t))
        return out
    # Pad ends for Catmull-Rom
    padded = [pts[0]] + pts + [pts[-1]]
    segments = len(pts) - 1
    out = []
    for i in range(max(2, samples)):
        u = _ease_smoothstep(i / max(1, samples - 1)) * segments
        seg = min(segments - 1, int(u))
        local_t = u - seg
        p0, p1, p2, p3 = padded[seg], padded[seg + 1], padded[seg + 2], padded[seg + 3]
        out.append(_catmull_rom(p0, p1, p2, p3, local_t))
    return out


def _subtle_shake(frame: int, amplitude: float = 0.018) -> Vector:
    """Deterministic micro-shake so previews stay reproducible."""
    # Low-frequency combination — reads as handheld, not noise.
    x = math.sin(frame * 0.17) * amplitude + math.sin(frame * 0.41) * amplitude * 0.35
    y = math.cos(frame * 0.13) * amplitude * 0.8 + math.sin(frame * 0.29) * amplitude * 0.25
    z = math.sin(frame * 0.23) * amplitude * 0.45
    return Vector((x, y, z))


def add_camera(frames, camera_style, camera_angle="eye"):
    bpy.ops.object.camera_add(location=(0, -12.5, 5.2))
    camera = bpy.context.object
    camera.name = "BAMO_Cinematic_Camera"
    camera.data.lens = 50
    camera.data.clip_start = 0.1
    camera.data.clip_end = 500.0
    bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0, 0, 1.2))
    target = bpy.context.object
    target.name = "Camera_Focus"
    track = camera.constraints.new(type="TRACK_TO")
    track.target = target
    track.track_axis = "TRACK_NEGATIVE_Z"
    track.up_axis = "UP_Y"

    end = max(2, frames)
    samples = max(12, min(end, 48))

    if camera_style == "orbit":
        radius = 11.5
        cam_controls = []
        focus_controls = []
        for angle_deg, height in ((-28, 4.5), (-12, 4.9), (8, 4.7), (25, 4.2), (42, 4.0)):
            angle = math.radians(angle_deg)
            cam_controls.append((radius * math.sin(angle), -radius * math.cos(angle), height))
            focus_controls.append((0.25 * math.sin(angle), 0.0, 1.3))
    elif camera_style == "push_in":
        cam_controls = [(0, -14.0, 5.5), (0, -11.0, 4.4), (0, -8.2, 3.3)]
        focus_controls = [(0, 0, 1.0), (0.1, 0, 1.15), (0.25, 0, 1.35)]
    elif camera_style == "tracking":
        cam_controls = [(-4.5, -11.5, 4.2), (-1.0, -10.0, 3.8), (4.2, -8.2, 3.0)]
        focus_controls = [(-0.5, 0, 1.1), (0.0, 0, 1.2), (0.4, 0, 1.3)]
    elif camera_style == "sweep":
        cam_controls = [(-5.5, -10.5, 5.0), (0.0, -9.5, 4.2), (5.5, -8.8, 3.5)]
        focus_controls = [(-0.3, 0, 1.1), (0.1, 0, 1.25), (0.4, 0, 1.35)]
    elif camera_style == "crane":
        cam_controls = [(0, -12.0, 8.5), (0.3, -10.5, 5.5), (0, -9.0, 3.0)]
        focus_controls = [(0, 0, 1.4), (0.1, 0, 1.25), (0.2, 0, 1.15)]
    elif camera_style == "static":
        cam_controls = [(0, -11.0, 4.5), (0, -11.0, 4.5)]
        focus_controls = [(0, 0, 1.2), (0, 0, 1.2)]
    else:
        raise RuntimeError("Unsupported camera motion: " + camera_style)

    cam_path = _sample_path(cam_controls, samples)
    focus_path = _sample_path(focus_controls, samples)
    elevation = {"low": -1.8, "eye": 0.0, "high": 2.0, "top": 5.0}.get(camera_angle, 0.0)

    for i, (cam_loc, focus_loc) in enumerate(zip(cam_path, focus_path)):
        frame = 1 + int(i * (end - 1) / max(1, samples - 1))
        shake = _subtle_shake(frame) if camera_style != "static" else Vector((0, 0, 0))
        camera.location = (cam_loc.x + shake.x, cam_loc.y + shake.y, cam_loc.z + elevation + shake.z)
        camera.keyframe_insert(data_path="location", frame=frame)
        target.location = (focus_loc.x, focus_loc.y, focus_loc.z)
        target.keyframe_insert(data_path="location", frame=frame)

    if camera.animation_data and camera.animation_data.action:
        for fcurve in camera.animation_data.action.fcurves:
            for point in fcurve.keyframe_points:
                point.interpolation = "BEZIER"
                point.easing = "EASE_IN_OUT"
    if target.animation_data and target.animation_data.action:
        for fcurve in target.animation_data.action.fcurves:
            for point in fcurve.keyframe_points:
                point.interpolation = "BEZIER"
                point.easing = "EASE_IN_OUT"

    camera.data.dof.use_dof = True
    camera.data.dof.focus_object = target
    camera.data.dof.aperture_fstop = 3.6
    try:
        camera.data.dof.aperture_blades = 6
    except Exception:
        pass
    bpy.context.scene.camera = camera


def lighting(gold, blue):
    world = bpy.context.scene.world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.008, 0.014, 0.03, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.22

    bpy.ops.object.light_add(type="AREA", location=(4.5, -5.0, 8.5))
    key = bpy.context.object
    key.name = "Warm cinematic key"
    key.data.energy = 1250
    key.data.shape = "DISK"
    key.data.size = 7
    key.data.color = gold
    key.rotation_euler = (math.radians(25), 0, math.radians(28))

    bpy.ops.object.light_add(type="AREA", location=(-5, 1.5, 5.5))
    fill = bpy.context.object
    fill.name = "Cool rim"
    fill.data.energy = 900
    fill.data.size = 6
    fill.data.color = blue
    fill.rotation_euler = (math.radians(20), 0, math.radians(-35))

    bpy.ops.object.light_add(type="POINT", location=(0, 0, 4))
    glow = bpy.context.object
    glow.name = "Subject glow"
    glow.data.energy = 260
    glow.data.color = gold
    glow.data.shadow_soft_size = 2.0


def ground(mat):
    cube("Infinite stage", (0, 0, -0.48), (200, 200, 0.6), mat, bevel=0)
