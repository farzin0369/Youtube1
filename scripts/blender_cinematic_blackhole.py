import bpy, math, random
from mathutils import Vector
random.seed(110)

# Reset and create a cinematic, stylized 3D black-hole shot.
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
for datablocks in (bpy.data.materials, bpy.data.curves, bpy.data.meshes, bpy.data.cameras, bpy.data.lights):
    pass

scene = bpy.context.scene
engine_ids = {item.identifier for item in scene.render.bl_rna.properties["engine"].enum_items}
scene.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in engine_ids else "BLENDER_EEVEE"
scene.render.resolution_x = 960
scene.render.resolution_y = 540
scene.render.resolution_percentage = 100
scene.render.fps = 24
scene.frame_start = 1
scene.frame_end = 144
scene.render.image_settings.file_format = "FFMPEG"
scene.render.ffmpeg.format = "MPEG4"
scene.render.ffmpeg.codec = "H264"
scene.render.ffmpeg.constant_rate_factor = "MEDIUM"
scene.render.filepath = "/tmp/blackhole_cinematic.mp4"
scene.render.image_settings.color_mode = "RGB"
scene.render.film_transparent = False
scene.render.resolution_percentage = 100
scene.world.color = (0.001, 0.002, 0.008)
scene.view_settings.view_transform = "AgX"
scene.render.image_settings.color_mode = "RGB"
try:
    scene.eevee.taa_render_samples = 16
except Exception:
    pass

def emission(name, color, strength):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    n = m.node_tree.nodes
    n.clear()
    out = n.new("ShaderNodeOutputMaterial")
    e = n.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = (*color, 1)
    e.inputs["Strength"].default_value = strength
    m.node_tree.links.new(e.outputs["Emission"], out.inputs["Surface"])
    return m

def principled(name, color, metallic=0.0, roughness=0.35):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    p = m.node_tree.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value = (*color, 1)
    p.inputs["Metallic"].default_value = metallic
    p.inputs["Roughness"].default_value = roughness
    return m

black = principled("Event horizon | lightless black", (0.0004,0.0006,0.001), 0.15, 0.2)
gold = emission("Hot plasma | amber", (1.0,0.19,0.025), 3.2)
hot = emission("Inner plasma | near white gold", (1.0,0.68,0.25), 5.0)
violet = emission("Outer plasma | ionized violet", (0.20,0.10,1.0), 1.7)
blue = emission("Lens glint | cyan", (0.12,0.52,1.0), 2.0)
star_mat = emission("Distant stars", (0.52,0.66,1.0), 1.6)

# Black spherical event horizon.
bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=1.18, location=(0,0,0))
core = bpy.context.object
core.name = "Black hole | event horizon"
core.data.materials.append(black)
bpy.ops.object.shade_smooth()

# Thin, layered hot accretion rings tilted toward the camera.
def ring(name, major, minor, mat, tilt=math.radians(69), xrot=0):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor, major_segments=128, minor_segments=16, location=(0,0,0))
    ob = bpy.context.object
    ob.name = name
    ob.rotation_euler[0] = tilt
    ob.rotation_euler[1] = xrot
    ob.data.materials.append(mat)
    for p in ob.data.polygons: p.use_smooth = True
    return ob

ring("Photon ring | incandescent gold", 1.36, 0.035, hot)
ring("Inner accretion | white-hot rim", 1.57, 0.055, hot)
ring("Accretion disk | amber plasma", 1.82, 0.12, gold)
ring("Accretion disk | violet outer rim", 2.12, 0.045, violet)
ring("Lens halo | cold blue", 1.28, 0.018, blue, tilt=math.radians(76), xrot=math.radians(7))

# A scattering of orbiting plasma beads gives the disk depth and scale.
for i in range(180):
    a = random.random() * math.tau
    r = random.uniform(1.48, 2.28)
    z = random.gauss(0, 0.055)
    pos = (r*math.cos(a), r*math.sin(a)*0.48, z)
    size = random.uniform(0.009, 0.028)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=size, location=pos)
    bead = bpy.context.object
    bead.name = "Plasma particle"
    bead.data.materials.append(random.choice([gold, hot, violet]))
    # Animate each particle around the black hole, at different angular speeds.
    bead.location = pos
    bead.keyframe_insert(data_path="location", frame=1)
    a2 = a + random.uniform(0.45, 1.25)
    bead.location = (r*math.cos(a2), r*math.sin(a2)*0.48, z)
    bead.keyframe_insert(data_path="location", frame=144)

# Deep-space starfield, intentionally behind the subject.
for i in range(320):
    x, y, z = random.uniform(-12,12), random.uniform(-7,7), random.uniform(-5,-1.5)
    size = random.uniform(0.008, 0.022)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=size, location=(x,y,z))
    star = bpy.context.object
    star.name = "Deep space star"
    star.data.materials.append(star_mat)

# Subtle rim lighting and volumetric-like atmosphere.
def area_light(name, loc, color, power, size):
    data = bpy.data.lights.new(name, "AREA")
    data.energy = power
    data.color = color
    data.shape = "DISK"
    data.size = size
    ob = bpy.data.objects.new(name, data)
    scene.collection.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = (Vector((0,0,0))-ob.location).to_track_quat("-Z","Y").to_euler()
    return ob
area_light("Amber plasma bounce", (1.8,2.5,3.5), (1.0,0.22,0.055), 850, 4.0)
area_light("Blue edge light", (-3.0,-1.5,1.4), (0.12,0.24,1.0), 1100, 3.5)

# Camera begins wide, then slowly pushes in and arcs around the subject.
bpy.ops.object.camera_add(location=(0.25,-8.7,4.4))
cam = bpy.context.object
scene.camera = cam
cam.data.lens = 48
target = Vector((0,0,0))
cam.rotation_euler = (target- cam.location).to_track_quat("-Z","Y").to_euler()
cam.location = (0.25,-8.7,4.4)
cam.keyframe_insert(data_path="location", frame=1)
cam.keyframe_insert(data_path="rotation_euler", frame=1)
cam.location = (0.9,-7.8,3.65)
cam.rotation_euler = (target-cam.location).to_track_quat("-Z","Y").to_euler()
cam.keyframe_insert(data_path="location", frame=144)
cam.keyframe_insert(data_path="rotation_euler", frame=144)
for ob in scene.objects:
    if ob.animation_data and ob.animation_data.action:
        for fc in ob.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"

# Bloom/glare in the compositor for a filmic plasma glow.
scene.use_nodes = True
tree = scene.node_tree
tree.nodes.clear()
rl = tree.nodes.new("CompositorNodeRLayers")
glare = tree.nodes.new("CompositorNodeGlare")
glare.glare_type = "FOG_GLOW"
glare.quality = "MEDIUM"
glare.threshold = 0.8
comp = tree.nodes.new("CompositorNodeComposite")
tree.links.new(rl.outputs["Image"], glare.inputs["Image"])
tree.links.new(glare.outputs["Image"], comp.inputs["Image"])

scene.render.filepath = "/tmp/blackhole_cinematic.mp4"
scene.frame_set(1)
bpy.ops.render.render(animation=True)
print("CINEMATIC_RENDER_OK=/tmp/blackhole_cinematic.mp4")
