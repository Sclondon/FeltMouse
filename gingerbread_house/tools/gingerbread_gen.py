# The gingerbread house library: builds houses the way real ones are made, from separate baked slabs
# stuck together with piped icing, and the sweets that go on them. Runs in Blender's Python (it uses
# mathutils); build_gingerbread.py is the command that turns what this makes into a .blend, a .glb and
# the manifest.
#
#   house(kind, lo)   -> House: its parts (shell, board, spill, door) and its slots (where things go)
#   piece(name, lo)   -> Part: a sweet, a fence wafer, an icicle, a snowman...
#   KINDS, PIECES     the names
#
# Sizes are metres, Z up, the front of a house faces -Y, its foot (the underside of its board) at z 0.
# A slab is a flat outline with holes, a thickness, edges rounded off and slightly out of square. Every
# face is wound from the way it must face, and build_gingerbread.py checks every closed piece again.
#
# Each point carries two numbers besides its place: `tone` (the bread darker at a slab's baked edge)
# and `glow` (how much of the light inside the house reaches it: 1 on the inner faces and the panes,
# fading to 0 at the outside of a window's reveal). They reach the game as the points' colour (red
# and green).
import math
import random

from mathutils import Matrix, Vector
from mathutils.geometry import tessellate_polygon

import paint_gingerbread as paint

TAU = math.pi * 2.0
X = Vector((1.0, 0.0, 0.0))
Y = Vector((0.0, 1.0, 0.0))
Z = Vector((0.0, 0.0, 1.0))
G = 0.008       # how thick the board is: the houses stand on z = G
T = 0.006       # how thick a baked slab is
BEAD = 0.0034   # half the width of a line of piped icing

KINDS = ["cottage", "townhouse", "chalet", "church", "shop", "wonky"]
PIECES = ["card", "gumdrop", "disc", "cane", "allsort", "wafer", "stick", "icicle", "roof_snow", "blob", "snowman",
          "person", "fir", "village_board"]


# ------------------------------------------------------------------ pieces of mesh
class Part:
    """Points (with tone, glow and, for piped icing, a normal of their own) and faces as [indices, uvs, material]."""

    def __init__(self):
        self.v = []
        self.tone = []
        self.glow = []
        self.n = []
        self.faces = []

    def add(self, p, tone=1.0, glow=0.0, normal=None):
        self.v.append(Vector((float(p[0]), float(p[1]), float(p[2]))))
        self.tone.append(tone)
        self.glow.append(glow)
        self.n.append(Vector(normal).normalized() if normal is not None else None)
        return len(self.v) - 1

    def normal_of(self, ids):
        total = Vector((0.0, 0.0, 0.0))
        pts = [self.v[i] for i in ids]
        for a, b in zip(pts, pts[1:] + pts[:1]):
            total += a.cross(b)
        return total

    def face(self, ids, uvs, mat, toward=None):
        """A face. Corners on top of the one before are dropped. toward: the way it must face."""
        keep = []
        for i, uv in zip(ids, uvs):
            if keep and (keep[-1][0] == i or (self.v[keep[-1][0]] - self.v[i]).length < 1e-7):
                continue
            keep.append((i, uv))
        while len(keep) > 2 and (self.v[keep[0][0]] - self.v[keep[-1][0]]).length < 1e-7:
            keep.pop()
        if len(keep) < 3:
            return
        ids = [k[0] for k in keep]
        uvs = [k[1] for k in keep]
        normal = self.normal_of(ids)
        if normal.length < 1e-12:
            return
        if toward is not None and normal.dot(toward) < 0.0:
            ids.reverse()
            uvs.reverse()
        self.faces.append([ids, uvs, mat])

    def away(self, ids, uvs, mat, centre):
        """A face that looks away from a point (for anything convex)."""
        mid = sum((self.v[i] for i in ids), Vector((0.0, 0.0, 0.0))) / len(ids)
        self.face(ids, uvs, mat, mid - Vector(centre))

    def transform(self, m):
        turn = m.to_3x3().inverted().transposed()
        self.v = [m @ p for p in self.v]
        self.n = [(turn @ n).normalized() if n is not None else None for n in self.n]

    def light(self, fn):
        self.glow = [max(g, fn(p)) for g, p in zip(self.glow, self.v)]

    def triangles(self):
        return sum(len(f[0]) - 2 for f in self.faces)


class Frame:
    """A flat place to draw on: x and y lie in it, z stands out of it."""

    def __init__(self, o, ex, ey):
        self.o = Vector(o)
        self.ex = Vector(ex).normalized()
        self.ey = Vector(ey).normalized()
        self.ez = self.ex.cross(self.ey)

    def at(self, x, y, z=0.0):
        return self.o + self.ex * x + self.ey * y + self.ez * z


def area(poly):
    return 0.5 * sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(poly, poly[1:] + poly[:1]))


def inset(poly, d):
    """An outline (anticlockwise) moved in by d all round (out for a negative d)."""
    out = []
    count = len(poly)
    for i in range(count):
        p0, p1, p2 = poly[i - 1], poly[i], poly[(i + 1) % count]
        e1 = Vector((p1[0] - p0[0], p1[1] - p0[1])).normalized()
        e2 = Vector((p2[0] - p1[0], p2[1] - p1[1])).normalized()
        n1 = Vector((-e1.y, e1.x))
        n2 = Vector((-e2.y, e2.x))
        k = max(1.0 + n1.dot(n2), 0.25)
        out.append((p1[0] + (n1.x + n2.x) * d / k, p1[1] + (n1.y + n2.y) * d / k))
    return out


def fill(part, ids, pts, uvs, mat, toward):
    """Fills loops of points (the first the outline, the rest holes in it) with triangles."""
    flat_ids = [i for loop in ids for i in loop]
    flat_uvs = [uv for loop in uvs for uv in loop]
    tris = tessellate_polygon([[Vector((p[0], p[1], 0.0)) for p in loop] for loop in pts])
    flat = [p for loop in pts for p in loop]
    got = 0.0
    # the filler winds all its triangles one way: find which from the fat ones, so that a sliver between
    # three points in a line (its own facing is noise) is wound like the rest and the skin stays closed
    votes = 0.0
    sized = []
    for (a, b, c) in tris:
        size = abs((flat[b][0] - flat[a][0]) * (flat[c][1] - flat[a][1]) - (flat[c][0] - flat[a][0]) * (flat[b][1] - flat[a][1])) / 2.0
        got += size
        sized.append(size)
        if size > 1e-8:
            votes += size if part.normal_of([flat_ids[a], flat_ids[b], flat_ids[c]]).dot(toward) > 0.0 else -size
    for (a, b, c), size in zip(tris, sized):
        ids, uvs = [flat_ids[a], flat_ids[b], flat_ids[c]], [flat_uvs[a], flat_uvs[b], flat_uvs[c]]
        if votes < 0.0:
            ids.reverse()
            uvs.reverse()
        part.faces.append([ids, uvs, mat])
    want = abs(area(pts[0])) - sum(abs(area(h)) for h in pts[1:])
    if abs(got - want) > 0.02 * want + 1e-9:
        raise SystemExit("BAD FILL: a slab's face came out %.6f m2, not %.6f" % (got, want))


def slab(part, frame, outline, holes=(), t=T, lo=False, key=0, grid=None, mat="bread", mat_in="inside", skew=0.0012,
         ground=False, uvfn=None, plain=False, tile=None, edge_tone=0.6):
    """A baked slab: `outline` (and `holes`) drawn on the frame, which is its outer face; it is t thick
    behind that. Out of square by up to `skew` (not at its foot if `ground`), its outer edge rounded
    and baked darker (not `plain` or `lo`). grid: (xs, ys) cuts the back face of a rectangular slab
    into cells, so the light inside can stop at a wall. Returns the outline and holes as built."""
    rng = random.Random(key)
    tile = tile or paint.TILE["bread"]
    if area(outline) < 0.0:
        outline = list(reversed(outline))
    holes = [list(h) if area(h) > 0.0 else list(reversed(h)) for h in holes]
    xs = [p[0] for p in outline]
    ys = [p[1] for p in outline]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    off = [[(rng.uniform(-skew, skew), 0.0 if (ground and j == 0) else rng.uniform(-skew, skew)) for j in range(2)] for _i in range(2)]

    def sk(p):
        s = (p[0] - x0) / max(x1 - x0, 1e-9)
        v = (p[1] - y0) / max(y1 - y0, 1e-9)
        dx = (off[0][0][0] * (1 - s) + off[1][0][0] * s) * (1 - v) + (off[0][1][0] * (1 - s) + off[1][1][0] * s) * v
        dy = (off[0][0][1] * (1 - s) + off[1][0][1] * s) * (1 - v) + (off[0][1][1] * (1 - s) + off[1][1][1] * s) * v
        return (p[0] + dx, p[1] + dy)

    shift = (rng.random(), rng.random())

    def uv(p, z=0.0):
        if uvfn is not None:
            return uvfn(p)
        return ((p[0] + z * 0.7) / tile + shift[0], (p[1] + z * 0.7) / tile + shift[1])

    def put(p, z, tone=1.0):
        return part.add(frame.at(p[0], p[1], z), tone)

    out = [sk(p) for p in outline]
    cut = [[sk(p) for p in h] for h in holes]
    n = frame.ez
    count = len(out)
    fancy = not (lo or plain)
    bev = min(0.0014, t * 0.3)
    dark = 0.0065
    if fancy:
        mid = inset(out, dark)
        b_ids = [put(p, -bev, edge_tone) for p in out]
        c_ids = [put(p, 0.0) for p in mid]
        for i in range(count):
            j = (i + 1) % count
            part.face([b_ids[i], b_ids[j], c_ids[j], c_ids[i]], [uv(out[i], -bev), uv(out[j], -bev), uv(mid[j]), uv(mid[i])], mat, n)
        loops_i, loops_p, loops_u = [c_ids], [mid], [[uv(p) for p in mid]]
        rim_top = b_ids
        rim_z = -bev
    else:
        f_ids = [put(p, 0.0, 0.92 if lo else 1.0) for p in out]
        loops_i, loops_p, loops_u = [f_ids], [out], [[uv(p) for p in out]]
        rim_top = f_ids
        rim_z = 0.0
    hole_front = []
    for h in cut:
        ids = [put(p, 0.0, edge_tone + 0.1) for p in h]
        hole_front.append(ids)
        if fancy:
            wide = inset(h, -dark * 0.6)
            w_ids = [put(p, 0.0) for p in wide]
            for i in range(len(h)):
                j = (i + 1) % len(h)
                part.face([ids[i], ids[j], w_ids[j], w_ids[i]], [uv(h[i]), uv(h[j]), uv(wide[j]), uv(wide[i])], mat, n)
            loops_i.append(w_ids)
            loops_p.append(wide)
            loops_u.append([uv(p) for p in wide])
        else:
            loops_i.append(ids)
            loops_p.append(h)
            loops_u.append([uv(p) for p in h])
    fill(part, loops_i, loops_p, loops_u, mat, n)
    # the back, and the edges between
    d_ids = [put(p, -t, 0.8) for p in out]
    for i in range(count):
        j = (i + 1) % count
        ex, ey = out[j][0] - out[i][0], out[j][1] - out[i][1]
        outward = frame.ex * ey - frame.ey * ex
        part.face([rim_top[i], rim_top[j], d_ids[j], d_ids[i]], [uv(out[i], rim_z), uv(out[j], rim_z), uv(out[j], -t), uv(out[i], -t)],
                  mat, outward)
    back_i, back_p, back_u = [d_ids], [out], [[uv(p, -t) for p in out]]
    for h, ids in zip(cut, hole_front):
        e_ids = [put(p, -t, 0.8) for p in h]
        for i in range(len(h)):
            j = (i + 1) % len(h)
            ex, ey = h[j][0] - h[i][0], h[j][1] - h[i][1]
            into = -(frame.ex * ey - frame.ey * ex)
            part.face([ids[i], ids[j], e_ids[j], e_ids[i]], [uv(h[i]), uv(h[j]), uv(h[j], -t), uv(h[i], -t)], mat, into)
        back_i.append(e_ids)
        back_p.append(h)
        back_u.append([uv(p, -t) for p in h])
    if grid is not None:
        gx, gy = grid
        have = {(round(p[0], 6), round(p[1], 6)): i for p, i in zip(outline, d_ids)}
        made = {}
        for x in gx:
            for y in gy:
                k = (round(x, 6), round(y, 6))
                made[k] = have[k] if k in have else put(sk((x, y)), -t, 0.8)
        for i in range(len(gx) - 1):
            for j in range(len(gy) - 1):
                c = [(gx[i], gy[j]), (gx[i + 1], gy[j]), (gx[i + 1], gy[j + 1]), (gx[i], gy[j + 1])]
                part.face([made[(round(p[0], 6), round(p[1], 6))] for p in c], [uv(sk(p), -t) for p in c], mat_in, -n)
    else:
        fill(part, back_i, back_p, back_u, mat_in, -n)
    return out, cut


def rect_outline(xs, ys):
    """The outline of a rectangle through every cut of a grid (so its back can be made of the grid's cells)."""
    pts = [(x, ys[0]) for x in xs]
    pts += [(xs[-1], y) for y in ys[1:]]
    pts += [(x, ys[-1]) for x in reversed(xs[:-1])]
    pts += [(xs[0], y) for y in reversed(ys[1:-1])]
    return pts


def bead(part, pts, a, b, o, rng, lo=False, step=0.03, mat="icing", swell=0.22, wander=0.0007):
    """A line of piped icing through points. At each, its two feet are at +a and +b and its top at +o
    (so it can lie on a flat, sit in a corner or ride over one). It swells and wanders as a hand does."""
    pts = [Vector(p) for p in pts]
    a, b, o = Vector(a), Vector(b), Vector(o)
    path = [pts[0]]
    for p, q in zip(pts, pts[1:]):
        parts = 1 if lo else max(1, int(round((q - p).length / step)))
        for k in range(1, parts + 1):
            path.append(p.lerp(q, k / parts))
    if len(path) < 2 or (path[-1] - path[0]).length < 1e-5:
        return
    tile = paint.TILE["icing"]
    rows = []
    along = 0.0
    side = (a - b).normalized()
    for k, p in enumerate(path):
        if k:
            along += (p - path[k - 1]).length
        ends = k == 0 or k == len(path) - 1
        big = (0.62 if ends else 1.0) * (1.0 + rng.uniform(-swell, swell))
        p = p + side * rng.uniform(-wander, wander)
        row = (part.add(p + a * big, 1.0, 0.0, a + o * 0.35), part.add(p + o * big, 1.0, 0.0, o), part.add(p + b * big, 1.0, 0.0, b + o * 0.35))
        rows.append((row, along / tile))
    for (r0, v0), (r1, v1) in zip(rows, rows[1:]):
        part.face([r0[0], r0[1], r1[1], r1[0]], [(0.0, v0), (0.5, v0), (0.5, v1), (0.0, v1)], mat, o)
        part.face([r0[1], r0[2], r1[2], r1[1]], [(0.5, v0), (1.0, v0), (1.0, v1), (0.5, v1)], mat, o)
    foot = (a + b) * 0.5
    for (row, v, way) in ((rows[0][0], rows[0][1], (path[0] - path[1]).normalized()), (rows[-1][0], rows[-1][1], (path[-1] - path[-2]).normalized())):
        mid = (part.v[row[0]] + part.v[row[2]]) * 0.5
        tip = part.add(mid + way * o.length * 0.7 + foot * 0.1, 1.0, 0.0, way + o.normalized() * 0.6)
        part.face([row[0], row[1], tip], [(0.0, v), (0.5, v), (0.5, v)], mat, way + o.normalized())
        part.face([row[1], row[2], tip], [(0.5, v), (1.0, v), (0.5, v)], mat, way + o.normalized())


def lathe(part, profile, sides, mat, tile_u, centre=(0.0, 0.0), turn=0.0, mats=None, wobble=None):
    """Something round: `profile` is (radius, height, v) from its foot to its top; a radius of 0 is a point.
    mats: a material for each band of the profile, if they differ."""
    cx, cy = centre
    rings = []
    for (rad, z, v) in profile:
        if rad <= 1e-9:
            rings.append([part.add((cx, cy, z))])
        else:
            ring = []
            for s in range(sides):
                ang = turn + TAU * s / sides
                r = rad * (wobble[s % len(wobble)] if wobble else 1.0)
                ring.append(part.add((cx + r * math.cos(ang), cy + r * math.sin(ang), z)))
            rings.append(ring)
    girth = TAU * max(p[0] for p in profile) / tile_u
    for k in range(len(profile) - 1):
        r0, r1 = rings[k], rings[k + 1]
        v0, v1 = profile[k][2], profile[k + 1][2]
        m = mats[k] if mats else mat
        for s in range(sides):
            s1 = (s + 1) % sides
            u0, u1 = girth * s / sides, girth * (s + 1) / sides
            if len(r0) == 1 and len(r1) == 1:
                continue
            if len(r0) == 1:
                ids, uvs = [r0[0], r1[s], r1[s1]], [((u0 + u1) / 2, v0), (u0, v1), (u1, v1)]
            elif len(r1) == 1:
                ids, uvs = [r0[s], r0[s1], r1[0]], [(u0, v0), (u1, v0), ((u0 + u1) / 2, v1)]
            else:
                ids, uvs = [r0[s], r0[s1], r1[s1], r1[s]], [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
            mid = sum((part.v[i] for i in ids), Vector((0.0, 0.0, 0.0))) / len(ids)
            # the profile runs from the foot up the outside: its right-hand side is out
            out = Vector((mid.x - cx, mid.y - cy, 0.0))
            out = out.normalized() if out.length > 1e-9 else X
            dr, dz = profile[k + 1][0] - profile[k][0], profile[k + 1][1] - profile[k][1]
            part.face(ids, uvs, m, out * dz - Z * dr)
    return rings


def box(part, lo_corner, hi_corner, mat, tile, mat_ends=None):
    """A plain box. Its four upright sides wear `mat` (u round it, v up it), its top and bottom `mat_ends`."""
    x0, y0, z0 = lo_corner
    x1, y1, z1 = hi_corner
    mid = Vector(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    c = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    low = [part.add((x, y, z0)) for (x, y) in c]
    high = [part.add((x, y, z1)) for (x, y) in c]
    run = 0.0
    for i in range(4):
        j = (i + 1) % 4
        wide = math.hypot(c[j][0] - c[i][0], c[j][1] - c[i][1])
        if tile:
            uvs = [(run / tile, z0 / tile), ((run + wide) / tile, z0 / tile), ((run + wide) / tile, z1 / tile), (run / tile, z1 / tile)]
        else:
            uvs = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
        part.away([low[i], low[j], high[j], high[i]], uvs, mat, mid)
        run += wide
    ends = mat_ends or mat
    k = tile or (x1 - x0)
    part.away(high, [((x - x0) / k, (y - y0) / k) for (x, y) in c], ends, mid)
    part.away(low, [((x - x0) / k, (y - y0) / k) for (x, y) in c], ends, mid)


# ------------------------------------------------------------------ slots: where the game puts things
def P(v):
    return ("P", Vector(v))


def D(v):
    return ("D", Vector(v))


def N(v):
    return ("N", Vector(v))


class House:
    def __init__(self, kind, lo):
        self.kind = kind
        self.lo = lo
        self.shell = Part()
        self.board = Part()
        self.spill = Part()
        self.door = Part()
        self.rng = random.Random(KINDS.index(kind) * 101 + 7)
        self.m = Matrix.Identity(4)
        self.slots = {"roofs": [], "ridges": [], "walls": [], "spots": [], "windows": [], "doors": [], "yard": [], "fences": [],
                      "path": [], "blobs": [], "finials": [], "keep_out": [], "chimneys": []}
        self.inside = []        # tests: is a point in the lit inside of the house?
        self.key = 0

    def next_key(self):
        self.key += 1
        return KINDS.index(self.kind) * 1000 + self.key

    def lit(self, p):
        return 1.0 if any(fn(p) for fn in self.inside) else 0.0


def opening_points(op, lo):
    """A window's outline on its wall, anticlockwise."""
    x, y, w, h = op["x"], op["y"], op["w"], op["h"]
    left, right, low, high = x - w / 2, x + w / 2, y - h / 2, y + h / 2
    shape = op.get("shape", "rect")
    if shape == "round":
        count = 6 if lo else 8
        return [(x + w / 2 * math.cos(TAU * (k + 0.5) / count), y + w / 2 * math.sin(TAU * (k + 0.5) / count)) for k in range(count)]
    if shape == "arch":
        cy = high - w / 2
        angs = (0, 90, 180) if lo else (0, 45, 90, 135, 180)
        return [(left, low), (right, low)] + [(x + w / 2 * math.cos(math.radians(a)), cy + w / 2 * math.sin(math.radians(a))) for a in angs]
    if shape == "lancet":
        return [(left, low), (right, low), (right, high - w * 0.8), (x, high), (left, high - w * 0.8)]
    return [(left, low), (right, low), (right, high), (left, high)]


def door_points(op, lo):
    """A doorway's outline from the floor up one side, over and down the other."""
    x, w, h = op["x"], op["w"], op["h"]
    left, right = x - w / 2, x + w / 2
    top = op.get("top", "flat")
    if top == "point":
        return [(left, 0.0), (left, h - w * 0.6), (x, h), (right, h - w * 0.6), (right, 0.0)]
    if top == "round":
        cy = h - w / 2
        angs = (180, 90, 0) if lo else (180, 135, 90, 45, 0)
        return [(left, 0.0)] + [(x + w / 2 * math.cos(math.radians(a)), cy + w / 2 * math.sin(math.radians(a))) for a in angs] + [(right, 0.0)]
    return [(left, 0.0), (left, h), (right, h), (right, 0.0)]


def wall(house, name, normal, foot, length, high, peak, openings, t=T, door_slab=True, role=None):
    """A wall slab standing on `foot` (the middle of its outer face's foot), `length` long and `high`
    to its eaves, with a gable `peak` higher in the middle (0 for none). Cuts its openings, glazes its
    windows, and notes where everything is."""
    lo = house.lo
    normal = Vector(normal)
    frame = Frame(foot, Z.cross(normal), Z)
    hl = length / 2.0
    doors = sorted([op for op in openings if op["type"] == "door"], key=lambda op: op["x"])
    outline = [(-hl, 0.0)]
    for op in doors:
        outline += door_points(op, lo)
    outline.append((hl, 0.0))
    if peak > 0.0:
        if high > 1e-6:
            outline += [(hl, high), (0.0, high + peak), (-hl, high)]
        else:
            outline.append((0.0, peak))
    else:
        outline += [(hl, high), (-hl, high)]
    wins = [op for op in openings if op["type"] == "win"]
    holes = [opening_points(op, lo) for op in wins]
    _out, cut = slab(house.shell, frame, outline, holes, t, lo, house.next_key(), ground=True)
    for op, hole in zip(wins, cut):
        # the pane: sugar glass set in the middle of the wall's thickness, seen from both sides
        tile = paint.TILE["glass"]
        for (z, toward) in ((-t * 0.45, normal), (-t * 0.55, -normal)):
            ids = [house.shell.add(frame.at(p[0], p[1], z), 1.0, 1.0) for p in hole]
            uvs = [(p[0] / tile, p[1] / tile) for p in hole]
            for i in range(1, len(ids) - 1):
                house.shell.face([ids[0], ids[i], ids[i + 1]], [uvs[0], uvs[i], uvs[i + 1]], "glass", toward)
        house.slots["windows"].append({"c": P(frame.at(op["x"], op["y"], 0.0)), "pane": P(frame.at(op["x"], op["y"], -t * 0.45)),
                                       "n": N(normal), "u": D(frame.ex), "w": op["w"], "h": op["h"], "shape": op.get("shape", "rect"),
                                       "shutters": bool(op.get("shutters", False)), "wall": name})
    for op in doors:
        pts = door_points(op, lo)
        if door_slab and op.get("slab", True):
            # the door: the piece that was cut out, a shade smaller, hinged on its left edge (seen from outside)
            left = op["x"] - op["w"] / 2
            shape = inset(list(reversed([(p[0] - left, p[1]) for p in pts])), 0.0012)
            shape = [(max(p[0], 0.0), max(p[1], 0.0008)) for p in shape]
            wide, tall = op["w"], op["h"]
            u0, v0, u1, v1 = paint.REGION["door"]
            slab(house.door, Frame((0.0, 0.0, 0.0), X, Z), shape, (), 0.0045, lo, house.next_key(), mat="biscuit", mat_in="bread",
                 skew=0.0, uvfn=lambda p: (u0 + (u1 - u0) * (0.04 + 0.92 * p[0] / wide), v0 + (v1 - v0) * (0.03 + 0.94 * p[1] / tall)),
                 plain=True)
            house.slots["doors"].append({"c": P(frame.at(op["x"], 0.0, 0.0)), "hinge": P(frame.at(left, 0.0, 0.0052)), "n": N(normal),
                                         "u": D(frame.ex), "w": wide, "h": tall, "top": op.get("top", "flat"),
                                         "canes": bool(op.get("canes", True)), "wall": name})
    spans = [[op["x"] - op["w"] / 2, 0.0, op["x"] + op["w"] / 2, op["h"]] for op in doors]
    spans += [[op["x"] - op["w"] / 2, op["y"] - op["h"] / 2, op["x"] + op["w"] / 2, op["y"] + op["h"] / 2] for op in wins]
    house.slots["walls"].append({"c": P(frame.at(0.0, 0.0, 0.0)), "u": D(frame.ex), "n": N(normal), "w": length, "h": high, "peak": peak,
                                 "holes": spans, "wall": name, "role": role or name})
    return frame


def base_beads(house, frame, x0, x1, gaps, r, lo):
    """Icing along the foot of a wall where it stands on the board, left out across doorways."""
    cuts = sorted(gaps)
    start = x0
    runs = []
    for (g0, g1) in cuts:
        if g0 - 0.003 > start:
            runs.append((start, g0 - 0.003))
        start = max(start, g1 + 0.003)
    if x1 > start:
        runs.append((start, x1))
    n = frame.ez
    for (a0, a1) in runs:
        if a1 - a0 < 0.008:
            continue
        bead(house.shell, [frame.at(a0, 0.0, 0.0), frame.at(a1, 0.0, 0.0)], n * r * 1.25, Z * r * 1.1, (n + Z) * r * 0.78, house.rng, lo)


def gable_house(house, S):
    """A house of two gable walls (front and back), two side walls (none if `wall` is 0: the roof comes
    down to the board), and two roof slabs that meet at a ridge and overhang. Before any turning the
    front is at -y and the ridge runs front to back."""
    lo = house.lo
    w, d, wh = S["w"], S["d"], S["wall"]
    hw, hd = w / 2.0, d / 2.0
    pitch = math.radians(S["pitch"])
    tan, cos, sin = math.tan(pitch), math.cos(pitch), math.sin(pitch)
    rise = hw * tan
    z0 = G
    r = BEAD * S.get("bead", 1.0)
    ohe = S.get("eave", 0.016)
    ohf, ohb = S.get("over_front", 0.014), S.get("over_back", 0.014)
    ops = S.get("openings", {})
    shell = house.shell
    rng = house.rng
    frames = {}
    frames["front"] = wall(house, "front", -Y, (0.0, -hd, z0), w, wh, rise, ops.get("front", []), role=S.get("front_role", "front"))
    frames["back"] = wall(house, "back", Y, (0.0, hd, z0), w, wh, rise, ops.get("back", []), role="back")
    if wh > 1e-6:
        frames["left"] = wall(house, "left", -X, (-hw, 0.0, z0), d - 2 * T, wh, 0.0, ops.get("left", []), role=S.get("left_role", "side"))
        frames["right"] = wall(house, "right", X, (hw, 0.0, z0), d - 2 * T, wh, 0.0, ops.get("right", []), role="side")
    # the roof
    long = hw / cos + (ohe if wh > 1e-6 else 0.0)
    crack = S.get("crack", 0)
    for sx in (-1.0, 1.0):
        n = Vector((sx * sin, 0.0, cos))
        up = Vector((-sx * cos, 0.0, sin))
        ex = up.cross(n)
        frame = Frame(Vector((0.0, 0.0, z0 + wh + rise)) + n * T, ex, up)
        u_lo = -(hd + (ohf if ex.y > 0 else ohb))
        u_hi = hd + (ohb if ex.y > 0 else ohf)
        gx = [u_lo, -(hd - T), hd - T, u_hi]
        gy = [-long, -(hw - T) / cos, 0.0] if wh > 1e-6 else [-long, 0.0]
        if crack == sx:
            # a roof slab that broke on the way out of the tin: two pieces, one slipped, stuck back with too much icing
            uc = 0.012
            line = [(uc + (0.0 if k in (0, 4) else rng.uniform(-0.009, 0.009)), -long * k / 4.0) for k in range(5)]
            one = [(u_lo, -long)] + list(reversed(line)) + [(u_lo, 0.0)]
            gap = 0.0025
            two = [(line[4][0] + gap, -long), (u_hi, -long), (u_hi, 0.0)] + [(p[0] + gap, p[1]) for p in line[:-1]]
            slab(shell, frame, one, (), T, lo, house.next_key(), skew=S.get("skew", 0.0012))
            slipped = Frame(frame.o - n * 0.0022 - up * 0.0045 + ex * 0.001, ex + up * 0.035, up - ex * 0.035)
            slab(shell, slipped, two, (), T, lo, house.next_key(), skew=S.get("skew", 0.0012))
            bead(shell, [frame.at(p[0] + gap * 0.5, p[1], 0.0) for p in line], -ex * r * 1.9, ex * r * 1.9, n * r * 1.2, rng, lo, 0.02)
        else:
            slab(shell, frame, rect_outline(gx, gy), (), T, lo, house.next_key(), grid=(gx, gy), skew=S.get("skew", 0.0012))
        slot = {"c": P(frame.at((u_lo + u_hi) / 2, -long / 2, 0.0)), "u": D(ex), "v": D(-up), "n": N(n), "w": u_hi - u_lo, "l": long,
                "eave": wh > 1e-6, "keep": [], "side": sx}
        house.slots["roofs"].append(slot)
        # where the roof meets each gable, under its overhang
        for sy in (-1.0, 1.0):
            a = Vector((sx * hw, sy * hd, z0 + wh))
            b = Vector((0.0, sy * hd, z0 + wh + rise))
            bead(shell, [a, b], -n * r * 1.2, Y * sy * r * 1.2, (-n + Y * sy) * r * 0.75, rng, lo)
        if wh > 1e-6:
            # the wall's corners, and (not on the low model) where the roof sits on the side walls
            for sy in (-1.0, 1.0):
                foot = Vector((sx * hw, sy * hd, z0))
                bead(shell, [foot, foot + Z * wh], -X * sx * r * 1.2, -Y * sy * r * 1.2, (X * sx + Y * sy) * r * 0.62, rng, lo)
            if not lo:
                down = Vector((sx * cos, 0.0, -sin))
                bead(shell, [(sx * hw, -hd, z0 + wh), (sx * hw, hd, z0 + wh)], -Z * r * 1.2, down * r * 1.2, (down - Z) * r * 0.75, rng, lo)
            base_beads(house, frames["left" if sx < 0 else "right"], -hd + T, hd - T,
                       [(op["x"] - op["w"] / 2, op["x"] + op["w"] / 2) for op in ops.get("left" if sx < 0 else "right", []) if op["type"] == "door"],
                       r, lo)
        else:
            reach = hw + T / sin
            bead(shell, [(sx * reach, -hd, z0), (sx * reach, hd, z0)], X * sx * r * 1.25, up * r * 1.2, (X * sx + up) * r * 0.78, rng, lo)
    # the ridge: the two slabs' top edges stand apart there, and a fat line of icing fills the gap
    top = z0 + wh + rise + T * cos
    reach = T * sin + r * 1.5 * cos
    bead(shell, [(0.0, -(hd + ohf) + 0.002, top), (0.0, hd + ohb - 0.002, top)], (-reach, 0.0, -r * 1.5 * sin), (reach, 0.0, -r * 1.5 * sin),
         (0.0, 0.0, r * 1.25), rng, lo, 0.02)
    house.slots["ridges"].append({"a": P((0.0, -(hd + ohf) + 0.008, top + r * 1.1)), "b": P((0.0, hd + ohb - 0.008, top + r * 1.1))})
    for name in ("front", "back"):
        gaps = [(op["x"] - op["w"] / 2, op["x"] + op["w"] / 2) for op in ops.get(name, []) if op["type"] == "door"]
        gaps += S.get("base_gaps", {}).get(name, [])
        base_beads(house, frames[name], -hw, hw, gaps, r, lo)
    # the chimney: four little slabs on one slope
    if "chimney" in S:
        sx, cy = S["chimney"]["side"], S["chimney"]["y"]
        cx = sx * hw * S["chimney"].get("out", 0.5)
        half, tall, tc = 0.014, S["chimney"].get("tall", 0.045), 0.004

        def roof_top(x):
            return z0 + wh + (hw - abs(x)) * tan + T / cos

        ztop = roof_top(cx) + tall
        lean = S["chimney"].get("lean", 0.0)
        for (m, wide) in ((Y, half * 2), (-Y, half * 2), (X, half * 2 - 2 * tc), (-X, half * 2 - 2 * tc)):
            ex = Z.cross(m)
            mid = Vector((cx, cy, 0.0)) + m * half
            lo_pts = []
            for s in (-1.0, 1.0):
                q = mid + ex * s * wide / 2
                lo_pts.append((s * wide / 2, roof_top(q.x) - 0.0025))
            frame = Frame(mid, ex + Z * lean * ex.x, Z + X * lean)
            slab(shell, frame, [lo_pts[0], lo_pts[1], (wide / 2, ztop), (-wide / 2, ztop)], (), tc, lo, house.next_key(), skew=0.0008, plain=True)
        house.slots["chimneys"].append({"top": P((cx + lean * tall, cy, ztop)), "r": half})
        for slot in house.slots["roofs"]:
            if slot["side"] == sx:
                slot["keep"].append([cy if slot["u"][1].y > 0 else -cy, abs(cx) / cos - long / 2, half * 1.7])
    # the lit inside
    def inside(p):
        if abs(p.x) > hw - T * 0.6 or abs(p.y) > hd - T * 0.6 or p.z < z0 - 0.001:
            return False
        return p.z <= z0 + wh + (hw - abs(p.x)) * tan + 0.0012

    house.inside.append(inside)
    # the floor inside (the board shows: baking parchment)
    ids = [shell.add(p, 1.0, 1.0) for p in ((-hw + T, -hd + T, z0 + 0.0004), (hw - T, -hd + T, z0 + 0.0004), (hw - T, hd - T, z0 + 0.0004),
                                            (-hw + T, hd - T, z0 + 0.0004))]
    shell.face(ids, [(p.x / 0.05, p.y / 0.05) for p in (shell.v[i] for i in ids)], "floor", Z)
    house.slots["light"] = P((0.0, 0.0, z0 + max(wh * 0.55, min(0.05, rise * 0.45))))
    house.slots["height"] = z0 + wh + rise + T * cos + r
    return frames


def spots_on(house, frame, normal, places):
    """Free places on a wall for a motif or a sweet: (x, y, radius)."""
    for (x, y, rad) in places:
        house.slots["spots"].append({"p": P(frame.at(x, y, 0.0)), "n": N(normal), "u": D(frame.ex), "r": rad})


def make_board(house, x0, x1, y0, y1, corner=0.022, doors=True):
    """The cake board the house stands on, dusted with icing sugar, the light from each doorway lying on it."""
    lo = house.lo
    board = house.board
    steps = 1 if lo else 3
    pts = []
    for (cx, cy, start) in ((x1 - corner, y1 - corner, 0.0), (x0 + corner, y1 - corner, 90.0), (x0 + corner, y0 + corner, 180.0),
                            (x1 - corner, y0 + corner, 270.0)):
        for k in range(steps + 1):
            a = math.radians(start + 90.0 * k / steps)
            pts.append((cx + corner * math.cos(a), cy + corner * math.sin(a)))
    mid = Vector(((x0 + x1) / 2, (y0 + y1) / 2, G / 2))
    high = [board.add((p[0], p[1], G)) for p in pts]
    low = [board.add((p[0], p[1], 0.0)) for p in pts]
    c_high = board.add((mid.x, mid.y, G))
    c_low = board.add((mid.x, mid.y, 0.0))
    st = paint.TILE["snow"]
    ft = paint.TILE["foil"]
    run = 0.0
    for i in range(len(pts)):
        j = (i + 1) % len(pts)
        board.face([c_high, high[i], high[j]], [(mid.x / st, mid.y / st), (pts[i][0] / st, pts[i][1] / st), (pts[j][0] / st, pts[j][1] / st)],
                   "snow_flat", Z)
        board.face([c_low, low[i], low[j]], [(mid.x / ft, mid.y / ft), (pts[i][0] / ft, pts[i][1] / ft), (pts[j][0] / ft, pts[j][1] / ft)],
                   "foil", -Z)
        wide = math.hypot(pts[j][0] - pts[i][0], pts[j][1] - pts[i][1])
        board.away([low[i], low[j], high[j], high[i]], [(run / ft, 0.0), ((run + wide) / ft, 0.0), ((run + wide) / ft, G / ft), (run / ft, G / ft)],
                   "foil", mid)
        run += wide
    house.slots["board"] = {"lo": P((x0, y0, 0.0)), "hi": P((x1, y1, G))}


def make_spill(house):
    """The warm light that falls out of each doorway onto the snow: a fan lying a hair above the board,
    the same snow, lit in its middle and not at all at its rim."""
    for door in house.slots["doors"]:
        c, n, u = door["c"][1], door["n"][1], door["u"][1]
        wide, reach = door["w"] * 1.35, 0.05
        mid = house.spill.add(c + n * 0.006 + Z * 0.0007, 1.0, 0.85)
        steps = 3 if house.lo else 6
        rim = []
        for k in range(steps + 1):
            a = math.pi * k / steps
            rim.append(house.spill.add(c + u * wide * math.cos(a) + n * (0.001 + reach * math.sin(a)) + Z * 0.0007, 1.0, 0.0))
        for k in range(steps):
            house.spill.face([mid, rim[k], rim[k + 1]], [(0.0, 0.0)] * 3, "snow_flat", Z)


def yard(house, x0, x1, y0, y1, hw, hd, door_x=0.0, door_w=0.045, front_y=None):
    """The board round a house: where a snowman, a tree or a gingerbread person may stand, where a
    fence runs along its front edge, and the stepping stones from the door."""
    fy = -hd if front_y is None else front_y
    yardy = (y0 + fy) / 2.0 - 0.004
    places = [(x0 + (door_x - door_w - x0) * 0.42, yardy, 0.02), (x1 - (x1 - door_x - door_w) * 0.42, yardy, 0.02),
              ((x0 - hw) / 2, -hd * 0.25, 0.013), ((x1 + hw) / 2, hd * 0.3, 0.013), ((x0 - hw) / 2, hd * 0.75, 0.013),
              ((x1 + hw) / 2, -hd * 0.55, 0.013), (x0 + 0.03, yardy + 0.006, 0.014), (x1 - 0.03, yardy - 0.004, 0.014)]
    for (x, y, rad) in places:
        house.slots["yard"].append({"p": P((x, y, G)), "r": rad})
    edge = y0 + 0.012
    house.slots["fences"].append({"a": P((x0 + 0.02, edge, G)), "b": P((door_x - door_w * 0.5 - 0.016, edge, G))})
    house.slots["fences"].append({"a": P((door_x + door_w * 0.5 + 0.016, edge, G)), "b": P((x1 - 0.02, edge, G))})
    steps = max(1, int((fy - y0 - 0.012) / 0.024))
    for k in range(steps):
        house.slots["path"].append({"p": P((door_x + 0.004 * math.sin(k * 2.3), fy - 0.02 - k * 0.024, G))})


def wall_print(house, frame, x0, x1, t=T, high=0.05):
    """A length of wall as something to keep a player out of."""
    house.slots.setdefault("solid", []).append({"a": P(frame.at(x0, 0.0, 0.0)), "b": P(frame.at(x1, 0.0, -t)), "h": high})


def wall_prints(house, frame, length, openings, high, t=T):
    start = -length / 2
    for op in sorted([o for o in openings if o["type"] == "door"], key=lambda o: o["x"]):
        wall_print(house, frame, start, op["x"] - op["w"] / 2, t, high)
        start = op["x"] + op["w"] / 2
    wall_print(house, frame, start, length / 2, t, high)


# ------------------------------------------------------------------ the houses
def win(x, y, w, h, shape="rect", shutters=False):
    return {"type": "win", "x": x, "y": y, "w": w, "h": h, "shape": shape, "shutters": shutters}


def door(x, w, h, top="flat", canes=True, slab_too=True):
    return {"type": "door", "x": x, "w": w, "h": h, "top": top, "canes": canes, "slab": slab_too}


def finish_plain(house, S, frames, margins=(0.036, 0.036, 0.055, 0.028), door_x=0.0, door_w=0.045, front_y=None, front_x=None):
    """What every gable house gets after its walls: footprints, a board, a yard."""
    hw, hd = S["w"] / 2, S["d"] / 2
    ops = S.get("openings", {})
    for name, frame in frames.items():
        length = S["w"] if name in ("front", "back") else S["d"] - 2 * T
        wall_prints(house, frame, length, ops.get(name, []), S["wall"] + (hw * math.tan(math.radians(S["pitch"])) if name in ("front", "back") else 0.0))
    left, right, front, back = margins
    x0, x1 = -hw - left, hw + right
    y0, y1 = (-hd if front_y is None else front_y) - front, hd + back
    make_board(house, x0, x1, y0, y1)
    yard(house, x0, x1, y0, y1, hw, hd, door_x, door_w, front_y)


def cottage(house):
    S = {"w": 0.2, "d": 0.17, "wall": 0.095, "pitch": 47.0,
         "openings": {"front": [door(0.0, 0.044, 0.072, "round"), win(-0.062, 0.054, 0.034, 0.036, "rect", True), win(0.062, 0.054, 0.034, 0.036, "rect", True)],
                      "back": [win(0.0, 0.058, 0.04, 0.04, "round")],
                      "left": [win(-0.036, 0.054, 0.034, 0.036), win(0.036, 0.054, 0.034, 0.036)],
                      "right": [win(0.0, 0.054, 0.04, 0.036, "arch")]},
         "chimney": {"side": 1.0, "y": 0.04, "out": 0.48}}
    frames = gable_house(house, S)
    spots_on(house, frames["front"], -Y, [(0.0, 0.135, 0.02), (-0.062, 0.1, 0.008), (0.062, 0.1, 0.008)])
    spots_on(house, frames["back"], Y, [(0.0, 0.14, 0.02), (-0.06, 0.05, 0.016), (0.06, 0.05, 0.016)])
    spots_on(house, frames["right"], X, [(-0.05, 0.05, 0.015), (0.05, 0.05, 0.015)])
    finish_plain(house, S, frames)


def townhouse(house):
    S = {"w": 0.125, "d": 0.13, "wall": 0.2, "pitch": 58.0, "eave": 0.013,
         "openings": {"front": [door(0.0, 0.04, 0.068, "flat"), win(-0.03, 0.125, 0.03, 0.042, "arch"), win(0.03, 0.125, 0.03, 0.042, "arch"),
                                win(0.0, 0.232, 0.028, 0.028, "round")],
                      "back": [win(0.0, 0.07, 0.034, 0.04), win(0.0, 0.14, 0.034, 0.04)],
                      "left": [win(0.0, 0.06, 0.032, 0.04, "rect", True), win(0.0, 0.135, 0.032, 0.04, "rect", True)],
                      "right": [win(0.0, 0.06, 0.032, 0.04, "rect", True), win(0.0, 0.135, 0.032, 0.04, "rect", True)]},
         "chimney": {"side": -1.0, "y": 0.025, "out": 0.5, "tall": 0.05}}
    frames = gable_house(house, S)
    spots_on(house, frames["front"], -Y, [(0.0, 0.088, 0.011), (-0.042, 0.05, 0.01), (0.042, 0.05, 0.01), (0.0, 0.178, 0.012)])
    spots_on(house, frames["back"], Y, [(0.0, 0.235, 0.016), (-0.04, 0.105, 0.01), (0.04, 0.105, 0.01)])
    spots_on(house, frames["left"], -X, [(0.0, 0.176, 0.012)])
    spots_on(house, frames["right"], X, [(0.0, 0.176, 0.012)])
    finish_plain(house, S, frames, (0.032, 0.032, 0.052, 0.026), 0.0, 0.04)


def chalet(house):
    S = {"w": 0.22, "d": 0.18, "wall": 0.0, "pitch": 62.0,
         "openings": {"front": [door(0.0, 0.046, 0.072, "flat"), win(0.0, 0.118, 0.034, 0.034, "round"), win(-0.055, 0.034, 0.026, 0.028),
                                win(0.055, 0.034, 0.026, 0.028)],
                      "back": [win(0.0, 0.05, 0.044, 0.044, "rect", True), win(0.0, 0.122, 0.03, 0.03, "round")]},
         "chimney": {"side": 1.0, "y": 0.035, "out": 0.42, "tall": 0.04}}
    frames = gable_house(house, S)
    spots_on(house, frames["front"], -Y, [(0.0, 0.158, 0.012), (0.0, 0.088, 0.008)])
    spots_on(house, frames["back"], Y, [(0.0, 0.16, 0.012), (-0.06, 0.03, 0.012), (0.06, 0.03, 0.012)])
    hw, hd = S["w"] / 2, S["d"] / 2
    pitch = math.radians(S["pitch"])
    for sx in (-1.0, 1.0):      # under the low of each slope there is no headroom: keep a walker out
        house.slots.setdefault("solid", []).append({"a": P((sx * (hw - 0.03 / math.tan(pitch)), -hd, G)),
                                                    "b": P((sx * (hw + T / math.sin(pitch)), hd, G)), "h": 0.03})
    finish_plain(house, S, frames, (0.03, 0.03, 0.055, 0.028), 0.0, 0.046)


def church(house):
    tw, th, sh = 0.07, 0.215, 0.11
    S = {"w": 0.13, "d": 0.2, "wall": 0.11, "pitch": 55.0, "over_front": 0.003, "eave": 0.013,
         "openings": {"front": [door(0.0, 0.038, 0.07, "point", False, False)],
                      "back": [win(0.0, 0.085, 0.04, 0.04, "round")],
                      "left": [win(-0.055, 0.058, 0.024, 0.056, "lancet"), win(0.0, 0.058, 0.024, 0.056, "lancet"), win(0.055, 0.058, 0.024, 0.056, "lancet")],
                      "right": [win(-0.055, 0.058, 0.024, 0.056, "lancet"), win(0.0, 0.058, 0.024, 0.056, "lancet"), win(0.055, 0.058, 0.024, 0.056, "lancet")]},
         "base_gaps": {"front": [(-tw / 2, tw / 2)]}, "front_role": "hidden"}
    frames = gable_house(house, S)
    lo = house.lo
    shell = house.shell
    hw, hd = S["w"] / 2, S["d"] / 2
    z0 = G
    r = BEAD
    yc = -hd - tw / 2
    half = tw / 2
    belfry = win(0.0, 0.178, 0.022, 0.04, "lancet")
    t_ops = {"front": [door(0.0, 0.038, 0.07, "point"), win(0.0, 0.118, 0.028, 0.028, "round"), dict(belfry)],
             "back": [door(0.0, 0.038, 0.07, "point", False, False), dict(belfry)],
             "left": [win(0.0, 0.058, 0.022, 0.05, "lancet"), dict(belfry)],
             "right": [win(0.0, 0.058, 0.022, 0.05, "lancet"), dict(belfry)]}
    tf = {"front": wall(house, "tower_front", -Y, (0.0, yc - half, z0), tw, th, 0.0, t_ops["front"], role="front"),
          "back": wall(house, "tower_back", Y, (0.0, yc + half, z0), tw, th, 0.0, t_ops["back"], role="hidden"),
          "left": wall(house, "tower_left", -X, (-half, yc, z0), tw - 2 * T, th, 0.0, t_ops["left"], role="tower"),
          "right": wall(house, "tower_right", X, (half, yc, z0), tw - 2 * T, th, 0.0, t_ops["right"], role="tower")}
    nave_edge = z0 + S["wall"] + (hw - half) * math.tan(math.radians(S["pitch"]))
    for sx in (-1.0, 1.0):
        foot = Vector((sx * half, yc - half, z0))
        bead(shell, [foot, foot + Z * th], -X * sx * r * 1.2, Y * r * 1.2, (X * sx - Y) * r * 0.62, house.rng, lo)
        foot = Vector((sx * half, yc + half, z0))
        bead(shell, [foot, foot + Z * (nave_edge - z0)], -Y * r * 1.2, X * sx * r * 1.2, (X * sx - Y) * r * 0.75, house.rng, lo)
        bead(shell, [foot + Z * (nave_edge - z0 + 0.012), foot + Z * th], -X * sx * r * 1.2, -Y * r * 1.2, (X * sx + Y) * r * 0.62, house.rng, lo)
        base_beads(house, tf["left" if sx < 0 else "right"], -half + T, half - T, [], r, lo)
    base_beads(house, tf["front"], -half, half, [(-0.019, 0.019)], r, lo)
    # the spire: four three-cornered slabs
    b = half + 0.008
    apex = Vector((0.0, yc, z0 + th + sh))
    long = math.hypot(b, sh)
    ts = 0.005
    for m in (X, -X, Y, -Y):
        n = (m * sh + Z * b).normalized()
        up = (-m * b + Z * sh).normalized()
        frame = Frame(Vector((0.0, yc, z0 + th)) + m * b + n * ts * 0.0, up.cross(n), up)
        slab(shell, frame, [(-b, 0.0), (b, 0.0), (0.0, long)], (), ts, lo, house.next_key(), skew=0.0006)
        house.slots["spots"].append({"p": P(frame.at(0.0, long * 0.3, 0.0)), "n": N(n), "u": D(frame.ex), "r": 0.011})
    for (m1, m2) in ((X, Y), (Y, -X), (-X, -Y), (-Y, X)):
        corner = Vector((0.0, yc, z0 + th)) + (m1 + m2) * b
        bead(shell, [corner, apex], -m2 * r * 1.3 + Z * r * 0.2, -m1 * r * 1.3 + Z * r * 0.2, (m1 + m2) * r * 0.55 + Z * r * 0.5, house.rng, lo)
    house.slots["finials"].append({"p": P(apex - Z * 0.004), "r": 0.011})
    house.slots["height"] = z0 + th + sh

    def in_tower(p):
        return abs(p.x) < half - T * 0.6 and yc - half + T * 0.6 < p.y < yc + half + T * 0.5 and z0 - 0.001 <= p.z <= z0 + th + 0.001

    house.inside.append(in_tower)
    ids = [shell.add(p, 1.0, 1.0) for p in ((-half + T, yc - half + T, z0 + 0.0004), (half - T, yc - half + T, z0 + 0.0004),
                                            (half - T, yc + half, z0 + 0.0004), (-half + T, yc + half, z0 + 0.0004))]
    shell.face(ids, [(p.x / 0.05, p.y / 0.05) for p in (shell.v[i] for i in ids)], "floor", Z)
    spots_on(house, tf["front"], -Y, [(0.0, 0.092, 0.008), (0.0, 0.148, 0.007)])
    spots_on(house, frames["back"], Y, [(0.0, 0.15, 0.016), (-0.04, 0.04, 0.012), (0.04, 0.04, 0.012)])
    spots_on(house, frames["front"], -Y, [(-0.05, 0.06, 0.012), (0.05, 0.06, 0.012)])
    # footprints: the nave's walls (its front left open behind the tower), the tower's
    ops = S["openings"]
    for name, frame in frames.items():
        length = S["w"] if name in ("front", "back") else S["d"] - 2 * T
        wall_prints(house, frame, length, ops.get(name, []), S["wall"])
    for name, frame in tf.items():
        if name != "back":
            wall_prints(house, frame, tw if name == "front" else tw - 2 * T, t_ops[name], th)
    x0, x1, y0, y1 = -hw - 0.036, hw + 0.036, yc - half - 0.05, hd + 0.028
    make_board(house, x0, x1, y0, y1)
    yard(house, x0, x1, y0, y1, hw, hd, 0.0, 0.04, yc - half)
    for sx in (-1.0, 1.0):
        house.slots["yard"].append({"p": P((sx * (half + 0.03), yc - 0.005, G)), "r": 0.018})


def shop(house):
    # built with its ridge front to back, then turned a quarter: its long eaves wall becomes the front
    S = {"w": 0.15, "d": 0.24, "wall": 0.118, "pitch": 40.0, "eave": 0.018,
         "openings": {"left": [door(0.074, 0.044, 0.076, "flat"), win(-0.036, 0.056, 0.1, 0.056)],
                      "right": [win(-0.05, 0.06, 0.036, 0.04), win(0.05, 0.06, 0.036, 0.04)],
                      "front": [win(0.0, 0.06, 0.04, 0.044, "arch", True)],
                      "back": [win(0.0, 0.06, 0.04, 0.044, "arch", True)]},
         "chimney": {"side": 1.0, "y": -0.06, "out": 0.5}, "left_role": "front", "front_role": "side"}
    frames = gable_house(house, S)
    lo = house.lo
    hw, hd = S["w"] / 2, S["d"] / 2
    # the awning over the shop window: a striped slab leaning out from the wall
    lean = math.radians(28.0)
    out = (-X * math.cos(lean) - Z * math.sin(lean)).normalized()
    ex = -(Z.cross(-X))
    frame = Frame(frames["left"].at(-0.036, 0.103, 0.0), ex, out)
    tile = paint.TILE["stripes"] * 1.6
    slab(house.shell, frame, [(-0.058, 0.0), (0.058, 0.0), (0.058, 0.04), (-0.058, 0.04)], (), 0.004, lo, house.next_key(), mat="awning",
         mat_in="awning", skew=0.0008, plain=True, uvfn=lambda p: (p[0] / tile, p[1] / tile * 0.5))
    bead(house.shell, [frame.at(-0.058, 0.0, 0.0), frame.at(0.058, 0.0, 0.0)], Z * BEAD * 1.1, out * BEAD * 1.2, (Z + out) * BEAD * 0.7 + frame.ez * BEAD * 0.5,
         house.rng, lo)
    spots_on(house, frames["front"], -Y, [(0.0, 0.135, 0.016)])
    spots_on(house, frames["back"], Y, [(0.0, 0.135, 0.016)])
    spots_on(house, frames["right"], X, [(0.0, 0.06, 0.014)])
    for name, frame in frames.items():
        length = S["w"] if name in ("front", "back") else S["d"] - 2 * T
        wall_prints(house, frame, length, S["openings"].get(name, []), S["wall"])
    x0, x1, y0, y1 = -hw - 0.058, hw + 0.028, -hd - 0.034, hd + 0.034
    make_board(house, x0, x1, y0, y1)
    # the yard is laid out as the house will stand once turned (its front at -x now)
    edge = x0 + 0.012
    for (y, x, rad) in ((0.0, -hw - 0.04, 0.016), (0.085, -hw - 0.036, 0.014), (-hd - 0.016, 0.02, 0.012), (hd + 0.016, -0.02, 0.012),
                        (-0.04, hw + 0.014, 0.01), (0.045, -hw - 0.044, 0.012)):
        house.slots["yard"].append({"p": P((x, y, G)), "r": rad})
    house.slots["fences"].append({"a": P((edge, hd + 0.014, G)), "b": P((edge, -0.074 + 0.04, G))})
    for k in range(2):
        house.slots["path"].append({"p": P((-hw - 0.02 - k * 0.024, -0.074 + 0.003 * k, G))})
    house.m = Matrix.Rotation(math.radians(90.0), 4, "Z")


def wonky(house):
    S = {"w": 0.16, "d": 0.14, "wall": 0.078, "pitch": 43.0, "bead": 1.55, "skew": 0.0032, "crack": 1.0, "eave": 0.018,
         "openings": {"front": [door(0.014, 0.04, 0.06, "flat"), win(-0.046, 0.046, 0.03, 0.03)],
                      "back": [win(0.012, 0.05, 0.034, 0.03)],
                      "left": [win(0.008, 0.044, 0.032, 0.03)],
                      "right": [win(-0.01, 0.046, 0.03, 0.032)]},
         "chimney": {"side": -1.0, "y": 0.02, "out": 0.5, "tall": 0.036, "lean": 0.16}}
    frames = gable_house(house, S)
    hw, hd = S["w"] / 2, S["d"] / 2
    spots_on(house, frames["front"], -Y, [(0.004, 0.108, 0.016), (0.052, 0.04, 0.011)])
    spots_on(house, frames["back"], Y, [(0.0, 0.11, 0.016), (-0.05, 0.04, 0.012)])
    spots_on(house, frames["right"], X, [(0.04, 0.04, 0.012)])
    spots_on(house, frames["left"], -X, [(-0.042, 0.04, 0.012)])
    # too much icing: blobs squeezed out at the corners, along the eaves and the ridge
    top = G + S["wall"]
    for (x, y, z, rad) in ((-hw, -hd, top * 0.55, 0.008), (hw, -hd, top + 0.004, 0.009), (hw, hd, top * 0.4, 0.007), (-hw, hd, top, 0.008),
                           (0.0, -hd - 0.012, top + hw * math.tan(math.radians(43.0)) + 0.004, 0.01), (hw * 0.5, -hd, G + 0.004, 0.009),
                           (-hw, 0.02, G + 0.004, 0.008)):
        out = Vector((x, y, 0.0)).normalized() if abs(x) + abs(y) > 0.001 else -Y
        house.slots["blobs"].append({"p": P((x, y, z)), "n": N(out + Z * 0.4), "r": rad})
    finish_plain(house, S, frames, (0.034, 0.03, 0.05, 0.026), 0.014, 0.04)
    lean = Matrix.Identity(4)
    lean[0][2] = 0.085
    lean[1][2] = 0.035
    house.m = Matrix.Translation((-0.085 * G, -0.035 * G, 0.0)) @ lean
    house.wonk_parts = True


BUILDERS = {"cottage": cottage, "townhouse": townhouse, "chalet": chalet, "church": church, "shop": shop, "wonky": wonky}


def house(kind, lo=False):
    """Builds a house. Its parts are ready for Blender; its slots are still in Blender's axes (see export_slots)."""
    made = House(kind, lo)
    BUILDERS[kind](made)
    make_spill(made)
    made.shell.light(made.lit)
    # a leaning house leans on its board: the board and the light on it stay flat
    made.shell.transform(made.m)
    if getattr(made, "wonk_parts", False):
        flat = Matrix.Identity(4)
    else:
        flat = made.m
    made.board.transform(flat)
    made.spill.transform(flat)
    made.flat = flat
    return made


def _godot(v):
    """Blender's axes to Godot's: y up, the front at +z."""
    return [round(v.x, 5), round(v.z, 5), round(-v.y, 5)]


def export_slots(made):
    """The house's slots for the manifest: every place and direction in Godot's axes, metres."""
    m = made.m
    turn = m.to_3x3()
    normal_turn = turn.inverted().transposed()
    flat_names = ("yard", "fences", "path", "board")

    def conv(value, flat):
        use = made.flat if flat else m
        if isinstance(value, tuple) and len(value) == 2 and value[0] in ("P", "D", "N"):
            if value[0] == "P":
                return _godot(use @ value[1])
            if value[0] == "D":
                return _godot((use.to_3x3() @ value[1]).normalized())
            return _godot((use.to_3x3().inverted().transposed() @ value[1]).normalized())
        if isinstance(value, dict):
            return {k: conv(v, flat) for k, v in value.items()}
        if isinstance(value, list):
            return [conv(v, flat) for v in value]
        if isinstance(value, float):
            return round(value, 5)
        return value

    out = {}
    for name, value in made.slots.items():
        out[name] = conv(value, name in flat_names)
    # the footprint: the box round everything that stands on the board within reach of a walker
    lows = [p for p in made.shell.v if p.z < G + 0.03]
    xs = [p.x for p in lows]
    ys = [p.y for p in lows]
    out["box"] = {"centre": [round((min(xs) + max(xs)) / 2, 5), 0.0, round(-(min(ys) + max(ys)) / 2, 5)],
                  "half": [round((max(xs) - min(xs)) / 2, 5), round((max(ys) - min(ys)) / 2, 5)],
                  "height": round(max(p.z for p in made.shell.v), 5)}
    solid = []
    for item in out.get("solid", []):
        a, b = item["a"], item["b"]
        solid.append({"centre": [round((a[0] + b[0]) / 2, 5), 0.0, round((a[2] + b[2]) / 2, 5)],
                      "half": [round(abs(a[0] - b[0]) / 2, 5), round(abs(a[2] - b[2]) / 2, 5)], "height": item["h"]})
    out["solid"] = solid
    lo_c, hi_c = out["board"]["lo"], out["board"]["hi"]
    out["board"] = {"centre": [round((lo_c[0] + hi_c[0]) / 2, 5), 0.0, round((lo_c[2] + hi_c[2]) / 2, 5)],
                    "half": [round(abs(hi_c[0] - lo_c[0]) / 2, 5), round(abs(hi_c[2] - lo_c[2]) / 2, 5)], "thick": G}
    out["triangles"] = {"shell": made.shell.triangles(), "board": made.board.triangles(), "door": made.door.triangles(),
                        "spill": made.spill.triangles()}
    return out


# ------------------------------------------------------------------ the sweets and the rest
PERSON = [(0.0, 0.22), (0.07, 0.0), (0.24, 0.0), (0.2, 0.4), (0.46, 0.5), (0.5, 0.62), (0.17, 0.66), (0.2, 0.78), (0.14, 0.93), (0.0, 1.0)]


def piece(name, lo=False):
    part = Part()
    rng = random.Random(PIECES.index(name) * 13 + 5)
    if name == "card":
        # a flat card for piping painted on the sheet: 1 by 1, lying in x and y, facing +z
        ids = [part.add(p) for p in ((-0.5, -0.5, 0.0), (0.5, -0.5, 0.0), (0.5, 0.5, 0.0), (-0.5, 0.5, 0.0))]
        part.face(ids, [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)], "card", Z)
    elif name == "gumdrop":
        r, h = 0.0095, 0.0115
        if lo:
            profile = [(r, 0.0, 0.03), (r * 0.8, h * 0.62, 0.6), (0.0, h, 0.97)]
        else:
            profile = [(r, 0.0, 0.03), (r * 0.93, h * 0.42, 0.4), (r * 0.55, h * 0.88, 0.82), (0.0, h, 0.97)]
        lathe(part, profile, 4 if lo else 5, "sugar", paint.TILE["sugar"])       # no underside: it is stuck down
    elif name == "disc":
        # a round flat sweet: its top wears one of the four discs of the sweets square (the game picks which)
        r, t = 0.011, 0.005
        sides = 5 if lo else 7
        ring = [(r * math.cos(TAU * s / sides), r * math.sin(TAU * s / sides)) for s in range(sides)]
        low = [part.add((x, y, 0.0)) for (x, y) in ring]
        mid = [part.add((x, y, t * 0.7)) for (x, y) in ring]
        if lo:
            top = mid
        else:
            top = [part.add((x * 0.86, y * 0.86, t)) for (x, y) in ring]
        crown = part.add((0.0, 0.0, t * (0.75 if lo else 1.08)))
        centre = (0.0, 0.0, t / 2)

        def duv(x, y, k=0.46):
            return (0.25 + 0.25 * k * x / r, 0.25 + 0.25 * k * y / r)

        for s in range(sides):
            s1 = (s + 1) % sides
            part.away([low[s], low[s1], mid[s1], mid[s]], [duv(*ring[s], 0.96), duv(*ring[s1], 0.96), duv(*ring[s1], 0.9), duv(*ring[s], 0.9)], "disc", centre)
            if not lo:
                part.away([mid[s], mid[s1], top[s1], top[s]], [duv(*ring[s], 0.9), duv(*ring[s1], 0.9), duv(*ring[s1], 0.8), duv(*ring[s], 0.8)], "disc", centre)
            part.away([top[s], top[s1], crown], [duv(*ring[s], 0.8 if not lo else 0.9), duv(*ring[s1], 0.8 if not lo else 0.9), (0.25, 0.25)], "disc", centre)
    elif name == "cane":
        # a candy cane standing on its foot, its crook to +x
        rad, tall, hook = 0.0032, 0.036, 0.0085
        pts = [(0.0, 0.0, 0.0), (0.0, 0.0, tall * 0.5), (0.0, 0.0, tall)]
        pts = [(0.0, 0.0, 0.0), (0.0, 0.0, tall)]
        steps = 2 if lo else 4
        for k in range(1, steps + 1):
            a = math.pi * k / steps
            pts.append((hook - hook * math.cos(a), 0.0, tall + hook * math.sin(a)))
        pts.append((2 * hook, 0.0, tall - 0.006))
        sides = 3 if lo else 4
        rows = []
        along = 0.0
        tile = paint.TILE["stripes"]
        for k, p in enumerate(pts):
            p = Vector(p)
            before = Vector(pts[k - 1]) if k else p
            after = Vector(pts[k + 1]) if k < len(pts) - 1 else p
            tang = (after - before).normalized()
            side = Y
            other = tang.cross(side).normalized()
            if k:
                along += (p - Vector(pts[k - 1])).length
            rows.append(([part.add(p + (side * math.cos(TAU * s / sides) + other * math.sin(TAU * s / sides)) * rad) for s in range(sides)], along / tile, p))
        for (r0, v0, p0), (r1, v1, p1) in zip(rows, rows[1:]):
            for s in range(sides):
                s1 = (s + 1) % sides
                part.away([r0[s], r0[s1], r1[s1], r1[s]], [(s / sides, v0), ((s + 1) / sides, v0), ((s + 1) / sides, v1), (s / sides, v1)], "stripes",
                          (p0 + p1) / 2)
        for (row, v, p, way) in ((rows[0][0], rows[0][1], rows[0][2], -Z), (rows[-1][0], rows[-1][1], rows[-1][2], -Z)):
            mid = part.add(p)
            for s in range(sides):
                part.face([mid, row[s], row[(s + 1) % sides]], [(0.5, v)] * 3, "stripes", way)
    elif name == "allsort":
        box(part, (-0.006, -0.006, 0.0), (0.006, 0.006, 0.0105), "allsort", None, "allsort_top")
    elif name == "wafer":
        # a wafer biscuit standing on its end: 14 mm wide, 3 thick, 45 tall
        tile = paint.TILE["wafer"]
        box(part, (-0.007, -0.0015, 0.0), (0.007, 0.0015, 0.045), "wafer", tile)
    elif name == "stick":
        # a pretzel stick standing up: 50 mm
        lathe(part, [(0.0, 0.0, 0.0), (0.0023, 0.0, 0.0), (0.0023, 0.05, 0.6), (0.0, 0.05, 0.6)], 3 if lo else 5, "pretzel", paint.TILE["bread"])
    elif name == "icicle":
        # hangs from its origin: 1 long, 1 in radius at its root (the game sizes it)
        sides = 3
        wob = [rng.uniform(0.8, 1.15) for _s in range(sides)]
        lathe(part, [(0.0, -1.0, 1.0), (0.42, -0.45, 0.6), (1.0, 0.02, 0.1)] if not lo else [(0.0, -1.0, 1.0), (1.0, 0.02, 0.1)],
              sides, "icing", 9.0, wobble=wob)     # no top: it hangs from under something
    elif name == "roof_snow":
        # snow lying on a slope: 1 wide (x), from the ridge at y 0 down to about y -1 where it ends in a ragged
        # lip, 1 thick (z). The game sizes it to a roof slab.
        cols = 4 if lo else 8
        tile = 1.0
        lip = [-1.0 + rng.uniform(0.0, 0.3) for _k in range(cols + 1)]
        lip[0] = lip[-1] = -0.9
        grid_ids = []
        for k in range(cols + 1):
            x = -0.5 + k / cols
            edge_fall = 0.0 if 0 < k < cols else 1.0
            if lo:
                rows = [(0.0, 0.7), (lip[k] + 0.12, 1.0), (lip[k], 0.0)]
            else:
                rows = [(0.0, 0.6), (lip[k] * 0.5, 1.0 + rng.uniform(-0.15, 0.15)), (lip[k] + 0.1, 1.1), (lip[k], 0.0)]
            grid_ids.append([(part.add((x, y, z * (1.0 - edge_fall))), (x * tile, y * tile)) for (y, z) in rows])
        for k in range(cols):
            a, b = grid_ids[k], grid_ids[k + 1]
            for j in range(len(a) - 1):
                part.face([a[j][0], a[j + 1][0], b[j + 1][0], b[j][0]], [a[j][1], a[j + 1][1], b[j + 1][1], b[j][1]], "snow", Z)
    elif name == "blob":
        # a dollop: 1 in radius, 0.6 high, not quite round
        sides = 4 if lo else 6
        wob = [rng.uniform(0.82, 1.18) for _s in range(sides)]
        if lo:
            profile = [(1.0, 0.0, 0.05), (0.0, 0.6, 1.0)]
        else:
            profile = [(1.0, 0.0, 0.05), (0.8, 0.34, 0.5), (0.0, 0.6, 1.0)]       # no underside: it sits on something
        lathe(part, profile, sides, "blob", 4.0, wobble=wob)
    elif name == "snowman":
        # three marshmallows, the top one with a face, pretzel-stick arms
        sides = 5 if lo else 7
        z = 0.0
        for k, (r, h, dx) in enumerate(((0.0135, 0.014, 0.0), (0.0105, 0.011, 0.001), (0.0082, 0.009, -0.0005))):
            turn = TAU * 0.75 - (2 if lo else 3) * TAU / (2 * sides)
            if lo:
                profile = [(0.0, z, 0.0), (r, z, 0.0), (r, z + h, 1.0), (0.0, z + h, 1.0)]
            else:
                profile = [(0.0, z, 0.0), (r * 0.88, z, 0.0), (r, z + h * 0.5, 0.5), (r * 0.88, z + h, 1.0), (0.0, z + h, 1.0)]
            first = len(part.faces)
            lathe(part, profile, sides, "marsh", 1.0, (dx, 0.0), turn)
            # the three sides (two on the low one) that look forward wear the face, or the buttons
            if k > 0:
                patch = "face" if k == 2 else "buttons"
                u0, v0, u1, v1 = paint.REGION[patch]
                front = 2 if lo else 3
                for f in part.faces[first:]:
                    pts = [part.v[i] for i in f[0]]
                    if len(pts) != 4 or abs(pts[0].z - pts[2].z) < 1e-6:
                        continue
                    mid = sum(pts, Vector((0.0, 0.0, 0.0))) / 4
                    ang = (math.atan2(mid.y, mid.x - dx) - turn) % TAU
                    s = int(ang / (TAU / sides))
                    if s >= front:
                        continue
                    uvs = []
                    for p in pts:
                        a = (math.atan2(p.y, p.x - dx) - turn) % TAU
                        if a > TAU - 0.01:
                            a = 0.0
                        fu = min(max(a / (front * TAU / sides), 0.0), 1.0)
                        fv = (p.z - z) / h
                        uvs.append((u0 + (u1 - u0) * (0.04 + 0.92 * fu), v0 + (v1 - v0) * (0.04 + 0.92 * fv)))
                    f[1] = uvs
                    f[2] = patch
            z += h - 0.0006
        for s in (-1.0, 1.0):
            a = Vector((s * 0.009, 0.0, 0.019))
            b = Vector((s * 0.026, -0.003, 0.028 + 0.003 * s))
            side = (b - a).normalized()
            up = side.cross(Y).normalized()
            rad = 0.0013
            ra = [part.add(a + (Y * math.cos(TAU * k / 3) + up * math.sin(TAU * k / 3)) * rad) for k in range(3)]
            rb = [part.add(b + (Y * math.cos(TAU * k / 3) + up * math.sin(TAU * k / 3)) * rad) for k in range(3)]
            for k in range(3):
                k1 = (k + 1) % 3
                part.away([ra[k], ra[k1], rb[k1], rb[k]], [(0.0, 0.0), (0.3, 0.0), (0.3, 0.3), (0.0, 0.3)], "pretzel", (a + b) / 2)
            part.face(rb, [(0.0, 0.0)] * 3, "pretzel", side)
            part.face(ra, [(0.0, 0.0)] * 3, "pretzel", -side)
    elif name == "person":
        # a gingerbread person, a biscuit standing on its feet: 42 mm wide, 52 tall, 4 thick, its face to -y
        wide, tall = 0.042, 0.052
        shape = PERSON + [(-x, y) for (x, y) in reversed(PERSON[1:-1])]
        u0, v0, u1, v1 = paint.REGION["person"]
        slab(part, Frame((0.0, -0.002, 0.0), X, Z), [(x * wide, y * tall) for (x, y) in shape], (), 0.004, lo, 77, mat="person", mat_in="bread",
             skew=0.0, plain=True, uvfn=lambda p: (u0 + (u1 - u0) * (p[0] / wide + 0.5), v0 + (v1 - v0) * (p[1] / tall)))
    elif name == "fir":
        # an ice-cream cone upside down, piped green: three skirts
        sides = 5 if lo else 7
        if lo:
            profile = [(0.0, 0.0, 0.0), (0.019, 0.0, 0.0), (0.0, 0.062, 2.0)]
        else:
            profile = [(0.0, 0.0, 0.0), (0.02, 0.0, 0.0), (0.0105, 0.024, 0.75), (0.0155, 0.021, 0.85), (0.0062, 0.044, 1.55), (0.0105, 0.041, 1.65),
                       (0.0, 0.064, 2.3)]
        lathe(part, profile, sides, "fir", paint.TILE["tree"])
    elif name == "village_board":
        # a board 1 by 1 for a whole village (the game stretches it): snow on top, foil round its edge
        made = House("cottage", lo)
        make_board(made, -0.5, 0.5, -0.5, 0.5, 0.05)
        part = made.board
    else:
        raise SystemExit("no such piece: " + name)
    return part
