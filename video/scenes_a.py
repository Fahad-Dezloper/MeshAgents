"""Scenes 1-3 (hook, clash, enter) plus shared helpers."""
import math
from PIL import Image
from gfx import *

CODE = (230, 230, 226); KW = PURPLE; FN = LBLUE; STR = GREEN; CM = DIM
A_COL = LBLUE; B_COL = PURPLE; C_COL = PINK


class TM:
    """scene-local timing: T.t('c1') = start of that sentence, T.e('c1') = end of it"""
    def __init__(self, sc):
        self.sc = sc; self.d = {s["key"]: s for s in sc["sentences"]}
        self.length = sc["length"]
    def t(self, k, off=0.0): return self.d[k]["t"] + off
    def e(self, k, off=0.0): return self.d[k]["t"] + self.d[k]["dur"] + off


def P(c, t, t0, cx, cy, d=0.55, dy=26, back=True, s0=0.92):
    k = prog(t, t0, d)
    sc = s0 + (1 - s0) * (e_back(k) if back else e_out(k))
    return c.push(scale=sc, cx=cx, cy=cy, alpha=e_out(min(1, k * 1.7)), dy=(1 - e_out(k)) * dy)


def typed(rows, n):
    """rows: list of (runs, bg). returns truncated rows and the (row, chars) cursor."""
    out, left = [], n
    for runs, bg in rows:
        if left <= 0: break
        cut = []
        for s, col in runs:
            if left <= 0: break
            cut.append((s[:int(left)], col)); left -= len(s)
        out.append((cut, bg))
    return out, left <= 0


def code_block(c, x, y, rows, size=32, lh=46, w=700, cursor=None, alpha=1.0, pad=10):
    for i, (runs, bg) in enumerate(rows):
        cy = y + i * lh + lh / 2
        if bg is not None: c.rect(x - pad, cy - lh / 2 + 2, w, lh - 4, 8, fill=bg, alpha=alpha * 0.22)
        c.runs(x, cy, runs, size, alpha=alpha)
    if cursor is not None and rows:
        i = len(rows) - 1; cx = x + sum(tw(s, size, "r", True) for s, _ in rows[-1][0])
        c.rect(cx + 2, y + i * lh + 6, tw("m", size, "r", True) * 0.6, lh - 12, 2, fill=WHITE, alpha=alpha * cursor)


def blink(t): return 1.0 if (t * 1.8) % 1.0 < 0.6 else 0.0


def file_card(c, x, y, w, h, name, alpha=1.0, outline=BORDER, glowc=None, gl=0.5):
    if glowc: c.glow(x, y, w, h, glowc, gl, 34, r=18, alpha=alpha)
    c.rect(x, y, w, h, 18, fill=PANEL, outline=outline, width=3 if glowc else 2, alpha=alpha)
    c.text(x + 26, y + 34, name, 30, MUTED, "m", mono=True, alpha=alpha)
    c.line([(x + 18, y + 64), (x + w - 18, y + 64)], BORDER, 2, alpha=alpha)


def bubble(c, x, y, w, h, alpha=1.0, outline=BORDER, fill=PANEL2, tail=None):
    c.rect(x, y, w, h, 26, fill=fill, outline=outline, width=2, alpha=alpha)


def shake(t, t0, d=0.55, amp=9):
    k = prog(t, t0, d)
    if k <= 0 or k >= 1: return 0.0, 0.0
    f = (1 - k) * amp
    return math.sin(t * 70) * f, math.cos(t * 83) * f * 0.6


def dashed(c, p0, p1, color, width=4, dash=22, gap=16, alpha=1.0, prog_=1.0, off=0.0):
    L = math.dist(p0, p1) * prog_
    if L <= 0: return
    ux, uy = (p1[0] - p0[0]) / math.dist(p0, p1), (p1[1] - p0[1]) / math.dist(p0, p1)
    d = -off % (dash + gap) - (dash + gap)
    while d < L:
        a, b = max(d, 0), min(d + dash, L)
        if b > a: c.line([(p0[0] + ux * a, p0[1] + uy * a), (p0[0] + ux * b, p0[1] + uy * b)], color, width, alpha=alpha)
        d += dash + gap


# ------------------------------------------------------------------ 1 HOOK
def scene_hook(c, t, T, head="Two AI coding helpers."):
    # headline
    words = [(w_, WHITE) for w_ in head.split()]
    x = 960 - tw(head, 92, "b") / 2
    for i, (wd, col) in enumerate(words):
        k = prog(t, 0.25 + i * 0.12, 0.5)
        with c.push(1, 0, 0, e_out(k), dy=(1 - e_out(k)) * 30):
            c.text(x, 150, wd, 92, col, "b")
        x += tw(wd + " ", 92, "b")
    k = prog(t, 0.85, 0.6)
    with c.push(1, 0, 0, e_out(k), dy=(1 - e_out(k)) * 30):
        c.text(960, 255, "One project.", 92, GREEN, "b", anchor="m")

    ya = 500
    for cx, col, letter, ph, t0 in [(560, A_COL, "A", 0.0, 0.6), (1360, B_COL, "B", 1.7, 0.8)]:
        k = prog(t, t0, 0.7)
        with P(c, t, t0, cx, ya, 0.7, 40, True, 0.6):
            avatar(c, cx, ya, 230, col, letter, "idle", t, glow=0.5 * e_out(k), phase=ph)
        c.text(cx, ya + 250, f"Helper {letter}", 44, WHITE, "s", anchor="m", alpha=e_out(prog(t, t0 + 0.4, 0.5)))

    # the missing link between them
    t2 = T.t("h2", 0.15)
    k = prog(t2, 0, 1)
    k = prog(t, t2, 0.9)
    dashed(c, (700, ya - 20), (820, ya - 20), DIM, 5, 16, 14, alpha=prog(t, 0.9, 0.6), prog_=1, off=t * 10)
    dashed(c, (1100, ya - 20), (1220, ya - 20), DIM, 5, 16, 14, alpha=prog(t, 0.9, 0.6), prog_=1, off=-t * 10)
    ge = e_back(prog(t, t2, 0.7))
    with c.push(max(ge, 0.001), 960, ya - 20, e_out(prog(t, t2, 0.4))):
        # crossed eye: "cannot see"
        c.glow_circle(960, ya - 20, 70, RED, 0.35 + 0.15 * math.sin(t * 4))
        c.circle(960, ya - 20, 62, fill=(34, 14, 14), outline=RED, width=5)
        c.line([(922, ya - 20), (938, ya - 40), (960, ya - 48), (982, ya - 40), (998, ya - 20), (982, ya), (960, ya + 8), (938, ya), (922, ya - 20)], WHITE, 6)
        c.circle(960, ya - 20, 12, fill=WHITE)
        c.line([(924, ya - 58), (996, ya + 18)], RED, 9)
    c.text(960, 830, "They cannot see each other.", 56, MUTED, "m", anchor="m", alpha=e_out(prog(t, t2 + 0.3, 0.6)))


# ------------------------------------------------------------------ 2 CLASH
def scene_clash(c, t, T):
    t_day2 = T.t("c4", -0.35)
    d1 = 1 - e_io(prog(t, t_day2, 0.6))
    d2 = e_io(prog(t, t_day2 + 0.15, 0.7))
    sx, sy = shake(t, T.t("c3", 1.95))

    if d1 > 0.01:
        with c.push(1, 0, 0, d1, dx=sx, dy=sy):
            clash_day1(c, t, T)
    if d2 > 0.01:
        with c.push(1, 0, 0, d2):
            clash_day2(c, t, T, t_day2)


def clash_day1(c, t, T):
    t_fail = T.t("c3", 1.95)
    failed = prog(t, t_fail, 0.5)
    # red wash when it breaks
    if failed > 0: c.glow(300, 200, 1320, 500, RED, 0.18 * e_out(failed), 160, r=200)
    for cx, col, letter, ph, t0 in [(330, A_COL, "A", 0.0, 0.2), (1590, B_COL, "B", 1.7, 0.4)]:
        mood = "worried" if failed > 0.3 else ("happy" if t > T.t("c1", 0.2) else "idle")
        if letter == "B": mood = "worried" if failed > 0.3 else "idle"
        with P(c, t, t0, cx, 250, 0.7, 40, True, 0.6):
            avatar(c, cx, 245, 190, col, letter, mood, t, glow=0.4, phase=ph)
    # labels
    c.text(500, 185, "Helper A", 46, WHITE, "s", alpha=e_out(prog(t, 0.5, 0.5)))
    c.text(500, 235, "working in shop/db.py", 36, MUTED, alpha=e_out(prog(t, 0.5, 0.5)))
    c.text(1420, 185, "Helper B", 46, WHITE, "s", anchor="r", alpha=e_out(prog(t, 0.7, 0.5)))
    c.text(1420, 235, "working in shop/api.py", 36, MUTED, anchor="r", alpha=e_out(prog(t, 0.7, 0.5)))

    # card A (typed diff)
    ta = T.t("c1", 0.9)
    rowsA = [([("- ", RED), ("def ", KW), ("get_order", FN), ("(order_id):", CODE)], RED),
             ([("+ ", GREEN), ("def ", KW), ("get_order", FN), ("(order_id, ", CODE), ("tenant", ORANGE), ("):", CODE)], GREEN)]
    rows, done = typed(rowsA, (t - ta) * 24)
    with P(c, t, 0.3, 500, 550, 0.6, 30):
        hot = prog(t, ta, 0.4) * (1 - prog(t, ta + 3, 0.5))
        file_card(c, 100, 460, 800, 190, "shop/db.py", glowc=A_COL if hot > 0 else None, gl=0.3 * hot, outline=mix(BORDER, A_COL, hot))
        code_block(c, 140, 510, rows, 32, 50, 740, cursor=blink(t) if (t > ta and not done or (t - ta) < 4.2) else None)
    # card B
    tb = T.t("c2", 0.9)
    rowsB = [([("def ", KW), ("fetch_order", FN), ("(order_id):", CODE)], None),
             ([("    return ", KW), ("get_order", FN), ("(order_id)", CODE)], ORANGE)]
    rows, done = typed(rowsB, (t - tb) * 24 if t > tb else 0)
    with P(c, t, 0.45, 1420, 550, 0.6, 30):
        hot = prog(t, tb, 0.4) * (1 - prog(t, tb + 3, 0.5))
        file_card(c, 1020, 460, 800, 190, "shop/api.py", glowc=B_COL if hot > 0 else None, gl=0.3 * hot, outline=mix(BORDER, B_COL, hot))
        code_block(c, 1060, 510, rows, 32, 50, 740, cursor=blink(t) if (t > tb and (t - tb) < 4.2) else None)
    if t > tb + 2.2:
        k = prog(t, tb + 2.2, 0.5)
        c.text(1100, 678, "still the old call", 34, ORANGE, "m", alpha=e_out(k) * (1 - 0.6 * failed))
    # nobody tells anybody: dashed link with ?
    k = prog(t, T.t("c3", 0.1), 0.7)
    if k > 0:
        dashed(c, (930, 555), (1000, 555), DIM, 5, 12, 10, alpha=k, off=t * 10)
        with c.push(max(e_back(k), 0.001), 965, 555, e_out(k)):
            c.circle(965, 555, 30, fill=PANEL2, outline=DIM, width=3)
            c.text(965, 557, "?", 40, MUTED, "b", anchor="m")
    # the failing test panel
    kf = prog(t, t_fail, 0.55)
    if kf > 0:
        with c.push(0.94 + 0.06 * e_back(kf), 960, 800, e_out(min(1, kf * 1.8)), dy=(1 - e_out(kf)) * 40):
            c.glow(260, 710, 1400, 185, RED, 0.5, 40, r=22)
            c.rect(260, 710, 1400, 185, 22, fill=(26, 12, 12), outline=RED, width=3)
            cross(c, 340, 800, 34, RED, e_out(prog(t, t_fail + 0.2, 0.5)))
            c.text(410, 745, "FAILED  test_orders.py::test_get_order", 36, RED, "s", mono=True)
            c.text(410, 807, "TypeError: get_order() missing 1 required", 34, WHITE, "r", mono=True)
            c.text(410, 853, "positional argument: 'tenant'", 34, WHITE, "r", mono=True)
    else:
        k = prog(t, T.t("c3", 0.9), 0.6)
        if k > 0 and False: pass
        kk = prog(t, T.t("c1", 0.4), 0.7)
        c.text(960, 800, "Same project. Same time. Nobody tells anybody.", 46, MUTED, "m", anchor="m",
               alpha=e_out(prog(t, T.t("c3", 0.1), 0.6)) * (1 - e_out(prog(t, t_fail - 0.2, 0.3))))


def clash_day2(c, t, T, t0):
    ts = t0 + 0.9
    # "next day" banner
    k = prog(t, t0 + 0.3, 0.6)
    with c.push(1, 0, 0, e_out(k), dy=(1 - e_out(k)) * -20):
        pill(c, 960, 100, "The next day", 48, WHITE, (36, 36, 34), padx=40, h=84, anchor="m", outline=BORDER)

    # user's old rule (yesterday) - left
    kk = prog(t, t0 + 0.7, 0.7)
    fade = 1 - 0.45 * e_io(prog(t, T.t("c4", 1.8), 1.0))
    with P(c, t, t0 + 0.7, 480, 320, 0.7, 30):
        c.rect(100, 190, 760, 250, 28, fill=PANEL2, outline=BORDER, width=2, alpha=fade)
        c.text(140, 255, "You told the first helper:", 38, MUTED, "m", alpha=fade)
        c.text(140, 330, "“Never use sqlite.", 54, WHITE, "b", alpha=fade)
        c.text(140, 392, "The server is read-only.”", 54, WHITE, "b", alpha=fade)
    kl = prog(t, T.t("c4", 1.6), 0.7)
    with c.push(1, 0, 0, e_out(kl), dy=(1 - e_out(kl)) * 20):
        c.text(480, 520, "Nobody passed it on.", 48, ORANGE, "s", anchor="m")

    # new helper C - right
    with P(c, t, t0 + 0.9, 1400, 330, 0.7, 40, True, 0.6):
        avatar(c, 1400, 320, 190, C_COL, "C", "blank" if t < T.t("c5", 1.6) else "idle", t, glow=0.35, phase=0.8)
    c.text(1590, 250, "New helper", 46, WHITE, "s", alpha=e_out(prog(t, t0 + 1.2, 0.5)))
    c.text(1590, 300, "knows nothing", 36, MUTED, alpha=e_out(prog(t, t0 + 1.2, 0.5)))

    tc = T.t("c5", 1.9)
    rows = [([("# store orders", CM)], None), ([("import ", KW), ("sqlite3", ORANGE)], RED)]
    r, done = typed(rows, (t - tc) * 22 if t > tc else 0)
    bad = prog(t, tc + 1.1, 0.5)
    with P(c, t, t0 + 1.1, 1400, 630, 0.6, 30):
        file_card(c, 1000, 540, 820, 190, "shop/db.py", glowc=RED if bad > 0 else None, gl=0.45 * bad, outline=mix(BORDER, RED, bad))
        code_block(c, 1040, 590, r, 34, 54, 760, cursor=blink(t) if (t > tc and (t - tc) < 2.6) else None)
    if bad > 0:
        with c.push(0.9 + 0.1 * e_back(bad), 1410, 810, e_out(bad)):
            cross(c, 1060, 810, 30, RED, bad)
            c.text(1110, 810, "Breaks: the server is read-only", 38, RED, "s")


# ------------------------------------------------------------------ 3 ENTER
def notebook(c, cx, cy, s=1.0, t=0.0, glow=0.6):
    w, h = 250 * s, 310 * s
    c.glow(cx - w / 2, cy - h / 2, w, h, GREEN, glow, 60 * s, r=28 * s)
    c.rect(cx - w / 2, cy - h / 2, w, h, 28 * s, fill=(16, 38, 32), outline=GREEN, width=4)
    for i in range(6):
        yy = cy - h / 2 + 52 * s + i * 40 * s
        c.rect(cx - w / 2 - 12 * s, yy - 9 * s, 30 * s, 18 * s, 9 * s, fill=(10, 24, 20), outline=GREEN, width=3)
    for i, ww in enumerate([0.55, 0.7, 0.45, 0.62, 0.38]):
        yy = cy - h / 2 + 70 * s + i * 46 * s
        pulse = 0.55 + 0.45 * math.sin(t * 3 + i)
        c.rect(cx - w / 2 + 50 * s, yy, w * ww * 0.8, 12 * s, 6 * s, fill=GREEN, alpha=0.35 + 0.35 * pulse)


def scene_enter(c, t, T):
    hub = (960, 600)
    # orbiting mini nodes (the graph)
    orbit = [("File", GREEN), ("Decision", PURPLE), ("Task", LBLUE), ("Function", PINK), ("File", GREEN), ("Decision", PURPLE)]
    ka = prog(t, 1.0, 1.0)
    for i, (nm, col) in enumerate(orbit):
        ang = t * 0.35 + i * math.tau / len(orbit)
        r = 245 + 12 * math.sin(t + i)
        x, y = hub[0] + math.cos(ang) * r * 1.35, hub[1] + math.sin(ang) * r * 0.62
        c.line([hub, (x, y)], col, 3, alpha=0.28 * ka)
        c.glow_circle(x, y, 18, col, 0.6 * ka)
        c.circle(x, y, 15, fill=col, alpha=ka)
    # helpers left and right feed the notebook
    for cx, col, letter, ph, mood in [(330, A_COL, "A", 0.0, "happy"), (1590, B_COL, "B", 1.7, "happy")]:
        with P(c, t, 0.5, cx, 600, 0.7, 40, True, 0.6):
            avatar(c, cx, 590, 190, col, letter, mood, t, glow=0.35, phase=ph)
        sgn = 1 if cx < 960 else -1
        p0 = (cx + sgn * 120, 600); p1 = (hub[0] - sgn * 150, 600)
        kk = prog(t, 1.0, 0.8)
        if kk > 0:
            c.line([p0, (lerp(p0[0], p1[0], e_io(kk)), 600)], col, 4, alpha=0.6)
            if kk >= 1:
                for j in range(3):
                    u = ((t * 0.5 + j / 3 + (0.3 if letter == "B" else 0)) % 1.0)
                    px = lerp(p0[0], p1[0], u)
                    c.glow_circle(px, 600, 10, col, 0.9); c.circle(px, 600, 7, fill=WHITE)
    with P(c, t, 0.7, hub[0], hub[1], 0.8, 30, True, 0.7):
        notebook(c, hub[0], hub[1] - 10, 1.0, t, 0.5 + 0.2 * math.sin(t * 2))
    # name + tagline
    k = prog(t, T.t("e1", 0.0), 0.7)
    with c.push(1 + 0.03 * (1 - e_out(k)), 960, 150, e_out(k), dy=(1 - e_out(k)) * 26):
        x0 = 960 - tw("MeshAgents", 124, "h") / 2
        c.text(x0, 150, "Mesh", 124, WHITE, "h")
        c.text(x0 + tw("Mesh", 124, "h"), 150, "Agents", 124, GREEN, "h")
    k = prog(t, T.t("e2", 0.0), 0.7)
    with c.push(1, 0, 0, e_out(k), dy=(1 - e_out(k)) * 20):
        c.text(960, 262, "A shared memory for AI coding helpers", 56, WHITE, "m", anchor="m")
    # pills
    k = prog(t, T.t("e3", 0.0), 0.6)
    k2 = prog(t, T.t("e3", 1.7), 0.6)
    with c.push(1, 0, 0, e_out(k), dy=(1 - e_out(k)) * 20):
        a, w1 = pill(c, 960 - 20, 850, "Runs quietly as a Claude Code plugin", 40, WHITE, (26, 36, 34), padx=34, h=76, outline=GREEN, anchor="r")
    with c.push(1, 0, 0, e_out(k2), dy=(1 - e_out(k2)) * 20):
        pill(c, 960 + 20, 850, "Nothing to type", 40, BG, GREEN, padx=34, h=76, anchor="l")
