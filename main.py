#!/usr/bin/env python3
"""THE WORLD - Monday 23 November 2026. Front-page news image, drawn
procedurally with the Python standard library only.

Writes a 1024x1024 PNG to $MAKEFUN_OUTPUT_DIR/entry.png (default /output).
Deterministic: no randomness, no clock, no network, no file reads.
"""
import math
import os
import struct
import zlib

W = 1024
H = 1024

# ---------------------------------------------------------------- palette
NAVY = (15, 26, 48)
NAVY2 = (9, 18, 34)
INK = (22, 26, 36)
CREAM = (246, 238, 218)
PAPER = (250, 244, 228)
GOLD = (232, 163, 61)
GOLDL = (244, 199, 92)
RED = (178, 38, 28)
RED2 = (203, 64, 46)
AMBER = (216, 106, 42)
DUSK = (74, 43, 77)
WHITE = (252, 248, 236)
DIM = (120, 116, 100)

# ------------------------------------------------------- 5x7 bitmap font
# Each glyph: 7 rows of 5 cells, '#' = ink, '.' = blank. Uppercase only;
# all copy in this program is uppercased before drawing.
FONT = {
    'A': (".###.", "#...#", "#####", "#...#", "#...#"),
    'B': ("####.", "#...#", "####.", "#...#", "####."),
    'C': (".###.", "#...#", "#....", "#...#", ".###."),
    'D': ("####.", "#...#", "#...#", "#...#", "####."),
    'E': ("#####", "#....", "####.", "#....", "#####"),
    'F': ("#####", "#....", "####.", "#....", "#...."),
    'G': (".###.", "#...#", "#.###", "#...#", ".####"),
    'H': ("#...#", "#...#", "#####", "#...#", "#...#"),
    'I': (".###.", "..#..", "..#..", "..#..", ".###."),
    'J': ("..###", "...#.", "...#.", "#..#.", ".##.."),
    'K': ("#...#", "#..#.", "##...", "#.#..", "#...#"),
    'L': ("#....", "#....", "#....", "#....", "#####"),
    'M': ("#...#", "##.##", "#.#.#", "#...#", "#...#"),
    'N': ("#...#", "##..#", "#.#.#", "#..##", "#...#"),
    'O': (".###.", "#...#", "#...#", "#...#", ".###."),
    'P': ("####.", "#...#", "####.", "#....", "#...."),
    'Q': (".###.", "#...#", "#...#", "#.#.#", ".##.#"),
    'R': ("####.", "#...#", "####.", "#.#..", "#...#"),
    'S': (".####", "#....", ".###.", "....#", "####."),
    'T': ("#####", "..#..", "..#..", "..#..", "..#.."),
    'U': ("#...#", "#...#", "#...#", "#...#", ".###."),
    'V': ("#...#", "#...#", "#...#", ".#.#.", "..#.."),
    'W': ("#...#", "#...#", "#.#.#", "#.#.#", ".#.#."),
    'X': ("#...#", ".#.#.", "..#..", ".#.#.", "#...#"),
    'Y': ("#...#", ".#.#.", "..#..", "..#..", "..#.."),
    'Z': ("#####", "....#", "...#.", ".#...", "#####"),
    '0': (".###.", "#..##", "#.#.#", "##..#", ".###."),
    '1': ("..#..", ".##..", "..#..", "..#..", ".###."),
    '2': (".###.", "#...#", "..##.", ".#...", "#####"),
    '3': (".###.", "....#", "..##.", "....#", ".###."),
    '4': ("...#.", "..##.", ".#.#.", "#####", "...#."),
    '5': ("#####", "#....", "####.", "....#", ".###."),
    '6': (".###.", "#....", "####.", "#...#", ".###."),
    '7': ("#####", "....#", "...#.", "..#..", ".#..."),
    '8': (".###.", "#...#", ".###.", "#...#", ".###."),
    '9': (".###.", "#...#", ".####", "....#", ".###."),
    ' ': (".....", ".....", ".....", ".....", "....."),
    '-': (".....", ".....", "#####", ".....", "....."),
    '.': (".....", ".....", ".....", ".....", ".##.."),
    ',': (".....", ".....", ".....", ".##..", ".#..."),
    ':': (".....", ".##..", ".....", ".##..", "....."),
    ';': (".....", ".##..", ".....", ".##..", ".#..."),
    "'": ("..#..", "..#..", ".....", ".....", "....."),
    '!': ("..#..", "..#..", "..#..", ".....", "..#.."),
    '?': (".###.", "#...#", "..##.", "..#..", "..#.."),
    '(': ("...#.", "..#..", ".#...", ".#...", "..#.."),
    ')': (".#...", "..#..", "...#.", "...#.", "..#.."),
    '/': ("....#", "...#.", "..#..", ".#...", "#...."),
    '&': (".##..", "#..#.", "#.#..", ".#...", "#..#."),
    '%': ("##..#", "##.#.", "...#.", ".#...", "#..##"),
    '+': (".....", "..#..", "#####", "..#..", "....."),
    '=': (".....", "#####", ".....", "#####", "....."),
    '"': (".#.#.", ".#.#.", ".....", ".....", "....."),
    '*': (".....", "#.#.#", ".###.", "#.#.#", "....."),
}
# NOTE: glyphs above are stored as 5 rows of 5; the renderer treats them as
# a 5-wide x 5-tall cell and stretches vertically to 7 rows by repeating
# rows 1 and 3, which keeps the classic blocky newspaper look while the
# table stays compact. (Rows are duplicated in _glyph_rows below.)
_GLYPH_ROWS = [0, 0, 1, 2, 2, 3, 4]


def _glyph(ch):
    g = FONT.get(ch)
    if g is None:
        g = FONT['?']
    return [_row(g[i]) for i in _GLYPH_ROWS]


def _row(s):
    return s


def text_width(s, sx, track=None):
    if track is None:
        track = sx
    return len(s) * (5 * sx + track) - track if s else 0


def draw_text(img, x, y, s, sx, sy, color, track=None, align="left"):
    """Draw uppercase text. Returns the x position just past the text."""
    if track is None:
        track = sx
    if align == "center":
        x -= text_width(s, sx, track) // 2
    elif align == "right":
        x -= text_width(s, sx, track)
    cx = x
    for ch in s:
        glyph = _glyph(ch)
        for gy in range(7):
            row = glyph[gy]
            for gx in range(5):
                if row[gx] == '#':
                    img.fill_rect(cx + gx * sx, y + gy * sy, sx, sy, color)
        cx += 5 * sx + track
    return cx


def draw_text_grad(img, x, y, s, sx, sy, c_top, c_bot, shadow=None,
                   track=None, align="left"):
    """Text with a vertical colour gradient and an optional drop shadow."""
    if track is None:
        track = sx
    if align == "center":
        x -= text_width(s, sx, track) // 2
    elif align == "right":
        x -= text_width(s, sx, track)
    if shadow is not None:
        draw_text(img, x + 3, y + 4, s, sx, sy, shadow, track=track)
    cx = x
    total_h = 7 * sy
    for ch in s:
        glyph = _glyph(ch)
        for gy in range(7):
            row = glyph[gy]
            t = (gy * sy + sy / 2.0) / total_h
            col = lerp_color(c_top, c_bot, t)
            for gx in range(5):
                if row[gx] == '#':
                    img.fill_rect(cx + gx * sx, y + gy * sy, sx, sy, col)
        cx += 5 * sx + track
    return cx


def lerp_color(c1, c2, t):
    return tuple(int(round(c1[i] + (c2[i] - c1[i]) * t)) for i in range(3))


# ------------------------------------------------------------------- image
class Img:
    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.px = bytearray(bg * (w * h))

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i:i + 3] = bytes(c)

    def fill_rect(self, x, y, w, h, c):
        x0 = max(0, int(x))
        y0 = max(0, int(y))
        x1 = min(self.w, int(x) + int(w))
        y1 = min(self.h, int(y) + int(h))
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(c) * (x1 - x0)
        for yy in range(y0, y1):
            i = (yy * self.w + x0) * 3
            self.px[i:i + len(row)] = row

    def vgrad(self, x, y, w, h, stops):
        """Vertical gradient; stops = list of (pos 0..1, color)."""
        for yy in range(int(y), int(y) + int(h)):
            t = (yy - y) / max(1, h - 1)
            c = grad_at(stops, t)
            self.fill_rect(x, yy, w, 1, c)

    def disc(self, cx, cy, r, c):
        r = int(r)
        for dy in range(-r, r + 1):
            dx = int(math.sqrt(max(0, r * r - dy * dy)))
            self.fill_rect(cx - dx, cy + dy, 2 * dx + 1, 1, c)

    def line(self, x0, y0, x1, y1, c, thick=1):
        dx = x1 - x0
        dy = y1 - y0
        steps = max(abs(dx), abs(dy), 1)
        for i in range(steps + 1):
            t = i / steps
            self.fill_rect(round(x0 + dx * t), round(y0 + dy * t),
                           thick, thick, c)

    def poly(self, pts, c):
        """Scanline fill for a simple polygon (list of (x, y))."""
        if len(pts) < 3:
            return
        ys = [p[1] for p in pts]
        for y in range(int(min(ys)), int(max(ys)) + 1):
            xs = []
            n = len(pts)
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    t = (y - y0) / (y1 - y0)
                    xs.append(x0 + t * (x1 - x0))
            xs.sort()
            for j in range(0, len(xs) - 1, 2):
                self.fill_rect(int(xs[j]), y, int(xs[j + 1]) - int(xs[j]) + 1,
                               1, c)

    def star(self, cx, cy, r, c):
        pts = []
        for i in range(10):
            ang = -math.pi / 2 + i * math.pi / 5
            rr = r if i % 2 == 0 else r * 0.45
            pts.append((cx + rr * math.cos(ang), cy + rr * math.sin(ang)))
        self.poly(pts, c)


def grad_at(stops, t):
    if t <= stops[0][0]:
        return stops[0][1]
    for i in range(1, len(stops)):
        if t <= stops[i][0]:
            p0, c0 = stops[i - 1]
            p1, c1 = stops[i]
            tt = (t - p0) / max(1e-9, p1 - p0)
            return lerp_color(c0, c1, tt)
    return stops[-1][1]


# --------------------------------------------------------------------- PNG
def write_png(img, path):
    raw = bytearray()
    stride = img.w * 3
    for y in range(img.h):
        raw.append(0)
        raw += img.px[y * stride:(y + 1) * stride]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", img.w, img.h, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", ihdr)
    png += chunk(b"IDAT", comp)
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    os.chmod(path, 0o644)
    return len(png)


# ------------------------------------------------------------ photo scenes
# Warm, photographic-style panels: dusk gradients, amber light, dark
# silhouettes. No posterize / Sobel / halftone anywhere.

def sky_dusk(img, x, y, w, h):
    img.vgrad(x, y, w, h, [
        (0.0, (28, 30, 68)), (0.45, (96, 52, 88)),
        (0.75, (214, 110, 56)), (1.0, (244, 178, 92))])


def sky_night(img, x, y, w, h):
    img.vgrad(x, y, w, h, [
        (0.0, (12, 18, 42)), (0.55, (38, 32, 66)), (1.0, (120, 62, 66))])


def sky_day(img, x, y, w, h):
    img.vgrad(x, y, w, h, [
        (0.0, (52, 84, 128)), (0.55, (150, 140, 110)),
        (1.0, (244, 186, 104))])


def sun(img, cx, cy, r):
    img.disc(cx, cy, r + 14, (238, 150, 70))
    img.disc(cx, cy, r + 6, (248, 190, 96))
    img.disc(cx, cy, r, (255, 222, 138))


def smoke(img, x, y, r, col):
    img.disc(x, y, r, col)
    img.disc(x + r // 2, y - r // 3, int(r * 0.7), col)
    img.disc(x - r // 2, y - r // 4, int(r * 0.6), col)


def flag_pole(img, x, y0, y1, cols):
    """Tiny vertical flag on a pole; cols = list of horizontal bands."""
    img.fill_rect(x, y0, 2, y1 - y0, (40, 30, 28))
    bh = max(2, (y1 - y0) // 6)
    for i, c in enumerate(cols):
        img.fill_rect(x + 2, y0 + i * bh, 16, bh, c)


def hero_scene(img, x, y, w, h):
    sky_dusk(img, x, y, w, h)
    sun(img, x + w - 190, y + h - 46, 30)
    # distant skyline
    base = y + h
    for bx, bw, bh in [(0, 90, 42), (100, 60, 66), (170, 110, 34),
                       (700, 80, 58), (790, 120, 38), (920, 84, 50)]:
        img.fill_rect(x + bx, base - bh, bw, bh, (36, 24, 50))
    # conference hall with dome and columns
    hx0, hx1 = x + 300, x + 704
    img.fill_rect(hx0, base - 108, hx1 - hx0, 108, (26, 18, 44))
    img.disc(x + 502, base - 108, 62, (26, 18, 44))
    img.fill_rect(x + 440, base - 108, 124, 22, (26, 18, 44))
    for cx in range(hx0 + 26, hx1 - 20, 44):
        img.fill_rect(cx, base - 96, 8, 96, (244, 199, 92))
    img.fill_rect(hx0, base - 112, hx1 - hx0, 6, (244, 199, 92))
    # flag row in front of the hall
    flag_cols = [[(178, 38, 28), (252, 248, 236), (178, 38, 28)],
                 [(30, 80, 140), (252, 248, 236)],
                 [(24, 120, 70), (252, 248, 236)],
                 [(216, 106, 42)], [(120, 60, 130)],
                 [(178, 38, 28), (252, 248, 236), (178, 38, 28)]]
    fx = x + 60
    for cols in flag_cols:
        flag_pole(img, fx, base - 78, base - 30, cols)
        fx += 46
    for cols in flag_cols:
        flag_pole(img, fx, base - 78, base - 30, cols)
        fx += 46
    # crowd silhouettes along the bottom
    for cx in range(x + 8, x + w - 8, 26):
        img.disc(cx, base - 12, 9, (16, 12, 26))
        img.fill_rect(cx - 12, base - 6, 24, 6, (16, 12, 26))


def capitol_scene(img, x, y, w, h):
    sky_day(img, x, y, w, h)
    sun(img, x + w - 34, y + 26, 14)
    base = y + h
    img.fill_rect(x, base - 30, w, 30, (34, 26, 48))
    img.disc(x + w // 2, base - 30, 26, (34, 26, 48))
    img.fill_rect(x + w // 2 - 26, base - 30, 52, 10, (34, 26, 48))
    for cx in range(x + 18, x + w - 18, 22):
        img.fill_rect(cx, base - 26, 5, 26, (244, 199, 92))
    flag_pole(img, x + 14, y + 12, base - 30,
              [(178, 38, 28), (252, 248, 236), (178, 38, 28)])


def hormuz_scene(img, x, y, w, h):
    sky_dusk(img, x, y, w, h)
    base = y + h
    img.vgrad(x, y + int(h * 0.55), w, h - int(h * 0.55),
              [(0.0, (150, 96, 60)), (1.0, (28, 44, 62))])
    # tanker silhouette
    img.fill_rect(x + 30, base - 26, w - 70, 14, (14, 14, 20))
    img.fill_rect(x + w - 90, base - 44, 26, 18, (14, 14, 20))
    img.fill_rect(x + 44, base - 36, 10, 10, (14, 14, 20))
    # fire glow + smoke above the deck
    img.disc(x + w // 2 - 30, base - 34, 12, (255, 170, 60))
    img.disc(x + w // 2 - 30, base - 34, 6, (255, 230, 140))
    smoke(img, x + w // 2 - 10, base - 52, 12, (90, 74, 78))
    smoke(img, x + w - 70, base - 58, 10, (80, 66, 72))
    # missile streak
    img.line(x + 40, y + 8, x + 110, y + 44, (255, 236, 180), 2)


def kyiv_scene(img, x, y, w, h):
    sky_night(img, x, y, w, h)
    img.disc(x + w - 40, y + 18, 10, (240, 226, 190))
    base = y + h
    # apartment block
    img.fill_rect(x + 40, y + 18, 90, h - 18, (18, 16, 30))
    img.fill_rect(x + 150, y + 34, 70, h - 34, (22, 18, 34))
    for wy in range(y + 26, base - 8, 14):
        for wx in (x + 52, x + 72, x + 92, x + 112):
            img.fill_rect(wx, wy, 7, 9, (244, 190, 90))
    # fire glow in one window + smoke
    img.disc(x + 82, y + 44, 12, (255, 150, 50))
    img.disc(x + 82, y + 44, 6, (255, 220, 120))
    smoke(img, x + 82, y + 20, 12, (96, 82, 88))
    # drone streak
    img.line(x + w - 130, y + 10, x + w - 70, y + 40, (255, 236, 180), 2)
    img.disc(x + w - 70, y + 40, 3, (255, 236, 180))


def factory_scene(img, x, y, w, h):
    sky_night(img, x, y, w, h)
    base = y + h
    img.fill_rect(x, base - 34, w, 34, (20, 18, 32))
    img.fill_rect(x + 30, base - 52, 150, 18, (20, 18, 32))
    img.fill_rect(x + 210, base - 44, 60, 10, (20, 18, 32))
    img.fill_rect(x + 300, base - 64, 14, 30, (20, 18, 32))
    # flames at the roofline
    for fx, fr in [(70, 12), (110, 16), (150, 11), (330, 9)]:
        img.disc(x + fx, base - 36, fr, (255, 140, 40))
        img.disc(x + fx, base - 36, fr // 2, (255, 220, 120))
    # big smoke column
    smoke(img, x + 120, y + 26, 16, (104, 90, 94))
    smoke(img, x + 150, y + 12, 12, (118, 102, 106))
    # floodlight beam
    img.line(x + 420, base - 60, x + 340, y + 10, (255, 236, 180), 2)


def delhi_scene(img, x, y, w, h):
    sky_day(img, x, y, w, h)
    sun(img, x + 40, y + 22, 13)
    base = y + h
    # domed government building + minarets
    img.fill_rect(x + 150, base - 40, 200, 40, (40, 28, 52))
    img.disc(x + 250, base - 40, 30, (40, 28, 52))
    img.fill_rect(x + 220, base - 40, 60, 12, (40, 28, 52))
    img.fill_rect(x + 120, base - 58, 10, 58, (40, 28, 52))
    img.fill_rect(x + 380, base - 58, 10, 58, (40, 28, 52))
    for cx in range(x + 170, x + 340, 26):
        img.fill_rect(cx, base - 34, 6, 34, (244, 199, 92))
    # Nepal flag (crimson double pennon) and India tricolour
    img.fill_rect(x + 30, y + 14, 2, base - 14 - y, (40, 30, 28))
    img.poly([(x + 32, y + 14), (x + 54, y + 20), (x + 32, y + 26),
              (x + 48, y + 30), (x + 32, y + 36)], (200, 40, 48))
    img.fill_rect(x + w - 60, y + 14, 2, base - 14 - y, (40, 30, 28))
    img.fill_rect(x + w - 58, y + 14, 26, 7, (255, 153, 51))
    img.fill_rect(x + w - 58, y + 21, 26, 7, (252, 248, 236))
    img.fill_rect(x + w - 58, y + 28, 26, 7, (19, 136, 8))
    img.disc(x + w - 45, y + 24, 3, (6, 60, 140))


# ------------------------------------------------------------------ layout
def chip(img, x, y, w, h, bg, fg, text, sx=2):
    img.fill_rect(x, y, w, h, bg)
    draw_text(img, x + 8, y + (h - 7 * sx) // 2, text, sx, sx, fg)


def panel(img, x, y, w, h, scene, kicker, kcolor, lines, subs):
    img.fill_rect(x, y, w, h, PAPER)
    img.fill_rect(x, y, w, 2, NAVY)
    img.fill_rect(x, y + h - 2, w, 2, NAVY)
    img.fill_rect(x, y, 2, h, NAVY)
    img.fill_rect(x + w - 2, y, 2, h, NAVY)
    scene(img, x + 2, y + 2, w - 4, 76)
    draw_text(img, x + 10, y + 84, kicker, 2, 2, kcolor)
    ly = y + 104
    for ln in lines:
        draw_text(img, x + 10, ly, ln, 4, 5, INK, track=2)
        ly += 37
    sy = y + h - 34
    for s in subs:
        draw_text(img, x + 10, sy, s, 2, 2, (70, 64, 54))
        sy += 16


def barcode(img, x, y, w, h):
    widths = [3, 1, 2, 1, 1, 3, 2, 2, 1, 1, 2, 3, 1, 2, 1, 1, 3, 2, 1, 2,
              1, 3, 1, 1, 2, 2, 3, 1, 2, 1, 1, 3]
    cx = x
    for i, bw in enumerate(widths):
        if i % 2 == 0:
            img.fill_rect(cx, y, bw, h, WHITE)
        cx += bw + 1
        if cx > x + w:
            break


def build():
    img = Img(W, H, NAVY)
    img.fill_rect(10, 10, W - 20, H - 20, CREAM)

    # ---- masthead
    img.fill_rect(10, 10, W - 20, 86, NAVY)
    draw_text(img, 24, 22, "THE WORLD", 9, 9, WHITE)
    draw_text(img, 1000, 30, "MONDAY, 23 NOVEMBER 2026", 3, 3, GOLDL,
              align="right")
    draw_text(img, 1000, 60, "ONE DAY - ONE PAGE - FREE", 2, 2, (200, 190, 160),
              align="right")
    img.fill_rect(10, 96, W - 20, 4, GOLD)

    # ---- dateline strip
    draw_text(img, 24, 106, "ANTALYA - WASHINGTON - HORMUZ - KYIV - "
              "SERANG - NEW DELHI", 2, 2, NAVY)
    draw_text(img, 1000, 106, "NO. 327", 2, 2, NAVY, align="right")

    # ---- hero photo
    hero_scene(img, 10, 122, W - 20, 218)
    chip(img, 24, 134, 236, 30, RED, WHITE, "CLIMATE - ANTALYA")
    # date stamp (circular seal, top right of the photo)
    img.disc(946, 186, 58, CREAM)
    img.disc(946, 186, 52, NAVY)
    img.disc(946, 186, 48, CREAM)
    draw_text(img, 946, 154, "23", 5, 5, NAVY, align="center")
    draw_text(img, 946, 194, "NOV 2026", 2, 2, NAVY, track=0,
              align="center")
    # dateline pill + quote chip, bottom of the photo
    chip(img, 24, 304, 500, 28, GOLD, NAVY,
         "ANTALYA, TURKIYE - SUNDAY 22 NOV 2026")
    img.fill_rect(700, 304, 300, 28, NAVY2)
    img.star(716, 318, 9, GOLDL)
    draw_text(img, 732, 311, "'NO CONSENSUS' - KURUM", 2, 2, WHITE)

    # ---- hero headline band
    img.fill_rect(10, 340, W - 20, 118, NAVY)
    draw_text_grad(img, 24, 348, "COP31 COLLAPSES", 8, 8,
                   (255, 244, 214), (242, 178, 92), shadow=(6, 10, 18))
    draw_text(img, 24, 410, "CLIMATE TALKS FAIL IN ANTALYA", 3, 3, WHITE)
    draw_text(img, 24, 433,
              "DRAFT DROPS FOSSIL FUELS - LONGEST COP EVER, NO PACT",
              3, 3, GOLDL)

    # ---- five panels
    row1 = [(12, capitol_scene, "POLITICS - WASHINGTON", RED,
             ["DEMOCRATS", "TAKE 258"],
             ["BIGGEST HOUSE MAJORITY", "SINCE 1992 - 22 NOV 2026"]),
            (349, hormuz_scene, "GULF - HORMUZ - 22 NOV", RED2,
             ["HORMUZ", "ATTACKS SURGE"],
             ["THREE TANKERS HIT;", "IRAN CLAIMS RADAR STRIKE"]),
            (686, kyiv_scene, "UKRAINE - KYIV REGION", RED,
             ["KYIV FLAT", "HIT: 3 DEAD"],
             ["OTHERS FEARED BURIED", "IN RUBBLE - 22 NOV 2026"])]
    for x, scene, kick, kc, lines, subs in row1:
        panel(img, x, 470, 325, 220, scene, kick, kc, lines, subs)

    row2 = [(12, factory_scene, "INDONESIA - SERANG, BANTEN", RED,
             ["FACTORY FIRE: 3 DEAD,", "DOZENS MISSING"],
             ["SEARCH RESUMES MONDAY 23 NOV", "IN SERANG, INDONESIA"]),
            (518, delhi_scene, "DIPLOMACY - NEW DELHI", (24, 120, 70),
             ["SHAH MEETS MODI", "IN DELHI"],
             ["NEPAL PM'S FIRST TRIP", "ABROAD - 23 NOV 2026"])]
    for x, scene, kick, kc, lines, subs in row2:
        panel(img, x, 702, 494, 222, scene, kick, kc, lines, subs)

    # ---- footer strip
    img.fill_rect(10, 936, W - 20, 78, NAVY)
    img.fill_rect(10, 936, W - 20, 3, GOLD)
    draw_text(img, 24, 950, "ALSO:  INDIA 720/9 - RECORD IN WELLINGTON  -  "
              "LIVERPOOL 4-0 MAN UTD", 2, 2, GOLDL)
    draw_text(img, 24, 972, "SEOUL MINISTER QUITS IN AI-CHEAT ROW  -  "
              "VERSTAPPEN WINS LAS VEGAS GP", 2, 2, WHITE)
    draw_text(img, 24, 994,
              "SOURCES: AP - REUTERS - CNN - LE MONDE - DETIKNEWS",
              2, 2, (170, 164, 140))
    barcode(img, 908, 950, 92, 52)
    return img


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    os.chmod(out_dir, 0o755)
    img = build()
    path = os.path.join(out_dir, "entry.png")
    size = write_png(img, path)
    print(f"wrote {path} ({size} bytes, {img.w}x{img.h})")


if __name__ == "__main__":
    main()
