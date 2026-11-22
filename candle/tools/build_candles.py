# Builds the candle component's models and pictures.
#
#   blender -b --factory-startup --python candle/tools/build_candles.py
#
# Writes, beside this folder:
#   tools/candles.blend          every candle, full and low, to open and edit
#   models/candles.glb           the same for Godot (no pictures inside: the script lays the materials on)
#   textures/candle_wax.png      tiling wax, near white (the wax colour is multiplied in)
#   textures/candle_glow.png     the warm light through the wax, read on the second UV set (top = at the flame)
#   textures/candle_parts.png    brass, tin, glazed saucer, holly leaf, berry and glass (with alpha) in one sheet
#
# Each candle is three objects at most under an empty named after it: <kind>_wax (wax and wick, with a shape
# key "burnt": 0 a new candle, 1 nearly gone), <kind>_parts (holder, saucer, holly) and <kind>_glass, plus
# empties <kind>_wick<n>_new / _burnt where a flame sits at each end of the shape key. Low versions are
# <kind>_lo_... Sizes are metres, Z up, the foot at the origin.
#
# Every closed piece of every mesh is checked for facing outwards (its signed volume, new and burnt) and
# the script stops if one is not.
import bpy
import bmesh
import math
import os
import random
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MODELS = os.path.join(ROOT, "models")
TEXTURES = os.path.join(ROOT, "textures")
TAU = math.pi * 2.0


def lerp(a, b, t):
    return a + (b - a) * t


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


# ------------------------------------------------------------------ the pictures
def _smooth(t):
    return t * t * (3.0 - 2.0 * t)


def pnoise(w, h, cells_x, cells_y, rs):
    """Value noise that tiles both ways: w x h pixels over a grid of cells."""
    grid = rs.random_sample((cells_y, cells_x))
    ys = np.arange(h) / h * cells_y
    xs = np.arange(w) / w * cells_x
    y0 = np.floor(ys).astype(int)
    x0 = np.floor(xs).astype(int)
    fy = _smooth(ys - y0)[:, None]
    fx = _smooth(xs - x0)[None, :]
    y1 = (y0 + 1) % cells_y
    x1 = (x0 + 1) % cells_x
    y0 %= cells_y
    x0 %= cells_x
    a = grid[y0][:, x0]
    b = grid[y0][:, x1]
    c = grid[y1][:, x0]
    d = grid[y1][:, x1]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def fbm(w, h, cells_x, cells_y, octaves, rs):
    total = np.zeros((h, w))
    amp = 1.0
    norm = 0.0
    for _o in range(octaves):
        total += pnoise(w, h, cells_x, cells_y, rs) * amp
        norm += amp
        amp *= 0.5
        cells_x *= 2
        cells_y *= 2
    return total / norm


def mix(a, b, t):
    """a, b: colours (3,), t: array -> array (h, w, 3)."""
    a = np.array(a)[None, None, :]
    b = np.array(b)[None, None, :]
    return a + (b - a) * t[:, :, None]


def save_png(name, rgba):
    """rgba: (h, w, 4) floats 0..1, row 0 at the BOTTOM (v = 0), as Blender keeps pictures."""
    h, w, _ = rgba.shape
    image = bpy.data.images.new(name, w, h, alpha=True)
    image.alpha_mode = 'STRAIGHT'
    image.pixels.foreach_set(np.clip(rgba, 0.0, 1.0).astype(np.float32).ravel())
    image.filepath_raw = os.path.join(TEXTURES, name + ".png")
    image.file_format = 'PNG'
    image.save()
    return image


def paint_wax():
    rs = np.random.RandomState(7)
    n = 256
    blotch = fbm(n, n, 3, 3, 4, rs)
    cloud = fbm(n, n, 6, 6, 3, rs)
    runs = fbm(n, n, 20, 2, 2, rs)          # faint streaks up and down, where wax ran
    grain = rs.random_sample((n, n))
    value = 0.90 + 0.13 * (blotch - 0.5) + 0.07 * (runs - 0.5) + 0.05 * (cloud - 0.5) + 0.016 * (grain - 0.5)
    # pale soft spots, as the bloom on old wax
    spots = np.clip((fbm(n, n, 9, 9, 2, rs) - 0.62) * 5.0, 0.0, 1.0)
    value = value + 0.05 * spots
    value = np.clip(value, 0.0, 1.0)
    warm = np.clip(1.0 - value, 0.0, 1.0)   # the darker places a little warmer
    rgba = np.ones((n, n, 4))
    rgba[:, :, 0] = value
    rgba[:, :, 1] = value * (1.0 - 0.10 * warm)
    rgba[:, :, 2] = value * (1.0 - 0.32 * warm)
    return save_png("candle_wax", rgba)


def paint_glow():
    rs = np.random.RandomState(3)
    w, h = 32, 128
    k = (np.arange(h) / (h - 1.0))[:, None] * np.ones((1, w))
    k = np.clip(k + (pnoise(w, h, 4, 6, rs) - 0.5) * 0.06 * k, 0.0, 1.0)
    low = mix((0.42, 0.11, 0.03), (1.0, 0.52, 0.16), np.clip(k / 0.6, 0.0, 1.0))
    high = mix((1.0, 0.52, 0.16), (1.0, 0.88, 0.58), np.clip((k - 0.6) / 0.4, 0.0, 1.0))
    colour = np.where((k < 0.6)[:, :, None], low, high)
    lum = 0.045 + 0.955 * np.power(k, 1.8)
    rgba = np.ones((h, w, 4))
    rgba[:, :, :3] = colour * lum[:, :, None]
    return save_png("candle_glow", rgba)


# Where each thing is on the parts sheet: u0, v0, u1, v1
REGION = {
    "brass": (0.0, 0.5, 0.5, 1.0),
    "tin": (0.5, 0.5, 1.0, 0.75),
    "ceramic": (0.5, 0.75, 1.0, 1.0),
    "leaf": (0.0, 0.25, 0.25, 0.5),
    "berry": (0.25, 0.25, 0.5, 0.5),
    "glass": (0.5, 0.25, 1.0, 0.5),
}


def paint_parts():
    rs = np.random.RandomState(11)
    n = 512
    rgba = np.ones((n, n, 4))
    rgba[:, :, :3] = (0.62, 0.46, 0.2)

    def block(name):
        u0, v0, u1, v1 = REGION[name]
        x0, x1, y0, y1 = int(u0 * n), int(u1 * n), int(v0 * n), int(v1 * n)
        w, h = x1 - x0, y1 - y0
        u = (np.arange(w) / w)[None, :] * np.ones((h, 1))
        v = (np.arange(h) / h)[:, None] * np.ones((1, w))
        return (slice(y0, y1), slice(x0, x1)), u, v, w, h

    # brass: painted sheen in bands round it (u goes round the turned shape), patina, lathe lines, tarnish
    where, u, v, w, h = block("brass")
    sheen = 0.52 + 0.27 * np.sin(TAU * (u - 0.08)) + 0.15 * np.sin(2 * TAU * u + 1.1) + 0.06 * np.sin(5 * TAU * u + 0.4)
    sheen += 0.16 * (fbm(w, h, 5, 5, 3, rs) - 0.5) + 0.03 * np.sin(v * h * 0.9)
    glint = np.exp(-np.square((np.mod(u - 0.2 + 0.5, 1.0) - 0.5) / 0.035))
    colour = mix((0.36, 0.21, 0.06), (0.95, 0.74, 0.3), np.clip(sheen, 0.0, 1.0))
    colour = colour + mix((0, 0, 0), (0.25, 0.25, 0.2), glint * 0.9)
    tarnish = np.clip((fbm(w, h, 12, 12, 2, rs) - 0.66) * 6.0, 0.0, 1.0)
    colour = colour * (1.0 - 0.45 * tarnish[:, :, None]) + np.array((0.05, 0.09, 0.05))[None, None, :] * tarnish[:, :, None]
    rgba[where[0], where[1], :3] = colour

    # tin: the pressed cup of a tea light, pale, with fine crimps and soft bands of sheen
    where, u, v, w, h = block("tin")
    sheen = 0.6 + 0.2 * np.sin(TAU * (u - 0.1)) + 0.1 * np.sin(3 * TAU * u + 0.7) + 0.08 * np.sin(TAU * u * 36.0)
    sheen += 0.1 * (fbm(w, h, 6, 3, 2, rs) - 0.5) + 0.08 * (v - 0.5)
    rgba[where[0], where[1], :3] = mix((0.5, 0.52, 0.56), (0.96, 0.96, 0.94), np.clip(sheen, 0.0, 1.0))

    # glazed saucer: cream, mottled, two blue lines round the inside of the rim
    where, u, v, w, h = block("ceramic")
    cream = mix((0.84, 0.79, 0.68), (0.97, 0.94, 0.86), fbm(w, h, 6, 4, 3, rs))
    speck = np.clip((rs.random_sample((h, w)) - 0.985) * 60.0, 0.0, 1.0)
    cream = cream * (1.0 - 0.35 * speck[:, :, None])
    wav = 0.004 * np.sin(TAU * u * 3.0)
    line = np.clip(1.0 - np.abs(v + wav - 0.572) / 0.014, 0.0, 1.0) + np.clip(1.0 - np.abs(v + wav - 0.615) / 0.006, 0.0, 1.0)
    line = np.clip(line * 1.6, 0.0, 1.0) * (0.8 + 0.2 * fbm(w, h, 16, 2, 2, rs))
    rgba[where[0], where[1], :3] = cream * (1.0 - line[:, :, None]) + np.array((0.2, 0.33, 0.6))[None, None, :] * line[:, :, None]

    # holly leaf: u along it, v across (0.5 the midrib)
    where, u, v, w, h = block("leaf")
    across = np.abs(v - 0.5) * 2.0
    green = mix((0.05, 0.22, 0.09), (0.16, 0.42, 0.16), fbm(w, h, 4, 4, 3, rs))
    veins = np.clip(1.0 - np.abs(np.mod(u * 5.0 - across * 1.6, 1.0) - 0.5) / 0.07, 0.0, 1.0) * (1.0 - across * 0.4)
    rib = np.clip(1.0 - across / 0.07, 0.0, 1.0)
    shine = np.clip((fbm(w, h, 3, 3, 2, rs) - 0.55) * 4.0, 0.0, 1.0) * (1.0 - rib)
    edge = np.clip((across - 0.72) / 0.28, 0.0, 1.0)
    colour = green + mix((0, 0, 0), (0.2, 0.3, 0.12), veins * 0.55) + mix((0, 0, 0), (0.36, 0.46, 0.2), rib)
    colour = colour + mix((0, 0, 0), (0.25, 0.36, 0.26), shine * 0.6) + mix((0, 0, 0), (0.1, 0.2, 0.05), edge)
    rgba[where[0], where[1], :3] = colour

    # berry: red, darker below, a pale glint high on it (v runs from its foot to its top)
    where, u, v, w, h = block("berry")
    red = mix((0.42, 0.02, 0.04), (0.9, 0.12, 0.08), np.clip(v * 1.1 + 0.1 * (fbm(w, h, 4, 4, 2, rs) - 0.5), 0.0, 1.0))
    glint = np.exp(-(np.square((np.mod(u - 0.2 + 0.5, 1.0) - 0.5) / 0.09) + np.square((v - 0.7) / 0.1)))
    dot = np.clip((v - 0.95) / 0.05, 0.0, 1.0)
    colour = red + mix((0, 0, 0), (0.8, 0.75, 0.7), glint) - mix((0, 0, 0), (0.7, 0.1, 0.08), dot)
    rgba[where[0], where[1], :3] = colour

    # glass: a pale green-blue, mostly clear, with painted streaks of light down it; thicker at the lip and foot
    # (v runs from the middle of the foot, up the outside, over the lip at about 0.47, and down the inside)
    where, u, v, w, h = block("glass")
    streak = 0.6 * np.exp(-np.square((np.mod(u - 0.14 + 0.5, 1.0) - 0.5) / 0.02))
    streak += 0.3 * np.exp(-np.square((np.mod(u - 0.2 + 0.5, 1.0) - 0.5) / 0.008))
    streak += 0.25 * np.exp(-np.square((np.mod(u - 0.68 + 0.5, 1.0) - 0.5) / 0.05))
    streak *= np.clip((v - 0.14) / 0.05, 0.0, 1.0) * np.clip((0.46 - v) / 0.04, 0.0, 1.0)   # the outside wall only
    lip = np.exp(-np.square((v - 0.47) / 0.02))
    foot = np.clip((0.16 - v) / 0.05, 0.0, 1.0) + np.clip((v - 0.84) / 0.05, 0.0, 1.0)
    alpha = 0.13 + 0.05 * fbm(w, h, 6, 4, 2, rs) + streak + 0.4 * lip + 0.2 * np.clip(foot, 0.0, 1.0)
    tint = mix((0.72, 0.9, 0.86), (1.0, 1.0, 0.98), np.clip(streak * 1.5 + lip * 0.6, 0.0, 1.0))
    rgba[where[0], where[1], :3] = tint
    rgba[where[0], where[1], 3] = np.clip(alpha, 0.0, 0.9)
    return save_png("candle_parts", rgba)


def region_uv(name, u, v):
    """A point of a region of the parts sheet, kept a little inside its edges."""
    u0, v0, u1, v1 = REGION[name]
    pad = 0.006
    return (lerp(u0 + pad, u1 - pad, u), lerp(v0 + pad, v1 - pad, clamp(v, 0.0, 1.0)))


# ------------------------------------------------------------------ pieces of mesh
class Part:
    """Points, their colours, and faces as (indices, uv1s, uv2s)."""

    def __init__(self):
        self.v = []
        self.col = []
        self.faces = []

    def add(self, p, col=1.0):
        self.v.append((float(p[0]), float(p[1]), float(p[2])))
        self.col.append(col if isinstance(col, tuple) else (col, col, col))
        return len(self.v) - 1

    def face(self, idx, uv1, uv2=None):
        self.faces.append((list(idx), list(uv1), list(uv2) if uv2 else [(0.0, 0.0)] * len(idx)))

    def triangles(self):
        return sum(len(f[0]) - 2 for f in self.faces)


def ang_noise(rng, amps):
    """A wavy line round a circle: sines of whole numbers of turns, so it closes."""
    terms = [(a, k + 1, rng.uniform(0.0, TAU)) for k, a in enumerate(amps)]
    total = sum(a for a in amps) or 1.0
    return lambda ang: sum(a * math.sin(k * ang + ph) for (a, k, ph) in terms) / total


def lathe(part, rings, segs, uvmap, shape=None, phase=0.0):
    """Turns a profile about Z. rings: dicts with r, z and optionally col, g (glow on uv2); r 0 is a single
    point. shape(ring, angle) -> (r, z, cx, cy) bends it. uvmap(u, ring, total) -> uv1."""
    t = 0.0
    prev = None
    for ring in rings:
        if prev is not None:
            t += math.hypot(ring["r"] - prev["r"], ring["z"] - prev["z"])
        ring["t"] = t
        prev = ring
    total = t or 1.0
    ids = []
    for ring in rings:
        if ring["r"] == 0.0:
            r, z, cx, cy = shape(ring, 0.0) if shape else (0.0, ring["z"], 0.0, 0.0)
            ids.append([part.add((cx, cy, z), ring.get("col", 1.0))])
        else:
            row = []
            for j in range(segs):
                a = phase + TAU * j / segs
                r, z, cx, cy = shape(ring, a) if shape else (ring["r"], ring["z"], 0.0, 0.0)
                row.append(part.add((cx + r * math.cos(a), cy + r * math.sin(a), z), ring.get("col", 1.0)))
            ids.append(row)
    for i in range(len(rings) - 1):
        low, high = ids[i], ids[i + 1]
        ra, rb = rings[i], rings[i + 1]
        if len(low) == 1 and len(high) == 1:
            continue
        for j in range(segs):
            j1 = (j + 1) % segs
            u0, u1, um = j / segs, (j + 1) / segs, (j + 0.5) / segs
            if len(low) == 1:
                idx, us, rs = [low[0], high[j1], high[j]], [um, u1, u0], [ra, rb, rb]
            elif len(high) == 1:
                idx, us, rs = [low[j], low[j1], high[0]], [u0, u1, um], [ra, ra, rb]
            else:
                idx, us, rs = [low[j], low[j1], high[j1], high[j]], [u0, u1, u1, u0], [ra, ra, rb, rb]
            part.face(idx, [uvmap(u, ring, total) for u, ring in zip(us, rs)],
                      [(u, ring.get("g", 0.0)) for u, ring in zip(us, rs)])


def tube(part, points, radii, sides, cols, uvs, glows, frame):
    """A closed tube through points (a point at each end, rings between). frame(k) -> two unit vectors
    across the tube at point k. uvs[k] is the uv1 of ring k's first corner (u grows by 0.02 a side)."""
    ids = []
    last = len(points) - 1
    for k, p in enumerate(points):
        if k == 0 or k == last:
            ids.append([part.add(p, cols[k])])
            continue
        a, b = frame(k)
        row = []
        for s in range(sides):
            ang = TAU * s / sides
            ca, sa = math.cos(ang) * radii[k], math.sin(ang) * radii[k]
            row.append(part.add((p[0] + a[0] * ca + b[0] * sa, p[1] + a[1] * ca + b[1] * sa,
                                 p[2] + a[2] * ca + b[2] * sa), cols[k]))
        ids.append(row)
    for k in range(last):
        low, high = ids[k], ids[k + 1]
        for s in range(sides):
            s1 = (s + 1) % sides
            du0, du1 = s * 0.02, (s + 1) * 0.02
            if len(low) == 1:
                idx = [low[0], high[s1], high[s]]
                uv = [uvs[k], (uvs[k + 1][0] + du1, uvs[k + 1][1]), (uvs[k + 1][0] + du0, uvs[k + 1][1])]
                gl = [glows[k], glows[k + 1], glows[k + 1]]
            elif len(high) == 1:
                idx = [low[s], low[s1], high[0]]
                uv = [(uvs[k][0] + du0, uvs[k][1]), (uvs[k][0] + du1, uvs[k][1]), uvs[k + 1]]
                gl = [glows[k], glows[k], glows[k + 1]]
            else:
                idx = [low[s], low[s1], high[s1], high[s]]
                uv = [(uvs[k][0] + du0, uvs[k][1]), (uvs[k][0] + du1, uvs[k][1]),
                      (uvs[k + 1][0] + du1, uvs[k + 1][1]), (uvs[k + 1][0] + du0, uvs[k + 1][1])]
                gl = [glows[k], glows[k], glows[k + 1], glows[k + 1]]
            part.face(idx, uv, [(0.5, g) for g in gl])


def column(part, rng, *, r_at, zb, height, well, wobble, slump, segs, lo, urep, bottom, tex_r,
           inner_r=0.72, well_r=0.40, rim_r=0.90, lean=(0.0, 0.0), lo_glow_ring=False, pool_col=0.9):
    """The wax of a candle from `bottom` (rings up to its foot at zb) to the melted well at the top:
    an uneven rim (wobble), slumped on one side (slump), a dip round the wick (well deep).
    r_at(z): its radius at a height. Returns what the drips and the wick need."""
    n_rim = ang_noise(rng, [1.0, 0.7, 0.5, 0.35])
    n_rad = ang_noise(rng, [0.4, 1.0, 0.6])
    n_foot = ang_noise(rng, [0.6, 1.0, 0.8, 0.5])
    slump_at = rng.uniform(0.0, TAU)
    tall = height - zb
    top_r = r_at(height)
    glow_r = 0.02 + 0.3 * top_r
    fa = clamp(1.0 - 1.3 * max(top_r, 0.02) / tall, 0.3, 0.85)
    fb = clamp(1.0 - 0.4 * max(top_r, 0.012) / tall, 0.62, 0.95)
    fc = 1.0 - min(0.003, 0.1 * tall) / tall

    def top_at(ang):
        d = (ang - slump_at + math.pi) % TAU - math.pi
        top = height + wobble * n_rim(ang) - slump * math.exp(-(d / 0.55) ** 2)
        return max(top, zb + 0.5 * tall)

    def glow_at(z):
        return 0.05 + 0.85 * math.exp(-max(height - z, 0.0) / glow_r)

    def rough(ang, weight):
        return 1.0 + 0.025 * n_rad(ang) * weight

    def shape(ring, ang):
        kind = ring.get("k")
        if kind is None:
            return (ring["r"] * (1.0 + ring.get("rn", 0.0) * n_foot(ang)), ring["z"], 0.0, 0.0)
        top = top_at(ang) if ring["r"] > 0.0 else height
        if kind == "sa":
            z, r = zb + (top - zb) * fa, r_at(zb + tall * fa) * rough(ang, 0.3)
        elif kind == "sb":
            z, r = zb + (top - zb) * fb, r_at(zb + tall * fb) * rough(ang, 0.7)
        elif kind == "ro":
            z, r = zb + (top - zb) * fc, top_r * 0.99 * rough(ang, 1.0)
        elif kind == "rt":
            z, r = top, top_r * rim_r * rough(ang, 1.0)
        elif kind == "in":
            z, r = height - 0.4 * well + 0.6 * (top - height), top_r * inner_r * rough(ang, 0.6)
        elif kind == "we":
            z, r = height - well + 0.15 * (top - height), top_r * well_r
        else:
            z, r = height - 1.05 * well, 0.0
        return (r, z, lean[0] * (z - zb), lean[1] * (z - zb))

    rings = [dict(ring) for ring in bottom]
    for ring in rings:
        ring.setdefault("g", glow_at(ring["z"]))
    za, zs, zo = zb + tall * fa, zb + tall * fb, zb + tall * fc
    if not lo or lo_glow_ring:
        rings.append({"k": "sa", "r": r_at(za), "z": za, "g": glow_at(za)})
    rings.append({"k": "sb", "r": r_at(zs), "z": zs, "g": glow_at(zs)})
    if not lo:
        rings.append({"k": "ro", "r": top_r * 0.99, "z": zo, "g": glow_at(zo)})
    rings.append({"k": "rt", "r": top_r * rim_r, "z": height, "g": 0.92})
    if not lo:
        rings.append({"k": "in", "r": top_r * inner_r, "z": height - 0.4 * well, "g": 0.97, "col": 0.96})
    rings.append({"k": "we", "r": top_r * well_r, "z": height - well, "g": 1.0, "col": pool_col})
    rings.append({"k": "po", "r": 0.0, "z": height - 1.05 * well, "g": 1.0, "col": pool_col * 0.96})
    tex_w = TAU * tex_r / urep

    def uvmap(u, ring, _total):
        return (u * urep, ring["t"] / tex_w)

    lathe(part, rings, segs, uvmap, shape)

    def surf(ang, z):
        r = r_at(z) * rough(ang, 0.7)
        return ((lean[0] * (z - zb) + r * math.cos(ang), lean[1] * (z - zb) + r * math.sin(ang), z),
                (math.cos(ang), math.sin(ang), 0.0))

    def uv_at(ang, z):
        return (ang / TAU * urep, z / tex_w)

    pole_z = height - 1.05 * well
    return {"top_at": top_at, "glow_at": glow_at, "surf": surf, "uv_at": uv_at, "slump_at": slump_at,
            "wick": (lean[0] * (pole_z - zb), lean[1] * (pole_z - zb), pole_z), "well_z": height - well,
            "top_r": top_r}


def drip(part, rng, col, *, ang, length, width, bulge, floor, lo):
    """A run of wax from the rim down the side, ending in a bead: a closed tube sunk a little in the wax."""
    top = col["top_at"](ang)
    end = max(top - max(length, 0.004), floor)
    if top - end < 0.004:
        end = top - 0.004
    run = top - end
    wig = [rng.uniform(-1.0, 1.0) for _ in range(4)]
    spots = [(top - 0.0012, 0.9, 0.7), (top - 0.32 * run - 0.001, 0.8, 0.8),
             (top - 0.72 * run, 0.9, 0.9), (end + min(1.1 * width, 0.25 * run), 1.3, 1.15)]
    if lo:
        spots = [spots[0], spots[3]]
    sink = 0.0016
    rows = []
    for k, (z, wide, out) in enumerate(spots):
        a = ang + wig[k] * 0.35 * width / max(col["top_r"], 0.008) * (k / 3.0)
        p, n = col["surf"](a, z)
        t = (-n[1], n[0], 0.0)
        w, h = width * wide, bulge * out
        cross = [(-w, -sink), (-0.45 * w, h), (0.45 * w, h), (w, -sink)] if not lo else [(-w, -sink), (0.0, h), (w, -sink)]
        row = []
        for (side, away) in cross:
            row.append(part.add((p[0] + t[0] * side + n[0] * away, p[1] + t[1] * side + n[1] * away, z), 1.0))
        rows.append((row, a, z))
    p, n = col["surf"](ang, top)
    first = part.add((p[0] - n[0] * 0.0022, p[1] - n[1] * 0.0022, top + 0.0006), 1.0)
    p, n = col["surf"](rows[-1][1], end)
    last = part.add((p[0] + n[0] * bulge * 0.25, p[1] + n[1] * bulge * 0.25, end), 0.97)
    sides = len(rows[0][0])
    uv_at, glow_at = col["uv_at"], col["glow_at"]

    def corner(a, z, s):
        u, v = uv_at(a, z)
        return (u + s * 0.015, v)

    row, a, z = rows[0]
    for s in range(sides):
        s1 = (s + 1) % sides
        part.face([first, row[s1], row[s]], [corner(a, top, 0.5), corner(a, z, s + 1), corner(a, z, s)],
                  [(0.5, glow_at(top)), (0.5, glow_at(z)), (0.5, glow_at(z))])
    for k in range(len(rows) - 1):
        (r0, a0, z0), (r1, a1, z1) = rows[k], rows[k + 1]
        for s in range(sides):
            s1 = (s + 1) % sides
            part.face([r0[s], r0[s1], r1[s1], r1[s]],
                      [corner(a0, z0, s), corner(a0, z0, s + 1), corner(a1, z1, s + 1), corner(a1, z1, s)],
                      [(0.5, glow_at(z0)), (0.5, glow_at(z0)), (0.5, glow_at(z1)), (0.5, glow_at(z1))])
    row, a, z = rows[-1]
    for s in range(sides):
        s1 = (s + 1) % sides
        part.face([row[s], row[s1], last], [corner(a, z, s), corner(a, z, s + 1), corner(a, end, 0.5)],
                  [(0.5, glow_at(z)), (0.5, glow_at(z)), (0.5, glow_at(end))])


def wick(part, rng, base, lo, scale=1.0):
    """A charred wick curling over at its tip. Returns where the flame sits."""
    turn = rng.uniform(0.0, TAU)
    cs, sn = math.cos(turn), math.sin(turn)
    path = [(0.0, -0.0015), (0.0, 0.0), (0.0002, 0.0042), (0.0013, 0.0078), (0.0034, 0.0096), (0.0046, 0.0093)]
    radii = [0.0, 0.00095, 0.0009, 0.00085, 0.0007, 0.0]
    cols = [(0.5, 0.45, 0.38), (0.5, 0.45, 0.38), (0.12, 0.09, 0.07), (0.04, 0.035, 0.03), (0.03, 0.03, 0.03),
            (0.05, 0.03, 0.02)]
    glows = [0.0, 0.0, 0.0, 0.0, 0.5, 0.62]
    if lo:
        keep = [0, 1, 3, 5]
        path, radii, cols, glows = ([x[i] for i in keep] for x in (path, radii, cols, glows))
    points = [(base[0] + x * cs * scale, base[1] + x * sn * scale, base[2] + z * scale) for (x, z) in path]

    def frame(k):
        dx = path[k + 1][0] - path[k - 1][0]
        dz = path[k + 1][1] - path[k - 1][1]
        size = math.hypot(dx, dz) or 1.0
        dx, dz = dx / size, dz / size
        # across the tube: the level direction square to the curl, and the one in the curl's plane
        return ((-sn, cs, 0.0), (-dz * cs, -dz * sn, dx))

    uvs = [(0.3, 0.1 + 0.1 * k) for k in range(len(points))]
    tube(part, points, [r * scale for r in radii], 3 if lo else 4, cols, uvs, glows, frame)
    return (base[0], base[1], base[2] + 0.0055 * scale)


def metal_lathe(part, region, profile, segs, phase=0.0):
    rings = [{"r": r, "z": z} for (r, z) in profile]
    lathe(part, rings, segs, lambda u, ring, total: region_uv(region, u, ring["t"] / total), None, phase)


# ------------------------------------------------------------------ the candles
def build_pillar(lo, b, *, radius=0.0375, new=0.10, gone=0.03, drips=5, seed=11, urep=3, holly=False):
    rng = random.Random(seed)
    wax = Part()
    R = radius
    height = lerp(new, gone, b)
    k = R / 0.0375
    bottom = ([{"r": 0.0, "z": 0.0, "col": 0.8}, {"r": 0.92 * R, "z": 0.0, "col": 0.85}, {"r": R, "z": 0.004, "col": 0.93}]
              if not lo else [{"r": 0.0, "z": 0.0, "col": 0.8}, {"r": R, "z": 0.0, "col": 0.88}])
    col = column(wax, rng, r_at=lambda z: R, zb=0.0 if lo else 0.004, height=height, well=lerp(0.006, 0.014, b) * k,
                 wobble=lerp(0.0015, 0.004, b), slump=lerp(0.002, 0.011, b), segs=8 if lo else 16, lo=lo,
                 urep=urep, bottom=bottom, tex_r=R)
    runs = []
    for d in range(drips):
        ang = col["slump_at"] + TAU * d / drips + rng.uniform(-0.35, 0.35) * (1 if d else 0)
        runs.append((ang, rng.uniform(0.004, 0.028), rng.uniform(0.022, 0.085), rng.uniform(0.0034, 0.0048)))
    runs[0] = (runs[0][0], 0.03, 0.3, 0.0042)   # the long run out of the slumped side of the rim
    if lo:
        runs = runs[:2] if drips else []
    for (ang, l0, l1, width) in runs:
        drip(wax, rng, col, ang=ang, length=lerp(l0, l1, b), width=width * (1.0 + 0.25 * b), bulge=0.0017 + 0.0005 * b,
             floor=0.005, lo=lo)
    wicks = [wick(wax, rng, col["wick"], lo)]
    parts = None
    if holly:
        parts = Part()
        holly_ring(parts, random.Random(seed + 1), R, lo)
    return {"wax": wax, "parts": parts, "glass": None, "wicks": wicks}


def holly_ring(part, rng, R, lo):
    """Holly round a candle's foot: spiked leaves lying outwards, and berries in twos and threes."""
    leaves = 6
    length, width = 0.036, 0.017
    side = [(0.2, 0.5, 1.0), (0.4, 0.2, 0.0), (0.6, 0.46, 1.0), (0.8, 0.14, 0.0)]   # along, half across, spike
    if lo:
        side = [(0.45, 0.42, 1.0)]
    outline = [(0.0, 0.0, 0.0)] + [(a, c, s) for (a, c, s) in side] + [(1.0, 0.0, 1.0)] + [(a, -c, s) for (a, c, s) in reversed(side)]
    for n in range(leaves):
        ang = TAU * n / leaves + rng.uniform(-0.12, 0.12)
        yaw = ang + rng.choice((-1.0, 1.0)) * rng.uniform(0.25, 0.6)
        tilt = rng.uniform(0.12, 0.3)
        start = (math.cos(ang) * (R - 0.003), math.sin(ang) * (R - 0.003), 0.0035 + 0.002 * (n % 2))
        along = (math.cos(yaw) * math.cos(tilt), math.sin(yaw) * math.cos(tilt), math.sin(tilt))
        across = (-math.sin(yaw), math.cos(yaw), 0.0)
        up = (-math.cos(yaw) * math.sin(tilt), -math.sin(yaw) * math.sin(tilt), math.cos(tilt))
        size = rng.uniform(0.85, 1.1)

        def at(a, c, lift):
            x, y = a * length * size, c * width * size
            return (start[0] + along[0] * x + across[0] * y + up[0] * lift,
                    start[1] + along[1] * x + across[1] * y + up[1] * lift,
                    start[2] + along[2] * x + across[2] * y + up[2] * lift)

        rim = [part.add(at(a, c, 0.0012 * s + 0.0025 * a * a)) for (a, c, s) in outline]
        uv = [region_uv("leaf", a, 0.5 + c) for (a, c, _s) in outline]
        top = part.add(at(0.5, 0.0, -0.0006))
        under = part.add(at(0.5, 0.0, -0.0024))
        mid = region_uv("leaf", 0.5, 0.5)
        count = len(rim)
        for i in range(count):
            i1 = (i + 1) % count
            part.face([top, rim[i], rim[i1]], [mid, uv[i], uv[i1]])
            part.face([under, rim[i1], rim[i]], [mid, uv[i1], uv[i]])
    spots = 3
    for n in range(spots):
        ang = TAU * (n + 0.5) / spots + rng.uniform(-0.2, 0.2)
        for m in range(1 if lo or n == 2 else 2):
            a = ang + (m - 0.5) * 0.3
            r = 0.0048 * rng.uniform(0.9, 1.1)
            centre = (math.cos(a) * (R + 0.006 + 0.004 * (m % 2)), math.sin(a) * (R + 0.006 + 0.004 * (m % 2)),
                      0.009 + 0.003 * (m == 2))
            segs = 4 if lo else 5
            rings = ([{"r": 0.0, "z": -r}, {"r": r * 0.87, "z": -r * 0.5}, {"r": r * 0.87, "z": r * 0.5}, {"r": 0.0, "z": r}]
                     if not lo else [{"r": 0.0, "z": -r}, {"r": r, "z": 0.0}, {"r": 0.0, "z": r}])
            lathe(part, rings, segs, lambda u, ring, total: region_uv("berry", u, ring["t"] / total),
                  lambda ring, _a2, c=centre: (ring["r"], ring["z"] + c[2], c[0], c[1]), rng.uniform(0.0, 1.0))


def build_holly(lo, b):
    return build_pillar(lo, b, radius=0.034, new=0.11, gone=0.036, drips=3, seed=23, urep=3, holly=True)


def build_three_wick(lo, b):
    rng = random.Random(31)
    wax = Part()
    R = 0.055
    height = lerp(0.085, 0.036, b)
    well = lerp(0.006, 0.012, b)
    bottom = ([{"r": 0.0, "z": 0.0, "col": 0.8}, {"r": 0.94 * R, "z": 0.0, "col": 0.85}, {"r": R, "z": 0.004, "col": 0.93}]
              if not lo else [{"r": 0.0, "z": 0.0, "col": 0.8}, {"r": R, "z": 0.0, "col": 0.88}])
    col = column(wax, rng, r_at=lambda z: R, zb=0.0 if lo else 0.004, height=height, well=well,
                 wobble=lerp(0.0015, 0.0035, b), slump=lerp(0.002, 0.009, b), segs=9 if lo else 18, lo=lo, urep=4,
                 bottom=bottom, tex_r=R, inner_r=0.8, well_r=0.42)
    runs = []
    for d in range(4):
        ang = col["slump_at"] + TAU * d / 4 + rng.uniform(-0.3, 0.3) * (1 if d else 0)
        runs.append((ang, rng.uniform(0.004, 0.022), rng.uniform(0.02, 0.06), rng.uniform(0.003, 0.0042)))
    runs[0] = (runs[0][0], 0.025, 0.3, 0.0045)
    if lo:
        runs = runs[:2]
    for (ang, l0, l1, width) in runs:
        drip(wax, rng, col, ang=ang, length=lerp(l0, l1, b), width=width * (1.0 + 0.25 * b), bulge=0.0018 + 0.0005 * b,
             floor=0.005, lo=lo)
    wicks = []
    for n in range(3):
        a = TAU * n / 3
        wicks.append(wick(wax, rng, (math.cos(a) * 0.42 * R, math.sin(a) * 0.42 * R, col["well_z"] - 0.0003), lo))
    return {"wax": wax, "parts": None, "glass": None, "wicks": wicks}


def build_taper(lo, b):
    rng = random.Random(41)
    wax = Part()
    foot, tip_new, r_foot, r_tip = 0.028, 0.25, 0.011, 0.0082
    height = lerp(tip_new, 0.058, b)

    def r_at(z):
        return lerp(r_foot, r_tip, clamp((z - foot) / (tip_new - foot), 0.0, 1.0))

    bottom = [{"r": 0.0, "z": foot, "col": 0.85}, {"r": r_foot, "z": foot, "col": 0.9}]
    col = column(wax, rng, r_at=r_at, zb=foot, height=height, well=0.0022, wobble=lerp(0.0006, 0.0012, b),
                 slump=lerp(0.0008, 0.002, b), segs=5 if lo else 10, lo=lo, urep=1, bottom=bottom, tex_r=0.0096,
                 inner_r=0.66, well_r=0.34, rim_r=0.86, lo_glow_ring=True)
    runs = [(col["slump_at"], 0.03, 0.3, 0.0028),
            (col["slump_at"] + 2.2 + rng.uniform(-0.3, 0.3), rng.uniform(0.008, 0.02), rng.uniform(0.012, 0.022), 0.0024),
            (col["slump_at"] + 4.3 + rng.uniform(-0.3, 0.3), rng.uniform(0.012, 0.045), rng.uniform(0.014, 0.02), 0.0026)]
    if lo:
        runs = runs[:1]
    for (ang, l0, l1, width) in runs:
        drip(wax, rng, col, ang=ang, length=lerp(l0, l1, b), width=width, bulge=0.0014 + 0.0004 * b, floor=0.0375, lo=lo)
    wicks = [wick(wax, rng, col["wick"], lo, 0.85)]
    # the brass chamberstick: a drip pan, a socket for the candle, a finger loop at the pan's edge
    brass = Part()
    if lo:
        metal_lathe(brass, "brass", [(0.0, 0.0), (0.05, 0.0), (0.058, 0.014), (0.045, 0.006), (0.0, 0.006)], 8)
        metal_lathe(brass, "brass", [(0.0, 0.005), (0.016, 0.005), (0.0185, 0.034), (0.0118, 0.034), (0.0, 0.03)], 5, 0.3)
    else:
        metal_lathe(brass, "brass", [(0.0, 0.0), (0.046, 0.0), (0.055, 0.004), (0.0585, 0.0135), (0.0555, 0.0142),
                                     (0.045, 0.0062), (0.0, 0.0058)], 12)
        metal_lathe(brass, "brass", [(0.0, 0.005), (0.0165, 0.005), (0.0138, 0.02), (0.0172, 0.03), (0.019, 0.0345),
                                     (0.0118, 0.0345), (0.0118, 0.03), (0.0, 0.03)], 8, 0.2)
    major, minor = (5, 3) if lo else (8, 4)
    centre, big, small = (0.0665, 0.0, 0.0148), 0.0115, 0.0023
    ids = []
    for i in range(major):
        a = TAU * i / major
        row = []
        for j in range(minor):
            c = TAU * j / minor
            r = big + small * math.cos(c)
            row.append(brass.add((centre[0] + math.cos(a) * r, centre[1] + small * math.sin(c), centre[2] + math.sin(a) * r)))
        ids.append(row)
    for i in range(major):
        i1 = (i + 1) % major
        for j in range(minor):
            j1 = (j + 1) % minor
            uv = [region_uv("brass", i / major, j / minor), region_uv("brass", (i + 1) / major, j / minor),
                  region_uv("brass", (i + 1) / major, (j + 1) / minor), region_uv("brass", i / major, (j + 1) / minor)]
            brass.face([ids[i][j], ids[i1][j], ids[i1][j1], ids[i][j1]], uv)
    return {"wax": wax, "parts": brass, "glass": None, "wicks": wicks}


def build_tealight(lo, b):
    rng = random.Random(53)
    wax = Part()
    R = 0.0183
    height = lerp(0.0146, 0.0068, b)
    bottom = [{"r": 0.0, "z": 0.003, "col": 0.9}, {"r": R, "z": 0.003, "col": 0.9}]
    col = column(wax, rng, r_at=lambda z: R, zb=0.003, height=height, well=0.0012, wobble=0.0002, slump=0.0,
                 segs=7 if lo else 12, lo=lo, urep=2, bottom=bottom, tex_r=R, inner_r=0.7, well_r=0.36, rim_r=0.93,
                 pool_col=lerp(0.92, 0.8, b))
    wicks = [wick(wax, rng, col["wick"], lo, 0.8)]
    tin = Part()
    if lo:
        metal_lathe(tin, "tin", [(0.0, 0.0), (0.019, 0.0), (0.0197, 0.016), (0.0186, 0.016), (0.0, 0.004)], 7)
    else:
        metal_lathe(tin, "tin", [(0.0, 0.0), (0.0178, 0.0), (0.019, 0.0012), (0.0197, 0.016), (0.0187, 0.016),
                                 (0.0185, 0.0045), (0.0, 0.004)], 12)
    return {"wax": wax, "parts": tin, "glass": None, "wicks": wicks}


def build_votive(lo, b):
    rng = random.Random(67)
    wax = Part()

    def r_at(z):
        return 0.0241 + (z - 0.006) / 0.059 * 0.004

    height = lerp(0.046, 0.017, b)
    bottom = [{"r": 0.0, "z": 0.0066, "col": 0.85}, {"r": r_at(0.0066), "z": 0.0066, "col": 0.88}]
    col = column(wax, rng, r_at=r_at, zb=0.0066, height=height, well=lerp(0.004, 0.0055, b), wobble=0.0012,
                 slump=0.0012, segs=7 if lo else 12, lo=lo, urep=2, bottom=bottom, tex_r=0.026, inner_r=0.76,
                 well_r=0.4, rim_r=0.95, pool_col=lerp(0.9, 0.82, b))
    wicks = [wick(wax, rng, col["wick"], lo)]
    glass = Part()
    if lo:
        metal_lathe(glass, "glass", [(0.0, 0.0), (0.0255, 0.0), (0.0305, 0.065), (0.0285, 0.065), (0.0245, 0.006),
                                     (0.0, 0.006)], 8)
    else:
        metal_lathe(glass, "glass", [(0.0, 0.0), (0.024, 0.0), (0.026, 0.003), (0.03, 0.061), (0.0307, 0.065),
                                     (0.0285, 0.065), (0.0245, 0.006), (0.0, 0.006)], 14)
    return {"wax": wax, "parts": None, "glass": glass, "wicks": wicks}


def build_stub(lo, b):
    rng = random.Random(79)
    wax = Part()
    R = 0.019
    zs = 0.0052
    height = lerp(0.056, 0.027, b)
    pool = lerp(0.03, 0.039, b)
    if lo:
        bottom = [{"r": 0.0, "z": zs, "col": 0.85}, {"r": pool, "z": zs + 0.0006, "rn": 0.18, "col": 0.9},
                  {"r": 1.3 * R, "z": zs + 0.0045, "rn": 0.05, "col": 0.95}]
        zb = zs + 0.0045
    else:
        bottom = [{"r": 0.0, "z": zs, "col": 0.85}, {"r": pool, "z": zs + 0.0004, "rn": 0.18, "col": 0.88},
                  {"r": 0.87 * pool, "z": zs + 0.003, "rn": 0.18, "col": 0.94},
                  {"r": 1.45 * R, "z": zs + 0.0044, "rn": 0.06, "col": 0.97}, {"r": 1.08 * R, "z": zs + 0.0085, "col": 0.97}]
        zb = zs + 0.0085
    col = column(wax, rng, r_at=lambda z: R, zb=zb, height=height, well=lerp(0.004, 0.006, b),
                 wobble=lerp(0.0028, 0.0035, b), slump=lerp(0.004, 0.007, b), segs=7 if lo else 12, lo=lo, urep=2,
                 bottom=bottom, tex_r=R, lean=(0.05, -0.03))
    runs = []
    for d in range(4):
        ang = col["slump_at"] + TAU * d / 4 + rng.uniform(-0.3, 0.3) * (1 if d else 0)
        runs.append((ang, rng.uniform(0.012, 0.04), 0.3, rng.uniform(0.003, 0.0042)))
    runs[0] = (runs[0][0], 0.3, 0.3, 0.0046)
    if lo:
        runs = runs[:2]
    for (ang, l0, l1, width) in runs:
        drip(wax, rng, col, ang=ang, length=lerp(l0, l1, b), width=width * (1.0 + 0.2 * b), bulge=0.0018 + 0.0005 * b,
             floor=zs + 0.004, lo=lo)
    wicks = [wick(wax, rng, col["wick"], lo)]
    saucer = Part()
    if lo:
        metal_lathe(saucer, "ceramic", [(0.0, 0.0), (0.03, 0.0), (0.056, 0.0128), (0.04, 0.0055), (0.0, 0.005)], 8)
    else:
        metal_lathe(saucer, "ceramic", [(0.0, 0.0), (0.03, 0.0), (0.052, 0.009), (0.056, 0.0125), (0.053, 0.0135),
                                        (0.04, 0.0055), (0.0, 0.005)], 14)
    return {"wax": wax, "parts": saucer, "glass": None, "wicks": wicks}


KINDS = [("pillar", build_pillar), ("taper", build_taper), ("tealight", build_tealight), ("votive", build_votive),
         ("stub", build_stub), ("holly", build_holly), ("three_wick", build_three_wick)]


# ------------------------------------------------------------------ into Blender
def islands_outward(mesh, name):
    """Every closed piece must face outwards. Turns over the ones that do not; returns the pieces as lists
    of face numbers. Stops the build on a piece that is not closed."""
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.faces.ensure_lookup_table()
    seen = set()
    pieces = []
    turned = 0
    for face in bm.faces:
        if face.index in seen:
            continue
        piece = []
        stack = [face]
        seen.add(face.index)
        while stack:
            f = stack.pop()
            piece.append(f)
            for edge in f.edges:
                if len(edge.link_faces) != 2:
                    raise SystemExit("NOT CLOSED: %s has an edge with %d faces" % (name, len(edge.link_faces)))
                for g in edge.link_faces:
                    if g.index not in seen:
                        seen.add(g.index)
                        stack.append(g)
        volume = 0.0
        for f in piece:
            vs = [v.co for v in f.verts]
            for i in range(1, len(vs) - 1):
                volume += vs[0].dot(vs[i].cross(vs[i + 1])) / 6.0
        if volume < 0.0:
            bmesh.ops.reverse_faces(bm, faces=piece)
            turned += 1
        pieces.append([f.index for f in piece])
    bm.to_mesh(mesh)
    bm.free()
    return pieces, turned


def piece_volumes(mesh, pieces, coords):
    out = []
    for piece in pieces:
        volume = 0.0
        for fi in piece:
            vs = [coords[i] for i in mesh.polygons[fi].vertices]
            for i in range(1, len(vs) - 1):
                volume += vs[0].dot(vs[i].cross(vs[i + 1])) / 6.0
        out.append(volume)
    return out


def make_object(name, new, burnt, material, parent):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(new.v, [], [f[0] for f in new.faces])
    mesh.uv_layers.new(name="UVMap")
    mesh.uv_layers.new(name="UV2")
    mesh.color_attributes.new("Col", 'FLOAT_COLOR', 'POINT')
    uv1 = mesh.uv_layers["UVMap"].data
    uv2 = mesh.uv_layers["UV2"].data
    loop = 0
    for (_idx, a, b) in new.faces:
        for corner in range(len(a)):
            uv1[loop].uv = a[corner]
            uv2[loop].uv = b[corner]
            loop += 1
    colours = mesh.color_attributes["Col"]
    for i, c in enumerate(new.col):
        colours.data[i].color = (c[0], c[1], c[2], 1.0)
    mesh.color_attributes.active_color = colours
    mesh.color_attributes.render_color_index = mesh.color_attributes.find("Col")
    pieces, turned = islands_outward(mesh, name)
    mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))
    mesh.set_sharp_from_angle(angle=math.radians(80.0))
    mesh.materials.append(material)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.parent = parent
    from mathutils import Vector
    worst = min(piece_volumes(mesh, pieces, [v.co.copy() for v in mesh.vertices]))
    moved = max((Vector(a) - Vector(b)).length for a, b in zip(new.v, burnt.v))
    if [f[0] for f in new.faces] != [f[0] for f in burnt.faces]:
        raise SystemExit("%s: new and burnt are not the same mesh" % name)
    worst_burnt = worst
    if moved > 1e-7:
        obj.shape_key_add(name="Basis")
        key = obj.shape_key_add(name="burnt")
        for i, p in enumerate(burnt.v):
            key.data[i].co = p
        worst_burnt = min(piece_volumes(mesh, pieces, [Vector(p) for p in burnt.v]))
    if worst <= 0.0 or worst_burnt <= 0.0:
        raise SystemExit("INSIDE OUT: %s (smallest piece volume new %.3g, burnt %.3g)" % (name, worst, worst_burnt))
    print("  %-22s %4d triangles, %2d closed pieces, %d turned over, all outward new and burnt"
          % (name, new.triangles(), len(pieces), turned))
    return obj


def material(name, image, tint=(1.0, 1.0, 1.0), vertex_colours=False, glass=False):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    shader = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
    shader.inputs["Roughness"].default_value = 0.5
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = image
    colour = tex.outputs["Color"]
    if vertex_colours or tint != (1.0, 1.0, 1.0):
        mul = nodes.new("ShaderNodeMixRGB")
        mul.blend_type = 'MULTIPLY'
        mul.inputs["Fac"].default_value = 1.0
        links.new(colour, mul.inputs["Color1"])
        mul.inputs["Color2"].default_value = (tint[0], tint[1], tint[2], 1.0)
        colour = mul.outputs["Color"]
    if vertex_colours:
        attr = nodes.new("ShaderNodeVertexColor")
        attr.layer_name = "Col"
        mul2 = nodes.new("ShaderNodeMixRGB")
        mul2.blend_type = 'MULTIPLY'
        mul2.inputs["Fac"].default_value = 1.0
        links.new(colour, mul2.inputs["Color1"])
        links.new(attr.outputs["Color"], mul2.inputs["Color2"])
        colour = mul2.outputs["Color"]
    links.new(colour, shader.inputs["Base Color"])
    if glass:
        links.new(tex.outputs["Alpha"], shader.inputs["Alpha"])
        mat.blend_method = 'BLEND'
        shader.inputs["Roughness"].default_value = 0.1
    return mat


def main():
    os.makedirs(MODELS, exist_ok=True)
    os.makedirs(TEXTURES, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    wax_image = paint_wax()
    paint_glow()
    parts_image = paint_parts()
    mats = {"wax": material("candle_wax", wax_image, (0.96, 0.9, 0.76), True),
            "parts": material("candle_parts", parts_image),
            "glass": material("candle_glass", parts_image, glass=True)}
    total = {}
    for n, (kind, build) in enumerate(KINDS):
        for lo in (False, True):
            name = kind + ("_lo" if lo else "")
            new, burnt = build(lo, 0.0), build(lo, 1.0)
            parent = bpy.data.objects.new(name, None)
            parent.empty_display_size = 0.01
            bpy.context.scene.collection.objects.link(parent)
            parent.location = (n * 0.17, 0.3 if lo else 0.0, 0.0)
            count = 0
            for piece in ("wax", "parts", "glass"):
                if new[piece] is not None:
                    make_object("%s_%s" % (name, piece), new[piece], burnt[piece], mats[piece], parent)
                    count += new[piece].triangles()
            for w, (p0, p1) in enumerate(zip(new["wicks"], burnt["wicks"])):
                for tag, p in (("new", p0), ("burnt", p1)):
                    mark = bpy.data.objects.new("%s_wick%d_%s" % (name, w, tag), None)
                    mark.empty_display_size = 0.004
                    bpy.context.scene.collection.objects.link(mark)
                    mark.parent = parent
                    mark.location = p
            total[name] = count
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "candles.blend"))
    bpy.ops.export_scene.gltf(filepath=os.path.join(MODELS, "candles.glb"), export_format='GLB', export_yup=True,
                              export_apply=False, export_morph=True, export_morph_normal=True,
                              export_image_format='NONE', export_vertex_color='ACTIVE',
                              export_active_vertex_color_when_no_material=True, export_animations=False)
    print("BUILT candles:", ", ".join("%s %d" % (k, v) for k, v in total.items()))


main()
