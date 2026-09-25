"""Render the scroll sequence from build/scene.blend.

`--step 2` renders every other frame of the sequence; running again without it
fills in the rest (existing frames are skipped).

    python render_frames.py --orient landscape --frames 180 [--start 0 --end 180]
                            [--res 1280] [--samples 28] [--only 0.1,0.4]

Writes build/frames/<orient>/f_0000.png ... ; encode with encode_frames.mjs.
"""
import argparse
import math
import os
import sys

import bpy
import bmesh
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common as C  # noqa: E402
import terrain_np as T  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
ap = argparse.ArgumentParser()
ap.add_argument("--orient", default="landscape", choices=["landscape", "portrait"])
ap.add_argument("--frames", type=int, default=180)
ap.add_argument("--start", type=int, default=0)
ap.add_argument("--end", type=int, default=None)
ap.add_argument("--res", type=int, default=1280, help="long edge in pixels")
ap.add_argument("--samples", type=int, default=28)
ap.add_argument("--only", default=None, help="comma-separated progress values (look-dev)")
ap.add_argument("--out", default=None)
ap.add_argument("--threads", type=int, default=0)
ap.add_argument("--step", type=int, default=1, help="render every Nth frame (2 = half-rate preview)")
args = ap.parse_args(argv)

bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, "build", "scene.blend"))
scene = bpy.context.scene
scene.cycles.samples = args.samples
scene.cycles.device = 'CPU'
if args.threads:
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = args.threads

if args.orient == "landscape":
    W, H = args.res, round(args.res * 9 / 16)
else:
    W, H = round(args.res * 9 / 16), args.res
scene.render.resolution_x, scene.render.resolution_y = W, H
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGB'
aspect = W / H

out_dir = args.out or os.path.join(HERE, "build", "frames", args.orient)
os.makedirs(out_dir, exist_ok=True)

terrain = bpy.data.objects["Terrain"]
me = terrain.data
xy = np.load(os.path.join(HERE, "build", "terrain_xy.npy"))
X, Y = xy[:, 0], xy[:, 1]
orig = T.height(X, Y, 0, 0)
pitm = T.pit_mask(X, Y)
spm = T.spoil_mask(X, Y)
water = bpy.data.objects["Water"]
fx = bpy.data.objects["FX"]
cam = bpy.data.objects["Camera"]
ground_mat = bpy.data.materials["Ground"]
wl_node = ground_mat.node_tree.nodes["water_level"]
ANIM_LAST = scene.frame_end


def set_terrain(pit, spoil):
    z = orig - C.PIT_DEPTH * pit * pitm + C.SPOIL_HEIGHT * spoil * spm
    co = np.empty(len(X) * 3, np.float32)
    co[0::3], co[1::3], co[2::3] = X, Y, z
    me.vertices.foreach_set("co", co)
    me.attributes["spoil"].data.foreach_set("value", (C.SPOIL_HEIGHT * spoil * spm).astype(np.float32))
    me.update()


def set_fx(p, cam_pos):
    bm = bmesh.new()
    cl = bm.loops.layers.color.new("Col")
    uv = bm.loops.layers.uv.new("UV")
    cp = Vector(cam_pos)
    for prt in C.particles(p):
        pos = Vector(prt["pos"])
        if prt["kind"] == "clod":
            g = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=prt["size"] * 0.5)
            bmesh.ops.translate(bm, vec=pos, verts=g["verts"])
            for f in {f for v in g["verts"] for f in v.link_faces}:
                f.material_index = 1
            continue
        fwd = (cp - pos).normalized()
        right = fwd.cross(Vector((0, 0, 1))).normalized()
        up = right.cross(fwd).normalized()
        s = prt["size"] * 0.5
        ang = C.hash1(prt["seed"] + 5) * math.tau
        r2 = right * math.cos(ang) + up * math.sin(ang)
        u2 = -right * math.sin(ang) + up * math.cos(ang)
        vs = [bm.verts.new(pos + (r2 * a + u2 * b) * s) for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        f = bm.faces.new(vs)
        if prt["kind"] == "smoke":
            k = 0.62 - 0.45 * prt.get("dark", 0)
            col = (k * 0.9, k * 0.9, k * 0.92)
        else:
            col = (0.52, 0.36, 0.25)
        for lp, (a, b) in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
            lp[cl] = (*col, prt["alpha"])
            lp[uv].uv = (a, b)
    bm.to_mesh(fx.data)
    bm.free()
    fx.data.update()


def set_camera(p):
    pos, tgt, lens = C.camera_at(p, aspect)
    cam.location = pos
    d = Vector(tgt) - Vector(pos)
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    vfov = C.fov_for_aspect(lens, aspect)
    cam.data.sensor_fit = 'VERTICAL'
    cam.data.angle_y = vfov
    sx, sy = C.lens_shift(aspect)
    m = max(W, H)
    cam.data.shift_x = sx / 2 * W / m
    cam.data.shift_y = sy / 2 * H / m
    # gentle depth of field on close shots only
    dist = d.length
    cam.data.dof.use_dof = dist < 14
    cam.data.dof.focus_distance = dist
    cam.data.dof.aperture_fstop = 4.0
    return pos


def frame(p, path):
    level, w = C.water_level(p)
    set_terrain(C.depth_at(p), C.spoil_at(p))
    water.location.z = level if w > 0.001 else -50
    wl_node.outputs[0].default_value = level if w > 0.001 else -50
    scene.frame_set(int(p * ANIM_LAST), subframe=(p * ANIM_LAST) % 1.0)
    cp = set_camera(p)
    set_fx(p, cp)
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


if args.only:
    for p in [float(x) for x in args.only.split(",")]:
        frame(p, os.path.join(out_dir, f"look_{args.orient}_{p:.3f}.png"))
else:
    end = args.end if args.end is not None else args.frames
    for i in range(args.start, end, args.step):
        path = os.path.join(out_dir, f"f_{i:04d}.png")
        if os.path.exists(path):
            continue
        frame(i / (args.frames - 1), path)
        print(f"frame {i}/{args.frames}", flush=True)
