# Builds the kitchen counter decorated for Christmas, after art_src/concept_kitchen_counter.jpg.
#   blender -b --factory-startup --python tools/build_kitchen.py
# Saves tools/kitchen.blend (editable), models/kitchen.glb, and data/kitchen.json: where the mouse can walk
# (the counter's edges and a circle round every thing standing on it), in Godot's coordinates.
# Blender: Z up, the room is seen from -Y, the wall is at +Y. One unit is the cocoa mug's width (about 8 cm).
# The counter top is z = 0 and the cocoa mug (models/mouse.glb) stands at the origin.
import bpy, bmesh, math, os, sys, json, random
from mathutils import Vector, Matrix
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
bpy.ops.wm.read_factory_settings(use_empty=True)
SCENE = bpy.context.scene
sys.path.insert(0, HERE)
from shapes import *  # mat, finish, ellipsoid, lathe, torus, spline, tube, prism, COL, ROUGH, CLEAR

random.seed(12)
# The layout follows the concept picture: the mug stands left of the middle and a little toward the front, the
# window is right of the middle. Places were read off the picture (1 pixel of its 434 = 0.0507 units).
LEFT, RIGHT = -9.0, 14.5
FRONT, WALL = -2.9, 3.8
OBSTACLES = []  # (x, y, radius) in Blender's ground plane

COL.update({
    "cabinet": (0.30, 0.36, 0.44), "cabinet_dark": (0.22, 0.27, 0.34), "handle": (0.05, 0.05, 0.06),
    "window_frame": (0.90, 0.90, 0.88), "night": (0.03, 0.06, 0.16), "frost": (0.75, 0.85, 0.95),
    "pine": (0.07, 0.30, 0.13), "pine_dark": (0.04, 0.20, 0.09), "berry": (0.75, 0.04, 0.05),
    "wire": (0.03, 0.08, 0.04),
    "glow_red": (1.0, 0.10, 0.08), "glow_green": (0.15, 0.95, 0.25), "glow_blue": (0.15, 0.35, 1.0),
    "glow_yellow": (1.0, 0.80, 0.20), "glow_pink": (1.0, 0.30, 0.65), "glow_flame": (1.0, 0.72, 0.30),
    "ceramic": (0.74, 0.80, 0.84), "orange": (0.95, 0.47, 0.05), "orange_leaf": (0.15, 0.40, 0.12),
    "kettle": (0.72, 0.05, 0.05), "black": (0.04, 0.04, 0.04), "steel": (0.62, 0.64, 0.66),
    "pin_wood": (0.78, 0.60, 0.38), "flour": (0.95, 0.94, 0.90),
    "terracotta": (0.62, 0.30, 0.18), "soil": (0.15, 0.09, 0.05), "trunk": (0.30, 0.18, 0.09),
    "gingerbread": (0.52, 0.29, 0.12), "icing": (0.97, 0.96, 0.93), "gumdrop_red": (0.85, 0.08, 0.10),
    "gumdrop_green": (0.20, 0.70, 0.25), "gumdrop_yellow": (0.95, 0.80, 0.15),
    "plate": (0.93, 0.92, 0.88), "cookie": (0.72, 0.50, 0.26), "choc": (0.22, 0.11, 0.05),
    "glass": (0.80, 0.92, 0.95), "cane_white": (0.96, 0.95, 0.93), "cane_red": (0.82, 0.05, 0.07),
    "nut_red": (0.72, 0.06, 0.07), "nut_blue": (0.10, 0.18, 0.50), "nut_skin": (0.90, 0.68, 0.52),
    "nut_gold": (0.88, 0.68, 0.18), "nut_white": (0.95, 0.94, 0.90),
    "wrap_red": (0.75, 0.06, 0.08), "wrap_green": (0.10, 0.45, 0.20), "wrap_gold": (0.85, 0.66, 0.20),
    "ribbon_gold": (0.92, 0.76, 0.25), "ribbon_red": (0.80, 0.05, 0.08), "ribbon_white": (0.95, 0.95, 0.92),
    "wax": (0.93, 0.88, 0.74), "wick": (0.08, 0.06, 0.05),
})
ROUGH.update({"ceramic": 0.25, "kettle": 0.2, "steel": 0.25, "plate": 0.25, "glass": 0.05, "orange": 0.5,
              "night": 0.1, "handle": 0.3, "cane_white": 0.3, "cane_red": 0.3, "nut_red": 0.4, "nut_blue": 0.4,
              "black": 0.3, "nut_gold": 0.3, "wrap_red": 0.45, "wrap_green": 0.45, "wrap_gold": 0.3,
              "ribbon_gold": 0.3, "wax": 0.6, "cabinet": 0.55, "cabinet_dark": 0.55, "window_frame": 0.5,
              "glow_red": 0.2, "glow_green": 0.2, "glow_blue": 0.2, "glow_yellow": 0.2, "glow_pink": 0.2})
CLEAR.update({"glass": 0.22})
# the colours above are picked as they look on a screen; Blender wants them as light, so they are converted here
for _name in [k for k in COL if not k.startswith(("felt_", "fleece_", "bead_", "thread_", "fibre_"))]:
    COL[_name] = tuple(c ** 2.2 for c in COL[_name])


# ---------------------------------------------------------------- helpers of this script
def put(o, x, y, z=0.0, turn=0.0, scale=1.0):
    """Moves a part built at the origin to its place on the counter."""
    o.data.transform(Matrix.Translation((x, y, z)) @ Matrix.Rotation(math.radians(turn), 4, "Z")
                     @ Matrix.Scale(scale, 4))
    return o


def box(name, centre, size, material, turn=0.0):
    w, d, h = size
    poly = [(-w / 2, -d / 2), (w / 2, -d / 2), (w / 2, d / 2), (-w / 2, d / 2)]
    m = Matrix.Translation((centre[0], centre[1], centre[2] - h / 2)) @ Matrix.Rotation(math.radians(turn), 4, "Z")
    o = prism(name, poly, 0.0, h, material, None)
    o.data.transform(m)
    return o


def blocks(x, y, r):
    OBSTACLES.append((x, y, r))


def painted(name, pixels, rough=0.6):
    """A material that wears a picture (pixels: height x width x 3, 0..1)."""
    h, w = pixels.shape[:2]
    img = bpy.data.images.new(name, w, h)
    rgba = np.ones((h, w, 4), dtype=np.float32)
    rgba[:, :, :pixels.shape[2]] = pixels  # (a fourth channel is how clear it is)
    img.pixels.foreach_set(rgba.ravel())
    img.pack()
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    tex = m.node_tree.nodes.new("ShaderNodeTexImage")
    tex.image = img
    m.node_tree.links.new(tex.outputs["Color"], b.inputs["Base Color"])
    if pixels.shape[2] == 4:
        m.node_tree.links.new(tex.outputs["Alpha"], b.inputs["Alpha"])
        m.blend_method = "BLEND"
    b.inputs["Roughness"].default_value = rough
    return m


def sheet(name, corners, material, per_unit, origin=None):
    """One flat four-cornered face wearing a repeating picture. corners go round anticlockwise seen from outside;
    the picture runs along the first edge (u) and the last (v), per_unit repeats to a unit."""
    bm = bmesh.new()
    vs = [bm.verts.new(c) for c in corners]
    f = bm.faces.new(vs)
    uv = bm.loops.layers.uv.new("UVMap")
    a = Vector(corners[0])
    eu = (Vector(corners[1]) - a)
    ev = (Vector(corners[3]) - a)
    for loop in f.loops:
        d = loop.vert.co - (Vector(origin) if origin else a)  # (origin: where the picture starts, shared by pieces)
        loop[uv].uv = (d.dot(eu.normalized()) * per_unit[0], d.dot(ev.normalized()) * per_unit[1])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    SCENE.collection.objects.link(o)
    me.materials.append(material)
    return o


# ---------------------------------------------------------------- the pictures: butcher block and subway tile
def wood_picture():
    rng = np.random.default_rng(3)
    n = 512
    pix = np.zeros((n, n, 3), dtype=np.float32)
    strips = 8
    sh = n // strips
    base = np.array([0.50, 0.33, 0.20])
    for s in range(strips):
        x = 0
        shift = int(rng.integers(0, n))
        while x < n:
            length = int(rng.integers(150, 330))
            tone = base * (0.78 + 0.42 * rng.random()) * np.array([1.0, 0.97 + 0.06 * rng.random(), 0.92 + 0.16 * rng.random()])
            cols = (np.arange(x, min(x + length, n)) + shift) % n
            pix[s * sh:(s + 1) * sh, cols, :] = tone
            pix[s * sh:(s + 1) * sh, cols[0], :] = tone * 0.6  # the joint between two blocks
            x += length
        pix[s * sh, :, :] *= 0.62  # the glue line between strips
    grain = rng.random((n, 1)).repeat(n, axis=1) * 0.10 + rng.random((n, n)) * 0.05
    streak = np.sin(np.linspace(0, 60, n))[None, :] * 0.02
    pix *= (0.92 + grain + streak)[:, :, None]
    return np.clip(pix, 0, 1)


def tile_picture():
    n = 256
    pix = np.zeros((n, n, 3), dtype=np.float32)
    grout = np.array([0.52, 0.50, 0.47])
    tile = np.array([0.93, 0.92, 0.88])
    g = 5
    for row in range(2):
        y0 = row * (n // 2)
        off = 0 if row == 0 else n // 2
        for yy in range(n // 2):
            for xx in range(n):
                tx = (xx + off) % n
                edge = min(tx, n - 1 - tx, yy * 2, (n // 2 - 1 - yy) * 2)
                if tx < g or yy < g:
                    pix[y0 + yy, xx] = grout
                else:
                    pix[y0 + yy, xx] = tile * (0.90 + 0.10 * min(edge / 26.0, 1.0))
    return pix


def frost_picture():
    """One window pane: a clear dark night in the middle, frost grown thick in from the frame, ragged at its edge."""
    rng = np.random.default_rng(8)
    n = 256
    yy, xx = np.mgrid[0:n, 0:n] / (n - 1.0)
    edge = np.minimum(np.minimum(xx, 1 - xx), np.minimum(yy, 1 - yy))  # 0 at the frame, 0.5 in the middle
    noise = np.zeros((n, n))
    for cells, amp in ((4, 0.5), (8, 0.3), (16, 0.2), (32, 0.12), (64, 0.08)):
        g = rng.random((cells + 1, cells + 1))
        idx = np.linspace(0, cells, n)
        i0 = np.floor(idx).astype(int).clip(0, cells - 1)
        f = idx - i0
        f = f * f * (3 - 2 * f)
        rows = g[i0, :] * (1 - f)[:, None] + g[i0 + 1, :] * f[:, None]
        noise += amp * (rows[:, i0] * (1 - f)[None, :] + rows[:, i0 + 1] * f[None, :])
    noise /= 1.2
    frost = np.clip((0.27 - edge + (noise - 0.5) * 0.40) / 0.14, 0, 1)
    frost = frost * frost * (3 - 2 * frost)
    thin = np.clip(noise - 0.5, 0, 1) * 0.35  # a faint bloom over the clear middle
    cover = np.clip(frost * (0.72 + 0.28 * noise) + thin, 0, 1)
    sparkle = (rng.random((n, n)) > 0.988) * frost * 0.25
    night = np.array([0.02, 0.05, 0.15])
    ice = np.array([0.78, 0.88, 0.97])
    pix = np.zeros((n, n, 4), dtype=np.float32)  # the ice, and how much of the glass it covers
    pix[:, :, :3] = ice[None, None, :] + sparkle[:, :, None]
    pix[:, :, 3] = 0.05 + 0.95 * cover
    return np.clip(pix, 0, 1)


def cane_picture():
    """Candy cane stripes: a broad red band and a thin one, slanting, repeating without a seam."""
    n = 64
    pix = np.ones((n, n, 3), dtype=np.float32) * np.array([0.96, 0.95, 0.93], dtype=np.float32)
    yy, xx = np.mgrid[0:n, 0:n]
    band = (xx + yy) % 32
    pix[band < 10] = (0.80, 0.04, 0.06)
    pix[(band >= 17) & (band < 20)] = (0.80, 0.04, 0.06)
    return pix


FROST = painted("window_frost", frost_picture(), rough=0.3)
painted("cane_stripes", cane_picture(), rough=0.3)


def striped_tube(name, points, radius, segs=10, wraps=1.3):
    """A tube that wears the candy cane picture: once round it, and wraps times to a unit of its length."""
    pts = [Vector(p) for p in points]
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    tang = [(pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized() for i in range(len(pts))]
    n = tang[0].orthogonal().normalized()
    rings = []
    run = [0.0]
    for i, p in enumerate(pts):
        t = tang[i]
        n = (n - t * n.dot(t)).normalized()
        bn = t.cross(n)
        rings.append([bm.verts.new(p + (n * math.cos(math.tau * k / segs) + bn * math.sin(math.tau * k / segs)) * radius)
                      for k in range(segs)])
        if i:
            run.append(run[-1] + (p - pts[i - 1]).length)
    for i in range(len(rings) - 1):
        a, b = rings[i], rings[i + 1]
        for k in range(segs):
            l = (k + 1) % segs
            f = bm.faces.new((a[k], b[k], b[l], a[l]))
            for loop, (uu, vv) in zip(f.loops, ((k, run[i]), (k, run[i + 1]), (k + 1, run[i + 1]), (k + 1, run[i]))):
                loop[uv].uv = (uu / segs, vv * wraps)
    for ring, centre, v, flip in ((rings[0], pts[0] - tang[0] * radius * 0.7, run[0], False),
                                  (rings[-1], pts[-1] + tang[-1] * radius * 0.7, run[-1], True)):
        c = bm.verts.new(centre)
        for k in range(segs):
            l = (k + 1) % segs
            f = bm.faces.new((c, ring[l], ring[k]) if flip else (c, ring[k], ring[l]))
            for loop in f.loops:
                loop[uv].uv = (0.5, v * wraps)
    return finish(name, bm, "cane_stripes")


WOOD = painted("counter_wood", wood_picture(), rough=0.45)
TILE = painted("wall_tile", tile_picture(), rough=0.3)

# ---------------------------------------------------------------- the room: counter, wall, cabinets, window
# the counter top (its picture: 4 units of wood to a repeat), its front edge, and a little beyond each end
sheet("CounterTop", [(LEFT - 3, FRONT, 0), (RIGHT + 3, FRONT, 0), (RIGHT + 3, WALL, 0), (LEFT - 3, WALL, 0)], WOOD,
      (0.25, 0.25))
sheet("CounterEdge", [(LEFT - 3, FRONT, -0.55), (RIGHT + 3, FRONT, -0.55), (RIGHT + 3, FRONT, 0), (LEFT - 3, FRONT, 0)],
      WOOD, (0.25, 0.25))
# lower cabinets under the counter, set back a little, with doors, drawers and handles
box("LowerCabinets", (0, FRONT + 0.35 + 3.0, -0.55 - 6.0), (RIGHT - LEFT + 6, 6.0, 12.0), "cabinet_dark")
x = LEFT - 2.6
door = 0
while x < RIGHT + 2.0:
    w = 3.6
    if door % 3 == 1:
        box("Drawer%d" % door, (x + w / 2, FRONT + 0.30, -1.6), (w - 0.25, 0.12, 1.5), "cabinet")
        box("DrawerPull%d" % door, (x + w / 2, FRONT + 0.20, -1.6), (1.3, 0.10, 0.14), "handle")
        box("Door%d" % door, (x + w / 2, FRONT + 0.30, -6.6), (w - 0.25, 0.12, 8.0), "cabinet")
        box("DoorPull%d" % door, (x + 0.55, FRONT + 0.20, -3.6), (0.14, 0.10, 1.3), "handle")
    else:
        box("Door%d" % door, (x + w / 2, FRONT + 0.30, -5.7), (w - 0.25, 0.12, 9.9), "cabinet")
        box("DoorPull%d" % door, (x + (w - 0.55 if door % 2 else 0.55), FRONT + 0.20, -2.0), (0.14, 0.10, 1.3), "handle")
    x += w
    door += 1
# upper cabinets either side of the window
WIN_L, WIN_R, WIN_B, WIN_T = 3.1, 8.0, 2.3, 7.3
# the tiled wall, in four pieces round the window's opening (one picture across them all)
for nm, (x0, x1, z0, z1) in (("WallLeft", (LEFT - 3, WIN_L, 0, 7.6)), ("WallRight", (WIN_R, RIGHT + 3, 0, 7.6)),
                             ("WallBelow", (WIN_L, WIN_R, 0, WIN_B)), ("WallAbove", (WIN_L, WIN_R, WIN_T, 7.6))):
    sheet(nm, [(x0, WALL, z0), (x1, WALL, z0), (x1, WALL, z1), (x0, WALL, z1)], TILE, (1 / 1.9, 1 / 1.9),
          origin=(LEFT - 3, WALL, 0))
for nm, x0, x1 in (("UpperLeft", LEFT - 3, WIN_L - 0.9), ("UpperRight", WIN_R + 0.9, RIGHT + 3)):
    box(nm, ((x0 + x1) / 2, WALL - 1.3, 7.6 + 3.0), (x1 - x0, 2.6, 6.0), "cabinet")
    n = max(1, round((x1 - x0) / 3.4))
    for i in range(n):
        cx = x0 + (i + 0.5) * (x1 - x0) / n
        box("%sDoor%d" % (nm, i), (cx, WALL - 2.64, 7.6 + 3.1), ((x1 - x0) / n - 0.25, 0.1, 5.4), "cabinet_dark")
        box("%sPull%d" % (nm, i), (cx + (x1 - x0) / n / 2 - 0.5, WALL - 2.72, 8.4), (0.14, 0.1, 1.0), "handle")
box("WallAboveWindow", ((WIN_L + WIN_R) / 2, WALL + 0.2, 7.6 + 3.0), (WIN_R - WIN_L + 1.8, 0.4, 6.0), "window_frame")
# the window: a frosty night behind a white frame with one upright and one cross bar
WMX, WMZ = (WIN_L + WIN_R) / 2, (WIN_B + WIN_T) / 2
for pi_, (x0, x1, z0, z1) in enumerate(((WIN_L, WMX, WIN_B, WMZ), (WMX, WIN_R, WIN_B, WMZ), (WIN_L, WMX, WMZ, WIN_T),
                                         (WMX, WIN_R, WMZ, WIN_T))):
    # each pane wears the frost picture whole
    sheet("WindowPane%d" % pi_, [(x0, WALL - 0.06, z0), (x1, WALL - 0.06, z0), (x1, WALL - 0.06, z1), (x0, WALL - 0.06, z1)],
          FROST, (1 / (x1 - x0), 1 / (z1 - z0)))
for nm, c, s in (("FrameL", (WIN_L, WALL - 0.15, (WIN_B + WIN_T) / 2), (0.36, 0.3, WIN_T - WIN_B + 0.36)),
                 ("FrameR", (WIN_R, WALL - 0.15, (WIN_B + WIN_T) / 2), (0.36, 0.3, WIN_T - WIN_B + 0.36)),
                 ("FrameT", ((WIN_L + WIN_R) / 2, WALL - 0.15, WIN_T), (WIN_R - WIN_L + 0.36, 0.3, 0.36)),
                 ("FrameUp", ((WIN_L + WIN_R) / 2, WALL - 0.12, (WIN_B + WIN_T) / 2), (0.16, 0.2, WIN_T - WIN_B)),
                 ("FrameAcross", ((WIN_L + WIN_R) / 2, WALL - 0.12, (WIN_B + WIN_T) / 2), (WIN_R - WIN_L, 0.2, 0.16)),
                 ("Sill", ((WIN_L + WIN_R) / 2, WALL - 0.35, WIN_B - 0.1), (WIN_R - WIN_L + 0.9, 0.8, 0.22))):
    box("Window" + nm, c, s, "window_frame")

# ---------------------------------------------------------------- outside the window: a snowy night
# The window is a real opening: behind the glass is a short tunnel through the wall and, set back, a painted
# night (snowy hills, pines, a neighbour's lit window). The game blows snow through the gap between them.
def night_picture():
    n = 256
    yy, xx = np.mgrid[0:n, 0:n] / (n - 1.0)  # yy 0 at the bottom
    low = np.array([0.13, 0.18, 0.34])
    high = np.array([0.02, 0.03, 0.10])
    pix = low[None, None, :] * (1 - yy[:, :, None]) + high[None, None, :] * yy[:, :, None]
    far_hill = 0.42 + 0.05 * np.sin(xx * 5.0 + 1.0) + 0.02 * np.sin(xx * 13.0)
    pix[yy < far_hill] = (0.20, 0.26, 0.42)
    # a neighbour's house on the far hill, one window lit
    house = (np.abs(xx - 0.74) < 0.07) & (yy > 0.40) & (yy < 0.52)
    roof = (np.abs(xx - 0.74) < 0.09 * (1 - (yy - 0.52) / 0.07)) & (yy >= 0.52) & (yy < 0.59)
    pix[house] = (0.05, 0.06, 0.12)
    pix[roof] = (0.55, 0.62, 0.78)
    pix[(np.abs(xx - 0.72) < 0.014) & (np.abs(yy - 0.455) < 0.02)] = (1.0, 0.72, 0.30)
    for cx, base, tall, wide in ((0.14, 0.30, 0.50, 0.11), (0.33, 0.34, 0.36, 0.08), (0.93, 0.28, 0.56, 0.12), (0.55, 0.36, 0.26, 0.06)):
        up = (yy - base) / tall
        tier = (up * 4.0) % 1.0
        tree = (up > 0) & (up < 1) & (np.abs(xx - cx) < wide * (1 - up) * (1.25 - 0.5 * tier))
        pix[tree] = (0.03, 0.08, 0.09)
        pix[tree & (tier > 0.72)] = (0.50, 0.58, 0.74)  # snow lying on each tier
    near_hill = 0.26 + 0.05 * np.sin(xx * 6.0 + 2.5) + 0.02 * np.sin(xx * 19.0)
    snow = yy < near_hill
    pix[snow] = (np.array([0.42, 0.50, 0.68])[None, :] * (0.75 + 0.25 * (yy / 0.3))[snow][:, None])
    return np.clip(pix, 0, 1).astype(np.float32)


NIGHT = painted("night_outside", night_picture(), rough=1.0)
DEEP = 2.2
sheet("Outside", [(WIN_L - 2.6, WALL + DEEP, WIN_B - 2.2), (WIN_R + 2.6, WALL + DEEP, WIN_B - 2.2),
                  (WIN_R + 2.6, WALL + DEEP, WIN_T + 2.2), (WIN_L - 2.6, WALL + DEEP, WIN_T + 2.2)], NIGHT,
      (1 / (WIN_R - WIN_L + 5.2), 1 / (WIN_T - WIN_B + 4.4)))
for nm, c, s in (("JambL", (WIN_L - 0.1, WALL + 0.45, WMZ), (0.2, 0.9, WIN_T - WIN_B + 0.4)),
                 ("JambR", (WIN_R + 0.1, WALL + 0.45, WMZ), (0.2, 0.9, WIN_T - WIN_B + 0.4)),
                 ("JambT", (WMX, WALL + 0.45, WIN_T + 0.1), (WIN_R - WIN_L, 0.9, 0.2)),
                 ("JambB", (WMX, WALL + 0.45, WIN_B - 0.1), (WIN_R - WIN_L, 0.9, 0.2))):
    box("Window" + nm, c, s, "window_frame")
ellipsoid("SnowOnSill", (WMX, WALL + 0.35, WIN_B + 0.02), ((WIN_R - WIN_L) / 2, 0.4, 0.22), "icing", subsurf=0)


# ---------------------------------------------------------------- detail pictures for the game's materials
# Grey pictures that repeat without a seam, written to textures/. The game lays them over every plain-coloured
# thing (scripts/main.gd, DETAIL) so that nothing is flat: paper, felt, glaze, sugar, wood grain, and dots and
# stripes for the wrapping paper. *_n are the same surfaces as bumps.
def wrap_noise(rng, n, cells_y, cells_x):
    g = rng.random((cells_y, cells_x))
    iy = np.linspace(0, cells_y, n, endpoint=False)
    ix = np.linspace(0, cells_x, n, endpoint=False)
    y0 = np.floor(iy).astype(int)
    x0 = np.floor(ix).astype(int)
    fy = iy - y0
    fx = ix - x0
    fy = fy * fy * (3 - 2 * fy)
    fx = fx * fx * (3 - 2 * fx)
    y1 = (y0 + 1) % cells_y
    x1 = (x0 + 1) % cells_x
    top = g[y0][:, x0] * (1 - fx)[None, :] + g[y0][:, x1] * fx[None, :]
    bot = g[y1][:, x0] * (1 - fx)[None, :] + g[y1][:, x1] * fx[None, :]
    return top * (1 - fy)[:, None] + bot * fy[:, None]


def save_grey(name, grey):
    n = grey.shape[0]
    img = bpy.data.images.new("detail_" + name, n, n)
    rgba = np.ones((n, n, 4), dtype=np.float32)
    rgba[:, :, :3] = np.clip(grey, 0, 1)[:, :, None]
    img.pixels.foreach_set(rgba.ravel())
    img.filepath_raw = os.path.join(ROOT, "textures", name + ".png")
    img.file_format = "PNG"
    img.save()


def save_bumps(name, height, strength):
    n = height.shape[0]
    dx = (np.roll(height, -1, axis=1) - np.roll(height, 1, axis=1)) * strength
    dy = (np.roll(height, -1, axis=0) - np.roll(height, 1, axis=0)) * strength
    length = np.sqrt(dx * dx + dy * dy + 1.0)
    img = bpy.data.images.new("detail_" + name, n, n)
    img.colorspace_settings.name = "Non-Color"
    rgba = np.ones((n, n, 4), dtype=np.float32)
    rgba[:, :, 0] = -dx / length * 0.5 + 0.5
    rgba[:, :, 1] = -dy / length * 0.5 + 0.5
    rgba[:, :, 2] = 1.0 / length * 0.5 + 0.5
    img.pixels.foreach_set(rgba.ravel())
    img.filepath_raw = os.path.join(ROOT, "textures", name + ".png")
    img.file_format = "PNG"
    img.save()


def detail_pictures():
    os.makedirs(os.path.join(ROOT, "textures"), exist_ok=True)
    rng = np.random.default_rng(21)
    n = 256
    yy, xx = np.mgrid[0:n, 0:n] / float(n)
    blotch = wrap_noise(rng, n, 4, 4) * 0.5 + wrap_noise(rng, n, 9, 9) * 0.3 + wrap_noise(rng, n, 20, 20) * 0.2
    grit = wrap_noise(rng, n, 128, 128)
    linen = wrap_noise(rng, n, 128, 10) * 0.5 + wrap_noise(rng, n, 10, 128) * 0.5
    fibres = wrap_noise(rng, n, 96, 20) * 0.35 + wrap_noise(rng, n, 20, 96) * 0.35 + wrap_noise(rng, n, 64, 64) * 0.3
    streaks = wrap_noise(rng, n, 96, 3) * 0.6 + wrap_noise(rng, n, 160, 6) * 0.4
    # painted paper: soft blotches of wash, a little grit, the weave of the sheet
    paper_h = blotch * 0.5 + grit * 0.25 + linen * 0.25
    save_grey("paper", 0.52 + 0.48 * (blotch * 0.55 + grit * 0.2 + linen * 0.25))
    save_bumps("paper_n", paper_h, 2.2)
    # felt: matted fibres
    save_grey("felt", 0.48 + 0.52 * (fibres * 0.75 + blotch * 0.25))
    save_bumps("felt_n", fibres, 4.0)
    # glaze: nearly even, with pooling and a few kiln specks
    glaze = 0.86 + 0.14 * blotch
    glaze[rng.random((n, n)) > 0.996] = 0.6
    save_grey("glaze", glaze)
    # sugar: bright grains
    sugar = 0.78 + 0.14 * grit + 0.08 * blotch
    sugar[rng.random((n, n)) > 0.97] = 1.0
    save_grey("sugar", sugar)
    # wood grain: long streaks
    save_grey("grain", 0.66 + 0.34 * (streaks * 0.8 + grit * 0.2))
    # wrapping paper: dots in staggered rows, and slanting stripes, both on a paper ground
    ground = 0.60 + 0.08 * blotch
    dots = ground.copy()
    for row in range(4):
        for col in range(4):
            cx = (col + 0.5 + 0.5 * (row % 2)) / 4.0
            cy = (row + 0.5) / 4.0
            ddx = np.abs(xx - cx)
            ddx = np.minimum(ddx, 1 - ddx)
            ddy = np.abs(yy - cy)
            ddy = np.minimum(ddy, 1 - ddy)
            dots[ddx * ddx + ddy * ddy < 0.055 ** 2] = 1.0
    save_grey("dots", dots)
    stripes = ground.copy()
    stripes[((xx + yy) * 6.0) % 1.0 < 0.38] = 1.0
    save_grey("stripes", stripes)
    # how much of each window pane the frost covers (the game makes the panes see-through from this)
    save_grey("frost_cover", frost_picture()[:, :, 3])


detail_pictures()

# ---------------------------------------------------------------- the garland and its lights, hung in swags
HOOKS = [LEFT - 2.5, -7.9, -4.3, -0.7, WIN_L - 0.5, WIN_R + 0.5, 11.6, RIGHT + 2.5]
HOOK_Z = [5.7, 5.7, 5.7, 5.7, 5.9, 5.9, 5.7, 5.7]
bulb = 0
GLOWS = ["glow_red", "glow_green", "glow_blue", "glow_yellow", "glow_pink"]
LAMPS = []  # where the game puts a real light: (name, colour name, place)
for s in range(len(HOOKS) - 1):
    over_window = HOOKS[s] > WIN_L - 1 and HOOKS[s + 1] < WIN_R + 1
    if over_window:
        continue  # the garland stops either side of the window
    x0, x1 = HOOKS[s], HOOKS[s + 1]
    sag = 0.16 * (x1 - x0)
    line = []
    for i in range(25):
        t = i / 24
        line.append(Vector((x0 + (x1 - x0) * t, WALL - 0.32, HOOK_Z[s] + (HOOK_Z[s + 1] - HOOK_Z[s]) * t
                            - sag * 4 * t * (1 - t))))
    tube("GarlandWire%d" % s, line, 0.05, "wire", segs=5)
    # the pine: bristly lumps along the swag, two greens
    for g, mat_name in ((0, "pine"), (1, "pine_dark")):
        bm = bmesh.new()
        for i in range(len(line) * 3):
            p = line[0].lerp(line[-1], 0)  # placeholder, replaced below
            t = (i + 0.5 * g) / (len(line) * 3)
            k = min(int(t * 24), 23)
            p = line[k].lerp(line[k + 1], t * 24 - k)
            tip = Vector((random.uniform(-1, 1), random.uniform(-0.9, 0.2), random.uniform(-1, 0.6))).normalized()
            base = p + Vector((0, -0.05, 0))
            length = random.uniform(0.35, 0.6)
            side = tip.orthogonal().normalized() * 0.11
            side2 = tip.cross(side).normalized() * 0.11
            v = [bm.verts.new(base + side), bm.verts.new(base + side2), bm.verts.new(base - side), bm.verts.new(base - side2),
                 bm.verts.new(base + tip * length)]
            for a in range(4):
                bm.faces.new((v[a], v[(a + 1) % 4], v[4]))
            bm.faces.new((v[3], v[2], v[1], v[0]))
        finish("Garland%d_%d" % (s, g), bm, mat_name, smooth=False)
    # berries in the pine, and a big coloured bulb hanging under every few points
    for i in range(2, 24, 3):
        p = line[i]
        ellipsoid("Berry%d_%d" % (s, i), p + Vector((random.uniform(-0.15, 0.15), -0.3, random.uniform(-0.1, 0.2))),
                  (0.13, 0.13, 0.13), "berry", subsurf=0)
    for i in range(1, 24, 3):
        p = line[i] + Vector((0, -0.22, -0.42))
        colour = GLOWS[bulb % len(GLOWS)]
        tube("BulbCap%d" % bulb, [p + Vector((0, 0, 0.30)), p + Vector((0, 0, 0.52))], 0.09, "wire", segs=6)
        ellipsoid("Bulb%d" % bulb, p, (0.17, 0.17, 0.32), colour, subsurf=0)
        if bulb % 8 == 3:
            LAMPS.append(("Lamp_%s_%d" % (colour, bulb), p + Vector((0, -0.4, 0))))
        bulb += 1

# ---------------------------------------------------------------- the things on the counter, left to right
# a bowl of oranges
X, Y = -6.0, 2.0
put(lathe("Bowl", [(0, 0.12), (0.7, 0.10), (1.25, 0.45), (1.5, 1.0), (1.42, 1.02), (1.15, 0.52), (0.6, 0.22), (0, 0.22)],
          "ceramic", segs=40), X, Y)
for i, (ox, oy, oz) in enumerate(((-0.5, -0.3, 0.75), (0.5, -0.35, 0.78), (0.05, 0.5, 0.76), (0.0, -0.02, 1.35), (-0.75, 0.45, 0.8))):
    ellipsoid("Orange%d" % i, (X + ox, Y + oy, oz), (0.5, 0.5, 0.47), "orange", subsurf=0)
ellipsoid("OrangeLeaf", (X + 0.12, Y - 0.05, 1.83), (0.22, 0.10, 0.03), "orange_leaf", subsurf=0)
blocks(X, Y, 1.5)

# a red kettle
X, Y = -3.2, 2.2
put(lathe("Kettle", [(0, 0), (1.15, 0), (1.3, 0.15), (1.28, 0.9), (1.0, 1.75), (0.55, 2.05), (0, 2.1)], "kettle", segs=40), X, Y)
put(lathe("KettleLid", [(0, 2.05), (0.5, 2.05), (0.45, 2.2), (0.16, 2.26), (0.2, 2.5), (0, 2.55)], "black", segs=24), X, Y)
tube("KettleSpout", spline([(X - 1.05, Y - 0.2, 0.9), (X - 1.6, Y - 0.35, 1.3), (X - 1.95, Y - 0.45, 1.95)]), 0.2, "kettle")
tube("KettleHandle", spline([(X - 0.75, Y, 1.95), (X - 0.6, Y, 2.9), (X, Y, 3.2), (X + 0.6, Y, 2.9), (X + 0.75, Y, 1.95)]),
     0.1, "black")
blocks(X, Y, 1.4)
blocks(X - 1.6, Y - 0.35, 0.5)

# a rolling pin on a dusting of flour
X, Y, TURN = -3.0, 0.1, 10.0
along = Vector((math.cos(math.radians(TURN)), math.sin(math.radians(TURN)), 0))
c = Vector((X, Y, 0.3))
tube("RollingPin", [c - along * 1.3, c + along * 1.3], 0.3, "pin_wood", segs=18)
tube("RollingPinGripA", [c - along * 1.35, c - along * 2.0], 0.13, "pin_wood", segs=10)
tube("RollingPinGripB", [c + along * 1.35, c + along * 2.0], 0.13, "pin_wood", segs=10)
for i in range(7):
    ellipsoid("Flour%d" % i, (X + random.uniform(-1.7, 1.7), Y + random.uniform(-1.0, 0.9), 0.012),
              (random.uniform(0.35, 0.9), random.uniform(0.3, 0.7), 0.012), "flour", subsurf=0)
for k in (-1.7, -0.85, 0.0, 0.85, 1.7):
    blocks(X + along.x * k, Y + along.y * k, 0.42)

# the cocoa mug itself is models/mouse.glb, at the origin
blocks(0, 0, 0.66)
blocks(0.68, 0, 0.2)

# a little Christmas tree in a pot
X, Y = 1.4, 2.4
put(lathe("TreePot", [(0, 0), (0.55, 0), (0.75, 0.9), (0.82, 0.9), (0.82, 1.05), (0.7, 1.05), (0, 1.0)], "terracotta", segs=28), X, Y)
put(lathe("TreeSoil", [(0, 0.9), (0.68, 0.9), (0.68, 1.0), (0, 1.02)], "soil", segs=20), X, Y)
tube("TreeTrunk", [(X, Y, 0.95), (X, Y, 1.5)], 0.13, "trunk")
tier_z = 1.35
for i, (r, h) in enumerate(((1.15, 1.2), (0.95, 1.1), (0.72, 1.0), (0.48, 0.9))):
    def frill(a, rr, zz, _r=r):
        return rr * (1.0 + (0.10 * math.sin(9 * a + i) if rr > _r * 0.5 else 0.0)), zz
    put(lathe("TreeTier%d" % i, [(0, tier_z), (r, tier_z + 0.02), (r * 0.55, tier_z + h * 0.55), (0, tier_z + h)],
              "pine" if i % 2 == 0 else "pine_dark", segs=36, mod=frill), X, Y)
    for b in range(5 - i):
        a = math.tau * (b / (5 - i)) + i * 0.9
        ellipsoid("Bauble%d_%d" % (i, b), (X + math.sin(a) * r * 0.86, Y - math.cos(a) * r * 0.86, tier_z + 0.12),
                  (0.12, 0.12, 0.12), GLOWS[(b + i) % len(GLOWS)], subsurf=0)
    tier_z += h * 0.62
TREE_TOP = tier_z + 0.42
star = []
for i in range(10):
    a = math.tau * i / 10 + math.pi / 2
    rr = 0.3 if i % 2 == 0 else 0.13
    star.append((math.cos(a) * rr, math.sin(a) * rr))
prism("TreeStar", star, -0.05, 0.05, "glow_yellow",
      Matrix.Translation((X, Y, TREE_TOP + 0.12)) @ Matrix.Rotation(math.radians(90), 4, "X"))
LAMPS.append(("Lamp_glow_yellow_star", Vector((X, Y - 0.6, TREE_TOP))))
blocks(X, Y, 0.85)  # (only the pot: he is short enough to walk under the branches)

# a gingerbread house
X, Y, TURN = 3.65, 0.9, -12.0
GM = Matrix.Translation((X, Y, 0)) @ Matrix.Rotation(math.radians(TURN), 4, "Z")
HW, HD, HH, ROOF = 1.0, 0.8, 1.15, 0.95


def house(name, o):
    o.data.transform(GM @ o.matrix_world)  # (a prism keeps its placing on the object: fold it into the mesh)
    o.matrix_world = Matrix.Identity(4)
    return o


house("a", box("GingerWalls", (0, 0, HH / 2), (HW * 2, HD * 2, HH), "gingerbread"))
gable = [(-HW, 0), (HW, 0), (0, ROOF)]
house("b", prism("GingerGable", gable, -HD, HD, "gingerbread",
                 Matrix.Translation((0, 0, HH)) @ Matrix.Rotation(math.radians(90), 4, "X")))
slope = math.atan2(ROOF, HW)
for sx in (-1, 1):
    m = (Matrix.Translation((sx * HW * 0.5, 0, HH + ROOF * 0.5 + 0.06)) @ Matrix.Rotation(sx * slope, 4, "Y"))
    o = prism("GingerRoof%d" % sx, [(-0.8, -HD - 0.18), (0.8, -HD - 0.18), (0.8, HD + 0.18), (-0.8, HD + 0.18)],
              0.0, 0.12, "icing", m)
    house("c", o)
    for r in range(3):  # gumdrops in rows down each slope
        for cidx in range(3):
            p = m @ Vector((-0.5 + r * 0.5, -0.55 + cidx * 0.55, 0.12))
            house("d", ellipsoid("Gumdrop%d_%d_%d" % (sx, r, cidx), p, (0.11, 0.11, 0.1),
                                 ("gumdrop_red", "gumdrop_green", "gumdrop_yellow")[(r + cidx) % 3], subsurf=0))
house("e", tube("GingerRidge", [(0, -HD - 0.2, HH + ROOF + 0.1), (0, HD + 0.2, HH + ROOF + 0.1)], 0.1, "icing", segs=8))
house("f", box("GingerDoor", (0, -HD - 0.02, 0.36), (0.42, 0.06, 0.72), "choc"))
house("g", tube("GingerDoorIcing", spline([(-0.25, -HD - 0.05, 0.0), (-0.25, -HD - 0.05, 0.6), (0, -HD - 0.05, 0.82),
                                             (0.25, -HD - 0.05, 0.6), (0.25, -HD - 0.05, 0.0)]), 0.035, "icing", segs=6))
for sx in (-1, 1):
    house("h", torus("GingerWindow%d" % sx, 0.16, 0.035, "icing",
                     Matrix.Translation((sx * 0.62, -HD - 0.03, 0.72)) @ Matrix.Rotation(math.radians(90), 4, "X"),
                     segs_R=16, segs_r=6))
    house("i", ellipsoid("GingerPane%d" % sx, (sx * 0.62, -HD - 0.01, 0.72), (0.14, 0.02, 0.14), "glow_yellow", subsurf=0))
house("j", tube("GingerSnow", [(-HW - 0.05, -HD - 0.05, 0.03), (HW + 0.05, -HD - 0.05, 0.03), (HW + 0.05, HD + 0.05, 0.03),
                               (-HW - 0.05, HD + 0.05, 0.03), (-HW - 0.05, -HD - 0.05, 0.03)], 0.06, "icing", segs=6))
blocks(X, Y, 1.0)

# a plate of cookies
X, Y = 5.6, -1.3
put(lathe("Plate", [(0, 0), (0.7, 0), (1.15, 0.12), (1.15, 0.17), (0.7, 0.07), (0, 0.07)], "plate", segs=40), X, Y)
for i, (ox, oy, oz, kind) in enumerate(((-0.45, 0.2, 0.1, 0), (0.4, 0.3, 0.1, 1), (0.05, -0.45, 0.1, 0), (0.0, 0.05, 0.2, 1))):
    put(lathe("Cookie%d" % i, [(0, 0), (0.36, 0), (0.4, 0.04), (0.36, 0.09), (0, 0.1)], "cookie", segs=18), X + ox, Y + oy, oz)
    for k in range(5):
        a = math.tau * k / 5 + i
        ellipsoid("CookieDot%d_%d" % (i, k), (X + ox + math.cos(a) * 0.2, Y + oy + math.sin(a) * 0.2, oz + 0.1),
                  (0.06, 0.06, 0.03), "choc" if kind == 0 else "icing", subsurf=0)
blocks(X, Y, 0.78)  # (he may tread on its rim)

# a glass jar of candy canes
X, Y = 7.25, 1.0
put(lathe("JarGlass", [(0, 0), (0.62, 0), (0.7, 0.1), (0.7, 1.7), (0.55, 1.9), (0.55, 2.0), (0.62, 2.0), (0.62, 2.08),
                       (0.5, 2.08), (0.5, 1.88), (0.64, 1.68), (0.64, 0.12), (0, 0.08)], "glass", segs=32), X, Y)
for i in range(5):
    a = math.tau * i / 5 + 0.4
    bx, by = X + math.cos(a) * 0.3, Y + math.sin(a) * 0.3
    lean = Vector((math.cos(a) * 0.25, math.sin(a) * 0.25, 0))
    hook = Vector((math.cos(a + 1.3), math.sin(a + 1.3), 0))
    top = Vector((bx, by, 0.1)) + lean + Vector((0, 0, 2.4))
    path = spline([Vector((bx, by, 0.1)), top, top + hook * 0.2 + Vector((0, 0, 0.22)), top + hook * 0.45 + Vector((0, 0, 0.1)),
                   top + hook * 0.5 + Vector((0, 0, -0.2))], per=6)
    striped_tube("Cane%d" % i, path, 0.085)
blocks(X, Y, 0.8)

# a nutcracker soldier
X, Y = 9.3, 1.2
NM = Matrix.Translation((X, Y, 0)) @ Matrix.Rotation(math.radians(-20), 4, "Z")


def nut(o):
    o.data.transform(NM @ o.matrix_world)
    o.matrix_world = Matrix.Identity(4)
    return o


nut(box("NutBase", (0, 0, 0.08), (0.9, 0.7, 0.16), "nut_gold"))
for sx in (-1, 1):
    nut(box("NutBoot%d" % sx, (sx * 0.17, -0.03, 0.3), (0.26, 0.36, 0.28), "black"))
    nut(tube("NutLeg%d" % sx, [(sx * 0.17, 0, 0.42), (sx * 0.17, 0, 1.05)], 0.12, "nut_blue"))
    nut(tube("NutArm%d" % sx, [(sx * 0.42, 0, 1.75), (sx * 0.44, 0, 1.15)], 0.1, "nut_red"))
    nut(ellipsoid("NutHand%d" % sx, (sx * 0.44, 0, 1.08), (0.1, 0.1, 0.1), "nut_skin", subsurf=0))
    nut(ellipsoid("NutShoulder%d" % sx, (sx * 0.42, 0, 1.8), (0.15, 0.13, 0.07), "nut_gold", subsurf=0))
nut(lathe("NutCoat", [(0, 1.0), (0.36, 1.0), (0.33, 1.85), (0, 1.9)], "nut_red", segs=20))
nut(box("NutBelt", (0, 0, 1.2), (0.76, 0.76, 0.1), "black"))
for k in range(3):
    nut(ellipsoid("NutButton%d" % k, (0, -0.34, 1.38 + k * 0.17), (0.045, 0.03, 0.045), "nut_gold", subsurf=0))
nut(lathe("NutHead", [(0, 1.88), (0.27, 1.9), (0.29, 2.3), (0, 2.34)], "nut_skin", segs=20))
nut(lathe("NutHat", [(0, 2.3), (0.31, 2.3), (0.31, 2.36), (0.27, 2.36), (0.25, 2.95), (0, 2.97)], "black", segs=20))
nut(box("NutHatBand", (0, -0.27, 2.5), (0.2, 0.05, 0.2), "nut_gold"))
nut(prism("NutBeard", [(-0.2, 0), (0.2, 0), (0.0, -0.36)], -0.03, 0.03, "nut_white",
          Matrix.Translation((0, -0.29, 2.02)) @ Matrix.Rotation(math.radians(90), 4, "X")))
nut(box("NutMoustache", (0, -0.29, 2.06), (0.36, 0.05, 0.07), "nut_white"))
for sx in (-1, 1):
    nut(ellipsoid("NutEye%d" % sx, (sx * 0.11, -0.275, 2.18), (0.035, 0.02, 0.045), "black", subsurf=0))
blocks(X, Y, 0.6)

# wrapped presents
PRESENTS = [((10.6, -0.3), (1.3, 1.0, 0.8), 12, "wrap_red", "ribbon_gold"),
            ((12.0, -0.7), (0.95, 0.95, 1.15), -18, "wrap_green", "ribbon_red"),
            ((11.1, -0.15), (0.7, 0.6, 0.45), 30, "wrap_gold", "ribbon_white")]
for i, ((px, py), (w, d, h), turn, wrap, ribbon) in enumerate(PRESENTS):
    z0 = 0.8 if i == 2 else 0.0  # the little one sits on the red one
    box("Present%d" % i, (px, py, z0 + h / 2), (w, d, h), wrap, turn)
    box("PresentRibbonA%d" % i, (px, py, z0 + h / 2 + 0.005), (w + 0.02, d * 0.16, h + 0.02), ribbon, turn)
    box("PresentRibbonB%d" % i, (px, py, z0 + h / 2 + 0.005), (w * 0.16, d + 0.02, h + 0.02), ribbon, turn)
    for sx in (-1, 1):
        torus("PresentBow%d_%d" % (i, sx), 0.13, 0.045, ribbon,
              Matrix.Translation((px, py, z0 + h + 0.1)) @ Matrix.Rotation(math.radians(turn), 4, "Z")
              @ Matrix.Translation((sx * 0.14, 0, 0)) @ Matrix.Rotation(math.radians(90), 4, "X"), segs_R=14, segs_r=6)
blocks(10.7, -0.3, 0.85)
blocks(12.0, -0.7, 0.75)

# a lit candle on a saucer, at the right end
X, Y = 13.2, 0.6
put(lathe("CandleSaucer", [(0, 0), (0.55, 0), (0.8, 0.12), (0.8, 0.17), (0.5, 0.07), (0, 0.07)], "ceramic", segs=28), X, Y)
put(lathe("Candle", [(0, 0.06), (0.36, 0.06), (0.36, 1.2), (0.3, 1.27), (0.12, 1.2), (0, 1.2)], "wax", segs=24), X, Y)
tube("CandleWick", [(X, Y, 1.2), (X, Y, 1.36)], 0.02, "wick", segs=5)
put(lathe("CandleFlame", [(0, 1.33), (0.09, 1.42), (0.07, 1.56), (0, 1.75)], "glow_flame", segs=12), X, Y)
LAMPS.append(("Lamp_glow_flame_candle", Vector((X, Y, 1.7))))
blocks(X, Y, 0.8)

# ---------------------------------------------------------------- lamps (empties the game hangs real lights on)
for name, p in LAMPS:
    e = bpy.data.objects.new(name, None)
    SCENE.collection.objects.link(e)
    e.location = p

# ---------------------------------------------------------------- save, export, and the walking data
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "kitchen.blend"))
bpy.ops.export_scene.gltf(filepath=os.path.join(ROOT, "models", "kitchen.glb"), export_format="GLB",
                          export_apply=True, export_yup=True)
os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
with open(os.path.join(ROOT, "data", "kitchen.json"), "w") as f:
    # Godot: x the same, z = -y
    json.dump({"left": LEFT + 0.4, "right": RIGHT - 0.4, "front": -(FRONT + 0.4), "back": -(WALL - 0.55),
               "obstacles": [[round(x, 3), round(-y, 3), round(r, 3)] for (x, y, r) in OBSTACLES],
               # the window, for the snow: its middle, its size, how far back the glass and the painted night are
               "window": {"x": WMX, "y": WMZ, "wide": WIN_R - WIN_L, "tall": WIN_T - WIN_B, "glass": -WALL,
                          "night": -(WALL + DEEP)}}, f, indent=1)
print("BUILT", len(SCENE.objects), "parts,", len(OBSTACLES), "obstacles")
