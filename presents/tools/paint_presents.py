# Paints the presents' one picture: sixteen 256-pixel squares in a 4 x 4 sheet (presents_papers.png).
# Used by build_presents.py (which runs in Blender; this file only needs numpy).
#
# No square holds a colour. Each is four masks, and the game's one shader tints them with each present's
# own colours:
#   red    where the printed pattern is (0 the paper's base colour .. 1 the print colour)
#   green  where the second ink is (the accent colour: berries, stars on the trees, thin lines)
#   blue   light and dark: paper grain, the sheen along a ribbon, creases (0.83 is "as it is")
#   alpha  how shiny (0.1 dull paper .. 0.9 foil and satin)
# Squares 0 to 13 tile both ways. Square 14 (the parts) does not: it holds the tag, the sticker and
# the tape, each in its own patch (REGION). Row 0 of every array here is the BOTTOM of the picture.
import math

import numpy as np

N = 256
TAU = math.pi * 2.0
SOFT = 1.3 / N

# the order is the game's Present.Paper enum, then the layers the script uses for the rest
LAYERS = ["stripes", "candy", "dots", "stars", "snow", "holly", "trees", "plaid", "kraft", "foil",
          "satin", "ribbon_foil", "twine", "tissue", "parts", "plain"]

# Where each thing is on the parts square: u0, v0, u1, v1
REGION = {
    "tag": (0.0, 0.5, 0.5, 1.0),
    "seal": (0.5, 0.5, 1.0, 1.0),
    "tape": (0.0, 0.0, 1.0, 0.25),
}

# colours for the previews only (the .blend's materials and the sheet for looking at): base, print, accent
PREVIEW = {
    "stripes": ((0.72, 0.1, 0.1), (0.96, 0.9, 0.78), (0.86, 0.66, 0.22)),
    "candy": ((0.96, 0.92, 0.84), (0.75, 0.1, 0.12), (0.15, 0.42, 0.22)),
    "dots": ((0.13, 0.38, 0.22), (0.96, 0.9, 0.78), (0.8, 0.14, 0.12)),
    "stars": ((0.1, 0.17, 0.4), (0.9, 0.78, 0.36), (0.95, 0.93, 0.86)),
    "snow": ((0.62, 0.78, 0.92), (0.97, 0.97, 0.98), (0.3, 0.45, 0.72)),
    "holly": ((0.96, 0.92, 0.82), (0.14, 0.4, 0.2), (0.8, 0.1, 0.1)),
    "trees": ((0.74, 0.12, 0.11), (0.95, 0.9, 0.78), (0.88, 0.68, 0.22)),
    "plaid": ((0.7, 0.1, 0.1), (0.1, 0.28, 0.16), (0.9, 0.75, 0.3)),
    "kraft": ((0.66, 0.5, 0.34), (0.5, 0.36, 0.22), (0.8, 0.1, 0.1)),
    "foil": ((0.8, 0.6, 0.2), (0.98, 0.9, 0.6), (1.0, 1.0, 1.0)),
    "satin": ((0.82, 0.62, 0.2), (0.62, 0.42, 0.1), (1.0, 1.0, 1.0)),
    "ribbon_foil": ((0.72, 0.74, 0.78), (0.98, 0.98, 1.0), (1.0, 1.0, 1.0)),
    "twine": ((0.9, 0.84, 0.7), (0.78, 0.14, 0.12), (1.0, 1.0, 1.0)),
    "tissue": ((0.95, 0.93, 0.88), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0)),
    "parts": ((0.94, 0.9, 0.8), (0.75, 0.12, 0.12), (0.7, 0.55, 0.25)),
    "plain": ((0.93, 0.91, 0.86), (1.0, 1.0, 1.0), (1.0, 1.0, 1.0)),
}


def _smooth(t):
    return t * t * (3.0 - 2.0 * t)


def pnoise(cells, rs, n=N):
    """Value noise that tiles both ways."""
    grid = rs.random_sample((cells, cells))
    t = np.arange(n) / n * cells
    i0 = np.floor(t).astype(int)
    f = _smooth(t - i0)
    i1 = (i0 + 1) % cells
    i0 %= cells
    fy = f[:, None]
    fx = f[None, :]
    a = grid[i0][:, i0]
    b = grid[i0][:, i1]
    c = grid[i1][:, i0]
    d = grid[i1][:, i1]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


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
    t = np.clip(((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy), 0.0, 1.0)
    return np.hypot(x - ax - t * dx, y - ay - t * dy)


def wobble(rs, amount=0.006):
    """A small wandering push for every pixel, so printed edges are not ruled."""
    return (fbm(4, 2, rs) - 0.5) * 2.0 * amount, (fbm(4, 2, rs) - 0.5) * 2.0 * amount


def ink(rs):
    """How well the ink took: mostly solid, thinner in blotches, a few specks missed."""
    cover = np.clip(0.9 + 0.3 * (fbm(8, 2, rs) - 0.5), 0.0, 1.0)
    missed = (rs.random_sample((N, N)) > 0.988) * 0.45
    return cover * (1.0 - missed)


def grain(rs, amount=1.0):
    """Paper: soft clouds, fine tooth, a few faint fibres."""
    g = 0.83 + amount * (0.08 * (fbm(6, 3, rs) - 0.5) + 0.035 * (rs.random_sample((N, N)) - 0.5))
    fibres = np.clip((pnoise(64, rs) * pnoise(8, rs) - 0.55) * 4.0, 0.0, 1.0)
    return g - 0.05 * amount * fibres


def layer(r, g, b, a):
    out = np.zeros((N, N, 4))
    out[:, :, 0] = np.clip(r, 0.0, 1.0)
    out[:, :, 1] = np.clip(g, 0.0, 1.0)
    out[:, :, 2] = np.clip(b, 0.0, 1.0)
    out[:, :, 3] = np.clip(a, 0.06, 1.0)
    return out


def staggered(cols, rows, rs, jitter=0.01):
    """Centres on a brick-laid grid (rows must be even to tile), each nudged a little."""
    out = []
    for j in range(rows):
        for i in range(cols):
            x = (i + 0.5 + (0.5 if j % 2 else 0.0)) / cols
            y = (j + 0.5) / rows
            out.append((x + rs.uniform(-jitter, jitter), y + rs.uniform(-jitter, jitter)))
    return out


# ------------------------------------------------------------------ the papers
def paint_stripes(rs):
    X, Y = grid()
    dx, _dy = wobble(rs, 0.004)
    t = (X + dx) * 4.0 % 1.0
    r = edge(np.abs(t - 0.25) - 0.25, SOFT * 4.0)
    g = edge(np.abs(t - 0.66) - 0.035, SOFT * 4.0)          # a thin line, a touch out of place
    return layer(r * ink(rs), g * ink(rs), grain(rs), 0.14)


def paint_candy(rs):
    X, Y = grid()
    dx, dy = wobble(rs, 0.004)
    t = (X + dx + Y + dy) * 4.0 % 1.0
    r = edge(np.abs(t - 0.22) - 0.2, SOFT * 5.6)
    g = edge(np.abs(t - 0.62) - 0.04, SOFT * 5.6) + edge(np.abs(t - 0.82) - 0.04, SOFT * 5.6)
    return layer(r * ink(rs), g * ink(rs), grain(rs), 0.16)


def paint_dots(rs):
    X, Y = grid()
    dx, dy = wobble(rs, 0.004)
    r = np.zeros((N, N))
    g = np.zeros((N, N))
    for (cx, cy) in staggered(4, 4, rs, 0.008):
        rad = rs.uniform(0.05, 0.062)
        d = np.hypot(wd(X + dx - cx), wd(Y + dy - cy))
        r = np.maximum(r, edge(d - rad))
        # the second ink landed a little down and right: a crescent shows beside each dot
        g = np.maximum(g, edge(np.hypot(wd(X + dx - cx - 0.014), wd(Y + dy - cy + 0.012)) - rad))
    g = np.clip(g - r, 0.0, 1.0)
    return layer(r * ink(rs), g * ink(rs) * 0.85, grain(rs), 0.14)


def star(x, y, rad, k, rot):
    r = np.hypot(x, y)
    sect = TAU / 5.0
    phi = np.abs((np.arctan2(y, x) - rot + sect / 2.0) % sect - sect / 2.0)
    beta = math.pi / 5.0
    edge_r = rad * k * math.sin(beta) / (np.cos(phi) * k * math.sin(beta) - np.sin(phi) * (k * math.cos(beta) - 1.0))
    return edge(r - edge_r)


def paint_stars(rs):
    X, Y = grid()
    dx, dy = wobble(rs, 0.003)
    r = np.zeros((N, N))
    g = np.zeros((N, N))
    spots = staggered(3, 4, rs, 0.012)
    for n, (cx, cy) in enumerate(spots):
        rad = 0.072 if n % 2 == 0 else 0.05
        r = np.maximum(r, star(wd(X + dx - cx), wd(Y + dy - cy), rad, 0.46, math.pi / 2 + rs.uniform(-0.35, 0.35)))
        # small dots of the second ink in the gaps
        for (ox, oy, rr) in ((0.16, 0.06, 0.011), (-0.15, -0.1, 0.008)):
            g = np.maximum(g, edge(np.hypot(wd(X - cx - ox), wd(Y - cy - oy)) - rr))
    g = np.clip(g - r, 0.0, 1.0)
    return layer(r * ink(rs), g * ink(rs), grain(rs), 0.14)


def flake(x, y, rad, rot, wide):
    r = np.hypot(x, y)
    sect = TAU / 6.0
    phi = np.abs((np.arctan2(y, x) - rot + sect / 2.0) % sect - sect / 2.0)
    px, py = r * np.cos(phi), r * np.sin(phi)
    d = seg(px, py, 0.0, 0.0, rad, 0.0)
    for (at, long) in ((0.45, 0.3), (0.72, 0.2)):
        d = np.minimum(d, seg(px, py, at * rad, 0.0, at * rad + long * rad * 0.5, long * rad * 0.866))
    d = np.minimum(d, r - wide * 0.9)
    return edge(d - wide)


def paint_snow(rs):
    X, Y = grid()
    dx, dy = wobble(rs, 0.002)
    r = np.zeros((N, N))
    g = np.zeros((N, N))
    big = staggered(2, 2, rs, 0.015)
    for (cx, cy) in big:
        r = np.maximum(r, flake(wd(X + dx - cx), wd(Y + dy - cy), 0.115, rs.uniform(0.0, 1.0), 0.0085))
        sx, sy = cx + 0.25 + rs.uniform(-0.02, 0.02), cy + 0.22 + rs.uniform(-0.02, 0.02)
        r = np.maximum(r, flake(wd(X + dx - sx), wd(Y + dy - sy), 0.06, rs.uniform(0.0, 1.0), 0.0065))
    for _n in range(22):
        cx, cy, rr = rs.uniform(0, 1), rs.uniform(0, 1), rs.uniform(0.006, 0.011)
        g = np.maximum(g, edge(np.hypot(wd(X - cx), wd(Y - cy)) - rr))
    g = np.clip(g - r * 2.0, 0.0, 1.0)
    return layer(r * ink(rs), g * ink(rs), grain(rs), 0.14)


def leaf(x, y, ang, long, wide):
    ca, sa = math.cos(ang), math.sin(ang)
    a = x * ca + y * sa
    b = -x * sa + y * ca
    t = np.clip(a / long, 0.0, 1.0)
    points = 1.0 - np.abs(np.sin(math.pi * 3.0 * t))
    w = wide * np.power(np.sin(math.pi * t), 0.6) * (0.55 + 0.45 * points)
    m = edge(np.abs(b) - w) * (a > 0.0) * (a < long)
    rib = edge(np.abs(b) - 0.0035) * (t > 0.1) * (t < 0.86)
    return m * (1.0 - 0.8 * rib)


def paint_holly(rs):
    X, Y = grid()
    dx, dy = wobble(rs, 0.003)
    r = np.zeros((N, N))
    g = np.zeros((N, N))
    for (cx, cy) in staggered(2, 2, rs, 0.02) + [(0.5 + rs.uniform(-0.02, 0.02), 0.0), (0.0, 0.5)]:
        turn = rs.uniform(0.0, TAU)
        x, y = wd(X + dx - cx), wd(Y + dy - cy)
        small = 0.8 if (cx, cy)[1] in (0.0, 0.5) else 1.0
        for k in (-1.0, 1.0):
            r = np.maximum(r, leaf(x, y, turn + k * 0.62, 0.15 * small, 0.04 * small))
        back = turn + math.pi
        for (ob, oa) in ((0.022, 0.0), (0.012, 0.03), (0.012, -0.03)):
            bx = math.cos(back) * ob * small - math.sin(back) * oa * small
            by = math.sin(back) * ob * small + math.cos(back) * oa * small
            g = np.maximum(g, edge(np.hypot(x - bx, y - by) - 0.019 * small))
    r = np.clip(r - g, 0.0, 1.0)
    return layer(r * ink(rs), g * ink(rs), grain(rs), 0.14)


def paint_trees(rs):
    X, Y = grid()
    dx, dy = wobble(rs, 0.003)
    r = np.zeros((N, N))
    g = np.zeros((N, N))
    for (cx, cy) in staggered(3, 2, rs, 0.012):
        x, y = wd(X + dx - cx), wd(Y + dy - cy)
        tall = rs.uniform(0.3, 0.36)
        foot = -tall * 0.5 + 0.045
        tiers = 3
        for k in range(tiers):
            y0 = foot + k * tall * 0.24
            h = tall * 0.42
            half = (0.105 - 0.022 * k) * (1.0 - (y - y0) / h)
            r = np.maximum(r, edge(np.abs(x) - half) * edge(y0 - y) * edge(y - y0 - h))
        g = np.maximum(g, edge(np.abs(x) - 0.014) * edge(foot - 0.045 - y) * edge(y - foot))      # the trunk
        top = foot + 2 * tall * 0.24 + tall * 0.42
        g = np.maximum(g, star(x, y - top - 0.004, 0.036, 0.45, math.pi / 2))
        for (ox, oy) in ((-0.045, foot + 0.035), (0.03, foot + 0.07), (-0.012, foot + 0.15), (0.05, foot + 0.02)):
            g = np.maximum(g, edge(np.hypot(x - ox, y - oy) - 0.0105))
    r = np.clip(r - g, 0.0, 1.0)
    return layer(r * ink(rs), g * ink(rs), grain(rs), 0.14)


def paint_plaid(rs):
    X, Y = grid()
    dx, dy = wobble(rs, 0.002)

    def bands(t):
        t = t % 1.0
        return np.clip(edge(np.abs(t - 0.25) - 0.15, SOFT * 2) + edge(np.abs(t - 0.56) - 0.03, SOFT * 2), 0.0, 1.0)

    def lines(t):
        t = t % 1.0
        return np.clip(edge(np.abs(t - 0.75) - 0.012, SOFT * 2) + edge(np.abs(t - 0.82) - 0.012, SOFT * 2), 0.0, 1.0)

    bx, by = bands((X + dx) * 2.0), bands((Y + dy) * 2.0)
    twill = np.where(((X + Y) * 64.0) % 1.0 < 0.5, 0.64, 0.36)     # where one band shows, the weave lets half through
    r = np.where(bx * by > 0.5, 1.0, np.maximum(bx, by) * twill)
    r = bx * by + (np.maximum(bx, by) - bx * by) * twill
    g = np.maximum(lines((X + dx) * 2.0), lines((Y + dy) * 2.0)) * (0.7 + 0.3 * twill)
    weave = 0.83 + 0.03 * np.sin((X - Y) * TAU * 64.0) + 0.05 * (fbm(6, 3, rs) - 0.5)
    return layer(r * (0.9 + 0.1 * ink(rs)), g, weave, 0.12)


def paint_kraft(rs):
    X, Y = grid()
    laid = 0.5 + 0.5 * np.sin(Y * TAU * 40.0 + 2.0 * (pnoise(4, rs) - 0.5))        # the fine ribs of brown paper
    flecks = np.clip((pnoise(96, rs) * pnoise(24, rs) - 0.4) * 5.0, 0.0, 1.0)
    r = 0.12 * laid + 0.75 * flecks + 0.2 * (fbm(5, 3, rs) - 0.4)
    b = 0.8 + 0.14 * (fbm(5, 4, rs) - 0.5) + 0.05 * (rs.random_sample((N, N)) - 0.5) - 0.03 * laid
    creases = np.clip(1.0 - np.abs(fbm(3, 2, rs) - 0.5) / 0.012, 0.0, 1.0)         # a few soft crease lines
    return layer(r, np.zeros((N, N)), b - 0.07 * creases, 0.1)


def cells(rs, count):
    """A crackle of flat facets that tiles: which random value each pixel's nearest point has, and how near
    the next point is (0 on a facet's edge)."""
    X, Y = grid()
    best = np.full((N, N), 9.0)
    second = np.full((N, N), 9.0)
    value = np.zeros((N, N))
    for _n in range(count):
        cx, cy, v = rs.uniform(0, 1), rs.uniform(0, 1), rs.uniform(0, 1)
        d = np.hypot(wd(X - cx), wd(Y - cy))
        closer = d < best
        second = np.where(closer, best, np.minimum(second, d))
        value = np.where(closer, v, value)
        best = np.where(closer, d, best)
    return value, second - best


def paint_foil(rs):
    value, gap = cells(rs, 46)
    crease = np.clip(1.0 - gap / 0.012, 0.0, 1.0)
    glint = np.clip((value - 0.55) / 0.45, 0.0, 1.0)
    sparkle = (rs.random_sample((N, N)) > 0.992) * 1.0
    r = 0.15 + 0.75 * glint * glint + 0.5 * crease + 0.6 * sparkle
    b = 0.74 + 0.2 * value + 0.04 * (fbm(6, 2, rs) - 0.5)
    return layer(r, np.zeros((N, N)), b, 0.9 - 0.3 * crease)


# ------------------------------------------------------------------ ribbon, string, tissue
def paint_satin(rs):
    """u across the ribbon, v along it."""
    X, Y = grid()
    side = np.minimum(X, 1.0 - X)
    woven = edge(side - 0.1, SOFT * 2)                       # the woven edge, each side
    stitch = 0.5 + 0.5 * np.sin(Y * TAU * 32.0)
    r = woven * (0.55 + 0.45 * stitch) + 0.5 * edge(np.abs(side - 0.135) - 0.008, SOFT * 2)
    sheen = np.exp(-np.square((X - 0.36 + 0.03 * (pnoise(3, rs) - 0.5)) / 0.16))
    ribs = 0.5 + 0.5 * np.sin(Y * TAU * 64.0)
    b = 0.7 + 0.26 * sheen + 0.025 * ribs + 0.04 * (fbm(4, 2, rs) - 0.5) - 0.1 * edge(side - 0.02)
    return layer(r, np.zeros((N, N)), b, 0.8 - 0.4 * woven)


def paint_ribbon_foil(rs):
    X, Y = grid()
    side = np.minimum(X, 1.0 - X)
    value, gap = cells(rs, 30)
    bars = np.clip(0.5 + 0.5 * np.sin(Y * TAU * 3.0 + 6.0 * (fbm(3, 2, rs) - 0.5)), 0.0, 1.0)   # light and dark along it
    streak = np.exp(-np.square((X - 0.4) / 0.12))
    r = 0.12 + 0.55 * streak * bars + 0.3 * np.clip((value - 0.6) / 0.4, 0.0, 1.0) + 0.6 * edge(np.abs(side - 0.07) - 0.012, SOFT * 2)
    b = 0.66 + 0.22 * bars + 0.12 * value - 0.08 * np.clip(1.0 - gap / 0.01, 0.0, 1.0)
    return layer(r, np.zeros((N, N)), b, 0.92)


def paint_twine(rs):
    """u round the string, v along it: two plies twisted, one of them the print colour."""
    X, Y = grid()
    t = (Y * 8.0 + X) % 1.0
    r = edge(np.abs(t - 0.25) - 0.22, SOFT * 6)
    ply = np.abs((t * 2.0) % 1.0 - 0.5) * 2.0                 # dark in the grooves between the plies
    b = 0.62 + 0.3 * (1.0 - ply * ply) + 0.08 * (rs.random_sample((N, N)) - 0.5) + 0.05 * (fbm(8, 2, rs) - 0.5)
    return layer(r, np.zeros((N, N)), b, 0.08)


def paint_tissue(rs):
    value, gap = cells(rs, 26)
    crease = np.clip(1.0 - gap / 0.02, 0.0, 1.0)
    r = 0.25 * crease + 0.3 * np.clip(value - 0.5, 0.0, 1.0)
    b = 0.76 + 0.16 * value + 0.05 * (fbm(5, 3, rs) - 0.5) - 0.1 * crease
    return layer(r, np.zeros((N, N)), b, 0.3)


def paint_plain(rs):
    return layer(np.zeros((N, N)), np.zeros((N, N)), grain(rs, 0.8), 0.14)


def paint_parts(rs):
    X, Y = grid()
    r = np.zeros((N, N))
    g = np.zeros((N, N))
    b = grain(rs, 0.7)
    a = np.full((N, N), 0.14)

    def patch(name):
        u0, v0, u1, v1 = REGION[name]
        inside = (X >= u0) & (X < u1) & (Y >= v0) & (Y < v1)
        return inside, (X - u0) / (u1 - u0), (Y - v0) / (v1 - v0), (u1 - u0) / (v1 - v0)

    # the tag: u along the card from its eyelet end, v across it. A ruled border in the print colour, a
    # ring of card round the eyelet, the eyelet itself in the accent. Blank: nothing is written on it.
    inside, u, v, _wide = patch("tag")
    border = edge(np.abs(np.minimum(np.minimum(u - 0.22, 0.95 - u) * 1.8, np.minimum(v, 1.0 - v)) - 0.11) - 0.014, SOFT * 3)
    border *= (u > 0.2)
    hole = np.hypot((u - 0.105) * 1.8, v - 0.5)
    ring = edge(np.abs(hole - 0.115) - 0.035, SOFT * 3)
    r = np.where(inside, np.clip(border + ring, 0.0, 1.0) * (0.85 + 0.15 * ink(rs)), r)
    g = np.where(inside, edge(hole - 0.07, SOFT * 3), g)
    b = np.where(inside, b + 0.04 - 0.06 * edge(0.03 - np.minimum(v, 1.0 - v), SOFT * 3), b)

    # the sticker: a round seal, a ring of small scallops and a star in the print colour
    inside, u, v, _wide = patch("seal")
    x, y = u - 0.5, v - 0.5
    rad = np.hypot(x, y)
    ang = np.arctan2(y, x)
    scallop = edge(np.abs(rad - 0.36 - 0.02 * np.cos(ang * 16.0)) - 0.022, SOFT * 3)
    mark = star(x, y, 0.2, 0.45, math.pi / 2)
    r = np.where(inside, np.clip(scallop + mark, 0.0, 1.0), r)
    b = np.where(inside, 0.8 + 0.1 * np.exp(-np.square((x + 0.12) / 0.2) - np.square((y - 0.14) / 0.2)), b)
    a = np.where(inside, 0.6, a)

    # the tape: u along the strip. Shiny, streaked along its length, a pinked edge at each end
    inside, u, v, _wide = patch("tape")
    streak = 0.5 + 0.5 * np.sin(v * 23.0 + 3.0 * pnoise(5, rs))
    teeth = edge(np.minimum(u, 1.0 - u) - 0.012 - 0.01 * np.abs(np.sin(v * math.pi * 7.0)), SOFT * 2)
    r = np.where(inside, 0.25 * streak + 0.5 * teeth, r)
    b = np.where(inside, 0.8 + 0.1 * streak - 0.12 * edge(np.minimum(v, 1.0 - v) - 0.05, SOFT * 3), b)
    a = np.where(inside, 0.95, a)
    return layer(r, g, b, a)


PAINTERS = {"stripes": paint_stripes, "candy": paint_candy, "dots": paint_dots, "stars": paint_stars,
            "snow": paint_snow, "holly": paint_holly, "trees": paint_trees, "plaid": paint_plaid,
            "kraft": paint_kraft, "foil": paint_foil, "satin": paint_satin, "ribbon_foil": paint_ribbon_foil,
            "twine": paint_twine, "tissue": paint_tissue, "parts": paint_parts, "plain": paint_plain}


def paint_all():
    """Every square, by name."""
    out = {}
    for n, name in enumerate(LAYERS):
        out[name] = PAINTERS[name](np.random.RandomState(101 + n * 7))
    return out


def sheet(layers):
    """The 4 x 4 sheet the game reads: square 0 top left, then along the rows."""
    big = np.zeros((N * 4, N * 4, 4))
    for n, name in enumerate(LAYERS):
        col, row = n % 4, n // 4
        y0 = (3 - row) * N
        big[y0:y0 + N, col * N:(col + 1) * N, :] = layers[name]
    return big


def tinted(masks, base, ink_colour, accent):
    """A square as the shader draws it, for the previews."""
    base, ink_colour, accent = (np.array(c)[None, None, :] for c in (base, ink_colour, accent))
    colour = base + (ink_colour - base) * masks[:, :, 0:1]
    colour = colour + (accent - colour) * masks[:, :, 1:2]
    out = np.ones(masks.shape)
    out[:, :, :3] = np.clip(colour * masks[:, :, 2:3] * 1.2, 0.0, 1.0)
    return out


def preview_sheet(layers):
    """Every square in a sample of colours, each shown twice across and twice up so its tiling shows."""
    big = np.ones((N * 4, N * 4, 4))
    for n, name in enumerate(LAYERS):
        col, row = n % 4, n // 4
        y0 = (3 - row) * N
        picture = tinted(layers[name], *PREVIEW[name])
        twice = np.tile(picture[::2, ::2, :], (2, 2, 1)) if name != "parts" else picture
        big[y0:y0 + N, col * N:(col + 1) * N, :] = twice
        big[y0:y0 + 2, col * N:(col + 1) * N, :3] = 0.0
        big[y0:y0 + N, col * N:col * N + 2, :3] = 0.0
    return big
