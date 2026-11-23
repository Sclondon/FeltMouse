# Builds the Christmas tree ornaments for GameCommon's ornaments component.
#
#   blender -b --factory-startup --python build_ornaments.py [-- <folder for the look-over sheets>]
#
# Writes, beside this file:  ornaments.blend                  (every ornament as an object, to open and edit)
#          and in ../models:    ornaments.glb                 (what the game loads: one mesh per ornament, by name,
#                                                              "orn_<kind>" and its low twin "orn_<kind>_lo")
#          and in ../textures:  ornament_designs.png          (the glass designs, 16 cells of 512 x 256, stacked)
#                               ornament_paint.png            (everything else's paint, 16 cells of 256 x 256)
#                               ornament_shine.png            (the room a shiny ball mirrors: window, floor, rim)
#
# Every ornament is real size in metres. A hanging one has its origin at the TOP of its thread (where it hangs
# from the branch) and hangs down Blender's -Z (the game's -Y), its front to Blender's -Y (the game's +Z). The
# thread is 3 cm long as built (L0); the game stretches it. A topper's origin is the mouth of its socket; a
# garland piece runs from its origin 10 cm along +X.
#
# The two paint pictures are not colours but four amounts, the same in both, so one shader draws everything in
# any colours:   R how light (1 the colour as given, less for shading, grain, lines)
#                G how much of the ornament's second colour (0 its first colour, 1 its second)
#                B how much white (icing, snow, frost, fluff)
#                A glitter (stored as 0.2 + 0.8 x amount, so no pixel is fully clear)
# Each mesh has two materials: "glass" (its UVs run 0..1 over ONE design cell: the game picks the cell) and
# "paint" (its UVs point into ornament_paint.png). The second UV layer, "tags", carries per corner:
#   u = (4 x part + 2 x glitter + 0.5 + hang) / 16     part 0 body, 1 metal cap and wire, 2 thread
#                                                      hang 0 at the top of the thread .. 1 at its foot and below
#   v = 1 - gloss                                      (the glTF exporter flips v: the game reads gloss)
#
# Every closed part is checked for inside-out faces (a ray from each triangle along its normal must leave the part
# an even number of times, and its signed volume must be positive); the script stops with an error if any fails.

import bpy
import bmesh
import math
import os
import sys
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from mathutils.geometry import tessellate_polygon

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

GLASS, PAINT = 0, 1
BODY, CAP, THREAD = 0, 1, 2
L0 = 0.03                      # the thread's length as built
CAP_TOP = -L0 - 0.0045         # the top of a glass ornament's metal cap (its wire loop reaches up to -L0)
CAP_H = 0.009
GLASS_TOP = CAP_TOP - CAP_H + 0.002   # the top of the glass neck, inside the cap
NECK = 0.0075                  # the neck's radius
TAU = math.tau


# =============================================================================================== painting
class Sheet:
    def __init__(self, name, w, h):
        self.name, self.w, self.h = name, w, h
        self.px = np.zeros((h, w, 4), np.float32)   # rows from the top down
        self.px[..., 0] = 1.0

    def image(self, name, px):
        img = bpy.data.images.new(name, px.shape[1], px.shape[0], alpha=True)
        img.alpha_mode = "STRAIGHT"
        img.pixels.foreach_set(np.clip(px[::-1], 0.0, 1.0).astype(np.float32).ravel())
        return img

    def save(self):
        out = self.px.copy()
        out[..., 3] = 0.2 + 0.8 * out[..., 3]
        img = self.image(self.name, out)
        img.filepath_raw = os.path.join(TEXTURES, self.name + ".png")
        img.file_format = "PNG"
        img.save()
        bpy.data.images.remove(img)


def decode(px, a, b):
    """What the game's shader makes of the four amounts, in colours `a` and `b`."""
    a, b = np.array(a, np.float32), np.array(b, np.float32)
    col = a[None, None, :] * (1.0 - px[..., 1:2]) + b[None, None, :] * px[..., 1:2]
    col = col * (1.0 - px[..., 2:3]) + px[..., 2:3]
    col = col * px[..., 0:1]
    return np.concatenate([col, np.ones_like(px[..., 0:1])], axis=2)


class Cell:
    """A rectangle of a sheet, in pixels from the top left."""

    def __init__(self, sheet, x, y, w, h):
        self.sheet, self.x, self.y, self.w, self.h = sheet, x, y, w, h
        self.cx = self.cz = 0.0
        self.s = 1.0

    def view(self):
        return self.sheet.px[self.y:self.y + self.h, self.x:self.x + self.w]

    def grid(self):
        return np.meshgrid((np.arange(self.w) + 0.5) / self.w, (np.arange(self.h) + 0.5) / self.h)

    def uv(self, fx, fy):
        """Blender UV of a point of the cell (fx across, fy down from its top)."""
        return ((self.x + fx * self.w) / self.sheet.w, 1.0 - (self.y + fy * self.h) / self.sheet.h)

    def fit(self, pts, margin=12):
        """Lays a flat shape (x, z in metres) into the cell, as large as fits."""
        xs, zs = [p[0] for p in pts], [p[1] for p in pts]
        self.cx, self.cz = (min(xs) + max(xs)) * 0.5, (min(zs) + max(zs)) * 0.5
        self.s = min((self.w - 2 * margin) / (max(xs) - min(xs)), (self.h - 2 * margin) / (max(zs) - min(zs)))
        return self

    def model(self):
        """Each pixel's place on the flat shape, in metres, and a pixel's size."""
        fx, fy = self.grid()
        return self.cx + (fx - 0.5) * self.w / self.s, self.cz - (fy - 0.5) * self.h / self.s, 1.0 / self.s

    def muv(self, x, z):
        return self.uv(0.5 + (x - self.cx) * self.s / self.w, 0.5 - (z - self.cz) * self.s / self.h)

    def put(self, mask, lum=None, two=None, white=None, glit=None):
        v = self.view()
        m = np.clip(mask, 0.0, 1.0)
        for ch, val in ((0, lum), (1, two), (2, white), (3, glit)):
            if val is not None:
                v[..., ch] = v[..., ch] * (1.0 - m) + val * m

    def mul(self, k):
        self.view()[..., 0] *= k


def noise(shape, cells, seed, wrap=False):
    rng = np.random.default_rng(seed)
    h, w = shape
    gy, gx = cells
    g = rng.random((gy + 2, gx + 2)).astype(np.float32)
    if wrap:
        g[:, gx] = g[:, 0]
        g[:, gx + 1] = g[:, 1]
    ys = np.linspace(0, gy, h, endpoint=False)
    xs = np.linspace(0, gx, w, endpoint=False)
    y0, x0 = ys.astype(int), xs.astype(int)
    ty, tx = (ys - y0)[:, None], (xs - x0)[None, :]
    ty, tx = ty * ty * (3 - 2 * ty), tx * tx * (3 - 2 * tx)
    a, b = g[y0][:, x0], g[y0][:, x0 + 1]
    c, d = g[y0 + 1][:, x0], g[y0 + 1][:, x0 + 1]
    return (a * (1 - tx) + b * tx) * (1 - ty) + (c * (1 - tx) + d * tx) * ty


def aa(d, px):
    """1 inside a shape whose signed distance is `d` (negative inside), softened over a pixel."""
    return np.clip(0.5 - d / px, 0.0, 1.0)


def rim(d, w):
    """1 at a shape's edge (and outside it), fading to 0 a distance `w` inside."""
    return 1.0 - np.clip(-d / w, 0.0, 1.0)


def seg(X, Y, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    t = np.clip(((X - ax) * dx + (Y - ay) * dy) / (dx * dx + dy * dy + 1e-20), 0.0, 1.0)
    return np.hypot(X - ax - t * dx, Y - ay - t * dy)


def poly(X, Y, pts):
    """Signed distance to a polygon (negative inside)."""
    d = np.full(X.shape, 1e9, np.float32)
    inside = np.zeros(X.shape, bool)
    n = len(pts)
    for i in range(n):
        ax, ay = pts[i]
        bx, by = pts[(i + 1) % n]
        d = np.minimum(d, seg(X, Y, ax, ay, bx, by))
        if ay != by:
            cross = ((ay > Y) != (by > Y)) & (X < (bx - ax) * (Y - ay) / (by - ay) + ax)
            inside ^= cross
    return np.where(inside, -d, d)


def star_pts(R, r, n=5, turn=math.pi / 2, cx=0.0, cy=0.0):
    return [(cx + (R if i % 2 == 0 else r) * math.cos(turn + math.pi * i / n),
             cy + (R if i % 2 == 0 else r) * math.sin(turn + math.pi * i / n)) for i in range(2 * n)]


def flake_d(X, Y, size):
    """Distance to the lines of a six-armed snowflake with two pairs of barbs an arm."""
    ang = np.arctan2(Y, X)
    r = np.hypot(X, Y)
    a = (ang + math.pi / 6) % (math.pi / 3) - math.pi / 6
    s, t = r * np.cos(a), np.abs(r * np.sin(a))
    d = seg(s, t, 0, 0, size, 0)
    for at, ln in ((0.45, 0.28), (0.72, 0.18)):
        d = np.minimum(d, seg(s, t, at * size, 0, (at + ln * 0.5) * size, ln * 0.87 * size))
    return d


# ----------------------------------------------------------------------------------------------- the glass designs
DESIGN_W, DESIGN_H, DESIGN_N = 512, 256, 16
designs = Sheet("ornament_designs", DESIGN_W, DESIGN_H * DESIGN_N)
D_PLAIN, D_BANDS, D_DOTS, D_STARS, D_FLAKES, D_GLITTER, D_SNOWCAP, D_SWIRLS, D_STRIPES, D_ZIGZAG, D_TREES, \
    D_HARLEQUIN, D_ANTIQUE, D_ICE, D_TINSEL, D_SPARE = range(16)


def paint_designs():
    PX = math.pi / DESIGN_H     # a pixel, in radians of the ball

    def cell(i):
        c = Cell(designs, 0, i * DESIGN_H, DESIGN_W, DESIGN_H)
        fx, fy = c.grid()
        return c, fx, fy

    def local(fx, fy, u0, v0):
        d = (fx - u0 + 0.5) % 1.0 - 0.5
        return d * TAU * np.sin(np.clip(fy, 0.04, 0.96) * math.pi), (v0 - fy) * math.pi

    def band(fy, lo, hi):
        return aa(np.abs(fy - (lo + hi) * 0.5) * math.pi - (hi - lo) * 0.5 * math.pi, PX)

    # plain: only the faintest unevenness, as a dipped ball has
    c, fx, fy = cell(D_PLAIN)
    c.put(1.0, lum=0.95 + 0.05 * noise(fx.shape, (3, 6), 1, True))

    c, fx, fy = cell(D_BANDS)
    c.put(band(fy, 0.40, 0.60), two=1.0)
    for v in (0.375, 0.625):
        c.put(band(fy, v - 0.008, v + 0.008), white=1.0, two=0.0)
    for v in (0.30, 0.70):
        c.put(band(fy, v - 0.006, v + 0.006), two=1.0)
    for k in range(12):   # a row of small first-colour dots along the band
        x, y = local(fx, fy, (k + 0.5) / 12, 0.5)
        c.put(aa(np.hypot(x, y) - 0.085, PX), two=0.0, lum=0.92)

    c, fx, fy = cell(D_DOTS)
    for (v, n, off, r) in ((0.26, 5, 0.0, 0.15), (0.5, 8, 0.5, 0.17), (0.74, 5, 0.5, 0.15)):
        for k in range(n):
            x, y = local(fx, fy, (k + off) / n, v)
            c.put(aa(np.hypot(x, y) - r, PX), two=1.0)
    for (v, n, off) in ((0.38, 8, 0.0), (0.62, 8, 0.0)):
        for k in range(n):
            x, y = local(fx, fy, (k + off) / n, v)
            c.put(aa(np.hypot(x, y) - 0.05, PX), white=1.0)

    c, fx, fy = cell(D_STARS)
    for k in range(6):
        x, y = local(fx, fy, (k + 0.5) / 6, 0.5)
        c.put(aa(poly(x, y, star_pts(0.30, 0.125)), PX), two=1.0)
        for (v, off) in ((0.27, 0.0), (0.73, 0.0)):   # four-pointed sparks above and below, between the stars
            x, y = local(fx, fy, (k + off) / 6, v)
            c.put(aa(poly(x, y, star_pts(0.13, 0.035, 4)), PX), white=1.0)
            x, y = local(fx, fy, (k + 0.5) / 6, v + (0.07 if v > 0.5 else -0.07))
            c.put(aa(np.hypot(x, y) - 0.035, PX), white=1.0)

    c, fx, fy = cell(D_FLAKES)
    for k in range(5):
        x, y = local(fx, fy, (k + 0.5) / 5, 0.5)
        c.put(aa(flake_d(x, y, 0.40) - 0.028, PX), white=1.0)
        c.put(aa(np.hypot(x, y) - 0.07, PX), white=1.0)
        for (v, off, r) in ((0.24, 0.0, 0.05), (0.76, 0.0, 0.05), (0.33, 0.27, 0.03), (0.67, 0.73, 0.03)):
            x, y = local(fx, fy, (k + off) / 5, v)
            c.put(aa(np.hypot(x, y) - r, PX), white=1.0)

    c, fx, fy = cell(D_GLITTER)
    wave = 0.012 * np.sin(fx * TAU * 12)
    inside = aa((np.abs(fy - 0.5) - 0.14 - wave) * math.pi, PX)
    grit = noise(fx.shape, (128, 256), 5, True)
    c.put(inside, two=0.75, white=0.25 + 0.3 * grit, glit=1.0, lum=0.8 + 0.2 * grit)
    for sgn in (-1, 1):
        edge = (np.abs((fy - 0.5) * sgn - 0.17 - wave) - 0.008) * math.pi
        c.put(aa(edge, PX), two=1.0, white=0.0, glit=0.0, lum=1.0)
        for k in range(12):
            x, y = local(fx, fy, (k + 0.25) / 12, 0.5 + sgn * 0.235)
            c.put(aa(np.hypot(x, y) - 0.045, PX), white=1.0)

    c, fx, fy = cell(D_SNOWCAP)
    line = 0.36 + 0.05 * np.sin(fx * TAU * 5) + 0.025 * np.sin(fx * TAU * 13 + 1.0) + 0.02 * np.sin(fx * TAU * 3 + 2)
    grit = noise(fx.shape, (128, 256), 6, True)
    c.put(aa((fy - line) * math.pi, PX * 1.5), white=0.92, glit=0.75, lum=0.92 + 0.08 * grit)
    c.put(aa((np.abs(fy - line - 0.012) - 0.01) * math.pi, PX * 2), lum=0.86)     # a soft shadow under the snow
    rng = np.random.default_rng(11)
    for k in range(46):    # flakes drifting down the rest
        u, v, r = rng.random(), 0.42 + 0.5 * rng.random() ** 1.5, 0.018 + 0.03 * rng.random()
        x, y = local(fx, fy, u, v)
        c.put(aa(np.hypot(x, y) - r, PX), white=1.0, glit=0.5)

    c, fx, fy = cell(D_SWIRLS)
    for k in range(6):
        up = k % 2 == 0
        x, y = local(fx, fy, (k + 0.5) / 6, 0.47 if up else 0.53)
        if not up:
            x, y = -x, -y
        d = np.full(fx.shape, 1e9, np.float32)
        last = None
        for i in range(34):    # a curl, wound in from a tail below
            th = 0.6 + i * 0.26
            rr = 0.035 * th
            p = (rr * math.cos(th), rr * math.sin(th) + 0.05)
            if last:
                d = np.minimum(d, seg(x, y, last[0], last[1], p[0], p[1]))
            last = p
        d = np.minimum(d, seg(x, y, last[0], last[1], last[0] + 0.02, -0.52))
        c.put(aa(d - 0.03, PX), two=1.0)
        c.put(aa(np.hypot(x, y - 0.05) - 0.04, PX), white=1.0, two=0.0)
        for (px_, py_) in ((0.36, 0.30), (-0.36, -0.10), (0.33, -0.36)):
            c.put(aa(np.hypot(x - px_, y - py_) - 0.04, PX), white=1.0)
    for v in (0.13, 0.87):
        c.put(band(fy, v - 0.006, v + 0.006), white=1.0)

    c, fx, fy = cell(D_STRIPES)
    f = (fx * 10.0) % 1.0
    wide = 0.5 * np.sin(np.clip(fy, 0.0, 1.0) * math.pi) ** 0.25
    c.put(aa((np.abs(f - 0.5) - wide * 0.5) * 0.6, PX * 0.6), two=1.0)
    c.put(aa((np.abs(np.abs(f - 0.5) - wide * 0.5) - 0.035) * 0.6, PX * 0.6), white=1.0, two=0.0)

    c, fx, fy = cell(D_ZIGZAG)
    tri = np.abs(((fx * 12.0) % 1.0) - 0.5) * 2.0
    zig = 0.5 + (tri - 0.5) * 0.14
    c.put(aa((np.abs(fy - zig) - 0.014) * math.pi, PX), white=1.0)
    c.put(aa((np.abs(fy - zig - 0.05) - 0.007) * math.pi, PX), two=1.0)
    c.put(aa((np.abs(fy - zig + 0.05) - 0.007) * math.pi, PX), two=1.0)
    for v in (0.30, 0.70):
        c.put(band(fy, v - 0.02, v + 0.02), two=1.0)
        c.put(band(fy, v - 0.032, v - 0.026), white=1.0)
        c.put(band(fy, v + 0.026, v + 0.032), white=1.0)
    for k in range(12):
        for (v, off) in ((0.385, 0.5), (0.615, 0.0)):
            x, y = local(fx, fy, (k + off) / 12, v)
            c.put(aa(np.hypot(x, y) - 0.04, PX), white=1.0)
    for k in range(16):
        for v in (0.30, 0.70):
            x, y = local(fx, fy, (k + 0.5) / 16, v)
            c.put(aa(np.abs(x) + np.abs(y) - 0.045, PX), white=1.0, two=0.0)

    c, fx, fy = cell(D_TREES)
    ground = 0.66 + 0.012 * np.sin(fx * TAU * 6) + 0.008 * np.sin(fx * TAU * 17)
    for k in range(6):
        x, y = local(fx, fy, (k + 0.5) / 6, 0.5)
        tree = np.minimum(poly(x, y, [(-0.26, -0.40), (0.26, -0.40), (0, -0.06)]),
                          np.minimum(poly(x, y, [(-0.21, -0.19), (0.21, -0.19), (0, 0.14)]),
                                     poly(x, y, [(-0.15, 0.02), (0.15, 0.02), (0, 0.33)])))
        c.put(aa(tree, PX), two=1.0)
        c.put(aa(seg(x, y, 0, -0.5, 0, -0.40) - 0.03, PX), two=1.0, lum=0.55)
        c.put(aa(poly(x, y, star_pts(0.085, 0.035, 5, math.pi / 2, 0.0, 0.40)), PX), white=1.0, two=0.0)
        for (px_, py_) in ((-0.10, -0.30), (0.09, -0.26), (-0.05, -0.08), (0.06, 0.12), (0.0, -0.33)):
            c.put(aa(np.hypot(x - px_, y - py_) - 0.022, PX), white=1.0, two=0.0)
        for (off, v, r) in ((0.0, 0.33, 0.035), (0.0, 0.47, 0.025), (0.12, 0.24, 0.03), (-0.1, 0.20, 0.022)):
            x, y = local(fx, fy, (k + off) / 6, v)
            c.put(aa(np.hypot(x, y) - r, PX), white=1.0)
    grit = noise(fx.shape, (128, 256), 9, True)
    c.put(aa((ground - fy) * math.pi, PX * 1.5), white=0.9, two=0.0, glit=0.6, lum=0.93 + 0.07 * grit)

    c, fx, fy = cell(D_HARLEQUIN)
    a_, b_ = fx * 8.0 + (fy - 0.5) * 5.0, fx * 8.0 - (fy - 0.5) * 5.0
    check = (np.floor(a_) + np.floor(b_)) % 2.0
    zone = band(fy, 0.16, 0.84)
    c.put(zone * check, two=1.0)
    edge = np.minimum(np.abs((a_ % 1.0) - 0.5) - 0.5, np.abs((b_ % 1.0) - 0.5) - 0.5)
    c.put(zone * aa((np.abs(edge) - 0.035) * 0.3, PX * 0.6), white=1.0, two=0.0)
    for v in (0.16, 0.84):
        c.put(band(fy, v - 0.012, v + 0.012), white=1.0, two=0.0)

    # antique: old mercury glass, mottled and foxed, with a fine sparkle
    c, fx, fy = cell(D_ANTIQUE)
    big, small = noise(fx.shape, (10, 20), 21, True), noise(fx.shape, (40, 80), 22, True)
    c.put(1.0, lum=0.78 + 0.22 * big, white=0.18 * small)
    c.put(aa(0.30 - big * small, 0.08), lum=0.62)
    c.put(aa(small - 0.16, 0.04), lum=0.5, white=0.0)
    c.put(aa(0.86 - small, 0.03), white=0.7, glit=0.6)

    # ice, for icicles: long streaks and frost
    c, fx, fy = cell(D_ICE)
    streak = noise(fx.shape, (3, 48), 31, True)
    c.put(1.0, lum=0.86 + 0.14 * streak, white=0.25 + 0.5 * streak * noise(fx.shape, (24, 12), 32, True), glit=0.35)

    # tinsel: every strand its own brightness (fx runs round a bristle disc, fy from its middle to its points)
    c, fx, fy = cell(D_TINSEL)
    strand = noise(fx.shape, (2, 96), 41, True)
    c.put(1.0, lum=0.55 + 0.45 * strand, white=0.45 * (strand > 0.6), glit=1.0)

    c, fx, fy = cell(D_SPARE)
    c.put(1.0, lum=1.0)


# ----------------------------------------------------------------------------------------------- the paint atlas
paint = Sheet("ornament_paint", 1024, 1024)
(P_WOOD, P_HEART, P_FLAKE, P_GINGER, P_MITTEN, P_STOCKING, P_DOUGH, P_HORSE, P_PAPER, P_DRUM, P_BELL, P_CONE,
 P_CANE, P_BURST, P_STARTOP, P_BITS) = range(16)
CELLS = [Cell(paint, (i % 4) * 256, (i // 4) * 256, 256, 256) for i in range(16)]
BIT_X, BIT_Y = 768, 768
BIT_METAL = Cell(paint, BIT_X, BIT_Y, 256, 64)
BIT_THREAD = Cell(paint, BIT_X, BIT_Y + 64, 256, 32)
BIT_STRAW = Cell(paint, BIT_X, BIT_Y + 96, 256, 64)
BIT_BEAD_A = Cell(paint, BIT_X, BIT_Y + 160, 128, 96)
BIT_BEAD_B = Cell(paint, BIT_X + 128, BIT_Y + 160, 128, 96)

# The colours each kind wears unless the game says otherwise (the game's table is in ornament_set.gd: keep them
# alike). Only used here for the pictures Blender shows.
WOOD, GOLD, RED, GREEN, CREAM = (0.86, 0.66, 0.42), (0.95, 0.72, 0.25), (0.82, 0.10, 0.09), (0.10, 0.45, 0.16), (0.95, 0.90, 0.78)
SHOW = {P_WOOD: (WOOD, RED), P_HEART: (RED, CREAM), P_FLAKE: ((0.82, 0.90, 1.0), CREAM), P_GINGER: ((0.70, 0.43, 0.20), RED),
        P_MITTEN: (RED, GREEN), P_STOCKING: (GREEN, RED), P_DOUGH: ((0.93, 0.86, 0.72), RED), P_HORSE: (RED, GREEN),
        P_PAPER: (CREAM, RED), P_DRUM: (RED, GOLD), P_BELL: (GOLD, RED), P_CONE: ((0.58, 0.37, 0.20), CREAM),
        P_CANE: (RED, GREEN), P_BURST: (RED, GOLD), P_STARTOP: (GOLD, RED), P_BITS: (GOLD, CREAM)}

# The flat shapes, in metres (x across, z up), shared by the models and their paint.
def mirror(half):
    """A whole outline from its right half, listed from the top of the middle line to the bottom of it."""
    left = [(-x, z) for (x, z) in reversed(half) if abs(x) > 1e-9]
    return half + left


def scaled(pts, k, dx=0.0, dz=0.0):
    return [(x * k + dx, z * k + dz) for (x, z) in pts]


def top_at(pts, z):
    """Moves an outline so that its highest point is at height z, its middle on x = 0."""
    hi = max(p[1] for p in pts)
    return [(x, zz - hi + z) for (x, zz) in pts]


STAR_OUT = top_at(star_pts(0.036, 0.0165), -L0 + 0.004)
STAR_C = (0.0, STAR_OUT[0][1] - 0.036)

HEART_OUT = [(16 * math.sin(t) ** 3, 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
             for t in [TAU * i / 28 for i in range(28)]]
HEART_OUT = scaled(HEART_OUT, 0.0019)
HEART_OUT = [(x, z - 0.0095 - L0 - 0.001) for (x, z) in HEART_OUT]       # the dip between the lobes under the thread
HEART_C = (0.0, -L0 - 0.001 - 0.0095)

GINGER_K = 0.0095
GINGER_OUT = top_at(scaled(mirror([
    (0, 4.0), (0.63, 3.83), (1.08, 3.38), (1.25, 2.75), (1.08, 2.12), (0.72, 1.73), (0.66, 1.55), (1.3, 1.5),
    (2.3, 1.75), (2.95, 1.55), (3.05, 1.1), (2.6, 0.75), (1.5, 0.6), (1.1, 0.35), (1.05, -0.6), (1.25, -1.3),
    (1.75, -2.5), (2.05, -3.2), (1.85, -3.75), (1.2, -3.85), (0.75, -3.4), (0.45, -2.0), (0, -1.5)]), GINGER_K),
    -L0 + 0.003)
GINGER_O = (0.0, GINGER_OUT[0][1] - 4.0 * GINGER_K)     # where the drawing's (0, 0) landed


def ginger(x, z):
    return (GINGER_O[0] + x * GINGER_K, GINGER_O[1] + z * GINGER_K)


MITT_K = 0.0105
MITT_BODY = [(-1.2, 2.0), (1.2, 2.0), (1.3, 1.2), (1.85, 1.05), (2.4, 0.5), (2.6, -0.2), (2.3, -0.75), (1.75, -0.6),
             (1.5, -0.1), (1.5, -1.2), (1.35, -2.0), (0.9, -2.6), (0, -2.85), (-0.9, -2.6), (-1.4, -2.0), (-1.5, -1.0),
             (-1.4, 0.5)]
MITT_CUFF = [(-1.38, 2.1), (-1.25, 1.95), (1.25, 1.95), (1.38, 2.1), (1.38, 2.9), (1.25, 3.05), (-1.25, 3.05), (-1.38, 2.9)]
MITT_DZ = -L0 + 0.004 - 3.05 * MITT_K
MITT_BODY, MITT_CUFF = scaled(MITT_BODY, MITT_K, 0, MITT_DZ), scaled(MITT_CUFF, MITT_K, 0, MITT_DZ)


def mitt(x, z):
    return (x * MITT_K, z * MITT_K + MITT_DZ)


SOCK_K = 0.0105
SOCK_BODY = [(-1.0, 2.25), (1.0, 2.25), (1.0, -0.6), (1.6, -1.3), (2.6, -1.7), (3.0, -2.3), (2.8, -3.0), (2.0, -3.3),
             (0.2, -3.3), (-0.8, -3.0), (-1.25, -2.2), (-1.1, -1.0)]
SOCK_CUFF = [(-1.2, 2.3), (-1.07, 2.15), (1.07, 2.15), (1.2, 2.3), (1.2, 3.1), (1.07, 3.25), (-1.07, 3.25), (-1.2, 3.1)]
SOCK_DX, SOCK_DZ = 0.9 * SOCK_K, -L0 + 0.004 - 3.25 * SOCK_K     # hung by its back corner
SOCK_BODY, SOCK_CUFF = scaled(SOCK_BODY, SOCK_K, SOCK_DX, SOCK_DZ), scaled(SOCK_CUFF, SOCK_K, SOCK_DX, SOCK_DZ)


def sock(x, z):
    return (x * SOCK_K + SOCK_DX, z * SOCK_K + SOCK_DZ)


def round_star(R, r, steps):
    """A five-pointed star with rounded points and dips, as cut from dough."""
    pts = []
    for i in range(10):
        a = math.pi / 2 + math.pi * i / 5
        rad, fillet = (R, 0.30 * r) if i % 2 == 0 else (r, 0.22 * r)
        cx, cy = (rad - fillet if i % 2 == 0 else rad + fillet) * math.cos(a), \
                 (rad - fillet if i % 2 == 0 else rad + fillet) * math.sin(a)
        n = steps if i % 2 == 0 else max(1, steps - 1)
        span = math.radians(110 if i % 2 == 0 else 70)
        for s in range(n):
            t = (s / (n - 1) - 0.5) if n > 1 else 0.0
            b = a + t * span if i % 2 == 0 else a + math.pi - t * span
            pts.append((cx + fillet * math.cos(b), cy + fillet * math.sin(b)))
    return pts


DOUGH_R = 0.034
DOUGH_OUT = top_at(round_star(DOUGH_R, 0.017, 4), -L0 + 0.0075)
DOUGH_OUT_LO = top_at(star_pts(DOUGH_R, 0.016), -L0 + 0.0075)
DOUGH_C = (0.0, -L0 + 0.0075 - DOUGH_R)
DOUGH_HOLE = [(0.0028 * math.cos(TAU * i / 6), -L0 - 0.0012 + 0.0028 * math.sin(TAU * i / 6)) for i in range(6)]

HORSE_K = 0.0098
HORSE_OUT = [(-3.4, -2.2), (-2.4, -3.0), (-1.0, -3.45), (0.2, -3.55), (1.4, -3.4), (2.7, -2.95), (3.6, -2.15),
             (3.3, -1.95), (2.75, -2.45), (2.2, -1.3), (1.75, -0.2), (1.9, 0.9), (2.5, 1.7), (3.3, 1.55), (3.6, 1.95),
             (3.3, 2.5), (2.75, 2.95), (2.65, 3.45), (2.3, 3.0), (1.5, 2.2), (0.9, 1.2), (-0.4, 0.95), (-1.6, 1.15),
             (-2.2, 0.9), (-3.0, 0.6), (-3.35, -0.5), (-2.8, -0.3), (-2.3, 0.2), (-2.2, -0.6), (-2.75, -1.6),
             (-2.9, -2.5)]
HORSE_HOLE = [(-2.0, -2.6), (-1.0, -2.95), (0.2, -3.05), (1.3, -2.9), (1.95, -2.6), (1.0, -0.85), (-0.2, -1.05),
              (-1.3, -0.85)]
HORSE_DX, HORSE_DZ = 0.2 * HORSE_K, -L0 + 0.003 - 1.05 * HORSE_K   # hung from the middle of its back
HORSE_OUT, HORSE_HOLE = scaled(HORSE_OUT, HORSE_K, HORSE_DX, HORSE_DZ), scaled(HORSE_HOLE, HORSE_K, HORSE_DX, HORSE_DZ)


def horse(x, z):
    return (x * HORSE_K + HORSE_DX, z * HORSE_K + HORSE_DZ)


PAPER_R, PAPER_r = 0.040, 0.0165
PAPER_OUT = top_at(star_pts(PAPER_R, PAPER_r), -L0 + 0.004)
PAPER_C = (0.0, -L0 + 0.004 - PAPER_R)

TOP_R, TOP_r = 0.066, 0.028
TOP_C = (0.0, 0.052 + TOP_R * math.cos(math.radians(36)) - 0.012)
TOP_OUT = star_pts(TOP_R, TOP_r, 5, math.pi / 2, TOP_C[0], TOP_C[1])


def flake_outline(R, w, barbs):
    pts = []
    s0 = w * 1.732
    for k in range(6):
        phi = math.pi / 2 + k * math.pi / 3
        arm = [(s0, -w)]
        marks = ((0.43 * R, 0.30 * R), (0.70 * R, 0.19 * R)) if barbs else ()
        back = []
        for (at, ln) in marks:
            bw = 0.0016
            arm += [(at - bw, -w), (at + ln * 0.5, -w - ln * 0.87), (at + bw, -w)]
            back = [(at + bw, w), (at + ln * 0.5, w + ln * 0.87), (at - bw, w)] + back
        arm += [(R - 0.005, -w * 1.5), (R, 0.0), (R - 0.005, w * 1.5)] + back
        for (s, t) in arm:
            pts.append((s * math.cos(phi) - t * math.sin(phi), s * math.sin(phi) + t * math.cos(phi)))
    return pts


FLAKE_R = 0.036
FLAKE_OUT = top_at(flake_outline(FLAKE_R, 0.0022, True), -L0 + 0.004)
FLAKE_OUT_LO = top_at(flake_outline(FLAKE_R, 0.0026, False), -L0 + 0.004)
FLAKE_C = (0.0, -L0 + 0.004 - FLAKE_R)

BURST_R = 0.0235      # the rim of a reflector ball's dent


def paint_atlas():
    def edge_dashes(c, X, Z, d, px, centre, count, inner, outer, duty=0.45):
        """Stitches round an edge: short dashes across the band between two distances inside it."""
        ang = np.arctan2(Z - centre[1], X - centre[0])
        dash = ((ang / TAU * count) % 1.0) < duty
        return aa(np.abs(d + (inner + outer) * 0.5) - (inner - outer) * 0.5, px) * dash

    # --- wooden star: grain, a darker sawn edge, a painted line and dots
    c = CELLS[P_WOOD].fit(STAR_OUT)
    X, Z, px = c.model()
    d = poly(X, Z, STAR_OUT)
    grain = noise(X.shape, (5, 70), 51)
    rings = 0.5 + 0.5 * np.sin(Z * 2600 + 6 * noise(X.shape, (4, 6), 52))
    c.put(1.0, lum=0.86 + 0.09 * grain + 0.05 * rings)
    c.put(rim(d, 0.0022), lum=0.62)                                                   # the sawn edge
    inner = poly(X, Z, star_pts(0.024, 0.011, 5, math.pi / 2, STAR_C[0], STAR_C[1]))
    c.put(aa(np.abs(inner) - 0.0009, px), two=1.0, lum=0.95)
    c.put(aa(np.hypot(X - STAR_C[0], Z - STAR_C[1]) - 0.0042, px), white=0.9, lum=1.0)
    for (x, z) in star_pts(0.0115, 0.0115, 5, math.pi / 2, STAR_C[0], STAR_C[1])[::2]:
        c.put(aa(np.hypot(X - x, Z - z) - 0.0017, px), two=1.0, lum=0.95)

    # --- felt heart: fibres, a pillowed edge, blanket stitch, an embroidered star
    c = CELLS[P_HEART].fit(HEART_OUT)
    X, Z, px = c.model()
    d = poly(X, Z, HEART_OUT)
    c.put(1.0, lum=0.84 + 0.16 * noise(X.shape, (90, 90), 53))
    c.put(rim(d, 0.007) * 0.8, lum=0.66)
    c.put(edge_dashes(c, X, Z, d, px, (HEART_C[0], HEART_C[1] - 0.004), 34, 0.0052, 0.0006, 0.3), two=1.0, lum=1.0)
    c.put(aa(np.abs(d + 0.0052) - 0.0005, px), two=1.0, lum=1.0)
    mid = (0.0, HEART_C[1] - 0.002)
    c.put(aa(flake_d(X - mid[0], Z - mid[1], 0.0095) - 0.0009, px), two=1.0, lum=1.0)
    c.put(aa(np.hypot(X - mid[0], Z - mid[1]) - 0.0022, px), two=1.0, lum=1.0)

    # --- snowflake: frosted white with a line down each arm
    c = CELLS[P_FLAKE].fit(FLAKE_OUT)
    X, Z, px = c.model()
    c.put(1.0, lum=1.0, white=0.82, glit=0.8)
    c.put(aa(flake_d(Z - FLAKE_C[1], X - FLAKE_C[0], FLAKE_R * 0.93) - 0.0006, px), lum=0.8, white=0.5)

    # --- gingerbread man: baked biscuit, icing cuffs, a face, two buttons
    c = CELLS[P_GINGER].fit(GINGER_OUT)
    X, Z, px = c.model()
    d = poly(X, Z, GINGER_OUT)
    speck = noise(X.shape, (120, 120), 54)
    c.put(1.0, lum=0.86 + 0.14 * noise(X.shape, (14, 14), 55) - 0.25 * (speck > 0.86))
    c.put(rim(d, 0.004), lum=0.62)

    def icing_line(points, width=0.0011):
        dd = np.full(X.shape, 1e9, np.float32)
        for i in range(len(points) - 1):
            a, b = ginger(*points[i]), ginger(*points[i + 1])
            dd = np.minimum(dd, seg(X, Z, a[0], a[1], b[0], b[1]))
        c.put(aa(dd - width, px), white=1.0, lum=1.0)

    for sx in (-1, 1):
        icing_line([(sx * 2.25, 1.62), (sx * 2.42, 1.38), (sx * 2.22, 1.18), (sx * 2.40, 0.98), (sx * 2.25, 0.80)])
        icing_line([(sx * 0.66, -2.62), (sx * 0.98, -2.78), (sx * 1.22, -2.58), (sx * 1.50, -2.76), (sx * 1.78, -2.60)])
        e = ginger(sx * 0.45, 2.98)
        c.put(aa(np.hypot(X - e[0], Z - e[1]) - 0.0017, px), white=1.0, lum=1.0)
        c.put(aa(np.hypot(X - e[0], Z - e[1]) - 0.0009, px), white=0.0, lum=0.22)
    icing_line([(-0.55, 2.42), (-0.3, 2.22), (0.0, 2.15), (0.3, 2.22), (0.55, 2.42)], 0.0009)
    for z in (0.75, -0.25):
        e = ginger(0.0, z)
        c.put(aa(np.hypot(X - e[0], Z - e[1]) - 0.0036, px), two=1.0, lum=1.0)
        c.put(aa(np.hypot(X - e[0] + 0.001, Z - e[1] - 0.001) - 0.0011, px), white=0.8)
    icing_line([(-0.75, 1.42), (-0.4, 1.22), (0.0, 1.38), (0.4, 1.22), (0.75, 1.42)], 0.0009)

    # --- felt mitten and stocking: fibres, a fluffy white cuff, stitching, a motif
    def felt(c, body, cuff, mapf, centre):
        c.fit(body + cuff)
        X, Z, px = c.model()
        d = poly(X, Z, body)
        c.put(1.0, lum=0.84 + 0.16 * noise(X.shape, (90, 90), 56))
        c.put(rim(d, 0.006) * 0.8, lum=0.66)
        cz = mapf(*centre)
        c.put(edge_dashes(c, X, Z, d, px, cz, 44, 0.0042, 0.0022, 0.5), two=1.0, lum=1.0)
        dc = poly(X, Z, cuff)
        fluff = noise(X.shape, (60, 60), 57)
        c.put(aa(dc - 0.001, px), lum=0.86 + 0.14 * fluff, white=0.93, two=0.0, glit=0.15)
        c.put(aa(np.abs(dc - 0.001) - 0.0012, 0.002) * aa(dc - 0.0005, px), lum=0.8)
        return X, Z, px, d

    c = CELLS[P_MITTEN]
    X, Z, px, d = felt(c, MITT_BODY, MITT_CUFF, mitt, (0.0, -0.4))
    m = mitt(0.0, -0.55)
    c.put(aa(flake_d(X - m[0], Z - m[1], 0.0125) - 0.0010, px), white=1.0, lum=1.0)
    c.put(aa(np.hypot(X - m[0], Z - m[1]) - 0.0026, px), white=1.0, lum=1.0)
    for zz in (1.45, 1.2):
        a, b = mitt(-1.5, zz), mitt(1.5, zz)
        c.put(aa(seg(X, Z, a[0], a[1], b[0], b[1]) - 0.0007, px) * aa(d + 0.001, px), two=1.0, lum=1.0)

    c = CELLS[P_STOCKING]
    X, Z, px, d = felt(c, SOCK_BODY, SOCK_CUFF, sock, (0.3, -0.8))
    toe, heel = sock(2.9, -2.6), sock(-0.9, -2.75)
    c.put(aa(np.hypot(X - toe[0], Z - toe[1]) - 0.0125, px) * aa(d + 0.0005, px), two=1.0, lum=0.9)
    c.put(aa(np.hypot(X - heel[0], Z - heel[1]) - 0.011, px) * aa(d + 0.0005, px), two=1.0, lum=0.9)
    for (i, zz) in enumerate((1.6, 0.9, 0.2)):
        a, b = sock(-1.2, zz), sock(1.2, zz)
        dd = seg(X, Z, a[0], a[1], b[0], b[1])
        c.put(aa(dd - 0.0022, px) * aa(d + 0.0005, px), white=0.95, lum=1.0)
    for (i, xx) in enumerate((-0.6, 0.0, 0.6)):
        for zz in (1.25, 0.55):
            p = sock(xx + (0.3 if zz < 1 else 0.0), zz)
            c.put(aa(np.hypot(X - p[0], Z - p[1]) - 0.0016, px), two=1.0, lum=1.0)

    # --- salt-dough star: pale and floury, browner at the edge, painted dots
    c = CELLS[P_DOUGH].fit(DOUGH_OUT)
    X, Z, px = c.model()
    d = poly(X, Z, DOUGH_OUT)
    c.put(1.0, lum=0.9 + 0.1 * noise(X.shape, (20, 20), 58) - 0.1 * (noise(X.shape, (110, 110), 59) > 0.9))
    c.put(rim(d, 0.005), lum=0.74)
    for i in range(5):
        a = math.pi / 2 + i * TAU / 5
        for (rad, size) in ((0.0235, 0.0020), (0.0165, 0.0026)):
            if i == 0 and rad > 0.02:
                continue    # the hole is there
            x, z = DOUGH_C[0] + rad * math.cos(a), DOUGH_C[1] + rad * math.sin(a)
            c.put(aa(np.hypot(X - x, Z - z) - size, px), two=1.0, lum=0.95)
    c.put(aa(np.abs(np.hypot(X - DOUGH_C[0], Z - DOUGH_C[1]) - 0.0085) - 0.0008, px), two=1.0, lum=0.95)
    c.put(aa(np.hypot(X - DOUGH_C[0], Z - DOUGH_C[1]) - 0.003, px), white=1.0, lum=1.0)

    # --- rocking horse: a white painted horse, dark mane and tail, a saddle in the first colour, the rocker in
    # the second
    c = CELLS[P_HORSE].fit(HORSE_OUT)
    X, Z, px = c.model()
    d = poly(X, Z, HORSE_OUT)
    dapple = noise(X.shape, (26, 26), 60)
    c.put(1.0, lum=0.92 + 0.08 * noise(X.shape, (8, 8), 61) - 0.14 * np.clip((dapple - 0.6) * 5.0, 0, 1), white=0.88)
    c.put(rim(d, 0.003), lum=0.75)

    def hp(points):
        return [horse(*p) for p in points]

    mane = poly(X, Z, hp([(1.45, 2.3), (2.3, 3.1), (2.75, 3.0), (2.3, 2.45), (1.75, 1.6), (1.05, 1.1), (0.8, 1.3)]))
    tail = poly(X, Z, hp([(-2.1, 1.0), (-3.1, 0.7), (-3.45, -0.6), (-2.7, -0.3), (-2.25, 0.3)]))
    c.put(aa(np.minimum(mane, tail), px), white=0.0, lum=0.3)
    arc = 0.045 * (X - horse(0.1, 0)[0]) ** 2 / (HORSE_K * HORSE_K) * HORSE_K     # the rocker's curve
    rocker_top = horse(0, -2.98)[1] + arc
    c.put(aa(Z - rocker_top, px), white=0.0, two=1.0, lum=1.0)
    for xx in (-2.4, -1.2, 0.0, 1.2, 2.4):
        p = horse(xx + 0.1, -3.22 + 0.045 * xx * xx)
        c.put(aa(np.hypot(X - p[0], Z - p[1]) - 0.0013, px), white=1.0, two=0.0)
    saddle = hp([(-1.25, 1.2), (0.55, 1.15), (0.75, 0.2), (0.2, -0.15), (-0.9, -0.15), (-1.35, 0.3)])
    ds = poly(X, Z, saddle)
    c.put(aa(ds, px), white=0.0, two=0.0, lum=1.0)
    c.put(aa(np.abs(ds + 0.0018) - 0.0005, px), white=1.0)
    for (a, b) in (((2.35, 2.75), (3.05, 1.6)), ((2.45, 2.05), (3.45, 2.2))):      # the bridle
        a, b = horse(*a), horse(*b)
        c.put(aa(seg(X, Z, a[0], a[1], b[0], b[1]) - 0.0007, px) * aa(d, px), white=0.0, two=0.0, lum=1.0)
    eye = horse(2.95, 2.5)
    c.put(aa(np.hypot(X - eye[0], Z - eye[1]) - 0.0014, px), white=0.0, lum=0.15)
    for hoof in ((2.62, -2.3), (-2.78, -2.25)):
        p = horse(*hoof)
        c.put(aa(np.hypot(X - p[0], Z - p[1]) - 0.0042, px) * aa(rocker_top - Z, px), white=0.0, lum=0.3)

    # --- paper star: cream paper printed with dots and a border
    c = CELLS[P_PAPER].fit(PAPER_OUT)
    X, Z, px = c.model()
    d = poly(X, Z, PAPER_OUT)
    c.put(1.0, lum=0.9 + 0.1 * noise(X.shape, (40, 40), 62))
    gx, gz = (X / 0.0062) % 1.0 - 0.5, (Z / 0.0062 + 0.5 * np.floor(X / 0.0062)) % 1.0 - 0.5
    c.put(aa(np.hypot(gx, gz) * 0.0062 - 0.0011, px), two=1.0)
    c.put(aa(np.abs(d + 0.003) - 0.0008, px), two=1.0)
    c.put(aa(d + 0.0015, px) * -1 + 1, two=0.0)

    # --- drum: (fy down the picture) skin, hoop, the body with its zigzag cord, hoop, skin
    c = CELLS[P_DRUM]
    fx, fy = c.grid()
    c.put(1.0, lum=0.95 + 0.05 * noise(fx.shape, (20, 20), 63, True), white=0.85)
    c.put(aa(np.abs(fy - 0.5) - 0.42, 1 / 256), white=0.0, two=1.0, lum=0.85 + 0.15 * np.cos(fy * 256 * 0.9))
    c.put(aa(np.abs(fy - 0.5) - 0.33, 1 / 256), white=0.0, two=0.0, lum=0.92 + 0.08 * noise(fx.shape, (4, 60), 64, True))
    tri = np.abs(((fx * 6.0) % 1.0) - 0.5) * 2.0
    c.put(aa(np.abs(fy - (0.2 + 0.6 * tri)) * 256 / 6.0 * 0.35 - 0.8, 0.6) * aa(np.abs(fy - 0.5) - 0.33, 1 / 256), white=1.0)
    for k in range(12):
        dxx = ((fx - (k + 0.0) / 12 + 0.5) % 1.0 - 0.5) * 2.4
        c.put(aa(np.hypot(dxx, fy - (0.2 if k % 2 == 0 else 0.8)) - 0.028, 1 / 256), two=1.0, white=0.0)

    # --- bell: (fy down) the outside from crown to lip with turned lines and a row of dots, then the dark inside
    c = CELLS[P_BELL]
    fx, fy = c.grid()
    c.put(1.0, lum=0.92 + 0.08 * noise(fx.shape, (6, 40), 65, True))
    for (v, wdt, lm) in ((0.10, 0.008, 0.62), (0.13, 0.004, 0.7), (0.52, 0.006, 0.62), (0.56, 0.012, 0.7), (0.66, 0.006, 0.66)):
        c.put(aa(np.abs(fy - v) - wdt, 1 / 256), lum=lm)
    for k in range(10):
        dxx = ((fx - (k + 0.5) / 10 + 0.5) % 1.0 - 0.5) * 2.2
        c.put(aa(np.hypot(dxx, fy - 0.36) - 0.035, 1 / 256), two=1.0, lum=1.0)
        c.put(aa(np.hypot(dxx - 0.012, fy - 0.35) - 0.010, 1 / 256), white=0.7)
    c.put(aa(0.72 - fy, 1 / 256), lum=0.42, two=0.0, white=0.0)

    # --- pine cone: (fy down, sixteen steps from the stalk to the tip) each scale's top brown with a pale, snowy
    # lip, its underside dark
    c = CELLS[P_CONE]
    fx, fy = c.grid()
    step = fy * 15.0 + 1.0
    part = step % 2.0                        # 0..1 a scale's upper face (from its root out), 1..2 its underside
    face = np.clip(part, 0.0, 1.0)
    streak = noise(fx.shape, (6, 64), 66, True)
    c.put(1.0, lum=0.72 + 0.22 * face + 0.06 * streak)
    c.put(aa(0.6 - part, 0.08) * (part < 1.0), white=0.6 + 0.4 * streak, lum=1.0, glit=0.5)
    c.put(part >= 1.0, lum=0.6, white=0.0)

    # --- candy cane: (fx round, fy along) white with a wide stripe in the first colour and a thin one in the second
    c = CELLS[P_CANE]
    fx, fy = c.grid()
    f = (fy * 9.0 + fx) % 1.0
    c.put(1.0, lum=1.0, white=0.96)
    c.put(aa((np.abs(f - 0.25) - 0.17) / 9.0, 1 / 256), white=0.0, two=0.0)
    c.put(aa((np.abs(f - 0.72) - 0.04) / 9.0, 1 / 256), white=0.0, two=1.0)

    # --- the starburst pressed into a reflector ball: folds light and dark in the second colour
    c = CELLS[P_BURST].fit([(-BURST_R, -BURST_R), (BURST_R, BURST_R)])
    X, Z, px = c.model()
    ang, rad = np.arctan2(Z, X), np.hypot(X, Z) / BURST_R
    fold = 0.5 + 0.5 * np.cos(ang * 16)
    c.put(1.0, two=1.0, lum=0.55 + 0.45 * fold, white=0.35 * fold * np.clip(1.2 - rad, 0, 1), glit=0.5)
    c.put(aa(0.9 - rad, 0.03), lum=0.7)
    c.put(aa(rad - 0.16, 0.03), white=0.8, lum=1.0)

    # --- the star topper: glittering, with a ridge up each point and a painted edge
    c = CELLS[P_STARTOP].fit(TOP_OUT)
    X, Z, px = c.model()
    d = poly(X, Z, TOP_OUT)
    grit = noise(X.shape, (128, 128), 67)
    c.put(1.0, lum=0.8 + 0.2 * grit, white=0.12 * grit, glit=0.9)
    for (i, (x, z)) in enumerate(TOP_OUT):
        dd = seg(X, Z, TOP_C[0], TOP_C[1], x, z)
        c.put(aa(dd - 0.0012, 0.002), lum=1.0 if i % 2 == 0 else 0.6, white=0.45 if i % 2 == 0 else 0.0)
    c.put(aa(np.abs(d + 0.005) - 0.0011, px), two=1.0, lum=1.0, white=0.0, glit=0.3)
    c.put(aa(np.hypot(X - TOP_C[0], Z - TOP_C[1]) - 0.006, px), white=0.6, lum=1.0)

    # --- bits: crimped cap metal, twisted thread, straw, two beads
    c = BIT_METAL
    fx, fy = c.grid()
    c.put(1.0, lum=0.66 + 0.34 * (0.5 + 0.5 * np.cos(fx * TAU * 24)) ** 0.7, two=0.0, white=0.0)
    c.put(aa(np.abs(fy - 0.5) - 0.06, 1 / 64), lum=0.55)
    c.put(aa(0.12 - fy, 1 / 64), lum=0.6)
    c = BIT_THREAD
    fx, fy = c.grid()
    f = (fx * 24.0 + fy * 1.0) % 1.0
    c.put(1.0, lum=0.8 + 0.2 * np.cos(f * TAU), two=0.0, white=0.0)
    c.put(aa((np.abs(f - 0.5) - 0.25) / 24.0, 1 / 256), two=1.0)
    c = BIT_STRAW
    fx, fy = c.grid()
    c.put(1.0, lum=0.72 + 0.28 * noise(fx.shape, (24, 3), 68), two=0.0, white=0.0)
    c.put(aa(np.abs(fy - 0.5) - 0.44, 1 / 64) * -1 + 1, lum=0.6)
    for (c, two) in ((BIT_BEAD_A, 0.0), (BIT_BEAD_B, 1.0)):
        c.put(1.0, lum=1.0, two=two, white=0.0)


def paint_shine():
    """The room a shiny ball mirrors, looked up by the surface's direction as the eye sees it (x right, y up).
    R: the room (a dim ceiling, a dark far wall, a warm floor); G: the window's highlight and a small second
    catch-light; B: a pale rim light."""
    n = 128
    ys, xs = np.meshgrid(1.0 - (np.arange(n) + 0.5) / n * 2.0, (np.arange(n) + 0.5) / n * 2.0 - 1.0, indexing="ij")
    r = np.hypot(xs, ys)
    room = 0.16 + 0.10 * np.clip(ys, 0, 1)
    room = room * (1.0 - 0.55 * np.exp(-((ys - 0.02) / 0.16) ** 2))                  # the far wall's dark band
    room = room + 0.34 * np.exp(-((ys + 0.52) / 0.26) ** 2) * (1.0 - 0.35 * xs * xs)  # the floor, lit
    room = room + 0.22 * np.exp(-(((xs + 0.30) / 0.42) ** 2 + ((ys - 0.42) / 0.36) ** 2))   # the wall round the window
    room = room * np.clip((1.02 - r) / 0.25, 0, 1) ** 0.5
    # the window: four panes, bowed as a ball bows them
    wx, wy = xs + 0.36 + 0.22 * (ys - 0.40), ys - 0.40 - 0.10 * (xs + 0.36)
    bow = 1.0 + 0.6 * (wx * wx + wy * wy)
    wx, wy = wx * bow, wy * bow
    box_d = np.maximum(np.abs(wx) - 0.17, np.abs(wy) - 0.21)
    pane = np.clip(-box_d / 0.035, 0, 1) * np.clip((np.abs(wx) - 0.018) / 0.02, 0, 1) * np.clip((np.abs(wy) - 0.018) / 0.02, 0, 1)
    glow = 0.30 * np.exp(-np.clip(box_d, 0, 9) / 0.10) * (box_d > 0) + 0.3 * (box_d <= 0)
    window = np.clip(pane + glow * (1 - pane), 0, 1)
    window = window + 0.55 * np.exp(-(((xs - 0.44) / 0.07) ** 2 + ((ys + 0.46) / 0.05) ** 2))
    rim = np.clip((r - 0.80) / 0.16, 0, 1) * np.clip((1.0 - r) / 0.05, 0, 1) * np.clip(0.3 + 0.7 * (xs * 0.7 - ys * 0.7), 0, 1)
    px = np.stack([np.clip(room, 0, 1), np.clip(window, 0, 1), np.clip(rim, 0, 1), np.ones_like(room)], axis=2).astype(np.float32)
    img = bpy.data.images.new("ornament_shine", n, n, alpha=False)
    img.pixels.foreach_set(px[::-1].ravel())
    img.filepath_raw = os.path.join(TEXTURES, "ornament_shine.png")
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)


# =============================================================================================== building
class Build:
    def __init__(self, hanging=True, hang_from=0.0):
        self.v, self.lv, self.f, self.uv, self.tag, self.mat, self.smooth, self.crisp = [], [], [], [], [], [], [], []
        self.parts = []
        self.m = Matrix.Identity(4)
        self.hanging, self.hang_from = hanging, hang_from

    def begin(self, name):
        self._name, self._start = name, len(self.f)

    def end(self):
        self.parts.append((self._name, self._start, len(self.f)))

    def vert(self, p):
        q = self.m @ Vector(p)
        self.v.append((q.x, q.y, q.z))
        self.lv.append(Vector(p))
        return len(self.v) - 1

    def face(self, idx, uvs, st):
        self.f.append(list(idx))
        self.uv.append(list(uvs))
        self.tag.append((st.get("part", BODY), st.get("glit", 0), st.get("gloss", 0.0)))
        self.mat.append(st["mat"])
        self.smooth.append(st.get("smooth", True))
        self.crisp.append(st.get("crisp", True))

    def out(self, idx, uvs, st, hint):
        """A face wound so that its normal points along `hint` (both in the builder's own space)."""
        a, b, c = (self.lv[i] for i in idx[:3])
        if (b - a).cross(c - a).dot(Vector(hint)) < 0:
            idx, uvs = idx[::-1], uvs[::-1]
        self.face(idx, uvs, st)

    def tris(self):
        return sum(len(f) - 2 for f in self.f)


def glass_uv(k, jf, run, z):
    return (jf, 0.02 + 0.96 * run)      # Blender v 1 at the top of the profile's run... see lathe (run is from the foot)


def wrap_uv(cell, top=0.0, bottom=1.0, reps=1.0, rows=None):
    """UVs for a turned part: round the cell across, and down it from `top` to `bottom` as the profile climbs
    (or at the heights listed in `rows`, one for each profile point)."""
    def f(k, jf, run, z):
        fy = rows[k] if rows else bottom + (top - bottom) * run
        return cell.uv(jf * reps, fy)
    return f


def lathe(b, name, profile, segs, st, uv, mod=None, twist=0.0, rowstyle=None, uv_twist=True):
    """Turns `profile` [(radius, z)...] about z. It runs from the foot up the outside (and, for a shell, starts
    by coming down the inside); radius 0 is a pole. `mod(r, z, angle, k, j)` may move each point."""
    b.begin(name)
    run = [0.0]
    for k in range(1, len(profile)):
        run.append(run[-1] + math.hypot(profile[k][0] - profile[k - 1][0], profile[k][1] - profile[k - 1][1]))
    rings = []
    for k, (r, z) in enumerate(profile):
        if r < 1e-9:
            rings.append([b.vert((0, 0, z))] * segs)
        else:
            ring = []
            for j in range(segs):
                a = TAU * j / segs + k * twist
                rr, zz = mod(r, z, a, k, j) if mod else (r, z)
                ring.append(b.vert((rr * math.cos(a), rr * math.sin(a), zz)))
            rings.append(ring)
    for k in range(len(profile) - 1):
        A, B = rings[k], rings[k + 1]
        style, uvf = rowstyle(k) if rowstyle else (st, uv)
        for j in range(segs):
            j1 = (j + 1) % segs
            ta, tb = (k * twist / TAU, (k + 1) * twist / TAU) if uv_twist else (0.0, 0.0)
            corners = [(A[j], uvf(k, j / segs + ta, run[k] / run[-1], profile[k][1])),
                       (A[j1], uvf(k, (j + 1) / segs + ta, run[k] / run[-1], profile[k][1])),
                       (B[j1], uvf(k + 1, (j + 1) / segs + tb, run[k + 1] / run[-1], profile[k + 1][1])),
                       (B[j], uvf(k + 1, j / segs + tb, run[k + 1] / run[-1], profile[k + 1][1]))]
            seen, keep = set(), []
            for c in corners:
                if c[0] not in seen:
                    seen.add(c[0])
                    keep.append(c)
            if len(keep) >= 3:
                b.face([c[0] for c in keep], [c[1] for c in keep], style)
    b.end()


def tube(b, name, path, r, sides, st, uv, closed=False):
    """A thin round rod along `path`; `uv(along 0..1, round 0..1)`."""
    b.begin(name)
    pts = [Vector(p) for p in path]
    n = len(pts)
    tans = []
    for i in range(n):
        a = pts[(i - 1) % n] if (closed or i > 0) else pts[i]
        c = pts[(i + 1) % n] if (closed or i < n - 1) else pts[i]
        tans.append((c - a).normalized())
    u = tans[0].orthogonal().normalized()
    rings = []
    for i in range(n):
        if i > 0:
            u = tans[i - 1].rotation_difference(tans[i]) @ u     # carried round each bend, never flipped
        u = (u - tans[i] * u.dot(tans[i])).normalized()
        w = tans[i].cross(u)
        rings.append([b.vert(pts[i] + (u * math.cos(TAU * j / sides) + w * math.sin(TAU * j / sides)) * r)
                      for j in range(sides)])
    spans = n if closed else n - 1
    for i in range(spans):
        A, B = rings[i], rings[(i + 1) % n]
        mid = (pts[i] + pts[(i + 1) % n]) * 0.5
        for j in range(sides):
            j1 = (j + 1) % sides
            idx = [A[j], A[j1], B[j1], B[j]]
            uvs = [uv(i / spans, j / sides), uv(i / spans, (j + 1) / sides), uv((i + 1) / spans, (j + 1) / sides),
                   uv((i + 1) / spans, j / sides)]
            centre = sum((b.lv[q] for q in idx), Vector()) / 4.0
            b.out(idx, uvs, st, centre - mid)
    if not closed:
        for (ring, at, way, t) in ((rings[0], pts[0], -tans[0], 0.0), (rings[-1], pts[-1], tans[-1], 1.0)):
            tip = b.vert(at + way * r * 0.6)
            for j in range(sides):
                b.out([tip, ring[j], ring[(j + 1) % sides]], [uv(t, 0.5), uv(t, j / sides), uv(t, (j + 1) / sides)], st, way)
    b.end()


def _orient(pts, ccw):
    n = len(pts)
    area = sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1] for i in range(n))
    return list(pts) if (area > 0) == ccw else list(pts)[::-1]


def _edge_distance(q, loops, mine, corner):
    """How far `q` is from every edge but the two that meet at corner `corner` of loop `mine`."""
    best = 1e9
    for l in loops:
        n = len(l)
        for i in range(n):
            if l is mine and (i == corner or i == (corner + 1) % n):
                continue
            a, c = Vector(l[i - 1]), Vector(l[i])
            e = c - a
            t = max(0.0, min(1.0, (q - a).dot(e) / max(e.dot(e), 1e-20)))
            best = min(best, (q - a - e * t).length)
    return best


def _inset(pts, d, loops):
    """Moves each corner `d` to the left of the way round (into the solid: outlines run anticlockwise, holes
    clockwise), but never further than keeps it as far from every edge as it has come: where the shape is
    narrower than the chamfer (a point, a neck, the rim of a hole) the chamfer thins instead of crossing itself."""
    out, n = [], len(pts)
    for i in range(n):
        p0, p, p1 = Vector(pts[i - 1]), Vector(pts[i]), Vector(pts[(i + 1) % n])
        e0, e1 = (p - p0).normalized(), (p1 - p).normalized()
        n0, n1 = Vector((-e0.y, e0.x)), Vector((-e1.y, e1.x))
        m = n0 + n1
        m = m.normalized() if m.length > 1e-6 else n0
        go = m * (d / max(0.45, m.dot(n0)))
        share = 1.0
        for _ in range(12):
            q = p + go * share
            if _edge_distance(q, loops, pts, i) >= 1.25 * d * share:
                break
            share *= 0.8
        out.append((q.x, q.y))
    return out


def slab(b, name, outline, thick, bevel, st, uv, holes=(), y=0.0):
    """A flat shape standing in the x-z plane, `thick` through (along y), its edges chamfered by `bevel`.
    `uv(x, z)`. Front and back wear the same picture."""
    b.begin(name)
    loops = [_orient(outline, True)] + [_orient(h, False) for h in holes]
    half = thick * 0.5
    edge_y = half - bevel
    tops = [_inset(l, bevel, loops) if bevel > 0 else l for l in loops]
    edges, caps = {}, {}
    for side in (-1, 1):
        edges[side] = [[b.vert((p[0], y + side * edge_y, p[1])) for p in l] for l in loops]
        caps[side] = [[b.vert((p[0], y + side * half, p[1])) for p in l] for l in tops] if bevel > 0 else edges[side]
        flat = [i for ring in caps[side] for i in ring]
        for tri in tessellate_polygon([[Vector((p[0], p[1], 0.0)) for p in l] for l in tops]):
            idx = [flat[i] for i in tri]
            b.out(idx, [uv(b.lv[i].x, b.lv[i].z) for i in idx], st, (0, side, 0))
    for li, l in enumerate(loops):
        n = len(l)
        for i in range(n):
            i1 = (i + 1) % n
            e = Vector(l[i1]) - Vector(l[i])
            outward = Vector((e.y, 0.0, -e.x)).normalized()       # to the right of the way round: out of the solid
            idx = [edges[-1][li][i], edges[-1][li][i1], edges[1][li][i1], edges[1][li][i]]
            b.out(idx, [uv(b.lv[q].x, b.lv[q].z) for q in idx], st, outward)
            if bevel > 0:
                for side in (-1, 1):
                    idx = [edges[side][li][i], edges[side][li][i1], caps[side][li][i1], caps[side][li][i]]
                    b.out(idx, [uv(b.lv[q].x, b.lv[q].z) for q in idx], st, outward + Vector((0, side, 0)))
    b.end()


def puffed_star(b, name, pts, centre, half, rim, st, uv):
    """A star standing in the x-z plane through `pts`, swelling to `half` thick at its middle; `rim` 0 folds it
    to a knife edge (folded paper), more gives it a flat edge."""
    b.begin(name)
    n = len(pts)
    mid = Vector((centre[0], 0, centre[1]))
    front, back = b.vert((centre[0], -half, centre[1])), b.vert((centre[0], half, centre[1]))
    if rim > 0:
        fr = [b.vert((x, -rim, z)) for (x, z) in pts]
        bk = [b.vert((x, rim, z)) for (x, z) in pts]
    else:
        fr = bk = [b.vert((x, 0, z)) for (x, z) in pts]
    for i in range(n):
        i1 = (i + 1) % n
        for apex, ring, side in ((front, fr, -1.0), (back, bk, 1.0)):
            idx = [apex, ring[i], ring[i1]]
            c = sum((b.lv[q] for q in idx), Vector()) / 3.0
            b.out(idx, [uv(b.lv[q].x, b.lv[q].z) for q in idx], st, Vector((0, side, 0)) * 3.0 + (c - mid).normalized())
        if rim > 0:
            idx = [fr[i], fr[i1], bk[i1], bk[i]]
            c = sum((b.lv[q] for q in idx), Vector()) / 4.0
            e = b.lv[fr[i1]] - b.lv[fr[i]]
            hint = Vector((e.z, 0, -e.x))
            if hint.dot(c - mid) < 0:
                hint = -hint
            b.out(idx, [uv(b.lv[q].x, b.lv[q].z) for q in idx], st, hint)
    b.end()


# ----------------------------------------------------------------------------------------------- shared parts
METAL = {"mat": PAINT, "part": CAP, "gloss": 0.7}
TWINE = {"mat": PAINT, "part": THREAD, "gloss": 0.0}


def metal_uv(reps=1.0):
    return lambda along, around: BIT_METAL.uv(along * reps, 0.25 + 0.2 * around)


def twine_uv(reps):
    return lambda along, around: BIT_THREAD.uv(along * reps, 0.15 + 0.7 * around)


def thread(b, lo, plane="yz", half=0.0024, foot=-L0 - 0.0012, r=0.0006, x=0.0, y=0.0):
    """The loop of thread it hangs by: from the origin (the branch) down to `foot`, in the given plane."""
    if lo:
        tube(b, "thread", [(x, y, 0.0), (x, y, foot)], r * 1.3, 3, TWINE, twine_uv(0.25))
        return
    shape = [(0.0, foot), (0.8 * half, foot + 1.1 * half), (half, foot * 0.5), (0.8 * half, -1.1 * half), (0.0, 0.0),
             (-0.8 * half, -1.1 * half), (-half, foot * 0.5), (-0.8 * half, foot + 1.1 * half)]
    path = [(x, y + s, z) if plane == "yz" else (x + s, y, z) for (s, z) in shape]
    tube(b, "thread", path, r, 3, TWINE, twine_uv(0.5), closed=True)


def eye(b, lo, base, r=0.0045, wire=0.0006):
    """A wire loop standing on `base` (z), in the x-z plane, its top at base + r."""
    if lo:
        return
    path = [(r * math.cos(math.pi * i / 4), 0.0, base - 0.001 + (r + 0.001) * math.sin(math.pi * i / 4) - wire) for i in range(5)]
    tube(b, "eye", path, wire, 3, METAL, metal_uv(0.1))


def cap(b, lo, r=0.0088):
    """A glass ornament's crimped metal cap with its wire loop."""
    zb = CAP_TOP - CAP_H
    if lo:
        lathe(b, "cap", [(0, zb), (r * 1.08, zb), (r * 0.9, CAP_TOP), (0, CAP_TOP)], 6, METAL, wrap_uv(BIT_METAL, 0.1, 0.9))
        return
    crimp = lambda rr, z, a, k, j: (rr * (1.0 + (0.09 if j % 2 == 0 else -0.02)), z - (0.0012 if j % 2 == 0 else 0.0)) if k == 1 else (rr, z)
    lathe(b, "cap", [(0, zb + 0.001), (r * 1.08, zb), (r, zb + 0.003), (r, CAP_TOP - 0.0018), (r * 0.72, CAP_TOP), (0, CAP_TOP)],
          10, METAL, wrap_uv(BIT_METAL, 0.1, 0.9, 0.5), mod=crimp)
    eye(b, lo, CAP_TOP)


def glass(b, name, shape, segs, mod=None, twist=0.0, flat=False, gloss=1.0):
    """A turned glass body from `shape` [(radius, depth below the neck's top)...], listed from the neck down."""
    profile = [(r, GLASS_TOP - dpt) for (r, dpt) in reversed(shape)]
    st = {"mat": GLASS, "gloss": gloss, "smooth": not flat, "crisp": False}
    lathe(b, name, profile, segs, st, lambda k, jf, run, z: (jf, 0.02 + 0.96 * run), mod=mod, twist=twist)


def ball_shape(R, degrees, neck=0.003):
    c = neck + math.sqrt(R * R - NECK * NECK)
    first = math.degrees(math.asin(NECK / R))
    shape = [(0, 0), (NECK, 0), (NECK, neck)]
    for a in degrees:
        if a > first + 4:
            shape.append((R * math.sin(math.radians(a)), c - R * math.cos(math.radians(a))))
    return shape + [(0, c + R)], c


def sphere_uv(b, start, centre):
    """Gives the glass faces from `start` on UVs by where they are on a ball about `centre` (round the vertical,
    the seam at the back), whatever way the part was turned."""
    for fi in range(start, len(b.f)):
        if b.mat[fi] != GLASS:
            continue
        us, vs = [], []
        for i in b.f[fi]:
            p = Vector(b.v[i]) - centre
            vs.append(0.02 + 0.96 * (1.0 - math.acos(max(-1.0, min(1.0, p.z / p.length))) / math.pi))
            us.append(None if math.hypot(p.x, p.y) < 1e-6 else math.atan2(p.x, -p.y) / TAU + 0.5)
        known = [u for u in us if u is not None]
        if max(known) - min(known) > 0.5:
            known = [u + 1.0 if u < 0.5 else u for u in known]
            us = [None if u is None else (u + 1.0 if u < 0.5 else u) for u in us]
        mean = sum(known) / len(known)
        b.uv[fi] = [(mean if u is None else u, v) for (u, v) in zip(us, vs)]


# ----------------------------------------------------------------------------------------------- the ornaments
def build(kind, lo):
    b = Build()
    wood = {"mat": PAINT, "gloss": 0.12, "smooth": False}
    felt = {"mat": PAINT, "gloss": 0.0, "crisp": False}

    if kind == "ball":
        shape, _ = ball_shape(0.030, (50, 90, 130) if lo else (38, 62, 86, 110, 134, 158))
        glass(b, "glass", shape, 8 if lo else 16)
        cap(b, lo)
        thread(b, lo)

    elif kind == "teardrop":
        if lo:
            shape = [(0, 0), (NECK, 0.001), (0.0215, 0.019), (0.019, 0.040), (0.0075, 0.066), (0, 0.088)]
        else:
            shape = [(0, 0), (NECK, 0), (NECK, 0.003), (0.016, 0.009), (0.0212, 0.018), (0.0225, 0.027), (0.0195, 0.039),
                     (0.0135, 0.052), (0.0078, 0.065), (0.0038, 0.076), (0.0014, 0.085), (0, 0.089)]
        glass(b, "glass", shape, 7 if lo else 12)
        cap(b, lo)
        thread(b, lo)

    elif kind == "onion":
        if lo:
            shape = [(0, 0), (NECK, 0.001), (0.031, 0.022), (0.027, 0.043), (0.008, 0.060), (0, 0.084)]
        else:
            shape = [(0, 0), (NECK, 0), (NECK, 0.003), (0.021, 0.009), (0.0300, 0.019), (0.0325, 0.029), (0.0290, 0.040),
                     (0.0200, 0.049), (0.0105, 0.057), (0.0042, 0.070), (0, 0.084)]
        glass(b, "glass", shape, 8 if lo else 14)
        cap(b, lo)
        thread(b, lo)

    elif kind == "reflector":
        R = 0.0325
        zc = GLASS_TOP - 0.002 - R
        segs = 8 if lo else 16
        rim = math.radians(134)
        angles = (0, 45, 90, 134) if lo else (0, 26, 52, 78, 104, 134)
        profile = [(R * math.sin(math.radians(a)), -R * math.cos(math.radians(a))) for a in angles]
        rr, ra = R * math.sin(rim), -R * math.cos(rim)
        dent = [(rr * 0.5, ra - 0.011), (0, ra - 0.019)] if lo else [(rr * 0.86, ra - 0.0025), (rr * 0.55, ra - 0.010),
                                                                       (rr * 0.24, ra - 0.016), (0, ra - 0.019)]
        first_dent = len(profile) - 1
        profile += dent

        def folds(r, z, a, k, j):
            if k > first_dent and j % 2 == 0:
                return r, z + 0.0045 * (r / rr) ** 0.6
            return r, z

        burst = {"mat": PAINT, "gloss": 0.9, "glit": 1, "smooth": False, "crisp": False}
        skin = {"mat": GLASS, "gloss": 1.0, "crisp": False}
        b.m = Matrix.Translation((0, 0, zc)) @ Matrix.Rotation(math.radians(90), 4, "X")
        start = len(b.f)
        lathe(b, "glass", profile, segs, skin, lambda k, jf, run, z: (0, 0), mod=folds,
              rowstyle=lambda k: (burst, lambda kk, jf, run, z: (0, 0)) if k >= first_dent else (skin, lambda kk, jf, run, z: (0, 0)))
        b.m = Matrix.Identity(4)
        sphere_uv(b, start, Vector((0, 0, zc)))
        cell = CELLS[P_BURST]
        for fi in range(start, len(b.f)):
            if b.mat[fi] == PAINT:
                b.uv[fi] = [cell.muv(b.v[i][0], b.v[i][2] - zc) for i in b.f[fi]]
        # a short neck up into the cap
        lathe(b, "neck", [(0, zc + R - 0.004), (NECK, zc + R - 0.004), (NECK, GLASS_TOP), (0, GLASS_TOP)], 6,
              skin, lambda k, jf, run, z: (jf, 0.97))
        cap(b, lo)
        thread(b, lo)

    elif kind == "ribbed":
        shape, _ = ball_shape(0.0305, (50, 90, 130) if lo else (42, 70, 98, 126, 152, 168))
        ribs = lambda r, z, a, k, j: (r * (1.0 + (0.075 if j % 2 == 0 else -0.075) * (1.0 if r > NECK * 1.2 else 0.0)), z)
        glass(b, "glass", shape, 10 if lo else 20, mod=ribs)
        cap(b, lo)
        thread(b, lo)

    elif kind == "icicle":
        top = GLASS_TOP
        if lo:
            shape = [(0, 0), (0.0072, 0.002), (0.0050, 0.035), (0, 0.092)]
            glass(b, "glass", shape, 4, twist=math.radians(30), flat=True)
        else:
            shape = [(0, 0), (0.0072, 0.001), (0.0080, 0.010), (0.0066, 0.026), (0.0052, 0.042), (0.0038, 0.058),
                     (0.0024, 0.074), (0.0011, 0.086), (0, 0.094)]
            glass(b, "glass", shape, 6, twist=math.radians(17), flat=True)
        cap(b, lo, 0.0080)
        thread(b, lo)

    elif kind == "bell":
        zt = CAP_TOP
        cell = CELLS[P_BELL]
        st = {"mat": PAINT, "gloss": 0.75}
        if lo:
            prof = [(0, -0.006), (0.024, -0.048), (0.027, -0.050), (0.0165, -0.026), (0.0115, -0.006), (0, 0.0)]
            rows = [1.0, 0.76, 0.70, 0.40, 0.12, 0.0]
        else:
            prof = [(0, -0.005), (0.0125, -0.014), (0.019, -0.036), (0.0252, -0.0485), (0.0272, -0.0505), (0.0276, -0.0475),
                    (0.0215, -0.038), (0.0168, -0.026), (0.0146, -0.014), (0.0112, -0.005), (0.0055, -0.0008), (0, 0.0)]
            rows = [1.0, 0.92, 0.84, 0.76, 0.70, 0.66, 0.52, 0.36, 0.20, 0.10, 0.03, 0.0]
        prof = [(r, zt + z) for (r, z) in prof]
        lathe(b, "bell", prof, 8 if lo else 14, st, wrap_uv(cell, rows=rows))
        dark = lambda along, around: cell.uv(0.5, 0.9)
        if not lo:
            tube(b, "rod", [(0, 0, zt - 0.004), (0.001, 0.0005, zt - 0.047)], 0.0008, 3, st, dark)
        lathe(b, "clapper", [(0, zt - 0.058), (0.0042, zt - 0.0535), (0.0042, zt - 0.0505), (0, zt - 0.046)], 5 if lo else 7,
              {"mat": PAINT, "gloss": 0.75}, wrap_uv(cell, 0.08, 0.2))
        eye(b, lo, zt)
        thread(b, lo)

    elif kind == "wooden_star":
        cell = CELLS[P_WOOD]
        slab(b, "star", STAR_OUT, 0.0065, 0.0 if lo else 0.0013, wood, cell.muv)
        thread(b, lo, plane="xz", half=0.003, foot=-L0 - 0.001)

    elif kind == "heart":
        cell = CELLS[P_HEART]
        out = HEART_OUT[::2] if lo else HEART_OUT
        slab(b, "heart", out, 0.013, 0.0 if lo else 0.0042, felt, cell.muv)
        thread(b, lo, plane="xz", half=0.003, foot=-L0 - 0.004)

    elif kind == "snowflake":
        cell = CELLS[P_FLAKE]
        st = {"mat": PAINT, "gloss": 0.25, "glit": 1, "smooth": False}
        slab(b, "flake", FLAKE_OUT_LO if lo else FLAKE_OUT, 0.003, 0.0, st, cell.muv)
        thread(b, lo, plane="xz", half=0.003, foot=-L0 - 0.001)

    elif kind == "pine_cone":
        cell = CELLS[P_CONE]
        outs = [0.0068, 0.0118, 0.0158, 0.0188, 0.0200, 0.0180, 0.0135]
        z0, dz = CAP_TOP - 0.062, 0.0078
        prof, rows = [(0, z0 - 0.004)], [1.0]
        n = len(outs)
        for i, r in enumerate(outs):
            nxt = outs[i + 1] if i + 1 < n else 0.006
            prof += [(r, z0 + i * dz), (0.62 * nxt + 0.1 * r, z0 + (i + 0.82) * dz)]
            rows += [1.0 - (2 * i + 1) / 15.0, 1.0 - (2 * i + 2) / 15.0]
        prof.append((0, CAP_TOP))
        rows.append(0.0)
        if lo:
            prof, rows = prof[::2] + [prof[-1]], rows[::2] + [rows[-1]]
        lathe(b, "cone", prof, 5 if lo else 8, {"mat": PAINT, "gloss": 0.1, "smooth": False}, wrap_uv(cell, rows=rows),
              twist=math.pi / (5 if lo else 8) * (1.0 if lo else 0.5), uv_twist=False)
        eye(b, lo, CAP_TOP - 0.0005)
        thread(b, lo)

    elif kind == "candy_cane":
        b.hanging = False
        cell = CELLS[P_CANE]
        Rk, r = 0.0125, 0.0046
        cz = -(Rk - r)
        steps = 3 if lo else 7
        path = [(-Rk, 0, cz - 0.006)] + [(Rk * math.cos(math.pi - math.pi * i / steps), 0, cz + Rk * math.sin(math.pi * i / steps))
                                          for i in range(steps + 1)]
        path += [(Rk, 0, cz - 0.03), (Rk, 0, cz - 0.06), (Rk, 0, cz - 0.088)]
        lengths = [0.0]
        for i in range(1, len(path)):
            lengths.append(lengths[-1] + (Vector(path[i]) - Vector(path[i - 1])).length)
        b.m = Matrix.Rotation(math.radians(-6.0), 4, "Y")     # it hangs with its weight under the crook
        n = len(path) - 1
        tube(b, "cane", path, r, 4 if lo else 6, {"mat": PAINT, "gloss": 0.55, "crisp": False},
             lambda along, around: cell.uv(around, 0.02 + 0.96 * lengths[min(n, int(round(along * n)))] / lengths[-1]))
        b.m = Matrix.Identity(4)

    elif kind == "gingerbread":
        cell = CELLS[P_GINGER]
        out = GINGER_OUT[::2] if lo else GINGER_OUT
        slab(b, "man", out, 0.0062, 0.0 if lo else 0.0016, {"mat": PAINT, "gloss": 0.04, "crisp": False}, cell.muv)
        thread(b, lo, plane="xz", half=0.003, foot=-L0 - 0.001)

    elif kind in ("mitten", "stocking"):
        cell = CELLS[P_MITTEN if kind == "mitten" else P_STOCKING]
        body, cuff = (MITT_BODY, MITT_CUFF) if kind == "mitten" else (SOCK_BODY, SOCK_CUFF)
        slab(b, "body", body, 0.010, 0.0 if lo else 0.0032, felt, cell.muv)
        slab(b, "cuff", cuff[::2] if lo else cuff, 0.0135, 0.0 if lo else 0.0032, felt, cell.muv)
        x = 0.0 if kind == "mitten" else 0.0
        thread(b, lo, plane="xz", half=0.003, foot=-L0 - 0.001, x=x)

    elif kind == "straw_star":
        st = {"mat": PAINT, "gloss": 0.2, "smooth": False}
        zc = -L0 + 0.004 - 0.040
        layers = [(0.040, 0.0024, 0.0), (0.031, 0.0019, 22.5)] if not lo else [(0.040, 0.0026, 0.0)]
        n = 0
        for (L, w, turn) in layers:
            bar = [(-L, 0), (-L + 0.008, -w), (L - 0.008, -w), (L, 0), (L - 0.008, w), (-L + 0.008, w)]
            for k in range(4):
                b.m = Matrix.Translation((0, (n - 3.5) * 0.0011, zc)) @ Matrix.Rotation(math.radians(turn + 90 + k * 45), 4, "Y")
                slab(b, "straw%d" % n, bar, 0.0011, 0.0, st, lambda x, z, L=L, w=w: BIT_STRAW.uv(0.5 + 0.5 * x / L * 0.96, 0.5 + 0.38 * z / w))
                n += 1
        b.m = Matrix.Translation((0, 0, zc)) @ Matrix.Rotation(math.radians(90), 4, "X")
        lathe(b, "knot", [(0, -0.0062), (0.0048, -0.0045), (0.0048, 0.0045), (0, 0.0062)], 5 if lo else 8,
              {"mat": PAINT, "gloss": 0.0}, lambda k, jf, run, z: BIT_BEAD_B.uv(0.5, 0.5))
        b.m = Matrix.Identity(4)
        thread(b, lo, plane="yz", half=0.004, foot=-L0 - 0.004)

    elif kind == "paper_star":
        cell = CELLS[P_PAPER]
        puffed_star(b, "star", PAPER_OUT, PAPER_C, 0.011, 0.0, {"mat": PAINT, "gloss": 0.0, "smooth": False}, cell.muv)
        thread(b, lo, plane="xz", half=0.003, foot=-L0 - 0.001)

    elif kind == "dough_star":
        cell = CELLS[P_DOUGH]
        st = {"mat": PAINT, "gloss": 0.05, "crisp": False}
        if lo:
            slab(b, "star", DOUGH_OUT_LO, 0.008, 0.0, st, cell.muv)
            thread(b, lo, plane="xz", foot=-L0 - 0.001)
        else:
            slab(b, "star", DOUGH_OUT, 0.008, 0.0026, st, cell.muv, holes=[DOUGH_HOLE])
            thread(b, lo, plane="yz", half=0.0062, foot=-L0 - 0.0022)

    elif kind == "drum":
        cell = CELLS[P_DRUM]
        r, h = 0.021, 0.030
        tilt = math.radians(16.0)
        # the drum's own space: its middle at the origin; hung by a wire loop on its top hoop
        anchor = Vector((r * 1.02, 0, h * 0.5))
        rot = Matrix.Rotation(tilt, 4, "Y")
        moved = rot @ anchor
        place = Matrix.Translation((-moved.x, 0, -L0 - 0.0045 - moved.z)) @ rot
        b.m = place
        if lo:
            prof = [(0, -h / 2), (r * 1.06, -h / 2), (r * 1.06, h / 2), (0, h / 2)]
            rows = [1.0, 0.9, 0.1, 0.0]
        else:
            prof = [(0, -h / 2), (r * 0.97, -h / 2), (r * 1.08, -h / 2 + 0.0006), (r * 1.08, -h / 2 + 0.0045), (r, -h / 2 + 0.0050),
                    (r, h / 2 - 0.0050), (r * 1.08, h / 2 - 0.0045), (r * 1.08, h / 2 - 0.0006), (r * 0.97, h / 2), (0, h / 2)]
            rows = [1.0, 0.94, 0.915, 0.85, 0.83, 0.17, 0.15, 0.085, 0.06, 0.0]
        lathe(b, "drum", prof, 8 if lo else 14, {"mat": PAINT, "gloss": 0.3}, wrap_uv(cell, rows=rows))
        if not lo:
            stick = {"mat": PAINT, "gloss": 0.12}
            for sgn in (-1, 1):
                a, c = Vector((-0.016, sgn * 0.012, h / 2 + 0.0016)), Vector((0.015, -sgn * 0.010, h / 2 + 0.0016 + (0.002 if sgn > 0 else 0.0)))
                tube(b, "stick%d" % sgn, [a, a.lerp(c, 0.85), c], 0.0011, 4, stick, lambda along, around: CELLS[P_WOOD].uv(0.5, 0.42))
                b.m = place @ Matrix.Translation(c)
                lathe(b, "knob%d" % sgn, [(0, -0.0024), (0.0022, 0), (0, 0.0024)], 4, stick, lambda k, jf, run, z: CELLS[P_WOOD].uv(0.5, 0.42))
                b.m = place
        b.m = Matrix.Identity(4)
        eye(b, lo, -L0 - 0.0045)
        thread(b, lo)

    elif kind == "rocking_horse":
        cell = CELLS[P_HORSE]
        if lo:
            slab(b, "horse", HORSE_OUT, 0.0065, 0.0, wood, cell.muv, holes=[HORSE_HOLE[::2]])
        else:
            slab(b, "horse", HORSE_OUT, 0.0065, 0.0013, wood, cell.muv, holes=[HORSE_HOLE])
        thread(b, lo, plane="xz", half=0.003, foot=-L0 - 0.001)

    elif kind == "star_topper":
        b.hanging = False
        cell = CELLS[P_STARTOP]
        st = {"mat": PAINT, "gloss": 0.6, "glit": 1, "smooth": False}
        puffed_star(b, "star", TOP_OUT, TOP_C, 0.015, 0.0 if lo else 0.0032, st, cell.muv)
        sock_st = {"mat": PAINT, "part": CAP, "gloss": 0.7}
        lathe(b, "socket", [(0, 0.046), (0.0135, 0.0), (0.016, 0.0), (0.0062, 0.052), (0, 0.054)], 6 if lo else 10, sock_st,
              wrap_uv(BIT_METAL, 0.1, 0.9, 0.5))

    elif kind == "spire_topper":
        b.hanging = False
        if lo:
            prof = [(0, 0.044), (0.0135, 0.0), (0.0158, 0.0), (0.008, 0.052), (0.027, 0.085), (0.008, 0.118), (0.016, 0.135),
                    (0.005, 0.156), (0, 0.255)]
        else:
            prof = [(0, 0.045), (0.0135, 0.0), (0.0158, 0.0), (0.0080, 0.050), (0.0125, 0.058), (0.0235, 0.068), (0.0280, 0.085),
                    (0.0235, 0.101), (0.0125, 0.110), (0.0072, 0.118), (0.0130, 0.126), (0.0160, 0.135), (0.0130, 0.144),
                    (0.0058, 0.153), (0.0044, 0.172), (0.0026, 0.210), (0.0011, 0.245), (0, 0.257)]
        st = {"mat": GLASS, "gloss": 1.0, "crisp": False}
        lathe(b, "spire", prof, 7 if lo else 12, st, lambda k, jf, run, z: (jf, 0.02 + 0.96 * run))

    elif kind == "beads":
        b.hanging = False
        st = {"mat": PAINT, "gloss": 0.9, "crisp": False}
        turn = Matrix.Rotation(math.radians(90), 4, "Y")
        for i in range(5):
            cell = BIT_BEAD_A if i % 2 == 0 else BIT_BEAD_B
            b.m = Matrix.Translation((0.01 + i * 0.02, 0, 0)) @ turn
            R = 0.0078
            angles = (-90, -30, 30, 90) if lo else (-90, -45, 0, 45, 90)
            lathe(b, "bead%d" % i, [(R * math.cos(math.radians(a)), R * math.sin(math.radians(a))) for a in angles],
                  4 if lo else 7, st, lambda k, jf, run, z, cell=cell: cell.uv(0.5, 0.5))
        b.m = Matrix.Identity(4)
        tube(b, "string", [(0, 0, 0), (0.1, 0, 0)], 0.0007, 3, TWINE, twine_uv(1.0))

    elif kind == "tinsel":
        b.hanging = False
        st = {"mat": GLASS, "gloss": 0.9, "glit": 1, "smooth": False}
        count = 4 if lo else 8
        for i in range(count):
            x = 0.1 * (i + 0.5) / count
            turn = TAU * i * 0.19
            lean = Matrix.Rotation(math.radians(34.0 * math.sin(i * 2.4 + 0.5)), 4, "Z") @ Matrix.Rotation(math.radians(28.0 * math.cos(i * 1.7)), 4, "Y")
            b.m = Matrix.Translation((x, 0, 0)) @ lean @ Matrix.Rotation(turn, 4, "X") @ Matrix.Rotation(math.radians(90), 4, "Z")
            pts = star_pts(0.018, 0.0045, 5 if lo else 7)
            ang = lambda px_, pz_: (math.atan2(pz_, px_) / TAU + 0.5, 0.05 + 0.9 * min(1.0, math.hypot(px_, pz_) / 0.018))
            puffed_star(b, "bristle%d" % i, pts, (0, 0), 0.0022, 0.0, st, ang)
        b.m = Matrix.Identity(4)
        tube(b, "core", [(0, 0, 0), (0.1, 0, 0)], 0.0012, 3, st, lambda along, around: (around, 0.05))
    return b


# =============================================================================================== checking
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
            at = (verts[a] + verts[bb] + verts[c]) / 3.0 + n * 1e-4
            n = (n + Vector((0.0131, 0.0073, 0.0112))).normalized()   # a hair off, so no ray runs along an edge
            hits = 0
            while hits < 64:
                hit = tree.ray_cast(at, n)
                if hit[0] is None:
                    break
                hits += 1
                at = hit[0] + n * 1e-4
            if hits % 2:
                wrong += 1
        ok = volume > 0 and wrong == 0
        if not ok:
            bad += 1
            print("  %-22s %-10s %3d tris  volume %9.2f mm3  %d of them inside out  FAIL" % (name, part, len(tris), volume, wrong))
    return bad


def finish(name, b, mats, at):
    me = bpy.data.meshes.new(name)
    me.from_pydata(b.v, [], b.f)
    me.uv_layers.new(name="UVMap")
    me.uv_layers.new(name="tags")
    uvl, tl = me.uv_layers["UVMap"], me.uv_layers["tags"]  # looked up after both exist (making one moves the other)
    span = L0 - b.hang_from
    for fi, poly_ in enumerate(me.polygons):
        poly_.material_index = b.mat[fi]
        poly_.use_smooth = b.smooth[fi]
        part, glit, gloss = b.tag[fi]
        for c, li in enumerate(poly_.loop_indices):
            uvl.data[li].uv = b.uv[fi][c]
            z = b.v[poly_.vertices[c]][2]
            hang = min(1.0, max(0.0, (-z - b.hang_from) / span)) if b.hanging else 0.0
            tl.data[li].uv = ((4 * part + 2 * glit + 0.5 + hang) / 16.0, 1.0 - gloss)
    for m in mats:
        me.materials.append(m)
    me.validate()
    me.update()
    crisp = {tuple(sorted(f)): b.crisp[i] for i, f in enumerate(b.f)}
    bm = bmesh.new()
    bm.from_mesh(me)
    for e in bm.edges:  # keep hard corners hard (wood, metal lips), leave soft things soft (glass, felt, dough)
        if len(e.link_faces) == 2 and e.calc_face_angle(0.0) > math.radians(40):
            if all(crisp.get(tuple(sorted(v.index for v in f.verts)), True) for f in e.link_faces):
                e.smooth = False
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    ob.location = at
    bpy.context.scene.collection.objects.link(ob)
    return ob


# =============================================================================================== look-over sheets
def sheet(path, objects):
    """Each ornament in a row of five: front, right, back, left, and from above. Brought to one size."""
    scene = bpy.context.scene
    made = []
    cell = 1.25
    for row, ob in enumerate(objects):
        pts = [Vector(v.co) for v in ob.data.vertices]
        lo_, hi_ = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))), \
            Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
        mid = (lo_ + hi_) * 0.5
        k = 1.0 / max(hi_ - lo_)
        for col in range(5):
            twin = bpy.data.objects.new("look", ob.data)
            scene.collection.objects.link(twin)
            if col < 4:
                rot = Matrix.Rotation(math.radians(90 * col), 4, "Z")
            else:
                rot = Matrix.Rotation(math.radians(90), 4, "X")
            twin.matrix_world = Matrix.Translation((col * cell, 0, -row * cell)) @ rot @ Matrix.Scale(k, 4) @ Matrix.Translation(-mid)
            made.append(twin)
    cam_data = bpy.data.cameras.new("look_cam")
    cam_data.type = "ORTHO"
    w, h = 5 * cell, len(objects) * cell
    cam_data.ortho_scale = max(w, h)
    cam = bpy.data.objects.new("look_cam", cam_data)
    scene.collection.objects.link(cam)
    cam.location = (2 * cell, -20, -(len(objects) - 1) * cell * 0.5)
    cam.rotation_euler = (math.radians(90), 0, 0)
    scene.camera = cam
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "TEXTURE"
    scene.display.shading.show_cavity = True
    scene.display.shading.show_object_outline = False
    scene.display.shading.show_backface_culling = True
    scene.view_settings.view_transform = "Standard"
    scene.render.resolution_x = int(w * 260)
    scene.render.resolution_y = int(h * 260)
    scene.render.film_transparent = False
    scene.world = scene.world or bpy.data.worlds.new("w")
    scene.world.color = (0.32, 0.33, 0.36)
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


# =============================================================================================== run
for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob)

paint_designs()
paint_atlas()
paint_shine()
designs.save()
paint.save()

# What Blender shows: the paint in each kind's usual colours, and one glass design (stars, red and gold).
shown = np.zeros_like(paint.px)
for i, cell_ in enumerate(CELLS):
    a_, b_ = SHOW[i]
    shown[cell_.y:cell_.y + 256, cell_.x:cell_.x + 256] = decode(cell_.view(), a_, b_)
shown[BIT_THREAD.y:BIT_THREAD.y + 32, BIT_X:BIT_X + 256] = decode(BIT_THREAD.view(), RED, CREAM)
shown[BIT_STRAW.y:BIT_STRAW.y + 64, BIT_X:BIT_X + 256] = decode(BIT_STRAW.view(), (0.88, 0.74, 0.40), CREAM)
shown[BIT_BEAD_A.y:BIT_BEAD_A.y + 96, BIT_X:BIT_X + 256] = decode(paint.px[BIT_BEAD_A.y:BIT_BEAD_A.y + 96, BIT_X:BIT_X + 256], RED, GOLD)
paint_shown = paint.image("ornament_paint_shown", shown)
paint_shown.pack()
glass_shown = designs.image("ornament_glass_shown", decode(designs.px[D_STARS * DESIGN_H:(D_STARS + 1) * DESIGN_H], RED, GOLD))
glass_shown.pack()
if SHEETS:
    for (name_, img_) in (("paint_shown.png", paint_shown), ("glass_shown.png", glass_shown)):
        img_.filepath_raw = os.path.join(SHEETS, name_)
        img_.file_format = "PNG"
        img_.save()
    for (name_, a_, b_) in (("designs_red_gold.png", RED, GOLD), ("designs_blue_silver.png", (0.10, 0.25, 0.65), (0.85, 0.87, 0.92))):
        img_ = designs.image("d", decode(designs.px, a_, b_))
        img_.filepath_raw = os.path.join(SHEETS, name_)
        img_.file_format = "PNG"
        img_.save()
        bpy.data.images.remove(img_)

mats = []
for (name_, img_, rough) in (("glass", glass_shown, 0.12), ("paint", paint_shown, 0.7)):
    m_ = bpy.data.materials.new(name_)
    m_.use_nodes = True
    bsdf = next(n for n in m_.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    tex = m_.node_tree.nodes.new("ShaderNodeTexImage")
    tex.image = img_
    m_.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = rough
    m_.use_backface_culling = True
    mats.append(m_)

KINDS = ["ball", "teardrop", "onion", "reflector", "ribbed", "icicle", "bell", "wooden_star", "heart", "snowflake",
         "pine_cone", "candy_cane", "gingerbread", "mitten", "stocking", "straw_star", "paper_star", "dough_star",
         "drum", "rocking_horse", "star_topper", "spire_topper", "beads", "tinsel"]
failed = 0
full, low = [], []
print("ornaments: triangles, full and low")
for i, kind in enumerate(KINDS):
    counts = []
    for lo in (False, True):
        name = "orn_%s%s" % (kind, "_lo" if lo else "")
        b = build(kind, lo)
        failed += check(name, b)
        ob = finish(name, b, mats, ((i % 6) * 0.12, 0.3 if lo else 0.0, -(i // 6) * 0.2))
        (low if lo else full).append(ob)
        counts.append(b.tris())
    print("  %-14s %4d %4d" % (kind, counts[0], counts[1]))
if failed:
    print("FAILED: %d part(s) inside out or open" % failed)
    sys.exit(1)

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "ornaments.blend"))

for ob in bpy.data.objects:
    ob.select_set(ob in full or ob in low)
for ob in full + low:       # every mesh at the origin in the .glb; they are laid out in rows only in the .blend
    ob["was"] = tuple(ob.location)
    ob.location = (0, 0, 0)
bpy.ops.export_scene.gltf(filepath=os.path.join(MODELS, "ornaments.glb"), export_format="GLB",
                          use_selection=True, export_apply=True, export_yup=True, export_image_format="NONE",
                          export_normals=True, export_texcoords=True, export_materials="EXPORT",
                          export_animations=False)
for ob in full + low:
    ob.location = ob["was"]

if SHEETS:
    for n in range(0, len(KINDS), 4):
        sheet(os.path.join(SHEETS, "full_%d.png" % (n // 4)), full[n:n + 4])
        sheet(os.path.join(SHEETS, "low_%d.png" % (n // 4)), low[n:n + 4])
print("ornaments: built")
