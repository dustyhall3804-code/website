"""Build the full hero environment around the rigged excavator.

Produces build/scene.blend (used by render_frames.py for the pre-rendered
sequence) and build/env.glb (fence, hay bales, ridges for the real-time hero)
plus build/tex/tree_*.png impostor cards for the real-time treeline.
"""
import math
import os
import sys

import bpy
import bmesh
import numpy as np
from mathutils import Vector, Matrix, noise

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common as C  # noqa: E402
import terrain_np as T  # noqa: E402
from bl_util import srgb, material, new_obj, box, cylinder  # noqa: E402

OUT = os.path.join(HERE, "build")
TEX = os.path.join(OUT, "tex")
FAST = "--fast" in sys.argv

bpy.ops.wm.open_mainfile(filepath=os.path.join(OUT, "excavator.blend"))
scene = bpy.context.scene
rng = np.random.default_rng(3)

SUN_AZ = math.radians(208)        # direction the sun shines FROM, measured from +X toward +Y
SUN_EL = math.radians(17)
HAZE = srgb("#b9c3cc")
# Nishita measures sun rotation from +Y clockwise; SUN_AZ is from +X counter-clockwise.
SUN_ROT = math.pi / 2 - SUN_AZ


def img(name, non_color=False):
    im = bpy.data.images.load(os.path.join(TEX, name), check_existing=True)
    if non_color:
        im.colorspace_settings.name = 'Non-Color'
    return im


# --------------------------------------------------------------- node helpers
class NB:
    """Tiny node-tree builder."""

    def __init__(self, mat):
        self.m = mat
        self.nt = mat.node_tree
        self.n = self.nt.nodes
        self.l = self.nt.links

    def node(self, kind, **props):
        nd = self.n.new(kind)
        for k, v in props.items():
            setattr(nd, k, v)
        return nd

    def link(self, a, b):
        self.l.new(a, b)

    def tex(self, name, vec, non_color=False, proj='BOX'):
        t = self.node("ShaderNodeTexImage", image=img(name, non_color), projection=proj)
        if proj == 'BOX':
            t.projection_blend = 0.25
        self.link(vec, t.inputs["Vector"])
        return t

    def math(self, op, a, b=None, clamp=False):
        m = self.node("ShaderNodeMath", operation=op, use_clamp=clamp)
        for i, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                m.inputs[i].default_value = v
            else:
                self.link(v, m.inputs[i])
        return m.outputs[0]

    def mix(self, fac, a, b, kind='RGBA'):
        m = self.node("ShaderNodeMix", data_type=kind)
        ia, ib, out = (6, 7, 2) if kind == 'RGBA' else (2, 3, 0)
        for sock, v in ((m.inputs[0], fac), (m.inputs[ia], a), (m.inputs[ib], b)):
            if isinstance(v, (int, float)):
                sock.default_value = v
            elif isinstance(v, tuple):
                sock.default_value = (*v, 1) if len(v) == 3 else v
            else:
                self.link(v, sock)
        return m.outputs[out]

    def band(self, x, edge, width):
        """smoothstep(edge - w, edge + w, x)"""
        mr = self.node("ShaderNodeMapRange", interpolation_type='SMOOTHSTEP')
        mr.inputs[1].default_value = edge - width
        mr.inputs[2].default_value = edge + width
        self.link(x, mr.inputs[0])
        return mr.outputs[0]


SKY_LIGHT = 0.02          # sky as a light source
SKY_SEEN = 0.03           # sky as seen by the camera (and the haze colour)


def sky_node(b):
    s = b.node("ShaderNodeTexSky")
    for t in ('NISHITA', 'MULTIPLE_SCATTERING', 'SINGLE_SCATTERING'):
        try:
            s.sky_type = t
            break
        except TypeError:
            continue
    s.sun_elevation = SUN_EL
    s.sun_rotation = SUN_ROT
    try:
        s.air_density = 1.4
        s.dust_density = 3.2       # late-summer haze
        s.ozone_density = 1.0
        s.sun_disc = False         # the sun lamp is the only sun
    except AttributeError:
        pass
    return s


def add_haze(mat, dist0=60.0, scale=900.0, strength=0.85):
    """Aerial perspective: blend the surface toward the sky's horizon colour with distance."""
    b = NB(mat)
    out = b.n["Material Output"]
    surf = out.inputs["Surface"].links[0].from_socket
    cam = b.node("ShaderNodeCameraData")
    d = b.math('SUBTRACT', cam.outputs["View Distance"], dist0)
    d = b.math('MAXIMUM', d, 0.0)
    d = b.math('DIVIDE', d, -scale)
    f = b.math('EXPONENT', d)
    f = b.math('SUBTRACT', 1.0, f)
    f = b.math('MULTIPLY', f, strength)
    geo = b.node("ShaderNodeNewGeometry")
    flip = b.node("ShaderNodeVectorMath", operation='MULTIPLY')
    flip.inputs[1].default_value = (-1.0, -1.0, -0.15)
    b.link(geo.outputs["Incoming"], flip.inputs[0])
    lift = b.node("ShaderNodeVectorMath", operation='ADD')
    lift.inputs[1].default_value = (0.0, 0.0, 0.03)
    b.link(flip.outputs[0], lift.inputs[0])
    sk = sky_node(b)
    b.link(lift.outputs[0], sk.inputs[0])
    em = b.node("ShaderNodeEmission")
    em.inputs[1].default_value = SKY_SEEN
    b.link(sk.outputs[0], em.inputs[0])
    mix = b.node("ShaderNodeMixShader")
    b.link(f, mix.inputs[0])
    b.link(surf, mix.inputs[1])
    b.link(em.outputs[0], mix.inputs[2])
    b.link(mix.outputs[0], out.inputs["Surface"])


# ------------------------------------------------------- machine grime (render only)
for mname, amount in (("Paint", 0.75), ("Undercarriage", 0.6)):
    m = bpy.data.materials[mname]
    nb = NB(m)
    p = nb.n["Principled BSDF"]
    base = p.inputs["Base Color"].links[0].from_socket
    ao = nb.node("ShaderNodeAmbientOcclusion", samples=8)
    ao.inputs["Distance"].default_value = 0.35
    gn = nb.node("ShaderNodeTexNoise")
    gn.inputs["Scale"].default_value = 9.0
    gn.inputs["Detail"].default_value = 6
    grime = nb.math('MULTIPLY', nb.math('SUBTRACT', 1.0, ao.outputs["AO"]), 1.6)
    grime = nb.math('MULTIPLY', grime, nb.math('ADD', gn.outputs[0], 0.2), clamp=True)
    grime = nb.math('MULTIPLY', grime, amount)
    dirty = nb.mix(grime, base, srgb("#3b2416"))
    nb.link(dirty, p.inputs["Base Color"])
    nb.link(nb.math('ADD', nb.math('MULTIPLY', grime, 0.4), 0.42 if mname == "Paint" else 0.8, clamp=True),
            p.inputs["Roughness"])

# ------------------------------------------------------------------- world
world = bpy.data.worlds.new("Sky")
scene.world = world
world.use_nodes = True
wb = NB(world)
sky = sky_node(wb)
bg = world.node_tree.nodes["Background"]
lp = wb.node("ShaderNodeLightPath")
strength = wb.mix(lp.outputs["Is Camera Ray"], SKY_LIGHT, SKY_SEEN, 'FLOAT')
wb.link(strength, bg.inputs[1])
wb.link(sky.outputs[0], bg.inputs[0])

sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", 'SUN'))
scene.collection.objects.link(sun)
sun.data.energy = 4.6
sun.data.color = srgb("#ffeed8")
sun.data.angle = math.radians(0.8)
sun_dir = Vector((math.cos(SUN_AZ) * math.cos(SUN_EL), math.sin(SUN_AZ) * math.cos(SUN_EL), math.sin(SUN_EL)))
sun.rotation_euler = (-sun_dir).to_track_quat('-Z', 'Y').to_euler()

# ------------------------------------------------------------------ terrain
R = 320.0
NG = 360 if FAST else 720
u = np.linspace(-1, 1, NG)
warp = np.sign(u) * np.abs(u) ** 2.25 * R
CX, CY = 1.0, 4.5
gx, gy = np.meshgrid(warp + CX, warp + CY)
gz = T.height(gx, gy, 0, 0)
verts = np.stack([gx.ravel(), gy.ravel(), gz.ravel()], -1)
faces = []
idx = np.arange(NG * NG).reshape(NG, NG)
a, b_, c, d = idx[:-1, :-1].ravel(), idx[:-1, 1:].ravel(), idx[1:, 1:].ravel(), idx[1:, :-1].ravel()
faces = np.stack([a, b_, c, d], -1)
me = bpy.data.meshes.new("Terrain")
me.vertices.add(len(verts))
me.vertices.foreach_set("co", verts.ravel())
me.loops.add(faces.size)
me.loops.foreach_set("vertex_index", faces.ravel())
me.polygons.add(len(faces))
me.polygons.foreach_set("loop_start", np.arange(0, faces.size, 4))
me.polygons.foreach_set("loop_total", np.full(len(faces), 4))
me.update(calc_edges=True)
me.polygons.foreach_set("use_smooth", np.ones(len(faces), bool))
terrain = bpy.data.objects.new("Terrain", me)
scene.collection.objects.link(terrain)
work = T.work_mask(gx, gy).ravel().astype(np.float32)
for name in ("work", "spoil", "orig"):
    me.attributes.new(name, 'FLOAT', 'POINT')
me.attributes["work"].data.foreach_set("value", work)
me.attributes["orig"].data.foreach_set("value", gz.ravel().astype(np.float32))
me.attributes["spoil"].data.foreach_set("value", np.zeros(len(verts), np.float32))
np.save(os.path.join(OUT, "terrain_xy.npy"), np.stack([gx.ravel(), gy.ravel()], -1))

# terrain material --------------------------------------------------------
tm = bpy.data.materials.new("Ground")
tm.use_nodes = True
b = NB(tm)
bsdf = b.n["Principled BSDF"]
coord = b.node("ShaderNodeTexCoord")
mp = b.node("ShaderNodeMapping")
mp.inputs["Scale"].default_value = (1 / 2.6, 1 / 2.6, 1 / 2.6)
b.link(coord.outputs["Object"], mp.inputs["Vector"])
vec = mp.outputs[0]
mp2 = b.node("ShaderNodeMapping")
mp2.inputs["Scale"].default_value = (1 / 7.0, 1 / 7.0, 1 / 7.0)
mp2.inputs["Rotation"].default_value = (0, 0, 0.6)
b.link(coord.outputs["Object"], mp2.inputs["Vector"])
vec_far = mp2.outputs[0]

layers = {}
for name in ("pasture", "topsoil", "clay", "gravel", "shale"):
    v = vec_far if name == "pasture" else vec
    layers[name] = (b.tex(f"{name}_albedo.png", v).outputs[0],
                    b.tex(f"{name}_rough.png", v, True).outputs[0],
                    b.tex(f"{name}_normal.png", v, True).outputs[0])

geo = b.node("ShaderNodeNewGeometry")
sep = b.node("ShaderNodeSeparateXYZ")
b.link(geo.outputs["Position"], sep.inputs[0])
z = sep.outputs[2]
orig = b.node("ShaderNodeAttribute", attribute_name="orig").outputs["Fac"]
workn = b.node("ShaderNodeAttribute", attribute_name="work").outputs["Fac"]
spoiln = b.node("ShaderNodeAttribute", attribute_name="spoil").outputs["Fac"]
nz = b.node("ShaderNodeTexNoise")
nz.inputs["Scale"].default_value = 0.35
b.link(coord.outputs["Object"], nz.inputs["Vector"])
wobble = b.math('MULTIPLY', b.math('SUBTRACT', nz.outputs[0], 0.5), 0.35)
depth = b.math('ADD', b.math('SUBTRACT', orig, z), wobble)


def layer_mix(i):
    top = layers["topsoil"][i]
    col = b.mix(b.band(depth, C.STRATA[0], 0.04), top, layers["clay"][i])
    col = b.mix(b.band(depth, C.STRATA[1], 0.05), col, layers["gravel"][i])
    col = b.mix(b.band(depth, C.STRATA[2], 0.05), col, layers["shale"][i])
    # spoil: churned clay with topsoil clods
    clods = b.node("ShaderNodeTexVoronoi")
    clods.inputs["Scale"].default_value = 6.0
    b.link(coord.outputs["Object"], clods.inputs["Vector"])
    sp_mix = b.mix(b.band(clods.outputs[0], 0.18, 0.12), layers["topsoil"][i], layers["clay"][i])
    col = b.mix(b.band(spoiln, 0.08, 0.06), col, sp_mix)
    return b.mix(workn, layers["pasture"][i], col)


col = layer_mix(0)
rough = layer_mix(1)
nrm = layer_mix(2)

# shoreline wetness: below/near the water line soil darkens and turns glossy
water_level = b.node("ShaderNodeValue", label="water_level")
water_level.name = "water_level"
water_level.outputs[0].default_value = -10.0
wet = b.math('SUBTRACT', b.math('ADD', water_level.outputs[0], 0.18), z)
wet = b.math('MULTIPLY', wet, 5.0, clamp=True)
dark = b.node("ShaderNodeMix", data_type='RGBA', blend_type='MULTIPLY')
dark.inputs[0].default_value = 1.0
b.link(col, dark.inputs[6])
dark.inputs[7].default_value = (0.5, 0.45, 0.42, 1)
col = b.mix(wet, col, dark.outputs[2])
rough = b.math('SUBTRACT', rough, b.math('MULTIPLY', wet, 0.55))
nm = b.node("ShaderNodeNormalMap")
nm.inputs["Strength"].default_value = 1.2
b.link(nrm, nm.inputs["Color"])
b.link(col, bsdf.inputs["Base Color"])
b.link(rough, bsdf.inputs["Roughness"])
b.link(nm.outputs[0], bsdf.inputs["Normal"])
terrain.data.materials.append(tm)
add_haze(tm, 80, 1100, 0.8)

# ------------------------------------------------------------------- grass
grass_col = bpy.data.collections.new("GrassClumps")
scene.collection.children.link(grass_col)
gm = bpy.data.materials.new("Grass")
gm.use_nodes = True
gb = NB(gm)
gbsdf = gb.n["Principled BSDF"]
vc = gb.node("ShaderNodeVertexColor", layer_name="Col")
gb.link(vc.outputs[0], gbsdf.inputs["Base Color"])
gbsdf.inputs["Roughness"].default_value = 0.6
gbsdf.inputs["Subsurface Weight"].default_value = 0.0
tr = gb.node("ShaderNodeBsdfTranslucent")
gb.link(vc.outputs[0], tr.inputs[0])
ms = gb.node("ShaderNodeMixShader")
ms.inputs[0].default_value = 0.4
gb.link(gbsdf.outputs[0], ms.inputs[1])
gb.link(tr.outputs[0], ms.inputs[2])
gb.link(ms.outputs[0], gb.n["Material Output"].inputs["Surface"])
add_haze(gm, 80, 1100, 0.8)

GREENS = [srgb(h) for h in ("#6d7a35", "#84893d", "#96914a", "#b3a45c", "#c4b06a", "#d2bf7e", "#8a8440")]


def grass_clump(i, blades=16):
    bm = bmesh.new()
    cl = bm.loops.layers.color.new("Col")
    r = np.random.default_rng(100 + i)
    for k in range(blades):
        ang = r.uniform(0, math.tau)
        rad = r.uniform(0, 0.09)
        bx, by = math.cos(ang) * rad, math.sin(ang) * rad
        hgt = r.uniform(0.28, 0.72)
        lean = r.uniform(0.15, 0.55)
        face = r.uniform(0, math.tau)
        w = r.uniform(0.006, 0.011)
        dry = r.uniform(0, 1) ** 0.7
        c_base = np.array(GREENS[r.integers(0, 3)])
        c_tip = np.array(GREENS[3 + int(dry * 3.99)])
        segs = 4
        prev = None
        for s in range(segs + 1):
            t = s / segs
            px = bx + math.cos(ang) * lean * hgt * t * t
            py = by + math.sin(ang) * lean * hgt * t * t
            pz = hgt * t * (1 - 0.25 * lean * t)
            ww = w * (1 - t * 0.85)
            ox, oy = math.cos(face) * ww, math.sin(face) * ww
            v0 = bm.verts.new((px - ox, py - oy, pz))
            v1 = bm.verts.new((px + ox, py + oy, pz))
            if prev:
                f = bm.faces.new((prev[0], prev[1], v1, v0))
                for lp in f.loops:
                    tt = lp.vert.co.z / hgt
                    c = c_base * (1 - tt) + c_tip * tt
                    c = c * (0.7 + 0.3 * tt)
                    lp[cl] = (*c, 1)
            prev = (v0, v1)
        if r.uniform() < 0.25:                       # seed head
            g = bmesh.ops.create_cone(bm, cap_ends=True, segments=5, radius1=0.006, radius2=0.002, depth=0.08)
            bmesh.ops.translate(bm, vec=(px, py, pz + 0.04), verts=g["verts"])
            for f in {f for v in g["verts"] for f in v.link_faces}:
                for lp in f.loops:
                    lp[cl] = (*srgb("#8a7a52"), 1)
    ob = new_obj(f"GrassClump{i}", bm, gm)
    ob.data.polygons.foreach_set("use_smooth", [True] * len(ob.data.polygons))
    scene.collection.objects.unlink(ob)
    grass_col.objects.link(ob)
    ob.location = (0, 0, -200)
    return ob


for i in range(6):
    grass_clump(i)

# density: pasture only, fading out with distance from the work area
dist = np.hypot(gx - CX, gy - CY).ravel()
dens = (1 - work) * np.clip(1 - (dist - 55) / 30, 0, 1)
vg = terrain.vertex_groups.new(name="grass")
levels = np.round(dens * 20).astype(int)          # batch by quantised weight (fast)
for lv in range(1, 21):
    idx_lv = np.nonzero(levels == lv)[0]
    if len(idx_lv):
        vg.add(idx_lv.tolist(), lv / 20, 'REPLACE')
ps_mod = terrain.modifiers.new("grass", 'PARTICLE_SYSTEM')
psys = terrain.particle_systems[0]
pset = psys.settings
pset.type = 'HAIR'
pset.use_advanced_hair = True
pset.hair_length = 1.0
pset.count = 60000 if FAST else 420000
pset.render_type = 'COLLECTION'
pset.instance_collection = grass_col
pset.use_collection_pick_random = True
pset.particle_size = 1.0
pset.size_random = 0.45
pset.use_rotations = True
pset.rotation_mode = 'OB_Z'
pset.phase_factor_random = 2.0
pset.use_emit_random = True
pset.distribution = 'RAND'
psys.vertex_group_density = "grass"
psys.seed = 11

# -------------------------------------------------------------------- trees
leaf_mat = bpy.data.materials.new("Leaves")
leaf_mat.use_nodes = True
lb = NB(leaf_mat)
lt = lb.node("ShaderNodeTexImage", image=img("leaves.png"))
uvn = lb.node("ShaderNodeTexCoord")
lb.link(uvn.outputs["UV"], lt.inputs[0])
lbsdf = lb.n["Principled BSDF"]
hue = lb.node("ShaderNodeHueSaturation")
lb.link(lt.outputs[0], hue.inputs["Color"])
objinfo = lb.node("ShaderNodeObjectInfo")
hue.inputs["Value"].default_value = 1.0
lb.link(lb.math('ADD', lb.math('MULTIPLY', objinfo.outputs["Random"], 0.35), 0.8), hue.inputs["Value"])
lb.link(hue.outputs[0], lbsdf.inputs["Base Color"])
lb.link(lt.outputs["Alpha"], lbsdf.inputs["Alpha"])
ltr = lb.node("ShaderNodeBsdfTranslucent")
lb.link(hue.outputs[0], ltr.inputs[0])
lmix = lb.node("ShaderNodeMixShader")
lmix.inputs[0].default_value = 0.3
lb.link(lbsdf.outputs[0], lmix.inputs[1])
lb.link(ltr.outputs[0], lmix.inputs[2])
lalpha = lb.node("ShaderNodeMixShader")
lb.link(lt.outputs["Alpha"], lalpha.inputs[0])
lb.link(lb.node("ShaderNodeBsdfTransparent").outputs[0], lalpha.inputs[1])
lb.link(lmix.outputs[0], lalpha.inputs[2])
lb.link(lalpha.outputs[0], lb.n["Material Output"].inputs["Surface"])
lbsdf.inputs["Roughness"].default_value = 0.85
lbsdf.inputs["Specular IOR Level"].default_value = 0.12
leaf_mat.surface_render_method = 'DITHERED'
add_haze(leaf_mat, 80, 1400, 0.4)
bark = material("Bark", srgb("#3b3129"), rough=0.9, use_vcol=False)
canopy = bpy.data.materials.new("Canopy")
canopy.use_nodes = True
cb = NB(canopy)
cbsdf = cb.n["Principled BSDF"]
ctc = cb.node("ShaderNodeTexCoord")
cn1 = cb.node("ShaderNodeTexNoise")
cn1.inputs["Scale"].default_value = 1.6
cn1.inputs["Detail"].default_value = 8
cb.link(ctc.outputs["Object"], cn1.inputs["Vector"])
cvor = cb.node("ShaderNodeTexVoronoi")
cvor.inputs["Scale"].default_value = 6.0
cb.link(ctc.outputs["Object"], cvor.inputs["Vector"])
cinfo = cb.node("ShaderNodeObjectInfo")
ccol = cb.node("ShaderNodeValToRGB")
ccol.color_ramp.elements[0].color = (*srgb("#1c2a0e"), 1)
ccol.color_ramp.elements[1].color = (*srgb("#6b7a2e"), 1)
e = ccol.color_ramp.elements.new(0.55)
e.color = (*srgb("#3d5119"), 1)
t = cb.math('ADD', cb.math('MULTIPLY', cn1.outputs[0], 0.7), cb.math('MULTIPLY', cvor.outputs[0], 0.45))
t = cb.math('ADD', t, cb.math('MULTIPLY', cb.math('SUBTRACT', cinfo.outputs["Random"], 0.5), 0.3))
t = cb.math('SUBTRACT', t, 0.3)
cb.link(t, ccol.inputs[0])
cb.link(ccol.outputs[0], cbsdf.inputs["Base Color"])
cbump = cb.node("ShaderNodeBump")
cbump.inputs["Strength"].default_value = 0.9
cbump.inputs["Distance"].default_value = 0.4
cb.link(cb.math('ADD', cvor.outputs[0], cn1.outputs[0]), cbump.inputs["Height"])
cb.link(cbump.outputs[0], cbsdf.inputs["Normal"])
cbsdf.inputs["Roughness"].default_value = 0.9
cbsdf.inputs["Specular IOR Level"].default_value = 0.15
add_haze(canopy, 80, 1400, 0.4)
add_haze(bark, 80, 1400, 0.4)


def tree(kind, seed):
    r = np.random.default_rng(seed)
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UV")
    if kind == "pine":
        H = r.uniform(17, 24)
        cylinder(bm, (0, 0, -0.5), (0, 0, H * 0.93), 0.26, segs=8, r1=0.06, mat_index=1)
        blobs = [(r.uniform(-1, 1), r.uniform(-1, 1), H * (0.55 + 0.38 * t), (1.0 - 0.55 * t) * r.uniform(1.8, 2.8))
                 for t in np.linspace(0, 1, 8)]
        nc = 380
    elif kind == "oak":
        H = r.uniform(12, 18)
        cylinder(bm, (0, 0, -0.5), (0, 0, H * 0.4), 0.34, segs=8, r1=0.22, mat_index=1)
        blobs = []
        for k in range(11):
            a = r.uniform(0, math.tau)
            rr = r.uniform(0.8, 4.2)
            z = H * r.uniform(0.3, 0.9)
            blobs.append((math.cos(a) * rr, math.sin(a) * rr, z, r.uniform(1.8, 3.2)))
            cylinder(bm, (0, 0, H * 0.35), (math.cos(a) * rr * 0.8, math.sin(a) * rr * 0.8, z - 0.5), 0.12,
                     segs=6, r1=0.05, mat_index=1)
        blobs.append((0, 0, H * 0.8, 3.4))
        nc = 700
    else:  # cedar / understory
        H = r.uniform(5, 8)
        cylinder(bm, (0, 0, -0.3), (0, 0, H * 0.6), 0.14, segs=6, r1=0.05, mat_index=1)
        blobs = [(0, 0, H * (0.25 + 0.6 * t), (1.0 - 0.7 * t) * 1.9) for t in np.linspace(0, 1, 5)]
        nc = 160
    # solid displaced canopy masses; leaf cards break up the silhouette
    for bx, by, bz, br in blobs:
        g = bmesh.ops.create_icosphere(bm, subdivisions=3, radius=br * 0.82)
        for v in g["verts"]:
            v.co.z *= 0.72
            v.co += v.co.normalized() * br * 0.28 * noise.noise(v.co * 0.9 + Vector((seed, bx, by)))
            v.co += Vector((bx, by, bz))
        for f in {f for v in g["verts"] for f in v.link_faces}:
            f.material_index = 2
    for _ in range(int(nc * 0.55)):
        bx, by, bz, br = blobs[r.integers(len(blobs))]
        d = r.normal(0, 1, 3)
        d /= np.linalg.norm(d)
        p = np.array([bx, by, bz]) + d * br * r.uniform(0.85, 1.12) * np.array([1, 1, 0.72])
        s = r.uniform(0.9, 1.6)
        # card oriented roughly outward, random roll
        n = Vector(d.tolist())
        q = Vector((0, 0, 1)).rotation_difference(n)
        roll = Matrix.Rotation(r.uniform(0, math.tau), 3, n)
        m = roll @ q.to_matrix()
        corners = [(-s, -s), (s, -s), (s, s), (-s, s)]
        vs = [bm.verts.new(Vector(p.tolist()) + m @ Vector((cx, cy, 0))) for cx, cy in corners]
        f = bm.faces.new(vs)
        for lp, (uu, vv) in zip(f.loops, [(0, 0), (1, 0), (1, 1), (0, 1)]):
            lp[uvl].uv = (uu, vv)
    ob = new_obj(f"Tree_{kind}_{seed}", bm)
    ob.data.materials.append(leaf_mat)
    ob.data.materials.append(bark)
    ob.data.materials.append(canopy)
    return ob


tree_col = bpy.data.collections.new("TreeProtos")
scene.collection.children.link(tree_col)
protos = []
for k, (kind, seed) in enumerate([("oak", 1), ("oak", 2), ("oak", 3), ("pine", 4), ("pine", 5), ("cedar", 6)]):
    t = tree(kind, seed)
    scene.collection.objects.unlink(t)
    tree_col.objects.link(t)
    t.location = (0, 0, -500)
    protos.append((kind, t))
tree_col.hide_render = False

instances = []


def plant_line(p0, p1, spacing, depth, kinds):
    p0, p1 = np.array(p0, float), np.array(p1, float)
    L = np.linalg.norm(p1 - p0)
    dvec = (p1 - p0) / L
    nvec = np.array([-dvec[1], dvec[0]])
    s = 0.0
    while s < L:
        for row in range(int(depth)):
            q = p0 + dvec * (s + rng.uniform(-2, 2)) + nvec * (row * 6 + rng.uniform(-3, 3))
            choices = [pt for pt in protos if pt[0] in kinds]
            if row == 0 and rng.uniform() < 0.4:
                choices = [pt for pt in protos if pt[0] == "cedar"]
            kind, proto = choices[rng.integers(len(choices))]
            instances.append((proto, (q[0], q[1]), rng.uniform(0.8, 1.2), rng.uniform(0, math.tau)))
        s += spacing * rng.uniform(0.6, 1.3)


plant_line((-120, 68), (140, 84), 5.0, 4, ("oak", "oak", "pine", "cedar"))     # treeline across the field (north)
plant_line((-95, -70), (-80, 60), 9.0, 2, ("oak", "cedar", "pine"))      # west fencerow
plant_line((150, -58), (-110, -66), 5.5, 4, ("oak", "oak", "pine", "cedar"))    # south treeline (behind final shot)
plant_line((120, -50), (130, 80), 10.0, 2, ("oak", "pine"))              # east
for x, y in [(-30, 38), (26, 44)]:                          # a few lone pasture trees
    instances.append((protos[0][1], (x, y), 1.1, rng.uniform(0, 6)))

tree_inst_col = bpy.data.collections.new("Trees")
scene.collection.children.link(tree_inst_col)
tree_records = []
for i, (proto, (x, y), s, rz) in enumerate(instances):
    e = bpy.data.objects.new(f"TreeInst{i}", None)
    e.instance_type = 'COLLECTION'
    col_one = bpy.data.collections.get(proto.name + "_col")
    if not col_one:
        col_one = bpy.data.collections.new(proto.name + "_col")
        col_one.objects.link(proto)
        proto.location = (0, 0, 0)
    e.instance_collection = col_one
    zg = float(T.height(np.array(x), np.array(y), 0, 0))
    e.location = (x, y, zg)
    e.scale = (s, s, s)
    e.rotation_euler = (0, 0, rz)
    tree_inst_col.objects.link(e)
    tree_records.append(dict(kind=proto.name, x=x, y=y, z=zg, s=s, r=rz))
for kind, t in protos:
    if t.name in tree_col.objects:
        tree_col.objects.unlink(t)
bpy.data.collections.remove(tree_col)

# ------------------------------------------------------------------- ridges
ridge_mat = material("Ridge", (1, 1, 1), rough=0.95)
add_haze(ridge_mat, 150, 900, 0.93)


def ridges():
    bm = bmesh.new()
    cl = bm.loops.layers.color.new("Col")
    for band, (rad, hgt, seed) in enumerate([(700, 110, 1), (1150, 190, 2), (1800, 260, 3)]):
        nseg = 360
        rows = []
        for i in range(nseg):
            a = i / nseg * math.tau
            # Ouachita ridges run east-west: higher to the north and south
            ew = 0.55 + 0.45 * abs(math.sin(a))
            h = hgt * ew * (0.55 + 0.45 * (noise.noise(Vector((math.cos(a) * 3 + seed * 10, math.sin(a) * 3, 0))) * 0.5 + 0.5))
            h += hgt * 0.25 * noise.noise(Vector((math.cos(a) * 11, math.sin(a) * 11, seed)))
            ring = []
            for k, (rr, zz) in enumerate([(rad * 0.93, -8), (rad, h * 0.7), (rad * 1.05, h), (rad * 1.12, h * 0.5)]):
                ring.append(bm.verts.new((math.cos(a) * rr + CX, math.sin(a) * rr + CY, zz)))
            rows.append(ring)
        for i in range(nseg):
            r0, r1 = rows[i], rows[(i + 1) % nseg]
            for k in range(3):
                f = bm.faces.new((r0[k], r1[k], r1[k + 1], r0[k + 1]))
                for lp in f.loops:
                    t = lp.vert.co.z / (hgt + 1)
                    base = np.array(srgb("#26331f")) * (0.85 + 0.3 * t)
                    lp[cl] = (*base, 1)
    ob = new_obj("Ridges", bm, ridge_mat, smooth_angle=80)
    return ob


ridges_ob = ridges()

# -------------------------------------------------------------------- fence
post_mat = material("Post", srgb("#6b5a48"), rough=0.9, use_vcol=False)
wire_mat = material("Wire", srgb("#8a8580"), rough=0.35, metal=0.9, use_vcol=False)
FENCE = [(-17.0, -45.0), (-17.5, 70.0)]
bm = bmesh.new()
wbm = bmesh.new()
bbm = bmesh.new()
p0, p1 = np.array(FENCE[0]), np.array(FENCE[1])
L = np.linalg.norm(p1 - p0)
n_posts = int(L / 3.6)
posts = []
for i in range(n_posts + 1):
    q = p0 + (p1 - p0) * i / n_posts
    zg = float(T.height(np.array(q[0]), np.array(q[1]), 0, 0))
    lean = rng.normal(0, 0.03, 2)
    top = (q[0] + lean[0], q[1] + lean[1], zg + 1.25 + rng.uniform(-0.05, 0.05))
    cylinder(bm, (q[0], q[1], zg - 0.2), top, 0.065 + rng.uniform(0, 0.02), segs=7)
    posts.append((q[0], q[1], zg, top))
for hz in (0.42, 0.68, 0.94, 1.18):
    for (x0, y0, z0, t0), (x1, y1, z1, t1) in zip(posts, posts[1:]):
        prev = None
        for s in range(7):
            t = s / 6
            sag = 0.035 * math.sin(math.pi * t)
            p = Vector((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, z0 + (z1 - z0) * t + hz - sag))
            if prev is not None:
                cylinder(wbm, prev, p, 0.0035, segs=4, cap=False)
            prev = p
        # barbs every ~12 cm
        nb = int(3.6 / 0.12)
        for k in range(1, nb):
            t = k / nb
            c0 = Vector((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, z0 + (z1 - z0) * t + hz - 0.035 * math.sin(math.pi * t)))
            a = rng.uniform(0, math.pi)
            dv = Vector((0.0, math.cos(a), math.sin(a))) * 0.018
            cylinder(bbm, c0 - dv, c0 + dv, 0.0022, segs=3, cap=False)
fence_posts = new_obj("FencePosts", bm, post_mat, smooth_angle=60)
fence_wire = new_obj("FenceWire", wbm, wire_mat)
fence_barbs = new_obj("FenceBarbs", bbm, wire_mat)
add_haze(post_mat, 60, 900, 0.8)

# ---------------------------------------------------------------- hay bales
straw_mat = bpy.data.materials.new("Straw")
straw_mat.use_nodes = True
sb = NB(straw_mat)
sbsdf = sb.n["Principled BSDF"]
stc = sb.node("ShaderNodeTexCoord")
smap = sb.node("ShaderNodeMapping")
smap.inputs["Scale"].default_value = (0.6, 0.6, 0.6)
sb.link(stc.outputs["Object"], smap.inputs[0])
sb.link(sb.tex("straw_albedo.png", smap.outputs[0]).outputs[0], sbsdf.inputs["Base Color"])
snm = sb.node("ShaderNodeNormalMap")
sb.link(sb.tex("straw_normal.png", smap.outputs[0], True).outputs[0], snm.inputs["Color"])
sb.link(snm.outputs[0], sbsdf.inputs["Normal"])
sbsdf.inputs["Roughness"].default_value = 0.9
add_haze(straw_mat, 60, 900, 0.8)
bales = []
for i, (x, y, rz) in enumerate([(-12.5, 15.5, 0.3), (-10.9, 17.4, 1.4)]):
    bm = bmesh.new()
    g = bmesh.ops.create_cone(bm, cap_ends=True, segments=40, radius1=0.78, radius2=0.78, depth=1.2)
    # soften the rounded shoulders and the flat-bottom sag
    for v in g["verts"]:
        if abs(v.co.z) > 0.59:
            v.co.x *= 0.93
            v.co.y *= 0.93
    bmesh.ops.subdivide_edges(bm, edges=[e for e in bm.edges if abs(e.verts[0].co.z - e.verts[1].co.z) > 1],
                              cuts=6)
    for v in bm.verts:
        v.co.z *= 1.0
        if v.co.x < -0.62:
            v.co.x = -0.62 - (v.co.x + 0.62) * 0.3                   # settled flat side
    ob = new_obj(f"HayBale{i}", bm, straw_mat, smooth_angle=50)
    zg = float(T.height(np.array(x), np.array(y), 0, 0))
    ob.rotation_euler = (0, math.pi / 2, rz)
    ob.location = (x, y, zg + 0.66)
    bales.append(ob)

# -------------------------------------------------------------------- water
water_mat = bpy.data.materials.new("Water")
water_mat.use_nodes = True
wb2 = NB(water_mat)
wbsdf = wb2.n["Principled BSDF"]
wbsdf.inputs["Base Color"].default_value = (*srgb("#3a2a1c"), 1)
wbsdf.inputs["Roughness"].default_value = 0.035
wbsdf.inputs["IOR"].default_value = 1.33
wtc = wb2.node("ShaderNodeTexCoord")
wmp = wb2.node("ShaderNodeMapping")
wmp.inputs["Scale"].default_value = (0.22, 0.22, 0.22)
wb2.link(wtc.outputs["Object"], wmp.inputs[0])
wn = wb2.node("ShaderNodeNormalMap")
wn.inputs["Strength"].default_value = 0.35
wb2.link(wb2.tex("water_normal.png", wmp.outputs[0], True, proj='FLAT').outputs[0], wn.inputs["Color"])
wb2.link(wn.outputs[0], wbsdf.inputs["Normal"])
bm = bmesh.new()
bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=1.0)
water = new_obj("Water", bm, water_mat)
water.scale = (C.PIT_HALF[0] + 1.5, C.PIT_HALF[1] + 1.5, 1)
water.location = (C.PIT_CENTER[0], C.PIT_CENTER[1], -10)

# ---------------------------------------------------------------------- fx
fx_mat = bpy.data.materials.new("FX")
fx_mat.use_nodes = True
fb = NB(fx_mat)
fbsdf = fb.n["Principled BSDF"]
ftex = fb.node("ShaderNodeTexImage", image=img("puff.png"))
fuv = fb.node("ShaderNodeTexCoord")
fb.link(fuv.outputs["UV"], ftex.inputs[0])
fcol = fb.node("ShaderNodeVertexColor", layer_name="Col")
fb.link(fcol.outputs["Color"], fbsdf.inputs["Base Color"])
fbsdf.inputs["Roughness"].default_value = 1.0
fbsdf.inputs["Specular IOR Level"].default_value = 0.0
ftr = fb.node("ShaderNodeBsdfTransparent")
fmix = fb.node("ShaderNodeMixShader")
fb.link(fb.math('MULTIPLY', ftex.outputs["Alpha"], fcol.outputs["Alpha"]), fmix.inputs[0])
fb.link(ftr.outputs[0], fmix.inputs[1])
fb.link(fbsdf.outputs[0], fmix.inputs[2])
fb.link(fmix.outputs[0], fb.n["Material Output"].inputs["Surface"])
clod_mat = material("Clod", srgb("#6d3522"), rough=0.95, use_vcol=False)
fx = new_obj("FX", bmesh.new())
fx.data.materials.append(fx_mat)
fx.data.materials.append(clod_mat)

# ---------------------------------------------------------------- camera
cam = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
scene.collection.objects.link(cam)
scene.camera = cam
cam.data.clip_start = 0.1
cam.data.clip_end = 4000
cam.data.sensor_fit = 'VERTICAL'

# ------------------------------------------------------------ render setup
scene.render.engine = 'CYCLES'
scene.cycles.samples = 28
scene.cycles.use_denoising = True
scene.cycles.use_adaptive_sampling = True
scene.cycles.adaptive_threshold = 0.03
scene.cycles.max_bounces = 4
scene.cycles.diffuse_bounces = 2
scene.cycles.glossy_bounces = 2
scene.cycles.transmission_bounces = 2
scene.cycles.transparent_max_bounces = 64
scene.cycles.volume_bounces = 0
scene.cycles.caustics_reflective = False
scene.cycles.caustics_refractive = False
scene.cycles.blur_glossy = 1.0
scene.render.film_transparent = False
for vt in ("ACES 2.0", "ACES 1.3", "AgX", "Filmic"):
    try:
        scene.view_settings.view_transform = vt
        break
    except TypeError:
        continue
try:
    scene.view_settings.look = 'AgX - Medium High Contrast' if scene.view_settings.view_transform == 'AgX' else 'None'
except TypeError:
    pass
scene.view_settings.exposure = 1.15
print("view transform:", scene.view_settings.view_transform)

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "scene.blend"))

import json  # noqa: E402
with open(os.path.join(OUT, "trees.json"), "w") as f:
    json.dump(tree_records, f)

# --------------------------------------------- export env.glb for the web
for ob in bpy.context.scene.objects:
    ob.select_set(False)
for ob in [fence_posts, fence_wire, ridges_ob] + bales:
    ob.select_set(True)
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "env_raw.glb"), export_format='GLB', use_selection=True,
                          export_animations=False, export_vertex_color='ACTIVE', export_yup=True)
print("scene built")
