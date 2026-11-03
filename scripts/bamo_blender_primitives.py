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


def add_camera(frames, camera_style, camera_angle="eye"):
    bpy.ops.object.camera_add(location=(0, -12.5, 5.2))
    camera = bpy.context.object
    camera.name = "BAMO_Cinematic_Camera"
    camera.data.lens = 48
    bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0, 0, 1.2))
    target = bpy.context.object
    target.name = "Camera_Focus"
    track = camera.constraints.new(type="TRACK_TO")
    track.target = target
    track.track_axis = "TRACK_NEGATIVE_Z"
    track.up_axis = "UP_Y"

    end = max(2, frames)
    if camera_style == "orbit":
        radius = 11.5
        for frame, angle, height in (
            (1, math.radians(-28), 4.5),
            (max(2, int(end * 0.25)), math.radians(-12), 4.9),
            (max(3, int(end * 0.50)), math.radians(8), 4.7),
            (max(4, int(end * 0.75)), math.radians(25), 4.2),
            (end, math.radians(42), 4.0),
        ):
            camera.location = (radius * math.sin(angle), -radius * math.cos(angle), height)
            camera.keyframe_insert(data_path="location", frame=frame)
            target.location = (0.2 * math.sin(angle), 0.0, 1.3)
            target.keyframe_insert(data_path="location", frame=frame)
    else:
        if camera_style == "push_in":
            start, finish = (0, -14, 5.5), (0, -8.2, 3.3)
        elif camera_style == "tracking":
            start, finish = (-4.5, -11.5, 4.2), (4.2, -8.2, 3.0)
        elif camera_style == "sweep":
            start, finish = (-5.5, -10.5, 5.0), (5.5, -8.8, 3.5)
        elif camera_style == "crane":
            start, finish = (0, -12.0, 8.5), (0, -9.0, 3.0)
        elif camera_style == "static":
            start, finish = (0, -11.0, 4.5), (0, -11.0, 4.5)
        else:
            raise RuntimeError("Unsupported camera motion: " + camera_style)
        for frame, location, focus in (
            (1, start, (0, 0, 1.0)),
            (end, finish, (0.3, 0.0, 1.35)),
        ):
            camera.location = location
            camera.keyframe_insert(data_path="location", frame=frame)
            target.location = focus
            target.keyframe_insert(data_path="location", frame=frame)
    elevation = {"low": -1.8, "eye": 0.0, "high": 2.0, "top": 5.0}.get(camera_angle, 0.0)
    if elevation and camera.animation_data and camera.animation_data.action:
        for fcurve in camera.animation_data.action.fcurves:
            if fcurve.data_path == "location" and fcurve.array_index == 2:
                for keyframe in fcurve.keyframe_points:
                    keyframe.co.y += elevation
                fcurve.update()
    camera.data.dof.use_dof = True
    camera.data.dof.focus_object = target
    camera.data.dof.aperture_fstop = 4.5
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
