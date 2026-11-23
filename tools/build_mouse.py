# Builds the felt mouse in a mug of cocoa, after art_src/reference_photo.jpg.
#   blender -b --factory-startup --python tools/build_mouse.py
# Saves tools/mouse.blend (editable) and models/mouse.glb.
# Blender: Z up, the mouse faces -Y. One unit is about the mug's width.
# Material names carry the look: Godot's scripts/main.gd reads them (felt_*, fleece_*, bead_*, thread_*).
import bpy, bmesh, math, os
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

bpy.ops.wm.read_factory_settings(use_empty=True)
SCENE = bpy.context.scene
import sys
sys.path.insert(0, HERE)
from shapes import *  # mat, finish, ellipsoid, lathe, torus, spline, tube, prism, COL

COL.update({
    "felt_white": (0.93, 0.91, 0.86),
    "felt_brown": (0.33, 0.19, 0.10),
    "felt_red": (0.80, 0.04, 0.05),
    "felt_pink": (0.93, 0.62, 0.50),
    "felt_candy_red": (0.78, 0.05, 0.06),
    "felt_candy_white": (0.95, 0.94, 0.92),
    "felt_wafer": (0.36, 0.21, 0.11),
    "felt_black": (0.02, 0.02, 0.02),
    "fleece_white": (0.96, 0.95, 0.93),
    "bead_black": (0.01, 0.01, 0.01),
    "thread_white": (0.90, 0.88, 0.84),
})


# ---------------------------------------------------------------- the mug
MUG_TOP = 0.62


def mug_r(z):
    return 0.47 + 0.03 * z / MUG_TOP


lathe("Mug", [(0, 0), (0.40, 0), (0.455, 0.015), (0.472, 0.05), (mug_r(0.3), 0.3), (0.50, MUG_TOP), (0, MUG_TOP)],
      "felt_brown")
torus("MugFoot", 0.455, 0.022, "fleece_white", Matrix.Translation((0, 0, 0.012)))
torus("MugHandle", 0.19, 0.058, "felt_brown",
      Matrix.Translation((0.50, 0, 0.33)) @ Matrix.Diagonal((1, 1, 1.15, 1)) @ Matrix.Rotation(math.pi / 2, 4, "X"))

# the stitched snowflake on the front: threads lying on the mug's side
FLAKE = (0.12, 0.27)  # angle round the mug from the front, height


def stitch(name, d_ang, d_z):
    pts = []
    for i in range(13):
        t = i / 12 * 2 - 1
        a = FLAKE[0] + d_ang * t
        z = FLAKE[1] + d_z * t
        r = mug_r(z) + 0.006
        pts.append((r * math.sin(a), -r * math.cos(a), z))
    tube(name, pts, 0.0075, "thread_white", segs=6)


stitch("Stitch1", 0.40, 0.15)
stitch("Stitch2", 0.40, -0.15)
stitch("Stitch3", 0.46, -0.015)
stitch("Stitch4", 0.03, 0.10)

# ---------------------------------------------------------------- whipped cream (two folds of fleece)


def cream_wave(a, r, z):
    k = min(max((r - 0.35) / 0.25, 0.0), 1.0)
    w = 1.0 + k * (0.045 * math.sin(7 * a + 0.6) + 0.03 * math.sin(4 * a + 2.0))
    return r * w, z - k * 0.02 * math.sin(5 * a + 1.0)


lathe("CreamLower", [(0, 0.735), (0.30, 0.735), (0.50, 0.71), (0.59, 0.665), (0.615, 0.615), (0.57, 0.575),
                     (0.45, 0.57), (0, 0.57)], "fleece_white", mod=cream_wave, subsurf=1)


def cream_wave2(a, r, z):
    k = min(max((r - 0.2) / 0.2, 0.0), 1.0)
    return r * (1.0 + k * (0.05 * math.sin(5 * a + 2.2) + 0.03 * math.sin(3 * a))), z - k * 0.012 * math.sin(4 * a)


lathe("CreamUpper", [(0, 0.80), (0.22, 0.797), (0.36, 0.77), (0.425, 0.725), (0.38, 0.70), (0, 0.70)],
      "fleece_white", mod=cream_wave2, subsurf=1)

# ---------------------------------------------------------------- the mouse
ellipsoid("Body", (0, 0.05, 0.90), (0.21, 0.19, 0.25), "felt_white")

HEAD_C = Vector((0, -0.02, 1.25))
HEAD_R = 0.215


def snout(c):
    if c.y < 0:
        t = -c.y / HEAD_R
        s = 1.0 - 0.30 * t * t
        return Vector((c.x * s, c.y * 1.45, c.z * s - 0.05 * t))
    return c


head = ellipsoid("Head", HEAD_C, (HEAD_R, HEAD_R, HEAD_R), "felt_white", deform=snout)


def on_head(p, lift):
    ok, loc, nor, _ = head.closest_point_on_mesh(Vector(p))
    return loc + nor * lift


ellipsoid("Nose", (0, -0.336, 1.20), (0.038, 0.036, 0.036), "felt_black", subsurf=0)
for side, sx in (("L", -1), ("R", 1)):
    ellipsoid("Eye" + side, on_head((0.095 * sx, -0.25, 1.29), 0.006), (0.023, 0.023, 0.023), "bead_black", subsurf=0)
    turn = Matrix.Rotation(math.radians(-18 * sx), 3, "Z") @ Matrix.Rotation(math.radians(8 * sx), 3, "Y")
    ear_c = Vector((0.175 * sx, 0.02, 1.47))
    ellipsoid("Ear" + side, ear_c, (0.128, 0.024, 0.128), "felt_white", rot=turn)
    ellipsoid("EarInner" + side, ear_c + turn @ Vector((0, -0.018, -0.005)), (0.092, 0.012, 0.092), "felt_pink",
              rot=turn)

# two stiff whiskers a side, rooted in the snout behind the nose and fanned apart
for side, sx in (("L", -1), ("R", 1)):
    for k, (rise, back) in enumerate(((0.024, 0.02), (-0.020, 0.04))):
        lean = 0.012 * sx  # the real one sits a little askew
        tube("Whisker%s%d" % (side, k), [(0.03 * sx, -0.295, 1.205 + 0.25 * rise),
                                         (0.29 * sx, -0.295 + back, 1.205 + rise - lean)], 0.0055, "bead_black", segs=6)

# the scarf
# his collar: a flat band of red felt round the neck (a ring, not a fat tube), a little wider at the bottom
collar = lathe("Scarf", [(0.12, -0.042), (0.192, -0.048), (0.203, -0.034), (0.196, 0.034), (0.186, 0.046), (0.12, 0.04),
                         (0.12, -0.042)], "felt_red")
collar.data.transform(Matrix.Translation((0, 0.03, 1.07)) @ Matrix.Rotation(math.radians(-6), 4, "X"))

# arms: thin wrapped wire, bowed out to the sides and down round the candy, pink hands on the cream
ARMS = {
    "L": [(-0.14, 0.02, 1.00), (-0.31, -0.06, 0.99), (-0.39, -0.24, 0.88), (-0.33, -0.43, 0.78), (-0.24, -0.50, 0.725)],
    "R": [(0.14, 0.02, 1.00), (0.30, -0.07, 0.98), (0.36, -0.25, 0.87), (0.27, -0.44, 0.775), (0.15, -0.50, 0.72)],
}
HANDS = {"L": (-0.20, -0.585, 0.675), "R": (0.10, -0.585, 0.672)}
# the arms were a little too long (the user): everything from the shoulders out is drawn in toward them
SHOULDERS = Vector((0, 0.02, 1.0))
ARM_LENGTH = 0.6  # (0.85 was "still too long", the user)


def drawn_in(p):
    return SHOULDERS + (Vector(p) - SHOULDERS) * ARM_LENGTH


for side in ("L", "R"):
    path = spline([drawn_in(p) for p in ARMS[side]])
    HANDS[side] = drawn_in(HANDS[side])
    tube("Arm" + side, path, 0.021, "felt_white")
    end = path[-1]
    tube("Hand" + side, [end, (end + HANDS[side]) / 2, HANDS[side]], 0.023, "felt_pink")

# ---------------------------------------------------------------- the candy: three sheets of felt, red white red
CANDY_AT = drawn_in((0.0, -0.385, 0.815))
CANDY = (Matrix.Translation(CANDY_AT) @ Matrix.Rotation(math.radians(-7), 4, "Y")
         @ Matrix.Rotation(math.radians(52), 4, "X") @ Matrix.Scale(1.18, 4))


def candy_outline(grow=1.0):
    right = [(0.10, 0.07), (0.118, 0.034), (0.235, 0.092), (0.257, 0.058), (0.236, 0.030), (0.258, 0.0),
             (0.236, -0.030), (0.257, -0.058), (0.235, -0.092), (0.118, -0.034), (0.10, -0.07)]
    left = [(-x, -y) for (x, y) in right]
    return [(x * grow, y * grow) for (x, y) in right + left]


prism("CandyBack", candy_outline(), 0.0, 0.016, "felt_candy_red", CANDY)
prism("CandyMiddle", candy_outline(1.05), 0.016, 0.030, "felt_candy_white", CANDY)
prism("CandyFront", candy_outline(), 0.030, 0.046, "felt_candy_red", CANDY)
for i, x0 in enumerate((-0.058, 0.0, 0.058)):
    prism("CandyStripe%d" % i, [(x0 - 0.036, -0.064), (x0 - 0.006, -0.064), (x0 + 0.036, 0.064), (x0 + 0.006, 0.064)],
          0.046, 0.051, "felt_candy_white", CANDY)

# ---------------------------------------------------------------- the wafer straw with its spiral of white
W0 = Vector((-0.30, 0.13, 0.72))
W1 = Vector((-0.41, 0.15, 1.56))
tube("Wafer", [W0, W1], 0.042, "felt_wafer", segs=14)
axis = (W1 - W0).normalized()
side_a = axis.orthogonal().normalized()
side_b = axis.cross(side_a)
TURNS = 5.5
helix = []
for i in range(141):
    t = i / 140
    ang = math.tau * TURNS * t
    helix.append(W0.lerp(W1, 0.06 + 0.94 * t) + (side_a * math.cos(ang) + side_b * math.sin(ang)) * 0.044)
tube("WaferSwirl", helix, 0.017, "felt_candy_white", segs=8)
ellipsoid("WaferTop", W1, (0.036, 0.036, 0.02), "felt_candy_white", subsurf=0)

# ---------------------------------------------------------------- legs and a tail (not in the photo: designed in
# the toy's own way of making things: wrapped-wire limbs with pink felt ends, like his arms and hands)
HIP_Z = 0.70
for side, sx in (("L", -1), ("R", 1)):
    leg = spline([(0.09 * sx, 0.04, HIP_Z + 0.04), (0.115 * sx, -0.015, 0.56), (0.115 * sx, 0.0, 0.425)])
    tube("Leg" + side, leg, 0.021, "felt_white")
    ellipsoid("Foot" + side, (0.12 * sx, -0.06, 0.408), (0.052, 0.095, 0.028), "felt_pink",
              rot=Matrix.Rotation(math.radians(-12 * sx), 3, "Z"))
TAIL_BASE = Vector((0.0, 0.20, 0.76))
tube("Tail", spline([TAIL_BASE, (0.04, 0.36, 0.71), (0.15, 0.47, 0.74), (0.27, 0.46, 0.85), (0.28, 0.37, 0.97),
                     (0.20, 0.33, 1.05), (0.15, 0.37, 1.10)], per=6), 0.013, "felt_pink", segs=8)

# ---------------------------------------------------------------- rogue strings and loops
# Real felt sheds: long loose fibres that curl away from it, and little loops pulled out of the surface.
# Each is a thin three-sided tube rooted at a random point of a felt part; one mesh of them per colour.
import random

random.seed(7)
COL.update({
    "fibre_white": (0.97, 0.96, 0.93),
    "fibre_brown": (0.62, 0.42, 0.24),
    "fibre_red": (0.90, 0.14, 0.14),
})
FIBRE_R = 0.0017
DG = bpy.context.evaluated_depsgraph_get()


def strand_tube(bm, pts, radius):
    tang = [(pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized() for i in range(len(pts))]
    n = tang[0].orthogonal().normalized()
    rings = []
    for i, p in enumerate(pts):
        t = tang[i]
        n = (n - t * n.dot(t)).normalized()
        bn = t.cross(n)
        rings.append([bm.verts.new(p + (n * math.cos(math.tau * k / 3) + bn * math.sin(math.tau * k / 3)) * radius)
                      for k in range(3)])
    for a, b in zip(rings, rings[1:]):
        for k in range(3):
            l = (k + 1) % 3
            bm.faces.new((a[k], b[k], b[l], a[l]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])


def rogue_string(p, n):
    """A loose fibre: leaves the felt at a slant, curls one way, and sags."""
    t = n.orthogonal().normalized()
    t = (Matrix.Rotation(random.uniform(0, math.tau), 3, n) @ t)
    d = (n + t * random.uniform(0.0, 0.9)).normalized()
    bend = d.cross(Matrix.Rotation(random.uniform(0, math.tau), 3, d) @ d.orthogonal()).normalized()
    length = 0.03 + 0.15 * random.random() ** 2.2
    k = random.uniform(4.0, 45.0)  # curl: 1 / the radius it bends on
    sag = random.uniform(0.5, 3.0)
    wob = random.uniform(0.0, 0.006)
    pts = []
    for i in range(11):
        s = length * i / 10
        q = p - n * 0.004 + d * (math.sin(k * s) / k) + bend * ((1.0 - math.cos(k * s)) / k)
        q += Vector((0, 0, -sag * s * s)) + t * (wob * math.sin(s * 140.0))
        pts.append(q)
    return pts


def loopy(p, n):
    """A pulled loop: both feet in the felt, a round eye standing off it, leaning a little."""
    t = Matrix.Rotation(random.uniform(0, math.tau), 3, n) @ n.orthogonal().normalized()
    side = n.cross(t)
    r = 0.004 + 0.017 * random.random() ** 1.7  # mostly small, a few bigger, no two alike
    tall = random.uniform(0.8, 1.9)
    lean = random.uniform(-0.6, 0.6)
    pts = []
    for i in range(15):
        a = math.radians(28 + (360 - 56) * i / 14)
        up = (0.85 - math.cos(a)) * r * tall
        pts.append(p + n * up + t * (math.sin(a) * r) + side * (lean * up + 0.25 * r * math.sin(a * 0.5)))
    return pts


def shed(name, sources, material, strings, loops, keep=None):
    """sources: object names. strings / loops: how many of each over all of them, spread by area."""
    tris = []
    for src in sources:
        ev = bpy.data.objects[src].evaluated_get(DG)
        me = ev.to_mesh()
        me.calc_loop_triangles()
        for lt in me.loop_triangles:
            a, b, c = (me.vertices[i].co.copy() for i in lt.vertices)
            tris.append((lt.area, a, b, c, lt.normal.copy()))
        ev.to_mesh_clear()
    weights = [x[0] for x in tris]
    bm = bmesh.new()
    made = 0
    for kind, count in ((rogue_string, strings), (loopy, loops)):
        done = 0
        while done < count:
            _, a, b, c, n = random.choices(tris, weights)[0]
            u, v = random.random(), random.random()
            if u + v > 1:
                u, v = 1 - u, 1 - v
            p = a + (b - a) * u + (c - a) * v
            if keep and not keep(p, n):
                continue
            strand_tube(bm, kind(p, n), FIBRE_R)
            done += 1
            made += 1
    print("SHED", name, made)
    return finish(name, bm, material)


def flat_r(p):
    return math.hypot(p.x, p.y)


# the mug is the hairiest; nothing on its hidden top and bottom
shed("FibresMug", ["Mug", "MugHandle"], "fibre_brown", 300, 110, lambda p, n: abs(n.z) < 0.5 and 0.03 < p.z < 0.58)
shed("FibresCream", ["CreamLower", "CreamUpper", "MugFoot"], "fibre_white", 110, 90,
     lambda p, n: (p.z < 0.1 or n.z > -0.2) and (p.z < 0.1 or flat_r(p) > 0.24))
shed("FibresBody", ["Body"], "fibre_white", 60, 30, lambda p, n: 0.68 < p.z < 1.0)
# (the head's own, so that they turn with it; none on his face)
shed("FibresHead", ["Head", "EarL", "EarR"], "fibre_white", 55, 28,
     lambda p, n: p.z > 1.12 and not (p.y < -0.12 and 1.1 < p.z < 1.36 and abs(p.x) < 0.14))
shed("FibresScarf", ["Scarf"], "fibre_red", 22, 14, lambda p, n: n.x * p.x + n.y * (p.y - 0.03) > 0.0)
shed("FibresWafer", ["Wafer"], "fibre_brown", 25, 10, lambda p, n: p.z > 0.85)

# ---------------------------------------------------------------- the mouse as one thing to move
# Everything that is him hangs from MouseRoot; each leg and the tail hang from a pivot at its joint,
# so the game can lift him out of the cocoa, kick his legs and wag his tail (scripts/main.gd).


def pivot(name, at, parent=None):
    e = bpy.data.objects.new(name, None)
    e.empty_display_size = 0.05
    SCENE.collection.objects.link(e)
    e.matrix_world = Matrix.Translation(at)
    if parent:
        e.parent = parent
    return e


def hang(names, parent, at):
    for nm in names:
        o = bpy.data.objects[nm]
        world = o.matrix_world.copy()
        o.parent = parent
        o.matrix_parent_inverse = Matrix.Translation(at).inverted()
        o.matrix_world = world


ORIGIN = Vector((0, 0, 0))
root = pivot("MouseRoot", ORIGIN)
hang([o.name for o in SCENE.objects if o.type == "MESH" and o.name.startswith(
    ("Body", "Scarf", "FibresBody", "FibresScarf"))],
    root, ORIGIN)
# his head turns and nods on his neck, inside the collar
NECK = Vector((0, 0.0, 1.08))
hang([o.name for o in SCENE.objects if o.type == "MESH" and o.name.startswith(
    ("Head", "Nose", "Eye", "Ear", "Whisker", "FibresHead"))], pivot("HeadPivot", NECK, root), NECK)
# each arm swings from the line of his shoulders; the candy has a pivot of its own so it can be thrown
for side in ("L", "R"):  # an arm each, so they can swing as he walks
    hang(["Arm" + side, "Hand" + side], pivot("ArmPivot" + side, SHOULDERS, root), SHOULDERS)
hang([o.name for o in SCENE.objects if o.type == "MESH" and o.name.startswith("Candy")],
     pivot("CandyPivot", CANDY_AT, root), CANDY_AT)
for side, sx in (("L", -1), ("R", 1)):
    at = Vector((0.09 * sx, 0.04, HIP_Z + 0.04))
    hang(["Leg" + side, "Foot" + side], pivot("LegPivot" + side, at, root), at)
hang(["Tail"], pivot("TailPivot", TAIL_BASE, root), TAIL_BASE)

# ---------------------------------------------------------------- save and export
for o in SCENE.objects:
    o.select_set(True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "mouse.blend"))
bpy.ops.export_scene.gltf(filepath=os.path.join(ROOT, "models", "mouse.glb"), export_format="GLB",
                          export_apply=True, export_yup=True)
print("BUILT", len(SCENE.objects), "parts")
