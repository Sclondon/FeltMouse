# Builds the nutcrackers: five wooden figures (soldier, king, drummer, guard, baker), each full and low,
# and a walnut whole and in halves. Saves the editable nutcrackers.blend beside this file, exports
# ../models/nutcrackers.glb and paints ../textures/nutcracker_paint.png and nutcracker_masks.png
# (paint_nutcrackers.py).
#
#   blender -b --factory-startup --python nutcracker/tools/build_nutcrackers.py [-- <folder for a preview> [clips]]
#
# (`clips` lets the build finish when a pose clips, to look at it.)
#
# A figure is ONE mesh. Each face says, in a second UV set, which moving part it belongs to (0 the body,
# 1 the jaw and the lever down the back, 2 its right arm, 3 its left arm, 4 the moustache, 5 the
# beard, which hangs from the jaw), which colour it wears (ZONES) and how readily its paint chips. Empties beside the mesh mark
# the pivots. The game turns the parts about those pivots in its one shader (nutcracker.gdshader).
#
# The build stops if any piece of a mesh is not a closed skin wound outwards, or if a moving part cuts
# into another anywhere in its travel (CHECKED POSES below; the game's nutcracker.gd keeps the same
# numbers: change both). Blender: z up, the figure faces -y, its right arm is at -x. Metres.
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import paint_nutcrackers as paint  # noqa: E402

MODELS = os.path.join(HERE, "..", "models")
TEXTURES = os.path.join(HERE, "..", "textures")

BODY, JAW, ARM_R, ARM_L, TASH, BEARD = 0, 1, 2, 3, 4, 5
COAT, TROUSERS, HAT, TRIM, HAIR, SKIN, NONE = 0, 1, 2, 3, 4, 5, 6
# the colours the .blend is shown in (classic red and blue); the game picks its own
SHOW = [(0.72, 0.08, 0.07), (0.1, 0.2, 0.5), (0.05, 0.05, 0.06), (0.86, 0.66, 0.2), (0.93, 0.91, 0.86),
        (0.93, 0.72, 0.58), (1.0, 1.0, 1.0)]

# ---------------------------------------------------------------- CHECKED POSES (also in nutcracker.gd)
JAW_MAX = 16.0                      # degrees the jaw opens at most
# how far each arm may swing about its shoulder peg, degrees: right from, to; left from, to
# (under 0 is forwards and up)
ARM_RANGE = {
    "soldier": (-155.0, 40.0, -60.0, 40.0),
    "king": (-45.0, 12.0, -60.0, 40.0),
    "drummer": (-55.0, 0.0, -30.0, 0.0),
    "guard": (-48.0, 12.0, -60.0, 40.0),
    "baker": (-50.0, 12.0, -60.0, 40.0),
}
# the right arm's salute: its swing, and how far it leans in towards the hat, degrees
SALUTE = {"soldier": (-150.0, 8.0), "king": (-40.0, 0.0), "drummer": (-50.0, 0.0), "guard": (-42.0, 0.0),
          "baker": (-45.0, 0.0)}
TASH_TILT = 7.0                     # the moustache sits crooked by up to this, either way


def lerp(a, b, t):
    return a + (b - a) * t


def wrap180(a):
    return (a + 180.0) % 360.0 - 180.0


def uvr(name, u, v):
    r = paint.region(name)
    return (r[0] + (r[2] - r[0]) * u, r[1] + (r[3] - r[1]) * v)


class Fig:
    """One figure's mesh being put together, piece by piece. Every piece is a closed skin of its own."""

    def __init__(self, name):
        self.name = name
        self.v = []
        self.faces = []      # (indices, uvs, zone, part, wear)
        self.pieces = []     # [name, part, first vertex, end vertex, first face, end face, through]
        self.marks = {}

    def begin(self, name, part=BODY, through=False):
        self.pieces.append([name, part, len(self.v), len(self.v), len(self.faces), len(self.faces), through])

    def end(self):
        self.pieces[-1][3] = len(self.v)
        self.pieces[-1][5] = len(self.faces)

    def add(self, p):
        self.v.append(Vector(p))
        return len(self.v) - 1

    def face(self, idx, uvs, zone, wear):
        self.faces.append((tuple(idx), tuple(uvs), zone, self.pieces[-1][1], wear))

    def triangles(self):
        return sum(len(f[0]) - 2 for f in self.faces)


def sweep(fig, name, pts, radii, sides, spans, part=BODY, turn=0.0, side=(1.0, 0.0, 0.0), wear=0.35,
          cap0=None, cap1=None, hole=None, lump=None, through=False):
    """A ring of `sides` points round each of `pts`, joined into a skin: a lathe when the points run
    straight up, a bent tube otherwise. `radii` are numbers or (across, deep) pairs; 0 closes to a point.
    Column k of a ring is at angle 180 + 360 k / sides + turn from the front (-y for an upright piece),
    so u is 0 at the back seam and 0.5 at the front.
    `spans`: [(first ring, last ring, patch, zone, {options})], v running 0 to 1 over each. Options:
      repeat   how many times the patch goes round
      patches  [(patch, middle angle, how wide in degrees)]: faces there wear that patch instead, u across it
      wear     how readily the paint chips here
    `cap0`, `cap1`: (patch, zone) laid flat on an open end; left out, the end takes the colour of its rim.
    `hole`: (first ring, last ring, first column, last column, y of its back, patch, zone): those faces are
    left out and a pocket goes straight back from their edge (the mouth).
    `lump(ring, column)`: a factor on that point's radius."""
    pts = [Vector(p) for p in pts]
    rr = [r if isinstance(r, tuple) else (r, r) for r in radii]
    n = len(pts)
    dirs = []
    for i in range(n - 1):
        d = pts[i + 1] - pts[i]
        dirs.append(d.normalized() if d.length > 1e-7 else None)

    def near(i, step):
        while 0 <= i < n - 1:
            if dirs[i] is not None:
                return dirs[i]
            i += step
        return None

    frames = []
    xa = Vector(side)
    for i in range(n):
        a, b = near(i - 1, -1), near(i, 1)
        a = a or b
        b = b or a
        t = a + b
        t = t.normalized() if t.length > 1e-7 else a
        xa = xa - t * xa.dot(t)
        if xa.length < 1e-6:
            xa = Vector((0.0, 1.0, 0.0)) - t * t.y
        xa.normalize()
        frames.append((xa.copy(), t.cross(xa)))
    prof = [0.0]
    for i in range(n - 1):
        prof.append(prof[-1] + math.hypot((pts[i + 1] - pts[i]).length, rr[i + 1][0] - rr[i][0]))
    fig.begin(name, part, through)
    rings = []
    angles = [math.pi + math.tau * k / sides + turn for k in range(sides)]
    for i in range(n):
        rx, ry = rr[i]
        if rx <= 1e-9 and ry <= 1e-9:
            rings.append([fig.add(pts[i])])
            continue
        xa, ya = frames[i]
        ring = []
        for k in range(sides):
            s = lump(i, k) if lump else 1.0
            ring.append(fig.add(pts[i] + xa * (rx * s * math.sin(angles[k])) - ya * (ry * s * math.cos(angles[k]))))
        rings.append(ring)
    full = []
    for s in spans:
        opts = s[4] if len(s) > 4 else {}
        last = s[1] if s[1] is not None else n - 1
        full.append((s[0], last, s[2], s[3], opts))
    step = 360.0 / sides
    turn_deg = math.degrees(turn)

    def span_of(i):
        for s in full:
            if s[0] <= i < s[1]:
                return s
        return full[-1]

    def uv(s, i, col, edge):
        """The corner at ring i on column `col`'s near (edge 0), far (1) or middle (0.5) side."""
        v = (prof[i] - prof[s[0]]) / max(prof[s[1]] - prof[s[0]], 1e-9)
        v = min(max(v, 0.0), 1.0)
        opts = s[4]
        mid = wrap180(180.0 + (col + 0.5) * step + turn_deg)
        for (patch, centre, wide) in opts.get("patches", ()):
            rel = wrap180(mid - centre)
            if abs(rel) < wide * 0.5 - 1e-6:
                return uvr(patch, 0.5 + (rel + (edge - 0.5) * step) / wide, v)
        rep = opts.get("repeat", 1)
        ua = col / sides * rep
        ua -= math.floor(ua + 1e-6)
        return uvr(s[2], min(ua + edge * rep / sides, 1.0), v)

    def flat(patch, k, scale):
        a = angles[k]
        return uvr(patch, 0.5 + 0.5 * scale * math.sin(a), 0.5 - 0.5 * scale * math.cos(a))

    for i in range(n - 1):
        A, B = rings[i], rings[i + 1]
        if len(A) == 1 and len(B) == 1:
            continue
        s = span_of(i)
        w = s[4].get("wear", wear)
        for k in range(sides):
            if hole and hole[0] <= i < hole[1] and hole[2] <= k < hole[3]:
                continue
            k2 = (k + 1) % sides
            if len(A) == 1:
                fig.face((A[0], B[k2], B[k]), (uv(s, i, k, 0.5), uv(s, i + 1, k, 1), uv(s, i + 1, k, 0)), s[3], w)
            elif len(B) == 1:
                fig.face((A[k], A[k2], B[0]), (uv(s, i, k, 0), uv(s, i, k, 1), uv(s, i + 1, k, 0.5)), s[3], w)
            else:
                fig.face((A[k], A[k2], B[k2], B[k]),
                         (uv(s, i, k, 0), uv(s, i, k, 1), uv(s, i + 1, k, 1), uv(s, i + 1, k, 0)), s[3], w)
    for end, cap in ((0, cap0), (n - 1, cap1)):
        ring = rings[end]
        if len(ring) == 1:
            continue
        s = span_of(0) if end == 0 else span_of(n - 2)
        w = s[4].get("wear", wear)
        c = fig.add(pts[end])
        big = max(max(rr[end]), 1e-9)
        for k in range(sides):
            k2 = (k + 1) % sides
            if cap:
                uvs = [uvr(cap[0], 0.5, 0.5), flat(cap[0], k, 0.96), flat(cap[0], k2, 0.96)]
                zone = cap[1]
            else:
                uvs = [uv(s, end, k, 0.5), uv(s, end, k, 0), uv(s, end, k, 1)]
                zone = s[3]
            if end == 0:
                fig.face((c, ring[k2], ring[k]), (uvs[0], uvs[2], uvs[1]), zone, w)
            else:
                fig.face((c, ring[k], ring[k2]), (uvs[0], uvs[1], uvs[2]), zone, w)
        del big
    if hole:
        i0, i1, k0, k1, yb, patch, zone = hole
        back = {}
        for i in range(i0, i1 + 1):
            for k in range(k0, k1 + 1):
                p = fig.v[rings[i][k]]
                if p.y > yb - 1e-5:
                    raise SystemExit("the mouth's back wall is in front of its rim: %s" % name)
                back[(i, k)] = fig.add((p.x, yb, p.z))

        def at(i, k, depth):
            return uvr(patch, (k - k0) / (k1 - k0), lerp(0.08, 1.0, depth) * (0.3 + 0.7 * (i - i0) / (i1 - i0)))

        for i in range(i0, i1):
            for k in range(k0, k1):
                fig.face((back[(i, k)], back[(i, k + 1)], back[(i + 1, k + 1)], back[(i + 1, k)]),
                         (at(i, k, 0), at(i, k + 1, 0), at(i + 1, k + 1, 0), at(i + 1, k, 0)), zone, 0.0)

        def wall(a, b):
            fig.face((rings[a[0]][a[1]], rings[b[0]][b[1]], back[b], back[a]),
                     (at(a[0], a[1], 1), at(b[0], b[1], 1), at(b[0], b[1], 0), at(a[0], a[1], 0)), zone, 0.0)

        for k in range(k0, k1):
            wall((i0, k), (i0, k + 1))
            wall((i1, k + 1), (i1, k))
        for i in range(i0, i1):
            wall((i, k1), (i + 1, k1))
            wall((i + 1, k0), (i, k0))
    fig.end()
    return rings


def lathe(fig, name, profile, sides, spans, centre=(0.0, 0.0), **more):
    """A sweep straight up: `profile` is (radius, z) pairs, or ((across, deep), z)."""
    pts = [(centre[0], centre[1], z) for (_r, z) in profile]
    return sweep(fig, name, pts, [r for (r, _z) in profile], sides, spans, **more)


def ball(fig, name, centre, r, sides, patch, zone, part=BODY, wear=0.6, squash=1.0, rings=3):
    c = Vector(centre)
    prof = []
    for j in range(rings + 2):
        a = math.pi * j / (rings + 1)
        prof.append((0.0 if j in (0, rings + 1) else r * math.sin(a), c.z - r * squash * math.cos(a)))
    return lathe(fig, name, prof, sides, [(0, None, patch, zone)], centre=(c.x, c.y), part=part, wear=wear)


def prism(fig, name, poly, z0, z1, side_uv, top, bottom, part=BODY, wear=0.5, mat=None):
    """`poly` ((x, y) points, anticlockwise seen from above) pushed up from z0 to z1.
    side_uv(j) gives (patch, zone, u at point j, u at point j + 1) for side j; top and bottom are (patch, zone)."""
    fig.begin(name, part)
    m = mat or Matrix.Identity(4)
    low = [fig.add(m @ Vector((x, y, z0))) for (x, y) in poly]
    high = [fig.add(m @ Vector((x, y, z1))) for (x, y) in poly]
    n = len(poly)
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]

    def planar(patch, p):
        return uvr(patch, (p[0] - min(xs)) / max(max(xs) - min(xs), 1e-9), (p[1] - min(ys)) / max(max(ys) - min(ys), 1e-9))

    for j in range(n):
        j2 = (j + 1) % n
        patch, zone, ua, ub = side_uv(j)
        fig.face((low[j], low[j2], high[j2], high[j]),
                 (uvr(patch, ua, 0), uvr(patch, ub, 0), uvr(patch, ub, 1), uvr(patch, ua, 1)), zone, wear)
    fig.face(high, [planar(top[0], p) for p in poly], top[1], wear)
    fig.face(low[::-1], [planar(bottom[0], p) for p in poly[::-1]], bottom[1], wear)
    fig.end()


def block(fig, name, centre, half, patch, zone, part=BODY, wear=0.6, mat=None):
    cx, cy, cz = centre
    hx, hy, hz = half
    poly = [(cx - hx, cy - hy), (cx + hx, cy - hy), (cx + hx, cy + hy), (cx - hx, cy + hy)]
    prism(fig, name, poly, cz - hz, cz + hz, lambda j: (patch, zone, 0.0, 1.0), (patch, zone), (patch, zone),
          part=part, wear=wear, mat=mat)


def tuft(fig, name, pts, radii, sides, zone=HAIR, part=BODY, side=(1.0, 0.0, 0.0)):
    """A soft lock of fur: fat near its root, closing to a point. With three sides (the low models) it
    is only its root, its fattest ring and its tip."""
    if sides <= 3 and len(pts) > 3:
        half = len(pts) // 2
        pts = [pts[0], pts[half], pts[-1]]
        radii = [radii[1], radii[half], radii[-1]]
    return sweep(fig, name, pts, radii, sides, [(0, None, "fur", zone)], part=part, side=side, wear=0.0)


def clamp_piece(fig, test, move):
    """Move the points of the piece just made that fail `test` (a flat side cut on it)."""
    piece = fig.pieces[-1]
    for i in range(piece[2], piece[3]):
        if not test(fig.v[i]):
            fig.v[i] = Vector(move(fig.v[i]))


# ================================================================ the figure
def figure(kind, K, lo):
    fig = Fig(kind + ("_lo" if lo else ""))
    fig.lo = lo
    seg = 6 if lo else 12
    hseg = 8 if lo else 12
    small = 4 if lo else 6
    limb = 4 if lo else 6
    lock = 3 if lo else 4
    R = K["head_r"]
    zp = K["plinth"][2]
    plain = lambda zone, **o: [(0, None, "plain", zone, o)]  # noqa: E731

    # ---- the plinth
    shape, pr, ph = K["plinth"]
    wood = [(0, None, "wood_side", NONE, {"repeat": 2, "wear": 0.0})]
    if shape == "round":
        prof = [(pr, 0.0), (pr, ph - 0.004), (pr - 0.006, ph)] if lo else \
            [(pr, 0.0), (pr, ph * 0.45), (pr - 0.005, ph * 0.6), (pr - 0.009, ph)]
        lathe(fig, "plinth", prof, seg, wood, cap1=("wood_top", NONE))
    else:
        sides = 4 if shape == "square" else 8
        r = pr / math.cos(math.pi / sides)
        lathe(fig, "plinth", [(r, 0.0), (r, ph - 0.005), (r - 0.006, ph)], sides, wood, turn=math.pi / sides,
              cap1=("wood_top", NONE))

    # ---- boots and legs, or a robe to the floor
    zb = zp + K["boot_h"]
    br = K["boot_r"]
    for sx in (-1, 1):
        x = sx * K["leg_x"]
        tag = "r" if sx < 0 else "l"
        toe_y = -br * 0.3
        if K.get("robe"):
            toe_y = -K["robe"] + 0.012
        else:
            lr = K["leg_r"]
            hip = K["hip_z"] + 0.008
            if lo:      # boot and leg in one
                lathe(fig, "leg_" + tag, [(br, zp - 0.001), (br, zb), (lr, hip)], limb,
                      [(0, 1, "boot", NONE, {"wear": 0.5}), (1, None, "leg", TROUSERS)],
                      centre=(x, 0.0), turn=sx * math.pi / 2)
            else:
                lathe(fig, "boot_" + tag, [(br, zp - 0.001), (br, zb - 0.007), (br * 1.1, zb)], limb,
                      [(0, None, "boot", NONE, {"wear": 0.5})], centre=(x, 0.0))
                lathe(fig, "leg_" + tag, [(lr, zb - 0.002), (lr * 1.07, lerp(zb, hip, 0.5)), (lr, hip)],
                      limb, [(0, None, "leg", TROUSERS)], centre=(x, 0.0), turn=sx * math.pi / 2)
        sweep(fig, "toe_" + tag, [(x, toe_y, zp + 0.0085), (x, toe_y - br * 0.7 - 0.012, zp + 0.008),
                                  (x, toe_y - br * 0.7 - 0.024, zp + 0.0055)],
              [(br * 0.86, 0.009), (br * 0.8, 0.0085), 0.0], 3 if lo else 4, [(0, None, "boot", NONE, {"wear": 0.9})],
              side=(1.0, 0.0, 0.0), turn=0.0 if lo else math.pi / 4)
    zw = K["waist_z"]
    wr = K["waist_r"]
    cr = K["chest_r"]
    zs = K["shoulder_z"]
    nr = K["neck_r"]
    zn = zs + K["slope"]
    outline = []       # (radius, z) up the body's front, for keeping the beard off it
    if K.get("robe"):
        hem = K["robe"]
        prof = [(hem, zp - 0.001), (hem + 0.002, zp + 0.01), (hem - 0.003, zp + 0.02), (wr, zw + 0.002)]
        if lo:
            prof = [prof[0], prof[2], prof[3]]
            spans = [(0, 1, "ermine", NONE, {"repeat": 6, "wear": 0.0}), (1, None, "plain", COAT)]
        else:
            spans = [(0, 2, "ermine", NONE, {"repeat": 6, "wear": 0.0}), (2, None, "plain", COAT)]
        lathe(fig, "robe", prof, seg, spans)
        outline += prof

    # ---- the coat: skirt, waist, chest, sloping shoulders
    chest = {"patches": [("torso_" + kind, 0.0, 180.0), ("back", 180.0, 180.0)]}
    bh = K["belt_h"]
    prof = []
    if not K.get("robe"):
        prof.append((K["skirt_r"], K["hip_z"] - 0.006))
    prof += [(wr, zw), (wr, zw + bh)]
    first = len(prof) - 1
    if K.get("belly"):
        prof.append((K["belly"], lerp(zw + bh, zs, 0.38)))
    prof += [(cr, zs), (nr + 0.002, zn)]
    belt = ("leather", NONE) if lo else ("plain", COAT)      # the low model's belt is only painted
    spans = [(0, first - 1, "plain", COAT), (first - 1, first, belt[0], belt[1]),
             (first, len(prof) - 2, "plain", COAT, chest), (len(prof) - 2, None, "plain", COAT)]
    if first - 1 == 0:
        spans = spans[1:]
    lathe(fig, "torso", prof, seg, spans, wear=0.3)
    outline += prof
    if not lo:
        lathe(fig, "belt", [(wr + 0.003, zw + 0.0012), (wr + 0.003, zw + bh - 0.0012)], seg, [(0, None, "leather", NONE)],
              wear=0.6)
        block(fig, "buckle", (0.0, -(wr + 0.0035), zw + bh * 0.5), (0.0085, 0.002, bh * 0.5 + 0.001), "plain", TRIM, wear=0.9)
        outline.append((wr + 0.006, zw + bh * 0.5))
    outline.sort(key=lambda rz: rz[1])

    def body_radius(z):
        best = 0.0
        for (r0, z0), (r1, z1) in zip(outline[:-1], outline[1:]):
            if z0 - 1e-9 <= z <= z1 + 1e-9:
                best = max(best, lerp(r0, r1, (z - z0) / max(z1 - z0, 1e-9)))
        return best

    # ---- neck and head
    fh = K["face_h"]
    zc = zn + K["neck_h"]
    zm = zc + paint.MOUTH_V * fh
    zh = zc + fh
    lathe(fig, "neck", [(nr, zn - 0.004), (nr, zc - 0.0006)], 3 if lo else limb, plain(TRIM), wear=0.3)
    face = {"patches": [("face_" + kind, 0.0, 180.0)], "wear": 0.3}
    if lo:      # no slot: the jaw sits against a mouth painted dark
        prof = [(0.0, zc), (R, zc), (R, zh), (R * 0.75, zh + 0.012), (0.0, zh + 0.014)]
        lathe(fig, "head", prof, hseg, [(0, 1, "plain", SKIN), (1, 2, "plain", SKIN, face), (2, None, "plain", SKIN)])
    else:
        prof = [(0.0, zc), (R * 0.6, zc), (R, zc), (R, zm), (R, zh), (R * 0.8, zh + 0.012), (0.0, zh + 0.014)]
        spans = [(0, 2, "plain", SKIN), (2, 4, "plain", SKIN, face), (4, None, "plain", SKIN)]
        # twelve sides, one of them square to the front: the slot is the three in front (90 degrees)
        lathe(fig, "head", prof, hseg, spans, turn=math.pi / hseg,
              hole=(1, 3, hseg // 2 - 2, hseg // 2 + 1, -R * 0.32, "mouth", NONE))
    # the nose: a peg
    nz = zm + 0.2 * fh
    nose = K.get("nose", 0.0052)
    sweep(fig, "nose", [(0.0, -R + 0.004, nz + 0.001), (0.0, -R - 0.008, nz), (0.0, -R - 0.0125, nz - 0.0005)],
          [nose, nose * 1.1, 0.0], 3 if lo else 5, plain(SKIN), wear=1.0)

    # ---- the jaw: a block in the mouth's slot, its beard, and the lever down the back.
    # It turns about a pin at the back of the head, a little above the chin, so the jaw comes almost
    # straight down (its top a few millimetres forwards, its foot a couple back). The beard hangs from it: it follows the jaw's front edge down without turning.
    lip = 0.003
    xw = R * math.sin(math.radians(paint.MOUTH_HALF_DEG)) - 0.0008
    a_max = math.asin(xw / (R + lip))
    cols = 2 if lo else 3
    front = []
    for j in range(cols + 1):
        a = -a_max + 2 * a_max * j / cols
        front.append(((R + lip) * math.sin(a), -(R + lip) * math.cos(a)))
    jy = -R * 0.7
    # its back corners are cut off: the slot in the head is a wedge, narrower towards the back
    xb, ys = -jy - 0.0045, -xw - 0.0045
    poly = [(-xb, jy), (-xw, ys)] + front + [(xw, ys), (xb, jy)]

    def jaw_side(j):
        if 2 <= j <= cols + 1:
            return ("jaw_front", SKIN, (j - 2) / cols, (j - 1) / cols)
        return ("plain", SKIN, 0.0, 1.0)

    prism(fig, "jaw", poly, zc + 0.0008, zm - 0.0008, jaw_side, ("jaw_top", NONE), ("plain", SKIN), part=JAW, wear=0.5)
    back_r = max(cr, K.get("belly", 0.0), wr)
    pivot = Vector((0.0, R * 0.95, lerp(zc, zm, 0.3)))
    fig.marks["jaw"] = pivot
    fig.marks["jawtop"] = Vector((0.0, -(R + lip), zm - 0.0008))
    fig.marks["mouth"] = Vector((0.0, -R * 0.8, zm))
    def clear(z, deep):
        """How far out a lock of the beard this deep must be at height z to stay off the body, also
        when the jaw has carried it down (the beard hangs: it goes down with the jaw and does not turn)."""
        need = 0.0
        for dz in (0.0, -0.008, -0.016, -0.024):
            need = max(need, body_radius(z + dz))
        if need <= 0.0:
            return 0.0
        return need + deep + 0.003

    beard = K["beard"]
    count = 3 if lo else beard.get("count", 5)
    for j in range(count):
        t = j / (count - 1) * 2.0 - 1.0
        long = beard["long"] * (1.0 - beard.get("taper", 0.45) * abs(t) ** 1.5)
        fat = beard.get("fat", 0.011) * (1.3 if lo else 1.0)
        base = R + lip + beard.get("out", 0.009)
        pts = []
        for (drop, spread, deep, more) in ((-0.01, 0.62, 0.003, -0.008), (0.003, 0.8, 0.006, -0.002),
                                           (long * 0.55, 1.0, 0.006, 0.0), (long, 0.92, 0.002, -0.002)):
            ang = math.radians(beard.get("wide", 34.0)) * t * spread
            z = zc - drop
            rad = max(base + more, clear(z, deep))
            pts.append(Vector((math.sin(ang) * rad, -math.cos(ang) * rad, z)))
        ang = math.radians(beard.get("wide", 34.0)) * t
        tuft(fig, "beard_%d" % j, pts, [(fat * 0.55, 0.003), (fat, 0.006), (fat * 0.85, 0.006), 0.0],
             lock, part=BEARD, side=(math.cos(ang), math.sin(ang), 0.0))
    # the lever: out of the back and down, a knob on its end
    lz = pivot.z
    reach = K.get("lever", 0.07)
    lever = [(0.0, pivot.y - 0.004, lz), (0.0, max(R, back_r) + 0.0065, zc - 0.014), (0.0, back_r + 0.008, zc - 0.014 - reach * 0.5),
             (0.0, back_r + 0.011, zc - 0.014 - reach)]
    if lo:
        lever = [lever[1], lever[3]]
    sweep(fig, "lever", lever, [(0.0125, 0.005)] * (len(lever) - 1) + [(0.012, 0.006) if lo else (0.0105, 0.005)],
          3 if lo else 4, plain(COAT, wear=0.8), part=JAW, turn=0.0 if lo else math.pi / 4, through=True)
    if not lo:
        ball(fig, "lever_knob", Vector(lever[-1]) + Vector((0.0, 0.002, -0.004)), 0.0095, 6, "plain", TRIM, part=JAW, wear=1.0, rings=2)

    # ---- hair: locks round the back of the head, under the hat
    hair = K["hair"]
    count = 3 if lo else hair["count"]
    start = hair.get("start", 122.0)
    for j in range(count):
        ang = math.radians(lerp(start, 360.0 - start, j / (count - 1)))
        out = Vector((math.sin(ang), -math.cos(ang), 0.0))
        along = Vector((math.cos(ang), math.sin(ang), 0.0))
        long = hair["long"] * (1.0 + 0.12 * math.cos(j * 2.4))
        fat = 0.0145 * (1.7 if lo else 1.0) * hair.get("fat", 1.0)
        z0 = zh + 0.002
        tuft(fig, "hair_%d" % j,
             [out * (R - 0.005) + Vector((0, 0, z0)), out * (R + 0.006) + Vector((0, 0, z0 - long * 0.3)),
              out * (R + 0.0085) + Vector((0, 0, z0 - long * 0.7)), out * (R + 0.004) + Vector((0, 0, z0 - long))],
             [(fat * 0.75, 0.004), (fat, 0.0065), (fat * 0.8, 0.006), 0.0], lock, side=along)

    # ---- the moustache: two locks from under the nose
    tz = zm + 0.15 * fh
    fig.marks["tash"] = Vector((0.0, -R, tz))
    tash = K.get("tash")
    if tash:
        for sx in (-1, 1):
            pts = []
            for (deg, dz, off) in tash["path"]:
                a = math.radians(deg) * sx
                pts.append(Vector((math.sin(a) * (R + off), -math.cos(a) * (R + off), tz + dz)))
            radii = [(r * 0.55, r) for r in tash["fat"]] + [0.0]
            tuft(fig, "tash_" + ("r" if sx < 0 else "l"), pts, radii, lock, zone=HAIR, part=TASH, side=(0.0, 1.0, 0.0))

    # ---- arms on their pegs
    ar = K["arm_r"]
    ax = max(cr, K.get("skirt_r", 0.0), K.get("belly", 0.0)) + ar + 0.0015
    az = zs - 0.011
    K = dict(K, arm_x=ax, arm_z=az)
    hands = {}
    for sx in (-1, 1):
        tag = "arm_r" if sx < 0 else "arm_l"
        part = ARM_R if sx < 0 else ARM_L
        piv = Vector((sx * ax, 0.0, az))
        fig.marks["armr" if sx < 0 else "arml"] = piv
        bent = K["bent"][0 if sx < 0 else 1]
        hr = ar * 1.06
        up = Vector((0.0, 0.0, 1.0))
        if bent is None:
            z0 = az - K["arm_len"]
            hand_at = Vector((piv.x, 0, z0 - 0.0105))
            fd = up
            run = [Vector((piv.x, 0, z0 + 0.024)), piv]
        else:
            fore, upper, inward, drop = bent
            elbow = piv - up * upper
            hand_at = elbow + Vector((-sx * inward, -fore, -drop))
            fd = (elbow - hand_at).normalized()
            run = [hand_at + fd * 0.0345, elbow - fd * 0.008 - up * 0.002, elbow + up * 0.012, piv]
        if lo:
            pts = [hand_at - fd * 0.0135, hand_at, hand_at + fd * 0.0105] + run[1:] + [piv + up * ar * 0.8]
            radii = [0.0, (hr * 0.82, hr), ar] + [ar] * (len(run) - 1) + [0.0]
            sleeve_from = 2
        else:
            pts = [hand_at - fd * 0.0125, hand_at - fd * 0.0095, hand_at, hand_at + fd * 0.0105, hand_at + fd * 0.0345]
            pts += run + [piv + up * ar * 0.72, piv + up * ar]
            radii = [0.0, (hr * 0.7, hr * 0.84), (hr * 0.85, hr * 1.04), ar * 1.1, ar * 1.1] + [ar] * len(run) + [ar * 0.74, 0.0]
            sleeve_from = 3
        sweep(fig, tag, pts, radii, limb, [(0, sleeve_from, "hand", SKIN, {"wear": 0.8}), (sleeve_from, None, "sleeve", COAT)],
              part=part, turn=sx * math.pi / 2, wear=0.35)
        hands[sx] = Vector(hand_at)
        # the epaulette on top of it, cut flat where it meets the body
        ez = az + ar - 0.0015
        er = ar * 1.55
        prof = [(0.0, ez + 0.0055), (er * 0.72, ez + 0.0055), (er, ez + 0.002), (er, ez - 0.0075), (0.0, ez - 0.0075)]
        if lo:
            prof = [(0.0, ez + 0.005), (er, ez + 0.002), (er, ez - 0.0075), (0.0, ez - 0.0075)]
        lathe(fig, tag + "_epaulette", prof, 4 if lo else 6, [(0, None, "epaulette", TRIM, {"wear": 0.9})],
              centre=(piv.x + sx * 0.004, 0.0), part=part)
        limit = ax - ar + 0.0005
        clamp_piece(fig, lambda p: p.x * sx >= limit, lambda p: (sx * limit, p.y, p.z))
        if not lo:
            # the peg's end showing on the outside of the shoulder
            sweep(fig, tag + "_pin", [(piv.x + sx * (ar - 0.002), 0, az), (piv.x + sx * (ar + 0.0025), 0, az)],
                  [0.0055, 0.0045], 4, plain(TRIM, wear=1.0), part=part, side=(0.0, 1.0, 0.0))
    return fig, K, hands, dict(zc=zc, zm=zm, zh=zh, R=R, seg=seg, small=small, lo=lo, lock=lock)


# ================================================================ hats and what they carry
def band(fig, name, r, z0, z1, seg, zone=TRIM, patch="plain", **opts):
    lathe(fig, name, [(r, z0), (r, z1)], seg, [(0, None, patch, zone, opts)], wear=0.8)


def visor(fig, R, z, reach, lo):
    """A peak: a thin disc cut off behind the brow and tipped down at the front."""
    lathe(fig, "visor", [(0.0, z - 0.0018), (R + reach, z - 0.0018), (R + reach - 0.002, z + 0.0018), (0.0, z + 0.0018)],
          4 if lo else 10, [(0, None, "leather", NONE)], wear=0.9, turn=math.pi / 4 if lo else 0.0)
    cut = -R * 0.45
    piece = fig.pieces[-1]
    for i in range(piece[2], piece[3]):
        p = fig.v[i]
        y = min(p.y, cut)
        fig.v[i] = Vector((p.x, y, p.z - 0.28 * (cut - y)))


def hat_soldier(fig, K, H):
    R, zh, seg, lo = H["R"], H["zh"], H["seg"], H["lo"]
    prof = [(R + 0.0045, zh - 0.003), (R + 0.009, zh + 0.078), (R + 0.0105, zh + 0.0815), (R + 0.006, zh + 0.084)]
    spans = [(0, 1, "plain", HAT, {"patches": [("shako", 0.0, 180.0)]}), (1, None, "plain", HAT)]
    if lo:
        prof = [prof[0], prof[1], prof[3]]
    lathe(fig, "shako", prof, seg, spans, wear=0.45)
    if not lo:
        band(fig, "shako_band", R + 0.0066, zh - 0.002, zh + 0.008, seg)
    visor(fig, R, zh + 0.001, 0.021, lo)
    ball(fig, "pompom", (0.0, -(R + 0.002), zh + 0.094), 0.0125, 4 if lo else 6, "fur", TRIM, wear=0.0, rings=1 if lo else 2)


def hat_king(fig, K, H):
    R, zh, seg, lo, small = H["R"], H["zh"], H["seg"], H["lo"], H["small"]
    prof = [(R + 0.004, zh - 0.007), (R + 0.0095, zh - 0.003), (R + 0.0095, zh + 0.008), (R + 0.0065, zh + 0.0105),
            (R + 0.007, zh + 0.031)]
    spans = [(0, 2, "ermine", NONE, {"repeat": 6, "wear": 0.0}), (2, 3, "plain", TRIM),
             (3, None, "crown", TRIM, {"repeat": 6, "wear": 0.7})]
    if lo:
        prof = [(R + 0.009, zh - 0.006), (R + 0.009, zh + 0.009), (R + 0.007, zh + 0.031)]
        spans = [(0, 1, "ermine", NONE, {"repeat": 6, "wear": 0.0}), (1, None, "crown", TRIM, {"repeat": 6, "wear": 0.7})]
    lathe(fig, "crown", prof, seg, spans)
    prof = [(R + 0.002, zh + 0.029), (R * 0.82, zh + 0.047), (0.0, zh + 0.056)]
    lathe(fig, "crown_cap", prof, seg, [(0, None, "plain", COAT)], wear=0.2)
    for j in range(6):
        a = math.radians(60.0 * j)
        out = Vector((math.sin(a), -math.cos(a), 0.0))
        along = (math.cos(a), math.sin(a), 0.0)
        base = out * (R + 0.0055)
        pts = [base + Vector((0, 0, zh + 0.029)), base + Vector((0, 0, zh + 0.04)), base + out * 0.002 + Vector((0, 0, zh + 0.053))]
        radii = [(0.009, 0.0028), (0.0065, 0.0028), 0.0]
        if lo:
            pts, radii = [pts[0], pts[2]], [radii[0], 0.0]
        sweep(fig, "crown_point_%d" % j, pts, radii, 3, [(0, None, "plain", TRIM)], side=along, wear=1.0)
    ball(fig, "crown_knob", (0.0, 0.0, zh + 0.061), 0.0065, small, "plain", TRIM, rings=1 if lo else 2)


def hat_drummer(fig, K, H):
    R, zh, seg, lo = H["R"], H["zh"], H["seg"], H["lo"]
    prof = [(R + 0.0045, zh - 0.003), (R + 0.005, zh + 0.035), (R + 0.002, zh + 0.039)]
    lathe(fig, "kepi", prof, seg, [(0, 1, "plain", HAT, {"patches": [("kepi", 0.0, 120.0)]}), (1, None, "plain", HAT)], wear=0.45)
    visor(fig, R, zh + 0.001, 0.017, lo)
    c = Vector((0.0, -(R + 0.004), zh + 0.03))
    tuft(fig, "plume", [c, c + Vector((0, -0.003, 0.022)), c + Vector((0, -0.006, 0.05)), c + Vector((0, -0.016, 0.07))],
         [0.005, (0.011, 0.009), (0.0095, 0.008), 0.0], 3 if lo else 5, zone=COAT)


def hat_guard(fig, K, H):
    R, zh, seg, lo = H["R"], H["zh"], H["seg"], H["lo"]
    rows = [(R + 0.004, zh - 0.004, 0.0), (R + 0.012, zh + 0.006, -0.001), (R + 0.0165, zh + 0.045, -0.003),
            (R + 0.0135, zh + 0.088, -0.005), (R * 0.72, zh + 0.112, -0.005), (0.0, zh + 0.119, -0.005)]
    if lo:
        rows = [rows[0], rows[2], rows[3], rows[5]]
    sweep(fig, "bearskin", [(0.0, y, z) for (_r, z, y) in rows], [r for (r, _z, _y) in rows], seg,
          [(0, None, "fur", HAT, {"repeat": 3})], wear=0.0,
          lump=None if lo else (lambda i, k: 1.0 + (0.035 if (i + k) % 2 else -0.02) * (1 if 0 < i else 0)))
    c = Vector((R + 0.012, 0.0, zh + 0.03))
    tuft(fig, "plume", [c, c + Vector((0.007, 0, 0.012)), c + Vector((0.009, 0, 0.034)), c + Vector((0.005, 0, 0.05))],
         [0.004, (0.008, 0.007), (0.007, 0.006), 0.0], H["lock"], zone=COAT, side=(0.0, 1.0, 0.0))


def hat_baker(fig, K, H):
    R, zh, seg, lo = H["R"], H["zh"], H["seg"], H["lo"]
    linen = [(0, None, "linen", NONE, {"repeat": 3, "wear": 0.0})]
    rows = [(R + 0.0045, zh - 0.004, 0.0), (R + 0.005, zh + 0.028, 0.0), (R + 0.022, zh + 0.04, 0.002),
            (R + 0.03, zh + 0.063, 0.005), (R + 0.02, zh + 0.084, 0.008), (0.0, zh + 0.092, 0.009)]
    if lo:
        rows = [rows[0], rows[1], rows[3], rows[5]]
    sweep(fig, "toque", [(x, 0.0, z) for (_r, z, x) in rows], [r for (r, _z, _x) in rows], seg, linen,
          lump=lambda i, k: 1.0 + (0.07 if k % 2 else -0.05) * (1 if 1 < i else 0))


def rod(fig, name, hand, z0, z1, r, sides, patch, zone, part, wear=0.8):
    lathe(fig, name, [(r, hand.z + z0), (r, hand.z + z1)], sides, [(0, None, patch, zone, {"wear": wear})],
          centre=(hand.x, hand.y), part=part)


def carry_king(fig, K, H, hands):
    lo, small = H["lo"], H["small"]
    h = hands[-1]
    rod(fig, "sceptre", h, -0.05, 0.1, 0.0045, 3 if lo else 5, "plain", TRIM, ARM_R)
    ball(fig, "sceptre_orb", (h.x, h.y, h.z + 0.11), 0.0145, small, "plain", TRIM, part=ARM_R, rings=1 if lo else 2)
    if not lo:
        ball(fig, "sceptre_tip", (h.x, h.y, h.z + 0.128), 0.0055, 4, "plain", COAT, part=ARM_R, rings=1)


def carry_guard(fig, K, H, hands):
    lo = H["lo"]
    h = hands[-1]
    lathe(fig, "sword_blade", [((0.0075, 0.0016), h.z + 0.016), ((0.0068, 0.0014), h.z + 0.15), (0.0, h.z + 0.172)], 4,
          [(0, None, "metal", NONE, {"wear": 0.0, "repeat": 2})], centre=(h.x, h.y), part=ARM_R)
    block(fig, "sword_guard", (h.x, h.y, h.z + 0.0145), (0.017, 0.0042, 0.0026), "plain", TRIM, part=ARM_R, wear=1.0)
    rod(fig, "sword_grip", h, -0.02, 0.013, 0.0042, 3 if lo else 5, "leather", NONE, ARM_R)
    if not lo:
        ball(fig, "sword_pommel", (h.x, h.y, h.z - 0.023), 0.0062, 5, "plain", TRIM, part=ARM_R, rings=1)


def carry_baker(fig, K, H, hands):
    lo = H["lo"]
    h = hands[-1]
    wood = [(0, None, "wood_side", NONE, {"wear": 0.0})]
    prof = [(0.004, h.z - 0.022), (0.004, h.z + 0.02), (0.0115, h.z + 0.022), (0.0125, h.z + 0.06), (0.0115, h.z + 0.098),
            (0.004, h.z + 0.1), (0.0045, h.z + 0.118)]
    if lo:
        prof = [prof[0], prof[1], prof[2], prof[4], prof[5], prof[6]]
    lathe(fig, "rolling_pin", prof, 4 if lo else 6, wood, centre=(h.x, h.y), part=ARM_R)


def carry_drummer(fig, K, H, hands):
    lo, seg = H["lo"], H["seg"]
    # the drum, slung in front, its top tipped forwards
    wr = K["waist_r"]
    tilt = math.radians(24.0)
    axis = Vector((0.0, -math.sin(tilt), math.cos(tilt)))
    dr, dh = 0.036, 0.038
    c = Vector((0.0, -(wr + dr * 0.82), K["waist_z"] - 0.012))
    side = [(0, None, "drum_side", COAT, {"repeat": 2})]
    sweep(fig, "drum", [c - axis * dh * 0.5, c + axis * dh * 0.5], [dr, dr], seg, side, cap0=("drum_head", NONE),
          cap1=("drum_head", NONE), wear=0.4)
    top = c + axis * dh * 0.5
    if not lo:
        for name, t in (("drum_rim_a", -0.5), ("drum_rim_b", 0.5)):
            sweep(fig, name, [c + axis * (dh * t - 0.0035), c + axis * (dh * t + 0.0035)], [dr + 0.0022, dr + 0.0022], seg,
                  [(0, None, "plain", TRIM)], wear=0.9)
        top = c + axis * (dh * 0.5 + 0.0035)
    fig.marks["drum"] = top
    for sx in (-1, 1):
        part = ARM_R if sx < 0 else ARM_L
        h = hands[sx]
        tip_r = 0.0042
        # where the bead of the stick rests: just off the skin, a little to its own side
        across = Vector((1.0, 0.0, 0.0))
        down = across.cross(axis)
        rest = top + across * (sx * 0.011) + down * 0.004 + axis * (tip_r + 0.0012)
        d = (rest - h).normalized()
        tag = "stick_r" if sx < 0 else "stick_l"
        sweep(fig, tag, [h - d * 0.016, h + d * ((rest - h).length - tip_r * 0.6)], [0.0026, 0.0021], 3 if lo else 4,
              [(0, None, "wood_side", NONE, {"wear": 0.0})], part=part)
        ball(fig, tag + "_bead", rest, tip_r, 4, "plain", NONE, part=part, rings=1, wear=0.0)


# ================================================================ the five
# a moustache: (degrees round the face, up or down, how far it stands off) along one side; how fat
HANDLEBAR = dict(path=[(4, 0.0005, 0.0045), (18, -0.001, 0.005), (32, 0.0, 0.005), (44, 0.0065, 0.0045)], fat=[0.0032, 0.0042, 0.0034])
WALRUS = dict(path=[(3, 0.001, 0.0045), (22, 0.0, 0.006), (42, -0.001, 0.006), (53, -0.012, 0.005), (57, -0.026, 0.004)],
              fat=[0.0042, 0.0055, 0.005, 0.0038])
CHEVRON = dict(path=[(3, 0.001, 0.0045), (18, 0.0, 0.005), (36, -0.0015, 0.005), (50, -0.009, 0.0045)], fat=[0.004, 0.005, 0.004])
CURL = dict(path=[(4, 0.0, 0.0045), (20, -0.0015, 0.0055), (36, 0.0, 0.006), (45, 0.007, 0.0065), (41, 0.0125, 0.007)],
            fat=[0.0036, 0.0046, 0.004, 0.0028])

SPECS = {
    "soldier": dict(
        plinth=("square", 0.056, 0.02), boot_h=0.064, boot_r=0.0195, leg_x=0.0205, leg_r=0.017, hip_z=0.158,
        skirt_r=0.043, waist_z=0.174, waist_r=0.034, belt_h=0.012, chest_r=0.039, shoulder_z=0.262, slope=0.024,
        neck_r=0.016, neck_h=0.013, head_r=0.035, face_h=0.068, arm_r=0.0132, arm_len=0.112, bent=(None, None),
        beard=dict(long=0.05, count=5), hair=dict(count=4, long=0.052, fat=1.2), tash=HANDLEBAR, hat=hat_soldier, carry=None),
    "king": dict(
        plinth=("round", 0.07, 0.024), boot_h=0.03, boot_r=0.02, leg_x=0.024, robe=0.062,
        waist_z=0.158, waist_r=0.05, belt_h=0.013, belly=0.0545, chest_r=0.048, shoulder_z=0.236, slope=0.026,
        neck_r=0.018, neck_h=0.016, head_r=0.04, face_h=0.072, arm_r=0.0145, arm_len=0.1,
        bent=((0.052, 0.056, 0.0, 0.004), None), nose=0.0062,
        beard=dict(long=0.08, count=5, fat=0.0135, taper=0.5, out=0.011), hair=dict(count=4, long=0.062, fat=1.45),
        tash=WALRUS, hat=hat_king, carry=carry_king),
    "drummer": dict(
        plinth=("octagon", 0.058, 0.02), boot_h=0.046, boot_r=0.02, leg_x=0.021, leg_r=0.0175, hip_z=0.112,
        skirt_r=0.044, waist_z=0.126, waist_r=0.036, belt_h=0.011, chest_r=0.04, shoulder_z=0.196, slope=0.024,
        neck_r=0.017, neck_h=0.013, head_r=0.039, face_h=0.07, arm_r=0.0135, arm_len=0.09,
        bent=((0.05, 0.04, 0.012, -0.006), (0.05, 0.04, 0.012, -0.006)),
        beard=dict(long=0.02, count=3, wide=20.0, fat=0.009, out=0.006), hair=dict(count=4, long=0.05, fat=1.2), tash=None,
        hat=hat_drummer, carry=carry_drummer),
    "guard": dict(
        plinth=("square", 0.05, 0.022), boot_h=0.07, boot_r=0.018, leg_x=0.019, leg_r=0.0155, hip_z=0.19,
        skirt_r=0.039, waist_z=0.206, waist_r=0.03, belt_h=0.012, chest_r=0.036, shoulder_z=0.302, slope=0.023,
        neck_r=0.015, neck_h=0.013, head_r=0.033, face_h=0.064, arm_r=0.0122, arm_len=0.125,
        bent=((0.046, 0.058, 0.0, 0.0), None),
        beard=dict(long=0.036, count=5, fat=0.0095, out=0.008), hair=dict(count=4, long=0.04, start=128.0, fat=1.1), tash=CHEVRON,
        hat=hat_guard, carry=carry_guard),
    "baker": dict(
        plinth=("round", 0.066, 0.02), boot_h=0.04, boot_r=0.021, leg_x=0.024, leg_r=0.019, hip_z=0.112,
        skirt_r=0.054, waist_z=0.128, waist_r=0.05, belt_h=0.008, belly=0.056, chest_r=0.046, shoulder_z=0.222, slope=0.025,
        neck_r=0.018, neck_h=0.016, head_r=0.04, face_h=0.07, arm_r=0.0145, arm_len=0.1,
        bent=((0.05, 0.054, 0.0, 0.002), None), nose=0.0066,
        beard=dict(long=0.018, count=3, wide=18.0, fat=0.009, out=0.006), hair=dict(count=4, long=0.046, fat=1.2), tash=CURL,
        hat=hat_baker, carry=carry_baker),
}


def build_kind(kind, lo):
    fig, K, hands, H = figure(kind, SPECS[kind], lo)
    K["hat"](fig, K, H)
    if K["carry"]:
        K["carry"](fig, K, H, hands)
    return fig


def build_walnut(which, lo):
    """A walnut: 22 mm across, 27 mm long, standing on end at the origin's level. Halves are cut along
    the seam (the plane x = 0): `a` is the half at +x, `b` the one at -x."""
    fig = Fig("walnut_" + which + ("_lo" if lo else ""))
    sides = 6 if lo else 10
    rings = 3 if lo else 5
    r, tall = 0.011, 0.027
    prof = []
    for j in range(rings + 2):
        a = math.pi * j / (rings + 1)
        prof.append((0.0 if j in (0, rings + 1) else r * math.sin(a) ** 0.85, tall * 0.5 * (1.0 - math.cos(a))))

    def lump(i, k):
        seam = 1.07 if k % (sides // 2) == 0 else 1.0
        return seam * (1.0 + 0.035 * math.sin(i * 2.3 + k * 1.7))

    lathe(fig, "shell", prof, sides, [(0, None, "walnut", NONE, {"repeat": 2, "wear": 0.0})], lump=lump, wear=0.0)
    if which != "whole":
        sx = 1.0 if which == "half_a" else -1.0
        piece = fig.pieces[-1]
        for i in range(piece[2], piece[3]):
            if fig.v[i].x * sx < 0.0:
                fig.v[i].x = 0.0
        for n in range(piece[4], piece[5]):
            idx, uvs, zone, part, wear = fig.faces[n]
            if all(abs(fig.v[i].x) < 1e-9 for i in idx):
                uvs = tuple(uvr("kernel", 0.5 + sx * fig.v[i].y / (r * 2.3), fig.v[i].z / tall) for i in idx)
                fig.faces[n] = (idx, uvs, zone, part, wear)
    return fig


# ================================================================ checks
def piece_tris(fig, piece):
    tris = []
    for n in range(piece[4], piece[5]):
        idx = fig.faces[n][0]
        for j in range(1, len(idx) - 1):
            tris.append((idx[0], idx[j], idx[j + 1]))
    return tris


def check_skins(fig):
    """Every piece must be a closed skin wound outwards: each edge used once each way, volume over 0."""
    for piece in fig.pieces:
        edges = {}
        for n in range(piece[4], piece[5]):
            idx = fig.faces[n][0]
            if len(set(idx)) != len(idx):
                raise SystemExit("BAD FACE: %s %s uses a corner twice" % (fig.name, piece[0]))
            for a, b in zip(idx, idx[1:] + idx[:1]):
                edges[(a, b)] = edges.get((a, b), 0) + 1
        for (a, b), count in edges.items():
            if count != 1 or edges.get((b, a), 0) != 1:
                p = fig.v[a]
                raise SystemExit("NOT A CLOSED SKIN: %s %s, at (%.4f, %.4f, %.4f)" % (fig.name, piece[0], p.x, p.y, p.z))
        volume = 0.0
        for (a, b, c) in piece_tris(fig, piece):
            volume += fig.v[a].dot(fig.v[b].cross(fig.v[c])) / 6.0
        if volume <= 1e-12:
            raise SystemExit("INSIDE OUT: %s %s (volume %.3g)" % (fig.name, piece[0], volume))


def posed(fig, part, jaw=0.0, arm=(0.0, 0.0), tash=0.0):
    """Where a part's points are when it is turned as the game's shader turns it (degrees)."""
    if part == JAW:
        m = Matrix.Translation(fig.marks["jaw"]) @ Matrix.Rotation(math.radians(jaw), 4, "X") @ Matrix.Translation(-fig.marks["jaw"])
    elif part in (ARM_R, ARM_L):
        piv = fig.marks["armr" if part == ARM_R else "arml"]
        lean = arm[1] if part == ARM_R else -arm[1]      # towards the hat when the arm is up
        m = (Matrix.Translation(piv) @ Matrix.Rotation(math.radians(lean), 4, "Y")
             @ Matrix.Rotation(math.radians(arm[0]), 4, "X") @ Matrix.Translation(-piv))
    elif part == BEARD:
        hang = fig.marks["jawtop"]
        m = Matrix.Translation(posed(fig, JAW, jaw=jaw) @ hang - hang)
    elif part == TASH:
        piv = fig.marks["tash"]
        m = Matrix.Translation(piv) @ Matrix.Rotation(math.radians(-tash), 4, "Y") @ Matrix.Translation(-piv)
    else:
        m = Matrix.Identity(4)
    return m


def tree_of(fig, part, m, skip=(), only_through=None, also=()):
    verts = []
    tris = []
    whose = []
    where = dict([(part, m)] + list(also))
    for piece in fig.pieces:
        if piece[1] not in where or piece[0] in skip:
            continue
        m = where[piece[1]]
        if only_through is not None and piece[6] != only_through:
            continue
        base = len(verts) - piece[2]
        verts += [m @ fig.v[i] for i in range(piece[2], piece[3])]
        mine = [(a + base, b + base, c + base) for (a, b, c) in piece_tris(fig, piece)]
        tris += mine
        whose += [piece[0]] * len(mine)
    if not tris:
        return None, [], []
    return BVHTree.FromPolygons(verts, tris, epsilon=0.0), verts, whose


def gap(tree_a, verts_a, whose_a, tree_b, verts_b, whose_b):
    """Which pieces of two parts cut into each other ("" if none), and about how near the parts come
    (from their points)."""
    if tree_a is None or tree_b is None:
        return "", 9.0
    pairs = sorted(set("%s/%s" % (whose_a[i], whose_b[j]) for (i, j) in tree_a.overlap(tree_b)))
    cut = ", ".join(pairs)
    near = 9.0
    for p in verts_a:
        hit = tree_b.find_nearest(p)
        if hit[3] is not None:
            near = min(near, hit[3])
    for p in verts_b:
        hit = tree_a.find_nearest(p)
        if hit[3] is not None:
            near = min(near, hit[3])
    return cut, near


def check_poses(fig, kind):
    """Turn the jaw and the arms through all their travel and see that nothing cuts into anything."""
    problems = []
    notes = []
    body = tree_of(fig, BODY, Matrix.Identity(4))
    # the low model has no slot for the jaw: its jaw sits in the head on purpose
    body_for_jaw = tree_of(fig, BODY, Matrix.Identity(4), skip=("head",)) if fig.lo else body
    # the lever goes into the back of the neck on purpose: against it, leave those pieces out
    body_for_lever = tree_of(fig, BODY, Matrix.Identity(4), skip=("torso", "neck", "head"))
    r0, r1, l0, l1 = ARM_RANGE[kind]
    jaws = [0.0, JAW_MAX * 0.5, JAW_MAX]
    least = 9.0
    for jaw in jaws:
        m = posed(fig, JAW, jaw=jaw)
        mouth = tree_of(fig, JAW, m, only_through=False, also=[(BEARD, posed(fig, BEARD, jaw=jaw))])
        lever = tree_of(fig, JAW, m, only_through=True)
        cut, near = gap(*mouth, *body_for_jaw)
        least = min(least, near)
        if cut:
            problems.append("the jaw cuts into the body at %g degrees (%s)" % (jaw, cut))
        cut, near = gap(*lever, *body_for_lever)
        if cut:
            problems.append("the lever cuts into the body at %g degrees (%s)" % (jaw, cut))
        for part, lo_, hi_ in ((ARM_R, r0, r1), (ARM_L, l0, l1)):
            a = lo_
            while a <= hi_ + 1e-6:
                arm = tree_of(fig, part, posed(fig, part, arm=(a, 0.0)))
                for other, what in ((mouth, "jaw"), (lever, "lever")):
                    cut, near = gap(*arm, *other)
                    if cut:
                        problems.append("arm %d at %g cuts into the %s at %g (%s)" % (part, a, what, jaw, cut))
                a += 5.0
    notes.append("jaw to body %.1f mm" % (least * 1000.0))
    for part, lo_, hi_, name in ((ARM_R, r0, r1, "right arm"), (ARM_L, l0, l1, "left arm")):
        a = lo_
        least = 9.0
        while a <= hi_ + 1e-6:
            arm = tree_of(fig, part, posed(fig, part, arm=(a, 0.0)))
            cut, near = gap(*arm, *body)
            least = min(least, near)
            if cut:
                problems.append("the %s cuts into the body at %g degrees (%s)" % (name, a, cut))
            a += 5.0
        notes.append("%s to body %.1f mm" % (name, least * 1000.0))
    swing, lean = SALUTE[kind]
    for s in (0.25, 0.5, 0.75, 1.0):
        arm = tree_of(fig, ARM_R, posed(fig, ARM_R, arm=(swing * s, lean * s)))
        cut, near = gap(*arm, *body)
        if cut:
            problems.append("the salute cuts into the body %d%% of the way up (%s)" % (s * 100, cut))
        if s == 1.0:
            notes.append("salute to body %.1f mm" % (near * 1000.0))
    # the two arms against each other where they could meet (the drummer's sticks)
    for a in (r0, r0 * 0.5, 0.0, r1):
        for b in (l0, l0 * 0.5, 0.0, l1):
            cut, near = gap(*tree_of(fig, ARM_R, posed(fig, ARM_R, arm=(a, 0.0))), *tree_of(fig, ARM_L, posed(fig, ARM_L, arm=(b, 0.0))))
            if cut:
                problems.append("the arms cut into each other at %g and %g (%s)" % (a, b, cut))
    for t in (-TASH_TILT, TASH_TILT):
        tash = tree_of(fig, TASH, posed(fig, TASH, tash=t))
        for jaw in jaws:
            cut, near = gap(*tash, *tree_of(fig, JAW, posed(fig, JAW, jaw=jaw), only_through=False,
                                            also=[(BEARD, posed(fig, BEARD, jaw=jaw))]))
            if cut:
                problems.append("the moustache at %g cuts into the jaw at %g (%s)" % (t, jaw, cut))
    return problems, notes


# ================================================================ into Blender
def make_object(fig, parent, mat):
    mesh = bpy.data.meshes.new(fig.name)
    mesh.from_pydata([tuple(p) for p in fig.v], [], [f[0] for f in fig.faces])
    mesh.uv_layers.new(name="UVMap")
    mesh.uv_layers.new(name="ids")
    mesh.color_attributes.new(name="tint", type='FLOAT_COLOR', domain='CORNER')
    uv = mesh.uv_layers["UVMap"]
    ids = mesh.uv_layers["ids"]
    tint = mesh.color_attributes["tint"]
    loop = 0
    for (_idx, uvs, zone, part, wear) in fig.faces:
        # the second UV set: u which part; v which colour it wears and how readily it chips. The glTF
        # exporter turns v upside down, so it is written upside down here.
        code = ((part + 0.5) / 8.0, 1.0 - (zone + 0.05 + 0.9 * min(max(wear, 0.0), 1.0)) / 8.0)
        shown = SHOW[zone]
        for one in uvs:
            uv.data[loop].uv = one
            ids.data[loop].uv = code
            tint.data[loop].color = (shown[0] ** 2.2, shown[1] ** 2.2, shown[2] ** 2.2, 1.0)
            loop += 1
    mesh.materials.append(mat)
    for poly in mesh.polygons:
        poly.use_smooth = True
    mesh.update()
    mesh.set_sharp_from_angle(angle=math.radians(64.0))
    mesh.uv_layers.active = uv
    uv.active_render = True
    obj = bpy.data.objects.new(fig.name + "_mesh", mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.parent = parent
    # which points move with which part, for anyone posing it by hand in Blender
    names = ["body", "jaw", "arm_r", "arm_l", "moustache", "beard"]
    for piece in fig.pieces:
        group = obj.vertex_groups.get(names[piece[1]]) or obj.vertex_groups.new(name=names[piece[1]])
        group.add(list(range(piece[2], piece[3])), 1.0, 'REPLACE')
    for name, at in fig.marks.items():
        mark = bpy.data.objects.new("%s_%s" % (fig.name, name), None)
        mark.empty_display_type = 'PLAIN_AXES'
        mark.empty_display_size = 0.01
        bpy.context.scene.collection.objects.link(mark)
        mark.parent = parent
        mark.location = at
    return obj


def save_png(path, rgba):
    h, w, _ = rgba.shape
    image = bpy.data.images.new(os.path.basename(path), w, h, alpha=True)
    image.alpha_mode = 'STRAIGHT'
    image.pixels.foreach_set(np.clip(rgba, 0.0, 1.0).astype(np.float32).ravel())
    image.filepath_raw = path
    image.file_format = 'PNG'
    image.save()
    bpy.data.images.remove(image)


def show_material():
    """How the .blend shows them: the game's sums, in the classic colours."""
    mat = bpy.data.materials.new("nutcracker_show")
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    shader = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
    shader.inputs["Roughness"].default_value = 0.35
    pictures = {}
    for key, file, space in (("paint", "nutcracker_paint.png", "sRGB"), ("masks", "nutcracker_masks.png", "Non-Color")):
        image = bpy.data.images.load(os.path.join(TEXTURES, file))
        image.colorspace_settings.name = space
        image.alpha_mode = 'CHANNEL_PACKED'
        node = nodes.new("ShaderNodeTexImage")
        node.image = image
        pictures[key] = node
    tint = nodes.new("ShaderNodeAttribute")
    tint.attribute_name = "tint"
    split = nodes.new("ShaderNodeSeparateColor")
    links.new(pictures["masks"].outputs["Color"], split.inputs["Color"])
    a = nodes.new("ShaderNodeMix")
    a.data_type = 'RGBA'
    links.new(split.outputs["Red"], a.inputs["Factor"])
    links.new(tint.outputs["Color"], a.inputs["A"])
    a.inputs["B"].default_value = (SHOW[TRIM][0] ** 2.2, SHOW[TRIM][1] ** 2.2, SHOW[TRIM][2] ** 2.2, 1.0)
    b = nodes.new("ShaderNodeMix")
    b.data_type = 'RGBA'
    links.new(pictures["paint"].outputs["Alpha"], b.inputs["Factor"])
    links.new(a.outputs["Result"], b.inputs["A"])
    links.new(pictures["paint"].outputs["Color"], b.inputs["B"])
    tone = nodes.new("ShaderNodeMath")
    tone.operation = 'MULTIPLY'
    links.new(split.outputs["Green"], tone.inputs[0])
    tone.inputs[1].default_value = 1.0 / 0.75
    c = nodes.new("ShaderNodeVectorMath")
    c.operation = 'SCALE'
    links.new(b.outputs["Result"], c.inputs[0])
    links.new(tone.outputs["Value"], c.inputs["Scale"])
    links.new(c.outputs["Vector"], shader.inputs["Base Color"])
    return mat


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = next((a for a in args if a not in ("clips", "pieces")), "")
    os.makedirs(MODELS, exist_ok=True)
    os.makedirs(TEXTURES, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    pic, masks = paint.paint_all()
    save_png(os.path.join(TEXTURES, "nutcracker_paint.png"), pic)
    save_png(os.path.join(TEXTURES, "nutcracker_masks.png"), masks)
    if out:
        os.makedirs(out, exist_ok=True)
        save_png(os.path.join(out, "paint_preview.png"), paint.preview(pic, masks))
    mat = show_material()
    problems = []
    report = []
    names = [(kind, lambda lo, kind=kind: build_kind(kind, lo)) for kind in paint.KINDS]
    names += [("walnut_" + which, lambda lo, which=which: build_walnut(which, lo)) for which in ("whole", "half_a", "half_b")]
    for n, (name, build) in enumerate(names):
        counts = []
        for lo in (False, True):
            fig = build(lo)
            check_skins(fig)
            parent = bpy.data.objects.new(fig.name, None)
            parent.empty_display_size = 0.02
            bpy.context.scene.collection.objects.link(parent)
            parent.location = (n * 0.25, 0.5 if lo else 0.0, 0.0)
            make_object(fig, parent, mat)
            counts.append(fig.triangles())
            if "pieces" in args:
                tally = {}
                for piece in fig.pieces:
                    key = piece[0].rstrip("0123456789").rstrip("_")
                    tally[key] = tally.get(key, 0) + len(piece_tris(fig, piece))
                print("  PIECES %s: %s" % (fig.name, ", ".join("%s %d" % kv for kv in sorted(tally.items(), key=lambda kv: -kv[1]))))
            if name in paint.KINDS:
                bad, notes = check_poses(fig, name)
                problems += ["%s: %s" % (fig.name, b) for b in bad]
                print("  %-12s %4d triangles, %2d pieces; %s" % (fig.name, fig.triangles(), len(fig.pieces), "; ".join(notes)))
        report.append("%s %d / %d" % (name, counts[0], counts[1]))
    for line in problems:
        print("CLIP", line)
    if problems and "clips" not in args:
        raise SystemExit("%d poses clip (see the CLIP lines)" % len(problems))
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "nutcrackers.blend"), relative_remap=True)
    bpy.ops.export_scene.gltf(filepath=os.path.join(MODELS, "nutcrackers.glb"), export_format='GLB', export_yup=True,
                              export_apply=False, export_image_format='NONE', export_animations=False,
                              export_vertex_color='NONE')
    print("BUILT nutcrackers (triangles full / low): " + ", ".join(report))


if __name__ == "__main__":
    main()
