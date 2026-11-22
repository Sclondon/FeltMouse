# Builds the Christmas light bulbs for GameCommon's christmas-lights component.
#
#   blender -b --factory-startup --python build_christmas_lights.py [-- <folder for the look-over sheets>]
#
# Writes, beside this file:  christmas_lights.blend           (every bulb as an object, to open and edit)
#                 and in ../models:    christmas_lights.glb   (what the game loads; one mesh per bulb, by name)
#                 and in ../textures:  socket_atlas.png       (the sockets' and wire's little picture)
#
# Every bulb is real size in metres, standing on Blender's +Z (the game's +Y) with its origin where the wire passes
# through the socket. Each has two materials: "glass" (the lit part) and "socket" (plastic, metal). A "_lo" twin of
# each is the far / phone version.
#
# UVs: the glass has u round the bulb and v from the socket (Blender v 1, so the game reads 0) to the tip (the game
# reads 1): the glass shader dims the glow toward the socket with it. Socket parts point into socket_atlas.png's four
# bands. A second UV layer, "glow", carries in u how much of the bulb's light spills on that point (1 at the socket's
# lip by the glass, 0 lower down, 1 over all the glass).
#
# Every closed part is checked for inside-out faces (a ray from each triangle along its normal must leave the part an
# even number of times, and its signed volume must be positive); the script stops with an error if any fails.

import bpy
import bmesh
import math
import os
import sys
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS = os.path.normpath(os.path.join(HERE, "..", "models"))
TEXTURES = os.path.normpath(os.path.join(HERE, "..", "textures"))
os.makedirs(MODELS, exist_ok=True)
os.makedirs(TEXTURES, exist_ok=True)
SHEETS = ""
if "--" in sys.argv:
    rest = sys.argv[sys.argv.index("--") + 1:]
    if rest:
        SHEETS = rest[0]
        os.makedirs(SHEETS, exist_ok=True)

GLASS, SOCKET = 0, 1
# The atlas's bands, as Blender v (0 at the bottom of the picture). "ribbed" and "plastic" are grey and take the
# wire's colour in the game; "brass" and "nickel" are painted as they are.
BANDS = {"ribbed": (0.0, 0.25), "brass": (0.25, 0.5), "plastic": (0.5, 0.75), "nickel": (0.75, 1.0)}
PAD = 0.2  # the share of a band left unused at its top and bottom, so neighbours do not bleed in


# ------------------------------------------------------------------------------------------------ the atlas
def make_atlas():
    size = 64
    px = [0.0] * (size * size * 4)
    for y in range(size):
        band = y // 16
        for x in range(size):
            if band == 0:  # ribbed plastic: eight ribs across, a light crest and a dark groove
                rib = 0.5 + 0.5 * math.cos(math.tau * x / 8.0)
                g = 0.34 + 0.30 * rib ** 1.5
                c = (g, g, g, 0.0)
            elif band == 1 or band == 3:  # a metal screw collar: threads, one side catching the light
                base = (0.80, 0.62, 0.27) if band == 1 else (0.74, 0.75, 0.78)
                thread = 0.72 + 0.28 * math.cos(math.tau * (y % 16) / 3.2)
                side = 0.82 + 0.26 * math.cos(math.tau * x / 64.0) ** 2
                k = thread * side
                c = (min(1.0, base[0] * k), min(1.0, base[1] * k), min(1.0, base[2] * k), 1.0)
            else:  # smooth plastic
                c = (0.5, 0.5, 0.5, 0.0)
            i = (y * size + x) * 4
            px[i:i + 4] = c
    img = bpy.data.images.new("socket_atlas", size, size, alpha=True)
    img.alpha_mode = "STRAIGHT"
    img.pixels.foreach_set(px)
    img.filepath_raw = os.path.join(TEXTURES, "socket_atlas.png")
    img.file_format = "PNG"
    img.save()
    img.alpha_mode = "NONE"  # in Blender, show the grey plastic (alpha only tells the game what to tint)
    return img


# ------------------------------------------------------------------------------------------------ building
class Build:
    def __init__(self):
        self.v, self.f, self.uv, self.glow, self.mat, self.smooth, self.parts = [], [], [], [], [], [], []

    def begin(self, name):
        self._name, self._start = name, len(self.f)

    def end(self):
        self.parts.append((self._name, self._start, len(self.f)))

    def vert(self, p):
        self.v.append((float(p[0]), float(p[1]), float(p[2])))
        return len(self.v) - 1

    def face(self, idx, uvs, glows, mat, smooth):
        self.f.append(list(idx))
        self.uv.append(list(uvs))
        self.glow.append(list(glows))
        self.mat.append(mat)
        self.smooth.append(smooth)

    def out(self, idx, uvs, glows, mat, smooth, hint):
        """A face wound so that its normal points along `hint`."""
        a, b, c = (Vector(self.v[i]) for i in idx[:3])
        if (b - a).cross(c - a).dot(hint) < 0:
            idx, uvs, glows = idx[::-1], uvs[::-1], glows[::-1]
        self.face(idx, uvs, glows, mat, smooth)

    def tris(self):
        return sum(len(f) - 2 for f in self.f)


def _value(g, z):
    return g(z) if callable(g) else g


def lathe(b, name, profile, segs, mat, band=None, reps=1.0, glow=0.0, smooth=True):
    """Turns `profile` [(radius, z)...] about z. It runs from the bottom up the outside; radius 0 is a pole."""
    b.begin(name)
    zs = [p[1] for p in profile]
    z0, z1 = min(zs), max(zs)
    run = [0.0]
    for k in range(1, len(profile)):
        run.append(run[-1] + math.hypot(profile[k][0] - profile[k - 1][0], profile[k][1] - profile[k - 1][1]))
    rings = []
    for (r, z) in profile:
        if r < 1e-9:
            rings.append([b.vert((0, 0, z))] * segs)
        else:
            rings.append([b.vert((r * math.cos(math.tau * j / segs), r * math.sin(math.tau * j / segs), z))
                          for j in range(segs)])

    def uv(k, j):
        if mat == GLASS:
            return (j / segs, 1.0 - (profile[k][1] - z0) / (z1 - z0))
        lo, hi = BANDS[band]
        return (j / segs * reps, lo + (hi - lo) * (PAD + (1.0 - 2.0 * PAD) * run[k] / run[-1]))

    for k in range(len(profile) - 1):
        A, B = rings[k], rings[k + 1]
        ga, gb = _value(glow, profile[k][1]), _value(glow, profile[k + 1][1])
        for j in range(segs):
            j1 = (j + 1) % segs
            corners = [(A[j], uv(k, j), ga), (A[j1], uv(k, j + 1), ga), (B[j1], uv(k + 1, j + 1), gb),
                       (B[j], uv(k + 1, j), gb)]
            seen, keep = set(), []
            for c in corners:
                if c[0] not in seen:
                    seen.add(c[0])
                    keep.append(c)
            if len(keep) >= 3:
                b.face([c[0] for c in keep], [c[1] for c in keep], [c[2] for c in keep], mat, smooth)
    b.end()


def faceted(b, name, profile, sides, twist):
    """Cut glass: rings of `sides` flat-shaded points, each ring turned `twist` radians on from the last."""
    b.begin(name)
    zs = [p[1] for p in profile]
    z0, z1 = min(zs), max(zs)
    rings, turns = [], []
    for k, (r, z) in enumerate(profile):
        turns.append(k * twist)
        if r < 1e-9:
            rings.append([b.vert((0, 0, z))] * sides)
        else:
            rings.append([b.vert((r * math.cos(math.tau * j / sides + k * twist),
                                  r * math.sin(math.tau * j / sides + k * twist), z)) for j in range(sides)])

    def uv(k, j):
        return (j / sides + turns[k] / math.tau, 1.0 - (profile[k][1] - z0) / (z1 - z0))

    for k in range(len(profile) - 1):
        A, B = rings[k], rings[k + 1]
        for j in range(sides):
            j1 = (j + 1) % sides
            for tri in (((A[j], uv(k, j)), (A[j1], uv(k, j + 1)), (B[j], uv(k + 1, j))),
                        ((A[j1], uv(k, j + 1)), (B[j1], uv(k + 1, j + 1)), (B[j], uv(k + 1, j)))):
                if len({t[0] for t in tri}) == 3:
                    b.face([t[0] for t in tri], [t[1] for t in tri], [1.0, 1.0, 1.0], GLASS, False)
    b.end()


def box(b, name, lo, hi, band):
    b.begin(name)
    lo, hi = Vector(lo), Vector(hi)
    mid = (lo + hi) * 0.5
    blo, bhi = BANDS[band]
    corners = {}
    for i in range(8):
        corners[i] = b.vert((hi.x if i & 1 else lo.x, hi.y if i & 2 else lo.y, hi.z if i & 4 else lo.z))
    quads = ((0, 1, 3, 2), (4, 5, 7, 6), (0, 1, 5, 4), (2, 3, 7, 6), (0, 2, 6, 4), (1, 3, 7, 5))
    for q in quads:
        idx = [corners[i] for i in q]
        centre = sum((Vector(b.v[i]) for i in idx), Vector()) / 4.0
        uvs = [(0.3 + 0.1 * (n % 2), blo + (bhi - blo) * (0.4 + 0.2 * (n // 2))) for n in range(4)]
        b.out(idx, uvs, [0.0] * 4, SOCKET, False, centre - mid)
    b.end()


def star(b, name, zc, outer, inner, half, rim, bevel=True):
    """A five-pointed star standing in the x-z plane, a point up, puffed to `half` thick at its middle."""
    b.begin(name)
    z0, z1 = zc - outer * math.cos(math.radians(36)), zc + outer

    def uv(p):
        return (0.5 + p[0] / (2.4 * outer), 1.0 - min(1.0, max(0.0, (p[2] - z0) / (z1 - z0))))

    pts = []
    for i in range(10):
        a = math.pi / 2 + math.tau * i / 10
        r = outer if i % 2 == 0 else inner
        pts.append((r * math.cos(a), r * math.sin(a) + zc))
    centre = Vector((0, 0, zc))
    front = b.vert((0, -half, zc))
    back = b.vert((0, half, zc))
    if bevel:
        fr = [b.vert((x, -rim, z)) for (x, z) in pts]
        bk = [b.vert((x, rim, z)) for (x, z) in pts]
    else:
        fr = bk = [b.vert((x, 0, z)) for (x, z) in pts]
    for i in range(10):
        i1 = (i + 1) % 10
        for apex, ring, side in ((front, fr, -1.0), (back, bk, 1.0)):
            idx = [apex, ring[i], ring[i1]]
            mid = sum((Vector(b.v[n]) for n in idx), Vector()) / 3.0
            hint = Vector((0, side, 0)) * 3.0 + (mid - centre).normalized()
            b.out(idx, [uv(b.v[n]) for n in idx], [1.0] * 3, GLASS, False, hint)
        if bevel:
            idx = [fr[i], fr[i1], bk[i1], bk[i]]
            mid = sum((Vector(b.v[n]) for n in idx), Vector()) / 4.0
            e = Vector(b.v[fr[i1]]) - Vector(b.v[fr[i]])
            hint = Vector((e.z, 0, -e.x))  # square to the edge, in the star's plane
            if hint.dot(mid - centre) < 0:
                hint = -hint
            b.out(idx, [uv(b.v[n]) for n in idx], [1.0] * 4, GLASS, False, hint)
    b.end()


def spill(top, reach=0.010):
    """How much of the bulb's light falls on a socket: 1 at its lip (`top`), fading to 0 `reach` lower down."""
    return lambda z: min(1.0, max(0.0, (z - (top - reach)) / reach))


def husk(b, s, lo):
    """The push-in plastic base of a mini bulb, `s` times life size."""
    if lo:
        lathe(b, "husk", [(0, -0.004 * s), (0.0046 * s, -0.004 * s), (0.0060 * s, 0.012 * s), (0.0040 * s, 0.018 * s),
                          (0, 0.018 * s)], 5, SOCKET, "plastic", glow=spill(0.018 * s, 0.008 * s))
    else:
        lathe(b, "husk", [(0, -0.004 * s), (0.0042 * s, -0.004 * s), (0.0046 * s, 0.008 * s), (0.0060 * s, 0.009 * s),
                          (0.0060 * s, 0.012 * s), (0.0044 * s, 0.013 * s), (0.0040 * s, 0.018 * s), (0, 0.018 * s)],
              8, SOCKET, "ribbed", reps=1.0, glow=spill(0.018 * s, 0.008 * s))


def screw_socket(b, r, top, lo, metal, collar_r, collar_top):
    """A ribbed plastic socket with a clip on its side and the bulb's metal screw collar showing above it."""
    if lo:
        lathe(b, "socket", [(0, -0.005), (r, -0.005), (r * 1.08, top), (collar_r, collar_top), (0, collar_top)], 5,
              SOCKET, "ribbed", reps=1.0, glow=spill(collar_top))
        return
    lathe(b, "socket", [(0, -0.3 * r - 0.002), (r * 0.94, -0.3 * r - 0.001), (r, top - 0.0065), (r * 1.12, top - 0.005),
                        (r * 1.12, top - 0.0005), (0, top)], 10, SOCKET, "ribbed", reps=3.0, glow=spill(top))
    lathe(b, "collar", [(0, top - 0.001), (collar_r, top - 0.0005), (collar_r, collar_top - 0.001),
                        (0, collar_top)], 10, SOCKET, metal, reps=1.0, glow=1.0)
    box(b, "clip", (r - 0.001, -r * 0.3, 0.003), (r + 0.0045, r * 0.3, top - 0.009), "plastic")


def sphere_profile(r, zc, degrees):
    return [(r * math.cos(math.radians(a)), zc + r * math.sin(math.radians(a))) for a in degrees]


def build(kind, lo):
    b = Build()
    if kind == "c9":
        screw_socket(b, 0.0118, 0.0265, lo, "brass", 0.0085, 0.034)
        if lo:
            lathe(b, "glass", [(0, 0.032), (0.0085, 0.034), (0.0146, 0.050), (0.0104, 0.069), (0, 0.083)], 6, GLASS,
                  glow=1.0)
        else:
            lathe(b, "glass", [(0, 0.032), (0.0080, 0.0325), (0.0120, 0.0368), (0.0143, 0.043), (0.0149, 0.050),
                               (0.0139, 0.058), (0.0113, 0.066), (0.0076, 0.074), (0.0035, 0.080), (0, 0.083)], 12,
                  GLASS, glow=1.0)
    elif kind == "c7":
        screw_socket(b, 0.0088, 0.0215, lo, "nickel", 0.0060, 0.0275)
        if lo:
            lathe(b, "glass", [(0, 0.026), (0.0060, 0.0275), (0.0097, 0.041), (0.0066, 0.054), (0, 0.0635)], 6, GLASS,
                  glow=1.0)
        else:
            lathe(b, "glass", [(0, 0.026), (0.0056, 0.0265), (0.0082, 0.0300), (0.0096, 0.035), (0.0099, 0.040),
                               (0.0091, 0.046), (0.0072, 0.052), (0.0046, 0.058), (0.0018, 0.0622), (0, 0.0635)], 12,
                  GLASS, glow=1.0)
    elif kind == "globe":
        screw_socket(b, 0.0088, 0.0215, lo, "nickel", 0.0060, 0.0275)
        zc, r = 0.0505, 0.020
        if lo:
            lathe(b, "glass", [(0, 0.026), (0.0070, 0.0305)] + sphere_profile(r, zc, (-38, 8, 52)) + [(0, zc + r)],
                  6, GLASS, glow=1.0)
        else:
            lathe(b, "glass", [(0, 0.026), (0.0064, 0.0270)]
                  + sphere_profile(r, zc, (-62, -42, -21, 0, 21, 42, 61, 78)) + [(0, zc + r)], 14, GLASS, glow=1.0)
    elif kind == "mini":
        husk(b, 1.0, lo)
        if lo:
            lathe(b, "glass", [(0, 0.017), (0.0031, 0.019), (0.0031, 0.031), (0, 0.040)], 5, GLASS, glow=1.0)
        else:
            lathe(b, "glass", [(0, 0.017), (0.0027, 0.0175), (0.0031, 0.021), (0.0031, 0.030), (0.0024, 0.034),
                               (0.0010, 0.037), (0.0006, 0.0395), (0, 0.040)], 8, GLASS, glow=1.0)
    elif kind == "faceted":
        husk(b, 1.3, lo)
        if lo:
            faceted(b, "glass", [(0, 0.0225), (0.0086, 0.030), (0.0085, 0.044), (0, 0.0535)], 5, math.pi / 5)
        else:
            faceted(b, "glass", [(0, 0.0225), (0.0050, 0.0240), (0.0086, 0.030), (0.0098, 0.037), (0.0080, 0.045),
                                 (0.0042, 0.051), (0, 0.0535)], 7, math.pi / 7)
    elif kind == "star":
        husk(b, 1.0, lo)
        star(b, "glass", 0.0256, 0.0175, 0.0078, 0.0058, 0.0016, bevel=not lo)
    elif kind == "icicle":
        husk(b, 1.0, lo)
        if lo:
            faceted(b, "glass", [(0, 0.017), (0.0074, 0.027), (0.0048, 0.055), (0, 0.085)], 4, math.radians(30))
        else:
            faceted(b, "glass", [(0, 0.017), (0.0044, 0.018), (0.0074, 0.027), (0.0064, 0.041), (0.0048, 0.055),
                                 (0.0031, 0.068), (0.0014, 0.080), (0, 0.085)], 6, math.radians(18))
    return b


# ------------------------------------------------------------------------------------------------ checking
def check(name, b):
    """Each part: positive signed volume, and every triangle's normal leaves the part an even number of times."""
    bad = 0
    for (part, start, end) in b.parts:
        used = sorted({i for f in b.f[start:end] for i in f})
        remap = {i: n for n, i in enumerate(used)}
        verts = [Vector(b.v[i]) * 1000.0 for i in used]  # in millimetres, so the small offsets are safe
        tris = []
        for f in b.f[start:end]:
            for n in range(1, len(f) - 1):
                tris.append((remap[f[0]], remap[f[n]], remap[f[n + 1]]))
        volume = sum(verts[a].dot(verts[bb].cross(verts[c])) for (a, bb, c) in tris) / 6.0
        tree = BVHTree.FromPolygons(verts, tris, epsilon=0.0)
        wrong = 0
        for (a, bb, c) in tris:
            n = (verts[bb] - verts[a]).cross(verts[c] - verts[a])
            if n.length < 1e-9:
                continue
            n.normalize()
            at = (verts[a] + verts[bb] + verts[c]) / 3.0 + n * 1e-3
            hits = 0
            while hits < 64:
                hit = tree.ray_cast(at, n)
                if hit[0] is None:
                    break
                hits += 1
                at = hit[0] + n * 1e-3
            if hits % 2:
                wrong += 1
        ok = volume > 0 and wrong == 0
        if not ok:
            bad += 1
        print("  %-14s %-7s %3d tris  volume %8.1f mm3  %d of them inside out  %s"
              % (name, part, len(tris), volume, wrong, "ok" if ok else "FAIL"))
    return bad


def finish(name, b, mats, at):
    me = bpy.data.meshes.new(name)
    me.from_pydata(b.v, [], b.f)
    me.uv_layers.new(name="UVMap")
    me.uv_layers.new(name="glow")
    uvl, gl = me.uv_layers["UVMap"], me.uv_layers["glow"]  # looked up after both exist (making one moves the other)
    for fi, poly in enumerate(me.polygons):
        poly.material_index = b.mat[fi]
        poly.use_smooth = b.smooth[fi]
        for c, li in enumerate(poly.loop_indices):
            uvl.data[li].uv = b.uv[fi][c]
            gl.data[li].uv = (b.glow[fi][c], 0.0)
    for m in mats:
        me.materials.append(m)
    me.validate()
    me.update()
    bm = bmesh.new()
    bm.from_mesh(me)
    for e in bm.edges:  # keep the corners of lips and rims crisp
        if (len(e.link_faces) == 2 and e.calc_face_angle(0.0) > math.radians(38)
                and all(f.material_index == SOCKET for f in e.link_faces)):  # glass stays one smooth skin
            e.smooth = False
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    ob.location = at
    bpy.context.scene.collection.objects.link(ob)
    return ob


# ------------------------------------------------------------------------------------------------ look-over sheets
def sheet(path, objects):
    """Each bulb in a row of five: front, right, back, left, and from the tip down. Brought to one height."""
    scene = bpy.context.scene
    made = []
    cell_w, cell_h = 1.0, 1.25
    for row, ob in enumerate(objects):
        pts = [Vector(v.co) for v in ob.data.vertices]
        zmin, zmax = min(p.z for p in pts), max(p.z for p in pts)
        k = 1.0 / (zmax - zmin)
        for col in range(5):
            twin = bpy.data.objects.new("look", ob.data)
            scene.collection.objects.link(twin)
            twin.scale = (k, k, k)
            cx, cz = col * cell_w, -row * cell_h
            if col < 4:
                twin.rotation_euler = (0, 0, math.radians(90 * col))
                twin.location = (cx, 0, cz - 0.5 - zmin * k)
            else:
                twin.rotation_euler = (math.radians(90), 0, 0)
                twin.location = (cx, 0.5, cz)
            made.append(twin)
    cam_data = bpy.data.cameras.new("look_cam")
    cam_data.type = "ORTHO"
    w, h = 5 * cell_w, len(objects) * cell_h
    cam_data.ortho_scale = max(w, h)
    cam = bpy.data.objects.new("look_cam", cam_data)
    scene.collection.objects.link(cam)
    cam.location = (2 * cell_w, -20, -(len(objects) - 1) * cell_h * 0.5)
    cam.rotation_euler = (math.radians(90), 0, 0)
    scene.camera = cam
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "TEXTURE"
    scene.display.shading.show_cavity = True
    scene.display.shading.show_object_outline = False
    scene.view_settings.view_transform = "Standard"
    scene.render.resolution_x = int(w * 300)
    scene.render.resolution_y = int(h * 300)
    scene.render.film_transparent = False
    scene.world = scene.world or bpy.data.worlds.new("w")
    scene.render.filepath = path
    hidden = [o for o in scene.collection.objects if o not in made and o != cam]
    for o in hidden:
        o.hide_render = True
    bpy.ops.render.render(write_still=True)
    for o in hidden:
        o.hide_render = False
    for o in made:
        bpy.data.objects.remove(o)
    bpy.data.objects.remove(cam)
    bpy.data.cameras.remove(cam_data)


# ------------------------------------------------------------------------------------------------ run
for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob)

atlas = make_atlas()

glass = bpy.data.materials.new("glass")
glass.use_nodes = True
bsdf = next(n for n in glass.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
bsdf.inputs["Base Color"].default_value = (0.85, 0.10, 0.06, 1.0)
bsdf.inputs["Roughness"].default_value = 0.15
bsdf.inputs["Emission Color"].default_value = (1.0, 0.25, 0.12, 1.0)
bsdf.inputs["Emission Strength"].default_value = 1.5
glass.diffuse_color = (0.85, 0.16, 0.10, 1.0)

socket = bpy.data.materials.new("socket")
socket.use_nodes = True
bsdf = next(n for n in socket.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
tex = socket.node_tree.nodes.new("ShaderNodeTexImage")
tex.image = atlas
socket.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
bsdf.inputs["Roughness"].default_value = 0.55
socket.diffuse_color = (0.3, 0.4, 0.3, 1.0)

KINDS = ["c9", "c7", "mini", "faceted", "globe", "star", "icicle"]
failed = 0
full, low = [], []
print("christmas lights: parts and their checks")
for i, kind in enumerate(KINDS):
    for lo in (False, True):
        name = "bulb_%s%s" % (kind, "_lo" if lo else "")
        b = build(kind, lo)
        failed += check(name, b)
        ob = finish(name, b, [glass, socket], (i * 0.06, 0.12 if lo else 0.0, 0.0))
        (low if lo else full).append(ob)
        print("%-16s %4d triangles" % (name, b.tris()))
if failed:
    print("FAILED: %d part(s) inside out or open" % failed)
    sys.exit(1)

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "christmas_lights.blend"))

for ob in bpy.data.objects:
    ob.select_set(ob in full or ob in low)
bpy.ops.export_scene.gltf(filepath=os.path.join(MODELS, "christmas_lights.glb"), export_format="GLB",
                          use_selection=True, export_apply=True, export_yup=True, export_image_format="NONE",
                          export_normals=True, export_texcoords=True, export_materials="EXPORT",
                          export_animations=False)

if SHEETS:
    sheet(os.path.join(SHEETS, "bulbs_full_a.png"), full[:4])
    sheet(os.path.join(SHEETS, "bulbs_full_b.png"), full[4:])
    sheet(os.path.join(SHEETS, "bulbs_low_a.png"), low[:4])
    sheet(os.path.join(SHEETS, "bulbs_low_b.png"), low[4:])
print("christmas lights: built")
