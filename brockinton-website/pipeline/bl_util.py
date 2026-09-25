"""Small Blender helpers shared by the build scripts."""
import math
import bpy  # noqa: F401  (must load before bmesh/mathutils)
import bmesh
from mathutils import Vector, Matrix


def srgb(h):
    """'#rrggbb' -> linear RGB tuple."""
    h = h.lstrip('#')
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def material(name, color=(0.8, 0.8, 0.8), rough=0.5, metal=0.0, coat=0.0, alpha=1.0,
             transmission=0.0, use_vcol=True, emission=None):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    bsdf.inputs["Coat Weight"].default_value = coat
    bsdf.inputs["Alpha"].default_value = alpha
    bsdf.inputs["Transmission Weight"].default_value = transmission
    if emission:
        bsdf.inputs["Emission Color"].default_value = (*emission, 1)
        bsdf.inputs["Emission Strength"].default_value = 4.0
    if use_vcol:
        # vertex colour carries dirt and mud; multiplies the paint colour
        attr = nt.nodes.new("ShaderNodeVertexColor")
        attr.layer_name = "Col"
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = 'RGBA'
        mix.blend_type = 'MULTIPLY'
        mix.inputs["Factor"].default_value = 1.0
        mix.inputs[6].default_value = (*color, 1)
        nt.links.new(attr.outputs["Color"], mix.inputs[7])
        nt.links.new(mix.outputs[2], bsdf.inputs["Base Color"])
    if alpha < 1:
        m.surface_render_method = 'BLENDED'
    return m


def new_obj(name, bm, mat=None, parent=None, smooth_angle=None):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    if mat:
        me.materials.append(mat)
    if parent:
        ob.parent = parent
    if smooth_angle is not None:
        for p in me.polygons:
            p.use_smooth = True
        try:
            me.set_sharp_from_angle(angle=math.radians(smooth_angle))
        except AttributeError:
            pass
    return ob


def empty(name, parent=None, loc=(0, 0, 0)):
    ob = bpy.data.objects.new(name, None)
    ob.empty_display_size = 0.2
    bpy.context.scene.collection.objects.link(ob)
    ob.parent = parent
    ob.location = loc
    return ob


def box(bm, center, size, bevel=0.0, segs=2, mat_index=0):
    """Axis-aligned box into bm, optionally bevelled."""
    geom = bmesh.ops.create_cube(bm, size=1.0)
    verts = geom["verts"]
    bmesh.ops.scale(bm, vec=Vector(size), verts=verts)
    bmesh.ops.translate(bm, vec=Vector(center), verts=verts)
    faces = list({f for v in verts for f in v.link_faces})
    for f in faces:
        f.material_index = mat_index
    if bevel > 0:
        edges = list({e for v in verts for e in v.link_edges})
        bmesh.ops.bevel(bm, geom=edges, offset=bevel, segments=segs, profile=0.5, affect='EDGES')
    return verts


def cylinder(bm, p0, p1, r, segs=24, cap=True, mat_index=0, r1=None):
    """Cylinder from p0 to p1."""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    L = d.length
    geom = bmesh.ops.create_cone(bm, cap_ends=cap, cap_tris=False, segments=segs,
                                 radius1=r, radius2=r if r1 is None else r1, depth=L)
    verts = geom["verts"]
    rotq = Vector((0, 0, 1)).rotation_difference(d.normalized())
    bmesh.ops.rotate(bm, cent=Vector(), matrix=rotq.to_matrix(), verts=verts)
    bmesh.ops.translate(bm, vec=(p0 + p1) / 2, verts=verts)
    for f in {f for v in verts for f in v.link_faces}:
        f.material_index = mat_index
    return verts


def extrude_profile(bm, pts, x0, x1, bevel=0.0, mat_index=0):
    """Extrude a 2D (y, z) polygon along X from x0 to x1."""
    vs0 = [bm.verts.new((x0, y, z)) for y, z in pts]
    vs1 = [bm.verts.new((x1, y, z)) for y, z in pts]
    n = len(pts)
    faces = [bm.faces.new(vs0[::-1]), bm.faces.new(vs1)]
    for i in range(n):
        j = (i + 1) % n
        faces.append(bm.faces.new((vs0[i], vs0[j], vs1[j], vs1[i])))
    for f in faces:
        f.material_index = mat_index
    bmesh.ops.recalc_face_normals(bm, faces=faces)
    if bevel > 0:
        edges = list({e for f in faces for e in f.edges})
        bmesh.ops.bevel(bm, geom=edges, offset=bevel, segments=2, profile=0.5, affect='EDGES',
                        clamp_overlap=True)
    return vs0 + vs1


def catmull_closed(pts, n=6):
    out = []
    m = len(pts)
    for i in range(m):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[(i + 1) % m], pts[(i + 2) % m]
        for k in range(n):
            t = k / n
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * b) + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t2 +
                                    (-a + 3 * b - 3 * c + d) * t3) for a, b, c, d in zip(p0, p1, p2, p3)))
    return out


def text_mesh(name, text, font_path, size, parent=None, mat=None, extrude=0.004):
    cu = bpy.data.curves.new(name, 'FONT')
    cu.body = text
    cu.font = bpy.data.fonts.load(font_path)
    cu.size = size
    cu.extrude = extrude
    cu.align_x = 'CENTER'
    cu.align_y = 'CENTER'
    ob = bpy.data.objects.new(name + "_tmp", cu)
    bpy.context.scene.collection.objects.link(ob)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    bpy.data.objects.remove(ob)
    out = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(out)
    if mat:
        me.materials.append(mat)
    out.parent = parent
    return out


def paint_vcol(ob, fn):
    """fn(world_co, normal) -> (r, g, b) multiplier; stored per corner as 'Col'."""
    me = ob.data
    if "Col" not in me.color_attributes:
        me.color_attributes.new("Col", 'FLOAT_COLOR', 'CORNER')
    attr = me.color_attributes["Col"]
    mw = ob.matrix_world
    for poly in me.polygons:
        n = (mw.to_3x3() @ poly.normal).normalized()
        for li in poly.loop_indices:
            v = me.vertices[me.loops[li].vertex_index].co
            c = fn(mw @ v, n)
            attr.data[li].color = (*c, 1.0)
