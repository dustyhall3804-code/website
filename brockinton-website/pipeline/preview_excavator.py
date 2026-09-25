"""Quick look-dev renders of build/excavator.blend (not part of the site build)."""
import bpy, math, os, sys
from mathutils import Vector
HERE = os.path.dirname(os.path.abspath(__file__))
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, "build", "excavator.blend"))
sc = bpy.context.scene
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
sky = w.node_tree.nodes.new("ShaderNodeTexSky")
try: sky.sky_type = 'NISHITA'
except Exception: pass
sky.sun_elevation = math.radians(18); sky.sun_rotation = math.radians(215)
w.node_tree.links.new(sky.outputs[0], w.node_tree.nodes["Background"].inputs[0])
w.node_tree.nodes["Background"].inputs[1].default_value = 0.35
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", 'SUN')); sc.collection.objects.link(sun)
sun.data.energy = 3.5; sun.data.angle = math.radians(1.5)
sun.rotation_euler = (math.radians(72), 0, math.radians(215 - 180 + 90))
bpy.ops.mesh.primitive_plane_add(size=80); g = bpy.context.object
m = bpy.data.materials.new("g"); m.use_nodes = True
m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.12, 0.1, 0.05, 1); g.data.materials.append(m)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
sc.render.engine = 'CYCLES'; sc.cycles.samples = 24; sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y = 900, 560
sc.view_settings.view_transform = 'AgX'
shots = [(0.0, (-9, -8, 4), (0.5, 2, 2)), (0.1, (9, -4, 3), (0, 4, 2)), (0.16, (-8, 10, 5), (1, 3, 2)), (0.13, (7, 6, 2.5), (0, 4, 2.5))]
for i, (p, pos, tgt) in enumerate(shots):
    sc.frame_set(round(p * sc.frame_end))
    cam.location = pos
    d = Vector(tgt) - Vector(pos)
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = 30
    sc.render.filepath = os.path.join(sys.argv[-1], f"exc_{i}.png")
    bpy.ops.render.render(write_still=True)
