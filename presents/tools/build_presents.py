# Builds the presents component's models and its one picture.
#
#   blender -b --factory-startup --python presents/tools/build_presents.py [-- <folder for a preview of the papers>]
#
# Writes, beside this folder:
#   tools/presents.blend              every present, bow and the tag, full and low, to open and edit
#   models/presents.glb               the same for Godot (no pictures inside: the script lays the material on)
#   textures/presents_papers.png      sixteen squares of masks (see paint_presents.py)
#
# Each present is an empty named after it (cube, shirt_box, tall_box, long_box, drum, bag, hat_box, parcel;
# the low ones end in _lo) with these under it:
#   <name>_body                 the wrapped thing: paper, tape, and whatever else it has (tissue, rope...)
#   <name>_lid                  the hat box's lid, a piece of its own
#   <name>_ribbon_cross / _ribbon_band / _ribbon_diag     one mesh for each way of tying it
#   <name>_bow_top / _bow_corner / _bow_side / _tag / _hinge   empties: where a bow or the tag goes (their
#                               local Z is out of the surface, the tag hangs along their local -Y, and their
#                               scale is how big a bow suits), and the line the hat box's lid opens about
# The bows (bow_classic, bow_pompom, bow_rosette, bow_string) and the tag sit at their own origin, Z up, front -Y.
# Faces are told apart by material name: paper, inside, ribbon, twine, rope, tissue, tag, seal, tape. The game
# gives each its square of the picture and its colours.
#
# Sizes are metres, Z up, the foot at the origin. Paper UVs are metres of paper / TILE, laid as the paper
# is really folded, so a pattern runs straight and at one scale over every face and changes direction only
# at a fold. Ribbon UVs: u across the ribbon, v along it (metres / RIB_TILE).
#
# Every piece of every mesh is checked: faces that share an edge must be wound alike, no edge may have more
# than two faces, and every closed piece must face outwards (its signed volume). The build stops otherwise.
import bpy
import math
import os
import random
import sys

import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MODELS = os.path.join(ROOT, "models")
TEXTURES = os.path.join(ROOT, "textures")
sys.path.insert(0, HERE)
import paint_presents as paint  # noqa: E402

TAU = math.pi * 2.0
TILE = 0.08         # metres of paper to one repeat of its pattern
RIB_TILE = 0.05     # metres of ribbon to one repeat along it
TWINE_TILE = 0.024  # metres of string to one repeat along it
EDGE = 0.0005       # how far a ribbon's edge stands off the paper
DOME = 0.0012       # how much higher its middle is
RELIEF = 0.0022     # how far the folded flaps at a box's ends stand out in their middle
X = Vector((1.0, 0.0, 0.0))
Y = Vector((0.0, 1.0, 0.0))
Z = Vector((0.0, 0.0, 1.0))


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def lerp(a, b, t):
    return a + (b - a) * t


def smooth(t):
    t = clamp(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


TURNED = [False]    # the paper turned a quarter, for a box wrapped standing up (so its pattern still stands up)


def uvp(along, round_it):
    """Paper UVs from metres of paper."""
    if TURNED[0]:
        return (round_it / TILE, along / TILE)
    return (along / TILE, round_it / TILE)


def region_uv(name, u, v):
    """A point of a patch of the parts square, kept a little inside its edges."""
    u0, v0, u1, v1 = paint.REGION[name]
    pad = 0.012
    return (lerp(u0 + pad, u1 - pad, clamp(u, 0.0, 1.0)), lerp(v0 + pad, v1 - pad, clamp(v, 0.0, 1.0)))


# ------------------------------------------------------------------ pieces of mesh
class Part:
    """Points, and faces as [indices, uvs, material name]."""

    def __init__(self):
        self.v = []
        self.faces = []

    def add(self, p):
        self.v.append(Vector((float(p[0]), float(p[1]), float(p[2]))))
        return len(self.v) - 1

    def _same(self, a, b):
        return a == b or (self.v[a] - self.v[b]).length < 1e-7

    def face(self, idx, uvs, mat):
        """A face; corners that fall on the one before are dropped, and so is a face left with two."""
        keep = []
        for i, uv in zip(idx, uvs):
            if keep and self._same(keep[-1][0], i):
                continue
            keep.append((i, uv))
        while len(keep) > 2 and self._same(keep[0][0], keep[-1][0]):
            keep.pop()
        if len(keep) < 3:
            return
        self.faces.append([[k[0] for k in keep], [k[1] for k in keep], mat])

    def warp(self, fn):
        self.v = [Vector(fn(p)) for p in self.v]

    def triangles(self):
        return sum(len(f[0]) - 2 for f in self.faces)


def settle(part, name):
    """Winds every piece alike and every closed piece outwards. Points at one place count as one point.
    Returns (closed pieces, open sheets, faces turned over)."""
    place = {}
    weld = []
    for p in part.v:
        key = (round(p.x * 2e4), round(p.y * 2e4), round(p.z * 2e4))
        weld.append(place.setdefault(key, len(place)))
    edges = {}
    rims = []
    for fi, (idx, _uv, _mat) in enumerate(part.faces):
        w = [weld[i] for i in idx]
        mine = []
        for a, b in zip(w, w[1:] + w[:1]):
            if a == b:
                raise SystemExit("BAD FACE: %s has a face with a corner used twice" % name)
            key = (min(a, b), max(a, b))
            edges.setdefault(key, []).append((fi, a < b))
            mine.append(key)
        rims.append(mine)
    for key, users in edges.items():
        if len(users) > 2:
            p = [q for q, k in zip(part.v, weld) if k == key[0]][0]
            raise SystemExit("NOT A SKIN: %s has an edge with %d faces, near (%.4f, %.4f, %.4f)"
                             % (name, len(users), p.x, p.y, p.z))
    flip = {}
    closed = opened = turned = 0
    for start in range(len(part.faces)):
        if start in flip:
            continue
        flip[start] = False
        piece = [start]
        stack = [start]
        shut = True
        while stack:
            f = stack.pop()
            for key in rims[f]:
                users = edges[key]
                if len(users) < 2:
                    shut = False
                    continue
                mine = [d for (g, d) in users if g == f][0]
                for (g, d) in users:
                    if g == f:
                        continue
                    want = d == (mine != flip[f])       # g must cross this edge the other way to f
                    if g in flip:
                        if flip[g] != want:
                            raise SystemExit("TWISTED: %s has a piece that cannot be wound one way" % name)
                    else:
                        flip[g] = want
                        piece.append(g)
                        stack.append(g)
        if shut:
            volume = 0.0
            for f in piece:
                vs = [part.v[i] for i in part.faces[f][0]]
                sign = -1.0 if flip[f] else 1.0
                for i in range(1, len(vs) - 1):
                    volume += sign * vs[0].dot(vs[i].cross(vs[i + 1])) / 6.0
            if abs(volume) < 1e-12:
                raise SystemExit("FLAT: %s has a closed piece with no volume" % name)
            if volume < 0.0:
                for f in piece:
                    flip[f] = not flip[f]
            closed += 1
        else:
            opened += 1
        for f in piece:
            if flip[f]:
                part.faces[f][0].reverse()
                part.faces[f][1].reverse()
                turned += 1
    return closed, opened, turned


def outward_check(part, name):
    """After everything (the settling, the bending): every closed piece must still have its faces outward."""
    place = {}
    weld = []
    for p in part.v:
        key = (round(p.x * 2e4), round(p.y * 2e4), round(p.z * 2e4))
        weld.append(place.setdefault(key, len(place)))
    edges = {}
    for fi, (idx, _uv, _mat) in enumerate(part.faces):
        w = [weld[i] for i in idx]
        for a, b in zip(w, w[1:] + w[:1]):
            edges.setdefault((min(a, b), max(a, b)), []).append((fi, a < b))
    seen = set()
    for start in range(len(part.faces)):
        if start in seen:
            continue
        seen.add(start)
        piece, stack, shut = [start], [start], True
        while stack:
            f = stack.pop()
            w = [weld[i] for i in part.faces[f][0]]
            for a, b in zip(w, w[1:] + w[:1]):
                users = edges[(min(a, b), max(a, b))]
                if len(users) != 2:
                    shut = False
                    continue
                if users[0][1] == users[1][1]:
                    raise SystemExit("INSIDE OUT: %s has two faces wound against each other" % name)
                for (g, _d) in users:
                    if g not in seen:
                        seen.add(g)
                        piece.append(g)
                        stack.append(g)
        if shut:
            volume = 0.0
            for f in piece:
                vs = [part.v[i] for i in part.faces[f][0]]
                for i in range(1, len(vs) - 1):
                    volume += vs[0].dot(vs[i].cross(vs[i + 1])) / 6.0
            if volume <= 0.0:
                raise SystemExit("INSIDE OUT: %s has a closed piece facing inwards (volume %.3g)" % (name, volume))


def fan(part, ids, uvs, mat):
    """A flat many-sided face as triangles from its last corner."""
    last = len(ids) - 1
    for i in range(last - 1):
        part.face([ids[last], ids[i], ids[i + 1]], [uvs[last], uvs[i], uvs[i + 1]], mat)


def strip(part, rows, mat, tile, closed=False):
    """A sheet through rows of points (each row a list of places, all the same length): u across, v along."""
    ids = [[part.add(p) for p in row] for row in rows]
    count = len(rows[0])
    mids = [sum(row, Vector((0.0, 0.0, 0.0))) / count for row in rows]
    vs = [0.0]
    for k in range(1, len(rows)):
        vs.append(vs[-1] + (mids[k] - mids[k - 1]).length / tile)
    total = vs[-1] + ((mids[0] - mids[-1]).length / tile if closed else 0.0)
    for k in range(len(rows) if closed else len(rows) - 1):
        k1 = (k + 1) % len(rows)
        va, vb = vs[k], (vs[k1] if k1 else total)
        for j in range(count - 1):
            ua, ub = j / (count - 1.0), (j + 1) / (count - 1.0)
            part.face([ids[k][j], ids[k][j + 1], ids[k1][j + 1], ids[k1][j]], [(ua, va), (ub, va), (ub, vb), (ua, vb)], mat)
    return ids


def ribbon(part, rows, lo, mat="ribbon", closed=True):
    """A ribbon lying on something: rows of (middle, half its width as a vector, out of the surface, lift)."""
    made = []
    for (c, across, n, lift) in rows:
        c, across, n = Vector(c), Vector(across), Vector(n)
        if lo:
            made.append([c - across + n * (lift + EDGE + DOME * 0.6), c + across + n * (lift + EDGE + DOME * 0.6)])
        else:
            made.append([c - across + n * (lift + EDGE), c + n * (lift + EDGE + DOME), c + across + n * (lift + EDGE)])
    strip(part, made, mat, RIB_TILE, closed)


def tube(part, pts, rad, sides, mat, tile, closed=False, outs=None, caps=True):
    """A round string through points. outs: for each point, a direction to stand its first side on."""
    pts = [Vector(p) for p in pts]
    count = len(pts)
    rows = []
    for k, p in enumerate(pts):
        before = pts[(k - 1) % count] if (closed or k > 0) else p
        after = pts[(k + 1) % count] if (closed or k < count - 1) else p
        t = (after - before).normalized()
        hint = Vector(outs[k]) if outs else (Z if abs(t.z) < 0.9 else X)
        a = (hint - t * hint.dot(t)).normalized()
        b = t.cross(a)
        row = [p + (a * math.cos(TAU * s / sides) + b * math.sin(TAU * s / sides)) * rad for s in range(sides)]
        rows.append(row + [row[0]])
    ids = [[part.add(q) for q in row[:-1]] for row in rows]
    vs = [0.0]
    for k in range(1, count):
        vs.append(vs[-1] + (pts[k] - pts[k - 1]).length / tile)
    total = vs[-1] + ((pts[0] - pts[-1]).length / tile if closed else 0.0)
    for k in range(count if closed else count - 1):
        k1 = (k + 1) % count
        va, vb = vs[k], (vs[k1] if k1 else total)
        for s in range(sides):
            s1 = (s + 1) % sides
            ua, ub = s / float(sides), (s + 1) / float(sides)
            part.face([ids[k][s], ids[k][s1], ids[k1][s1], ids[k1][s]], [(ua, va), (ub, va), (ub, vb), (ua, vb)], mat)
    if caps and not closed:
        for (k, at) in ((0, pts[0]), (count - 1, pts[-1])):
            mid = part.add(at)
            for s in range(sides):
                s1 = (s + 1) % sides
                part.face([mid, ids[k][s], ids[k][s1]], [(0.5, vs[k]), (0.0, vs[k]), (1.0, vs[k])], mat)


def flat_string(part, pts, wide, mat, tile, closed=False, outs=None):
    """The low string: a flat band standing off the surface."""
    pts = [Vector(p) for p in pts]
    count = len(pts)
    rows = []
    for k, p in enumerate(pts):
        before = pts[(k - 1) % count] if (closed or k > 0) else p
        after = pts[(k + 1) % count] if (closed or k < count - 1) else p
        t = (after - before).normalized()
        out = Vector(outs[k]) if outs else (Z if abs(t.z) < 0.9 else X)
        side = t.cross(out).normalized() * wide
        rows.append([p - side, p + side])
    strip(part, rows, mat, tile, closed)


def ball(part, centre, radii, segs, rings, mat, tile=RIB_TILE):
    """A squashed ball (a knot): rings between two poles."""
    centre = Vector(centre)
    rows = []
    for i in range(1, rings):
        lat = math.pi * i / rings - math.pi / 2
        rows.append([part.add(centre + Vector((radii[0] * math.cos(lat) * math.cos(TAU * s / segs),
                                               radii[1] * math.cos(lat) * math.sin(TAU * s / segs),
                                               radii[2] * math.sin(lat)))) for s in range(segs)])
    low = part.add(centre - Vector((0, 0, radii[2])))
    high = part.add(centre + Vector((0, 0, radii[2])))
    step = max(radii) * 2.0 / tile / rings
    for s in range(segs):
        s1 = (s + 1) % segs
        ua, ub = s / float(segs), (s + 1) / float(segs)
        part.face([low, rows[0][s1], rows[0][s]], [((ua + ub) / 2, 0.0), (ub, step), (ua, step)], mat)
        for i in range(len(rows) - 1):
            part.face([rows[i][s], rows[i][s1], rows[i + 1][s1], rows[i + 1][s]],
                      [(ua, step * (i + 1)), (ub, step * (i + 1)), (ub, step * (i + 2)), (ua, step * (i + 2))], mat)
        part.face([rows[-1][s], rows[-1][s1], high], [(ua, step * (rings - 1)), (ub, step * (rings - 1)), ((ua + ub) / 2, step * rings)], mat)


def tape(part, centre, along, across, long, wide):
    """A strip of sticky tape, lying where it is put."""
    centre, along, across = Vector(centre), Vector(along).normalized() * long / 2, Vector(across).normalized() * wide / 2
    ids = [part.add(centre - along - across), part.add(centre + along - across), part.add(centre + along + across),
           part.add(centre - along + across)]
    part.face(ids, [region_uv("tape", 0, 0), region_uv("tape", 1, 0), region_uv("tape", 1, 1), region_uv("tape", 0, 1)], "tape")


class Anchor:
    def __init__(self, name, at, out=Z, down=-Y, scale=1.0):
        """Where a bow or the tag goes: `out` is out of the surface, `down` the way the tag hangs or the
        bow's front."""
        self.name = name
        self.at = Vector(at)
        self.out = Vector(out).normalized()
        down = Vector(down)
        self.down = (down - self.out * down.dot(self.out)).normalized()
        self.scale = scale


# ------------------------------------------------------------------ a wrapped box
def wrapped_box(L, A, B, lo):
    """Paper round a box L long (along x), A wide, B high: wrapped round its length, the join underneath,
    the ends folded in as four flaps and taped. Its foot is at z = 0."""
    part = Part()
    r = 0.0 if lo else clamp(0.035 * min(L, A, B), 0.003, 0.007)
    relief = 0.0 if lo else RELIEF
    hy = A / 2.0
    ys = -0.24 * A          # where the paper's join runs, underneath
    round_all = 2.0 * (A + B)

    def girth(y, z, face):
        """How far round the paper a place is, from the join."""
        if face == "b":
            return y - ys
        if face == "r":
            return hy - ys + z
        if face == "t":
            return hy - ys + B + (hy - y)
        if face == "l":
            return hy - ys + B + A + (B - z)
        return hy - ys + 2.0 * B + A + (y + hy)

    if lo:
        sec = [(ys, 0.0, "b"), (hy, 0.0, "b"), (hy, B, "r"), (-hy, B, "t"), (-hy, 0.0, "l")]
        xs = [-L / 2, L / 2]
    else:
        sec = [(ys, 0.0, "b"), (hy - r, 0.0, "b"), (hy, r, "r"), (hy, B / 2, "r"), (hy, B - r, "r"), (hy - r, B, "t"),
               (0.0, B, "t"), (-hy + r, B, "t"), (-hy, B - r, "l"), (-hy, B / 2, "l"), (-hy, r, "l"), (-hy + r, 0.0, "c")]
        xs = [-L / 2 + r, 0.0, L / 2 - r]
    count = len(sec)
    g = [girth(y, z, f) for (y, z, f) in sec]
    rings = [[part.add((x, y, z)) for (y, z, _f) in sec] for x in xs]
    for j in range(len(xs) - 1):
        for i in range(count):
            i1 = (i + 1) % count
            ga, gb = g[i], (g[i1] if i1 else round_all)
            part.face([rings[j][i], rings[j + 1][i], rings[j + 1][i1], rings[j][i1]],
                      [uvp(xs[j], ga), uvp(xs[j + 1], ga), uvp(xs[j + 1], gb), uvp(xs[j], gb)], "paper")
    yl, yr, zb, zt = -hy + r, hy - r, r, B - r
    a, b, cz = A - 2 * r, B - 2 * r, B / 2.0
    for sx in (-1.0, 1.0):
        xe = sx * L / 2
        ring = rings[-1] if sx > 0 else rings[0]
        xr = xs[-1] if sx > 0 else xs[0]
        if lo:
            ids = list(ring)
            ends = [(y, z) for (y, z, _f) in sec]
        else:
            made = {}
            ids, ends = [], []
            for (y, z, _f) in sec:
                q = (clamp(y, yl, yr), clamp(z, zb, zt))
                key = (round(q[0], 7), round(q[1], 7))
                if key not in made:
                    made[key] = part.add((xe, q[0], q[1]))
                ids.append(made[key])
                ends.append(q)
            for i in range(count):
                i1 = (i + 1) % count
                ga, gb = g[i], (g[i1] if i1 else round_all)
                part.face([ring[i], ids[i], ids[i1], ring[i1]],
                          [uvp(xr, ga), uvp(sx * (L / 2 + r), ga), uvp(sx * (L / 2 + r), gb), uvp(xr, gb)], "paper")
        rim = {}
        for i, q in zip(ids, ends):
            rim[i] = q
        rim = list(rim.items())

        def on(test, order):
            return [i for (i, q) in sorted([(i, q) for (i, q) in rim if test(q)], key=lambda e: order(e[1]))]

        outer = {"b": on(lambda q: abs(q[1] - zb) < 1e-7, lambda q: q[0]),
                 "r": on(lambda q: abs(q[0] - yr) < 1e-7, lambda q: q[1]),
                 "t": on(lambda q: abs(q[1] - zt) < 1e-7, lambda q: -q[0]),
                 "l": on(lambda q: abs(q[0] - yl) < 1e-7, lambda q: -q[1])}
        # the flaps unfold onto the paper they came from, so each wears the pattern its side wears
        unfold = {"b": lambda y, z: uvp(sx * (L / 2 + z), y - ys),
                  "r": lambda y, z: uvp(sx * (L / 2 + (hy - y)), hy - ys + z),
                  "t": lambda y, z: uvp(sx * (L / 2 + (B - z)), hy - ys + B + (hy - y)),
                  "l": lambda y, z: uvp(sx * (L / 2 + (y + hy)), hy - ys + B + A + (B - z))}
        if a >= b:
            p1, p2 = (yl + b / 2, cz), (yr - b / 2, cz)
            inner = {"b": [p2, p1], "r": [p2], "t": [p1, p2], "l": [p1]}
        else:
            p1, p2 = (0.0, zb + a / 2), (0.0, zt - a / 2)
            inner = {"b": [p1], "r": [p2, p1], "t": [p2], "l": [p1, p2]}
        where = dict(rim)
        for side in ("b", "r", "t", "l"):
            ids2 = list(outer[side])
            places = [where[i] for i in ids2]
            for q in inner[side]:
                ids2.append(part.add((xe + sx * relief, q[0], q[1])))
                places.append(q)
            fan(part, ids2, [unfold[side](y, z) for (y, z) in places], "paper")
        if not lo:
            if a >= b:
                at = (xe + sx * (relief + 0.0007), clamp(0.3 * (a - b), 0.0, a / 2 - 0.02), cz)
                tape(part, at, Z, Y, min(0.045, 0.7 * b), min(0.018, 0.3 * a))
            else:
                at = (xe + sx * (relief + 0.0007), 0.0, cz + clamp(0.3 * (b - a), 0.0, b / 2 - 0.02))
                tape(part, at, Y, Z, min(0.045, 0.7 * a), min(0.018, 0.3 * b))
    if not lo:
        for x in (-0.27 * L, 0.24 * L):     # two bits of tape over the join underneath
            tape(part, (x, ys, -0.0006), Y, X, min(0.04, 0.5 * A), 0.018)
    return part, r


def rect_path(half, H, r, lo, extra=None, bump=None, middle=None):
    """Round a box's outline in a plane (p across, q up): (p, q, out p, out q, lift). `extra` lifts the
    ribbon further on a face (bottom, pos, top, neg); `bump` lifts it over another ribbon in the middle
    of a face: face -> (half the span, how high)."""
    extra = extra or {}
    middle = middle or {}       # a lift for the middle of a face only (over the folded flaps of a box's end)
    outs = {"bottom": (0.0, -1.0), "pos": (1.0, 0.0), "top": (0.0, 1.0), "neg": (-1.0, 0.0)}
    pts = []

    def put(p, q, face, more=0.0):
        pts.append((p, q, outs[face][0], outs[face][1], extra.get(face, 0.0) + more))

    def mid(face, p, q, along):
        if bump and face in bump and not lo:
            span, high = bump[face]
            put(p - along[0] * span, q - along[1] * span, face, middle.get(face, 0.0))
            put(p, q, face, high + middle.get(face, 0.0))
            put(p + along[0] * span, q + along[1] * span, face, middle.get(face, 0.0))
        elif not lo:
            put(p, q, face, middle.get(face, 0.0))

    mid("bottom", 0.0, 0.0, (1.0, 0.0))
    put(half - r, 0.0, "bottom")
    put(half, r, "pos")
    mid("pos", half, H / 2, (0.0, 1.0))
    put(half, H - r, "pos")
    put(half - r, H, "top")
    mid("top", 0.0, H, (-1.0, 0.0))
    put(-half + r, H, "top")
    put(-half, H - r, "neg")
    mid("neg", -half, H / 2, (0.0, -1.0))
    put(-half, r, "neg")
    put(-half + r, 0.0, "bottom")
    return pts


def plane_loop(part, pts, axis, hw, lo, mat="ribbon"):
    """A ribbon round an outline: in the plane x = 0 (axis "x": p is y) or y = 0 (axis "y": p is x)."""
    rows = []
    for (p, q, op, oq, lift) in pts:
        if axis == "x":
            rows.append(((0.0, p, q), (hw, 0.0, 0.0), (0.0, op, oq), lift))
        else:
            rows.append(((p, 0.0, q), (0.0, hw, 0.0), (op, 0.0, oq), lift))
    ribbon(part, rows, lo, mat)


def box_ribbons(W, D, H, r, lo, ends):
    """The three ways of tying a box W by D by H. ends: "x" if its folded ends face along x, "z" if up
    and down. Returns the parts and half the ribbon's width."""
    hw = clamp(0.085 * min(W, D), 0.006, 0.014)
    more = RELIEF + 0.0008
    over = {"top": (hw + 0.005, 0.0022), "bottom": (hw + 0.005, 0.0022)}
    lift_x = {"top": more, "bottom": more} if ends == "z" else {}
    lift_y = {"top": more, "bottom": more} if ends == "z" else {"pos": more, "neg": more}
    upper = {face: 0.0012 for face in ("bottom", "pos", "top", "neg")} if lo else {}
    cross = Part()
    plane_loop(cross, rect_path(D / 2, H, r, lo, None, None, lift_x), "x", hw, lo)
    plane_loop(cross, rect_path(W / 2, H, r, lo, upper, over, lift_y), "y", hw, lo)
    band = Part()
    plane_loop(band, rect_path(D / 2, H, r, lo, None, None, lift_x), "x", hw, lo)
    # across two opposite corners of the top, and slanting down the sides from there
    diag = Part()
    hx, hy = W / 2, D / 2
    s = hw * math.sqrt(2.0)
    c = clamp(0.42 * min(W, D), s + r + 0.004, 0.09)
    top_more = more * 0.4 if ends == "z" and not lo else 0.0
    x_more = more * 0.4 if ends == "x" and not lo else 0.0
    xa, ya = hx - c, hy - c
    xb = max(xa - (H - 2 * r), -hx + r + s + 0.004)
    yb = max(ya - (H - 2 * r), -hy + r + s + 0.004)
    for turn in (1.0, -1.0):
        rows = [(Vector((xb, hy, r)), X * s, Y, 0.0)]
        if not lo:
            rows.append((Vector(((xa + xb) / 2, hy, H / 2)), X * s, Y, 0.0))
        rows += [(Vector((xa, hy, H - r)), X * s, Y, 0.0),
                 (Vector((xa, hy - r, H)), X * s, Z, top_more)]
        if not lo:
            rows.append((Vector(((xa + hx) / 2, (hy + ya) / 2, H)), Vector((s / 2, s / 2, 0.0)), Z, top_more))
        rows += [(Vector((hx - r, ya, H)), Y * s, Z, top_more),
                 (Vector((hx, ya, H - r)), Y * s, X, x_more)]
        if not lo:
            rows.append((Vector((hx, (ya + yb) / 2, H / 2)), Y * s, X, x_more))
        rows.append((Vector((hx, yb, r)), Y * s, X, x_more))
        rows = [(Vector((c0.x * turn, c0.y * turn, c0.z)), Vector((a0.x * turn, a0.y * turn, a0.z)),
                 Vector((n0.x * turn, n0.y * turn, n0.z)), lift) for (c0, a0, n0, lift) in rows]
        ribbon(diag, rows, lo, closed=False)
    corner_at = Vector(((xa + hx) / 2, (hy + ya) / 2, H + top_more + EDGE + DOME))
    return {"ribbon_cross": cross, "ribbon_band": band, "ribbon_diag": diag}, hw, corner_at


def box_warp(W, D, H, rng, amount=1.0, lo=False):
    """A hand-wrapped box is not true: the top sinks a little, the sides belly, it leans, one corner is
    knocked in. Nothing moves at the foot. The low model only leans: its few flat faces must stay flat,
    or they would crease and come through its ribbon."""
    ph = [rng.uniform(0.0, TAU) for _ in range(6)]
    small = min(W, D)
    dip = rng.uniform(0.02, 0.034) * small * amount
    lean = (rng.uniform(-1, 1) * 0.014 * amount, rng.uniform(-1, 1) * 0.014 * amount)
    if lo:
        return lambda p: (p[0] + lean[0] * p[2], p[1] + lean[1] * p[2], p[2])
    corner = (rng.choice((-1.0, 1.0)), rng.choice((-1.0, 1.0)))
    crush = rng.uniform(0.03, 0.05) * min(W, D, H * 1.5) * amount
    wander = 0.011 * min(small, H * 2.0) * amount

    def fn(p):
        x, y, z = p
        u, v, t = x / (W / 2), y / (D / 2), clamp(z / H, 0.0, 1.1)
        hold = smooth(t * 3.0)
        z2 = z - dip * max(0.0, 1.0 - u * u) * max(0.0, 1.0 - v * v) * smooth((t - 0.5) * 2.0)
        swell = 4.0 * t * max(0.0, 1.0 - t)
        x2 = x + 0.008 * W * amount * u * max(0.0, 1.0 - v * v) * swell
        y2 = y + 0.008 * D * amount * v * max(0.0, 1.0 - u * u) * swell
        x2 += hold * (lean[0] * z + wander * math.sin(2.1 * v + 1.7 * t + ph[0]))
        y2 += hold * (lean[1] * z + wander * math.sin(2.3 * u + 1.3 * t + ph[1]))
        z2 += hold * wander * math.sin(1.9 * u + ph[2]) * math.sin(1.6 * v + ph[3])
        d2 = (u - corner[0]) ** 2 + (v - corner[1]) ** 2 + ((t - 1.0) * 2.0) ** 2
        k = hold * crush * math.exp(-d2 / 0.2)
        return (x2 - corner[0] * k * 0.6, y2 - corner[1] * k * 0.6, z2 - k * 0.8)

    return fn


def build_box(dims, lo, seed, upright=False, tag_on_top=False):
    """A wrapped box of dims (wide x, deep y, high z). upright: its folded ends are its top and bottom."""
    W, D, H = dims
    rng = random.Random(seed)
    if upright:
        TURNED[0] = True
        body, r = wrapped_box(H, W, D, lo)
        TURNED[0] = False
        body.warp(lambda p: (p.y, p.z - D / 2, p.x + H / 2))
    else:
        body, r = wrapped_box(W, D, H, lo)
        body.warp(lambda p: (-p.x, -p.y, p.z))      # turned about, so the pattern stands upright on its front
    parts, hw, corner_at = box_ribbons(W, D, H, r, lo, "z" if upright else "x")
    if H > 1.3 * min(W, D):
        del parts["ribbon_diag"]        # on a tall box the corner bands would slant the whole way across its sides
    parts["body"] = body
    top = H + (RELIEF if upright and not lo else 0.0)
    bow = clamp(min(W, D) / 0.16, 0.55, 1.15)
    anchors = [Anchor("bow_top", (0, 0, top + EDGE + DOME + 0.0025), Z, -Y, bow),
               Anchor("bow_corner", corner_at + Z * 0.0015, Z, Vector((-1, -1, 0)), bow * 0.85)]
    if H >= 0.1:
        anchors.append(Anchor("bow_side", (0, -D / 2 - EDGE - DOME - 0.002, H * 0.6), -Y, -Z, clamp(min(W, H) / 0.18, 0.5, 1.0)))
    else:
        anchors.append(Anchor("bow_side", (W * 0.24, -D * 0.2, top + 0.002), Z, -Y, bow * 0.8))
    if tag_on_top:
        anchors.append(Anchor("tag", (W * 0.05, -hw * 0.5, top + EDGE + DOME + 0.002), Z, Vector((0.9, -0.45, 0)), 0.95))
    else:
        anchors.append(Anchor("tag", (min(W * 0.2, hw + 0.03), -D / 2 - 0.0035, H - r - 0.004), -Y, -Z,
                              clamp(0.8 * H / 0.09, 0.5, 1.0)))
    return parts, anchors, box_warp(W, D, H, rng, 1.0, lo)


# ------------------------------------------------------------------ round things
def round_band(part, rad, z, hw, segs, lo, mat="ribbon"):
    """A ribbon round an upright drum of `segs` flat sides."""
    rows = []
    steps = segs if lo else segs * 2
    for k in range(steps):
        a = TAU * (k + 0.5) / segs if lo else TAU * k / steps
        on_corner = lo or k % 2 == 1
        reach = rad if on_corner else rad * math.cos(math.pi / segs)
        out = Vector((math.cos(a), math.sin(a), 0.0))
        rows.append((out * reach + Z * z, Z * hw, out, 0.0003))
    ribbon(part, rows, lo, mat)


def round_warp(R, H, rng, amount=1.0, lo=False):
    ph = [rng.uniform(0.0, TAU) for _ in range(4)]
    dip = rng.uniform(0.01, 0.02) * R * amount
    lean = (rng.uniform(-1, 1) * 0.012 * amount, rng.uniform(-1, 1) * 0.012 * amount)
    if lo:
        return lambda p: (p[0] + lean[0] * p[2], p[1] + lean[1] * p[2], p[2])

    def fn(p):
        x, y, z = p
        t = clamp(z / H, 0.0, 1.2)
        hold = smooth(t * 3.0)
        rr = math.hypot(x, y) / R
        ang = math.atan2(y, x)
        oval = 1.0 + hold * 0.012 * amount * math.sin(2.0 * ang + ph[0]) + hold * 0.006 * amount * math.sin(3.0 * ang + ph[1])
        z2 = z - dip * max(0.0, 1.0 - rr * rr) * smooth((t - 0.5) * 2.0) + hold * 0.006 * R * amount * math.sin(ang + ph[2]) * rr
        return (x * oval + hold * lean[0] * z, y * oval + hold * lean[1] * z, z2)

    return fn


def build_drum(lo, seed):
    """A round tin wrapped in paper: the paper pleated over its top to a sticker in the middle."""
    R, H = 0.09, 0.12
    segs = 8 if lo else 16
    r = 0.0 if lo else 0.005
    step = 0.0 if lo else 0.0028
    rng = random.Random(seed)
    body = Part()
    arc = TAU * R / segs
    angs = [TAU * (i + 0.5) / segs for i in range(segs)]

    def ring(rad, z):
        return [body.add((rad * math.cos(a), rad * math.sin(a), z)) for a in angs]

    w0, w1 = ring(R, r), ring(R, H - r)
    for i in range(segs):
        i1 = (i + 1) % segs
        body.face([w0[i], w0[i1], w1[i1], w1[i]], [uvp(i * arc, r), uvp((i + 1) * arc, r), uvp((i + 1) * arc, H - r), uvp(i * arc, H - r)], "paper")
    if lo:
        bot, top = w0, w1
        vb, vt = 0.0, H
    else:
        bot, top = ring(R - r, 0.0), ring(R - r, H)
        vb, vt = -0.4 * r, H + 0.4 * r
        for i in range(segs):
            i1 = (i + 1) % segs
            body.face([bot[i], bot[i1], w0[i1], w0[i]], [uvp(i * arc, vb), uvp((i + 1) * arc, vb), uvp((i + 1) * arc, r), uvp(i * arc, r)], "paper")
            body.face([w1[i], w1[i1], top[i1], top[i]], [uvp(i * arc, H - r), uvp((i + 1) * arc, H - r), uvp((i + 1) * arc, vt), uvp(i * arc, vt)], "paper")
    # underneath: the paper gathered flat to the middle. Each wedge wears the paper that came down its side
    low = body.add((0, 0, 0))
    for i in range(segs):
        i1 = (i + 1) % segs
        body.face([bot[i1], bot[i], low], [uvp((i + 1) * arc, vb), uvp(i * arc, vb), uvp((i + 0.5) * arc, vb - (R - r))], "paper")
    # on top: pleats, each lapping over the next like the blades of a fan
    for i in range(segs):
        i1 = (i + 1) % segs
        uva, uvb, uvm = uvp(i * arc, vt), uvp((i + 1) * arc, vt), uvp((i + 0.5) * arc, vt + (R - r))
        if lo:
            mid = body.add((0, 0, H))
            body.face([top[i], top[i1], mid], [uva, uvb, uvm], "paper")
            continue
        p1 = body.v[top[i1]]
        high = body.add((p1.x, p1.y, p1.z + step))
        mid = body.add((0, 0, H + step * 0.5))
        body.face([top[i], high, mid], [uva, uvb, uvm], "paper")
        body.face([top[i], top[i1], high], [uva, uvb, uvb], "paper")
        body.face([high, top[i1], body.add((0, 0, H + step * 0.5))], [uvb, uvb, uvm], "paper")
    seal_r = 0.021
    seal_z = H + step + 0.0012
    mid = body.add((0, 0, seal_z + 0.0006))
    sides = 6 if lo else 10
    rim = [body.add((seal_r * math.cos(TAU * k / sides), seal_r * math.sin(TAU * k / sides), seal_z)) for k in range(sides)]
    for k in range(sides):
        k1 = (k + 1) % sides
        body.face([mid, rim[k], rim[k1]], [region_uv("seal", 0.5, 0.5),
                                           region_uv("seal", 0.5 + 0.5 * math.cos(TAU * k / sides), 0.5 + 0.5 * math.sin(TAU * k / sides)),
                                           region_uv("seal", 0.5 + 0.5 * math.cos(TAU * k1 / sides), 0.5 + 0.5 * math.sin(TAU * k1 / sides))], "seal")
    if not lo:
        a0 = angs[0]
        tape(body, ((R + 0.0008) * math.cos(a0), (R + 0.0008) * math.sin(a0), H * 0.78), (-math.sin(a0), math.cos(a0), 0.0), Z, 0.036, 0.018)       # over the join in the paper, down its side
    hw = 0.011
    more = step + 0.0024
    over = {"top": (hw + 0.005, 0.0022), "bottom": (hw + 0.005, 0.0022)}
    lift = {"top": more}
    lift_over = dict(lift)
    if lo:
        lift_over = {face: lift.get(face, 0.0) + 0.0012 for face in ("bottom", "pos", "top", "neg")}
    cross = Part()
    plane_loop(cross, rect_path(R * math.cos(math.pi / segs), H, r, lo, lift), "x", hw, lo)
    plane_loop(cross, rect_path(R * math.cos(math.pi / segs), H, r, lo, lift_over, over), "y", hw, lo)
    band = Part()
    round_band(band, R, H * 0.5, hw, segs, lo)
    front = R * math.cos(math.pi / segs)
    anchors = [Anchor("bow_top", (0, 0, H + more + EDGE + DOME + 0.0025), Z, -Y, 0.95),
               Anchor("bow_corner", (0.03, -0.03, H + more + 0.002), Z, Vector((1, -1, 0)), 0.7),
               Anchor("bow_side", (0, -front - 0.004, H * 0.5), -Y, -Z, 0.62),
               Anchor("tag", (0.034, -front - 0.004, H - 0.012), -Y, -Z, 0.9)]
    return {"body": body, "ribbon_cross": cross, "ribbon_band": band}, anchors, round_warp(R, H, rng, 1.0, lo)


def build_hat_box(lo, seed):
    """A round hat box: the box, its lid a separate piece that lifts, tissue under the lid."""
    R, HB = 0.12, 0.115
    RL, Z0, Z1 = R + 0.007, 0.1, 0.14
    segs = 8 if lo else 16
    r = 0.0 if lo else 0.004
    rng = random.Random(seed)
    arc = TAU * R / segs
    angs = [TAU * (i + 0.5) / segs for i in range(segs)]
    body = Part()

    def ring(part, rad, z):
        return [part.add((rad * math.cos(a), rad * math.sin(a), z)) for a in angs]

    def flat_uv(part, i):
        return uvp(part.v[i].x, part.v[i].y)

    w0, w1 = ring(body, R, r), ring(body, R, HB)
    bot = w0 if lo else ring(body, R - r, 0.0)
    for i in range(segs):
        i1 = (i + 1) % segs
        body.face([w0[i], w0[i1], w1[i1], w1[i]], [uvp(i * arc, r), uvp((i + 1) * arc, r), uvp((i + 1) * arc, HB), uvp(i * arc, HB)], "paper")
        if not lo:
            body.face([bot[i], bot[i1], w0[i1], w0[i]], [uvp(i * arc, -0.4 * r), uvp((i + 1) * arc, -0.4 * r), uvp((i + 1) * arc, r), uvp(i * arc, r)], "paper")
    low = body.add((0, 0, 0))
    for i in range(segs):
        i1 = (i + 1) % segs
        body.face([bot[i1], bot[i], low], [flat_uv(body, bot[i1]), flat_uv(body, bot[i]), (0.0, 0.0)], "paper")
    if lo:
        heap = body.add((0, 0, HB - 0.004))
        for i in range(segs):
            i1 = (i + 1) % segs
            body.face([w1[i], w1[i1], heap], [flat_uv(body, w1[i]), flat_uv(body, w1[i1]), (0.0, 0.0)], "tissue")
    else:
        # the box's own edge, the inside of its wall, and tissue paper heaped in it
        lip, deep = ring(body, R - 0.004, HB), ring(body, R - 0.004, HB - 0.03)
        heap = body.add((0.01, -0.006, HB - 0.008))
        for i in range(segs):
            i1 = (i + 1) % segs
            body.face([w1[i], w1[i1], lip[i1], lip[i]], [uvp(i * arc, HB), uvp((i + 1) * arc, HB), uvp((i + 1) * arc, HB + 0.004), uvp(i * arc, HB + 0.004)], "inside")
            body.face([lip[i], lip[i1], deep[i1], deep[i]], [uvp(i * arc, 0.0), uvp((i + 1) * arc, 0.0), uvp((i + 1) * arc, 0.03), uvp(i * arc, 0.03)], "inside")
            body.face([deep[i], deep[i1], heap], [flat_uv(body, deep[i]), flat_uv(body, deep[i1]), (0.0, 0.0)], "tissue")
        for i in deep:      # crumple the tissue's edge
            body.v[i].z += rng.uniform(0.0, 0.012)
    lid = Part()
    l0, l1 = ring(lid, RL, Z0), ring(lid, RL, Z1 - r)
    top = l1 if lo else ring(lid, RL - r, Z1)
    crown = lid.add((0, 0, Z1 + 0.003))
    under = lid.add((0, 0, Z0))
    arc_l = TAU * RL / segs
    for i in range(segs):
        i1 = (i + 1) % segs
        lid.face([l0[i], l0[i1], l1[i1], l1[i]], [uvp(i * arc_l, Z0), uvp((i + 1) * arc_l, Z0), uvp((i + 1) * arc_l, Z1 - r), uvp(i * arc_l, Z1 - r)], "paper")
        if not lo:
            lid.face([l1[i], l1[i1], top[i1], top[i]], [uvp(i * arc_l, Z1 - r), uvp((i + 1) * arc_l, Z1 - r), uvp((i + 1) * arc_l, Z1 + 0.4 * r), uvp(i * arc_l, Z1 + 0.4 * r)], "paper")
        lid.face([top[i], top[i1], crown], [flat_uv(lid, top[i]), flat_uv(lid, top[i1]), (0.0, 0.0)], "paper")
        lid.face([l0[i1], l0[i], under], [flat_uv(lid, l0[i1]), flat_uv(lid, l0[i]), (0.0, 0.0)], "inside")
    hw = 0.013
    over = 0.0 if lo else 0.0
    flat = math.cos(math.pi / segs)

    def outline(scale, more):
        """Over the lid and down to the foot: the ribbon is pulled straight from the lid's edge to the floor."""
        rl, rb = RL * scale, R * scale
        pts = []
        if not lo:
            pts.append((0.0, 0.0, 0.0, -1.0, more))
        pts += [(rb - r, 0.0, 0.0, -1.0, more), (rb, r, 1.0, 0.0, more), (rl, Z0, 1.0, 0.0, more), (rl, Z1 - r, 1.0, 0.0, more),
                (rl - r, Z1, 0.0, 1.0, more)]
        pts.append((0.0, Z1 + 0.003, 0.0, 1.0, more + (0.0022 if more > 0.0 and not lo else 0.0)))
        pts += [(-rl + r, Z1, 0.0, 1.0, more), (-rl, Z1 - r, -1.0, 0.0, more), (-rl, Z0, -1.0, 0.0, more), (-rb, r, -1.0, 0.0, more),
                (-rb + r, 0.0, 0.0, -1.0, more)]
        return pts

    cross = Part()
    plane_loop(cross, outline(flat, 0.0), "x", hw, lo)
    plane_loop(cross, outline(flat, 0.0012 if lo else 0.0004), "y", hw, lo)
    band = Part()
    round_band(band, R, 0.05, hw, segs, lo)
    front = R * flat
    anchors = [Anchor("bow_top", (0, 0, Z1 + 0.003 + EDGE + DOME + 0.0035), Z, -Y, 1.1),
               Anchor("bow_corner", (0.045, -0.045, Z1 + 0.004), Z, Vector((1, -1, 0)), 0.8),
               Anchor("bow_side", (0, -front - 0.0045, 0.05), -Y, -Z, 0.7),
               Anchor("tag", (0.04, -front - 0.004, Z0 - 0.006), -Y, -Z, 0.95),
               Anchor("hinge", (0, R, HB), Z, -Y, 1.0)]
    return {"body": body, "lid": lid, "ribbon_cross": cross, "ribbon_band": band}, anchors, round_warp(RL, Z1, rng, 0.6, lo)


# ------------------------------------------------------------------ the bag
def build_bag(lo, seed):
    """A paper gift bag: creased sides, rope handles, tissue paper standing out of it."""
    W, D, H = 0.18, 0.09, 0.22
    hx, hy = W / 2, D / 2
    rng = random.Random(seed)
    body = Part()

    def outline(s):
        """The bag's outline at a height (s: 0 its foot .. 1 its mouth): it opens out a little, its sides
        creased inwards, its front and back bellied."""
        wide = 1.0 + 0.05 * s
        pinch = 0.024 * s * s
        belly = 0.004 * s + 0.005 * math.sin(math.pi * s)
        return [(-hx * wide + pinch, 0.0), (-hx * wide, -hy * wide), (0.0, -hy * wide - belly), (hx * wide, -hy * wide),
                (hx * wide - pinch, 0.0), (hx * wide, hy * wide), (0.0, hy * wide + belly), (-hx * wide, hy * wide)]

    levels = [0.0, 1.0] if lo else [0.0, 0.5, 1.0]
    base = outline(0.0)
    count = len(base)
    g = [0.0]
    for i in range(1, count + 1):
        a, b = base[i - 1], base[i % count]
        g.append(g[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    rings = [[body.add((x, y, s * H)) for (x, y) in outline(s)] for s in levels]
    for j in range(len(levels) - 1):
        za, zb = levels[j] * H, levels[j + 1] * H
        for i in range(count):
            i1 = (i + 1) % count
            body.face([rings[j][i], rings[j][i1], rings[j + 1][i1], rings[j + 1][i]],
                      [uvp(g[i], za), uvp(g[i + 1], za), uvp(g[i + 1], zb), uvp(g[i], zb)], "paper")
    foot = body.add((0, 0, 0))
    for i in range(count):
        i1 = (i + 1) % count
        body.face([rings[0][i1], rings[0][i], foot], [uvp(*base[i1]), uvp(*base[i]), (0.0, 0.0)], "paper")
    mouth = rings[-1]
    if lo:
        heap = body.add((0, 0, H - 0.02))
        for i in range(count):
            i1 = (i + 1) % count
            body.face([mouth[i], mouth[i1], heap], [uvp(body.v[mouth[i]].x, body.v[mouth[i]].y),
                                                    uvp(body.v[mouth[i1]].x, body.v[mouth[i1]].y), (0.0, 0.0)], "tissue")
    else:
        lip = [body.add((body.v[i].x * 0.975, body.v[i].y * 0.955, H)) for i in mouth]
        deep = [body.add((body.v[i].x * 0.975, body.v[i].y * 0.955, H - 0.035 + rng.uniform(0.0, 0.012))) for i in mouth]
        heap = body.add((0.0, 0.0, H - 0.022))
        for i in range(count):
            i1 = (i + 1) % count
            body.face([mouth[i], mouth[i1], lip[i1], lip[i]], [uvp(g[i], H), uvp(g[i + 1], H), uvp(g[i + 1], H + 0.003), uvp(g[i], H + 0.003)], "paper")
            body.face([lip[i], lip[i1], deep[i1], deep[i]], [uvp(g[i], 0.0), uvp(g[i + 1], 0.0), uvp(g[i + 1], 0.035), uvp(g[i], 0.035)], "inside")
            body.face([deep[i], deep[i1], heap], [uvp(body.v[deep[i]].x, body.v[deep[i]].y), uvp(body.v[deep[i1]].x, body.v[deep[i1]].y), (0.0, 0.0)], "tissue")
    # sheets of tissue paper standing out of the mouth, folded like a fan
    sheets = [(-0.028, -0.02, 0.105, 0.2, (0.03, 0.064, 0.035, 0.07, 0.028)),
              (0.03, 0.006, 0.11, -0.25, (0.05, 0.03, 0.082, 0.045, 0.06)),
              (-0.012, 0.026, 0.085, 0.12, (0.04, 0.066, 0.03, 0.055, 0.02))]
    if lo:
        sheets = sheets[:2]
    for (cx, cy, span, turn, tall) in sheets:
        root = body.add((cx, cy, H - 0.045))
        ca, sa = math.cos(turn), math.sin(turn)
        picks = (0, 2, 4) if lo else (0, 1, 2, 3, 4)
        tips = []
        for k in picks:
            along = (k - 2) * span / 4.0
            fold = 0.011 * (1 if k % 2 else -1)
            tips.append((body.add((cx + along * ca - fold * sa, cy + along * sa + fold * ca, H + tall[k])), along, tall[k]))
        for (a, b) in zip(tips, tips[1:]):
            body.face([root, a[0], b[0]], [uvp(0.0, -0.045), uvp(a[1], a[2]), uvp(b[1], b[2])], "tissue")
    # rope handles: the front one fallen forward, the back one standing
    def front(x, z):
        """How far forward the bag's front face is at a place on it (y, negative)."""
        s = clamp(z / H, 0.0, 1.0)
        k = 0 if lo else (0 if s < 0.5 else 1)
        f = (s - levels[k]) / (levels[k + 1] - levels[k])
        ys = []
        for level in (levels[k], levels[k + 1]):
            pts = outline(level)
            ys.append(lerp(pts[2][1], pts[3][1], clamp(abs(x) / pts[3][0], 0.0, 1.0)))
        return lerp(ys[0], ys[1], f)

    front_y = front(0.045, H - 0.026) - 0.0026
    for (y0, lean, rise) in ((front_y, -0.034, 0.07), (-front_y, 0.012, 0.094)):
        steps = 4 if lo else 8
        pts = []
        for k in range(steps + 1):
            t = k / float(steps)
            arch = math.sin(math.pi * t) ** 0.8
            pts.append((-0.045 + 0.09 * t, y0 + lean * arch, H - 0.026 + rise * arch))
        if lo:
            flat_string(body, pts, 0.003, "rope", TWINE_TILE, outs=[(0, -1 if y0 < 0 else 1, 0.3)] * len(pts))
        else:
            tube(body, pts, 0.0024, 4, "rope", TWINE_TILE)
    anchors = [Anchor("bow_top", (0, front(0.0, H - 0.085) - 0.003, H - 0.085), -Y, -Z, 0.6),
               Anchor("bow_corner", (-0.045, front(0.045, H - 0.034) - 0.003, H - 0.034), -Y, -Z, 0.4),
               Anchor("bow_side", (0, front(0.0, H - 0.085) - 0.003, H - 0.085), -Y, -Z, 0.6),
               Anchor("tag", (0.045, front(0.045, H - 0.03) - 0.0035, H - 0.03), -Y, -Z, 0.85)]
    ph = [rng.uniform(0.0, TAU) for _ in range(3)]

    def warp(p):
        x, y, z = p
        t = clamp(z / H, 0.0, 1.4)
        hold = smooth(t * 3.0)
        return (x + hold * (0.012 * z + 0.002 * math.sin(9.0 * y / D + ph[0])), y + hold * (0.02 * z + 0.002 * math.sin(7.0 * x / W + ph[1])), z)

    return {"body": body}, anchors, warp


# ------------------------------------------------------------------ the lumpy parcel
def build_parcel(lo, seed):
    """Something awkward wrapped anyway: a lump of paper, tied both ways with string that pulls it in."""
    half = Vector((0.11, 0.08, 0.065))
    n = 2 if lo else 4
    rng = random.Random(seed)
    ph = [rng.uniform(0.0, TAU) for _ in range(9)]
    body = Part()

    def place(q):
        q = Vector(q)
        s = q.normalized()
        p = q * 0.4 + s * 0.68
        bump = 1.0 + 0.07 * (math.sin(2.6 * q.x + 1.9 * q.y + ph[0]) + math.sin(2.2 * q.y - 2.4 * q.z + ph[1]) + math.sin(2.9 * q.z + 2.1 * q.x + ph[2])) / 1.8
        p = Vector((p.x * half.x, p.y * half.y, p.z * half.z)) * bump
        fat = 1.0 + 0.2 * q.x                              # bigger at one end
        tie_a = 1.0 - 0.1 * math.exp(-(q.x / 0.3) ** 2)    # the string round its middle pulls it in
        tie_b = 1.0 - 0.08 * math.exp(-(q.y / 0.32) ** 2)  # and the one along it
        p = Vector((p.x * tie_b, p.y * fat * tie_a, p.z * fat * tie_a * tie_b))
        z = p.z + half.z * 0.93
        if z < 0.012:
            z = 0.012 + (z - 0.012) * 0.12                 # it sits on its flattened underside
        return Vector((p.x, p.y, z))

    ids = {}

    def point(q):
        key = (round(q[0] * n), round(q[1] * n), round(q[2] * n))
        if key not in ids:
            ids[key] = body.add(place(q))
        return ids[key]

    for axis in range(3):
        for side in (-1.0, 1.0):
            for i in range(n):
                for j in range(n):
                    corners = []
                    for (di, dj) in ((0, 0), (1, 0), (1, 1), (0, 1)):
                        q = [0.0, 0.0, 0.0]
                        q[axis] = side
                        q[(axis + 1) % 3] = -1.0 + 2.0 * (i + di) / n
                        q[(axis + 2) % 3] = -1.0 + 2.0 * (j + dj) / n
                        corners.append(point(q))
                    uvs = []
                    for c in corners:
                        p = body.v[c]
                        uvs.append(uvp(p[(axis + 1) % 3], p[(axis + 2) % 3]) if axis != 1 else uvp(p.x, p.z))
                    body.face(corners, uvs, "paper")
    low_z = min(p.z for p in body.v)
    for p in body.v:
        p.z -= low_z
    middle = Vector((0.0, 0.0, half.z * 0.9))

    def loop(axis):
        """The points of the lump along the line where a coordinate of its box is 0, in order round it."""
        a, b = (axis + 1) % 3, (axis + 2) % 3
        walk = [(-1.0 + 2.0 * i / n, -1.0) for i in range(n)] + [(1.0, -1.0 + 2.0 * i / n) for i in range(n)]
        walk += [(1.0 - 2.0 * i / n, 1.0) for i in range(n)] + [(-1.0, 1.0 - 2.0 * i / n) for i in range(n)]
        out = []
        for (u, v) in walk:
            q = [0.0, 0.0, 0.0]
            q[a], q[b] = u, v
            out.append(body.v[point(q)].copy())
        return out

    rad = 0.0013
    parts = {"body": body}
    for (name, axes) in (("ribbon_cross", (0, 1)), ("ribbon_band", (0,))):
        string = Part()
        for axis in axes:
            pts = loop(axis)
            outs = [(p - middle).normalized() for p in pts]
            lift = rad * (0.55 if axis == 0 else 0.7)
            lifted = []
            for p, out in zip(pts, outs):
                over = abs(p.x) < 0.004 and abs(p.y) < 0.004 and axis == 1     # the second string crosses the first
                lifted.append(p + out * (lift + (rad * 1.7 if over else 0.0)))
            if lo:
                flat_string(string, lifted, 0.0022, "twine", TWINE_TILE, closed=True, outs=outs)
            else:
                tube(string, lifted, rad, 3, "twine", TWINE_TILE, closed=True, outs=outs)
        parts[name] = string
    top = body.v[point((0.0, 0.0, 1.0))].copy()
    if not lo:
        for q, axis, turn in (((0.5, 0.5, 1.0), 2, 0.5), ((-0.5, 0.0, 1.0), 2, -0.3), ((1.0, -0.5, 0.0), 0, 0.2), ((0.5, -1.0, 0.0), 1, 1.3)):
            p = body.v[point(q)]
            du, dv = [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]
            du[(axis + 1) % 3] = 0.25
            dv[(axis + 2) % 3] = 0.25
            du, dv = Vector(du), Vector(dv)
            a = (place(Vector(q) + du) - place(Vector(q) - du)).normalized()
            b = (place(Vector(q) + dv) - place(Vector(q) - dv)).normalized()
            out = a.cross(b).normalized()
            if out.dot(p - middle) < 0.0:
                out = -out
            along = (a * math.cos(turn) + out.cross(a) * math.sin(turn))
            tape(body, p + out * 0.0022, along, out.cross(along), 0.028, 0.014)
    slope = (place((0.5, -0.5, 1.0)) - Z * low_z - top).normalized()
    out = (Z * 0.9 + (top - middle).normalized() * 0.1).normalized()
    anchors = [Anchor("bow_top", top + Z * (rad * 3.2), Z, -Y, 0.8),
               Anchor("bow_corner", top + Z * (rad * 3.2), Z, -Y, 0.8),
               Anchor("bow_side", body.v[point((0.0, -1.0, 0.0))] - Y * 0.004, -Y, -Z, 0.55),
               Anchor("tag", top + Z * 0.0045, (out - slope * 0.25).normalized(), slope, 0.9)]
    return parts, anchors, None


# ------------------------------------------------------------------ bows and the tag
def bow_loop(part, sx, sweep, lo, long=0.056, up=0.027, down=0.012, knot=0.013, wide=0.025, roll=0.65):
    """One loop of a bow: a ribbon out from the knot and back, pinched at the knot, its tip sagging."""
    segs = 4 if lo else 8
    ca, sa = math.cos(sweep), math.sin(sweep)
    rows = []
    for k in range(segs + 1):
        th = TAU * k / segs
        open_ = math.sin(th / 2.0)
        x = long * (1.0 - math.cos(th)) / 2.0
        z = knot + (up if math.sin(th) > 0 else down) * math.sin(th) * open_ ** 0.6 - 0.1 * x
        hw = wide / 2.0 * (0.36 + 0.64 * open_)
        # out of the loop's own curve, to puff the ribbon's middle
        nx, nz = x - long / 2.0, z - knot
        size = math.hypot(nx, nz) or 1.0
        puff = 0.0018 * open_
        mid = Vector((x + nx / size * puff, 0.0, z + nz / size * puff))
        row = [Vector((x, -hw, z)), Vector((x, hw, z))] if lo else [Vector((x, -hw, z)), mid, Vector((x, hw, z))]
        turned = []
        for p in row:
            # rolled about its own length so its face shows from the front, then swung, then set down
            y2 = p.y * math.cos(roll) - (p.z - knot) * math.sin(roll)
            z2 = knot + p.y * math.sin(roll) + (p.z - knot) * math.cos(roll)
            turned.append(Vector((sx * (p.x * ca - y2 * sa), p.x * sa + y2 * ca, max(z2, 0.0012))))
        rows.append(turned)
    strip(part, rows, "ribbon", RIB_TILE)


def bow_tail(part, turn, lo, long=0.074, wide=0.021, wave=1.0):
    """A tail of the bow: out from under the knot across the top of the present, its end curling up, cut
    to a swallow tail."""
    segs = 2 if lo else 5
    ca, sa = math.cos(turn), math.sin(turn)
    rows = []
    for k in range(segs + 1):
        t = k / float(segs)
        d = 0.006 + long * t
        z = 0.007 * (1.0 - t) ** 2 + 0.0016 + 0.005 * wave * math.sin(math.pi * t) * t + 0.009 * max(0.0, t - 0.7) ** 2 / 0.09
        hw = wide / 2.0 * (0.5 + 0.5 * smooth(t * 3.0))
        side = 0.01 * wave * math.sin(t * 2.6)                  # it wanders a little sideways
        notch = 0.013 if k == segs else 0.0
        if lo:
            row = [(d, side - hw, z), (d, side + hw, z)]
        else:
            row = [(d, side - hw, z), (d - notch, side, z + 0.0006), (d, side + hw, z)]
        rows.append([Vector((p[0] * ca - p[1] * sa, p[0] * sa + p[1] * ca, p[2])) for p in row])
    strip(part, rows, "ribbon", RIB_TILE)


def build_bow_classic(lo):
    """Two loops, a pinched knot, two tails."""
    part = Part()
    bow_loop(part, 1.0, -0.2, lo)
    bow_loop(part, -1.0, -0.2, lo)
    bow_tail(part, math.radians(-58), lo, wave=1.0)
    bow_tail(part, math.radians(-124), lo, long=0.066, wave=-0.8)
    ball(part, (0, -0.002, 0.0125), (0.0082, 0.0095, 0.009), 4 if lo else 6, 2 if lo else 3, "ribbon")
    return {"body": part}, [], None


def build_bow_pompom(lo):
    """A pom-pom of ribbon loops, the kind that comes with a sticky back."""
    part = Part()
    rng = random.Random(5)
    tiers = [(6, 16.0, 0.046), (4, 46.0, 0.04), (1, 88.0, 0.03)] if lo else [(8, 16.0, 0.047), (6, 44.0, 0.042), (4, 68.0, 0.036), (1, 89.0, 0.028)]
    hw = 0.0085
    for t, (count, tilt, long) in enumerate(tiers):
        for k in range(count):
            az = TAU * (k + 0.5 * (t % 2)) / count + rng.uniform(-0.12, 0.12)
            el = math.radians(tilt + rng.uniform(-5.0, 5.0))
            ln = long * rng.uniform(0.92, 1.06)
            d = Vector((math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), math.sin(el)))
            u = Vector((-math.cos(az) * math.sin(el), -math.sin(az) * math.sin(el), math.cos(el)))
            w = Vector((-math.sin(az), math.cos(az), 0.0))
            shape = [(0.12, -0.035, 0.5), (1.0, 0.0, 1.0), (0.12, 0.035, 0.5)] if lo else \
                [(0.1, -0.03, 0.5), (0.5, -0.2, 0.95), (0.88, -0.17, 1.0), (1.0, 0.0, 1.0), (0.88, 0.17, 1.0), (0.5, 0.2, 0.95), (0.1, 0.03, 0.5)]
            rows = []
            for (s, v, wide) in shape:
                c = Vector((0.0, 0.0, 0.0065)) + d * (s * ln) + u * (v * ln)
                rows.append([c - w * (hw * wide), c + w * (hw * wide)])
            strip(part, rows, "ribbon", RIB_TILE)
    return {"body": part}, [], None


def build_bow_rosette(lo):
    """A flat stick-on rosette: rings of pointed ribbon petals round a button."""
    part = Part()
    layers = [(6, 0.046, 0.0016, 0.004, 0.0), (5, 0.032, 0.005, 0.01, 0.5)] if lo else \
        [(8, 0.048, 0.0016, 0.0035, 0.0), (8, 0.037, 0.0048, 0.009, 0.5), (6, 0.025, 0.0085, 0.015, 0.25)]
    for (count, long, z0, z1, shift) in layers:
        for k in range(count):
            az = TAU * (k + shift) / count
            d = Vector((math.cos(az), math.sin(az), 0.0))
            w = Vector((-math.sin(az), math.cos(az), 0.0))
            wide = long * math.tan(math.pi / count) * 0.62
            root = part.add(d * 0.004 + Z * z0)
            left = part.add(d * (long * 0.52) - w * wide + Z * lerp(z0, z1, 0.5))
            right = part.add(d * (long * 0.52) + w * wide + Z * lerp(z0, z1, 0.5))
            tip = part.add(d * long + Z * z1)
            va, vm, vb = 0.0, long * 0.52 / RIB_TILE, long / RIB_TILE
            if lo:
                part.face([root, left, tip], [(0.5, va), (0.0, vm), (0.5, vb)], "ribbon")
                part.face([root, tip, right], [(0.5, va), (0.5, vb), (1.0, vm)], "ribbon")
            else:
                ridge = part.add(d * (long * 0.5) + Z * (lerp(z0, z1, 0.5) + 0.0035))
                part.face([root, left, ridge], [(0.5, va), (0.0, vm), (0.5, vm)], "ribbon")
                part.face([left, tip, ridge], [(0.0, vm), (0.5, vb), (0.5, vm)], "ribbon")
                part.face([tip, right, ridge], [(0.5, vb), (1.0, vm), (0.5, vm)], "ribbon")
                part.face([right, root, ridge], [(1.0, vm), (0.5, va), (0.5, vm)], "ribbon")
    sides = 6 if lo else 8
    z = layers[-1][2] + 0.002
    mid = part.add((0, 0, z + 0.006))
    inner = [part.add((0.0055 * math.cos(TAU * k / sides), 0.0055 * math.sin(TAU * k / sides), z + 0.0045)) for k in range(sides)]
    outer = [part.add((0.0095 * math.cos(TAU * k / sides), 0.0095 * math.sin(TAU * k / sides), z)) for k in range(sides)]
    for k in range(sides):
        k1 = (k + 1) % sides
        if lo:
            part.face([mid, outer[k], outer[k1]], [(0.5, 0.0), (0.2, 0.2), (0.8, 0.2)], "ribbon")
        else:
            part.face([mid, inner[k], inner[k1]], [(0.5, 0.0), (0.3, 0.1), (0.7, 0.1)], "ribbon")
            part.face([inner[k], outer[k], outer[k1], inner[k1]], [(0.3, 0.1), (0.3, 0.3), (0.7, 0.3), (0.7, 0.1)], "ribbon")
    return {"body": part}, [], None


def build_bow_string(lo):
    """String tied in a bow: two loops lying nearly flat, two ends, a knot."""
    part = Part()
    rad = 0.0013
    for sx in (-1.0, 1.0):
        steps = 5 if lo else 9
        pts = []
        for k in range(steps + 1):
            th = TAU * k / steps
            open_ = math.sin(th / 2.0)
            x = 0.034 * (1.0 - math.cos(th)) / 2.0
            y = 0.013 * math.sin(th) * open_ ** 0.5
            pts.append((sx * x, y * (1.0 if sx > 0 else -1.0) - 0.004 * x / 0.034, 0.0034 + 0.0075 * open_ * (0.5 + 0.5 * math.cos(th) ** 2)))
        if lo:
            flat_string(part, pts, 0.0022, "twine", TWINE_TILE)
        else:
            tube(part, pts, rad, 3, "twine", TWINE_TILE, caps=False)
    for (turn, long, bend) in ((math.radians(-62), 0.04, 1.0), (math.radians(-118), 0.033, -1.0)):
        steps = 2 if lo else 4
        pts = []
        for k in range(steps + 1):
            t = k / float(steps)
            d = 0.002 + long * t
            side = bend * 0.006 * math.sin(t * 3.0)
            pts.append((d * math.cos(turn) - side * math.sin(turn), d * math.sin(turn) + side * math.cos(turn),
                        0.0034 * (1.0 - t) + 0.0015))
        if lo:
            flat_string(part, pts, 0.0022, "twine", TWINE_TILE)
        else:
            tube(part, pts, rad, 3, "twine", TWINE_TILE)
    ball(part, (0, 0, 0.0036), (0.0034, 0.0034, 0.003), 4, 2, "twine", TWINE_TILE)
    return {"body": part}, [], None


def build_tag(lo):
    """A blank card tag on a loop of string. It hangs along -Y from its origin, lying on whatever is under it."""
    part = Part()
    turn = math.radians(13.0)
    eye = Vector((0.0, -0.03, 0.0))

    def card(x, y):
        dx, dy = x - eye.x, y - eye.y
        p = Vector((eye.x + dx * math.cos(turn) - dy * math.sin(turn), eye.y + dx * math.sin(turn) + dy * math.cos(turn), 0.0))
        p.z = 0.0018 + 0.05 * max(0.0, -0.03 - p.y)
        return p

    shape = [(-0.008, -0.022), (-0.017, -0.033), (-0.017, -0.086), (0.017, -0.086), (0.017, -0.033), (0.008, -0.022)]
    ids = [part.add(card(x, y)) for (x, y) in shape]
    uvs = [region_uv("tag", (-y - 0.022) / 0.064, (x + 0.017) / 0.034) for (x, y) in shape]
    fan(part, ids, uvs, "tag")
    hole = card(0.0, -0.0285)
    pts = [(0.0, 0.0, 0.0012), (0.003, -0.01, 0.004), (0.002, -0.02, 0.0042), (hole.x, hole.y, hole.z + 0.0008)]
    if lo:
        flat_string(part, pts, 0.0018, "twine", TWINE_TILE)
    else:
        tube(part, pts, 0.0011, 3, "twine", TWINE_TILE)
    return {"body": part}, [], None


# ------------------------------------------------------------------ into Blender
SHARP = {"parcel": 24.0, "bow_classic": 62.0, "bow_pompom": 62.0, "bow_rosette": 30.0, "bow_string": 62.0, "tag": 40.0}


def make_object(name, part, mats, parent, sharp):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([tuple(p) for p in part.v], [], [f[0] for f in part.faces])
    layer = mesh.uv_layers.new(name="UVMap")
    loop = 0
    for (_idx, uvs, _mat) in part.faces:
        for uv in uvs:
            layer.data[loop].uv = uv
            loop += 1
    used = []
    for (_idx, _uvs, mat) in part.faces:
        if mat not in used:
            used.append(mat)
    for mat in used:
        mesh.materials.append(mats[mat])
    for poly, (_idx, _uvs, mat) in zip(mesh.polygons, part.faces):
        poly.material_index = used.index(mat)
        poly.use_smooth = True
    mesh.update()
    mesh.set_sharp_from_angle(angle=math.radians(sharp))
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.parent = parent
    return obj


def preview_material(name, picture, shiny):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    shader = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
    shader.inputs["Roughness"].default_value = 0.4 if shiny else 0.8
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = picture
    links.new(tex.outputs["Color"], shader.inputs["Base Color"])
    mat.use_backface_culling = False
    return mat


def save_png(path, rgba):
    h, w, _ = rgba.shape
    image = bpy.data.images.new(os.path.basename(path), w, h, alpha=True)
    image.alpha_mode = 'STRAIGHT'
    image.pixels.foreach_set(np.clip(rgba, 0.0, 1.0).astype(np.float32).ravel())
    image.filepath_raw = path
    image.file_format = 'PNG'
    image.save()
    bpy.data.images.remove(image)


# which square each material wears in the .blend, and in which sample colours (the game picks its own)
WEARS = {"paper": ("trees", None), "inside": ("plain", None), "ribbon": ("satin", None), "twine": ("twine", None),
         "rope": ("twine", ((0.82, 0.62, 0.2), (0.6, 0.42, 0.12), (1, 1, 1))), "tissue": ("tissue", None),
         "tag": ("parts", None), "seal": ("parts", ((0.82, 0.62, 0.2), (0.98, 0.9, 0.6), (1, 1, 1))),
         "tape": ("parts", ((0.93, 0.9, 0.8), (1, 1, 1), (1, 1, 1)))}

KINDS = [("cube", lambda lo: build_box((0.16, 0.16, 0.16), lo, 11)),
         ("shirt_box", lambda lo: build_box((0.30, 0.22, 0.06), lo, 23, tag_on_top=True)),
         ("tall_box", lambda lo: build_box((0.12, 0.12, 0.26), lo, 37, upright=True)),
         ("long_box", lambda lo: build_box((0.36, 0.09, 0.08), lo, 41, tag_on_top=True)),
         ("drum", lambda lo: build_drum(lo, 53)),
         ("bag", lambda lo: build_bag(lo, 61)),
         ("hat_box", lambda lo: build_hat_box(lo, 71)),
         ("parcel", lambda lo: build_parcel(lo, 83)),
         ("bow_classic", build_bow_classic),
         ("bow_pompom", build_bow_pompom),
         ("bow_rosette", build_bow_rosette),
         ("bow_string", build_bow_string),
         ("tag", build_tag)]


def main():
    out = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv and len(sys.argv) > sys.argv.index("--") + 1 else ""
    os.makedirs(MODELS, exist_ok=True)
    os.makedirs(TEXTURES, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    layers = paint.paint_all()
    save_png(os.path.join(TEXTURES, "presents_papers.png"), paint.sheet(layers))
    if out:
        os.makedirs(out, exist_ok=True)
        save_png(os.path.join(out, "papers_preview.png"), paint.preview_sheet(layers))
    mats = {}
    for name, (square, colours) in WEARS.items():
        picture = paint.tinted(layers[square], *(colours or paint.PREVIEW[square]))
        image = bpy.data.images.new("preview_" + name, paint.N, paint.N, alpha=True)
        image.pixels.foreach_set(picture.astype(np.float32).ravel())
        image.pack()
        mats[name] = preview_material(name, image, name in ("ribbon", "tape", "seal"))
    report = []
    for n, (kind, build) in enumerate(KINDS):
        counts = {}
        for lo in (False, True):
            name = kind + ("_lo" if lo else "")
            parts, anchors, warp = build(lo)
            parent = bpy.data.objects.new(name, None)
            parent.empty_display_size = 0.02
            bpy.context.scene.collection.objects.link(parent)
            parent.location = (n * 0.45, 0.6 if lo else 0.0, 0.0)
            for piece, part in parts.items():
                closed, opened, turned = settle(part, "%s_%s" % (name, piece))
                if warp:
                    part.warp(warp)
                outward_check(part, "%s_%s" % (name, piece))
                make_object("%s_%s" % (name, piece), part, mats, parent, SHARP.get(kind, 50.0))
                counts.setdefault(piece, []).append(part.triangles())
                print("  %-28s %4d triangles, %2d closed pieces outward, %2d open sheets, %3d faces turned"
                      % ("%s_%s" % (name, piece), part.triangles(), closed, opened, turned))
            for anchor in anchors:
                mark = bpy.data.objects.new("%s_%s" % (name, anchor.name), None)
                mark.empty_display_type = 'ARROWS'
                mark.empty_display_size = 0.02
                bpy.context.scene.collection.objects.link(mark)
                mark.parent = parent
                mark.location = Vector(warp(anchor.at)) if warp else anchor.at
                up = -anchor.down
                side = up.cross(anchor.out).normalized()
                from mathutils import Matrix
                basis = Matrix((side, up, anchor.out)).transposed()
                mark.rotation_euler = basis.to_euler()
                mark.scale = (anchor.scale, anchor.scale, anchor.scale)
        report.append((kind, counts))
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "presents.blend"))
    bpy.ops.export_scene.gltf(filepath=os.path.join(MODELS, "presents.glb"), export_format='GLB', export_yup=True,
                              export_apply=False, export_image_format='NONE', export_animations=False)
    print("BUILT presents (triangles full / low):")
    for kind, counts in report:
        body = [counts["body"][i] + (counts["lid"][i] if "lid" in counts else 0) for i in (0, 1)]
        line = "  %-12s body %d / %d" % (kind, body[0], body[1])
        for piece in ("ribbon_cross", "ribbon_band", "ribbon_diag"):
            if piece in counts:
                line += ", with %s %d / %d" % (piece[7:], body[0] + counts[piece][0], body[1] + counts[piece][1])
        print(line)


main()
