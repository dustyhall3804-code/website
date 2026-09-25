"""Model, rig and animate a 20-25 t class tracked excavator, export GLB.

Run:  python build_excavator.py  (with the `bpy` module)  or
      blender -b -P build_excavator.py

Outputs  build/excavator.glb  and  build/excavator.blend
The node animation `dig` covers progress 0..1 over ANIM_FRAMES frames and is
generated from common.py, so hydraulic cylinders, bucket linkage and swing are
all solved from the same pin geometry every frame.
"""
import math
import os
import sys

import bpy  # noqa: F401  (must load before bmesh/mathutils)
import bmesh
from mathutils import Vector, Matrix, noise

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common as C  # noqa: E402
from bl_util import (srgb, reset, material, new_obj, empty, box, cylinder,  # noqa: E402
                     extrude_profile, catmull_closed, text_mesh, paint_vcol)

OUT = os.path.join(HERE, "build")
os.makedirs(OUT, exist_ok=True)
FONT = os.path.join(HERE, "fonts", "BarlowCondensed_800ExtraBold.ttf")
ANIM_FRAMES = 481          # samples of progress 0..1 (glTF clip = 16 s @ 30 fps)

reset()
scene = bpy.context.scene

# ------------------------------------------------------------------ materials
WHITE = (1, 1, 1)
M_PAINT = material("Paint", WHITE, rough=0.42, coat=0.2)
M_UNDER = material("Undercarriage", WHITE, rough=0.82, metal=0.15)
M_STEEL = material("Steel", srgb("#34322f"), rough=0.45, metal=0.7, use_vcol=False)
M_CHROME = material("Chrome", (0.86, 0.86, 0.86), rough=0.09, metal=1.0, use_vcol=False)
M_GLASS = material("Glass", (0.012, 0.015, 0.018), rough=0.04, metal=0.2, use_vcol=False)
M_BLACK = material("Trim", srgb("#141414"), rough=0.55, use_vcol=False)
M_DECAL = material("Decal", srgb("#121110"), rough=0.5, use_vcol=False)
M_LENS = material("Lens", (0.8, 0.8, 0.78), rough=0.08, use_vcol=False)
M_LOAD = material("Load", WHITE, rough=0.96)

YELLOW = srgb("#F2B41C")
DUST = srgb("#A06A45")
CLAY_MUD = srgb("#55291a")
DRY_MUD = srgb("#6A4632")
STEEL_DARK = srgb("#2B2926")


def mix(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(x + (y - x) * t for x, y in zip(a, b))


def sstep(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def paint_fn(z_clean=1.6, z_dirty=0.4, top_dust=0.25):
    def fn(p, n):
        nz = noise.noise(p * 2.3) * 0.5 + noise.noise(p * 7.0) * 0.25
        f = sstep(z_clean, z_dirty, p.z + nz * 0.35) * 0.7
        f += max(n.z, 0) * top_dust * (0.6 + nz)          # dust settles on top faces
        c = mix(YELLOW, DUST, f)
        # a little paint variation / sun fade
        k = 1.0 + 0.05 * noise.noise(p * 0.8)
        return tuple(x * k for x in c)
    return fn


def under_fn(p, n):
    nz = noise.noise(p * 3.1) * 0.6 + noise.noise(p * 11.0) * 0.3
    wet = sstep(0.55, 0.0, p.z + nz * 0.25)
    dry = sstep(1.0, 0.3, p.z + nz * 0.4)
    c = mix(STEEL_DARK, DRY_MUD, dry * 0.5)
    return mix(c, CLAY_MUD, wet * 0.85)


def bucket_fn(p, n):
    nz = noise.noise(p * 4.0) * 0.5 + noise.noise(p * 13.0) * 0.3
    c = mix(YELLOW, DRY_MUD, 0.55 + nz * 0.5)
    return mix(c, CLAY_MUD, 0.4 + nz * 0.4)


def load_fn(p, n):
    nz = noise.noise(p * 6.0) * 0.5 + noise.noise(p * 17.0) * 0.4
    return mix(srgb("#7A3A1F"), srgb("#4A2616"), 0.5 + nz)


# ------------------------------------------------------------------ hierarchy
root = empty("Excavator")
under_bm = bmesh.new()

# ------------------------------------------------------------- undercarriage
TRACK_X = 1.19
SHOE_W = 0.60
LOOP_R = 0.44
LOOP_Z = 0.47
SPROCKET_Y, IDLER_Y = -1.83, 1.83


def loop_point(s):
    """Position/tangent on the track loop for arc length s (y, z)."""
    straight = IDLER_Y - SPROCKET_Y
    arc = math.pi * LOOP_R
    total = 2 * straight + 2 * arc
    s %= total
    if s < straight:                                          # bottom run, rear -> front
        return (SPROCKET_Y + s, LOOP_Z - LOOP_R), (1, 0), (0, -1)
    s -= straight
    if s < arc:                                               # around the idler
        a = -math.pi / 2 + s / LOOP_R
        return (IDLER_Y + LOOP_R * math.cos(a), LOOP_Z + LOOP_R * math.sin(a)), \
            (-math.sin(a), math.cos(a)), (math.cos(a), math.sin(a))
    s -= arc
    if s < straight:                                          # top run, front -> rear
        return (IDLER_Y - s, LOOP_Z + LOOP_R), (-1, 0), (0, 1)
    s -= straight
    a = math.pi / 2 + s / LOOP_R                              # around the sprocket
    return (SPROCKET_Y + LOOP_R * math.cos(a), LOOP_Z + LOOP_R * math.sin(a)), \
        (-math.sin(a), math.cos(a)), (math.cos(a), math.sin(a))


total_len = 2 * (IDLER_Y - SPROCKET_Y) + 2 * math.pi * LOOP_R
N_SHOES = 52
for side in (-1, 1):
    x = side * TRACK_X
    for i in range(N_SHOES):
        (y, z), (ty, tz), (ny, nz) = loop_point(i * total_len / N_SHOES)
        m = Matrix(((1, 0, 0), (0, ty, ny), (0, tz, nz))).to_4x4()
        m.translation = (x, y, z)
        g = bmesh.ops.create_cube(under_bm, size=1.0)
        v = g["verts"]
        bmesh.ops.scale(under_bm, vec=(SHOE_W, 0.175, 0.045), verts=v)
        bmesh.ops.transform(under_bm, matrix=m, verts=v)
        g = bmesh.ops.create_cube(under_bm, size=1.0)       # grouser bar
        v = g["verts"]
        bmesh.ops.scale(under_bm, vec=(SHOE_W, 0.035, 0.035), verts=v)
        bmesh.ops.translate(under_bm, vec=(0, -0.05, 0.035), verts=v)
        bmesh.ops.transform(under_bm, matrix=m, verts=v)
    # track frame, rollers, sprocket, idler
    box(under_bm, (x, 0, 0.47), (0.36, 3.2, 0.5), bevel=0.05)
    box(under_bm, (x * 0.93, 0, 0.73), (0.44, 3.0, 0.06), bevel=0.02)
    for k in range(7):
        yy = -1.32 + k * 0.44
        cylinder(under_bm, (x - 0.26, yy, 0.155), (x + 0.26, yy, 0.155), 0.105, segs=16)
    for yy in (-0.7, 0.75):
        cylinder(under_bm, (x - 0.2, yy, 0.8), (x + 0.2, yy, 0.8), 0.075, segs=14)
    cylinder(under_bm, (x - 0.24, IDLER_Y, LOOP_Z), (x + 0.24, IDLER_Y, LOOP_Z), 0.37, segs=32)
    cylinder(under_bm, (x - 0.22, SPROCKET_Y, LOOP_Z), (x + 0.22, SPROCKET_Y, LOOP_Z), 0.4, segs=32)
    cylinder(under_bm, (x - side * 0.2, SPROCKET_Y, LOOP_Z), (x - side * 0.55, SPROCKET_Y, LOOP_Z), 0.26, segs=24)
    for k in range(10):                                      # sprocket teeth
        a = k / 10 * 2 * math.pi
        c = Vector((x, SPROCKET_Y + 0.42 * math.cos(a), LOOP_Z + 0.42 * math.sin(a)))
        box(under_bm, c, (0.12, 0.07, 0.07))

# carbody and swing bearing
box(under_bm, (0, 0, 0.7), (1.9, 1.7, 0.42), bevel=0.06)
box(under_bm, (0, 0, 0.6), (2.2, 0.9, 0.3), bevel=0.05)
cylinder(under_bm, (0, 0, 0.9), (0, 0, C.SWING_Z), 0.96, segs=48)
undercarriage = new_obj("Undercarriage", under_bm, M_UNDER, root, smooth_angle=35)
paint_vcol(undercarriage, under_fn)

# ------------------------------------------------------------------- upper
upper = empty("Upper", root, (0, 0, C.SWING_Z))


def extrude_plan(bm, pts, z0, z1, bevel=0.0):
    """Extrude a plan-view (x, y) polygon along Z."""
    vs0 = [bm.verts.new((x, y, z0)) for x, y in pts]
    vs1 = [bm.verts.new((x, y, z1)) for x, y in pts]
    n = len(pts)
    faces = [bm.faces.new(vs0[::-1]), bm.faces.new(vs1)]
    for i in range(n):
        j = (i + 1) % n
        faces.append(bm.faces.new((vs0[i], vs0[j], vs1[j], vs1[i])))
    bmesh.ops.recalc_face_normals(bm, faces=faces)
    if bevel:
        edges = list({e for f in faces for e in f.edges})
        bmesh.ops.bevel(bm, geom=edges, offset=bevel, segments=3, profile=0.5, affect='EDGES',
                        clamp_overlap=True)


bm = bmesh.new()
box(bm, (0, -0.35, 0.09), (2.54, 3.3, 0.18), bevel=0.03)                  # deck
TAIL_R = 2.72
# counterweight: plan outline from the left inner corner around the tail arc
a0 = math.asin(1.27 / TAIL_R)
outline = [(-1.27, -1.9)]
for k in range(19):
    a = -math.pi / 2 - a0 + k * (2 * a0 / 18)
    outline.append((TAIL_R * math.cos(a), TAIL_R * math.sin(a)))
outline.append((1.27, -1.9))
extrude_plan(bm, outline, 0.1, 1.2, bevel=0.07)
box(bm, (0.46, -1.15, 0.64), (1.62, 1.55, 0.92), bevel=0.06)               # engine hood
box(bm, (-0.8, -1.25, 0.6), (0.92, 1.3, 0.84), bevel=0.06)                  # left compartment
box(bm, (0.95, 0.47, 0.56), (0.64, 1.56, 0.78), bevel=0.06)                 # tank / tool box
# boom foot brackets and boom-cylinder lugs
for s in (-1, 1):
    extrude_profile(bm, [(0.1, 0.18), (1.05, 0.18), (1.02, 0.9), (0.72, 1.18), (0.42, 1.05), (0.1, 0.5)],
                    C.ARM_X + s * 0.3, C.ARM_X + s * 0.38, bevel=0.01)
    extrude_profile(bm, [(0.98, 0.18), (1.42, 0.14), (1.42, -0.12), (1.2, -0.16), (0.98, 0.0)],
                    C.ARM_X + s * 0.36, C.ARM_X + s * 0.49, bevel=0.01)
upper_body = new_obj("UpperBody", bm, M_PAINT, upper, smooth_angle=35)
paint_vcol(upper_body, paint_fn(z_clean=1.45, z_dirty=0.8, top_dust=0.18))

# dark details: grilles, walkway, steps, counterweight band
bm = bmesh.new()
for k in range(9):
    box(bm, (0.46, -1.8 + k * 0.16, 1.105), (1.3, 0.06, 0.012))
box(bm, (1.28, -1.15, 0.72), (0.02, 1.1, 0.5))                              # side grille
box(bm, (0.95, 0.47, 0.955), (0.6, 1.5, 0.02))                              # walkway plate
box(bm, (1.33, 0.95, 0.25), (0.1, 0.4, 0.03))                               # step
box(bm, (0, -2.66, 0.2), (1.7, 0.1, 0.12), bevel=0.02)                       # tail band
cylinder(bm, (0.2, 0.72, 0.88), (0.36, 0.72, 0.88), 0.12)                    # pins at foot
new_obj("UpperTrim", bm, M_BLACK, upper)

# handrails (painted), exhaust (steel), mirror
bm = bmesh.new()
for y0, y1 in ((-0.25, 1.15),):
    for x in (1.2,):
        pts = [(x, y0, 0.96), (x, y0, 1.5), (x, y1, 1.5), (x, y1, 0.96)]
        for a, b in zip(pts, pts[1:]):
            cylinder(bm, a, b, 0.022, segs=10)
cylinder(bm, (1.2, -1.95, 1.12), (1.2, -0.3, 1.12), 0.02, segs=10)
rails = new_obj("Handrails", bm, M_PAINT, upper, smooth_angle=60)
paint_vcol(rails, paint_fn())

bm = bmesh.new()
cylinder(bm, (0.95, -1.35, 1.1), (0.95, -1.35, 1.55), 0.055, segs=16)
cylinder(bm, (0.95, -1.35, 1.55), (0.95, -1.28, 1.62), 0.055, segs=16)
cylinder(bm, (-0.2, -1.6, 1.1), (-0.2, -1.6, 1.34), 0.12, segs=20)          # pre-cleaner
cylinder(bm, (-1.3, 1.1, 1.3), (-1.45, 1.25, 1.75), 0.012, segs=8)          # mirror arm
box(bm, (-1.47, 1.26, 1.8), (0.06, 0.2, 0.26), bevel=0.01)
new_obj("Exhaust", bm, M_STEEL, upper, smooth_angle=50)
empty("fx_exhaust", upper, (0.95, -1.26, 1.64))

# cab: frame, glass, roof, seat silhouette
CAB = dict(x0=-1.27, x1=-0.33, y0=-0.62, y1=1.2, z0=0.18, z1=1.98)
bm = bmesh.new()
x0, x1, y0, y1, z0, z1 = (CAB[k] for k in ("x0", "x1", "y0", "y1", "z0", "z1"))
posts = [((x0, y1, 0.55), (x0, y1 - 0.12, z1)), ((x1, y1, 0.55), (x1, y1 - 0.12, z1)),
         ((x0, y0, z0), (x0, y0, z1)), ((x1, y0, z0), (x1, y0, z1)),
         ((x0, 0.25, 0.55), (x0, 0.25, z1))]
for a, b in posts:
    box(bm, ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (a[2] + b[2]) / 2), (0.07, 0.07, b[2] - a[2]))
box(bm, ((x0 + x1) / 2, (y0 + y1) / 2 - 0.04, z1 + 0.04), (x1 - x0 + 0.06, y1 - y0 + 0.02, 0.09), bevel=0.03)
box(bm, ((x0 + x1) / 2, y1 - 0.02, 0.38), (x1 - x0, 0.08, 0.36), bevel=0.02)  # front lower panel
box(bm, (x0 + 0.02, (y0 + y1) / 2, 0.38), (0.05, y1 - y0, 0.4), bevel=0.01)
box(bm, (x1 - 0.02, (y0 + y1) / 2, 0.38), (0.05, y1 - y0, 0.4), bevel=0.01)
box(bm, ((x0 + x1) / 2, y0 + 0.02, (z0 + z1) / 2), (x1 - x0, 0.05, z1 - z0))   # rear wall
cab_frame = new_obj("CabFrame", bm, M_BLACK, upper, smooth_angle=40)

bm = bmesh.new()
gv = [bm.verts.new(v) for v in [(x0 + 0.02, y1 - 0.03, 0.56), (x1 - 0.02, y1 - 0.03, 0.56),
                                 (x1 - 0.02, y1 - 0.14, z1 - 0.02), (x0 + 0.02, y1 - 0.14, z1 - 0.02)]]
bm.faces.new(gv)
for xs in (x0 + 0.01, x1 - 0.01):
    gv = [bm.verts.new(v) for v in [(xs, y0 + 0.05, 0.58), (xs, y1 - 0.06, 0.58),
                                     (xs, y1 - 0.16, z1 - 0.03), (xs, y0 + 0.05, z1 - 0.03)]]
    bm.faces.new(gv)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
glass = new_obj("CabGlass", bm, M_GLASS, upper)
glass.data.materials[0].use_backface_culling = False

bm = bmesh.new()
box(bm, (-0.8, -0.1, 0.72), (0.5, 0.5, 0.1), bevel=0.03)                     # seat
box(bm, (-0.8, -0.34, 1.05), (0.48, 0.1, 0.62), bevel=0.04)
box(bm, (-0.8, 0.55, 0.62), (0.6, 0.35, 0.3), bevel=0.03)                    # console
new_obj("CabInterior", bm, M_BLACK, upper)

bm = bmesh.new()
box(bm, (x1 - 0.1, y1 - 0.2, z1 + 0.1), (0.14, 0.08, 0.08))
box(bm, (x0 + 0.1, y1 - 0.2, z1 + 0.1), (0.14, 0.08, 0.08))
new_obj("CabLights", bm, M_LENS, upper)

# BROCKINTON decals: counterweight rear (wrapped on the tail arc) and cab-side
dec = text_mesh("DecalRear", "BROCKINTON", FONT, 0.3, upper, M_DECAL)
for v in dec.data.vertices:
    x, y, z = v.co
    r = TAIL_R + 0.01 + z
    v.co = (x, -math.sqrt(max(r * r - x * x, 0.0)), 0.72 + y)
dec2 = text_mesh("DecalHood", "BROCKINTON", FONT, 0.2, upper, M_DECAL)
for v in dec2.data.vertices:
    x, y, z = v.co
    v.co = (1.27 + 0.012 + z, -1.12 + x, 0.34 + y)

# ------------------------------------------------------------------- the arm
# Parts are modelled in their own frame: +Y along the part (u), +Z its top (v),
# X across the arm, origin at the part's root pin.
ARM_HALF = 0.30


def smin(a, b, k):
    h = max(k - abs(a - b), 0.0) / k
    return min(a, b) - h * h * k * 0.25


def boom_c(u):
    return smin(1.1 * u / 2.5, 1.1 * (C.BOOM_LEN - u) / 3.2, 0.9)


def boom_hh(u):
    return 0.26 + 0.11 * math.exp(-((u - 2.5) / 1.6) ** 2)


prof = []
N = 36
for i in range(N + 1):
    u = C.BOOM_LEN * i / N
    prof.append((u, boom_c(u) + boom_hh(u)))
r_tip = boom_hh(C.BOOM_LEN)
for i in range(1, 12):
    a = math.pi / 2 - math.pi * i / 12
    prof.append((C.BOOM_LEN + r_tip * math.cos(a), boom_c(C.BOOM_LEN) + r_tip * math.sin(a)))
for i in range(N, -1, -1):
    u = C.BOOM_LEN * i / N
    prof.append((u, boom_c(u) - boom_hh(u)))
r_foot = boom_hh(0)
for i in range(1, 12):
    a = -math.pi / 2 - math.pi * i / 12
    prof.append((r_foot * math.cos(a), boom_c(0) + r_foot * math.sin(a)))

boom = empty("Boom", upper, (C.ARM_X, *C.BOOM_FOOT))
bm = bmesh.new()
extrude_profile(bm, prof, -ARM_HALF, ARM_HALF, bevel=0.035)
# belly lugs for the boom cylinder rods and top lugs for the stick cylinder
bu, bv = C.BOOM_CYL_ROD
yb = boom_c(bu) - boom_hh(bu)
for s in (-1, 1):
    extrude_profile(bm, [(bu - 0.32, yb + 0.05), (bu + 0.32, yb + 0.05), (bu + 0.12, bv - 0.1), (bu - 0.12, bv - 0.1)],
                    s * 0.22, s * 0.3, bevel=0.008)
su, sv = C.STICK_CYL_BASE
yt = boom_c(su) + boom_hh(su)
for s in (-1, 1):
    extrude_profile(bm, [(su - 0.45, yt - 0.03), (su + 0.35, yt - 0.03), (su + 0.13, sv + 0.13), (su - 0.13, sv + 0.13)],
                    s * 0.12, s * 0.19, bevel=0.008)
boom_mesh = new_obj("BoomMesh", bm, M_PAINT, boom, smooth_angle=35)

bm = bmesh.new()
cylinder(bm, (-0.36, 0, 0), (0.36, 0, 0), 0.19, segs=28)
cylinder(bm, (-0.33, C.BOOM_LEN, 0), (0.33, C.BOOM_LEN, 0), 0.17, segs=28)
cylinder(bm, (-0.52, bu, bv), (0.52, bu, bv), 0.085, segs=20)
cylinder(bm, (-0.22, su, sv), (0.22, su, sv), 0.085, segs=20)
new_obj("BoomPins", bm, M_STEEL, boom, smooth_angle=50)

# hydraulic lines along the top of the boom
bm = bmesh.new()
for dx in (-0.12, 0.12):
    pts = []
    for i in range(24):
        u = 0.3 + (C.BOOM_LEN - 0.4) * i / 23
        pts.append(Vector((dx, u, boom_c(u) + boom_hh(u) + 0.045)))
    for a, b in zip(pts, pts[1:]):
        cylinder(bm, a, b, 0.03, segs=10, cap=False)
new_obj("BoomHoses", bm, M_BLACK, boom, smooth_angle=70)

# lights on the boom
bm = bmesh.new()
for s in (-1, 1):
    box(bm, (s * 0.34, 1.6, boom_c(1.6) + 0.1), (0.06, 0.14, 0.12), bevel=0.01)
new_obj("BoomLights", bm, M_LENS, boom)

# boom-side decals following the knee-to-tip segment
seg_a = math.atan2(boom_c(4.6) - boom_c(3.0), 1.6)
for s, name in ((1, "DecalBoomR"), (-1, "DecalBoomL")):
    d = text_mesh(name, "BROCKINTON", FONT, 0.3, boom, M_DECAL)
    for v in d.data.vertices:
        x, y, z = v.co
        uu = 3.75 + s * x * math.cos(seg_a)
        vv = boom_c(3.75) + y * math.cos(seg_a) + s * x * math.sin(seg_a)
        v.co = (s * (ARM_HALF + 0.004 + z), uu, vv)

# stick
STICK = [(-0.86, 0.18), (-0.8, 0.44), (-0.55, 0.52), (-0.1, 0.42), (0.6, 0.32), (1.6, 0.25), (2.55, 0.2),
         (2.95, 0.13), (3.06, 0.0), (2.97, -0.15), (2.6, -0.2), (1.0, -0.3), (0.25, -0.33), (-0.25, -0.27),
         (-0.62, -0.05)]
stick = empty("Stick", boom, (0, C.BOOM_LEN, 0))
bm = bmesh.new()
extrude_profile(bm, catmull_closed(STICK, 4), -0.2, 0.2, bevel=0.03)
ku, kv = C.BKT_CYL_BASE
for s in (-1, 1):
    extrude_profile(bm, [(ku - 0.3, 0.3), (ku + 0.3, 0.3), (ku + 0.12, kv + 0.12), (ku - 0.12, kv + 0.12)],
                    s * 0.12, s * 0.19, bevel=0.008)
stick_mesh = new_obj("StickMesh", bm, M_PAINT, stick, smooth_angle=35)

bm = bmesh.new()
cylinder(bm, (-0.3, 0, 0), (0.3, 0, 0), 0.13, segs=24)
cylinder(bm, (-0.3, C.STICK_LEN, 0), (0.3, C.STICK_LEN, 0), 0.12, segs=24)
cylinder(bm, (-0.24, *C.STICK_CYL_ROD), (0.24, *C.STICK_CYL_ROD), 0.08, segs=20)
cylinder(bm, (-0.24, *C.ROCKER_PIVOT), (0.24, *C.ROCKER_PIVOT), 0.075, segs=20)
cylinder(bm, (-0.22, ku, kv), (0.22, ku, kv), 0.075, segs=20)
new_obj("StickPins", bm, M_STEEL, stick, smooth_angle=50)

# bucket
bucket = empty("Bucket", stick, (0, C.STICK_LEN, 0))
BW = 0.56
SIDE = [(-0.3, -0.14), (-0.3, 0.3), (0.12, 0.62), (0.7, 0.7), (1.16, 0.48), (1.36, 0.14), (1.38, -0.02)]
SHELL = [(-0.3, 0.3), (-0.02, 0.56), (0.32, 0.68), (0.72, 0.69), (1.05, 0.56), (1.26, 0.32), (1.37, 0.06)]
bm = bmesh.new()
for s in (-1, 1):
    extrude_profile(bm, SIDE, s * BW, s * (BW - 0.035), bevel=0.008)
# curved shell swept across the width
rows = []
for (u, v) in SHELL:
    rows.append([bm.verts.new((x, u, v)) for x in (-BW, BW)])
inner = []
for (u, v) in SHELL:
    inner.append([bm.verts.new((x, u - 0.02, v - 0.03)) for x in (-BW + 0.03, BW - 0.03)])
for a, b in zip(rows, rows[1:]):
    bm.faces.new((a[0], a[1], b[1], b[0]))
for a, b in zip(inner, inner[1:]):
    bm.faces.new((a[0], b[0], b[1], a[1]))
bm.faces.new((rows[0][0], inner[0][0], inner[0][1], rows[0][1]))
bm.faces.new((rows[-1][1], inner[-1][1], inner[-1][0], rows[-1][0]))
box(bm, (0, -0.3, 0.08), (2 * BW, 0.04, 0.44), bevel=0.01)                   # back plate
for s in (-1, 1):                                                           # ears
    extrude_profile(bm, [(-0.3, 0.66), (0.05, 0.62), (0.2, 0.1), (0.12, -0.14), (-0.12, -0.16), (-0.3, 0.0)],
                    s * 0.22, s * 0.28, bevel=0.008)
bucket_mesh = new_obj("BucketMesh", bm, M_PAINT, bucket, smooth_angle=40)

bm = bmesh.new()
box(bm, (0, 1.34, 0.03), (2 * BW + 0.02, 0.1, 0.05), bevel=0.01)             # cutting lip
for k in range(5):
    x = -0.44 + k * 0.22
    g = bmesh.ops.create_cone(bm, cap_ends=True, segments=4, radius1=0.07, radius2=0.02, depth=0.2)
    bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=Matrix.Rotation(-math.pi / 2, 3, 'X'), verts=g["verts"])
    bmesh.ops.rotate(bm, cent=(0, 0, 0), matrix=Matrix.Rotation(math.pi / 4, 3, 'Y'), verts=g["verts"])
    bmesh.ops.scale(bm, vec=(1.0, 1.0, 0.55), verts=g["verts"])
    bmesh.ops.translate(bm, vec=(x, C.BUCKET_TIP - 0.08, 0.02), verts=g["verts"])
cylinder(bm, (-0.3, 0, 0), (0.3, 0, 0), 0.1, segs=24)
cylinder(bm, (-0.3, *C.LINK_PIN), (0.3, *C.LINK_PIN), 0.085, segs=20)
teeth = new_obj("BucketTeeth", bm, M_STEEL, bucket, smooth_angle=30)
paint_vcol(bucket_mesh, bucket_fn)
paint_vcol(boom_mesh, paint_fn(z_clean=3.0, z_dirty=1.2, top_dust=0.12))
paint_vcol(stick_mesh, paint_fn(z_clean=4.0, z_dirty=1.0, top_dust=0.12))

# bucket load, scaled by fill
bm = bmesh.new()
g = bmesh.ops.create_icosphere(bm, subdivisions=3, radius=1.0)
for v in g["verts"]:
    v.co.x *= BW - 0.04
    v.co.y *= 0.62
    v.co.z *= 0.36
    v.co += Vector((0, 0.66, 0.2))
    v.co += v.normal * 0.06 * noise.noise(v.co * 5.0)
load_ob = new_obj("BucketLoad", bm, M_LOAD, bucket, smooth_angle=80)
paint_vcol(load_ob, load_fn)
empty("fx_teeth", bucket, (0, C.BUCKET_TIP, 0))

# ------------------------------------------------------ cylinders & linkage
CYL = {
    "boom_cyl": dict(xs=(-0.42, 0.42), r=0.1, rod=0.058),
    "stick_cyl": dict(xs=(0.0,), r=0.11, rod=0.062),
    "bkt_cyl": dict(xs=(0.0,), r=0.092, rod=0.052),
}
# sample pin distances over the whole animation to size each cylinder
ranges = {k: [1e9, 0] for k in CYL}
states = []
for i in range(ANIM_FRAMES):
    p = i / (ANIM_FRAMES - 1)
    st = C.machine_state(p)
    pose = C.arm_pose(st["b"], st["s"], st["k"])
    states.append((st, pose))
    for k in CYL:
        d = C.length(C.sub(*pose[k]))
        ranges[k][0] = min(ranges[k][0], d)
        ranges[k][1] = max(ranges[k][1], d)

cyl_nodes = {}
for k, spec in CYL.items():
    dmin, dmax = ranges[k]
    eye = 0.1
    barrel_len = dmin - eye - 0.06            # rod eye + gland clearance when fully closed
    rod_len = dmax - barrel_len + 0.12        # rod stays 0.12 m inside the barrel at full stroke
    assert rod_len < barrel_len + 0.25, (k, barrel_len, rod_len)
    for j, x in enumerate(spec["xs"]):
        bm = bmesh.new()
        cylinder(bm, (0, -eye, 0), (0, 0.02, 0), spec["r"] * 0.8, segs=20)             # base clevis
        cylinder(bm, (-0.07, 0, 0), (0.07, 0, 0), eye, segs=20)
        cylinder(bm, (0, 0.05, 0), (0, barrel_len, 0), spec["r"], segs=28)
        cylinder(bm, (0, barrel_len - 0.08, 0), (0, barrel_len + 0.02, 0), spec["r"] * 1.12, segs=28)
        barrel = new_obj(f"{k}_{j}_barrel", bm, M_PAINT, upper, smooth_angle=40)
        paint_vcol(barrel, paint_fn())
        bm = bmesh.new()
        cylinder(bm, (0, -rod_len, 0), (0, -eye, 0), spec["rod"], segs=20)
        cylinder(bm, (-0.065, 0, 0), (0.065, 0, 0), eye, segs=20)
        rod = new_obj(f"{k}_{j}_rod", bm, M_CHROME, upper, smooth_angle=50)
        cyl_nodes.setdefault(k, []).append((barrel, rod, x))
    print(f"{k}: pin distance {dmin:.2f}-{dmax:.2f} m, barrel {barrel_len:.2f} m, rod {rod_len:.2f} m")

bm = bmesh.new()
for s in (-1, 1):
    box(bm, (s * 0.2, C.ROCKER_LEN / 2, 0), (0.035, C.ROCKER_LEN + 0.12, 0.13), bevel=0.02)
rocker = new_obj("Rocker", bm, M_PAINT, upper, smooth_angle=40)
paint_vcol(rocker, bucket_fn)
bm = bmesh.new()
for s in (-1, 1):
    box(bm, (s * 0.27, C.LINK_LEN / 2, 0), (0.04, C.LINK_LEN + 0.14, 0.15), bevel=0.02)
cylinder(bm, (-0.3, 0, 0), (0.3, 0, 0), 0.07, segs=20)
link = new_obj("Link", bm, M_PAINT, upper, smooth_angle=40)
paint_vcol(link, bucket_fn)

# ------------------------------------------------------------------ animate
scene.frame_start = 0
scene.frame_end = ANIM_FRAMES - 1
scene.render.fps = 30
for ob in [upper, boom, stick, bucket, rocker, link, load_ob] + [n for v in cyl_nodes.values() for t in v for n in t[:2]]:
    ob.rotation_mode = 'XYZ'


def aim(ob, a, b, x):
    ob.location = (C.ARM_X + x, a[0], a[1])
    ob.rotation_euler = (math.atan2(b[1] - a[1], b[0] - a[0]), 0, 0)


def pose_frame(i):
    st, pose = states[i]
    upper.rotation_euler = (0, 0, st["yaw"])
    boom.rotation_euler = (st["b"], 0, 0)
    stick.rotation_euler = (st["s"], 0, 0)
    bucket.rotation_euler = (st["k"], 0, 0)
    for k, nodes in cyl_nodes.items():
        a, b = pose[k]
        for barrel, rod, x in nodes:
            aim(barrel, a, b, x)
            aim(rod, b, a, x)                        # rod eye sits on pin b...
            rod.rotation_euler.x = math.atan2(b[1] - a[1], b[0] - a[0])  # ...and slides back into the barrel
    aim(rocker, *pose["rocker"], 0)
    aim(link, *pose["link"], 0)
    f = max(st["fill"], 0.001)
    load_ob.scale = (1, f ** 0.5, f)


for i in range(ANIM_FRAMES):
    pose_frame(i)
    for ob in [upper, boom, stick, bucket, rocker, link]:
        ob.keyframe_insert("rotation_euler", frame=i)
        ob.keyframe_insert("location", frame=i)
    for nodes in cyl_nodes.values():
        for barrel, rod, _ in nodes:
            for ob in (barrel, rod):
                ob.keyframe_insert("rotation_euler", frame=i)
                ob.keyframe_insert("location", frame=i)
    load_ob.keyframe_insert("scale", frame=i)

for act in bpy.data.actions:
    try:
        for fc in act.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR'
    except AttributeError:
        # Blender 5 layered actions
        for layer in act.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    for fc in bag.fcurves:
                        for kp in fc.keyframe_points:
                            kp.interpolation = 'LINEAR'

scene.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "excavator.blend"))

bpy.ops.export_scene.gltf(
    filepath=os.path.join(OUT, "excavator_raw.glb"),
    export_format='GLB',
    export_animations=True,
    export_animation_mode='SCENE',
    export_frame_range=True,
    export_force_sampling=True,
    export_optimize_animation_size=False,
    export_vertex_color='ACTIVE',
    export_all_vertex_colors=False,
    export_yup=True,
    export_apply=False,
    export_extras=False,
)
print("wrote", os.path.join(OUT, "excavator_raw.glb"))
