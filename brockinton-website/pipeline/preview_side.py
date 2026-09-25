import bpy, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, "build", "excavator.blend"))
sc = bpy.context.scene
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.6, 0.65, 0.7, 1)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = 'ORTHO'; cam.data.ortho_scale = 14
cam.location = (20, 4.5, 1.5); cam.rotation_euler = (math.pi/2, 0, math.pi/2)
sc.render.engine = 'BLENDER_WORKBENCH'
sc.display.shading.color_type = 'MATERIAL'
sc.render.resolution_x, sc.render.resolution_y = 700, 500
for p in [float(x) for x in sys.argv[-2].split(',')]:
    sc.frame_set(round(p * sc.frame_end))
    sc.render.filepath = os.path.join(sys.argv[-1], f"side_{p:.3f}.png")
    bpy.ops.render.render(write_still=True)
