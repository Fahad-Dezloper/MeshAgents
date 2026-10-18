"""Scenes 4-8: split screen, board, graph, numbers, honest, try-it."""
import math, os
from PIL import Image
from gfx import *
from scenes_a import *

HERE = os.path.dirname(os.path.abspath(__file__))
IMG = {}
def shot(name):
    if name not in IMG:
        IMG[name] = Image.open(os.path.join(HERE, "..", "docs", "img", name)).convert("RGB")
    return IMG[name]


# ------------------------------------------------------------------ 4 SPLIT SCREEN
def msg_card(c, x, y, w, title, lines, size, color, alpha=1.0, glow=0.4, hl=None, lh=38):
    h = 58 + len(lines) * lh + 24
    c.glow(x, y, w, h, color, glow, 36, r=20, alpha=alpha)
    c.rect(x, y, w, h, 20, fill=(18, 20, 26), outline=color, width=3, alpha=alpha)
    c.text(x + 24, y + 34, title, 32, color, "s", alpha=alpha)
    for i, ln in enumerate(lines):
        yy = y + 58 + i * lh + lh / 2
        if hl is not None and i in hl:
            c.rect(x + 12, yy - lh / 2 + 2, w - 24, lh - 4, 8, fill=GREEN, alpha=alpha * 0.2)
        c.text(x + 24, yy, ln, size, WHITE, "r", mono=True, alpha=alpha)
    return h


def result_panel(c, t, t0, x0, w, y, h, col, fill, glyph, head, sub, l1, l2, ghost=False):
    k = prog(t, t0, 0.55)
    if k <= 0: return
    with c.push(0.94 + 0.06 * e_back(k), x0 + w / 2, y + h / 2, e_out(min(1, k * 1.8)), dy=(1 - e_out(k)) * 30):
        c.glow(x0, y, w, h, col, 0.45, 40, r=22)
        c.rect(x0, y, w, h, 22, fill=fill, outline=col, width=3)
        (cross if glyph == "x" else check)(c, x0 + 66, y + 70, 34, col, e_out(prog(t, t0 + 0.2, 0.5)))
        c.text(x0 + 130, y + 52, head, 36, col, "s", mono=True)
        c.text(x0 + 130, y + 104, sub, 38, WHITE, "m")
        c.text(x0 + 36, y + 178, l1, 30, WHITE, "r", mono=True)
        c.text(x0 + 36, y + 220, l2, 30, WHITE, "r", mono=True)


def half(c, t, T, left):
    x0 = 50 if left else 1010; W_ = 860
    tD = T.t("w5", -0.25)
    d1 = 1 - e_io(prog(t, tD, 0.5)); d2 = e_io(prog(t, tD + 0.2, 0.6))
    if d1 > 0.01:
        with c.push(1, 0, 0, d1): half_day1(c, t, T, left, x0, W_)
    if d2 > 0.01:
        with c.push(1, 0, 0, d2): half_day2(c, t, T, left, x0, W_, tD)


def half_day1(c, t, T, left, x0, w):
    tA = T.t("w2", 0.45)
    tW = T.t("w3", 0.35); tW2 = T.t("w3", 3.55)
    tFail = T.t("w3", 4.0); tFix = T.t("w4", 0.15); tOk = T.t("w4", 1.7)
    sx, sy = shake(t, tFail, 0.5, 6) if left else (0, 0)
    c.push(1, 0, 0, 1.0, dx=sx, dy=sy)
    failed = left and t >= tFail + 0.3
    ok = (not left) and t >= tOk
    # --- row A
    mA = "happy" if t > tA else "idle"
    if failed: mA = "worried"
    with P(c, t, 0.2, x0 + 80, 220, 0.6, 30, True, 0.6):
        avatar(c, x0 + 78, 200, 110, A_COL, "A", mA, t, glow=0.25, phase=0.0)
    hot = prog(t, tA, 0.3) * (1 - prog(t, tA + 3, 0.5))
    rowsA = [([("- ", RED), ("def ", KW), ("get_order", FN), ("(order_id):", CODE)], RED),
             ([("+ ", GREEN), ("def ", KW), ("get_order", FN), ("(order_id, ", CODE), ("tenant", ORANGE), ("):", CODE)], GREEN)]
    if t <= tA:
        rows = [([("def ", KW), ("get_order", FN), ("(order_id):", CODE)], None)]
    else:
        r2, _ = typed(rowsA[1:], (t - tA) * 26)
        rows = [rowsA[0]] + r2
    with P(c, t, 0.3, x0 + 500, 210, 0.6, 24):
        file_card(c, x0 + 150, 125, w - 150, 170, "shop/db.py", glowc=A_COL if hot > 0 else None, gl=0.3 * hot, outline=mix(BORDER, A_COL, hot))
        code_block(c, x0 + 176, 190, rows, 30, 44, w - 196, cursor=blink(t) if (t > tA and t - tA < 3) else None)
    # --- row B
    mB = "worried" if failed else ("happy" if ok else "idle")
    with P(c, t, 0.4, x0 + 80, 400, 0.6, 30, True, 0.6):
        avatar(c, x0 + 78, 395, 110, B_COL, "B", mB, t, glow=0.25, phase=1.7)
    callrow = [("  return ", KW), ("get_order", FN), ("(order_id)", CODE)]
    fixed = [("  return ", KW), ("get_order", FN), ("(order_id, ", CODE), ("tenant", GREEN), (")", CODE)]
    head_row = ([("def ", KW), ("fetch_order", FN), ("(order_id):", CODE)], None)
    tFixed = (not left) and t > tFix
    curs = None
    if tFixed:
        n = (t - tFix) * 26
        r, _ = typed([(fixed, GREEN)], max(n, 0))
        rowsB = [head_row, r[0]]
        curs = blink(t) if n < 40 else None
    else:
        rowsB = [head_row, (callrow, ORANGE if t > tW else None)]
    hotb = prog(t, tFix, .3) * (1 - prog(t, tFix + 3, .5)) if tFixed else 0
    with P(c, t, 0.45, x0 + 500, 400, 0.6, 24):
        file_card(c, x0 + 150, 320, w - 150, 170, "shop/api.py", glowc=B_COL if hotb > 0 else None, gl=0.3 * hotb, outline=mix(BORDER, B_COL, hotb))
        code_block(c, x0 + 176, 385, rowsB, 30, 44, w - 196, cursor=curs)

    # --- outcome area
    oy = 520
    p1 = e_out(prog(t, 0.9, 0.6)) * (1 - e_out(prog(t, tA + 0.6, 0.4)))
    if p1 > 0.01:
        with c.push(1, 0, 0, p1):
            if left:
                c.text(x0 + w / 2, oy + 130, "Each helper works alone.", 52, MUTED, "s", anchor="m")
            else:
                notebook(c, x0 + 130, oy + 150, 0.5, t, 0.5)
                c.text(x0 + 290, oy + 120, "One shared notebook", 52, WHITE, "s")
                c.text(x0 + 290, oy + 178, "read and written automatically", 38, MUTED, "r")
    if left:
        k = prog(t, tA + 1.2, 0.6) * (1 - e_out(prog(t, tFail, 0.3)))
        with c.push(1, 0, 0, e_out(k)):
            c.text(x0 + w / 2, oy + 90, "Nothing recorded.", 54, MUTED, "s", anchor="m")
            c.text(x0 + w / 2, oy + 160, "B cannot see what A changed.", 42, DIM, "r", anchor="m")
        result_panel(c, t, tFail, x0, w, oy, 290, RED, (26, 12, 12), "x", "FAILED  test_get_order", "A change broke B's code",
                     "TypeError: get_order() missing 1", "required positional argument: 'tenant'")
    else:
        kr = prog(t, tA + 1.3, 0.6)
        gone = e_io(prog(t, tW2, 0.3))
        gy = oy + 20
        nd = "Decision: get_order needs tenant"; nf = "shop/db.py"
        wd = tw(nd, 30, "m") + 40; wf = tw(nf, 30, "m") + 40
        with c.push(1, 0, 0, 1 - gone):
            with P(c, t, tA + 1.3, x0 + 300, gy + 30, 0.5, 14):
                c.rect(x0, gy, wd, 58, 29, fill=mix(BG, PURPLE, 0.2), outline=PURPLE, width=3)
                c.text(x0 + wd / 2, gy + 29, nd, 30, WHITE, "m", anchor="m")
                ax0 = x0 + wd + 8; ax1 = x0 + wd + 74
                c.line([(ax0, gy + 29), (ax1, gy + 29)], MUTED, 3)
                c.poly([(ax1 + 12, gy + 29), (ax1 - 4, gy + 21), (ax1 - 4, gy + 37)], MUTED)
                c.text((ax0 + ax1) / 2, gy + 6, "ABOUT", 22, MUTED, "m", mono=True, anchor="m")
                c.rect(ax1 + 16, gy, wf, 58, 29, fill=mix(BG, GREEN, 0.2), outline=GREEN, width=3)
                c.text(ax1 + 16 + wf / 2, gy + 29, nf, 30, WHITE, "m", anchor="m")
            c.text(x0 + w / 2, gy + 120, "Written into the graph. Nobody typed anything.", 36, GREEN, "m", anchor="m",
                   alpha=e_out(prog(t, tA + 1.9, 0.5)) * (1 - e_out(prog(t, tW - 0.2, 0.3))))
        mw = ["[MeshAgents] Possible collision on shop/db.py:", "- sess-A-storag is working on 'Ticket 12: ...'", "  touching shop/db.py, last edit 2s ago"]
        with c.push(1, 0, 0, 1 - gone):
            with P(c, t, tW, x0 + w / 2, oy + 190, 0.6, 40):
                msg_card(c, x0, oy + 90, w, "Helper B is told before it edits", mw, 28, ORANGE)
        if gone > 0:
            with c.push(1, 0, 0, e_io(prog(t, tW2 + 0.25, 0.3))):
                c.rect(x0, oy, w, 56, 28, fill=mix(BG, ORANGE, 0.15), outline=ORANGE, width=2)
                c.text(x0 + 28, oy + 28, "Helper B: warned before it edits", 32, ORANGE, "s")
                check(c, x0 + w - 36, oy + 28, 20, GREEN, e_out(prog(t, tW2 + 0.2, 0.4)))
            lines2 = ["[MeshAgents] You changed how shop/db.py is", "called (get_order: new required parameter", "tenant). Callers elsewhere that may now break:",
                      "- shop/api.py (session sess-B-e is working", "  in it now)"]
            with P(c, t, tW2 + 0.3, x0 + w / 2, oy + 220, 0.6, 40):
                msg_card(c, x0, oy + 76, w, "Helper A is told which callers may break", lines2, 28, RED,
                         alpha=1.0 - e_io(prog(t, tFix - 0.1, 0.5)))
        result_panel(c, t, tOk, x0, w, oy + 10, 290, GREEN, (12, 26, 20), "ok", "PASSED  test_get_order", "B adjusted its call in time",
                     "2 passed in 0.31s", "no collision, nothing redone")
    c.pop()


def half_day2(c, t, T, left, x0, w, tD):
    tC = tD + 1.3 if left else tD + 3.6
    mC = "worried" if (left and t > tD + 3.0) else ("happy" if (not left and t > tD + 5.4) else "blank")
    with P(c, t, tD + 0.4, x0 + 80, 280, 0.6, 30, True, 0.6):
        avatar(c, x0 + 78, 270, 120, C_COL, "C", mC, t, glow=0.25, phase=0.8)
    if left:
        rows = [([("# store orders", CM)], None), ([("import ", KW), ("sqlite3", ORANGE)], RED)]
        r, done = typed(rows, (t - tC) * 20 if t > tC else 0)
        hot = prog(t, tC + 1.2, 0.5)
        with P(c, t, tD + 0.5, x0 + 500, 270, 0.6, 24):
            file_card(c, x0 + 150, 190, w - 150, 170, "shop/db.py", glowc=RED if hot > 0 else None, gl=0.4 * hot, outline=mix(BORDER, RED, hot))
            code_block(c, x0 + 176, 255, r, 30, 44, w - 196, cursor=blink(t) if (t > tC and t - tC < 2.4) else None)
        kb = prog(t, tD + 3.0, 0.55)
        if kb > 0:
            with c.push(0.94 + 0.06 * e_back(kb), x0 + w / 2, 600, e_out(min(1, kb * 1.8)), dy=(1 - e_out(kb)) * 30):
                c.glow(x0, 440, w, 330, RED, 0.45, 40, r=22)
                c.rect(x0, 440, w, 330, 22, fill=(26, 12, 12), outline=RED, width=3)
                cross(c, x0 + 80, 560, 44, RED, e_out(prog(t, tD + 3.2, 0.5)))
                c.text(x0 + 160, 535, "Adds sqlite anyway.", 48, WHITE, "b")
                c.text(x0 + 160, 595, "The server is read-only.", 42, RED, "s")
                c.text(x0 + 40, 700, "It never knew the rule.", 38, MUTED, "r")
    else:
        lines = ["[MeshAgents] Coordination context for", "this repository:", "...", "Rules and facts stated earlier by the user", "(not in the code):",
                 "- FYI never use sqlite here, the server", "  filesystem is read-only."]
        with P(c, t, tD + 0.7, x0 + w / 2, 560, 0.6, 40):
            msg_card(c, x0, 395, w, "Briefing the new helper gets first", lines, 28, GREEN, glow=0.3, hl=[5, 6], lh=36)
        rows = [([("# store orders", CM)], None), ([("import ", KW), ("json", FN), ("  ", CODE), ("# orders.json", CM)], GREEN)]
        r, done = typed(rows, (t - tC) * 22 if t > tC else 0)
        hot = prog(t, tC + 1.2, 0.5)
        with P(c, t, tD + 0.5, x0 + 500, 270, 0.6, 24):
            file_card(c, x0 + 150, 190, w - 150, 170, "shop/db.py", glowc=GREEN if hot > 0 else None, gl=0.35 * hot, outline=mix(BORDER, GREEN, hot))
            code_block(c, x0 + 176, 255, r, 30, 44, w - 196, cursor=blink(t) if (t > tC and t - tC < 2.4) else None)
        ko = prog(t, tD + 5.6, 0.55)
        if ko > 0:
            with c.push(0.9 + 0.1 * e_back(ko), x0 + w / 2, 840, e_out(ko)):
                check(c, x0 + 60, 840, 30, GREEN, e_out(prog(t, tD + 5.8, 0.5)))
                c.text(x0 + 120, 840, "Uses a JSON file instead. Rule kept.", 40, GREEN, "s")


def scene_split(c, t, T):
    k = e_out(prog(t, 0.1, 0.6))
    with c.push(1, 0, 0, k, dy=(1 - k) * -16):
        pill(c, 480, 62, "Without", 44, WHITE, mix(BG, RED, 0.35), padx=40, h=76, anchor="m", outline=RED)
        pill(c, 1440, 62, "With MeshAgents", 44, BG, GREEN, padx=40, h=76, anchor="m")
    c.glow(956, 120, 8, 780, (90, 110, 150), 0.25, 20, r=4, alpha=k)
    c.rect(959, 120, 2, 780, 1, fill=(60, 60, 58), alpha=k)
    tD = T.t("w5", -0.25)
    kd = prog(t, tD + 0.3, 0.5)
    if kd > 0:
        with c.push(0.9 + 0.1 * e_back(kd), 960, 132, e_out(kd)):
            pill(c, 960, 132, "The next day", 36, WHITE, (36, 36, 34), padx=30, h=60, anchor="m", outline=BORDER)
    half(c, t, T, True)
    half(c, t, T, False)


# ------------------------------------------------------------------ 4b BOARD
def scene_board(c, t, T):
    b = shot("ui-board-dark.png"); m = shot("ui-memory-dark.png")
    sw = 1080; sh = sw * 900 / 1440; wx, wy = 70, 130
    t2 = T.t("b2", -0.4)
    ko = e_io(prog(t, t2, 0.7))
    kb = prog(t, 0.35, 0.8)
    if ko < 0.99:
        with c.push(1, 0, 0, 1 - ko, dx=-ko * 160):
            with c.push(0.95 + 0.05 * e_out(kb), wx + sw / 2, wy + sh / 2, e_out(kb), dy=(1 - e_out(kb)) * 40):
                c.glow(wx, wy, sw, sh + 52, BLUE, 0.35, 60, r=18)
                window(c, wx, wy, sw, sh + 52, "meshagents ui  -  127.0.0.1:7777")
                c.image(b, wx, wy + 52, sw, sh, 0)
            kc = prog(t, T.t("b1", 0.5), 0.6)
            with c.push(1, 0, 0, e_out(kc), dx=(1 - e_out(kc)) * 40):
                c.text(1210, 250, "The live board", 60, WHITE, "b")
            items = [(LBLUE, "Who is working on what"), (ORANGE, "What needs attention"), (RED, "Where trouble is")]
            for i, (col, s) in enumerate(items):
                kk = prog(t, T.t("b1", 1.0 + i * 0.5), 0.5)
                with c.push(1, 0, 0, e_out(kk), dx=(1 - e_out(kk)) * 30):
                    c.glow_circle(1226, 350 + i * 90, 14, col, 0.6)
                    c.circle(1226, 350 + i * 90, 14, fill=col)
                    c.text(1262, 350 + i * 90, s, 40, WHITE, "m")
    if ko > 0.01:
        with c.push(1, 0, 0, ko, dx=(1 - ko) * 160):
            c.glow(wx, wy, sw, sh + 52, GREEN, 0.3, 60, r=18)
            window(c, wx, wy, sw, sh + 52, "Memory  -  what the next session is told")
            c.image(m, wx, wy + 52, sw, sh, 0)
            sc_ = sw / 1440
            hk = prog(t, T.t("b2", 1.9), 0.5)
            hx, hy, hw, hh = wx + 262 * sc_, wy + 52 + 116 * sc_, 570 * sc_, 38 * sc_
            c.glow(hx, hy, hw, hh, GREEN, 0.7 * hk, 20, r=10)
            c.rect(hx, hy, hw, hh, 10, outline=GREEN, width=4, alpha=hk)
            kc = prog(t, t2 + 0.9, 0.7)
            with c.push(1, 0, 0, e_out(kc), dx=(1 - e_out(kc)) * 40):
                c.text(1210, 235, "about", 44, MUTED, "m")
                c.text(1210, 315, "370 tokens", 100, GREEN, "h")
                c.text(1210, 395, "is all a new helper is told", 40, WHITE, "m")
            for i, s in enumerate(["Rules people stated", "Who else is working now", "Recent decisions", "The last handoff"]):
                kk = prog(t, t2 + 1.8 + i * 0.35, 0.5)
                with c.push(1, 0, 0, e_out(kk), dx=(1 - e_out(kk)) * 30):
                    check(c, 1226, 500 + i * 76, 17, GREEN, e_out(kk))
                    c.text(1262, 500 + i * 76, s, 40, WHITE, "m")


# ------------------------------------------------------------------ 5 GRAPH
NODE = {  # id: (x, y, label, color)
    "t12": (340, 510, "A: Task 12", LBLUE), "t15": (340, 730, "B: Task 15", LBLUE),
    "db": (790, 510, "shop/db.py", GREEN), "api": (790, 730, "shop/api.py", GREEN),
    "get": (1240, 510, "get_order", PINK), "fetch": (1240, 730, "fetch_order", PINK),
    "n2": (340, 290, "reads db", PURPLE), "n1": (790, 290, "use sqlite", PURPLE), "n0": (1240, 290, "Note: must persist", PURPLE),
}
EDGES = [  # (id, from, to, label, orientation)
    ("e1", "t12", "db", "TOUCHES", "h"), ("e2", "t15", "api", "TOUCHES", "h"),
    ("e3", "db", "get", "DEFINES", "h"), ("e4", "api", "fetch", "DEFINES", "h"),
    ("e5", "fetch", "get", "CALLS", "v"), ("e6", "n1", "db", "ABOUT", "v"),
    ("e7", "n2", "n1", "BASED_ON", "h"), ("e8", "n1", "n0", "BASED_ON", "h"),
]
NW = {k: tw(v[2], 34, "m") + 54 for k, v in NODE.items()}
NH = 66


def win(t, a, b, fade=0.4):
    return clamp01((t - a) / fade) * (1 - clamp01((t - b) / fade))


def edge_pts(a, b, side):
    ax, ay, _, _ = NODE[a]; bx, by, _, _ = NODE[b]
    if side == "h":
        s = 1 if bx > ax else -1
        return (ax + s * NW[a] / 2 + s * 8, ay), (bx - s * NW[b] / 2 - s * 8, by)
    s = 1 if by > ay else -1
    return (ax, ay + s * NH / 2 + s * 8), (bx, by - s * NH / 2 - s * 8)


def scene_graph(c, t, T):
    f1, f2, f3, f4, f5 = [T.t(k) for k in ("f1", "f2", "f3", "f4", "f5")]
    q1 = win(t, f2 + 1.9, f3 - 0.3)
    q2 = win(t, f3 + 0.2, f4 - 0.3)
    q3 = win(t, f4 + 0.2, f5 - 0.2)
    fin = prog(t, f5 - 0.1, 0.8)
    lit_nodes = {"t12": q1, "db": q1, "get": q2, "fetch": q2, "api": q2, "t15": q2, "n0": q3, "n1": q3, "n2": q3}
    lit_edges = {"e1": q1, "e5": q2, "e4": q2, "e2": q2, "e3": 0, "e6": 0, "e7": q3, "e8": q3}
    focus = max(q1, q2, q3)
    red = {"n0": e_out(prog(t, f4 + 3.0, 0.35)), "n1": e_out(prog(t, f4 + 3.7, 0.35)), "n2": e_out(prog(t, f4 + 4.4, 0.35)),
           "e8": e_out(prog(t, f4 + 3.5, 0.35)), "e7": e_out(prog(t, f4 + 4.2, 0.35))}
    red = {k: v * (1 - e_io(fin)) for k, v in red.items()}
    gscale = 1 - 0.32 * e_io(fin)

    def title(text, t0, t1, col=WHITE, size=68):
        k = win(t, t0, t1, 0.35)
        with c.push(1, 0, 0, k, dy=(1 - k) * 16):
            c.text(960, 100, text, size, col, "b", anchor="m")
    title("Your helpers' notes live in a graph", 0.2, f2 + 0.2, WHITE, 64)
    title("Who is working on this file?", f2 + 0.3, f3 - 0.1)
    title("What breaks if I change this function?", f3 - 0.05, f4 - 0.1)
    title("What was this note based on?", f4 - 0.05, f4 + 2.7)
    title("A note was wrong? See everything built on it.", f4 + 2.8, f5 - 0.1, RED, 64)
    k = e_out(prog(t, f5 + 0.0, 0.6))
    with c.push(1, 0, 0, k, dy=(1 - k) * 16):
        c.text(940, 100, "Built on", 64, MUTED, "m", anchor="r")
        c.text(970, 100, "FalkorDB", 80, GREEN, "h", anchor="l")

    with c.push(gscale, 960, 100):
        with c.push(1, 0, 0, 1.0, dx=125 * e_io(fin)):
            for n_, (eid, a, b, lab, side) in enumerate(EDGES):
                p0, p1 = edge_pts(a, b, side)
                ke = prog(t, 0.6 + n_ * 0.15, 0.7)
                if ke <= 0: continue
                dim = 1 - 0.78 * focus * (1 - lit_edges[eid])
                col = mix((120, 120, 118), ORANGE if eid == "e5" else LBLUE, lit_edges[eid])
                if eid in red: col = mix(col, RED, red[eid]); dim = max(dim, red[eid])
                q = (lerp(p0[0], p1[0], e_io(ke)), lerp(p0[1], p1[1], e_io(ke)))
                c.line([p0, q], col, 4 + 4 * max(lit_edges[eid], red.get(eid, 0)), alpha=dim)
                if ke >= 1:
                    ux, uy = (p1[0] - p0[0]), (p1[1] - p0[1]); L = math.hypot(ux, uy); ux, uy = ux / L, uy / L
                    c.poly([(p1[0] + ux * 6, p1[1] + uy * 6), (p1[0] - ux * 18 - uy * 11, p1[1] - uy * 18 + ux * 11), (p1[0] - ux * 18 + uy * 11, p1[1] - uy * 18 - ux * 11)], col, alpha=dim)
                    mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
                    wlab = tw(lab, 26, "m", True) + 16
                    if side == "h":
                        c.rect(mx - wlab / 2, my - 40, wlab, 32, 8, fill=BG, alpha=0.9 * dim)
                        c.text(mx, my - 24, lab, 26, col, "m", mono=True, anchor="m", alpha=dim)
                    else:
                        c.rect(mx - 18 - wlab, my - 16, wlab, 32, 8, fill=BG, alpha=0.9 * dim)
                        c.text(mx - 26, my, lab, 26, col, "m", mono=True, anchor="r", alpha=dim)
                    if lit_edges[eid] > 0.3:
                        u = (t * 0.9) % 1.0
                        px, py = lerp(p0[0], p1[0], u), lerp(p0[1], p1[1], u)
                        c.glow_circle(px, py, 12, col, 0.9 * lit_edges[eid]); c.circle(px, py, 7, fill=WHITE, alpha=lit_edges[eid])
            for i, (nid, (x, y, lab, col)) in enumerate(NODE.items()):
                kn = prog(t, 0.3 + i * 0.12, 0.6)
                if kn <= 0: continue
                lit = lit_nodes.get(nid, 0)
                cc = mix(col, RED, red[nid]) if nid in red else col
                dim = 1 - 0.78 * focus * (1 - lit)
                if nid in red: dim = max(dim, red[nid])
                if nid in ("fetch", "api"): cc = mix(cc, ORANGE, q2 * 0.8)
                with c.push(0.6 + 0.4 * e_back(kn), x, y, e_out(min(1, kn * 1.6))):
                    gl = max(lit, red.get(nid, 0))
                    if gl > 0.05:
                        c.glow(x - NW[nid] / 2, y - NH / 2, NW[nid], NH, cc, 0.8 * gl, 28, r=NH / 2, alpha=dim)
                    c.rect(x - NW[nid] / 2, y - NH / 2, NW[nid], NH, NH / 2, fill=mix(BG, cc, 0.22), outline=cc, width=3, alpha=dim)
                    c.text(x, y, lab, 34, WHITE, "m", anchor="m", alpha=dim)
            if q1 > 0.02:
                with c.push(1, 0, 0, q1):
                    pill(c, 340 + 20, 510 - 62, "working now", 28, BG, GREEN, padx=16, h=40, anchor="m")
            if q2 > 0.02:
                with c.push(1, 0, 0, q2):
                    pill(c, 1240 + 40, 730 + 62, "may break", 28, BG, ORANGE, padx=16, h=40, anchor="m")
        kl = win(t, 1.8, f2 + 0.2, 0.4)
        if kl > 0.01:
            xx = 250
            for nm, col in [("Task", LBLUE), ("File", GREEN), ("Function", PINK), ("Decision", PURPLE)]:
                c.circle(xx, 850, 14, fill=col, alpha=kl)
                c.text(xx + 28, 850, nm, 36, WHITE, "m", alpha=kl)
                xx += 60 + tw(nm, 36, "m") + 50

    def answer(t0, t1, head, body, col):
        k = win(t, t0, t1, 0.45)
        if k <= 0.01: return
        with c.push(1, 0, 0, k, dx=(1 - k) * 40):
            c.glow(1480, 330, 390, 330, col, 0.25, 40, r=24)
            c.rect(1480, 330, 390, 330, 24, fill=PANEL, outline=col, width=3)
            c.text(1510, 380, "The answer", 30, MUTED, "m", mono=True)
            c.text(1510, 450, head, 48, col, "b")
            for i, ln in enumerate(wrap(body, 36, 330, "r")):
                c.text(1510, 520 + i * 46, ln, 36, WHITE, "r")
    answer(f2 + 2.6, f3 - 0.2, "Helper A", "has shop/db.py, last edit 2 seconds ago.", LBLUE)
    answer(f3 + 1.6, f4 - 0.3, "shop/api.py", "calls it. Helper B is working there now.", ORANGE)
    answer(f4 + 3.6, f5 - 0.2, "2 notes", "were built on it. Both are flagged.", RED)

    chips = [("1 query", "claims a task atomically", f5 + 0.5),
             ("about 3 ms", "to find everything built on a wrong note (25 of 25 test graphs)", T.t("f5", 1.9)),
             ("Git history", "shows which files usually change together", T.t("f5", 5.6))]
    for i, (big, small, t0) in enumerate(chips):
        k = prog(t, t0, 0.6)
        cw = 580; x = 60 + i * (cw + 40); y = 600
        with c.push(0.94 + 0.06 * e_back(k), x + cw / 2, y + 120, e_out(min(1, k * 1.6)), dy=(1 - e_out(k)) * 30):
            c.rect(x, y, cw, 260, 24, fill=PANEL, outline=BORDER, width=2)
            c.glow(x, y, cw, 260, GREEN, 0.12, 40, r=24)
            c.text(x + 30, y + 62, big, 56, GREEN, "h")
            for j, ln in enumerate(wrap(small, 36, cw - 60, "r")[:3]):
                c.text(x + 30, y + 130 + j * 44, ln, 36, WHITE, "r")


# ------------------------------------------------------------------ 6 NUMBERS
def stat_card(c, t, t0, x, y, w, h, title):
    k = prog(t, t0, 0.6)
    c.push(0.94 + 0.06 * e_back(k), x + w / 2, y + h / 2, e_out(min(1, k * 1.6)), dy=(1 - e_out(k)) * 34)
    c.rect(x, y, w, h, 24, fill=PANEL, outline=BORDER, width=2)
    c.text(x + 30, y + 48, title, 38, WHITE, "s")


def bar_row(c, t, t0, x, y, w, label, val, col, vsize=48, dur=1.3):
    k = prog(t, t0, dur)
    c.text(x, y, label, 36, MUTED, "m")
    c.text(x + w, y, f"{val * e_out(k):.0f}%", vsize, col, "h", anchor="r")
    c.rect(x, y + 30, w, 20, 10, fill=(38, 38, 36))
    if k > 0.01:
        bw = max(20, w * val / 100 * e_out(k))
        c.glow(x, y + 30, bw, 20, col, 0.35, 14, r=10)
        c.rect(x, y + 30, bw, 20, 10, fill=col)


def scene_numbers(c, t, T):
    k = e_out(prog(t, 0.2, 0.6))
    with c.push(1, 0, 0, k):
        c.text(960, 70, "Measured, not promised", 52, WHITE, "b", anchor="m")
    X = [45, 665, 1285]; CW = 590
    t1 = T.t("n1", 0.1)
    stat_card(c, t, t1, X[0], 130, CW, 385, "Runs that finish clean")
    bar_row(c, t, t1 + 0.4, X[0] + 30, 235, CW - 60, "Without", 53, RED)
    bar_row(c, t, t1 + 1.6, X[0] + 30, 350, CW - 60, "With MeshAgents", 80, GREEN)
    c.text(X[0] + 30, 450, "180 runs  -  +27 points  -  p < 0.001", 33, MUTED, "r", alpha=e_out(prog(t, t1 + 2.6, 0.5)))
    c.pop()
    t2 = T.t("n2", 0.1)
    stat_card(c, t, t2, X[1], 130, CW, 385, "Next session finishes")
    bar_row(c, t, t2 + 0.5, X[1] + 30, 245, CW - 60, "No memory", 45, RED, vsize=44)
    bar_row(c, t, t2 + 2.0, X[1] + 30, 330, CW - 60, "Notes file", 92, ORANGE, vsize=44)
    bar_row(c, t, t2 + 3.5, X[1] + 30, 415, CW - 60, "MeshAgents", 95, GREEN, vsize=44)
    c.text(X[1] + 30, 495, "150 runs", 33, MUTED, "r", alpha=e_out(prog(t, t2 + 4.2, 0.5)))
    c.pop()
    t3 = T.t("n3", 0.1)
    stat_card(c, t, t3, X[2], 130, CW, 385, "One rule hidden among 20")
    for i in range(10):
        r_, c_ = divmod(i, 5)
        cx, cy = X[2] + 80 + c_ * 108, 250 + r_ * 84
        kk = prog(t, t3 + 0.6 + i * 0.16, 0.35)
        c.circle(cx, cy, 30, fill=mix((38, 38, 36), GREEN, e_out(kk)))
        if kk > 0.3: c.line([(cx - 12, cy), (cx - 3, cy + 10), (cx + 13, cy - 9)], BG, 6, alpha=e_out(kk))
    ka = e_out(prog(t, t3 + 1.8, 0.5))
    c.text(X[2] + 30, 455, "10 of 10", 66, GREEN, "h", alpha=ka)
    c.text(X[2] + 330, 455, "found", 40, MUTED, "m", alpha=ka)
    c.pop()
    t4 = T.t("n4", 0.1)
    stat_card(c, t, t4, X[0], 545, CW * 2 + 30, 340, "Cost per clean result")
    k = e_out(prog(t, t4 + 0.5, 0.9))
    c.text(X[0] + 40, 665, "$0.0159", 70, RED, "h", alpha=k)
    c.text(X[0] + 40, 729, "without", 36, MUTED, "m", alpha=k)
    c.line([(X[0] + 350, 668), (X[0] + 412, 668)], MUTED, 6, alpha=k)
    c.poly([(X[0] + 440, 668), (X[0] + 413, 652), (X[0] + 413, 684)], MUTED, alpha=k)
    k2 = e_out(prog(t, t4 + 1.4, 0.9))
    c.text(X[0] + 480, 665, "$0.0113", 70, GREEN, "h", alpha=k2)
    c.text(X[0] + 480, 729, "with MeshAgents", 36, MUTED, "m", alpha=k2)
    k3 = prog(t, t4 + 2.2, 1.1)
    c.glow(X[0] + 840, 605, 340, 190, GREEN, 0.25 * e_out(k3), 40, r=24)
    c.rect(X[0] + 840, 605, 340, 190, 24, fill=mix(BG, GREEN, 0.14), outline=GREEN, width=3, alpha=e_out(k3))
    c.text(X[0] + 1010, 686, f"{29 * e_out(k3):.0f}%", 110, GREEN, "h", anchor="m", alpha=e_out(k3))
    c.text(X[0] + 1010, 765, "lower", 42, WHITE, "s", anchor="m", alpha=e_out(k3))
    c.text(X[0] + 40, 835, "Per run: about the same (+6%)", 36, MUTED, "r", alpha=e_out(prog(t, t4 + 3.2, 0.6)))
    c.pop()
    t5 = T.t("n5", 0.1)
    stat_card(c, t, t5, X[2], 545, CW, 340, "A second, stronger model")
    bar_row(c, t, t5 + 0.4, X[2] + 30, 665, CW - 60, "Without", 33, RED)
    bar_row(c, t, t5 + 1.5, X[2] + 30, 765, CW - 60, "With MeshAgents", 83, GREEN)
    c.text(X[2] + 30, 862, "24 runs per side", 33, MUTED, "r", alpha=e_out(prog(t, t5 + 2.3, 0.5)))
    c.pop()


# ------------------------------------------------------------------ 7 HONEST
def scene_honest(c, t, T):
    k = e_out(prog(t, 0.2, 0.6))
    with c.push(1, 0, 0, k, dy=(1 - k) * 16):
        c.text(960, 100, "The honest part", 76, WHITE, "b", anchor="m")
    items = [("g2", "Built to collide", "The tests make helpers clash on purpose. Real projects will see fewer clashes.", ORANGE, "!"),
             ("g3", "A notes file is close", "On memory it does about as well. But someone has to keep it up.", ORANGE, "="),
             ("g4", "One test is not fixed", "Two helpers adding the same stock reservation.", RED, "x")]
    for i, (key, head, sub, col, glyph) in enumerate(items):
        y = 190 + i * 235; k = prog(t, T.t(key, -0.1), 0.6)
        with c.push(0.95 + 0.05 * e_back(k), 960, y + 100, e_out(min(1, k * 1.6)), dx=(1 - e_out(k)) * -60):
            c.glow(120, y, 1680, 205, col, 0.10, 40, r=28)
            c.rect(120, y, 1680, 205, 28, fill=PANEL, outline=BORDER, width=2)
            c.glow_circle(235, y + 102, 54, col, 0.35)
            c.circle(235, y + 102, 52, fill=mix(BG, col, 0.2), outline=col, width=4)
            if glyph == "!":
                c.rect(230, y + 72, 10, 36, 5, fill=col); c.circle(235, y + 128, 7, fill=col)
            elif glyph == "=":
                c.rect(213, y + 84, 44, 8, 4, fill=col); c.rect(213, y + 110, 44, 8, 4, fill=col)
            else:
                c.line([(216, y + 83), (254, y + 121)], col, 9); c.line([(254, y + 83), (216, y + 121)], col, 9)
            c.text(340, y + 70, head, 56, WHITE, "b")
            for j, ln in enumerate(wrap(sub, 40, 1380, "r")):
                c.text(340, y + 130 + j * 46, ln, 40, MUTED, "r")


# ------------------------------------------------------------------ 8 TRY
def scene_try(c, t, T):
    t_end = T.t("t2", -0.2)
    k_term = 1 - e_io(prog(t, t_end, 0.6))
    if k_term > 0.01:
        with c.push(1, 0, 0, k_term, dy=-(1 - k_term) * 30):
            k = prog(t, 0.2, 0.7)
            with c.push(0.95 + 0.05 * e_back(k), 960, 420, e_out(k), dy=(1 - e_out(k)) * 30):
                c.glow(190, 130, 1540, 560, GREEN, 0.18, 70, r=20)
                window(c, 190, 130, 1540, 560, "terminal")
                lines = [("git clone https://github.com/Fahad-Dezloper/MeshAgents", 0.9),
                         ("meshagents doctor", T.t("t1", 1.5)),
                         ("claude --plugin-dir ./meshagents/plugin", T.t("t1", 2.9))]
                for i, (cmd, t0) in enumerate(lines):
                    y = 270 + i * 130
                    c.text(240, y, "$", 40, GREEN, "b", mono=True)
                    n = max(0, int((t - t0) * 34))
                    shown = cmd[:n]
                    c.text(290, y, shown, 38, WHITE, "r", mono=True)
                    if t > t0 and (n < len(cmd) or (i == 2 and (t * 1.8) % 1 < .6)):
                        c.rect(290 + tw(shown, 38, "r", True) + 4, y - 22, 20, 44, 2, fill=WHITE, alpha=1)
                    if t > t0 + len(cmd) / 34 + 0.2 and i < 2:
                        check(c, 1650, y, 22, GREEN, e_out(prog(t, t0 + len(cmd) / 34 + 0.2, 0.4)))
            c.text(960, 790, "The demo needs no API key. Docker and Python 3.10+.", 40, MUTED, "m", anchor="m", alpha=e_out(prog(t, 1.2, 0.6)))
    k = e_io(prog(t, t_end + 0.2, 0.8))
    if k > 0.01:
        with c.push(0.96 + 0.04 * e_out(k), 960, 480, k):
            notebook(c, 960, 205, 0.6, t, 0.5 + 0.2 * math.sin(t * 2))
            x0 = 960 - tw("MeshAgents", 150, "h") / 2
            c.text(x0, 470, "Mesh", 150, WHITE, "h")
            c.text(x0 + tw("Mesh", 150, "h"), 470, "Agents", 150, GREEN, "h")
            c.text(960, 600, "A shared memory for AI coding helpers", 58, WHITE, "m", anchor="m")
            pill(c, 960, 692, "Built on FalkorDB", 44, BG, GREEN, padx=40, h=78, anchor="m")
            c.text(960, 776, "github.com/Fahad-Dezloper/MeshAgents", 42, LBLUE, "m", mono=True, anchor="m")
            c.text(960, 836, "WeMakeDevs x FalkorDB Graph Hacks, Track 2", 38, MUTED, "m", anchor="m")
