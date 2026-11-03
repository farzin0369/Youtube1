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
        # A true multi-point orbit around the subject, not a straight camera pan.
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
    # Apply the AI director's requested camera elevation to the animated path.
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


def scene_choice(gold, blue, dark, frames):
    ground(dark)
    for side, mat in ((-1, blue), (1, gold)):
        pts = [
            (0, -7, 0.03),
            (side * 0.5, -4.0, 0.03),
            (side * 1.25, -1.5, 0.03),
            (side * 2.7, 1.4, 0.03),
            (side * 4.6, 5.8, 0.03),
        ]
        curve("Diverging road", pts, 0.24, mat)
        for k in range(7):
            y = -5.8 + k * 1.45
            x = side * (0.15 + (k / 7) * 3.2)
            cube("Road marker", (x, y, 0.04), (0.12, 0.62, 0.035), mat, bevel=0.02)
    sphere("Decision light", (0, -5.6, 0.42), 0.34, gold)


def scene_journey(gold, blue, dark, frames):
    ground(dark)
    for i, (x, y, scale) in enumerate(((-6, 5, 3.0), (-3.5, 7, 4.0), (4.0, 7, 4.5), (7, 4, 3.0))):
        bpy.ops.mesh.primitive_cone_add(vertices=7, radius1=scale, radius2=0.15, depth=scale * 2.6,
                                        location=(x, y, scale * 1.15 - 0.3))
        mountain = bpy.context.object
        mountain.name = "Distant mountain"
        assign(mountain, blue if i % 2 else dark)
    road_points = [
        (-0.2, -8, 0.04), (0.2, -5.5, 0.04), (-0.8, -3.0, 0.04),
        (-0.2, -0.4, 0.04), (1.0, 2.4, 0.04), (0.2, 5.8, 0.04),
    ]
    curve("Winding journey road", road_points, 0.42, blue)
    curve("Road center light", [(x, y, 0.48) for x, y, _ in road_points], 0.035, gold)
    torus("Distant sunrise", (0, 6.8, 3.2), 1.35, 0.055, gold, (math.pi / 2, 0, 0))


def scene_growth(gold, blue, dark, frames):
    ground(dark)
    for i in range(8):
        x = -3.2 + i * 0.88
        y = -1.5 + i * 0.55
        height = 0.45 + i * 0.22
        obj = cube("Rising 3D step", (x, y, height * 0.5 - 0.1), (0.82, 1.0, height), gold if i > 4 else blue)
        obj.keyframe_insert(data_path="location", frame=1)
        obj.location.z += 0.18
        obj.keyframe_insert(data_path="location", frame=frames)
    torus("Progress halo", (2.9, 2.7, 2.8), 1.0, 0.045, gold, (math.pi / 2, 0, 0))


def scene_atom(gold, blue, dark, frames):
    sphere("Atomic nucleus", (0, 0, 1.3), 0.72, gold)
    sphere("Nucleus core", (0.15, -0.2, 1.45), 0.32, blue)
    for i, rot in enumerate(((0.2, 0.0, 0.0), (1.05, 0.55, 0.2), (-0.9, 0.7, -0.3))):
        shell = torus("Electron shell", (0, 0, 1.3), 2.25, 0.035, blue if i % 2 else gold, rot)
        electron = sphere("Orbiting electron", (2.2, 0, 1.3), 0.18, blue if i % 2 else gold)
        for frame, angle in ((1, 0), (frames, math.tau)):
            electron.location = (2.2 * math.cos(angle), 1.35 * math.sin(angle), 1.3 + 0.25 * math.sin(angle * 2))
            electron.keyframe_insert(data_path="location", frame=frame)
        shell.rotation_euler.z = 0
        shell.keyframe_insert(data_path="rotation_euler", frame=1)
        shell.rotation_euler.z = math.pi * 0.45
        shell.keyframe_insert(data_path="rotation_euler", frame=frames)


def scene_neural(gold, blue, dark, frames):
    nodes = [
        (-3.1, -0.4, 1.0), (-2.1, 1.1, 2.0), (-1.1, -1.1, 1.6),
        (0.0, 0.6, 2.7), (1.0, -1.0, 1.1), (2.0, 1.2, 2.1), (3.1, -0.2, 1.5),
        (-0.1, 2.3, 1.4), (1.9, -2.0, 2.5),
    ]
    links = [(0,1),(0,2),(1,2),(1,3),(2,3),(2,4),(3,4),(3,5),(4,5),(4,6),(5,6),(3,7),(5,8),(4,8)]
    for i, (a, b) in enumerate(links):
        cylinder_between("Synapse connection", nodes[a], nodes[b], 0.055, blue if i % 2 else gold)
    for i, point in enumerate(nodes):
        obj = sphere("Glowing neural node", point, 0.22 if i % 3 else 0.32, gold if i % 2 else blue)
        key_scale(obj, (1, frames), (0.82, 1.18))


def scene_molecule(gold, blue, dark, frames):
    nodes = [(-2,0,1.2),(-0.8,1.0,2.0),(0.7,0.8,1.0),(2.0,-0.2,1.8),(0.1,-1.2,2.1)]
    links = [(0,1),(1,2),(2,3),(2,4),(4,0)]
    for i,(a,b) in enumerate(links):
        cylinder_between("Chemical bond", nodes[a], nodes[b], 0.13, blue)
    for i,point in enumerate(nodes):
        sphere("Molecule atom", point, 0.43 if i == 0 else 0.32, gold if i % 2 == 0 else blue)


def scene_geometry(gold, blue, dark, frames):
    sphere("Geometric core", (0,0,1.2), 0.22, gold)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=2.0, location=(0,0,1.2))
    poly = bpy.context.object
    poly.name = "Rotating geometric solid"
    assign(poly, blue)
    wire = poly.modifiers.new("Precision wireframe", "WIREFRAME")
    wire.thickness = 0.035
    bevel = poly.modifiers.new("Glowing bevel", "BEVEL")
    bevel.width = 0.025
    bevel.segments = 2
    poly.keyframe_insert(data_path="rotation_euler", frame=1)
    poly.rotation_euler = (0.8, 0.6, math.tau * 0.65)
    poly.keyframe_insert(data_path="rotation_euler", frame=frames)
    for r in (2.5, 3.1):
        torus("Geometric construction ring", (0,0,1.2), r, 0.025, gold, (math.pi/2,0,0))


def scene_launch(gold, blue, dark, frames):
    ground(dark)
    for i in range(4):
        ring = torus("Portal energy ring", (0,0,1.5), 1.4 + i * 0.48, 0.045, gold if i % 2 == 0 else blue,
                     (math.pi/2, 0, i * 0.22))
        ring.keyframe_insert(data_path="rotation_euler", frame=1)
        ring.rotation_euler.z += math.pi * 0.65
        ring.keyframe_insert(data_path="rotation_euler", frame=frames)
    beam = cube("Rising energy column", (0,0,2.2), (0.18,0.18,4.0), blue, bevel=0.05)
    beam.keyframe_insert(data_path="scale", frame=1)
    beam.scale.z = 1.35
    beam.keyframe_insert(data_path="scale", frame=frames)
    sphere("Launch core", (0,0,1.5), 0.48, gold)




def scene_notebook(gold, blue, dark, frames):
    """An unmistakable open notebook with page ruling and an animated writing pen."""
    ground(dark)
    # Leather cover and two thick paper blocks form an open book.
    paper = material("Warm ivory notebook paper", (0.78, 0.72, 0.56), 0.03, 0.84, 0.0)
    cube("Notebook leather cover", (0, 0, 0.18), (6.5, 4.6, 0.28), gold, bevel=0.16)
    cube("Left paper block", (-1.52, 0, 0.36), (2.85, 4.18, 0.10), paper, bevel=0.035)
    cube("Right paper block", (1.52, 0, 0.36), (2.85, 4.18, 0.10), paper, bevel=0.035)
    cube("Notebook center binding", (0, 0, 0.43), (0.18, 4.22, 0.12), gold, bevel=0.04)
    for side in (-1, 1):
        for row in range(7):
            y = -1.45 + row * 0.46
            curve("Printed notebook ruling", [(side * 1.48, y, 0.43), (side * 0.28, y, 0.43)],
                  0.012, gold)
    # A visible pen moves across the right page while its tip traces a line.
    pen_a, pen_b = (0.55, -0.65, 0.78), (2.35, 0.65, 0.78)
    pen = cylinder_between("Moving fountain pen", pen_a, pen_b, 0.075, gold)
    pen.keyframe_insert(data_path="location", frame=1)
    pen.location.x += 0.45
    pen.location.y += 0.35
    pen.keyframe_insert(data_path="location", frame=frames)
    nib = sphere("Pen nib", pen_b, 0.10, blue)
    nib.keyframe_insert(data_path="location", frame=1)
    nib.location.x += 0.45
    nib.location.y += 0.35
    nib.keyframe_insert(data_path="location", frame=frames)
    curve("Fresh ink stroke", [(0.55, -0.7, 0.49), (0.95, -0.42, 0.49),
                               (1.35, -0.12, 0.49), (1.75, 0.18, 0.49)],
          0.025, blue)


def scene_sunrise(gold, blue, dark, frames):
    """A literal sunrise over a layered horizon; not an abstract portal substitute."""
    ground(dark)
    # Layered distant ridges create a readable horizon silhouette.
    for index, (x, y, width, height) in enumerate((
        (-5.0, 5.0, 5.0, 2.0), (0.0, 6.0, 6.0, 2.6), (5.0, 5.0, 5.0, 1.8),
    )):
        bpy.ops.mesh.primitive_cone_add(vertices=5, radius1=width, radius2=0.08,
                                        depth=height * 2, location=(x, y, height))
        ridge = bpy.context.object
        ridge.name = "Sunrise mountain silhouette"
        assign(ridge, blue if index == 1 else dark)
    sun = sphere("Rising sun", (0, 6.5, 1.1), 1.85, gold)
    sun.keyframe_insert(data_path="location", frame=1)
    sun.location.z += 2.1
    sun.keyframe_insert(data_path="location", frame=frames)
    for index, angle in enumerate((-0.9, -0.55, -0.2, 0.2, 0.55, 0.9)):
        x = math.sin(angle) * 2.5
        z = 1.0 + math.cos(angle) * 1.2
        ray = curve("Sunrise ray", [(x, 6.2, z), (x * 1.55, 6.0, z + 0.65)],
                    0.035, gold)
        ray.keyframe_insert(data_path="scale", frame=1)
        ray.scale = (1.0, 1.0, 1.25)
        ray.keyframe_insert(data_path="scale", frame=frames)
    for index, x in enumerate((-3.5, 3.1)):
        cloud = sphere("Soft dawn cloud", (x, 3.5, 3.2 + index * 0.35), 0.55, blue)
        cloud.scale = (1.8, 0.45, 0.45)
        cloud.keyframe_insert(data_path="location", frame=1)
        cloud.location.x += 1.0 if index == 0 else -0.8
        cloud.keyframe_insert(data_path="location", frame=frames)


def scene_starfield(gold, blue, dark, frames):
    """Dense 3D starfield with a curved planetary horizon and animated stellar parallax."""
    ground(dark)
    sphere("Planetary night horizon", (0, 8.5, -7.2), 9.0, material("Blue planet limb", (0.018, 0.055, 0.13), 0.25, 0.42, 0.12))
    for i in range(180):
        angle = (i * 2.399963229728653) % math.tau
        radius = 3.0 + (i % 17) * 0.48
        z = 1.2 + ((i * 37) % 29) * 0.22
        star = sphere("Distant star", (math.cos(angle)*radius, 5.0 + (i%11)*0.12, z),
                      0.025 + (i%5)*0.012, gold if i%7==0 else blue)
        key_scale(star, (1, frames), (0.7, 1.25 if i%3==0 else 0.9))
    sphere("Bright foreground star", (-1.2, 2.5, 3.0), 0.16, gold)


def scene_cosmic_shells(gold, blue, dark, frames):
    """Nested 3D shells of stars around an observer, illustrating Olbers' paradox."""
    sphere("Observer Earth", (0, 0, 1.1), 0.48, blue)
    for layer, radius in enumerate((1.8, 3.0, 4.3, 5.7)):
        shell = torus("Cosmic distance shell", (0, 0, 1.1), radius, 0.025, gold if layer%2==0 else blue,
                      (math.pi/2, 0, 0))
        shell.keyframe_insert(data_path="rotation_euler", frame=1)
        shell.rotation_euler.z += math.radians(18 + layer*7)
        shell.keyframe_insert(data_path="rotation_euler", frame=frames)
        count = 18 + layer*10
        for n in range(count):
            angle = math.tau*n/count
            star = sphere("Star on cosmic shell",
                          (radius*math.cos(angle), radius*math.sin(angle), 1.1 + 0.22*math.sin(angle*3)),
                          0.07 if layer<2 else 0.045, gold if n%4==0 else blue)
            key_scale(star, (1, frames), (0.65, 1.1))


def scene_expanding_spacetime(gold, blue, dark, frames):
    """Animated expanding spacetime grid with propagating, redshifting light."""
    for x in range(-5, 6):
        curve("Spacetime longitudinal grid", [(x*0.72, y, 0.15 + 0.018*x*x) for y in (-5,-2.5,0,2.5,5)],
              0.018, blue)
    for y in range(-5, 6):
        curve("Spacetime transverse grid", [(x, y*0.72, 0.15 + 0.018*y*y) for x in (-5,-2.5,0,2.5,5)],
              0.018, gold)
    for i in range(3):
        ray = curve("Traveling photon path",
                    [(-4.2, -2+i*2, 0.55+i*0.18), (-1.5, -1+i*2, 1.0+i*0.18),
                     (1.4, 0.2+i*2, 1.55+i*0.18), (4.3, 1.5+i*2, 2.0+i*0.18)],
                    0.055, gold if i==0 else blue)
        ray.keyframe_insert(data_path="scale", frame=1)
        ray.scale = (1.0, 1.0, 0.72)
        ray.keyframe_insert(data_path="scale", frame=frames)
    for i, x in enumerate((-3,0,3)):
        sphere("Expanding universe marker", (x, 0.2, 0.7+i*0.25), 0.18, gold if i==1 else blue)


def scene_cosmic_web(gold, blue, dark, frames):
    """Volumetric cosmic web of galaxy clusters connected by luminous filaments."""
    nodes = [(-4,1,1),(-2,3,2),(0,0,1.5),(2,3,2.6),(4,1,1.3),
             (-3,-2,2.4),(-1,-3,1),(2,-2,2.1),(4,-3,1.4),(0,4,1.1)]
    edges = [(0,1),(1,2),(2,3),(3,4),(0,5),(5,6),(6,2),(2,7),(7,8),(7,4),(1,9),(9,3),(5,2),(2,8)]
    for idx,(a,b) in enumerate(edges):
        curve("Cosmic web filament", [nodes[a],nodes[b]], 0.045, blue if idx%3 else gold)
    for idx,point in enumerate(nodes):
        cluster = sphere("Galaxy cluster", point, 0.28 if idx%3 else 0.43, gold if idx%2==0 else blue)
        key_scale(cluster, (1,frames), (0.85,1.12))
        for arm in range(3):
            angle = math.tau*arm/3
            sphere("Galaxy in cluster", (point[0]+math.cos(angle)*0.55,point[1]+math.sin(angle)*0.55,point[2]+0.18),
                   0.07, blue if arm%2 else gold)


def neon_material(name, color, strength=3.5):
    """Emission-first material for crisp neon geometry and compositor bloom."""
    mat = material(name, color, metallic=0.18, roughness=0.22, emission=strength)
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf and "Emission Strength" in bsdf.inputs:
        bsdf.inputs["Emission Strength"].default_value = strength
    return mat


def linear_animation(obj):
    """Keep orbital and wave motion at constant speed between authored keys."""
    animation = getattr(obj, "animation_data", None)
    action = getattr(animation, "action", None) if animation else None
    if not action:
        return
    for fc in getattr(action, "fcurves", []):
        for point in fc.keyframe_points:
            point.interpolation = "LINEAR"


def scene_neon_ellipse(gold, blue, dark, frames):
    """BAMO signature scene: neon ellipse, orbiting particles, chords and 3D trails."""
    ground(dark)
    cyan = neon_material("BAMO neon cyan", (0.025, 0.62, 0.95), 4.8)
    violet = neon_material("BAMO neon violet", (0.34, 0.12, 0.92), 3.8)
    amber = neon_material("BAMO neon amber", (1.0, 0.39, 0.055), 4.2)
    white = neon_material("BAMO particle core", (0.78, 0.94, 1.0), 5.5)
    center = (0.0, 0.0, 2.0)
    # Main ellipse and two faint construction orbits occupy different depths.
    for idx, (rx, ry, z, mat, bevel) in enumerate((
        (3.7, 5.25, 2.0, cyan, 0.045),
        (3.05, 4.35, 2.12, violet, 0.018),
        (4.25, 5.9, 1.82, amber, 0.014),
    )):
        pts = [(rx * math.cos(math.tau * i / 160), ry * math.sin(math.tau * i / 160), z)
               for i in range(161)]
        curve("Neon ellipse orbit %02d" % idx, pts, bevel, mat, cyclic=True)
    # A 3D chord mesh grows from sparse links to a dense mathematical web.
    nodes = []
    count = 18
    for i in range(count):
        angle = math.tau * i / count
        nodes.append((3.7 * math.cos(angle), 5.25 * math.sin(angle), 2.0 + 0.24 * math.sin(2 * angle)))
    for step in (2, 5, 7):
        for i in range(count):
            j = (i + step) % count
            if i < j:
                curve("Neon geometric chord", [nodes[i], nodes[j]], 0.012 if step > 2 else 0.022,
                      violet if step == 2 else cyan)
    # Persistent curved trails are actual 3D splines, not painted pixels.
    for i in range(8):
        angle = math.tau * i / 8
        trail = []
        for q in range(36):
            u = angle - 0.9 + 0.9 * q / 35
            trail.append((3.7 * math.cos(u), 5.25 * math.sin(u), 2.0 + 0.24 * math.sin(2*u)))
        curve("Accumulating particle light trail", trail, 0.028, amber if i % 2 else cyan)
    # A rotating parent gives the particle system continuous, deterministic motion.
    orbit = bpy.data.objects.new("BAMO orbital particle rig", None)
    bpy.context.scene.collection.objects.link(orbit)
    orbit.location = center
    for i in range(count):
        angle = math.tau * i / count
        particle = sphere("Orbiting luminous particle", (0, 0, 0), 0.105 if i % 3 else 0.16,
                          white if i % 5 == 0 else (amber if i % 3 == 0 else cyan))
        particle.parent = orbit
        particle.location = (3.7 * math.cos(angle), 5.25 * math.sin(angle), 0.24 * math.sin(2*angle))
    orbit.rotation_euler.z = 0.0
    orbit.keyframe_insert(data_path="rotation_euler", frame=1)
    orbit.rotation_euler.z = math.tau
    orbit.keyframe_insert(data_path="rotation_euler", frame=frames)
    linear_animation(orbit)
    # A luminous focal nucleus anchors the composition.
    sphere("Neon geometry focal nucleus", center, 0.24, white)


def scene_wave_interference(gold, blue, dark, frames):
    """Two coherent sources drive a continuous, animated 3D interference surface."""
    ground(dark)
    cyan = neon_material("Interference cyan wave", (0.02, 0.65, 1.0), 4.2)
    magenta = neon_material("Interference magenta wave", (0.92, 0.08, 0.48), 4.2)
    white = neon_material("Interference bright maxima", (0.82, 0.95, 1.0), 4.8)
    source_a, source_b = (-2.0, 0.0, 1.5), (2.0, 0.0, 1.5)

    # Two visible point sources and expanding circular wavefronts.
    for source, mat, label in ((source_a, magenta, "A"), (source_b, cyan, "B")):
        sphere("Wave source " + label, source, 0.22, white)
        for ring_index in range(6):
            ring = torus("Expanding wavefront " + label, source, 0.30 + ring_index * 0.48,
                         0.018, mat, (0.0, 0.0, 0.0))
            ring.scale = (0.08, 0.08, 0.08)
            ring.keyframe_insert(data_path="scale", frame=1)
            ring.scale = (1.0, 1.0, 1.0)
            ring.keyframe_insert(data_path="scale", frame=max(2, int(frames * (0.35 + ring_index * 0.1))))
            linear_animation(ring)

    # A connected 49x49 mesh replaces the old disconnected particle-only field.
    # Height is the sum of two coherent wave amplitudes; face colors reveal
    # constructive maxima and destructive minima across the whole surface.
    divisions = 49
    extent = 4.2
    vertices = []
    faces = []
    amplitudes = []
    for iy in range(divisions):
        y = -extent + (2.0 * extent * iy / (divisions - 1))
        for ix in range(divisions):
            x = -extent + (2.0 * extent * ix / (divisions - 1))
            da = math.hypot(x - source_a[0], y - source_a[1])
            db = math.hypot(x - source_b[0], y - source_b[1])
            amplitude = 0.5 * (math.cos(da * 2.7) + math.cos(db * 2.7))
            amplitudes.append(amplitude)
            vertices.append((x, y, 0.42 + amplitude * 0.72))
    for iy in range(divisions - 1):
        for ix in range(divisions - 1):
            a = iy * divisions + ix
            b = a + 1
            c = b + divisions
            d = a + divisions
            faces.append((a, b, c, d))

    mesh = bpy.data.meshes.new("Continuous interference height field")
    mesh.from_pydata(vertices, [], faces)
    mesh.materials.append(cyan)
    mesh.materials.append(magenta)
    mesh.materials.append(white)
    mesh.update()
    surface = bpy.data.objects.new("Continuous 3D interference surface", mesh)
    bpy.context.scene.collection.objects.link(surface)
    for polygon in mesh.polygons:
        values = [amplitudes[index] for index in polygon.vertices]
        mean_amp = sum(values) / len(values)
        polygon.material_index = 2 if abs(mean_amp) > 0.72 else (0 if mean_amp >= 0 else 1)
        polygon.use_smooth = True

    # Animate the wave phase through a shape key so the interference pattern evolves.
    basis = surface.shape_key_add(name="Basis")
    animated = surface.shape_key_add(name="Travelling wave phase")
    for index, vertex in enumerate(animated.data):
        x, y, _ = vertices[index]
        da = math.hypot(x - source_a[0], y)
        db = math.hypot(x - source_b[0], y)
        amplitude = 0.5 * (math.cos(da * 2.7 + 0.9) + math.cos(db * 2.7 + 0.9))
        vertex.co.z = 0.42 + amplitude * 0.72
    animated.value = 0.0
    animated.keyframe_insert(data_path="value", frame=1)
    animated.value = 1.0
    animated.keyframe_insert(data_path="value", frame=frames)
    linear_animation(animated)

    # Fine luminous grid traces make the continuous height field readable in depth.
    for offset in (-3.0, -1.5, 0.0, 1.5, 3.0):
        curve("Interference field grid X", [(-extent, offset, 0.48), (extent, offset, 0.48)], 0.006, blue)
        curve("Interference field grid Y", [(offset, -extent, 0.48), (offset, extent, 0.48)], 0.006, gold)
    curve("Interference horizontal axis", [(-4.5, 0, 0.18), (4.5, 0, 0.18)], 0.012, blue)
    curve("Interference vertical axis", [(0, -4.5, 0.18), (0, 4.5, 0.18)], 0.012, gold)

def hex_rgb(value):
    raw = str(value).lstrip("#")
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
            objects[item["id"]] = curve(name, [start, finish], 0.025, mats[item["material"]]); continue
        obj = bpy.context.object; obj.name = name; obj.scale = scale
        obj.rotation_euler = tuple(item["rotation"]); assign(obj, mats[item["material"]]); smooth(obj)
        objects[item["id"]] = obj
        action, amount = item["action"], float(item["action_amount"])
        base_loc, base_rot, base_scale = obj.location.copy(), obj.rotation_euler.copy(), obj.scale.copy()
        # Five samples so pulse/orbit are visible. Two endpoints make sin(0) and
        # sin(2π) identical, which previously froze pulse motion.
        for factor in (0.0, 0.25, 0.5, 0.75, 1.0):
            frame = 1 if factor <= 0 else max(2, int(round(1 + (frames - 1) * factor)))
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
    # Denoise CPU Cycles output to remove speckling from low-sample renders.
    scene.cycles.use_denoising = bool(cfg.get("denoise", True))
    try:
        scene.cycles.denoiser = "OPENIMAGEDENOISE"
    except (AttributeError, TypeError, ValueError):
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
