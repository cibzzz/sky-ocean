#!/usr/bin/env python3
"""The Sky Ocean -- a generative artwork for make.fun coolest-art-01.

A humpback whale swims across the face of the moon above a quiet night
sea, trailing a stream of glowing plankton, while a lone boat's lantern
answers from below.  Drawn entirely in code (Python standard library
only), deterministically, and written to entry.png in the output dir.
"""

import os
import struct
import zlib
from binascii import crc32

W = 1024
H = 1024
HORIZON = 812


# ---------------------------------------------------------------- rng
class Rng:
    """Tiny xorshift64: identical numbers on every Python, every run."""

    def __init__(self, seed):
        self.s = seed & 0xFFFFFFFFFFFFFFFF or 0x9E3779B97F4A7C15

    def next(self):
        x = self.s
        x ^= (x << 13) & 0xFFFFFFFFFFFFFFFF
        x ^= x >> 7
        x ^= (x << 17) & 0xFFFFFFFFFFFFFFFF
        self.s = x & 0xFFFFFFFFFFFFFFFF
        return self.s

    def f(self):
        return self.next() / 18446744073709551616.0

    def range(self, a, b):
        return a + (b - a) * self.f()


# ---------------------------------------------------------------- canvas
px = bytearray(W * H * 3)


def put(x, y, r, g, b):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        px[i] = r
        px[i + 1] = g
        px[i + 2] = b


def blend(x, y, r, g, b, a):
    """Alpha-blend a colour over the canvas; a in [0, 1]."""
    if 0 <= x < W and 0 <= y < H and a > 0.0:
        i = (y * W + x) * 3
        ia = 1.0 - a
        px[i] = int(px[i] * ia + r * a)
        px[i + 1] = int(px[i + 1] * ia + g * a)
        px[i + 2] = int(px[i + 2] * ia + b * a)


def add(x, y, r, g, b, a):
    """Additive light stamp (for glows)."""
    if 0 <= x < W and 0 <= y < H and a > 0.0:
        i = (y * W + x) * 3
        px[i] = min(255, px[i] + int(r * a))
        px[i + 1] = min(255, px[i + 1] + int(g * a))
        px[i + 2] = min(255, px[i + 2] + int(b * a))


def glow(cx, cy, rad, r, g, b, peak, additive=True):
    """Soft radial light stamp with quadratic falloff."""
    x0 = max(0, int(cx - rad))
    x1 = min(W - 1, int(cx + rad))
    y0 = max(0, int(cy - rad))
    y1 = min(H - 1, int(cy + rad))
    fn = add if additive else blend
    for y in range(y0, y1 + 1):
        dy = (y - cy) / rad
        for x in range(x0, x1 + 1):
            dx = (x - cx) / rad
            d2 = dx * dx + dy * dy
            if d2 < 1.0:
                fn(x, y, r, g, b, peak * (1.0 - d2) * (1.0 - d2))


def lerp(a, b, t):
    return a + (b - a) * t


def grad(stops, t):
    """Piecewise-linear gradient; stops = [(pos, (r, g, b)), ...]."""
    for k in range(len(stops) - 1):
        p0, c0 = stops[k]
        p1, c1 = stops[k + 1]
        if p0 <= t <= p1:
            f = 0.0 if p1 == p0 else (t - p0) / (p1 - p0)
            return (int(lerp(c0[0], c1[0], f)),
                    int(lerp(c0[1], c1[1], f)),
                    int(lerp(c0[2], c1[2], f)))
    return stops[-1][1]


BAYER = ((0, 8, 2, 10), (12, 4, 14, 6), (3, 11, 1, 9), (15, 7, 13, 5))


# ---------------------------------------------------------------- sky
def paint_sky(rng):
    stops = [
        (0.00, (5, 7, 22)),
        (0.35, (11, 16, 46)),
        (0.62, (23, 34, 78)),
        (0.79, (38, 56, 102)),
        (1.00, (30, 48, 84)),
    ]
    for y in range(HORIZON):
        t = y / HORIZON
        r, g, b = grad(stops, t)
        row = (y * W) * 3
        brow = BAYER[y & 3]
        for x in range(W):
            d = brow[x & 3] - 8          # ordered dither, kills banding
            i = row + x * 3
            px[i] = max(0, min(255, r + d // 4))
            px[i + 1] = max(0, min(255, g + d // 4))
            px[i + 2] = max(0, min(255, b + d // 4))


def paint_stars(rng):
    # a faint milky band drifting from upper-left to mid-right
    for _ in range(2600):
        t = rng.f()
        cx = 80 + t * 900 + (rng.f() - 0.5) * 190
        cy = 60 + t * 330 + (rng.f() - 0.5) * 120
        if 0 <= cx < W and 0 <= cy < HORIZON - 60:
            a = 0.05 + 0.10 * rng.f()
            blend(int(cx), int(cy), 200, 215, 255, a)
    # stars, denser and brighter higher up
    for _ in range(850):
        x = int(rng.f() * W)
        y = int((rng.f() ** 1.4) * (HORIZON - 40))
        roll = rng.f()
        if roll < 0.72:
            c = (235, 240, 255)
        elif roll < 0.9:
            c = (190, 210, 255)
        else:
            c = (255, 230, 190)
        a = 0.25 + 0.75 * rng.f() * (1.0 - y / HORIZON * 0.55)
        put(x, y, int(c[0] * a + px[(y * W + x) * 3] * (1 - a)),
            int(c[1] * a + px[(y * W + x) * 3 + 1] * (1 - a)),
            int(c[2] * a + px[(y * W + x) * 3 + 2] * (1 - a)))
        if rng.f() < 0.06:  # a few bright stars get a small cross sparkle
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                blend(x + dx, y + dy, c[0], c[1], c[2], a * 0.45)


# ---------------------------------------------------------------- moon
MOON = (505, 392, 232)


def paint_moon(rng):
    cx, cy, rad = MOON
    glow(cx, cy, rad * 1.9, 120, 130, 170, 0.16)
    glow(cx, cy, rad * 1.25, 190, 185, 160, 0.20)
    # maria: soft darker patches, clipped to the disc
    import math
    patches = []
    for _ in range(12):
        ang = rng.f() * 6.28318
        dist = rad * (0.15 + rng.f() * 0.68)
        patches.append((cx + dist * math.cos(ang), cy + dist * math.sin(ang),
                        35 + rng.f() * 50))
    for y in range(cy - rad, cy + rad + 1):
        dy = y - cy
        for x in range(cx - rad, cx + rad + 1):
            dx = x - cx
            d2 = dx * dx + dy * dy
            if d2 > rad * rad:
                continue
            d = (d2 ** 0.5) / rad
            # warm ivory heart cooling to a pale gold rim, gentle limb shading
            r = int(lerp(250, 226, d * d))
            g = int(lerp(240, 198, d * d))
            b = int(lerp(214, 158, d * d))
            shade = 0.0
            for mx, my, mr in patches:
                md = ((x - mx) ** 2 + (y - my) ** 2) ** 0.5
                if md < mr:
                    f = 1 - md / mr
                    shade = max(shade, f * f * 0.055)
            put(x, y, int(r * (1 - shade)), int(g * (1 - shade)),
                int(b * (1 - shade)))


# ---------------------------------------------------------------- shapes
def chaikin(pts, rounds):
    for _ in range(rounds):
        out = [pts[0]]
        for i in range(len(pts) - 1):
            ax, ay = pts[i]
            bx, by = pts[i + 1]
            out.append((ax * 0.75 + bx * 0.25, ay * 0.75 + by * 0.25))
            out.append((ax * 0.25 + bx * 0.75, ay * 0.25 + by * 0.75))
        out.append(pts[-1])
        pts = out
    return pts


def fill_polygon(mask, pts, x0, y0, x1, y1):
    """Even-odd scanline fill of a closed polygon into a byte mask."""
    n = len(pts)
    for y in range(y0, y1 + 1):
        nodes = []
        for i in range(n):
            ax, ay = pts[i]
            bx, by = pts[(i + 1) % n]
            if (ay <= y < by) or (by <= y < ay):
                nodes.append(ax + (y - ay) * (bx - ax) / (by - ay))
        nodes.sort()
        for k in range(0, len(nodes) - 1, 2):
            xa = max(x0, int(nodes[k]))
            xb = min(x1, int(nodes[k + 1]))
            base = y * W
            for x in range(xa, xb + 1):
                mask[base + x] = 255


def blur_mask(mask, x0, y0, x1, y1):
    """One separable box blur (radius 2) over a region of the mask."""
    tmp = bytearray(W * H)
    for y in range(y0, y1 + 1):
        base = y * W
        for x in range(x0, x1 + 1):
            s = 0
            for dx in (-2, -1, 0, 1, 2):
                xx = min(x1, max(x0, x + dx))
                s += mask[base + xx]
            tmp[base + x] = s // 5
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            s = 0
            for dy in (-2, -1, 0, 1, 2):
                yy = min(y1, max(y0, y + dy))
                s += tmp[yy * W + x]
            mask[y * W + x] = s // 5


# ---------------------------------------------------------------- whale
def whale_polygons():
    # Humpback, head to the right: blunt rounded rostrum, a full throat,
    # a long tapering body, a narrow peduncle and a wide notched fluke.
    top = [
        (992, 226), (980, 202), (928, 182), (872, 158), (800, 138),
        (700, 126), (590, 122), (480, 120), (380, 124), (290, 132),
        (215, 146), (168, 162),
        (150, 150), (140, 138), (128, 158),   # the dorsal hump and fin
        (96, 168), (40, 120), (6, 112),      # fluke, upper lobe
        (52, 176),                            # fluke notch
        (20, 232), (100, 208),               # fluke, lower lobe
    ]
    bottom = [
        (180, 226), (280, 254), (400, 278), (520, 290), (640, 288),
        (770, 282), (870, 250), (942, 238), (985, 236),
    ]
    body = chaikin(top + bottom, 3)
    fin = chaikin([
        (712, 276), (738, 284), (706, 398), (668, 442), (640, 430),
        (656, 300), (672, 282),
    ], 3)
    return body, fin


def paint_whale():
    scale = 0.9
    ox, oy = 62, 238
    mask = bytearray(W * H)
    for poly in whale_polygons():
        pts = [(ox + x * scale, oy + y * scale) for x, y in poly]
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        fill_polygon(mask, pts, int(min(xs)), int(min(ys)),
                     int(max(xs)), int(max(ys)))
    blur_mask(mask, 40, 320, 990, 660)
    # silhouette: near-black blue, a breath lighter toward the belly,
    # with a hair of moonlight caught on its anti-aliased edge
    for y in range(320, 661):
        belly = (y - 320) / 340.0
        r = int(lerp(4, 10, belly))
        g = int(lerp(6, 14, belly))
        b = int(lerp(14, 30, belly))
        base = y * W
        for x in range(40, 991):
            m = mask[base + x]
            if m == 255:
                blend(x, y, r, g, b, 1.0)
            elif m:
                a = m / 255.0
                er = int(lerp(r, 150, 0.25))
                eg = int(lerp(g, 165, 0.25))
                eb = int(lerp(b, 205, 0.25))
                blend(x, y, er, eg, eb, a)


def paint_plankton(rng):
    # a stream of light spilling from the tail, curling down-left then right
    path = [(70, 398), (44, 442), (52, 502), (104, 556), (196, 606),
            (318, 640), (452, 656)]
    dots = []
    for i in range(len(path) - 1):
        ax, ay = path[i]
        bx, by = path[i + 1]
        steps = 46
        for s in range(steps):
            t = s / steps
            x = lerp(ax, bx, t) + (rng.f() - 0.5) * 26 * (0.3 + t)
            y = lerp(ay, by, t) + (rng.f() - 0.5) * 26 * (0.3 + t)
            dots.append((x, y, (i + t) / (len(path) - 1)))
    for x, y, t in dots:
        rad = lerp(4.5, 2.0, t) * (0.6 + rng.f() * 0.7)
        peak = lerp(0.55, 0.25, t) * (0.6 + rng.f() * 0.6)
        glow(x, y, rad, 110, 220, 255, peak)
        add(int(x), int(y), 220, 250, 255, min(1.0, peak + 0.25))


# ---------------------------------------------------------------- sea
def paint_sea(rng):
    stops = [(0.0, (26, 42, 70)), (0.25, (16, 29, 52)),
             (0.7, (9, 17, 34)), (1.0, (5, 9, 20))]
    for y in range(HORIZON, H):
        t = (y - HORIZON) / (H - HORIZON)
        r, g, b = grad(stops, t)
        row = (y * W) * 3
        for x in range(W):
            i = row + x * 3
            px[i] = r
            px[i + 1] = g
            px[i + 2] = b
    # horizon hairline
    for x in range(W):
        blend(x, HORIZON, 150, 175, 215, 0.28)
    # the moon's reflection: a broken column of pale gold shimmers
    mcx = MOON[0]
    for i in range(340):
        t = rng.f()
        y = HORIZON + 6 + int(t * (H - HORIZON - 14))
        spread = 26 + t * 120
        x = mcx + (rng.f() - 0.5) * 2 * spread
        ln = 4 + rng.f() * (14 + t * 42)
        a = (1 - t * 0.75) * (0.10 + rng.f() * 0.22)
        for xx in range(int(x), int(x + ln)):
            blend(xx, y, 246, 224, 170, a)
    # general faint shimmer across the water
    for _ in range(210):
        y = HORIZON + 4 + int(rng.f() * (H - HORIZON - 8))
        x = int(rng.f() * (W - 30))
        ln = 3 + rng.f() * 16
        a = 0.04 + rng.f() * 0.08
        for xx in range(x, x + int(ln)):
            blend(xx, y, 170, 195, 235, a)


def paint_islets():
    mask = bytearray(W * H)
    left = [(30, HORIZON + 2), (70, HORIZON - 16), (150, HORIZON - 24),
            (238, HORIZON - 8), (268, HORIZON + 2)]
    right = [(782, HORIZON + 2), (838, HORIZON - 12), (922, HORIZON - 18),
             (992, HORIZON - 4), (1010, HORIZON + 2)]
    fill_polygon(mask, left, 20, HORIZON - 30, 280, HORIZON + 2)
    fill_polygon(mask, right, 770, HORIZON - 30, 1020, HORIZON + 2)
    for y in range(HORIZON - 30, HORIZON + 3):
        for x in range(20, 1021):
            if mask[y * W + x]:
                blend(x, y, 5, 8, 18, 0.96)


def paint_boat(rng):
    bx, by = 292, 848
    mask = bytearray(W * H)
    hull = [(bx - 52, by), (bx + 54, by), (bx + 38, by + 17),
            (bx - 30, by + 17)]
    fill_polygon(mask, hull, bx - 56, by - 2, bx + 58, by + 20)
    cabin = [(bx - 6, by - 14), (bx + 22, by - 14), (bx + 22, by),
             (bx - 6, by)]
    fill_polygon(mask, cabin, bx - 8, by - 16, bx + 24, by + 1)
    for y in range(by - 16, by + 20):
        for x in range(bx - 56, bx + 59):
            if mask[y * W + x]:
                blend(x, y, 4, 6, 13, 0.97)
    # mast and a furled line to the bow
    for y in range(by - 44, by - 13):
        put(bx + 2, y, 4, 6, 13)
    for i in range(40):
        x = bx + 3 + i
        y = by - 44 + int(i * 0.62)
        put(x, y, 4, 6, 13)
    # the lantern: a warm heart of light and its reflection
    lx, ly = bx + 30, by - 18
    glow(lx, ly, 30, 255, 166, 66, 0.55)
    glow(lx, ly, 12, 255, 196, 110, 0.8)
    put(lx, ly, 255, 240, 205)
    put(lx - 1, ly, 255, 226, 170)
    put(lx + 1, ly, 255, 226, 170)
    for i in range(26):
        y = by + 20 + i * 2
        a = 0.20 * (1 - i / 26) * (0.6 + rng.f() * 0.6)
        wob = int((rng.f() - 0.5) * 6)
        for xx in range(lx - 3 + wob, lx + 4 + wob):
            blend(xx, y, 255, 176, 84, a)


# ---------------------------------------------------------------- finish
def vignette():
    cx, cy = W / 2, H / 2
    maxd2 = cx * cx + cy * cy
    dx2 = [(x - cx) ** 2 for x in range(W)]
    for y in range(H):
        dy2 = (y - cy) ** 2
        row = y * W * 3
        for x in range(W):
            d2 = (dx2[x] + dy2) / maxd2
            f = 1.0 - 0.34 * d2 * d2
            i = row + x * 3
            px[i] = int(px[i] * f)
            px[i + 1] = int(px[i + 1] * f)
            px[i + 2] = int(px[i + 2] * f)


def render():
    rng = Rng(0x51AB3)
    paint_sky(rng)
    paint_stars(rng)
    paint_moon(rng)
    paint_plankton(rng)
    paint_sea(rng)
    paint_islets()
    paint_whale()
    paint_boat(rng)
    vignette()
    return encode_png()


def encode_png():
    raw = bytearray()
    stride = W * 3
    for y in range(H):
        raw.append(0)
        raw += px[y * stride:(y + 1) * stride]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(tag, data):
        return (struct.pack('>I', len(data)) + tag + data +
                struct.pack('>I', crc32(tag + data) & 0xFFFFFFFF))

    ihdr = struct.pack('>IIBBBBB', W, H, 8, 2, 0, 0, 0)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr) +
            chunk(b'IDAT', comp) + chunk(b'IEND', b''))


def main():
    out_dir = os.environ.get('MAKEFUN_OUTPUT_DIR', '/output')
    data = render()
    with open(os.path.join(out_dir, 'entry.png'), 'wb') as fh:
        fh.write(data)


if __name__ == '__main__':
    main()
