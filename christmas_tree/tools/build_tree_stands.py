# Builds what a Christmas tree stands in, and the little things the tree script falls back on:
#
#   blender -b --factory-startup --python christmas_tree/tools/build_tree_stands.py -- [folder for pictures]
#
# Writes tools/tree_stands.blend (editable), models/tree_stands.glb and textures/tree_stands.png, and with a
# folder also pictures of every model from the front, right, back, left, above and three-quarters.
#
# Every model is real size IN METRES FOR A TREE ONE METRE TALL (the script scales it to the tree), z up here
# (y up in Godot), standing on the floor at the origin with the trunk going down its middle:
#   pot           terracotta pot on a saucer, soil in it
#   bucket        galvanised bucket with ribs, ears and a dropped bail handle, pebbles in it
#   basket        wicker basket with a braided rim and two loop handles, a burlap liner gathered in it
#   metal_stand   the classic one: a green water bowl, four red strap legs up to a red ring, four eye bolts
#   plank_cross   two sawn planks nailed across each other, blocks under the upper one's ends
#   root_ball     a root ball wrapped in burlap, gathered at the trunk and tied with twine
#   skirt_felt    a red felt tree skirt with a cream blanket-stitched scalloped trim (radius 1; shape key "rise")
#   skirt_quilted a quilted patchwork skirt in wedges with a bound edge (radius 1; shape key "rise")
#   bauble        a plain glass ball with its cap and loop, hanging from the origin (a stand-in ornament, a berry)
#   star          a folded five-pointed star on a cone socket (a stand-in topper)
# and each again as <name>_lo, about a quarter of the triangles. One picture colours them all: sixteen squares
# (see CELLS). The skirts' shape key lifts the middle of the cloth up over a stand (1 = one radius high).
#
# Every closed piece is checked for inside-out faces: a ray from each face along its normal must leave the piece
# an even number of times; a face that does not is turned, and the check is run again (it must then find none).
import bpy
import math
import os
import sys

import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MODELS = os.path.join(ROOT, "models")
TEXTURES = os.path.join(ROOT, "textures")
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
SHEETS = args[0] if args else ""
os.makedirs(MODELS, exist_ok=True)
os.makedirs(TEXTURES, exist_ok=True)
TAU = math.tau

# ---------------------------------------------------------------------------------------------- the picture
N = 256          # pixels to a square
GRID = 4         # squares to a side
INSET = 5.0 / N  # how far inside its square a model's UVs stay (so the next square never bleeds in)
CELLS = ["terracotta", "soil", "galvanised", "pebbles",
         "wicker", "red_enamel", "green_enamel", "steel",
         "wood", "wood_end", "burlap", "twine",
         "felt", "quilt", "water", "pearl_gold"]
YY, XX = np.mgrid[0:N, 0:N] / float(N)   # y up: row 0 is the bottom of a square (v = 0)


def lerp(a, b, t):
    return a + (b - a) * t


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def noise(cx, cy, seed):
    """Smooth noise 0..1 that repeats at the square's edges, cx by cy lumps."""
    rs = np.random.RandomState(seed)
    lat = rs.rand(cy, cx)
    fx = XX * cx
    fy = YY * cy
    ix = np.floor(fx).astype(int)
    iy = np.floor(fy).astype(int)
    tx = fx - ix
    ty = fy - iy
    tx = tx * tx * (3 - 2 * tx)
    ty = ty * ty * (3 - 2 * ty)
    a = lat[iy % cy, ix % cx]
    b = lat[iy % cy, (ix + 1) % cx]
    c = lat[(iy + 1) % cy, ix % cx]
    d = lat[(iy + 1) % cy, (ix + 1) % cx]
    return lerp(lerp(a, b, tx), lerp(c, d, tx), ty)


def fbm(cx, cy, octaves, seed):
    total = np.zeros((N, N))
    weight = 0.0
    for o in range(octaves):
        total += noise(cx * 2 ** o, cy * 2 ** o, seed + o * 17) / 2 ** o
        weight += 1.0 / 2 ** o
    return total / weight


def voronoi(count, seed):
    """Nearest and second nearest of scattered points (repeating): (d1, d2, which, x to it, y to it)."""
    rs = np.random.RandomState(seed)
    pts = rs.rand(count, 2)
    d1 = np.full((N, N), 9.0)
    d2 = np.full((N, N), 9.0)
    which = np.zeros((N, N), dtype=int)
    ox = np.zeros((N, N))
    oy = np.zeros((N, N))
    for i, (px, py) in enumerate(pts):
        for sx in (-1, 0, 1):
            for sy in (-1, 0, 1):
                dx = XX - px - sx
                dy = YY - py - sy
                d = np.sqrt(dx * dx + dy * dy)
                nearer = d < d1
                d2 = np.where(nearer, d1, np.minimum(d2, d))
                which = np.where(nearer, i, which)
                ox = np.where(nearer, dx, ox)
                oy = np.where(nearer, dy, oy)
                d1 = np.where(nearer, d, d1)
    return d1, d2, which, ox, oy


def rgb(colour, shade=1.0):
    out = np.zeros((N, N, 3))
    for k in range(3):
        out[:, :, k] = colour[k] * shade
    return out


def mix(a, b, t):
    return a + (b - a) * t[:, :, None]


def paint_terracotta():
    t = fbm(4, 4, 4, 1)
    rings = 0.5 + 0.5 * np.sin(YY * TAU * 22 + fbm(2, 6, 2, 2) * 5.0)
    out = rgb((0.74, 0.36, 0.21), (0.80 + 0.34 * t) * (0.93 + 0.09 * rings))
    bloom = smoothstep(0.45, 0.05, YY) * fbm(6, 3, 3, 3) ** 1.6 * 1.4
    out = mix(out, rgb((0.86, 0.78, 0.68)), np.clip(bloom, 0, 0.6))
    out *= (1.0 - 0.25 * (fbm(48, 48, 1, 4) > 0.80))[:, :, None]
    out *= lerp(0.80, 1.0, smoothstep(0.0, 0.14, YY))[:, :, None]
    return out


def paint_soil():
    n = fbm(8, 8, 4, 5)
    out = rgb((0.17, 0.115, 0.08), 0.55 + 0.95 * n)
    crumbs = fbm(40, 40, 2, 6)
    out = mix(out, rgb((0.30, 0.21, 0.14)), (crumbs > 0.62) * 0.7)
    out = mix(out, rgb((0.05, 0.035, 0.03)), (crumbs < 0.34) * 0.8)
    bark = fbm(22, 22, 1, 7) > 0.86
    out = mix(out, rgb((0.42, 0.24, 0.12)), bark * 0.8)
    perlite = fbm(50, 50, 1, 8) > 0.93
    out = mix(out, rgb((0.82, 0.80, 0.74)), perlite * 0.85)
    return out


def paint_galvanised():
    d1, d2, which, ox, oy = voronoi(170, 9)
    rs = np.random.RandomState(10)
    tone = rs.rand(170)[which]
    way = rs.rand(170)[which] * TAU
    sheen = (ox * np.cos(way) + oy * np.sin(way)) * 0.7
    shade = 0.84 + 0.10 * tone + sheen
    out = rgb((0.66, 0.69, 0.73), shade)
    out[:, :, 2] *= 1.0 + 0.05 * tone
    out *= (0.90 + 0.14 * fbm(3, 3, 3, 11))[:, :, None]
    out *= (1.0 - 0.10 * (noise(2, 90, 12) > 0.80))[:, :, None]
    return out


def paint_pebbles():
    d1, d2, which, ox, oy = voronoi(30, 13)
    rs = np.random.RandomState(14)
    stones = np.array([(0.62, 0.60, 0.56), (0.48, 0.47, 0.46), (0.70, 0.62, 0.50), (0.56, 0.44, 0.36), (0.78, 0.76, 0.72),
                       (0.40, 0.42, 0.45)])
    out = stones[rs.randint(0, len(stones), 30)][which]
    out = out * (0.92 + 0.16 * rs.rand(30)[which])[:, :, None]
    dome = 1.0 - smoothstep(0.0, 0.16, d1) * 0.35 + (oy - ox) * 1.1
    out *= np.clip(dome, 0.5, 1.25)[:, :, None]
    out *= (0.90 + 0.2 * fbm(40, 40, 2, 15))[:, :, None]
    gap = 1.0 - smoothstep(0.0, 0.045, d2 - d1)
    out = mix(out, rgb((0.09, 0.08, 0.07)), gap * 0.9)
    return out


def paint_wicker():
    cols, rows = 8, 16
    gx = XX * cols
    gy = YY * rows
    fx = gx - np.floor(gx)
    fy = gy - np.floor(gy)
    over = (np.floor(gx) + np.floor(gy)) % 2 == 0
    across = np.sin(np.pi * fy) ** 0.55
    weaver = np.where(over, 0.55 + 0.45 * np.sin(np.pi * fx), 0.30 + 0.20 * np.abs(np.cos(np.pi * fx))) * across
    out = rgb((0.74, 0.54, 0.31), 0.25 + 0.95 * weaver)
    stake_in = np.abs(fx - 0.5) / 0.21
    stake = (~over) & (stake_in < 1.0)
    round_ = np.sqrt(np.clip(1.0 - stake_in ** 2, 0, 1))
    out = np.where(stake[:, :, None], rgb((0.66, 0.46, 0.25), 0.45 + 0.6 * round_), out)
    out *= (0.86 + 0.28 * noise(3, 64, 16))[:, :, None]
    out *= (0.92 + 0.16 * fbm(5, 5, 2, 17))[:, :, None]
    return out


def paint_enamel(colour, seed):
    out = rgb(colour, 0.88 + 0.2 * fbm(3, 3, 3, seed))
    gleam = np.exp(-((XX - 0.3) / 0.07) ** 2) * 0.22 + np.exp(-((XX - 0.78) / 0.03) ** 2) * 0.10
    out = mix(out, rgb((1.0, 0.96, 0.9)), gleam * (0.6 + 0.4 * noise(2, 5, seed + 3)))
    chips = (fbm(18, 18, 2, seed + 5) > 0.80) & (fbm(4, 4, 2, seed + 6) > 0.55)
    out = mix(out, rgb((0.20, 0.17, 0.16)), chips * 0.85)
    return out


def paint_steel():
    thread = 0.5 + 0.5 * np.sin(TAU * (YY * 3.0 + XX * 22.0))
    out = rgb((0.60, 0.61, 0.63), 0.62 + 0.42 * thread)
    out *= (0.88 + 0.2 * fbm(6, 6, 2, 21))[:, :, None]
    return out


def paint_wood():
    grain = fbm(2, 36, 3, 22)
    out = mix(rgb((0.56, 0.38, 0.21)), rgb((0.83, 0.65, 0.42)), grain)
    out *= (0.95 + 0.07 * np.sin(YY * 60.0 + fbm(3, 3, 2, 23) * 12.0))[:, :, None]
    for kx, ky, kr in ((0.28, 0.62, 0.05), (0.74, 0.25, 0.035)):
        d = np.sqrt(((XX - kx) / 1.9) ** 2 + (YY - ky) ** 2) / kr
        knot = smoothstep(1.0, 0.3, d)
        halo = (0.5 + 0.5 * np.sin(d * 9.0)) * smoothstep(3.2, 1.0, d) * 0.25
        out = mix(out, rgb((0.30, 0.18, 0.10)), np.clip(knot * 0.85 + halo, 0, 1))
    out *= (0.96 + 0.05 * np.sin((XX * 3.0 + YY) * TAU * 14.0))[:, :, None]   # saw marks
    out *= (0.92 + 0.14 * fbm(30, 6, 2, 24))[:, :, None]
    return out


def paint_wood_end():
    dx = XX - 0.5
    dy = YY - 0.36
    d = np.sqrt(dx * dx + dy * dy) + (fbm(4, 4, 2, 25) - 0.5) * 0.07
    rings = 0.5 + 0.5 * np.sin(d * TAU * 15.0)
    out = mix(rgb((0.52, 0.35, 0.20)), rgb((0.84, 0.68, 0.46)), rings * 0.7 + 0.15)
    ang = np.arctan2(dy, dx)
    crack = (np.abs(np.sin(ang * 3.0 + 0.6)) < 0.03) & (d > 0.06) & (d < 0.42 + 0.2 * noise(3, 3, 26))
    out = mix(out, rgb((0.20, 0.12, 0.07)), crack * 0.8)
    out *= (0.88 + 0.2 * fbm(40, 40, 2, 27))[:, :, None]
    return out


def paint_burlap():
    k = 26
    gx = XX * k + (noise(3, 26, 28) - 0.5) * 0.5
    gy = YY * k + (noise(26, 3, 29) - 0.5) * 0.5
    fx = gx - np.floor(gx)
    fy = gy - np.floor(gy)
    over = (np.floor(gx) + np.floor(gy)) % 2 == 0
    warp = np.sin(np.pi * fx) ** 0.7 * (0.7 + 0.3 * np.sin(np.pi * fy))
    weft = np.sin(np.pi * fy) ** 0.7 * (0.7 + 0.3 * np.sin(np.pi * fx))
    shade = np.where(over, warp, weft * 0.92)
    out = rgb((0.76, 0.62, 0.42), 0.34 + 0.76 * shade)
    out *= (0.80 + 0.36 * fbm(5, 5, 3, 30))[:, :, None]
    out *= (0.9 + 0.2 * noise(2, 26, 31))[:, :, None]
    return out


def paint_twine():
    twist = np.abs(np.sin(np.pi * (XX * 8.0 + YY * 3.0)))
    out = rgb((0.84, 0.71, 0.47), 0.50 + 0.55 * twist ** 0.7)
    out *= (0.88 + 0.24 * noise(60, 6, 32))[:, :, None]
    return out


def fuzz(seed, amount=1.0):
    return 1.0 + amount * ((fbm(52, 52, 2, seed) - 0.5) * 0.22 + (fbm(5, 5, 3, seed + 1) - 0.5) * 0.24)


def paint_felt():
    out = rgb((0.66, 0.075, 0.09), 1.0) * fuzz(33)[:, :, None]
    hairs = (noise(90, 14, 35) > 0.83) | (noise(14, 90, 36) > 0.85)
    out = mix(out, rgb((0.86, 0.30, 0.28)), hairs * 0.35)
    # a row of cream French knots and little stitched stars
    for i in range(4):
        cx = (i + 0.5) / 4.0
        d = np.sqrt((XX - cx) ** 2 + (YY - 0.60) ** 2)
        ang = np.arctan2(YY - 0.60, XX - cx)
        star = d < 0.018 + 0.030 * np.abs(np.cos(ang * 4.0)) ** 6
        out = mix(out, rgb((0.95, 0.90, 0.78)), star * 0.95)
        for kx in (-0.085, 0.085):
            knot = np.sqrt((XX - cx - kx) ** 2 + (YY - 0.66) ** 2) < 0.012
            out = mix(out, rgb((0.95, 0.82, 0.40)), knot * 0.95)
    # the trim: cream wool along the top of the square, blanket-stitched on in red
    trim = smoothstep(0.795, 0.805, YY)
    wool = rgb((0.94, 0.89, 0.77), 1.0) * fuzz(37, 0.8)[:, :, None]
    out = mix(out, wool, trim)
    sx = XX * 8.0 - np.floor(XX * 8.0)
    stitch = ((np.abs(sx - 0.5) < 0.07) & (YY > 0.80) & (YY < 0.925)) | (np.abs(YY - 0.925) < 0.008)
    out = mix(out, rgb((0.62, 0.07, 0.08)), stitch * 0.95)
    out = mix(out, rgb((0.35, 0.03, 0.05)), (np.abs(YY - 0.80) < 0.006) * 0.6)
    return out


def paint_quilt():
    red, green, cream, gold = (0.68, 0.09, 0.10), (0.10, 0.36, 0.18), (0.94, 0.89, 0.76), (0.86, 0.66, 0.26)
    bounds = [0.0, 0.22, 0.44, 0.66, 0.88, 1.0]

    def dots(base, dot, n):
        fx = XX * n * 2 - np.floor(XX * n * 2)
        fy = YY * n * 2 - np.floor(YY * n * 2)
        return mix(rgb(base), rgb(dot), (np.sqrt((fx - 0.5) ** 2 + (fy - 0.5) ** 2) < 0.2) * 1.0)

    def stripes(base, other, n):
        return mix(rgb(base), rgb(other), ((XX * n + YY * n) % 1.0 < 0.35) * 1.0)

    def plaid(base, other, n):
        a = (XX * n) % 1.0 < 0.3
        b = (YY * n) % 1.0 < 0.3
        return mix(mix(rgb(base), rgb(other), a * 0.6), rgb(other), b * 0.6)

    fabrics = [
        [dots(red, cream, 5), plaid(cream, green, 6), stripes(green, cream, 8), dots(cream, red, 6), rgb(green)],
        [plaid(green, gold, 5), dots(cream, green, 6), stripes(red, cream, 7), plaid(red, cream, 6), rgb(red)],
    ]
    out = np.zeros((N, N, 3))
    puff = np.ones((N, N))
    seam = np.zeros((N, N))
    stitch = np.zeros((N, N))
    for w in range(2):
        in_w = (XX >= w * 0.5) & (XX < (w + 1) * 0.5)
        fx = (XX - w * 0.5) / 0.5
        for b in range(5):
            in_b = in_w & (YY >= bounds[b]) & (YY < bounds[b + 1])
            out = np.where(in_b[:, :, None], fabrics[w][b], out)
            fy = (YY - bounds[b]) / (bounds[b + 1] - bounds[b])
            bulge = (np.sin(np.pi * np.clip(fx, 0, 1)) ** 0.35) * (np.sin(np.pi * np.clip(fy, 0, 1)) ** 0.35)
            puff = np.where(in_b, 0.66 + 0.40 * bulge, puff)
            edge = np.minimum(np.minimum(fx, 1 - fx) * 0.5, np.minimum(fy, 1 - fy) * (bounds[b + 1] - bounds[b]))
            seam = np.where(in_b, 1.0 - smoothstep(0.0, 0.012, edge), seam)
            dash = ((XX * 40.0) % 1.0 < 0.6) & ((YY * 40.0) % 1.0 < 0.6)
            stitch = np.where(in_b, (np.abs(edge - 0.028) < 0.006) & dash, stitch)
    out *= (puff * fuzz(38, 0.7))[:, :, None]
    out = mix(out, rgb((0.97, 0.94, 0.84)), stitch * 0.9)
    out = mix(out, rgb((0.10, 0.06, 0.05)), seam * 0.75)
    return out


def paint_water():
    out = rgb((0.035, 0.085, 0.075), 0.8 + 0.5 * fbm(3, 3, 3, 40))
    glint = smoothstep(0.62, 0.80, fbm(5, 2, 3, 41))
    out = mix(out, rgb((0.45, 0.58, 0.55)), glint * 0.5)
    needles = (noise(70, 9, 42) > 0.9) & (fbm(6, 6, 2, 43) > 0.6)
    out = mix(out, rgb((0.16, 0.30, 0.14)), needles * 0.8)
    return out


def paint_pearl_gold():
    # left half: a white glass ball (coloured by whoever draws it), lit from above with a window's gleam
    lit = lerp(0.62, 1.0, smoothstep(0.05, 0.75, YY))
    pearl = rgb((0.94, 0.94, 0.94), 1.0) * lit[:, :, None]
    gleam = np.exp(-(((XX - 0.25) / 0.045) ** 2 + ((YY - 0.70) / 0.07) ** 2))
    pearl = mix(pearl, rgb((1.3, 1.3, 1.3)), np.clip(gleam, 0, 1))
    band = np.exp(-((YY - 0.30) / 0.05) ** 2) * 0.12
    pearl = mix(pearl, rgb((1.0, 1.0, 1.0)), band)
    # right half: gold foil
    gold = rgb((0.90, 0.66, 0.20), 0.72 + 0.5 * fbm(4, 9, 3, 44))
    gold = mix(gold, rgb((1.0, 0.93, 0.62)), smoothstep(0.62, 0.85, fbm(9, 3, 2, 45)) * 0.7)
    return np.where((XX < 0.5)[:, :, None], pearl, gold)


def paint_atlas():
    painters = [paint_terracotta, paint_soil, paint_galvanised, paint_pebbles,
                paint_wicker, lambda: paint_enamel((0.72, 0.06, 0.07), 18), lambda: paint_enamel((0.07, 0.36, 0.16), 19), paint_steel,
                paint_wood, paint_wood_end, paint_burlap, paint_twine,
                paint_felt, paint_quilt, paint_water, paint_pearl_gold]
    size = N * GRID
    atlas = np.zeros((size, size, 4), dtype=np.float32)
    atlas[:, :, 3] = 1.0
    for i, painter in enumerate(painters):
        col = i % GRID
        row = i // GRID
        y0 = (GRID - 1 - row) * N
        atlas[y0:y0 + N, col * N:(col + 1) * N, :3] = np.clip(painter(), 0.0, 1.0)
    return atlas


def cuv(cell, u, v):
    """A place in a square of the picture: u, v 0..1 across and up it."""
    i = CELLS.index(cell) if isinstance(cell, str) else cell
    col = i % GRID
    row = i // GRID
    return ((col + INSET + u * (1 - 2 * INSET)) / GRID, (GRID - 1 - row + INSET + v * (1 - 2 * INSET)) / GRID)


# ---------------------------------------------------------------------------------------------- building
class Part:
    """Points and faces of one model, with the piece each face belongs to (a closed solid, checked by itself)."""

    def __init__(self):
        self.v = []
        self.f = []          # [ids, uvs, piece]
        self.piece = 0
        self.open = set()    # pieces that are sheets, not solids: faces must look up or outward

    def new_piece(self, sheet=False):
        self.piece += 1
        if sheet:
            self.open.add(self.piece)
        return self.piece

    def vert(self, p):
        self.v.append((float(p[0]), float(p[1]), float(p[2])))
        return len(self.v) - 1

    def face(self, ids, uvs):
        # leave out faces squeezed to nothing
        if len(set(self.v[i] for i in ids)) < 3:
            return
        self.f.append([list(ids), list(uvs), self.piece])

    def triangles(self):
        return sum(len(f[0]) - 2 for f in self.f)


def face_normal(part, ids):
    a, b, c = (Vector(part.v[i]) for i in ids[:3])
    n = (b - a).cross(c - a)
    if n.length < 1e-12 and len(ids) > 3:
        a, b, c = (Vector(part.v[i]) for i in (ids[0], ids[2], ids[3]))
        n = (b - a).cross(c - a)
    return n.normalized() if n.length > 0 else Vector((0, 0, 1))


def outward(part, name):
    """Turns every face that looks into its own solid; returns how many it turned and how many are still wrong."""
    turned = 0
    wrong = 0
    for attempt in range(2):
        wrong = 0
        for piece in range(1, part.piece + 1):
            faces = [f for f in part.f if f[2] == piece]
            if not faces:
                continue
            if piece in part.open:
                for f in faces:
                    c = sum((Vector(part.v[i]) for i in f[0]), Vector()) / len(f[0])
                    want = Vector((c.x, c.y, 0.0)).normalized() * 0.35 + Vector((0, 0, 1))
                    if face_normal(part, f[0]).dot(want) < 0.0:
                        f[0].reverse()
                        f[1].reverse()
                        turned += 1
                        wrong += 1
                continue
            # (as triangles fanned from each face's first corner, the same ones the rays start from: a bent
            # quad's middle can lie under the triangles another split would give it)
            tris = []
            for f in faces:
                for n in range(1, len(f[0]) - 1):
                    tris.append((f[0][0], f[0][n], f[0][n + 1]))
            tree = BVHTree.FromPolygons(part.v, tris, all_triangles=True, epsilon=0.0)
            for f in faces:
                a, b, c = (Vector(part.v[i]) for i in f[0][:3])
                n = face_normal(part, f[0])
                start = (a + b + c) / 3.0 + n * 1e-5
                hits = 0
                for _ in range(64):
                    hit = tree.ray_cast(start, n)
                    if hit[0] is None:
                        break
                    hits += 1
                    start = hit[0] + n * 1e-5
                if hits % 2 == 1:
                    wrong += 1
                    if attempt == 0:
                        f[0].reverse()
                        f[1].reverse()
                        turned += 1
        if wrong == 0:
            break
    if wrong:
        print("INSIDE OUT: %s still has %d faces looking inward (last piece checked %d of %d)" % (name, wrong, piece, part.piece))
    return turned, wrong


def lathe(part, runs, segs, mod=None, piece=None):
    """Turns a profile about the upright. `runs` are stretches of it, each {cell, pts: [(r, z)..], rep: times the
    square repeats round, v: (from, to) up the square, planar: R to lay the square flat over a disc of that
    radius instead}. Runs meet at shared places but not shared points, so the join is a crease. `mod(theta, r, z,
    run index, share along the run)` may move each point: return (r, z)."""
    if piece is None:
        part.new_piece()
    for ri, run in enumerate(runs):
        pts = run["pts"]
        rep = run.get("rep", 1)
        v0, v1 = run.get("v", (0.0, 1.0))
        planar = run.get("planar", 0.0)
        per = max(segs // rep, 1)
        along = [0.0]
        for j in range(1, len(pts)):
            along.append(along[-1] + math.hypot(pts[j][0] - pts[j - 1][0], pts[j][1] - pts[j - 1][1]))
        total = max(along[-1], 1e-9)
        rings = []
        for j, (r, z) in enumerate(pts):
            share = along[j] / total
            ring = []
            for i in range(segs):
                th = TAU * i / segs
                rr, zz = (r, z) if mod is None else mod(th, r, z, ri, share)
                if r <= 1e-9:
                    rr = 0.0
                ring.append((rr * math.cos(th), rr * math.sin(th), zz))
            if r <= 1e-9:
                zz = sum(p[2] for p in ring) / segs
                one = part.vert((0.0, 0.0, zz))
                rings.append(([one] * segs, [(0.0, 0.0, zz)] * segs, share))
            else:
                rings.append(([part.vert(p) for p in ring], ring, share))

        def uv_at(ring, i, i_shown):
            if planar > 0.0:
                p = ring[1][i % segs]
                return cuv(run["cell"], 0.5 + 0.5 * p[0] / planar, 0.5 + 0.5 * p[1] / planar)
            return cuv(run["cell"], i_shown / float(per), lerp(v0, v1, ring[2]))

        for j in range(len(pts) - 1):
            lo_ring, hi_ring = rings[j], rings[j + 1]
            for i in range(segs):
                k = i % per
                ids = [lo_ring[0][i], lo_ring[0][(i + 1) % segs], hi_ring[0][(i + 1) % segs], hi_ring[0][i]]
                uvs = [uv_at(lo_ring, i, k), uv_at(lo_ring, i + 1, k + 1), uv_at(hi_ring, i + 1, k + 1), uv_at(hi_ring, i, k)]
                keep = [n for n in range(4) if ids[n] not in ids[:n]]
                part.face([ids[n] for n in keep], [uvs[n] for n in keep])


def sweep(part, pts, section, cell, hint, closed=False, caps=True, per=4, v=(0.0, 1.0), flat=False, scale=None, piece=None):
    """Carries a closed outline (`section`: points across and up, metres) along a line of points. `hint` is a
    direction (or a function of the point giving one) that the outline's `up` leans towards. The square repeats
    along the line every `per` steps and wraps once round the outline over `v`. `flat` gives every side of the
    outline its own points (hard corners). `scale` (per point) fattens or thins it."""
    if piece is None:
        part.new_piece()
    count = len(pts)
    pts = [Vector(p) for p in pts]
    sides = len(section)
    rings = []
    for k in range(count):
        if closed:
            ahead = (pts[(k + 1) % count] - pts[(k - 1) % count]).normalized()
        else:
            ahead = (pts[min(k + 1, count - 1)] - pts[max(k - 1, 0)]).normalized()
        h = Vector(hint(pts[k])) if callable(hint) else Vector(hint)
        up = (h - ahead * h.dot(ahead))
        up = up.normalized() if up.length > 1e-6 else ahead.orthogonal().normalized()
        across = ahead.cross(up).normalized()
        s = scale[k] if scale else 1.0
        ring = [pts[k] + across * (a * s) + up * (b * s) for a, b in section]
        rings.append(ring)
    lengths = [0.0]
    for j in range(sides):
        a = Vector(section[j] + (0.0,))
        b = Vector(section[(j + 1) % sides] + (0.0,))
        lengths.append(lengths[-1] + (b - a).length)
    ids = []
    for ring in rings:
        if flat:
            ids.append([[part.vert(ring[j]), part.vert(ring[(j + 1) % sides])] for j in range(sides)])
        else:
            made = [part.vert(p) for p in ring]
            ids.append([[made[j], made[(j + 1) % sides]] for j in range(sides)])
    spans = count if closed else count - 1
    for k in range(spans):
        k2 = (k + 1) % count
        u0 = (k % per) / float(per)
        u1 = u0 + 1.0 / per
        for j in range(sides):
            va = lerp(v[0], v[1], lengths[j] / lengths[-1])
            vb = lerp(v[0], v[1], lengths[j + 1] / lengths[-1])
            part.face([ids[k][j][0], ids[k][j][1], ids[k2][j][1], ids[k2][j][0]],
                      [cuv(cell, u0, va), cuv(cell, u0, vb), cuv(cell, u1, vb), cuv(cell, u1, va)])
    if caps and not closed:
        for end in (0, count - 1):
            ring = [part.vert(p) for p in rings[end]]
            part.face(ring, [cuv(cell, 0.5 + 0.2 * math.cos(TAU * j / sides), 0.5 + 0.2 * math.sin(TAU * j / sides)) for j in range(sides)])


def circle(radius, sides, squash=1.0):
    return [(radius * math.cos(TAU * j / sides), radius * squash * math.sin(TAU * j / sides)) for j in range(sides)]


def box(part, centre, half, turn, cells, bands):
    """A box turned `turn` radians about the upright. `cells`: (sides and top, ends). The long way is x."""
    part.new_piece()
    c, s = math.cos(turn), math.sin(turn)

    def at(x, y, z):
        return (centre[0] + x * c - y * s, centre[1] + x * s + y * c, centre[2] + z)

    hx, hy, hz = half
    faces = [
        ((-hx, -hy, hz), (hx, -hy, hz), (hx, hy, hz), (-hx, hy, hz), cells[0], bands[0]),        # top
        ((-hx, hy, -hz), (hx, hy, -hz), (hx, -hy, -hz), (-hx, -hy, -hz), cells[0], bands[1]),    # bottom
        ((-hx, -hy, -hz), (hx, -hy, -hz), (hx, -hy, hz), (-hx, -hy, hz), cells[0], bands[2]),    # front
        ((hx, hy, -hz), (-hx, hy, -hz), (-hx, hy, hz), (hx, hy, hz), cells[0], bands[3]),        # back
        ((hx, -hy, -hz), (hx, hy, -hz), (hx, hy, hz), (hx, -hy, hz), cells[1], (0.05, 0.95)),    # ends
        ((-hx, hy, -hz), (-hx, -hy, -hz), (-hx, -hy, hz), (-hx, hy, hz), cells[1], (0.05, 0.95)),
    ]
    for a, b, cc, d, cell, band in faces:
        ids = [part.vert(at(*p)) for p in (a, b, cc, d)]
        part.face(ids, [cuv(cell, 0.03, band[0]), cuv(cell, 0.97, band[0]), cuv(cell, 0.97, band[1]), cuv(cell, 0.03, band[1])])


def blob(part, centre, radii, segs, rings, cell, patch, seed, lump=0.18):
    """A lumpy rounded stone; the square laid over it from above, `patch` = (u, v, half-size)."""
    part.new_piece()
    rs = np.random.RandomState(seed)
    ph = rs.rand(6) * TAU
    grid = []
    for j in range(rings + 1):
        lat = -math.pi / 2 + math.pi * j / rings
        row = []
        for i in range(segs):
            th = TAU * i / segs
            n = 1.0 + lump * (math.sin(2 * th + ph[0]) * math.cos(lat * 2 + ph[1]) * 0.6 + math.sin(3 * th + ph[2] + lat) * 0.4)
            x = math.cos(lat) * math.cos(th) * radii[0] * n
            y = math.cos(lat) * math.sin(th) * radii[1] * n
            z = math.sin(lat) * radii[2]
            row.append((centre[0] + x, centre[1] + y, centre[2] + z, x / radii[0], y / radii[1]))
        grid.append(row)
    ids = []
    for j, row in enumerate(grid):
        if j == 0 or j == rings:
            one = part.vert((centre[0], centre[1], row[0][2]))
            ids.append([one] * segs)
        else:
            ids.append([part.vert(p[:3]) for p in row])

    def uv(j, i):
        p = grid[j][i % segs]
        if j == 0 or j == rings:
            return cuv(cell, patch[0], patch[1])
        return cuv(cell, patch[0] + patch[2] * p[3] * 0.8, patch[1] + patch[2] * p[4] * 0.8)

    for j in range(rings):
        for i in range(segs):
            q = [ids[j][i], ids[j][(i + 1) % segs], ids[j + 1][(i + 1) % segs], ids[j + 1][i]]
            uvs = [uv(j, i), uv(j, i + 1), uv(j + 1, i + 1), uv(j + 1, i)]
            keep = [n for n in range(4) if q[n] not in q[:n]]
            part.face([q[n] for n in keep], [uvs[n] for n in keep])


def arc(r0, z0, r1, z1, bulge, steps):
    """Points from one place of a profile to another, bowed out by `bulge` (metres, to the right of the way)."""
    out = []
    dx, dz = r1 - r0, z1 - z0
    long = math.hypot(dx, dz)
    nx, nz = dz / long, -dx / long
    for k in range(steps + 1):
        t = k / steps
        b = math.sin(math.pi * t) * bulge
        out.append((r0 + dx * t + nx * b, z0 + dz * t + nz * b))
    return out


def bumps(seed, count=5):
    rs = np.random.RandomState(seed)
    terms = [(rs.randint(1, 6), rs.rand() * TAU, rs.randint(1, 4), rs.rand() * TAU, rs.rand()) for _ in range(count)]

    def f(th, share):
        return sum(w * math.sin(k * th + p) * math.sin(m * share * math.pi + q) for k, p, m, q, w in terms) / count

    return f


# ---------------------------------------------------------------------------------------------- the models
def build_pot(lo):
    part = Part()
    segs = 12 if lo else 24
    soil_bump = bumps(3)

    def mod(th, r, z, ri, share):
        if ri == 5:   # the soil: heaped a little, crumbly
            edge = 1.0 - (r / 0.108) ** 2
            return r, z + 0.006 * edge + (0.0 if lo else 0.006 * soil_bump(th, r / 0.108) * min(edge * 3.0, 1.0))
        return r, z

    lathe(part, [
        {"cell": "terracotta", "pts": [(0.0, 0.006), (0.078, 0.006)], "planar": 0.3},
        {"cell": "terracotta", "pts": [(0.078, 0.006), (0.082, 0.012)] + arc(0.083, 0.014, 0.116, 0.152, 0.004, 1 if lo else 5), "rep": 4, "v": (0.02, 0.72)},
        {"cell": "terracotta", "pts": [(0.116, 0.152), (0.129, 0.152), (0.132, 0.157)], "rep": 4, "v": (0.60, 0.66)},
        {"cell": "terracotta", "pts": [(0.132, 0.157)] + arc(0.133, 0.160, 0.133, 0.190, 0.0025, 1 if lo else 3) + [(0.130, 0.197)], "rep": 4, "v": (0.66, 0.90)},
        {"cell": "terracotta", "pts": [(0.130, 0.197), (0.126, 0.200), (0.114, 0.200), (0.110, 0.196), (0.108, 0.176)], "rep": 4, "v": (0.90, 0.99)},
        {"cell": "soil", "pts": [(0.108, 0.176), (0.075, 0.176), (0.04, 0.176), (0.0, 0.176)] if not lo else [(0.108, 0.176), (0.0, 0.176)], "planar": 0.11},
    ], segs, mod)
    # the saucer it stands on
    lathe(part, [
        {"cell": "terracotta", "pts": [(0.0, 0.0), (0.104, 0.0)], "planar": 0.3},
        {"cell": "terracotta", "pts": [(0.104, 0.0), (0.128, 0.016), (0.140, 0.020), (0.141, 0.024)], "rep": 4, "v": (0.55, 0.70)},
        {"cell": "terracotta", "pts": [(0.141, 0.024), (0.134, 0.025), (0.122, 0.014), (0.090, 0.008), (0.0, 0.008)], "rep": 4, "v": (0.70, 0.96)},
    ], segs)
    return part


def build_bucket(lo):
    part = Part()
    segs = 12 if lo else 24
    wall = []
    # (radius grows from 0.094 at the foot to 0.130 at the rim; two rolled ribs)

    def rad(z):
        return 0.094 + (0.130 - 0.094) * z / 0.21

    zs = [0.0, 0.004, 0.010] + ([0.064, 0.070, 0.076, 0.144, 0.150, 0.156] if not lo else [0.070, 0.150]) + [0.200]
    for z in zs:
        rib = 0.0045 if z in (0.070, 0.150) else 0.0
        foot = 0.003 if z <= 0.004 else 0.0
        wall.append((rad(z) + rib + foot, z))
    pebble_bump = bumps(5)

    def mod(th, r, z, ri, share):
        if ri == 4:
            edge = max(1.0 - (r / 0.124) ** 2, 0.0)
            return r, z + 0.004 * edge + (0.0 if lo else 0.004 * pebble_bump(th, r / 0.124) * min(edge * 3.0, 1.0))
        return r, z

    lathe(part, [
        {"cell": "galvanised", "pts": [(0.0, 0.0), (0.097, 0.0)], "planar": 0.2},
        {"cell": "galvanised", "pts": wall, "rep": 4, "v": (0.02, 0.92)},
        {"cell": "galvanised", "pts": [(rad(0.2), 0.200)] + ([(0.1345, 0.203), (0.1365, 0.208), (0.1345, 0.213), (0.130, 0.215), (0.126, 0.212)] if not lo else [(0.136, 0.208), (0.130, 0.215)]), "rep": 4, "v": (0.92, 0.99)},
        {"cell": "galvanised", "pts": [(0.126, 0.212) if not lo else (0.130, 0.215), (0.124, 0.186)], "rep": 4, "v": (0.80, 0.90)},
        {"cell": "pebbles", "pts": [(0.124, 0.186), (0.08, 0.186), (0.04, 0.186), (0.0, 0.186)] if not lo else [(0.124, 0.186), (0.0, 0.186)], "planar": 0.13},
    ], segs, mod)
    # loose pebbles on top, clear of the trunk
    rs = np.random.RandomState(8)
    for n in range(4 if lo else 13):
        a = TAU * (n + rs.rand() * 0.6) / (4 if lo else 13)
        d = 0.062 + 0.05 * rs.rand()
        size = 0.011 + 0.008 * rs.rand()
        blob(part, (d * math.cos(a), d * math.sin(a), 0.190 + size * 0.2), (size, size * (0.7 + 0.3 * rs.rand()), size * 0.6),
             5 if lo else 8, 3 if lo else 5, "pebbles", (0.15 + 0.7 * rs.rand(), 0.15 + 0.7 * rs.rand(), 0.07), n)
    # ears and the bail handle, dropped to one side
    for sx in (-1, 1):
        box(part, (sx * 0.1335, 0.0, 0.192), (0.0035, 0.016, 0.013), 0.0, ("galvanised", "galvanised"),
            [(0.3, 0.4), (0.3, 0.4), (0.4, 0.5), (0.5, 0.6)])
    steps = 6 if lo else 18
    handle = []
    R = 0.146
    tip = math.radians(110.0)   # how far it has swung down from upright, towards -y
    for k in range(steps + 1):
        a = math.pi * k / steps
        up = math.sin(a) * R
        handle.append((-math.cos(a) * 0.137, -up * math.sin(tip), 0.196 + up * math.cos(tip)))
    sweep(part, handle, circle(0.0032, 4 if lo else 6), "steel", (0.0, -math.cos(tip), -math.sin(tip)), per=3)
    mid = handle[steps // 2]
    sweep(part, [(mid[0] - 0.03, mid[1], mid[2]), (mid[0] + 0.03, mid[1], mid[2])], circle(0.009, 5 if lo else 8), "wood",
          (0, 0, 1), per=1, v=(0.1, 0.5))
    return part


def build_basket(lo):
    part = Part()
    segs = 12 if lo else 24
    rows = 10

    def rad(z):
        t = z / 0.19
        return 0.088 + 0.050 * math.sin(math.pi * min(t * 0.62, 1.0)) ** 0.9 - 0.012 * max(t - 0.75, 0.0) / 0.25

    wall = []
    if lo:
        for z in (0.004, 0.06, 0.12, 0.19):
            wall.append((rad(z), z))
    else:
        for k in range(rows * 2 + 1):
            z = 0.004 + (0.19 - 0.004) * k / (rows * 2)
            wall.append((rad(z) + (0.0028 if k % 2 == 1 else 0.0), z))
    cloth = bumps(11, 6)

    def mod(th, r, z, ri, share):
        if ri == 3:   # the liner: gathered folds, heaped towards the trunk
            fold = 0.0 if lo else 0.006 * math.sin(th * 9 + 2.0 * math.sin(th * 2)) * (r / 0.11)
            edge = max(1.0 - r / 0.118, 0.0)
            return r, z + 0.018 * edge + (fold + (0.0 if lo else 0.004 * cloth(th, r / 0.118))) * min(edge * 4.0, 1.0)
        return r, z

    lathe(part, [
        {"cell": "wicker", "pts": [(0.0, 0.0), (0.086, 0.0), (rad(0.004), 0.004)], "planar": 0.2},
        {"cell": "wicker", "pts": wall, "rep": 4, "v": (0.0, 1.0)},
        {"cell": "wicker", "pts": [(rad(0.19), 0.19), (rad(0.19) - 0.008, 0.196), (0.118, 0.180)], "rep": 4, "v": (0.80, 0.99)},
        {"cell": "burlap", "pts": [(0.118, 0.180), (0.09, 0.180), (0.06, 0.180), (0.03, 0.180), (0.0, 0.180)] if not lo else [(0.118, 0.180), (0.06, 0.180), (0.0, 0.180)], "planar": 0.14},
    ], segs, mod)
    # the braided rim
    rim_r = rad(0.19) - 0.002
    count = 12 if lo else 24
    sweep(part, [(rim_r * math.cos(TAU * k / count), rim_r * math.sin(TAU * k / count), 0.193) for k in range(count)],
          circle(0.0105, 4 if lo else 7, 0.85), "twine", (0, 0, 1), closed=True, per=2)
    # two loop handles standing on the rim
    for sx in (-1, 1):
        steps = 4 if lo else 9
        loop = []
        for k in range(steps + 1):
            a = math.pi * k / steps
            loop.append((sx * (rim_r + 0.004 + 0.012 * math.sin(a)), -0.034 * math.cos(a), 0.193 + 0.030 * math.sin(a)))
        sweep(part, loop, circle(0.0055, 4 if lo else 6), "twine", (sx, 0, 0.2), per=2)
    return part


def build_metal_stand(lo):
    part = Part()
    segs = 12 if lo else 24
    # the green water bowl
    lathe(part, [
        {"cell": "green_enamel", "pts": [(0.0, 0.026), (0.072, 0.026)], "planar": 0.2},
        {"cell": "green_enamel", "pts": [(0.072, 0.026)] + arc(0.077, 0.029, 0.104, 0.118, 0.008, 1 if lo else 5), "rep": 2, "v": (0.03, 0.9)},
        {"cell": "green_enamel", "pts": [(0.104, 0.118), (0.108, 0.121), (0.107, 0.125), (0.102, 0.126), (0.099, 0.123)] if not lo else [(0.104, 0.118), (0.108, 0.123), (0.099, 0.123)], "rep": 2, "v": (0.9, 0.99)},
        {"cell": "green_enamel", "pts": [(0.099, 0.123), (0.093, 0.098)], "rep": 2, "v": (0.6, 0.75)},
        {"cell": "water", "pts": [(0.093, 0.098), (0.05, 0.098), (0.0, 0.098)] if not lo else [(0.093, 0.098), (0.0, 0.098)], "planar": 0.095},
    ], segs)
    # the red ring the bolts go through
    count = 12 if lo else 24
    sweep(part, [(0.088 * math.cos(TAU * k / count), 0.088 * math.sin(TAU * k / count), 0.199) for k in range(count)],
          [(-0.004, -0.015), (0.004, -0.015), (0.004, 0.015), (-0.004, 0.015)], "red_enamel", (0, 0, 1), closed=True,
          per=count // 4, flat=True, v=(0.1, 0.9))
    # four red strap legs: a foot flat on the floor, up and in to the bowl's rim, then upright to the ring
    for q in range(4):
        a = TAU * q / 4
        c, s = math.cos(a), math.sin(a)
        line = [(0.262, 0.0035), (0.222, 0.0035), (0.212, 0.008), (0.116, 0.112), (0.108, 0.128), (0.095, 0.184), (0.095, 0.216)]
        if lo:
            line = [(0.262, 0.0035), (0.217, 0.0045), (0.112, 0.120), (0.095, 0.216)]
        pts = [(r * c, r * s, z) for r, z in line]
        sweep(part, pts, [(-0.017, -0.003), (0.017, -0.003), (0.017, 0.003), (-0.017, 0.003)], "red_enamel",
              lambda p, c=c, s=s: (c * 0.5, s * 0.5, 1.0), per=len(pts) - 1, flat=True, v=(0.1, 0.9))
        # a eye bolt between this leg and the next: threaded rod, a ring to turn it by, a pad on the trunk
        b = a + TAU / 8
        bc, bs = math.cos(b), math.sin(b)
        sweep(part, [(0.026 * bc, 0.026 * bs, 0.199), (0.140 * bc, 0.140 * bs, 0.199)], circle(0.0042, 4 if lo else 6), "steel",
              (0, 0, 1), per=1)
        sweep(part, [(0.022 * bc, 0.022 * bs, 0.199), (0.027 * bc, 0.027 * bs, 0.199)], circle(0.011, 5 if lo else 8), "steel",
              (0, 0, 1), per=1, v=(0.4, 0.6))
        eye = []
        steps = 5 if lo else 10
        for k in range(steps):
            e = TAU * k / steps
            eye.append(((0.153 + 0.013 * math.cos(e)) * bc, (0.153 + 0.013 * math.cos(e)) * bs, 0.199 + 0.013 * math.sin(e)))
        sweep(part, eye, circle(0.0036, 4 if lo else 5), "steel", (-bs, bc, 0.0), closed=True, per=steps)
        if not lo:   # the nut welded to the ring
            sweep(part, [(0.093 * bc, 0.093 * bs, 0.199), (0.101 * bc, 0.101 * bs, 0.199)], circle(0.009, 6), "steel",
                  (0, 0, 1), per=1, flat=True, v=(0.4, 0.6))
    return part


def build_plank_cross(lo):
    part = Part()
    bands = [(0.04, 0.34), (0.62, 0.92), (0.38, 0.48), (0.50, 0.60)]
    box(part, (0.0, 0.0, 0.012), (0.25, 0.036, 0.012), math.radians(3.0), ("wood", "wood_end"), bands)
    box(part, (0.004, 0.0, 0.036), (0.235, 0.034, 0.012), math.radians(91.5), ("wood", "wood_end"), bands[1:] + bands[:1])
    for sy in (-1, 1):   # blocks under the upper plank's ends, so it sits level
        box(part, (0.004 - sy * 0.005, sy * 0.19, 0.012), (0.036, 0.034, 0.012), math.radians(91.5 + sy * 4.0),
            ("wood", "wood_end"), bands[2:] + bands[:2])
    if not lo:
        # a block nailed each side of the trunk to hold it, and nail heads
        for sx in (-1, 1):
            box(part, (sx * 0.052, 0.002, 0.058), (0.012, 0.03, 0.010), math.radians(sx * 6.0), ("wood", "wood_end"), bands)
        for x, y in ((0.052, 0.012), (-0.052, -0.010), (0.004, 0.19), (0.006, -0.19), (0.03, -0.02), (-0.028, 0.022)):
            z = 0.068 if abs(x) > 0.04 else 0.048
            first = len(part.v)
            lathe(part, [{"cell": "steel", "pts": [(0.0, z - 0.004), (0.0045, z - 0.004), (0.0045, z + 0.0012), (0.0, z + 0.002)], "planar": 0.02}], 6)
            for i in range(first, len(part.v)):   # (a lathe turns about the middle: moved to its place)
                part.v[i] = (part.v[i][0] + x, part.v[i][1] + y, part.v[i][2])
    return part


def build_root_ball(lo):
    part = Part()
    segs = 12 if lo else 24
    lump = bumps(21, 7)
    fold = bumps(22, 4)

    def body(z):
        # a squashed ball, flat underneath
        t = min(max(z / 0.175, 0.0), 1.0)
        return 0.132 * math.sqrt(max(1.0 - ((t - 0.42) / 0.62) ** 2, 0.1))

    zs = [0.0, 0.012, 0.035, 0.065, 0.095, 0.125, 0.150, 0.168] if not lo else [0.0, 0.03, 0.09, 0.15]
    wall = [(max(body(z), 0.05) if z > 0 else 0.085, z) for z in zs]
    neck = [(0.060, 0.182), (0.043, 0.194), (0.039, 0.206)]
    ruffle = [(0.039, 0.206), (0.052, 0.226), (0.066, 0.236)]
    ruffle_in = [(0.066, 0.236), (0.052, 0.231), (0.036, 0.218), (0.0, 0.214)]
    if lo:
        ruffle = [(0.039, 0.206), (0.066, 0.236)]
        ruffle_in = [(0.066, 0.236), (0.034, 0.218), (0.0, 0.214)]

    def step(a, b, x):
        t = min(max((x - a) / (b - a), 0.0), 1.0)
        return t * t * (3.0 - 2.0 * t)

    def mod(th, r, z, ri, share):
        # (by height, not by stretch of the profile, so the stretches meet without a crack)
        up = min(z / 0.182, 1.0)
        lumps = (0.0 if lo else 0.11) * lump(th, up) * (0.4 + up) * step(0.0, 0.03, z) * (1.0 - step(0.165, 0.190, z))
        gather = 0.10 * math.sin(th * 11 + 1.5 * math.sin(th * 3)) * step(0.165, 0.195, z)
        if ri >= 3:   # the ruffle of cloth above the tie, out and back in (by how far out, so its two sides meet)
            wave = math.sin(th * 7 + 2.0 * math.sin(th * 2.0))
            w = min(max((r - 0.039) / (0.066 - 0.039), 0.0), 1.0)
            return (r * (1.0 + gather * (1.0 - w) + 0.09 * wave * w),
                    z + (0.008 * wave + 0.004 * fold(th, w)) * w)
        return r * (1.0 + lumps + gather), z

    lathe(part, [
        {"cell": "burlap", "pts": [(0.0, 0.0), (0.085, 0.0)], "planar": 0.2},
        {"cell": "burlap", "pts": wall + [neck[0]], "rep": 4, "v": (0.0, 1.0)},
        {"cell": "burlap", "pts": neck, "rep": 4, "v": (0.3, 0.6)},
        {"cell": "burlap", "pts": ruffle, "rep": 4, "v": (0.1, 0.45)},
        {"cell": "burlap", "pts": ruffle_in, "rep": 4, "v": (0.5, 0.9)},
    ], segs, mod)

    def skin(th, z):
        r, zz = mod(th, wall_r(z), z, 1, 0.0)
        return r

    def wall_r(z):
        for k in range(len(wall) - 1):
            if wall[k][1] <= z <= wall[k + 1][1]:
                t = (z - wall[k][1]) / (wall[k + 1][1] - wall[k][1])
                return lerp(wall[k][0], wall[k + 1][0], t)
        return 0.06

    out = lambda p: (p[0], p[1], 0.25)
    sides = 3 if lo else 5
    # twine round its middle twice, slanted each its own way
    for z0, slant, ph in ((0.070, 0.022, 0.4), (0.118, -0.018, 2.1)):
        count = 12 if lo else 24
        loop = []
        for k in range(count):
            th = TAU * k / count
            z = z0 + slant * math.sin(th + ph)
            r = skin(th, z) + 0.0025
            loop.append((r * math.cos(th), r * math.sin(th), z))
        sweep(part, loop, circle(0.0042, sides), "twine", out, closed=True, per=2)
    # strands up and over from under the ball to the neck
    for q in range(3 if lo else 5):
        th = TAU * (q + 0.3) / (3 if lo else 5)
        strand = []
        for z in ([0.02, 0.09, 0.168] if lo else [0.012, 0.035, 0.065, 0.095, 0.125, 0.150, 0.168]):
            r = skin(th, z) + 0.0025
            strand.append((r * math.cos(th), r * math.sin(th), z))
        strand.append((0.062 * math.cos(th), 0.062 * math.sin(th), 0.184))
        strand.append((0.046 * math.cos(th), 0.046 * math.sin(th), 0.197))
        # (leaning on the way round the ball, never along the strand itself)
        sweep(part, strand, circle(0.0040, sides), "twine", (-math.sin(th), math.cos(th), 0.0), per=2)
    # and wound round the neck
    count = 10 if lo else 30
    turns = 1 if lo else 2
    wind = []
    for k in range(count + 1):
        th = TAU * turns * k / count
        r = 0.0445 + (0.0 if lo else 0.004 * math.sin(th * 11 + 1.5 * math.sin(th * 3)) * 0.4)
        wind.append((r * math.cos(th), r * math.sin(th), 0.188 + 0.021 * k / count))
    sweep(part, wind, circle(0.0042, sides), "twine", out, per=2)
    return part


def build_skirt(lo, quilted, rise):
    """The cloth laid round the foot. `rise` 0 flat on the floor, 1 its middle lifted one radius (the shape key)."""
    part = Part()
    part.new_piece(sheet=True)
    segs = 16 if lo else 64
    rings = 3 if lo else 9
    hole = 0.10
    reps = 8 if not quilted else 4
    per = segs // reps
    folds = 9

    def place(j, i):
        th = TAU * i / segs
        t = j / float(rings)
        rim = 1.0 + 0.030 * math.cos(folds * th + 1.3 * math.sin(2 * th + 0.7))
        if not quilted and not lo:
            rim += 0.028 * abs(math.sin(8 * th))
        r = hole + (rim - hole) * t ** 0.85
        ripple = 0.5 + 0.5 * math.cos(folds * th + 1.3 * math.sin(2 * th + 0.7) + 2.2 * (1.0 - t))
        z = 0.006 + (0.050 if not quilted else 0.036) * (r ** 1.6) * ripple
        lift = 1.0 - (min(max((r - 0.13) / (0.60 - 0.13), 0.0), 1.0)) ** 0.8
        lift = lift * lift * (3.0 - 2.0 * lift)
        # (lifted, the cloth is pulled in a little and its folds deepen up the cone)
        z += rise * lift * (1.0 + 0.10 * math.cos(folds * th + 0.6) * t)
        return (r * math.cos(th), r * math.sin(th), z), t

    grid = []
    for j in range(rings + 1):
        row = []
        for i in range(segs):
            p, t = place(j, i)
            row.append(part.vert(p))
        grid.append(row)
    cell = "quilt" if quilted else "felt"
    for j in range(rings):
        for i in range(segs):
            k = i % per
            u0, u1 = k / float(per), (k + 1) / float(per)
            v0, v1 = j / float(rings), (j + 1) / float(rings)
            part.face([grid[j][i], grid[j][(i + 1) % segs], grid[j + 1][(i + 1) % segs], grid[j + 1][i]],
                      [cuv(cell, u0, v0), cuv(cell, u1, v0), cuv(cell, u1, v1), cuv(cell, u0, v1)])
    # the edge turned down to the floor, so no gap shows under it
    hem = []
    edge = []
    for i in range(segs):
        p, t = place(rings, i)
        edge.append(part.vert(p))    # (its own points: a crease along the cloth's edge)
        hem.append(part.vert((p[0] * 0.985, p[1] * 0.985, 0.0)))
    for i in range(segs):
        k = i % per
        u0, u1 = k / float(per), (k + 1) / float(per)
        part.face([edge[i], edge[(i + 1) % segs], hem[(i + 1) % segs], hem[i]],
                  [cuv(cell, u0, 0.99), cuv(cell, u1, 0.99), cuv(cell, u1, 0.93), cuv(cell, u0, 0.93)])
    return part


def build_bauble(lo):
    part = Part()
    segs = 8 if lo else 16
    steps = 4 if lo else 9
    R = 0.03
    top = -0.014          # the top of the glass, below the loop it hangs from
    pts = []
    for k in range(steps + 1):
        a = math.pi * k / steps
        pts.append((max(R * math.sin(a), 0.0), top - R + R * math.cos(a) * -1.0))
    pts[0] = (0.0, top - 2 * R)
    pts[-1] = (0.0, top)
    lathe(part, [{"cell": "pearl_gold", "pts": pts, "rep": 1, "v": (0.03, 0.97)}], segs,
          lambda th, r, z, ri, share: (r, z))
    # (the ball's u runs over the white half of its square only)
    for f in part.f:
        f[1] = [(lerp(cuv("pearl_gold", 0.04, 0)[0], cuv("pearl_gold", 0.46, 0)[0],
                      (uv[0] - cuv("pearl_gold", 0.0, 0)[0]) / (cuv("pearl_gold", 1.0, 0)[0] - cuv("pearl_gold", 0.0, 0)[0])), uv[1]) for uv in f[1]]
    start = len(part.f)
    lathe(part, [{"cell": "pearl_gold", "pts": [(0.0, top - 0.004), (0.0075, top - 0.004), (0.0075, top + 0.005), (0.0, top + 0.006)], "rep": 1, "v": (0.1, 0.9)}],
          5 if lo else 8)
    if not lo:
        loop = [(0.0, 0.004 * math.cos(TAU * k / 6), top + 0.009 + 0.004 * math.sin(TAU * k / 6)) for k in range(6)]
        sweep(part, loop, circle(0.0009, 3), "pearl_gold", (1, 0, 0), closed=True, per=6)
    for f in part.f[start:]:   # the cap and loop: the gold half
        f[1] = [cuv("pearl_gold", 0.62 + 0.25 * ((uv[0] * GRID) % 1.0), 0.2 + 0.6 * ((uv[1] * GRID) % 1.0)) for uv in f[1]]
    return part


def build_star(lo):
    part = Part()
    part.new_piece()
    R, r, deep = 0.052, 0.022, 0.011
    mid = 0.050          # the height of its middle over the socket's mouth
    rim = []
    for k in range(10):
        a = math.pi / 2 + TAU * k / 10
        rad = R if k % 2 == 0 else r
        rim.append((rad * math.cos(a), 0.0, mid + rad * math.sin(a)))
    for side in (-1, 1):
        for k in range(10):
            a, b = rim[k], rim[(k + 1) % 10]
            ids = [part.vert((0.0, side * deep, mid)), part.vert(a), part.vert(b)]
            shade = 0.25 + 0.5 * ((k + (1 if side > 0 else 0)) % 2)
            part.face(ids, [cuv("pearl_gold", 0.75, shade), cuv("pearl_gold", 0.55 + 0.4 * (k % 3) / 3.0, shade + 0.2),
                            cuv("pearl_gold", 0.60 + 0.3 * (k % 2), shade - 0.15)])
    # the cone socket that goes over the tree's tip (its mouth at the origin, open)
    first = len(part.f)
    lathe(part, [{"cell": "pearl_gold", "pts": [(0.0, -0.001), (0.013, 0.0), (0.0075, 0.030), (0.0, 0.031)], "rep": 1, "v": (0.1, 0.9)}],
          5 if lo else 8)
    for f in part.f[first:]:
        f[1] = [cuv("pearl_gold", 0.55 + 0.4 * ((uv[0] * GRID) % 1.0), 0.1 + 0.8 * ((uv[1] * GRID) % 1.0)) for uv in f[1]]
    return part


BUILDERS = [
    ("pot", build_pot), ("bucket", build_bucket), ("basket", build_basket), ("metal_stand", build_metal_stand),
    ("plank_cross", build_plank_cross), ("root_ball", build_root_ball),
    ("skirt_felt", lambda lo, rise=0.0: build_skirt(lo, False, rise)), ("skirt_quilted", lambda lo, rise=0.0: build_skirt(lo, True, rise)),
    ("bauble", build_bauble), ("star", build_star),
]


# ---------------------------------------------------------------------------------------------- into Blender
def make_object(name, part, material, risen=None):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(part.v, [], [f[0] for f in part.f])
    uv = mesh.uv_layers.new(name="UVMap")
    n = 0
    for f in part.f:
        for pair in f[1]:
            uv.data[n].uv = pair
            n += 1
    for poly in mesh.polygons:
        poly.use_smooth = True
    mesh.materials.append(material)
    mesh.update()
    ob = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(ob)
    if risen is not None:
        ob.shape_key_add(name="Basis")
        key = ob.shape_key_add(name="rise")
        for i, p in enumerate(risen.v):
            key.data[i].co = p
    return ob


def sheet(path, objects, everything):
    """A row for each model: front, right, back, left, above, three-quarters."""
    scene = bpy.context.scene
    cell = 360
    scene.render.engine = 'BLENDER_EEVEE_NEXT'
    scene.render.resolution_x = cell
    scene.render.resolution_y = cell
    scene.render.image_settings.file_format = 'PNG'
    scene.view_settings.view_transform = 'Standard'
    if scene.world is None:
        scene.world = bpy.data.worlds.new("look")
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs[0].default_value = (0.30, 0.32, 0.36, 1.0)
    scene.world.node_tree.nodes["Background"].inputs[1].default_value = 1.0
    cam_data = bpy.data.cameras.new("look_cam")
    cam_data.type = 'ORTHO'
    cam = bpy.data.objects.new("look_cam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    sun_data = bpy.data.lights.new("look_sun", 'SUN')
    sun_data.energy = 3.2
    sun = bpy.data.objects.new("look_sun", sun_data)
    scene.collection.objects.link(sun)
    rows = []
    for ob in objects:
        for other in everything:
            other.hide_render = other != ob
        ob.location = (0, 0, 0)
        pts = [Vector(v.co) for v in ob.data.vertices]
        lo_ = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
        hi_ = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
        mid = (lo_ + hi_) / 2
        span = max((hi_ - lo_).length, 0.01)
        cam_data.ortho_scale = span * 1.08
        row = []
        for way in ((0, -1, 0.18), (1, 0, 0.18), (0, 1, 0.18), (-1, 0, 0.18), (0, -0.001, 1), (0.7, -0.7, 0.55)):
            d = Vector(way).normalized()
            cam.location = mid + d * span * 3.0
            cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
            sun.rotation_euler = (d + Vector((0.4, -0.2, 0.9)).normalized() * 0.9).normalized().to_track_quat('Z', 'Y').to_euler()
            scene.render.filepath = os.path.join(SHEETS, "_view.png")
            bpy.ops.render.render(write_still=True)
            img = bpy.data.images.load(scene.render.filepath)
            px = np.array(img.pixels[:], dtype=np.float32).reshape(cell, cell, 4)
            bpy.data.images.remove(img)
            row.append(px)
        rows.append(np.concatenate(row, axis=1))
    whole = np.concatenate(rows[::-1], axis=0)
    out = bpy.data.images.new("sheet", whole.shape[1], whole.shape[0], alpha=True)
    out.pixels = whole.ravel()
    out.filepath_raw = path
    out.file_format = 'PNG'
    out.save()
    bpy.data.images.remove(out)
    for other in everything:
        other.hide_render = False
    bpy.data.objects.remove(cam)
    bpy.data.objects.remove(sun)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    atlas = paint_atlas()
    size = N * GRID
    image = bpy.data.images.new("tree_stands", size, size, alpha=False)
    image.pixels = atlas.ravel()
    image.filepath_raw = os.path.join(TEXTURES, "tree_stands.png")
    image.file_format = 'PNG'
    image.save()
    material = bpy.data.materials.new("tree_stands")
    material.use_nodes = True
    shader = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    shader.inputs["Roughness"].default_value = 0.8
    picture = material.node_tree.nodes.new("ShaderNodeTexImage")
    picture.image = image
    material.node_tree.links.new(picture.outputs["Color"], shader.inputs["Base Color"])
    material.use_backface_culling = True

    full, low = [], []
    print("name              triangles  low   radius  height  turned")
    for name, builder in BUILDERS:
        for lo in (False, True):
            part = builder(lo)
            turned, wrong = outward(part, name + ("_lo" if lo else ""))
            risen = None
            if name.startswith("skirt"):
                risen = builder(lo, 1.0)
                outward(risen, name + " risen")
            ob = make_object(name + ("_lo" if lo else ""), part, material, risen)
            (low if lo else full).append(ob)
            if not lo:
                radius = max(math.hypot(v[0], v[1]) for v in part.v)
                height = max(v[2] for v in part.v)
                line = "%-17s %5d" % (name, part.triangles())
            else:
                print("%s    %5d   %.3f   %.3f   %d+%d%s" % (line, part.triangles(), radius, height, first_turned, turned, "  WRONG" if wrong else ""))
            first_turned = turned
    # (the .glb has every one at the origin; in the .blend they are laid out in two rows, further down)
    for ob in bpy.data.objects:
        ob.select_set(ob in full or ob in low)
    bpy.ops.export_scene.gltf(filepath=os.path.join(MODELS, "tree_stands.glb"), export_format="GLB",
                              use_selection=True, export_apply=False, export_yup=True, export_image_format="NONE",
                              export_normals=True, export_texcoords=True, export_materials="EXPORT",
                              export_morph=True, export_morph_normal=True, export_animations=False)
    if SHEETS:
        os.makedirs(SHEETS, exist_ok=True)
        everything = full + low
        sheet(os.path.join(SHEETS, "stands_full.png"), full[:6], everything)
        sheet(os.path.join(SHEETS, "skirts_and_bits_full.png"), full[6:], everything)
        sheet(os.path.join(SHEETS, "stands_low.png"), low[:6], everything)
        sheet(os.path.join(SHEETS, "skirts_and_bits_low.png"), low[6:], everything)
    for row, objects in enumerate((full, low)):
        for i, ob in enumerate(objects):
            ob.location = (i * 0.7 if i < 6 else (5.6 + (i - 6) * 2.3 if i < 8 else 9.6 + (i - 8) * 0.3), row * 2.6, 0)
    image.pack()
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "tree_stands.blend"))
    print("tree stands: built")


main()
