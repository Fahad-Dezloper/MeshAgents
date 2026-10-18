"""Tiny 2D drawing toolkit on Pillow: supersampled canvas, transforms, alpha shapes, glows, text, easing."""
import math, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

W, H, S = 1920, 1080, 2
BG = (11, 11, 10)
WHITE = (244, 244, 242); MUTED = (161, 161, 156); DIM = (96, 96, 92)
PANEL = (22, 22, 21); PANEL2 = (28, 28, 27); BORDER = (46, 46, 44)
GREEN = (52, 211, 153); BLUE = (59, 130, 246); LBLUE = (110, 168, 255)
ORANGE = (245, 158, 11); RED = (239, 68, 68); PURPLE = (192, 132, 252); PINK = (244, 114, 182)

# ---------- easing ----------
def clamp01(x): return 0.0 if x < 0 else 1.0 if x > 1 else x
def prog(t, t0, d): return clamp01((t - t0) / d) if d > 0 else (1.0 if t >= t0 else 0.0)
def e_io(x): x = clamp01(x); return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2
def e_out(x): x = clamp01(x); return 1 - (1 - x) ** 3
def e_in(x): x = clamp01(x); return x ** 3
def e_back(x, k=1.9):
    x = clamp01(x); return 1 + (k + 1) * (x - 1) ** 3 + k * (x - 1) ** 2
def e_spring(x):
    x = clamp01(x)
    return 1.0 if x >= 1 else 1 - math.exp(-7 * x) * math.cos(11 * x)
def lerp(a, b, k): return a + (b - a) * k
def mix(c1, c2, k): return tuple(int(round(lerp(a, b, k))) for a, b in zip(c1, c2))

# ---------- fonts ----------
_fonts = {}
SANS = "/System/Library/Fonts/SFNS.ttf"; MONO = "/System/Library/Fonts/Menlo.ttc"
WEIGHTS = {"r": "Regular", "m": "Medium", "s": "Semibold", "b": "Bold", "h": "Heavy"}
def font(size, w="r", mono=False):
    key = (int(round(size)), w, mono)
    f = _fonts.get(key)
    if f is None:
        if mono:
            f = ImageFont.truetype(MONO, key[0], index=1 if w in "bhs" else 0)
        else:
            f = ImageFont.truetype(SANS, key[0]); f.set_variation_by_name(WEIGHTS[w])
        _fonts[key] = f
    return f

def tw(text, size, w="r", mono=False):
    """text width in 1080p units"""
    return font(size * S, w, mono).getlength(text) / S

def wrap(text, size, maxw, w="r", mono=False):
    words, lines, cur = text.split(), [], ""
    for wd in words:
        t = (cur + " " + wd).strip()
        if tw(t, size, w, mono) <= maxw or not cur: cur = t
        else: lines.append(cur); cur = wd
    if cur: lines.append(cur)
    return lines

# ---------- background ----------
_bg = None
def background():
    global _bg
    if _bg is None:
        pad = 60
        w, h = (W + pad * 2) * S, (H + pad * 2) * S
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        arr = np.zeros((h, w, 3), np.float32) + np.array(BG, np.float32)
        def blob(cx, cy, r, col, a):
            d = np.sqrt((xx - cx * S) ** 2 + (yy - cy * S) ** 2) / (r * S)
            k = np.clip(1 - d, 0, 1) ** 2 * a
            arr[:] += k[..., None] * (np.array(col, np.float32) - arr)
        blob(300 + pad, 150 + pad, 900, GREEN, 0.10)
        blob(1700 + pad, 950 + pad, 1000, BLUE, 0.11)
        blob(1000 + pad, 540 + pad, 700, (40, 40, 60), 0.12)
        step = 48 * S
        mask = ((xx % step) < 2.2 * S) & ((yy % step) < 2.2 * S)
        arr[mask] += 9
        _bg = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")
    return _bg

def bg_crop(t):
    pad = 60
    dx = int((pad + 24 * math.sin(t * 0.11)) * S); dy = int((pad + 16 * math.cos(t * 0.09)) * S)
    return background().crop((dx, dy, dx + W * S, dy + H * S))

# ---------- canvas ----------
class Canvas:
    def __init__(self, img):
        self.img = img; self.d = ImageDraw.Draw(img)
        self.s, self.tx, self.ty, self.a = 1.0, 0.0, 0.0, 1.0
        self.stack = []

    # transform stack: local -> device
    def push(self, scale=1.0, cx=0.0, cy=0.0, alpha=1.0, dx=0.0, dy=0.0):
        self.stack.append((self.s, self.tx, self.ty, self.a))
        self.tx += self.s * (cx * (1 - scale) + dx); self.ty += self.s * (cy * (1 - scale) + dy)
        self.s *= scale; self.a *= alpha
        return self
    def pop(self): self.s, self.tx, self.ty, self.a = self.stack.pop()
    def __enter__(self): return self
    def __exit__(self, *e): self.pop()

    def X(self, x): return (x * self.s + self.tx) * S
    def Y(self, y): return (y * self.s + self.ty) * S
    def L(self, v): return v * self.s * S

    def _fill(self, bbox, drawfn, color, alpha):
        """paste `color` through a mask drawn by drawfn(draw, ox, oy); bbox in device px"""
        x0, y0, x1, y1 = [int(math.floor(v)) for v in bbox]; x1 = int(math.ceil(bbox[2])); y1 = int(math.ceil(bbox[3]))
        x0 = max(x0, 0); y0 = max(y0, 0); x1 = min(x1, W * S); y1 = min(y1, H * S)
        if x1 <= x0 or y1 <= y0: return
        m = Image.new("L", (x1 - x0, y1 - y0), 0)
        drawfn(ImageDraw.Draw(m), x0, y0, int(255 * alpha))
        self.img.paste(color, (x0, y0), m)

    def rect(self, x, y, w, h, r=0, fill=None, outline=None, width=2, alpha=1.0):
        a = alpha * self.a
        if a <= 0.004: return
        X0, Y0, X1, Y1 = self.X(x), self.Y(y), self.X(x + w), self.Y(y + h)
        R = self.L(r); wd = max(1, int(round(self.L(width))))
        if fill is not None:
            if a > .995: self.d.rounded_rectangle((X0, Y0, X1, Y1), R, fill=fill)
            else: self._fill((X0 - 1, Y0 - 1, X1 + 2, Y1 + 2), lambda d, ox, oy, v: d.rounded_rectangle((X0 - ox, Y0 - oy, X1 - ox, Y1 - oy), R, fill=v), fill, a)
        if outline is not None:
            self._fill((X0 - 2, Y0 - 2, X1 + 3, Y1 + 3), lambda d, ox, oy, v: d.rounded_rectangle((X0 - ox, Y0 - oy, X1 - ox, Y1 - oy), R, outline=v, width=wd), outline, a)

    def circle(self, x, y, r, fill=None, outline=None, width=2, alpha=1.0):
        a = alpha * self.a
        if a <= 0.004 or r <= 0: return
        cx, cy, R = self.X(x), self.Y(y), self.L(r); wd = max(1, int(round(self.L(width))))
        box = (cx - R - 2, cy - R - 2, cx + R + 3, cy + R + 3)
        if fill is not None:
            self._fill(box, lambda d, ox, oy, v: d.ellipse((cx - R - ox, cy - R - oy, cx + R - ox, cy + R - oy), fill=v), fill, a)
        if outline is not None:
            self._fill(box, lambda d, ox, oy, v: d.ellipse((cx - R - ox, cy - R - oy, cx + R - ox, cy + R - oy), outline=v, width=wd), outline, a)

    def ellipse(self, x, y, rx, ry, fill, alpha=1.0):
        a = alpha * self.a
        if a <= 0.004 or rx <= 0 or ry <= 0: return
        cx, cy, RX, RY = self.X(x), self.Y(y), self.L(rx), self.L(ry)
        self._fill((cx - RX - 2, cy - RY - 2, cx + RX + 3, cy + RY + 3), lambda d, ox, oy, v: d.ellipse((cx - RX - ox, cy - RY - oy, cx + RX - ox, cy + RY - oy), fill=v), fill, a)

    def line(self, pts, color, width=4, alpha=1.0, cap=True):
        a = alpha * self.a
        if a <= 0.004: return
        P = [(self.X(x), self.Y(y)) for x, y in pts]; wd = self.L(width)
        xs = [p[0] for p in P]; ys = [p[1] for p in P]; m = wd + 3
        def fn(d, ox, oy, v):
            Q = [(x - ox, y - oy) for x, y in P]
            d.line(Q, fill=v, width=int(round(wd)), joint="curve")
            if cap:
                for q in (Q[0], Q[-1]): d.ellipse((q[0] - wd / 2, q[1] - wd / 2, q[0] + wd / 2, q[1] + wd / 2), fill=v)
        self._fill((min(xs) - m, min(ys) - m, max(xs) + m, max(ys) + m), fn, color, a)

    def poly(self, pts, fill, alpha=1.0):
        a = alpha * self.a
        if a <= 0.004: return
        P = [(self.X(x), self.Y(y)) for x, y in pts]
        xs = [p[0] for p in P]; ys = [p[1] for p in P]
        self._fill((min(xs) - 2, min(ys) - 2, max(xs) + 3, max(ys) + 3), lambda d, ox, oy, v: d.polygon([(x - ox, y - oy) for x, y in P], fill=v), fill, a)

    def glow(self, x, y, w, h, color, strength=0.5, blur=30, r=None, alpha=1.0):
        """soft glow behind a rounded rect (x,y,w,h) in local coords"""
        a = alpha * self.a * strength
        if a <= 0.004: return
        k = 4
        pad = self.L(blur) * 3
        X0, Y0, X1, Y1 = self.X(x), self.Y(y), self.X(x + w), self.Y(y + h)
        bx0, by0, bx1, by1 = max(0, X0 - pad), max(0, Y0 - pad), min(W * S, X1 + pad), min(H * S, Y1 + pad)
        if bx1 <= bx0 or by1 <= by0: return
        sw, sh = int((bx1 - bx0) / k) + 1, int((by1 - by0) / k) + 1
        m = Image.new("L", (sw, sh), 0)
        R = (self.L(r) if r is not None else min(X1 - X0, Y1 - Y0) / 2) / k
        ImageDraw.Draw(m).rounded_rectangle(((X0 - bx0) / k, (Y0 - by0) / k, (X1 - bx0) / k, (Y1 - by0) / k), R, fill=255)
        m = m.filter(ImageFilter.GaussianBlur(self.L(blur) / k)).point(lambda v: int(v * min(a, 1)))
        m = m.resize((int(bx1 - bx0), int(by1 - by0)), Image.BILINEAR)
        self.img.paste(color, (int(bx0), int(by0)), m)

    def glow_circle(self, x, y, r, color, strength=0.6, blur=None, alpha=1.0):
        self.glow(x - r, y - r, 2 * r, 2 * r, color, strength, blur if blur is not None else r * 0.8, r=r, alpha=alpha)

    def text(self, x, y, s, size, color=WHITE, w="r", mono=False, anchor="l", alpha=1.0, va="m"):
        a = alpha * self.a
        if a <= 0.004 or not s: return
        f = font(size * self.s * S, w, mono)
        an = {"l": "l", "m": "m", "r": "r"}[anchor] + {"m": "m", "s": "s", "t": "a"}[va]
        X, Y = self.X(x), self.Y(y)
        bb = f.getbbox(s, anchor=an)
        box = (X + bb[0] - 3, Y + bb[1] - 3, X + bb[2] + 4, Y + bb[3] + 4)
        if a > .995:
            self.d.text((X, Y), s, font=f, fill=color, anchor=an)
        else:
            self._fill(box, lambda d, ox, oy, v: d.text((X - ox, Y - oy), s, font=f, fill=v, anchor=an), color, a)

    def runs(self, x, y, runs, size, w="r", mono=True, alpha=1.0, anchor="l"):
        """runs: [(text, color)], drawn left to right"""
        total = sum(tw(t, size, w, mono) for t, _ in runs)
        cx = x - (total / 2 if anchor == "m" else total if anchor == "r" else 0)
        for t, c in runs:
            self.text(cx, y, t, size, c, w, mono, "l", alpha); cx += tw(t, size, w, mono)

    def image(self, im, x, y, w, h, r=0, alpha=1.0):
        a = alpha * self.a
        if a <= 0.004: return
        X0, Y0, X1, Y1 = int(self.X(x)), int(self.Y(y)), int(self.X(x + w)), int(self.Y(y + h))
        pw, ph = X1 - X0, Y1 - Y0
        key = (id(im), pw, ph)
        rs = _imgcache.get(key)
        if rs is None:
            rs = im.resize((pw, ph), Image.LANCZOS).convert("RGB"); _imgcache[key] = rs
        m = Image.new("L", (pw, ph), 0)
        ImageDraw.Draw(m).rounded_rectangle((0, 0, pw - 1, ph - 1), self.L(r), fill=int(255 * a))
        self.img.paste(rs, (X0, Y0), m)

_imgcache = {}

def new_canvas(t):
    return Canvas(bg_crop(t).copy())

def finish(c):
    return c.img.resize((W, H), Image.LANCZOS)

# ---------- shared widgets ----------
def check(c, x, y, size, color=GREEN, p=1.0, width=None):
    """animated check mark inside a circle of radius size"""
    width = width or size * 0.18
    c.circle(x, y, size, fill=mix(BG, color, 0.18), outline=color, width=width * 0.6, alpha=min(1, p * 2))
    pts = [(x - size * .42, y + size * .02), (x - size * .1, y + size * .34), (x + size * .46, y - size * .3)]
    k = e_out(p)
    seg1 = math.dist(pts[0], pts[1]); seg2 = math.dist(pts[1], pts[2]); tot = seg1 + seg2; d = k * tot
    if d <= seg1:
        q = [pts[0], (lerp(pts[0][0], pts[1][0], d / seg1), lerp(pts[0][1], pts[1][1], d / seg1))]
    else:
        f = (d - seg1) / seg2
        q = [pts[0], pts[1], (lerp(pts[1][0], pts[2][0], f), lerp(pts[1][1], pts[2][1], f))]
    if k > 0.01: c.line(q, color, width)

def cross(c, x, y, size, color=RED, p=1.0, width=None):
    width = width or size * 0.18
    c.circle(x, y, size, fill=mix(BG, color, 0.18), outline=color, width=width * 0.6, alpha=min(1, p * 2))
    k = e_out(p); s = size * 0.38
    if k > .01:
        c.line([(x - s, y - s), (x - s + 2 * s * min(1, k * 2), y - s + 2 * s * min(1, k * 2))], color, width)
        if k > .5: c.line([(x + s, y - s), (x + s - 2 * s * (k * 2 - 1), y - s + 2 * s * (k * 2 - 1))], color, width)

def pill(c, x, y, text, size, fg, bgc, padx=22, h=None, w="s", alpha=1.0, anchor="l", outline=None):
    h = h or size * 1.7; wd = tw(text, size, w) + padx * 2
    x0 = x - (wd / 2 if anchor == "m" else wd if anchor == "r" else 0)
    c.rect(x0, y - h / 2, wd, h, h / 2, fill=bgc, outline=outline, width=2, alpha=alpha)
    c.text(x0 + wd / 2, y, text, size, fg, w, anchor="m", alpha=alpha)
    return x0, wd

def window(c, x, y, w, h, title="", alpha=1.0, r=16):
    c.rect(x, y, w, h, r, fill=PANEL, outline=BORDER, width=2, alpha=alpha)
    c.rect(x, y, w, 52, r, fill=PANEL2, alpha=alpha)
    c.rect(x, y + 30, w, 22, 0, fill=PANEL2, alpha=alpha)
    for i, col in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        c.circle(x + 28 + i * 26, y + 26, 8, fill=col, alpha=alpha * .9)
    if title: c.text(x + w / 2, y + 26, title, 26, MUTED, "m", mono=True, anchor="m", alpha=alpha)

def avatar(c, cx, cy, u, color, letter, mood="idle", t=0.0, alpha=1.0, glow=0.0, phase=0.0):
    """Original robot-ish helper. u = head width. moods: idle, worried, happy, blank, work"""
    bob = math.sin(t * 2.2 + phase) * u * 0.02
    cy = cy + bob
    dark = mix(color, (0, 0, 0), 0.55); light = mix(color, (255, 255, 255), 0.35)
    hh = u * 0.82
    if glow > 0: c.glow_circle(cx, cy, u * 0.8, color, glow * 0.6, u * 0.4, alpha=alpha)
    # body
    c.rect(cx - u * 0.36, cy + hh * 0.5 + u * 0.04, u * 0.72, u * 0.5, u * 0.2, fill=dark, alpha=alpha)
    c.circle(cx, cy + hh * 0.5 + u * 0.3, u * 0.14, fill=color, alpha=alpha)
    c.text(cx, cy + hh * 0.5 + u * 0.3, letter, u * 0.19, BG, "h", anchor="m", alpha=alpha)
    # antenna
    c.line([(cx, cy - hh * 0.5), (cx, cy - hh * 0.5 - u * 0.17)], light, u * 0.04, alpha=alpha)
    pulse = 0.5 + 0.5 * math.sin(t * 5 + phase)
    ac = {"worried": RED, "happy": GREEN}.get(mood, light)
    c.circle(cx, cy - hh * 0.5 - u * 0.2, u * 0.065, fill=ac, alpha=alpha)
    if mood in ("worried", "happy"): c.glow_circle(cx, cy - hh * 0.5 - u * 0.2, u * 0.12, ac, 0.5 + 0.4 * pulse, alpha=alpha)
    # head
    c.rect(cx - u / 2, cy - hh / 2, u, hh, u * 0.26, fill=color, alpha=alpha)
    c.rect(cx - u / 2, cy - hh / 2, u, hh * 0.45, u * 0.26, fill=light, alpha=alpha * 0.28)
    # face plate
    c.rect(cx - u * 0.39, cy - hh * 0.3, u * 0.78, hh * 0.6, u * 0.16, fill=(12, 14, 20), alpha=alpha)
    ex = u * 0.2; ey = cy - hh * 0.07
    blink = 1.0
    ph = (t * 0.55 + phase * 0.3) % 1.0
    if ph > 0.96: blink = 0.12
    ec = WHITE if mood != "worried" else (255, 220, 220)
    if mood == "happy":
        for sx in (-1, 1):
            c.line([(cx + sx * ex - u * .09, ey + u * .04), (cx + sx * ex, ey - u * .06), (cx + sx * ex + u * .09, ey + u * .04)], ec, u * 0.045, alpha=alpha)
    elif mood == "blank":
        for sx in (-1, 1):
            c.line([(cx + sx * ex - u * .08, ey), (cx + sx * ex + u * .08, ey)], MUTED, u * 0.045, alpha=alpha)
    else:
        r = u * (0.075 if mood != "worried" else 0.09)
        for sx in (-1, 1):
            c.ellipse(cx + sx * ex, ey, r, r * blink, ec, alpha=alpha)
        if mood == "worried":
            for sx in (-1, 1):
                c.line([(cx + sx * ex - sx * u * .1, ey - u * .17 - sx * u * .0), (cx + sx * ex + sx * u * .09, ey - u * .12 + u * .06)], ec, u * .035, alpha=alpha)
    my = cy + hh * 0.19
    if mood == "happy":
        c.line([(cx - u * .1, my - u * .02), (cx - u * .04, my + u * .04), (cx + u * .04, my + u * .04), (cx + u * .1, my - u * .02)], ec, u * .04, alpha=alpha)
    elif mood == "worried":
        c.line([(cx - u * .09, my + u * .04), (cx - u * .03, my - u * .01), (cx + u * .03, my + u * .03), (cx + u * .09, my - u * .0)], ec, u * .04, alpha=alpha)
        dy = (t * 0.9 + phase) % 1.0
        c.ellipse(cx + u * 0.5, cy - hh * 0.3 + dy * u * 0.35, u * .05, u * .075, LBLUE, alpha=alpha * (1 - dy) * .9)
    else:
        c.line([(cx - u * .07, my), (cx + u * .07, my)], MUTED if mood == "blank" else ec, u * .04, alpha=alpha)

def subtitle(c, text, a):
    if a <= 0.01 or not text: return
    size = 40; maxw = 1480
    lines = wrap(text, size, maxw, "m")
    if len(lines) >= 2:  # balance into two lines of similar width
        ws = text.split(); best = None
        for i in range(1, len(ws)):
            la, lb = " ".join(ws[:i]), " ".join(ws[i:])
            m_ = max(tw(la, size, "m"), tw(lb, size, "m"))
            if best is None or m_ < best[0]: best = (m_, [la, lb])
        if best[0] <= maxw * 1.1: lines = best[1]
    lh = 56; wd = max(tw(l, size, "m") for l in lines) + 70; h = lh * len(lines) + 30
    y1 = H - 36; y0 = y1 - h
    c.rect((W - wd) / 2, y0, wd, h, 22, fill=(0, 0, 0), alpha=0.66 * a)
    for i, l in enumerate(lines):
        c.text(W / 2, y0 + 15 + lh * (i + .5), l, size, WHITE, "m", anchor="m", alpha=a)
