"""Short silent cut: scenes composed from the long cut's building blocks, with warped (faster) time."""
import math
from gfx import *
from scenes_a import *
import scenes_b as B


class FT:
    def __init__(self, **cues): self.c = cues
    def t(self, k, off=0.0): return self.c[k] + off
    def e(self, k, off=0.0): return self.c[k] + off


def s_graph(c, t):
    B.GRAPH_SHORT = True
    B.scene_graph(c, t * 1.75, FT(f1=0.0, f2=1.8, f3=5.4, f4=8.6, f5=14.0))


def s_hook(c, t):
    scene_hook(c, t * 1.25, FT(h2=1.6), "Two AI helpers.")


def s_clash(c, t):
    w = 1.5; tw_ = t * w; T = FT(c1=0.0, c2=1.8, c3=3.2, c4=999, c5=999)
    sx, sy = shake(tw_, T.t("c3", 1.95))
    with c.push(1, 0, 0, 1.0, dx=sx, dy=sy):
        clash_day1(c, tw_, T)
    # big headline once it breaks
    k = e_out(prog(tw_, T.t("c3", 2.3), 0.3))
    with c.push(1, 0, 0, k, dy=(1 - k) * 20):
        c.text(960, 960, "Nobody told anybody.", 56, WHITE, "b", anchor="m")


def s_day2(c, t):
    clash_day2(c, t * 1.4, FT(c4=-0.6, c5=-0.7), 0.0)


def s_mesh(c, t):
    t = t * 1.25
    hub = (960, 600)
    orbit = [("File", GREEN), ("Decision", PURPLE), ("Task", LBLUE), ("Function", PINK), ("File", GREEN), ("Decision", PURPLE)]
    ka = prog(t, 0.6, 0.4)
    lit = e_out(prog(t, 4.6, 0.4))
    for i, (nm, col) in enumerate(orbit):
        ang = t * 0.5 + i * math.tau / len(orbit)
        r = 245 + 12 * math.sin(t + i)
        x, y = hub[0] + math.cos(ang) * r * 1.35, hub[1] + math.sin(ang) * r * 0.62
        c.line([hub, (x, y)], col, 3 + 3 * lit, alpha=(0.28 + 0.5 * lit) * ka)
        c.glow_circle(x, y, 18 + 8 * lit, col, (0.6 + 0.8 * lit) * ka)
        c.circle(x, y, 15, fill=col, alpha=ka)
    for cx, col, letter, ph in [(330, A_COL, "A", 0.0), (1590, B_COL, "B", 1.7)]:
        with P(c, t, 0.0, cx, 600, 0.3, 40, True, 0.6):
            avatar(c, cx, 590, 190, col, letter, "happy", t, glow=0.35, phase=ph)
        sgn = 1 if cx < 960 else -1
        p0 = (cx + sgn * 120, 600); p1 = (hub[0] - sgn * 150, 600)
        kk = prog(t, 0.4, 0.4)
        if kk > 0:
            c.line([p0, (lerp(p0[0], p1[0], e_io(kk)), 600)], col, 4, alpha=0.6)
            if kk >= 1:
                for j in range(3):
                    u = ((t * 0.9 + j / 3 + (0.3 if letter == "B" else 0)) % 1.0)
                    px = lerp(p0[0], p1[0], u)
                    c.glow_circle(px, 600, 10, col, 0.9); c.circle(px, 600, 7, fill=WHITE)
    with P(c, t, 0.2, hub[0], hub[1], 0.35, 30, True, 0.7):
        notebook(c, hub[0], hub[1] - 10, 1.0, t, 0.5 + 0.2 * math.sin(t * 3))
    k = prog(t, 0.3, 0.3)
    with c.push(1 + 0.03 * (1 - e_out(k)), 960, 150, e_out(k), dy=(1 - e_out(k)) * 26):
        x0 = 960 - tw("MeshAgents", 124, "h") / 2
        c.text(x0, 150, "Mesh", 124, WHITE, "h"); c.text(x0 + tw("Mesh", 124, "h"), 150, "Agents", 124, GREEN, "h")
    k = prog(t, 4.4, 0.3)
    with P(c, t, 4.4, 960, 262, 0.3, 14):
        pill(c, 960, 262, "Built on FalkorDB", 44, BG, GREEN, padx=34, h=70, anchor="m")
    beats = ["Warns", "Remembers", "Hands over"]
    ws = [tw(b, 56, "b") + 70 for b in beats]; gap = 26
    x = 960 - (sum(ws) + gap * 2) / 2
    cols = [ORANGE, LBLUE, GREEN]
    for i, b in enumerate(beats):
        with P(c, t, 1.4 + i * 0.7, x + ws[i] / 2, 850, 0.3, 20):
            c.rect(x, 805, ws[i], 90, 45, fill=mix(BG, cols[i], 0.18), outline=cols[i], width=3)
            c.text(x + ws[i] / 2, 850, b, 56, WHITE, "b", anchor="m")
        x += ws[i] + gap


def s_stats(c, t):
    B.scene_numbers(c, t * 1.6, FT(n1=0.0, n2=2.4, n3=4.8, n4=6.2, n5=8.6))
    k = e_out(prog(t, 6.6, 0.4))
    c.text(960, 930, "Tests are built to make helpers collide; real projects see fewer clashes.", 34, MUTED, "r", anchor="m", alpha=k)


def s_end(c, t):
    with P(c, t, 0.1, 960, 120, 0.35, 20):
        notebook(c, 960, 125, 0.34, t, 0.5 + 0.2 * math.sin(t * 2))
    with P(c, t, 0.2, 960, 260, 0.35, 20):
        x0 = 960 - tw("MeshAgents", 120, "h") / 2
        c.text(x0, 255, "Mesh", 120, WHITE, "h"); c.text(x0 + tw("Mesh", 120, "h"), 255, "Agents", 120, GREEN, "h")
    with P(c, t, 0.4, 960, 350, 0.3, 14):
        c.text(960, 350, "A shared memory for AI coding helpers", 52, WHITE, "m", anchor="m")
    with P(c, t, 0.6, 960, 425, 0.3, 14):
        pill(c, 960, 425, "Built on FalkorDB", 42, BG, GREEN, padx=36, h=70, anchor="m")
    with P(c, t, 0.9, 960, 620, 0.35, 24):
        c.glow(300, 490, 1320, 270, GREEN, 0.15, 60, r=20)
        window(c, 300, 490, 1320, 270, "terminal")
        for i, cmd in enumerate(["git clone https://github.com/Fahad-Dezloper/MeshAgents", "meshagents doctor", "claude --plugin-dir ./plugin"]):
            y = 600 + i * 58
            c.text(340, y, "$", 36, GREEN, "b", mono=True)
            c.text(385, y, cmd, 36, WHITE, "r", mono=True, alpha=e_out(prog(t, 1.0 + i * 0.35, 0.25)))
    k = prog(t, 1.9, 0.3)
    with c.push(1, 0, 0, e_out(k)):
        c.text(960, 825, "github.com/Fahad-Dezloper/MeshAgents", 42, LBLUE, "m", mono=True, anchor="m")
        c.text(960, 890, "WeMakeDevs x FalkorDB Graph Hacks, Track 2", 38, MUTED, "m", anchor="m")


SEGS = [(0.0, 5.0, s_hook), (5.0, 15.0, s_clash), (15.0, 22.0, s_day2), (22.0, 28.0, s_mesh), (28.0, 37.0, s_graph), (37.0, 51.0, s_stats), (51.0, 58.5, s_end)]
