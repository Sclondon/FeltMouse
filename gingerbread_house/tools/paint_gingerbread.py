# Paints the gingerbread houses' one picture: twenty 256-pixel squares in a 5 x 4 sheet
# (textures/gingerbread_sheet.png). Used by build_gingerbread.py (which runs in Blender; this file
# only needs numpy).
#
# No square holds a colour. Each is four masks, and the game's one shader tints them with the colours
# every point of a house carries (so one picture serves every palette):
#   red    where the "print" colour is: icing piped on, the stripes of a sweet, flour, sugar crystals
#   green  where the "accent" colour is: a second colour of icing, buttons, a carrot nose
#   blue   light and dark, painted (0.83 is "as it is"): pits and cracks in the bread, the round of a
#          piped line, bubbles in sugar glass
#   alpha  how shiny (0.1 dull bread .. 0.9 boiled sugar)
# The squares named in DECALS are drawn only where red or green is: they are piping laid over
# whatever is underneath. Row 0 of every array here is the BOTTOM of the picture.
import math

import numpy as np

N = 256
TAU = math.pi * 2.0
SOFT = 1.3 / N
COLS, ROWS = 5, 4

LAYERS = ["bread", "icing", "snow", "glass", "scallop", "lattice",
          "bands", "motifs_a", "motifs_b", "sweets", "stripes", "sugar",
          "wafer", "cookie", "tree", "parts", "foil", "plain", "motifs_c", "spare"]
DECALS = ("scallop", "lattice", "bands", "motifs_a", "motifs_b", "motifs_c")

# How many metres of a surface one repeat of a tiling square covers.
TILE = {"bread": 0.08, "icing": 0.03, "snow": 0.07, "glass": 0.05, "scallop": 0.04, "lattice": 0.03,
        "bands": 0.04, "stripes": 0.022, "sugar": 0.03, "wafer": 0.024, "tree": 0.03, "foil": 0.04, "plain": 0.05}

# The bands square: four strips that tile along u. Each is (v0, v1).
BANDS = {"zigzag": (0.75, 1.0), "loops": (0.5, 0.75), "dots": (0.25, 0.5), "wave": (0.0, 0.25)}
# The motif squares: 3 x 3 cells, counted from the bottom left.
MOTIFS_A = ["heart", "snowflake", "star", "swirl", "holly", "wreath", "fir", "flower", "drips"]
MOTIFS_B = ["frame_square", "frame_arch", "frame_round", "door_arch", "bricks", "sprinkles", "hatch", "bow", "frame_tall"]
MOTIFS_C = ["ring_square", "ring_arch", "ring_round", "ring_tall", "cross", "dot", "burst", "curl", "dashes"]
# The sweets square: 2 x 2 discs. The parts and cookie squares: patches (u0, v0, u1, v1).
DISCS = ["peppermint", "lolly", "button", "jammy"]
REGION = {
    "face": (0.0, 0.5, 0.5, 1.0),
    "allsort": (0.5, 0.5, 1.0, 1.0),
    "buttons": (0.0, 0.0, 0.5, 0.5),
    "marsh": (0.5, 0.0, 1.0, 0.5),
    "person": (0.0, 0.0, 0.5, 1.0),
    "door": (0.5, 0.0, 1.0, 1.0),
}

# colours for the previews only (the .blend's materials and the sheet for looking at): base, print, accent
BREAD = (0.56, 0.31, 0.14)
PREVIEW = {
    "bread": (BREAD, (0.36, 0.17, 0.07), (0.93, 0.87, 0.76)),
    "icing": ((0.97, 0.95, 0.9), (1, 1, 1), (1, 1, 1)),
    "snow": ((0.95, 0.96, 0.98), (0.8, 0.86, 0.95), (1, 1, 1)),
    "glass": ((0.95, 0.6, 0.14), (1.0, 0.86, 0.5), (1, 1, 1)),
    "scallop": ((0.8, 0.78, 0.74), (0.97, 0.95, 0.9), (0.78, 0.1, 0.1)),
    "lattice": ((0.8, 0.78, 0.74), (0.97, 0.95, 0.9), (0.78, 0.1, 0.1)),
    "bands": ((0.8, 0.78, 0.74), (0.97, 0.95, 0.9), (0.78, 0.1, 0.1)),
    "motifs_a": ((0.8, 0.78, 0.74), (0.97, 0.95, 0.9), (0.78, 0.1, 0.1)),
    "motifs_b": ((0.8, 0.78, 0.74), (0.97, 0.95, 0.9), (0.14, 0.5, 0.2)),
    "motifs_c": ((0.8, 0.78, 0.74), (0.97, 0.95, 0.9), (0.78, 0.1, 0.1)),
    "spare": ((0.93, 0.91, 0.86), (1, 1, 1), (1, 1, 1)),
    "sweets": ((0.78, 0.08, 0.1), (0.97, 0.95, 0.92), (0.14, 0.5, 0.2)),
    "stripes": ((0.97, 0.95, 0.92), (0.78, 0.08, 0.1), (0.14, 0.5, 0.2)),
    "sugar": ((0.78, 0.08, 0.1), (1.0, 0.92, 0.9), (1, 1, 1)),
    "wafer": ((0.86, 0.68, 0.42), (0.66, 0.46, 0.24), (1, 1, 1)),
    "cookie": (BREAD, (0.97, 0.95, 0.9), (0.78, 0.1, 0.1)),
    "tree": ((0.16, 0.5, 0.22), (0.97, 0.97, 0.95), (0.85, 0.12, 0.12)),
    "parts": ((0.97, 0.96, 0.94), (0.12, 0.1, 0.1), (0.95, 0.5, 0.1)),
    "foil": ((0.78, 0.8, 0.84), (1, 1, 1), (1, 1, 1)),
    "plain": ((0.93, 0.91, 0.86), (1, 1, 1), (1, 1, 1)),
}


def _smooth(t):
    return t * t * (3.0 - 2.0 * t)


def pnoise(cells, rs, n=N):
    """Value noise that tiles both ways."""
    g = rs.random_sample((cells, cells))
    t = np.arange(n) / n * cells
    i0 = np.floor(t).astype(int)
    f = _smooth(t - i0)
    i1 = (i0 + 1) % cells
    i0 %= cells
    fy = f[:, None]
    fx = f[None, :]
    return (g[i0][:, i0] * (1 - fx) + g[i0][:, i1] * fx) * (1 - fy) + (g[i1][:, i0] * (1 - fx) + g[i1][:, i1] * fx) * fy


def fbm(cells, octaves, rs, n=N):
    total = np.zeros((n, n))
    amp, norm = 1.0, 0.0
    for _o in range(octaves):
        total += pnoise(cells, rs, n) * amp
        norm += amp
        amp *= 0.5
        cells *= 2
    return total / norm


def grid():
    t = (np.arange(N) + 0.5) / N
    return np.meshgrid(t, t)      # X along a row, Y up the rows


def wd(a):
    """A difference wrapped into -0.5 .. 0.5, so shapes run over the square's edge and back in."""
    return (a + 0.5) % 1.0 - 0.5


def edge(d, soft=SOFT):
    """1 inside a shape (d below 0), 0 outside, a soft pixel between."""
    return np.clip(0.5 - d / soft, 0.0, 1.0)


def seg(x, y, ax, ay, bx, by):
    """How far each point is from the line from a to b."""
    dx, dy = bx - ax, by - ay
    t = np.clip(((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy + 1e-12), 0.0, 1.0)
    return np.hypot(x - ax - t * dx, y - ay - t * dy)


def path(x, y, pts, closed=False):
    """How far each point is from a line through points."""
    d = np.full(x.shape, 9.0)
    ends = list(zip(pts, pts[1:])) + ([(pts[-1], pts[0])] if closed else [])
    for (a, b) in ends:
        d = np.minimum(d, seg(x, y, a[0], a[1], b[0], b[1]))
    return d


def layer(r, g, b, a):
    out = np.zeros((N, N, 4))
    out[:, :, 0] = np.clip(r, 0.0, 1.0)
    out[:, :, 1] = np.clip(g, 0.0, 1.0)
    out[:, :, 2] = np.clip(b, 0.0, 1.0)
    out[:, :, 3] = np.clip(a, 0.06, 1.0)
    return out


def piped(d, r):
    """A piped line from how far each point is from its middle: (where it is, how high it stands 0..1)."""
    return edge(d - r), np.sqrt(np.clip(1.0 - (d / r) ** 2, 0.0, 1.0))


def lit(height, strength=0.2, wrap=True):
    """Light and dark for something standing up off the surface, lit from the upper left."""
    if wrap:
        sx = np.roll(height, 2, axis=1) - np.roll(height, -2, axis=1)
        sy = np.roll(height, -2, axis=0) - np.roll(height, 2, axis=0)
    else:
        pad = np.pad(height, 2, mode="edge")
        sx = pad[2:-2, :-4] - pad[2:-2, 4:]
        sy = pad[4:, 2:-2] - pad[:-4, 2:-2]
    return 0.78 + 0.1 * height - strength * (sx + sy)


def icing_layer(r_d, r_r, g_d=None, g_r=0.0, wrap=True):
    """A decal square: white piping where r_d < r_r, the second colour where g_d < g_r."""
    mask, high = piped(r_d, r_r)
    green = np.zeros_like(mask)
    if g_d is not None:
        green, high_g = piped(g_d, g_r)
        high = np.maximum(high, high_g)
        mask = np.maximum(mask, green)
    return layer(mask, green, lit(high, 0.2, wrap), 0.45 + 0.0 * mask)


# ------------------------------------------------------------------ what the houses are made of
def bread(rs):
    """Baked gingerbread: mottled, pitted, a few fine cracks, a dusting of flour."""
    X, Y = grid()
    tone = 0.83 + 0.12 * (fbm(5, 4, rs) - 0.5) + 0.04 * (rs.random_sample((N, N)) - 0.5)
    dark = np.clip((fbm(4, 3, rs) - 0.52) * 2.6, 0.0, 1.0) * 0.32
    for _k in range(420):       # pits where bubbles burst in the oven
        cx, cy, rad = rs.random_sample(), rs.random_sample(), rs.uniform(0.0028, 0.0085)
        dx, dy = wd(X - cx), wd(Y - cy)
        d = np.hypot(dx, dy)
        pit = edge(d - rad, 2.0 / N)
        rim = edge(np.hypot(dx - rad * 0.5, dy + rad * 0.5) - rad, 2.0 / N) * (1.0 - pit)
        tone = tone - 0.2 * pit * rs.uniform(0.5, 1.0) + 0.035 * rim
    for _k in range(7):         # cracks
        px, py = rs.random_sample(), rs.random_sample()
        ang = rs.uniform(0.0, TAU)
        for _s in range(rs.randint(3, 7)):
            ang += rs.uniform(-0.9, 0.9)
            qx, qy = px + 0.035 * math.cos(ang), py + 0.035 * math.sin(ang)
            d = seg(wd(X - px), wd(Y - py), 0.0, 0.0, qx - px, qy - py)
            crack = edge(d - 0.0022, 1.6 / N)
            tone = tone - 0.16 * crack
            dark = np.maximum(dark, crack * 0.8)
            px, py = qx, qy
    flour = np.clip((fbm(9, 3, rs) - 0.6) * 4.0, 0.0, 1.0) * (rs.random_sample((N, N)) > 0.5) * 0.34
    flour = (flour + np.roll(flour, 1, axis=0) + np.roll(flour, 1, axis=1)) / 3.0
    return layer(dark, flour, tone, 0.12)


def icing(rs):
    """Royal icing out of a piping bag: u across the line, v along it; the rope of a star nozzle."""
    X, Y = grid()
    rope = np.sin(TAU * (Y * 4.0 + 0.35 * np.sin(math.pi * X)))
    tone = 0.84 + 0.06 * rope + 0.07 * np.sin(math.pi * X) ** 2 + 0.03 * (fbm(6, 2, rs) - 0.5)
    shine = 0.4 + 0.25 * np.clip(rope, 0.0, 1.0) * np.sin(math.pi * X) ** 2
    return layer(0.0 * X, 0.0 * X, tone, shine)


def snow(rs):
    """Icing sugar or shredded coconut lying as snow: soft, grainy, a sparkle here and there."""
    tone = 0.845 + 0.07 * (fbm(5, 3, rs) - 0.5) + 0.05 * (rs.random_sample((N, N)) - 0.5)
    spark = rs.random_sample((N, N)) > 0.993
    tone = np.where(spark, 1.0, tone)
    shade = np.clip((fbm(3, 2, rs) - 0.48) * 2.2, 0.0, 1.0) * 0.6
    return layer(shade, 0.0 * tone, tone, np.where(spark, 1.0, 0.14))


def glass(rs):
    """Sugar glass (a melted boiled sweet): bubbles, a wavy surface, streaks of light across it."""
    X, Y = grid()
    wave = fbm(3, 3, rs)
    tone = 0.8 + 0.14 * (wave - 0.5)
    streak = np.clip(np.sin(TAU * (X + Y + 0.25 * wave)) * 1.6 - 0.9, 0.0, 1.0)
    light = streak * 0.7
    for _k in range(26):
        cx, cy, rad = rs.random_sample(), rs.random_sample(), rs.uniform(0.008, 0.022)
        d = np.hypot(wd(X - cx), wd(Y - cy))
        ring = edge(np.abs(d - rad) - 0.003)
        tone = tone - 0.12 * ring
        light = np.maximum(light, edge(np.hypot(wd(X - cx) + rad * 0.4, wd(Y - cy) - rad * 0.4) - rad * 0.3))
    return layer(light, 0.0 * X, tone, 0.9)


def scallop(rs):
    """Rows of piped loops, like roof tiles, a dot hung at each point."""
    X, Y = grid()
    cols, rows = 3, 4
    d = np.full((N, N), 9.0)
    g = np.full((N, N), 9.0)
    for j in range(rows):
        for i in range(cols):
            cx = (i + 0.5 + (0.5 if j % 2 else 0.0)) / cols + rs.uniform(-0.006, 0.006)
            cy = (j + 0.95) / rows
            dx, dy = wd(X - cx), wd(Y - cy)
            rx, ry = 0.5 / cols, 0.86 / rows
            rho = np.sqrt((dx / rx) ** 2 + (dy / ry) ** 2)
            arc = np.abs(rho - 1.0) * min(rx, ry)
            arc = np.where(dy < 0.004, arc, np.hypot(np.abs(dx) - rx, dy))
            d = np.minimum(d, arc)
            g = np.minimum(g, np.hypot(wd(X - cx - rx), wd(Y - cy)))
    return icing_layer(d, 0.02, g, 0.028)


def lattice(rs):
    """Piped diagonal lattice, a dot at every other crossing."""
    X, Y = grid()
    k = 3.0
    d = np.minimum(np.abs(wd((X + Y) * k)), np.abs(wd((X - Y) * k))) / k / math.sqrt(2.0)
    g = np.full((N, N), 9.0)
    for i in range(3):
        g = np.minimum(g, np.hypot(wd(X - i / 3.0), wd(Y - i / 3.0)))
    return icing_layer(d + 0.004 * (fbm(6, 2, rs) - 0.5), 0.02, g, 0.036)


def bands(rs):
    """Four strips of piping that run along u: a zigzag, hanging loops, a row of dots, a wave."""
    X, Y = grid()
    d = np.full((N, N), 9.0)
    g = np.full((N, N), 9.0)

    def mid(name):
        v0, v1 = BANDS[name]
        return (v0 + v1) / 2.0

    # zigzag
    m, amp, n = mid("zigzag"), 0.062, 5
    t = X * n
    tri = np.abs((t % 1.0) * 2.0 - 1.0) * 2.0 - 1.0
    d = np.minimum(d, np.abs(Y - (m + amp * tri)) / math.sqrt(1.0 + (4.0 * amp * n) ** 2))
    # hanging loops, a dot where they meet
    m, n = mid("loops"), 4
    dx = wd(X * n) / n
    top = m + 0.055
    rx, ry = 0.5 / n, 0.105
    rho = np.sqrt((dx / rx) ** 2 + ((Y - top) / ry) ** 2)
    arc = np.where(Y < top + 0.004, np.abs(rho - 1.0) * rx, 9.0)
    d = np.minimum(d, arc)
    g = np.minimum(g, np.hypot(wd(X * n - 0.5) / n, Y - top + 0.012))
    # dots, big and small in turn
    m, n = mid("dots"), 4
    d = np.minimum(d, np.hypot(wd(X * n) / n, Y - m) - 0.02)
    g = np.minimum(g, np.hypot(wd(X * n - 0.5) / n, Y - m) + 0.008)
    # a wave with a dot in each trough
    m, n = mid("wave"), 3
    d = np.minimum(d, np.abs(Y - (m + 0.045 * np.sin(TAU * X * n))) / np.sqrt(1.0 + (0.045 * TAU * n * np.cos(TAU * X * n)) ** 2))
    g = np.minimum(g, np.hypot(wd(X * n - 0.75) / n, Y - m - 0.035))
    g = np.minimum(g, np.hypot(wd(X * n - 0.25) / n, Y - m + 0.035))
    return icing_layer(d, 0.021, g, 0.03)


def _cells(draw_list, rs):
    """A square of 3 x 3 motifs. Each draws in its own cell, x and y from -1 to 1."""
    X, Y = grid()
    r_all = np.zeros((N, N))
    g_all = np.zeros((N, N))
    high = np.zeros((N, N))
    for k, draw in enumerate(draw_list):
        cx, cy = (k % 3 + 0.5) / 3.0, (k // 3 + 0.5) / 3.0
        x, y = (X - cx) * 6.0, (Y - cy) * 6.0
        inside = (np.abs(x) < 1.0) & (np.abs(y) < 1.0)
        rd, rr, gd, gr = draw(x, y, rs)
        soft = SOFT * 6.0
        for (dist, rad, into) in ((rd, rr, r_all), (gd, gr, g_all)):
            if dist is None:
                continue
            m = np.clip(0.5 - (dist - rad) / soft, 0.0, 1.0) * inside
            into += m
            if rad > 0.0:
                high = np.maximum(high, np.sqrt(np.clip(1.0 - (dist / rad) ** 2, 0.0, 1.0)) * inside)
            else:       # a filled shape: flat on top, rounded only at its edge
                high = np.maximum(high, np.clip(-dist / 0.12, 0.0, 1.0) * inside)
    r_all = np.clip(r_all + g_all, 0.0, 1.0)
    return layer(r_all, g_all, lit(high, 0.2, False), 0.45 + 0.0 * X)


LINE = 0.085     # half the width of a piped line in a motif's own cell


def m_heart(x, y, rs):
    yy = y * 1.25 + 0.15
    xx = x * 1.25
    f = (xx * xx + yy * yy - 0.62) ** 3 - xx * xx * yy ** 3
    fill = np.where(f < 0.0, -1.0, 1.0)
    return None, 0.0, fill, 0.5


def m_snowflake(x, y, rs):
    d = np.full(x.shape, 9.0)
    for k in range(3):
        a = k * math.pi / 3.0 + math.pi / 2.0
        ca, sa = math.cos(a), math.sin(a)
        d = np.minimum(d, seg(x, y, -0.8 * ca, -0.8 * sa, 0.8 * ca, 0.8 * sa))
        for s in (-1.0, 1.0):
            for t in (0.5,):
                px, py = s * t * ca, s * t * sa
                for turn in (-0.9, 0.9):
                    b = a + turn
                    d = np.minimum(d, seg(x, y, px, py, px + s * 0.26 * math.cos(b), py + s * 0.26 * math.sin(b)))
    return d, LINE * 0.85, np.hypot(x, y), 0.13


def m_star(x, y, rs):
    pts = []
    for k in range(10):
        a = math.pi / 2.0 + k * math.pi / 5.0
        rad = 0.82 if k % 2 == 0 else 0.36
        pts.append((rad * math.cos(a), rad * math.sin(a)))
    return path(x, y, pts, True), LINE, np.hypot(x, y), 0.14


def m_swirl(x, y, rs):
    pts = []
    for k in range(40):
        a = k * 0.36
        rad = 0.07 + 0.02 * k
        pts.append((rad * math.cos(a), rad * math.sin(a)))
    return path(x, y, pts), LINE, None, 0.0


def m_holly(x, y, rs):
    d = np.full(x.shape, 9.0)
    for turn in (0.5, -0.5 + math.pi):
        ca, sa = math.cos(turn), math.sin(turn)
        u = x * ca + y * sa - 0.45
        v = -x * sa + y * ca
        leaf = np.abs(v) - 0.24 * np.clip(1.0 - (u / 0.42) ** 2, 0.0, 1.0) * (1.0 + 0.25 * np.cos(u * 22.0))
        leaf = np.where(np.abs(u) < 0.42, leaf, 9.0)
        d = np.minimum(d, leaf)
    berries = np.minimum(np.hypot(x - 0.07, y + 0.1), np.minimum(np.hypot(x + 0.12, y - 0.06), np.hypot(x - 0.1, y - 0.14)))
    return d, 0.0, berries, 0.13


def m_wreath(x, y, rs):
    d = np.full(x.shape, 9.0)
    g = np.full(x.shape, 9.0)
    for k in range(12):
        a = k * TAU / 12.0
        px, py = 0.62 * math.cos(a), 0.62 * math.sin(a)
        if k % 3 == 0:
            g = np.minimum(g, np.hypot(x - px, y - py))
        else:
            d = np.minimum(d, np.hypot(x - px, y - py))
    return d, 0.15, g, 0.13


def m_fir(x, y, rs):
    pts = [(0.0, 0.85), (-0.3, 0.4), (-0.12, 0.4), (-0.48, -0.05), (-0.2, -0.05), (-0.62, -0.52), (0.62, -0.52), (0.2, -0.05),
           (0.48, -0.05), (0.12, 0.4), (0.3, 0.4)]
    d = path(x, y, pts, True)
    d = np.minimum(d, seg(x, y, 0.0, -0.52, 0.0, -0.82))
    g = np.minimum(np.hypot(x, y - 0.1), np.minimum(np.hypot(x + 0.22, y + 0.32), np.hypot(x - 0.22, y + 0.3)))
    return d, LINE * 0.9, g, 0.09


def m_flower(x, y, rs):
    d = np.full(x.shape, 9.0)
    for k in range(6):
        a = k * TAU / 6.0
        d = np.minimum(d, np.hypot(x - 0.46 * math.cos(a), y - 0.46 * math.sin(a)))
    return d, 0.19, np.hypot(x, y), 0.2


def m_drips(x, y, rs):
    """Too much icing: a thick line along the top that runs down in drips."""
    d = seg(x, y, -0.95, 0.72, 0.95, 0.72) - 0.1
    for (px, long) in ((-0.7, 0.5), (-0.32, 1.1), (0.05, 0.7), (0.42, 1.3), (0.78, 0.45)):
        d = np.minimum(d, seg(x, y, px, 0.72, px, 0.72 - long) - 0.03)
        d = np.minimum(d, np.hypot(x - px, y - 0.72 + long) - 0.07)
    return d + 0.1, 0.1, None, 0.0


def _frame(x, y, pts, cross):
    d = path(x, y, pts, True)
    for (a, b) in cross:
        d = np.minimum(d, seg(x, y, a[0], a[1], b[0], b[1]))
    return d


def m_frame_square(x, y, rs):
    e = 0.8
    d = _frame(x, y, [(-e, -e), (e, -e), (e, e), (-e, e)], [((0, -e), (0, e)), ((-e, 0), (e, 0))])
    return d, LINE, None, 0.0


def m_frame_arch(x, y, rs):
    e = 0.7
    pts = [(-e, -0.85), (e, -0.85), (e, 0.2)] + [(e * math.cos(a), 0.2 + 0.65 * math.sin(a)) for a in np.linspace(0.3, math.pi - 0.3, 7)] + [(-e, 0.2)]
    d = _frame(x, y, pts, [((0, -0.85), (0, 0.85)), ((-e, 0.0), (e, 0.0))])
    return d, LINE, None, 0.0


def m_frame_round(x, y, rs):
    d = np.abs(np.hypot(x, y) - 0.78)
    d = np.minimum(d, seg(x, y, -0.78, 0.0, 0.78, 0.0))
    d = np.minimum(d, seg(x, y, 0.0, -0.78, 0.0, 0.78))
    return d, LINE, None, 0.0


def m_door_arch(x, y, rs):
    """Piping round a doorway: up one side, over and down the other, a dot at the top."""
    e = 0.82
    pts = [(-e, -0.97), (-e, 0.25)] + [(e * math.cos(a), 0.25 + 0.6 * math.sin(a)) for a in np.linspace(math.pi - 0.3, 0.3, 7)] + [(e, 0.25), (e, -0.97)]
    d = path(x, y, pts)
    return d, LINE * 1.1, np.hypot(x, y - 0.85), 0.11


def m_bricks(x, y, rs):
    d = np.full(x.shape, 9.0)
    for (ax, ay, long) in ((-0.8, 0.55, 0.55), (0.1, 0.6, 0.6), (-0.45, 0.1, 0.5), (0.3, 0.05, 0.5), (-0.85, -0.4, 0.5), (-0.05, -0.45, 0.6),
                           (0.4, -0.8, 0.45), (-0.6, -0.85, 0.4)):
        d = np.minimum(d, seg(x, y, ax, ay, ax + long, ay + rs.uniform(-0.03, 0.03)))
        d = np.minimum(d, seg(x, y, ax, ay, ax, ay - 0.2))
    return d, LINE * 0.75, None, 0.0


def m_sprinkles(x, y, rs):
    d = np.full(x.shape, 9.0)
    g = np.full(x.shape, 9.0)
    for k in range(26):
        px, py, a = rs.uniform(-0.82, 0.82), rs.uniform(-0.82, 0.82), rs.uniform(0.0, math.pi)
        one = seg(x, y, px, py, px + 0.16 * math.cos(a), py + 0.16 * math.sin(a))
        if k % 2:
            d = np.minimum(d, one)
        else:
            g = np.minimum(g, one)
    return d, 0.05, g, 0.05


def m_hatch(x, y, rs):
    d = np.full(x.shape, 9.0)
    for cx in (-0.5, 0.5):
        for cy in (-0.5, 0.5):
            d = np.minimum(d, seg(x, y, cx - 0.28, cy - 0.28, cx + 0.28, cy + 0.28))
            d = np.minimum(d, seg(x, y, cx - 0.28, cy + 0.28, cx + 0.28, cy - 0.28))
    return d, LINE * 0.9, np.hypot(x, y), 0.12


def m_bow(x, y, rs):
    pts_l = [(0.0, 0.1), (-0.75, 0.55), (-0.75, -0.2), (0.0, 0.1)]
    pts_r = [(0.0, 0.1), (0.75, 0.55), (0.75, -0.2), (0.0, 0.1)]
    g = np.minimum(path(x, y, pts_l), path(x, y, pts_r))
    g = np.minimum(g, seg(x, y, 0.0, 0.1, -0.35, -0.8))
    g = np.minimum(g, seg(x, y, 0.0, 0.1, 0.35, -0.8))
    return None, 0.0, g, LINE


def m_frame_tall(x, y, rs):
    """A pointed (lancet) window's frame."""
    e = 0.52
    pts = [(-e, -0.88), (e, -0.88), (e, 0.25), (0.0, 0.9), (-e, 0.25)]
    d = _frame(x, y, pts, [((0, -0.88), (0, 0.9)), ((-e, -0.2), (e, -0.2))])
    return d, LINE * 0.9, None, 0.0


def m_ring_square(x, y, rs):
    e = 0.8
    return path(x, y, [(-e, -e), (e, -e), (e, e), (-e, e)], True), LINE, None, 0.0


def m_ring_arch(x, y, rs):
    e = 0.7
    pts = [(-e, -0.85), (e, -0.85), (e, 0.2)] + [(e * math.cos(a), 0.2 + 0.65 * math.sin(a)) for a in np.linspace(0.3, math.pi - 0.3, 7)] + [(-e, 0.2)]
    return path(x, y, pts, True), LINE, None, 0.0


def m_ring_round(x, y, rs):
    g = np.full(x.shape, 9.0)
    for k in range(4):
        a = k * TAU / 4.0 + TAU / 8.0
        g = np.minimum(g, np.hypot(x - 0.78 * math.cos(a), y - 0.78 * math.sin(a)))
    return np.abs(np.hypot(x, y) - 0.78), LINE, g, 0.12


def m_ring_tall(x, y, rs):
    e = 0.52
    return path(x, y, [(-e, -0.88), (e, -0.88), (e, 0.25), (0.0, 0.9), (-e, 0.25)], True), LINE * 0.9, None, 0.0


def m_cross(x, y, rs):
    """The bars of a window, piped on its pane: they run right to the cell's edge."""
    return np.minimum(np.abs(x), np.abs(y)), LINE * 0.8, None, 0.0


def m_dot(x, y, rs):
    return np.hypot(x, y), 0.6, None, 0.0


def m_burst(x, y, rs):
    d = np.full(x.shape, 9.0)
    for k in range(8):
        a = k * TAU / 8.0
        d = np.minimum(d, seg(x, y, 0.3 * math.cos(a), 0.3 * math.sin(a), 0.8 * math.cos(a), 0.8 * math.sin(a)))
    return d, LINE * 0.9, np.hypot(x, y), 0.17


def m_curl(x, y, rs):
    pts_a = [(-0.85 + 0.05 * k, 0.25 * math.sin(k * 0.55)) for k in range(35)]
    return path(x, y, pts_a), LINE, np.minimum(np.hypot(x + 0.5, y + 0.55), np.hypot(x - 0.5, y - 0.55)), 0.12


def m_dashes(x, y, rs):
    d = np.full(x.shape, 9.0)
    for k in range(5):
        d = np.minimum(d, seg(x, y, -0.8 + k * 0.4 - 0.1, 0.0, -0.8 + k * 0.4 + 0.1, 0.0))
    return d, LINE, None, 0.0


def sweets(rs):
    """Four round sweets seen from above: a peppermint swirl, a spiral lolly, a chocolate button, a jam biscuit."""
    X, Y = grid()
    r_all = np.zeros((N, N))
    g_all = np.zeros((N, N))
    tone = np.full((N, N), 0.83)
    shine = np.full((N, N), 0.2)
    for k in range(4):
        cx, cy = (k % 2 + 0.5) / 2.0, (k // 2 + 0.5) / 2.0
        x, y = (X - cx) * 4.0, (Y - cy) * 4.0      # -1 .. 1 across the cell
        rho = np.hypot(x, y)
        th = np.arctan2(y, x)
        inside = (np.abs(x) < 1.0) & (np.abs(y) < 1.0)
        gloss = edge(np.hypot(x + 0.34, y - 0.38) - 0.2, 0.3) * 0.16 - 0.1 * np.clip(rho - 0.6, 0.0, 0.4)
        if k == 0:      # peppermint: curved wedges, a thin line between
            wave = np.sin(6.0 * th + 2.2 * rho)
            r = np.clip(wave * 6.0, 0.0, 1.0)
            g = edge(np.abs(np.sin(3.0 * th + 1.1 * rho + 0.8)) - 0.07, 0.08) * (1.0 - r) * (rho > 0.2)
            t, s = 0.83 + gloss, 0.8
        elif k == 1:    # a spiral
            wave = np.sin(th + rho * 11.0)
            r = np.clip(wave * 5.0 + 0.5, 0.0, 1.0)
            g = np.clip((np.sin(th + rho * 11.0 + 2.6) - 0.86) * 12.0, 0.0, 1.0) * (1.0 - r)
            t, s = 0.83 + gloss, 0.85
        elif k == 2:    # a chocolate button: a rim, a piped swirl in its middle
            r = np.clip((np.sin(th * 1.0 + rho * 9.0) - 0.55) * 3.0, 0.0, 1.0) * (rho < 0.55) * 0.5
            g = 0.0 * x
            t = 0.83 + gloss - 0.1 * edge(np.abs(rho - 0.78) - 0.05, 0.1) + 0.08 * r
            s = 0.6
        else:           # a biscuit ring with a jam middle
            g = edge(rho - 0.42, 0.06)
            r = np.zeros_like(x)
            for j in range(10):
                a = j * TAU / 10.0
                r = np.maximum(r, edge(np.hypot(x - 0.7 * math.cos(a), y - 0.7 * math.sin(a)) - 0.07, 0.06))
            t = 0.83 + 0.1 * g * (0.5 + gloss * 3.0) + 0.05 * (fbm(8, 2, rs) - 0.5) * (1.0 - g)
            s = 0.15 + 0.7 * g
        r_all = np.where(inside, r, r_all)
        g_all = np.where(inside, g, g_all)
        tone = np.where(inside, t, tone)
        shine = np.where(inside, s, shine)
    return layer(r_all, g_all, tone, shine)


def stripes(rs):
    """Candy stripes on the slant: a wide one and a thin one beside it. Round a stick they spiral."""
    X, Y = grid()
    t = (X + Y * 2.0) % 1.0
    wide = edge(np.abs(t - 0.3) - 0.17, 0.02)
    thin = edge(np.abs(t - 0.72) - 0.04, 0.02)
    tone = 0.8 + 0.14 * np.sin(math.pi * ((X + 0.2) % 1.0)) ** 6 + 0.02 * (fbm(6, 2, rs) - 0.5)
    return layer(wide, thin, tone, 0.8)


def sugar(rs):
    """A sugared jelly sweet: v from its foot to its top. Paler where the light comes through near the
    foot, crusted with sugar crystals."""
    X, Y = grid()
    tone = 0.72 + 0.2 * (1.0 - Y) ** 1.6 + 0.05 * (fbm(5, 2, rs) - 0.5)
    crystals = rs.random_sample((N, N)) > 0.86
    crystals = (crystals + np.roll(crystals, 1, axis=1) * 0.6 + np.roll(crystals, 1, axis=0) * 0.6).clip(0.0, 1.0)
    spark = rs.random_sample((N, N)) > 0.985
    tone = np.where(spark, 1.0, tone + 0.06 * crystals)
    return layer(crystals * 0.62, 0.0 * X, tone, np.where(spark, 1.0, 0.35 + 0.3 * crystals))


def wafer(rs):
    """A wafer biscuit: a grid of pressed squares."""
    X, Y = grid()
    k = 5.0
    gx, gy = np.abs(wd(X * k)) / k, np.abs(wd(Y * k)) / k
    groove = np.maximum(edge(gx - 0.012, 0.012), edge(gy - 0.012, 0.012))
    pad = 1.0 - groove
    tone = 0.87 - 0.16 * groove + 0.05 * (fbm(6, 3, rs) - 0.5) + 0.03 * pad * (wd(X * k) - wd(Y * k))
    return layer(groove * 0.8, 0.0 * X, tone, 0.12)


def cookie(rs):
    """Left half: the face and piping of a gingerbread person (see PERSON in the builder). Right half: a
    biscuit door with a piped frame, planks, a knob and a little heart."""
    X, Y = grid()
    crumb = 0.83 + 0.09 * (fbm(6, 3, rs) - 0.5) + 0.04 * (rs.random_sample((N, N)) - 0.5)
    # the person: x -0.5 .. 0.5 across the half, y 0 .. 1 up it
    x, y = X * 2.0 - 0.5, Y
    d = np.minimum(np.hypot(x + 0.1, (y - 0.835) * 1.0) - 0.012, np.hypot(x - 0.1, y - 0.835) - 0.012)       # eyes
    smile = np.abs(np.hypot(x, (y - 0.80)) - 0.085)
    d = np.minimum(d, np.where(y < 0.775, smile, 9.0))
    for (cx, cy, turn) in ((-0.36, 0.565, 0.5), (0.36, 0.565, -0.5), (-0.15, 0.1, 0.0), (0.15, 0.1, 0.0)):     # cuffs
        ca, sa = math.cos(turn), math.sin(turn)
        u = (x - cx) * ca + (y - cy) * sa
        v = -(x - cx) * sa + (y - cy) * ca
        zig = np.abs(v - 0.022 * (np.abs((u * 14.0) % 2.0 - 1.0) * 2.0 - 1.0))
        d = np.minimum(d, np.where(np.abs(u) < 0.11, zig, 9.0))
    g = np.full((N, N), 9.0)
    for cy in (0.56, 0.45, 0.34):
        g = np.minimum(g, np.hypot(x, y - cy))
    person_r, high_r = piped(d, 0.017)
    person_g, high_g = piped(g, 0.035)
    # the door: x 0 .. 1 across the half, y 0 .. 1 up it
    x, y = X * 2.0 - 1.0, Y
    e = 0.13
    d = path(x, y, [(e, 0.06), (e, 0.94), (1.0 - e, 0.94), (1.0 - e, 0.06)], True)
    d = np.minimum(d, seg(x, y, 0.38, 0.06, 0.38, 0.94) + 0.006)
    d = np.minimum(d, seg(x, y, 0.62, 0.06, 0.62, 0.94) + 0.006)
    knob = np.hypot((x - 0.76), (y - 0.46) * 2.0)
    xx, yy = (x - 0.5) * 7.0, (y - 0.74) * 14.0 + 0.2
    heart = np.where((xx * xx + yy * yy - 0.62) ** 3 - xx * xx * yy ** 3 < 0.0, -1.0, 1.0)
    door_r, high_d = piped(d, 0.022)
    door_g = np.maximum(edge(knob - 0.06, 0.02), edge(heart, 0.5))
    left = X < 0.5
    r = np.where(left, np.maximum(person_r, person_g), np.maximum(door_r, door_g))
    g2 = np.where(left, person_g, door_g)
    high = np.where(left, np.maximum(high_r, high_g), np.maximum(high_d, door_g))
    tone = np.where(r > 0.3, lit(high, 0.16, False) + 0.05, crumb)
    return layer(r, g2, tone, 0.12 + 0.35 * r)


def tree(rs):
    """Green icing piped with a star nozzle in rows of little peaks; snow on some, a sprinkle here and there."""
    X, Y = grid()
    cols, rows = 5, 6
    high = np.zeros((N, N))
    white = np.zeros((N, N))
    dots = np.full((N, N), 9.0)
    for j in range(rows):
        for i in range(cols):
            cx = (i + 0.5 + (0.5 if j % 2 else 0.0)) / cols + rs.uniform(-0.012, 0.012)
            cy = (j + 0.5) / rows + rs.uniform(-0.01, 0.01)
            dx, dy = wd(X - cx), wd(Y - cy)
            d = np.hypot(dx * 1.0, dy * 1.15)
            peak = np.clip(1.0 - d / 0.115, 0.0, 1.0)
            high = np.maximum(high, peak)
            if rs.random_sample() < 0.3:
                white = np.maximum(white, edge(np.hypot(dx, dy - 0.03) - 0.04, 0.03))
            elif rs.random_sample() < 0.2:
                dots = np.minimum(dots, np.hypot(dx, dy))
    tone = lit(high, 0.3) + 0.04 * (fbm(8, 2, rs) - 0.5) - 0.12 * (1.0 - high) ** 3
    green = edge(dots - 0.027)
    tone = np.where(green > 0.5, 0.9, tone)
    return layer(white * 0.85, green, tone, 0.35 + 0.3 * green)


def parts(rs):
    """Patches (REGION): the snowman's face, the side of a layered sweet, the snowman's buttons, marshmallow."""
    X, Y = grid()
    r = np.zeros((N, N))
    g = np.zeros((N, N))
    tone = 0.84 + 0.04 * (fbm(6, 2, rs) - 0.5) + 0.03 * (rs.random_sample((N, N)) - 0.5)
    shine = np.full((N, N), 0.15)
    # the face: x, y from -1 to 1 over its patch
    x, y = (X - 0.25) * 4.0, (Y - 0.75) * 4.0
    face = (X < 0.5) & (Y >= 0.5)
    d = np.minimum(np.hypot(x + 0.3, y - 0.32), np.hypot(x - 0.3, y - 0.32)) - 0.1
    for k in range(5):
        a = math.pi * (1.2 + 0.15 * k)
        d = np.minimum(d, np.hypot(x - 0.52 * math.cos(a), y - 0.1 - 0.52 * math.sin(a)) - 0.065)
    nose = np.maximum(np.abs(y - 0.02) - 0.13 * (1.0 - (x + 0.05) / 0.6), -(x + 0.05))
    nose = np.maximum(nose, x - 0.55)
    r = np.where(face, edge(d, 0.05), r)
    g = np.where(face, edge(nose, 0.05), g)
    # a layered sweet from the side: base, a band of the print colour, base; a thin line of the accent between
    x, y = (X - 0.5) * 2.0, (Y - 0.5) * 2.0
    side = (X >= 0.5) & (Y >= 0.5)
    r = np.where(side, edge(np.abs(y - 0.5) - 0.17, 0.02), r)
    g = np.where(side, edge(np.abs(np.abs(y - 0.5) - 0.2) - 0.025, 0.02), g)
    tone = np.where(side, 0.83 + 0.03 * (fbm(8, 2, rs) - 0.5), tone)
    shine = np.where(side, 0.45, shine)
    # three buttons down the snowman's front
    x, y = (X - 0.25) * 4.0, (Y - 0.25) * 4.0
    front = (X < 0.5) & (Y < 0.5)
    d = np.minimum(np.hypot(x, y - 0.5), np.minimum(np.hypot(x, y), np.hypot(x, y + 0.5))) - 0.11
    r = np.where(front, edge(d, 0.05), r)
    return layer(r, g, tone, shine)


def foil(rs):
    """The embossed foil of a cake board."""
    X, Y = grid()
    k = 6.0
    a, b = np.abs(wd((X + Y) * k)), np.abs(wd((X - Y) * k))
    tone = 0.74 + 0.22 * np.minimum(a, b) * 2.0 + 0.08 * (fbm(4, 2, rs) - 0.5)
    return layer(np.clip(np.minimum(a, b) * 2.6 - 0.5, 0.0, 1.0), 0.0 * X, tone, 0.85)


def plain(rs):
    X, _Y = grid()
    return layer(0.0 * X, 0.0 * X, 0.83 + 0.0 * X, 0.12 + 0.0 * X)


def paint_all():
    """Every square by name."""
    made = {}
    todo = {"bread": bread, "icing": icing, "snow": snow, "glass": glass, "scallop": scallop, "lattice": lattice, "bands": bands,
            "sweets": sweets, "stripes": stripes, "sugar": sugar, "wafer": wafer, "cookie": cookie, "tree": tree, "parts": parts,
            "foil": foil, "plain": plain, "spare": plain}
    for i, name in enumerate(LAYERS):
        rs = np.random.RandomState(1200 + i * 17)
        if name == "motifs_a":
            made[name] = _cells([m_heart, m_snowflake, m_star, m_swirl, m_holly, m_wreath, m_fir, m_flower, m_drips], rs)
        elif name == "motifs_b":
            made[name] = _cells([m_frame_square, m_frame_arch, m_frame_round, m_door_arch, m_bricks, m_sprinkles, m_hatch, m_bow, m_frame_tall], rs)
        elif name == "motifs_c":
            made[name] = _cells([m_ring_square, m_ring_arch, m_ring_round, m_ring_tall, m_cross, m_dot, m_burst, m_curl, m_dashes], rs)
        else:
            made[name] = todo[name](rs)
    return made


def sheet(layers):
    """The squares side by side, as the game cuts them: the first at the top left."""
    out = np.zeros((N * ROWS, N * COLS, 4))
    for i, name in enumerate(LAYERS):
        col, row = i % COLS, i // COLS
        r0 = (ROWS - 1 - row) * N
        out[r0:r0 + N, col * N:(col + 1) * N] = layers[name]
    return out


def tinted(square, base, printed, accent, cut=False):
    """A square as the shader draws it, for the previews. cut: see-through where there is no piping."""
    r, g, b = square[:, :, 0:1], square[:, :, 1:2], square[:, :, 2:3]
    colour = np.array(base)[None, None, :] * (1.0 - r) + np.array(printed)[None, None, :] * r
    colour = colour * (1.0 - g) + np.array(accent)[None, None, :] * g
    tone = (b * 1.2) ** 2.2
    out = np.ones((square.shape[0], square.shape[1], 4))
    out[:, :, 0:3] = np.clip(colour * tone, 0.0, 1.0)
    if cut:
        out[:, :, 3] = (np.maximum(square[:, :, 0], square[:, :, 1]) > 0.5) * 1.0
    return out


def preview_sheet(layers):
    """Every square in its sample colours (the piping over gingerbread), to look at."""
    out = np.zeros((N * ROWS, N * COLS, 4))
    under = tinted(layers["bread"], *PREVIEW["bread"])
    for i, name in enumerate(LAYERS):
        col, row = i % COLS, i // COLS
        r0 = (ROWS - 1 - row) * N
        one = tinted(layers[name], *PREVIEW[name], cut=name in DECALS)
        if name in DECALS:
            a = one[:, :, 3:4]
            one = one * a + under * (1.0 - a)
            one[:, :, 3] = 1.0
        out[r0:r0 + N, col * N:(col + 1) * N] = one
    return out
