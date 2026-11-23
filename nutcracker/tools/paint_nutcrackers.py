# Paints the nutcrackers' two pictures (1024 x 1024 each). Used by build_nutcrackers.py, which runs in
# Blender; this file only needs numpy.
#
#   nutcracker_paint.png   what is painted in a colour of its own, whatever the uniform: faces (eyes, brows,
#                          cheeks, teeth), black boots and belts, bare turned wood, linen, ermine, steel, the
#                          walnut. Its alpha is how much it covers the uniform's colour (0: none of it).
#   nutcracker_masks.png   red    where the TRIM colour is painted over the part's own colour (braid, buttons)
#                          green  light and dark: brush marks, fur strands, outlines (0.75 is "as it is")
#                          blue   how glossy (enamel 0.75, fur and linen near 0)
#                          alpha  a field of blotches that tiles over the whole picture: where paint has
#                                 chipped off, by each figure's `wear` (the game reads it at a shifted place)
#
# Neither picture holds a uniform's colour. Each part of a model says which colour it wears (coat, trousers,
# hat, trim, hair, skin) and the game's one shader does
#   mix(mix(that colour, trim, masks.red), paint.rgb, paint.alpha) * masks.green / 0.75
#
# The pictures are an atlas of patches (REGIONS). A patch is painted a few pixels past its edges so
# nothing bleeds in when it is drawn small. Row 0 of every array here is the BOTTOM of the picture.
import math

import numpy as np

SIZE = 1024
PAD = 5
INK = (0.07, 0.05, 0.05)
WOOD = (0.66, 0.47, 0.28)

# The face patch is laid over the front half of the head (180 degrees), from the chin to the hat line.
# The mouth is a slot cut in the head for the jaw, this far up the patch and this wide.
MOUTH_V = 0.37
MOUTH_HALF_DEG = 45.0

KINDS = ["soldier", "king", "drummer", "guard", "baker"]

# name, width, height in pixels
REGIONS = [
    ("face_soldier", 224, 152), ("face_king", 224, 152), ("face_drummer", 224, 152), ("face_guard", 224, 152),
    ("face_baker", 224, 152), ("jaw_front", 168, 72), ("jaw_top", 96, 48), ("mouth", 40, 40),
    ("crown", 64, 64), ("hand", 48, 48), ("plain", 64, 64), ("leather", 40, 40), ("metal", 32, 96),
    ("torso_soldier", 196, 168), ("torso_king", 196, 168), ("torso_drummer", 196, 168),
    ("torso_guard", 196, 168), ("torso_baker", 196, 168),
    ("back", 128, 128), ("shako", 160, 140), ("kepi", 128, 72), ("fur", 128, 192), ("linen", 96, 128),
    ("leg", 64, 128), ("sleeve", 96, 128), ("boot", 64, 96), ("epaulette", 64, 64),
    ("wood_side", 256, 48), ("wood_top", 96, 96), ("drum_side", 192, 64), ("drum_head", 64, 64),
    ("ermine", 96, 48), ("walnut", 128, 96), ("kernel", 64, 64), ("shell_in", 32, 32),
]


def _pack():
    rect = {}
    x = y = PAD
    tall = 0
    for name, w, h in REGIONS:
        if x + w + PAD > SIZE:
            x = PAD
            y += tall + 2 * PAD
            tall = 0
        rect[name] = (x, y, w, h)
        x += w + 2 * PAD
        tall = max(tall, h)
    if y + tall + PAD > SIZE:
        raise SystemExit("the patches do not fit the picture")
    return rect


RECT = _pack()


def region(name):
    """A patch as u0, v0, u1, v1 in the picture."""
    x, y, w, h = RECT[name]
    return (x / SIZE, y / SIZE, (x + w) / SIZE, (y + h) / SIZE)


def vnoise(rs, shape, cx, cy, tile=False):
    h, w = shape
    cx = max(int(cx), 1)
    cy = max(int(cy), 1)
    g = rs.rand(cy, cx) if tile else rs.rand(cy + 1, cx + 1)
    ys = np.arange(h) * (cy / h)
    xs = np.arange(w) * (cx / w)
    yi = ys.astype(int)
    xi = xs.astype(int)
    fy = ys - yi
    fx = xs - xi
    fy = fy * fy * (3 - 2 * fy)
    fx = fx * fx * (3 - 2 * fx)
    y1 = (yi + 1) % cy if tile else yi + 1
    x1 = (xi + 1) % cx if tile else xi + 1
    a = g[yi][:, xi]
    b = g[yi][:, x1]
    c = g[y1][:, xi]
    d = g[y1][:, x1]
    return (a * (1 - fx) + b * fx) * (1 - fy)[:, None] + (c * (1 - fx) + d * fx) * fy[:, None]


class Patch:
    """One patch being painted. X runs across it in units of its height (0 in the middle), Y from 0 at
    its bottom to 1 at its top; U from 0 to 1 across. Lengths given to the shapes are in those units."""

    def __init__(self, name, marks="across"):
        x, y, w, h = RECT[name]
        self.name = name
        self.w, self.h = w, h
        self.asp = w / h
        us = (np.arange(-PAD, w + PAD) + 0.5) / w
        vs = (np.arange(-PAD, h + PAD) + 0.5) / h
        self.U, self.Y = np.meshgrid(us, vs)
        self.X = (self.U - 0.5) * self.asp
        self.soft = 1.1 / h
        self.rs = np.random.RandomState(abs(hash(name)) % 100000 if False else sum(ord(c) * (i + 3) for i, c in enumerate(name)))
        shape = self.U.shape
        self.over = np.zeros(shape + (3,))
        self.cover = np.zeros(shape)
        self.trim = np.zeros(shape)
        self.gloss = np.full(shape, 0.75)
        # brush marks: long soft streaks the way the brush went, and broad uneven patches
        if marks == "across":
            streak = vnoise(self.rs, shape, 3, h // 3) + 0.5 * vnoise(self.rs, shape, 6, h // 2)
        elif marks == "along":
            streak = vnoise(self.rs, shape, w // 3, 3) + 0.5 * vnoise(self.rs, shape, w // 2, 6)
        else:
            streak = vnoise(self.rs, shape, 8, 8) * 1.5
        self.shade = 0.75 + (streak / 1.5 - 0.5) * 0.11 + (vnoise(self.rs, shape, 2, 2) - 0.5) * 0.06

    # ---- shapes: distances, under 0 inside
    def disc(self, cx, cy, r):
        return np.hypot(self.X - cx, self.Y - cy) - r

    def ell(self, cx, cy, rx, ry):
        return (np.hypot((self.X - cx) / rx, (self.Y - cy) / ry) - 1.0) * min(rx, ry)

    def seg(self, ax, ay, bx, by, r):
        px, py = self.X - ax, self.Y - ay
        dx, dy = bx - ax, by - ay
        t = np.clip((px * dx + py * dy) / max(dx * dx + dy * dy, 1e-9), 0.0, 1.0)
        return np.hypot(px - dx * t, py - dy * t) - r

    def box(self, cx, cy, hx, hy, r=0.0):
        qx = np.abs(self.X - cx) - hx + r
        qy = np.abs(self.Y - cy) - hy + r
        return np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - r

    def line(self, pts, r):
        d = np.full(self.U.shape, 9.0)
        for a, b in zip(pts[:-1], pts[1:]):
            d = np.minimum(d, self.seg(a[0], a[1], b[0], b[1], r))
        return d

    def m(self, d, soft=None):
        return np.clip(0.5 - d / (soft or self.soft), 0.0, 1.0)

    # ---- paint
    def ink(self, mask, rgb, amount=1.0):
        """Paint in a colour of its own, over whatever is there."""
        k = np.clip(mask * amount, 0.0, 1.0)
        out = k + self.cover * (1 - k)
        safe = np.maximum(out, 1e-6)
        for i in range(3):
            self.over[..., i] = (rgb[i] * k + self.over[..., i] * self.cover * (1 - k)) / safe
        self.cover = out
        self.trim *= 1 - k

    def tr(self, mask, amount=1.0):
        """Paint in the trim colour."""
        k = np.clip(mask * amount, 0.0, 1.0)
        self.trim = self.trim * (1 - k) + k
        self.cover *= 1 - k

    def dark(self, mask, amount):
        self.shade *= 1 - np.clip(mask, 0, 1) * amount

    def light(self, mask, amount):
        self.shade += np.clip(mask, 0, 1) * amount

    def matt(self, mask, to=0.1):
        k = np.clip(mask, 0, 1)
        self.gloss = self.gloss * (1 - k) + to * k

    def button(self, x, y, r, own=None):
        """A painted button in the trim colour (or one of its own), ringed, with a dab of light."""
        d = self.disc(x, y, r)
        if own is None:
            self.tr(self.m(d))
        else:
            self.ink(self.m(d), own)
        self.dark(self.m(np.abs(d) - 0.011), 0.5)
        self.light(self.m(self.disc(x - r * 0.3, y + r * 0.32, r * 0.3)), 0.3)

    def outline(self, d, wide=0.012, amount=0.55):
        self.dark(self.m(np.abs(d) - wide), amount)


# ------------------------------------------------------------------ faces
WHITE = (0.96, 0.95, 0.91)
FACES = {
    #            eye w, h    iris  iris colour         brow: inner y, outer y, thick, colour
    "soldier": dict(ew=0.074, eh=0.098, iris=0.054, col=(0.16, 0.3, 0.55), bi=0.105, bo=0.175, bt=0.03, bc=INK,
                    cheek=0.6),
    "king": dict(ew=0.068, eh=0.084, iris=0.05, col=(0.3, 0.2, 0.1), bi=0.15, bo=0.13, bt=0.042,
                 bc=(0.93, 0.92, 0.88), cheek=0.7),
    "drummer": dict(ew=0.082, eh=0.108, iris=0.06, col=(0.2, 0.42, 0.25), bi=0.17, bo=0.19, bt=0.022, bc=(0.3, 0.16, 0.08),
                    cheek=0.75),
    "guard": dict(ew=0.074, eh=0.078, iris=0.05, col=(0.1, 0.1, 0.12), bi=0.085, bo=0.165, bt=0.036, bc=INK,
                  cheek=0.45),
    "baker": dict(ew=0.07, eh=0.09, iris=0.054, col=(0.32, 0.2, 0.1), bi=0.16, bo=0.145, bt=0.026, bc=(0.35, 0.22, 0.12),
                  cheek=0.95),
}


def paint_face(kind):
    p = Patch("face_" + kind)
    f = FACES[kind]
    X, Y = p.X, p.Y
    for sx in (-1, 1):
        d = np.hypot(X - sx * 0.33, (Y - 0.5) / 0.85)
        p.ink(np.exp(-(d / 0.1) ** 2) * min(f["cheek"] * 1.25, 1.0), (0.88, 0.2, 0.18))
    if kind == "drummer":   # freckles
        for i in range(14):
            fx = (p.rs.rand() * 2 - 1) * 0.36
            fy = 0.5 + (p.rs.rand() - 0.5) * 0.12
            if abs(fx) > 0.12:
                p.ink(p.m(p.disc(fx, fy, 0.008)), (0.6, 0.3, 0.16), 0.7)
    if kind == "king":      # crow's feet and a line across the brow
        for sx in (-1, 1):
            for k in (-1, 0, 1):
                p.dark(p.m(p.seg(sx * 0.29, 0.66 + k * 0.012, sx * 0.35, 0.665 + k * 0.035, 0.004)), 0.3)
        p.dark(p.m(p.seg(-0.16, 0.9, 0.16, 0.9, 0.004)), 0.25)
    if kind == "guard":     # the bearskin's chin strap down each cheek
        strap = np.abs(np.abs(X) - 0.5) - 0.024
        p.tr(p.m(strap))
        p.outline(strap, 0.008, 0.5)
        p.dark(p.m(np.abs(np.abs(X) - 0.5) - 0.02) * (np.sin(Y * 60.0) > 0.55), 0.25)
    for sx in (-1, 1):
        cx, cy = sx * 0.2, 0.68
        dw = p.ell(cx, cy, f["ew"], f["eh"])
        p.ink(p.m(dw - 0.013), INK)
        p.ink(p.m(dw), WHITE)
        inside = p.m(dw + 0.003)
        ix = cx - sx * 0.006
        iy = cy - 0.012
        p.ink(p.m(p.disc(ix, iy, f["iris"])) * inside, f["col"])
        p.ink(p.m(p.disc(ix, iy, f["iris"] * 0.52)) * inside, INK)
        p.ink(p.m(p.disc(ix - 0.016, iy + 0.02, 0.012)), (1, 1, 1))
        # a heavy upper lid
        p.ink(p.m(np.abs(dw) - 0.017) * (Y > cy + f["eh"] * 0.25), INK)
        # the brow, inner end to outer end
        ax, ay = cx - sx * 0.085, cy + f["bi"]
        bx, by = cx + sx * 0.1, cy + f["bo"]
        if kind in ("baker", "drummer"):   # arched
            mx, my = cx, cy + max(f["bi"], f["bo"]) + 0.035
            brow = p.line([(ax, ay), (mx, my), (bx, by)], f["bt"])
        else:
            brow = p.seg(ax, ay, bx, by, f["bt"])
        if kind == "king":
            p.ink(p.m(brow - 0.008), (0.45, 0.42, 0.4), 0.6)
        p.ink(p.m(brow), f["bc"])
    # the open mouth under them (the full model cuts a slot here; the low one only has this paint)
    p.ink(p.m(p.box(0.0, MOUTH_V * 0.5 - 0.05, MOUTH_HALF_DEG / 180.0 * p.asp, MOUTH_V * 0.5 + 0.05, 0.0)), (0.2, 0.03, 0.04))
    # the top row of teeth, a red lip round them
    half = MOUTH_HALF_DEG / 180.0 * p.asp - 0.03
    teeth = p.box(0.0, MOUTH_V + 0.034, half, 0.038, 0.012)
    p.ink(p.m(teeth - 0.016), (0.62, 0.08, 0.08))
    p.ink(p.m(teeth), WHITE)
    pitch = half * 2 / 7.0
    gap = np.abs((X / pitch + 0.5) % 1.0 - 0.5) * pitch
    p.ink(p.m(gap - 0.005) * p.m(teeth + 0.004), (0.35, 0.3, 0.3))
    p.dark(p.m(teeth) * np.clip((Y - MOUTH_V - 0.035) / 0.04, 0, 1), 0.12)
    return p


def paint_jaw_front():
    """The front of the jaw, round its curve: the bottom row of teeth along its top, a red lip, the chin."""
    p = Patch("jaw_front")
    X, Y = p.X, p.Y
    half = p.asp * 0.5 - 0.09
    teeth = p.box(0.0, 0.86, half, 0.11, 0.03)
    p.ink(p.m(teeth - 0.045), (0.62, 0.08, 0.08))
    p.ink(p.m(teeth), WHITE)
    pitch = half * 2 / 7.0
    gap = np.abs((X / pitch + 0.5) % 1.0 - 0.5) * pitch
    p.ink(p.m(gap - 0.014) * p.m(teeth + 0.01), (0.35, 0.3, 0.3))
    p.dark(p.m(p.seg(-0.22, 0.42, 0.22, 0.42, 0.012)) * 0.5, 0.25)
    return p


def paint_jaw_top():
    p = Patch("jaw_top", "blotch")
    p.ink(np.ones_like(p.X), (0.3, 0.05, 0.06))
    p.ink(p.m(p.ell(0.0, 0.45, 0.55, 0.3), 0.08), (0.75, 0.3, 0.32))
    p.dark(p.m(p.seg(0.0, 0.3, 0.0, 0.7, 0.012)), 0.3)
    p.gloss[:] = 0.6
    return p


def paint_mouth():
    p = Patch("mouth", "blotch")
    p.ink(np.ones_like(p.X), (0.2, 0.03, 0.04))
    p.shade *= 0.55 + 0.45 * np.clip(p.Y, 0, 1)
    p.gloss[:] = 0.2
    return p


# ------------------------------------------------------------------ coats
def paint_torso(kind):
    """The front half of the chest, belt (bottom) to shoulders (top)."""
    p = Patch("torso_" + kind)
    X, Y = p.X, p.Y
    if kind == "soldier":
        for i in range(4):
            y = 0.17 + 0.2 * i
            long = 0.17 + 0.035 * i
            bar = p.seg(-long, y, long, y, 0.02)
            p.tr(p.m(bar))
            p.outline(bar, 0.008, 0.4)
            for sx in (-1, 0, 1):
                p.button(sx * long, y, 0.042 if sx else 0.036)
    elif kind == "king":
        panel = np.abs(X) - 0.15
        p.ink(p.m(panel), (0.95, 0.94, 0.9))
        p.matt(p.m(panel), 0.15)
        for row in range(7):
            for col in (-1, 0, 1):
                tx = col * 0.085 + (0.042 if row % 2 else 0.0)
                ty = 0.08 + row * 0.14
                if abs(tx) < 0.12:
                    p.ink(p.m(p.seg(tx, ty + 0.028, tx, ty - 0.02, 0.011)), INK)
        edge = np.abs(np.abs(X) - 0.172) - 0.02
        p.tr(p.m(edge))
        p.outline(edge, 0.007, 0.45)
        chain = [(x, 0.5 + 0.48 * (x / 0.42) ** 2) for x in np.linspace(-0.42, 0.42, 15)]
        links = p.line(chain, 0.02)
        p.tr(p.m(links))
        p.outline(links, 0.007, 0.5)
        p.dark(p.m(links) * (np.sin(X * 90.0) > 0.3), 0.2)
        p.button(0.0, 0.43, 0.085)
        p.button(0.0, 0.43, 0.045, own=(0.7, 0.05, 0.1))
    elif kind == "drummer":
        bib = np.maximum(np.abs(X) - (0.17 + 0.12 * Y), np.abs(Y - 0.5) - 0.44)
        p.ink(p.m(bib), (0.94, 0.93, 0.89))
        edge = np.abs(bib) - 0.016
        p.tr(p.m(edge))
        p.outline(bib - 0.016, 0.006, 0.4)
        for i in range(4):
            y = 0.16 + 0.225 * i
            for sx in (-1, 1):
                p.button(sx * (0.1 + 0.12 * y), y, 0.036)
    elif kind == "guard":
        for sx in (-1, 1):
            band = p.seg(-sx * 0.46, 1.05, sx * 0.4, -0.05, 0.045)
            p.ink(p.m(band - 0.012), (0.4, 0.38, 0.36))
            p.ink(p.m(band), (0.95, 0.94, 0.9))
        for y in (0.12, 0.28, 0.76, 0.92):
            p.button(0.0, y, 0.036)
        plate = p.box(0.0, 0.52, 0.07, 0.085, 0.03)
        p.tr(p.m(plate))
        p.outline(plate, 0.011, 0.55)
        p.dark(p.m(np.abs(p.disc(0.0, 0.52, 0.035)) - 0.008), 0.45)
    elif kind == "baker":
        for y in (0.3, 0.56):
            for sx in (-1, 1):
                p.button(sx * 0.37, y, 0.038)
        for sx in (-1, 1):
            strap = p.seg(sx * 0.2, 0.68, sx * 0.4, 1.05, 0.026)
            p.ink(p.m(strap - 0.01), (0.55, 0.53, 0.5))
            p.ink(p.m(strap), (0.94, 0.92, 0.87))
        bib = p.box(0.0, 0.3, 0.27, 0.44, 0.05)
        p.ink(p.m(bib - 0.012), (0.55, 0.53, 0.5))
        p.ink(p.m(bib), (0.94, 0.92, 0.87))
        p.matt(p.m(bib), 0.12)
        folds = vnoise(p.rs, p.X.shape, 9, 2)
        p.dark(p.m(bib) * np.clip((folds - 0.55) * 4, 0, 1), 0.1)
        pocket = p.box(0.0, 0.27, 0.13, 0.1, 0.02)
        p.dark(p.m(np.abs(pocket) - 0.006), 0.4)
        p.dark(p.m(p.seg(-0.13, 0.37, 0.13, 0.37, 0.004)), 0.3)
        tie = np.maximum(np.abs(X) - (Y - 0.76) * 0.95, 0.76 - Y)
        p.tr(p.m(tie))
        p.outline(tie, 0.008, 0.45)
        p.button(0.0, 0.8, 0.04)
    return p


def paint_back():
    """The back half of a coat: a seam down the middle, two buttons at the waist."""
    p = Patch("back")
    p.dark(p.m(np.abs(p.X) - 0.006) * (p.Y < 0.72), 0.35)
    for sx in (-1, 1):
        p.button(sx * 0.1, 0.1, 0.04)
    return p


# ------------------------------------------------------------------ hats
def paint_shako():
    p = Patch("shako")
    X, Y = p.X, p.Y
    for k in (0.0, 0.07):
        cord = [(x, 0.93 - k - (0.3 - k) * (1 - (x / 0.56) ** 2)) for x in np.linspace(-0.56, 0.56, 17)]
        d = p.line(cord, 0.014)
        p.tr(p.m(d))
        p.dark(p.m(d) * (np.sin(X * 110.0) > 0.2), 0.25)
        p.outline(d, 0.006, 0.4)
    ang = np.arctan2(Y - 0.42, X)
    rad = np.hypot(X, Y - 0.42)
    star = rad - 0.17 * (1.0 + 0.28 * np.cos(ang * 8.0))
    p.tr(p.m(star))
    p.outline(star, 0.009, 0.5)
    p.dark(p.m(np.abs(p.disc(0.0, 0.42, 0.075)) - 0.008), 0.45)
    p.light(p.m(p.disc(-0.02, 0.44, 0.025)), 0.25)
    return p


def paint_kepi():
    p = Patch("kepi")
    d = p.disc(0.0, 0.5, 0.26)
    p.tr(p.m(d))
    p.outline(d, 0.02, 0.5)
    p.dark(p.m(np.abs(p.disc(0.0, 0.5, 0.13)) - 0.016), 0.4)
    p.light(p.m(p.disc(-0.07, 0.6, 0.05)), 0.25)
    return p


def paint_crown():
    """One sixth of the crown's band (it wears the trim colour): a jewel, half a pearl at each edge."""
    p = Patch("crown")
    gem = p.ell(0.0, 0.5, 0.2, 0.27)
    p.ink(p.m(gem), (0.72, 0.05, 0.1))
    p.outline(gem, 0.025, 0.6)
    p.ink(p.m(p.disc(-0.06, 0.6, 0.045)), (1.0, 0.8, 0.8), 0.9)
    for sx in (-1, 1):
        pearl = p.disc(sx * 0.5, 0.5, 0.1)
        p.ink(p.m(pearl), (0.95, 0.94, 0.9))
        p.outline(pearl, 0.02, 0.5)
    for y in (0.08, 0.92):
        p.dark(p.m(np.abs(p.Y - y) - 0.02), 0.35)
    return p


# ------------------------------------------------------------------ the rest
def paint_plain():
    return Patch("plain")


def paint_hand():
    p = Patch("hand")
    for k in (-1, 0, 1):
        p.dark(p.m(p.seg(k * 0.16, 0.0, k * 0.16, 0.34, 0.012)), 0.35)
    return p


def paint_leather():
    p = Patch("leather")
    p.ink(np.ones_like(p.X), (0.05, 0.045, 0.05))
    p.shade += 0.1 * np.exp(-((p.Y - 0.6) / 0.15) ** 2)
    p.gloss[:] = 0.85
    return p


def paint_metal():
    """Steel, along a blade: bright down the middle, dark at the edges."""
    p = Patch("metal", "along")
    p.ink(np.ones_like(p.X), (0.72, 0.75, 0.8))
    p.shade *= 0.8 + 0.3 * np.exp(-((p.U - 0.42) / 0.12) ** 2)
    p.dark(p.m(np.abs(p.U - 0.5) - 0.02, 0.05), 0.2)
    p.gloss[:] = 0.95
    return p


def paint_fur():
    """Strands running up the patch (v: root at the bottom, tip at the top), in locks with dark between."""
    p = Patch("fur", "blotch")
    shape = p.X.shape
    fine = vnoise(p.rs, shape, p.w // 2, 5)
    lock = vnoise(p.rs, shape, 9, 3)
    wisp = vnoise(p.rs, shape, p.w // 5, 9)
    p.shade = 0.58 + 0.17 * fine + 0.14 * wisp + 0.1 * lock
    p.shade *= 1.0 - 0.5 * np.clip((0.36 - lock) * 5.0, 0, 1) * np.clip(wisp * 1.6, 0, 1)
    p.shade *= 0.82 + 0.22 * np.clip(p.Y, 0, 1)
    p.gloss[:] = 0.06
    return p


def paint_linen():
    """White cloth in upright pleats (the baker's hat)."""
    p = Patch("linen", "blotch")
    p.ink(np.ones_like(p.X), (0.94, 0.93, 0.88))
    pleat = np.abs((p.U * 4.0) % 1.0 - 0.5) * 2.0
    p.shade = 0.75 * (0.84 + 0.2 * pleat ** 0.7) + (vnoise(p.rs, p.X.shape, 20, 20) - 0.5) * 0.04
    p.gloss[:] = 0.08
    return p


def paint_leg():
    """A trouser leg: a stripe in the trim colour down its outer side (the middle of the patch)."""
    p = Patch("leg")
    stripe = np.abs(p.X) - 0.035
    p.tr(p.m(stripe))
    p.outline(stripe, 0.006, 0.35)
    return p


def paint_sleeve():
    """A sleeve, shoulder at the top: a cuff in the trim colour, two buttons above it on the outer side."""
    p = Patch("sleeve")
    cuff = p.Y - 0.2
    p.tr(p.m(cuff))
    p.dark(p.m(np.abs(cuff) - 0.008), 0.5)
    p.dark(p.m(np.abs(p.Y - 0.06) - 0.006), 0.3)
    for y in (0.29, 0.4):
        p.button(0.0, y, 0.035)
    return p


def paint_boot():
    """A black boot: a long soft shine down it, the sole at the bottom."""
    p = Patch("boot")
    p.ink(np.ones_like(p.X), (0.05, 0.045, 0.05))
    p.shade += 0.14 * np.exp(-((p.U - 0.38) / 0.07) ** 2) * np.clip(p.Y * 1.3, 0, 1)
    p.gloss[:] = 0.9
    return p


def paint_epaulette():
    """An epaulette from its middle (bottom of the patch) out and down its fringe (top)."""
    p = Patch("epaulette", "blotch")
    fringe = (np.sin(p.U * math.pi * 2 * 14) > 0.0) * np.clip((p.Y - 0.5) * 8, 0, 1)
    p.dark(fringe, 0.3)
    p.dark(p.m(np.abs(p.Y - 0.5) - 0.02), 0.45)
    p.dark(p.m(np.abs(p.Y - 0.26) - 0.012), 0.3)
    return p


def paint_wood_side():
    """Bare turned wood, round a plinth: the tool's fine rings, grain showing through as long streaks."""
    p = Patch("wood_side", "blotch")
    shape = p.X.shape
    p.ink(np.ones_like(p.X), WOOD)
    grain = vnoise(p.rs, shape, 5, p.h // 2) * 0.6 + vnoise(p.rs, shape, 10, p.h) * 0.4
    p.shade = 0.75 * (0.8 + 0.42 * grain)
    p.shade *= 1.0 - 0.18 * (vnoise(p.rs, shape, 40, 3) > 0.74)
    p.gloss[:] = 0.4
    return p


def paint_wood_top():
    """Bare turned wood from above: rings round its middle."""
    p = Patch("wood_top", "blotch")
    p.ink(np.ones_like(p.X), WOOD)
    rad = np.hypot(p.X, p.Y - 0.5)
    wob = rad + 0.012 * vnoise(p.rs, p.X.shape, 5, 5)
    p.shade = 0.75 * (0.86 + 0.22 * (0.5 + 0.5 * np.sin(wob * 150.0)) * (0.5 + 0.5 * np.sin(wob * 43.0)))
    p.shade += (vnoise(p.rs, p.X.shape, 6, 6) - 0.5) * 0.08
    p.gloss[:] = 0.4
    return p


def paint_drum_side():
    """Half way round the drum: its shell in the coat colour, white cords zigzagging, a stud at each turn."""
    p = Patch("drum_side")
    n = 4
    zig = np.abs((p.U * n) % 1.0 - 0.5) * 2.0
    d = np.abs(p.Y - (0.14 + 0.72 * zig)) / math.hypot(1.0, 0.72 * 2 * n / p.asp) - 0.03
    p.ink(p.m(d - 0.02), (0.3, 0.28, 0.26), 0.7)
    p.ink(p.m(d), (0.95, 0.94, 0.9))
    for i in range(n + 1):
        p.button((i / n - 0.5) * p.asp, 0.86, 0.06)
        p.button(((i + 0.5) / n - 0.5) * p.asp, 0.14, 0.06)
    return p


def paint_drum_head():
    p = Patch("drum_head", "blotch")
    p.ink(np.ones_like(p.X), (0.9, 0.85, 0.72))
    rad = np.hypot(p.X, p.Y - 0.5)
    p.shade *= 1.0 - 0.14 * np.exp(-(rad / 0.16) ** 2) - 0.25 * np.clip((rad - 0.4) * 8, 0, 1)
    p.gloss[:] = 0.25
    return p


def paint_ermine():
    """White fur with black tails, round a hem or a crown's brim. Tiles across."""
    p = Patch("ermine", "blotch")
    p.ink(np.ones_like(p.X), (0.95, 0.94, 0.9))
    p.shade = 0.75 * (0.86 + 0.2 * vnoise(p.rs, p.X.shape, p.w // 2, 6))
    for i in range(4):
        tx = ((i + 0.5) / 4.0 - 0.5) * p.asp
        ty = 0.62 if i % 2 else 0.4
        p.ink(p.m(p.seg(tx, ty + 0.13, tx, ty - 0.1, 0.045)), INK)
    p.gloss[:] = 0.08
    return p


def paint_walnut():
    """A walnut's shell: furrows wandering over it, the seam where the halves meet along the middle."""
    p = Patch("walnut", "blotch")
    shape = p.X.shape
    p.ink(np.ones_like(p.X), (0.56, 0.37, 0.19))
    a = vnoise(p.rs, shape, 7, 6, tile=True)
    b = vnoise(p.rs, shape, 14, 11, tile=True)
    furrow = np.minimum(np.abs(a - 0.5) * 2.0, np.abs(b - 0.5) * 2.0 + 0.1)
    p.shade = 0.75 * (0.6 + 0.55 * np.clip(furrow * 3.2, 0, 1))
    p.shade += 0.08 * np.exp(-((p.Y - 0.5) / 0.03) ** 2)
    p.gloss[:] = 0.3
    return p


def paint_kernel():
    """The nut inside a cracked half: pale lobes, the dark shell round its edge."""
    p = Patch("kernel", "blotch")
    p.ink(np.ones_like(p.X), (0.36, 0.23, 0.12))
    rad = np.hypot(p.X, p.Y - 0.5)
    ang = np.arctan2(p.Y - 0.5, p.X)
    lobes = rad - 0.36 * (1.0 + 0.1 * np.cos(ang * 4.0) + 0.05 * np.cos(ang * 9.0))
    p.ink(p.m(lobes), (0.84, 0.7, 0.46))
    p.dark(p.m(np.abs(p.X) - 0.02) * p.m(lobes), 0.35)
    p.dark(p.m(np.abs(p.Y - 0.5) - 0.012) * p.m(lobes), 0.25)
    p.dark(p.m(lobes) * (vnoise(p.rs, p.X.shape, 9, 9) > 0.62), 0.14)
    p.gloss[:] = 0.2
    return p


def paint_shell_in():
    p = Patch("shell_in", "blotch")
    p.ink(np.ones_like(p.X), (0.4, 0.26, 0.14))
    p.gloss[:] = 0.15
    return p


PAINTERS = {
    "jaw_front": paint_jaw_front, "jaw_top": paint_jaw_top, "mouth": paint_mouth, "crown": paint_crown,
    "hand": paint_hand, "plain": paint_plain, "leather": paint_leather, "metal": paint_metal, "back": paint_back,
    "shako": paint_shako, "kepi": paint_kepi, "fur": paint_fur, "linen": paint_linen, "leg": paint_leg,
    "sleeve": paint_sleeve, "boot": paint_boot, "epaulette": paint_epaulette, "wood_side": paint_wood_side,
    "wood_top": paint_wood_top, "drum_side": paint_drum_side, "drum_head": paint_drum_head,
    "ermine": paint_ermine, "walnut": paint_walnut, "kernel": paint_kernel, "shell_in": paint_shell_in,
}


def chip_field():
    """Blotches that tile over the whole picture, 0 to 1 and evenly spread: paint is gone where this is
    under a figure's wear."""
    rs = np.random.RandomState(77)
    shape = (SIZE, SIZE)
    f = (0.5 * vnoise(rs, shape, 40, 40, True) + 0.3 * vnoise(rs, shape, 90, 90, True)
         + 0.2 * vnoise(rs, shape, 200, 200, True))
    order = np.argsort(f.ravel())
    even = np.empty(f.size)
    even[order] = np.linspace(0.0, 1.0, f.size)
    return even.reshape(shape)


def paint_all():
    """The two pictures as float arrays (SIZE, SIZE, 4), row 0 at the bottom: paint, masks."""
    paint = np.zeros((SIZE, SIZE, 4))
    masks = np.zeros((SIZE, SIZE, 4))
    masks[..., 1] = 0.75
    masks[..., 2] = 0.75
    for name, _w, _h in REGIONS:
        if name.startswith("face_"):
            p = paint_face(name[5:])
        elif name.startswith("torso_"):
            p = paint_torso(name[6:])
        else:
            p = PAINTERS[name]()
        x, y, w, h = RECT[name]
        rows = slice(y - PAD, y + h + PAD)
        cols = slice(x - PAD, x + w + PAD)
        paint[rows, cols, :3] = p.over
        paint[rows, cols, 3] = p.cover
        masks[rows, cols, 0] = p.trim
        masks[rows, cols, 1] = np.clip(p.shade, 0.0, 1.0)
        masks[rows, cols, 2] = p.gloss
    masks[..., 3] = chip_field()
    # where nothing covers, carry the nearest painted colour outwards so no dark fringe is filtered in
    rgb = paint[..., :3].copy()
    filled = paint[..., 3] > 0.02
    rgb[~filled] = 0.0
    for _ in range(10):
        acc = np.zeros_like(rgb)
        cnt = np.zeros(filled.shape)
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            acc += np.roll(rgb * filled[..., None], (dy, dx), (0, 1))
            cnt += np.roll(filled, (dy, dx), (0, 1))
        new = (~filled) & (cnt > 0)
        rgb[new] = acc[new] / cnt[new][:, None]
        filled |= new
    rgb[~filled] = 0.5
    paint[..., :3] = rgb
    return np.clip(paint, 0, 1), np.clip(masks, 0, 1)


def preview(paint, masks, colour=(0.72, 0.08, 0.07), trim=(0.86, 0.66, 0.2)):
    """The two pictures put together in one colour, to look at."""
    base = np.empty((SIZE, SIZE, 3))
    for i in range(3):
        base[..., i] = colour[i] * (1 - masks[..., 0]) + trim[i] * masks[..., 0]
        base[..., i] = base[..., i] * (1 - paint[..., 3]) + paint[..., i] * paint[..., 3]
        base[..., i] *= masks[..., 1] / 0.75
    out = np.ones((SIZE, SIZE, 4))
    out[..., :3] = np.clip(base, 0, 1)
    return out
