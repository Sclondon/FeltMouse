# Shape helpers shared by the build scripts (build_mouse.py, build_kitchen.py): every part is a closed mesh
# made with bmesh, given a named material whose colour comes from COL (the scripts fill it in).
# Names starting glow_ shine by themselves; ROUGH and CLEAR give a material a shine or see-through-ness.
import bpy, bmesh, math
from mathutils import Vector, Matrix

COL = {}
ROUGH = {}
CLEAR = {}


def mat(name):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*COL[name], 1.0)
    b.inputs["Roughness"].default_value = ROUGH.get(name, 0.15 if name.startswith("bead") else 1.0)
    if name.startswith("glow_"):
        b.inputs["Emission Color"].default_value = (*COL[name], 1.0)
        b.inputs["Emission Strength"].default_value = 1.6
    if name in CLEAR:
        b.inputs["Alpha"].default_value = CLEAR[name]
        m.blend_method = "BLEND"
    m.diffuse_color = (*COL[name], 1.0)
    return m


def finish(name, bm, material, smooth=True, subsurf=0, matrix=None):
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    # every part is closed: a negative volume means it is inside out
    vol = bm.calc_volume(signed=True)
    if vol < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
        print("FLIPPED", name)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = smooth
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    me.materials.append(mat(material))
    if matrix is not None:
        o.matrix_world = matrix
    if subsurf:
        m = o.modifiers.new("subsurf", "SUBSURF")
        m.levels = subsurf
        m.render_levels = subsurf
    return o


def ellipsoid(name, centre, radii, material, rot=None, deform=None, subsurf=1):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=28, v_segments=14, radius=1.0)
    for v in bm.verts:
        c = Vector((v.co.x * radii[0], v.co.y * radii[1], v.co.z * radii[2]))
        if deform:
            c = deform(c)
        if rot is not None:
            c = rot @ c
        v.co = c + Vector(centre)
    return finish(name, bm, material, subsurf=subsurf)


def lathe(name, profile, material, segs=56, mod=None, subsurf=0):
    bm = bmesh.new()
    rings = []
    for (r, z) in profile:
        if r <= 1e-6:
            rings.append([bm.verts.new((0, 0, z))])
            continue
        ring = []
        for i in range(segs):
            a = math.tau * i / segs
            rr, zz = (r, z) if mod is None else mod(a, r, z)
            ring.append(bm.verts.new((rr * math.sin(a), -rr * math.cos(a), zz)))
        rings.append(ring)
    for a, b in zip(rings, rings[1:]):
        for i in range(segs):
            j = (i + 1) % segs
            if len(a) == 1 and len(b) == 1:
                continue
            if len(a) == 1:
                bm.faces.new((a[0], b[i], b[j]))
            elif len(b) == 1:
                bm.faces.new((a[i], b[0], a[j]))
            else:
                bm.faces.new((a[i], b[i], b[j], a[j]))
    return finish(name, bm, material, subsurf=subsurf)


def torus(name, R, r, material, matrix, segs_R=44, segs_r=14):
    bm = bmesh.new()
    rings = []
    for i in range(segs_R):
        a = math.tau * i / segs_R
        ring = []
        for k in range(segs_r):
            b = math.tau * k / segs_r
            d = R + r * math.cos(b)
            ring.append(bm.verts.new(matrix @ Vector((d * math.cos(a), d * math.sin(a), r * math.sin(b)))))
        rings.append(ring)
    for i in range(segs_R):
        a, b = rings[i], rings[(i + 1) % segs_R]
        for k in range(segs_r):
            l = (k + 1) % segs_r
            bm.faces.new((a[k], b[k], b[l], a[l]))
    return finish(name, bm, material)


def spline(points, per=8):
    """Catmull-Rom through the points."""
    pts = [Vector(p) for p in points]
    ext = [pts[0] * 2 - pts[1]] + pts + [pts[-1] * 2 - pts[-2]]
    out = []
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
        for s in range(per):
            t = s / per
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t * t * t))
    out.append(pts[-1])
    return out


def tube(name, points, radius, material, segs=10):
    pts = [Vector(p) for p in points]
    bm = bmesh.new()
    tang = []
    for i in range(len(pts)):
        a = pts[max(i - 1, 0)]
        b = pts[min(i + 1, len(pts) - 1)]
        tang.append((b - a).normalized())
    n = tang[0].orthogonal().normalized()
    rings = []
    for i, p in enumerate(pts):
        t = tang[i]
        n = (n - t * n.dot(t)).normalized()
        bn = t.cross(n)
        rings.append([bm.verts.new(p + (n * math.cos(math.tau * k / segs) + bn * math.sin(math.tau * k / segs)) * radius)
                      for k in range(segs)])
    for a, b in zip(rings, rings[1:]):
        for k in range(segs):
            l = (k + 1) % segs
            bm.faces.new((a[k], b[k], b[l], a[l]))
    c0 = bm.verts.new(pts[0] - tang[0] * radius * 0.7)
    c1 = bm.verts.new(pts[-1] + tang[-1] * radius * 0.7)
    for k in range(segs):
        l = (k + 1) % segs
        bm.faces.new((c0, rings[0][k], rings[0][l]))
        bm.faces.new((c1, rings[-1][l], rings[-1][k]))
    return finish(name, bm, material)


def prism(name, poly, z0, z1, material, matrix):
    bm = bmesh.new()
    lo = [bm.verts.new((x, y, z0)) for (x, y) in poly]
    hi = [bm.verts.new((x, y, z1)) for (x, y) in poly]
    bm.faces.new(hi)
    bm.faces.new(list(reversed(lo)))
    n = len(poly)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((lo[i], lo[j], hi[j], hi[i]))
    return finish(name, bm, material, smooth=False, matrix=matrix)


