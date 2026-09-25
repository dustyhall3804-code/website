"""Render the tree prototypes as alpha impostor cards for the real-time treeline.

Output: build/tex/trees.png (3 x 2 grid of cards, 2048x2048, straight alpha).
Card order: cedar, oak, oak, oak, pine, pine (row-major from the top-left).
"""
import math
import os
import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, "build", "scene.blend"))
src = bpy.context.scene
cols = sorted([c for c in bpy.data.collections if c.name.startswith("Tree_") and c.name.endswith("_col")],
              key=lambda c: c.name)
sc = bpy.data.scenes.new("Cards")
sc.world = src.world
sun = bpy.data.objects["Sun"]
sc.collection.objects.link(sun)
sc.render.engine = 'CYCLES'
sc.cycles.samples = 48
sc.cycles.use_denoising = True
sc.cycles.transparent_max_bounces = 64
sc.render.film_transparent = True
sc.view_settings.view_transform = src.view_settings.view_transform
sc.view_settings.exposure = src.view_settings.exposure
sc.render.resolution_x, sc.render.resolution_y = 682, 1024
sc.render.image_settings.color_mode = 'RGBA'
cam = bpy.data.objects.new("CardCam", bpy.data.cameras.new("CardCam"))
sc.collection.objects.link(cam)
sc.camera = cam
cam.data.type = 'ORTHO'
out = []
for i, c in enumerate(cols[:6]):
    e = bpy.data.objects.new(f"card{i}", None)
    e.instance_type = 'COLLECTION'
    e.instance_collection = c
    sc.collection.objects.link(e)
    for o in sc.collection.objects:
        if o.name.startswith("card"):
            o.hide_render = o is not e
    H = 26.0
    cam.data.ortho_scale = H
    # look from the south-west so the lit side faces the viewer, as in the hero
    cam.location = (-60, -60, H / 2 - 0.5)
    cam.rotation_euler = (Vector((0, 0, H / 2 - 0.5)) - cam.location).to_track_quat('-Z', 'Y').to_euler()
    path = os.path.join(HERE, "build", "tex", f"_card{i}.png")
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True, scene=sc.name)
    out.append(path)
    print("card", i, c.name)

# 3 x 2 grid of 682 x 1024 cards; Blender image rows run bottom-up
atlas = bpy.data.images.new("atlas", 2048, 2048, alpha=True)
import numpy as np  # noqa: E402
px = np.zeros((2048, 2048, 4), np.float32)
for i, path in enumerate(out):
    im = bpy.data.images.load(path)
    a = np.array(im.pixels[:], np.float32).reshape(1024, 682, 4)
    col, row = i % 3, i // 3
    y0 = (1 - row) * 1024
    px[y0:y0 + 1024, col * 683:col * 683 + 682] = a
atlas.pixels = px.ravel()
atlas.filepath_raw = os.path.join(HERE, "build", "tex", "trees.png")
atlas.file_format = 'PNG'
atlas.save()
print("wrote trees.png", [c.name for c in cols[:6]])
