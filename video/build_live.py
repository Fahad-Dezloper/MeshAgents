"""Live demo cut: .venv/bin/python video/build_live.py [frames t...]  ->  video/out/MeshAgents-60s-live.mp4 (silent, 58 s)

Needs the recordings from record_capture.py and record_live.py (video/rec/). The split-screen is built from
real screenshots of the running dashboard and the real, timestamped output of the demo; the hook, stats and end
scenes are reused from build_short.py's scenes. Nothing in the split-screen is drawn from imagined data.
"""
import bisect, json, os, subprocess, sys
from multiprocessing import Pool
from PIL import Image, ImageDraw
from gfx import *
import scenes_short as SS

HERE = os.path.dirname(os.path.abspath(__file__)); REC = f"{HERE}/rec"; FPS = 30; XF = 0.25
TOTAL = 58.0
T_DEMO0, T_DEMO1 = 6.0, 21.5       # paced demo + board
T_LIVE1 = 29.5                      # real Claude Code sessions
T_MEM1, T_SPLIT1 = 32.5, 36.0       # memory view, code view
SPEED = 1.87                        # demo waits shortened
R0 = 2.0                            # recording time at the start of the demo block
TAKE = f"{REC}/live/take1"

# ---------- recordings ----------
def _load_frames(tag):
    meta = json.load(open(f"{REC}/frames_{tag}.json"))
    return [m["t"] for m in meta], [f"{REC}/frames_{tag}/" + os.path.basename(m["file"]) for m in meta], [m["view"] for m in meta]
F15 = _load_frames("z15"); F13 = _load_frames("z13")
OUT_LINES = [json.loads(l) for l in open(f"{REC}/stdout_z15.jsonl")]
_img = {}
def frame(F, t, view=None):
    ts, paths, views = F
    i = min(max(bisect.bisect_left(ts, t), 0), len(ts) - 1)
    if view:
        while i < len(ts) - 1 and views[i] != view: i += 1
    p = paths[i]
    if p not in _img:
        if len(_img) > 6: _img.clear()
        _img[p] = Image.open(p).convert("RGB")
    return _img[p]

def view_start(F, view): return next(t for t, v in zip(F[0], F[2]) if v == view)

# ---------- terminal text ----------
TFS = 26; TLH = 36; CPL = 41
def wrap_line(s):
    if not s: return [""]
    ind = len(s) - len(s.lstrip(" "))
    hang = ind + (2 if s.lstrip().startswith("- ") else 0)
    out, cur, first = [], "", True
    for w in s.split(" "):
        cand = (cur + " " + w) if cur else w
        if len(cand) + (0 if first else hang) <= CPL or not cur: cur = cand
        else:
            out.append(cur if first else " " * hang + cur); cur = w; first = False
    out.append(cur if first else " " * hang + cur)
    return out
# classify blocks: lines after "[to X]" until blank are the message; message kinds by first line
ROWS = []  # (t, text, kind)  kind: None | "digest" | "collision" | "callers" | "head"
_kind = None
for r in OUT_LINES:
    ln = r["line"]
    if ln.startswith("[to "): _kind = "to"
    elif ln == "": _kind = None
    k = None
    if _kind == "to" and not ln.startswith("[to "):
        k = "msg"
        if ln.startswith("[MeshAgents]"):
            k = "digest" if "recently changed" in ln else "collision" if "collision" in ln else "callers" if "Callers elsewhere" in ln or "how" in ln and "called" in ln else "msg"
    if _kind == "to" and k in ("digest", "collision", "callers"): _cur = k
    for i, w in enumerate(wrap_line(ln)): ROWS.append([r["t"], w, k, ln])
# propagate message kind through the block
cur = None
for row in ROWS:
    if row[2] in ("digest", "collision", "callers"): cur = row[2]
    elif row[2] == "msg" and cur: row[2] = cur
    elif row[2] is None: cur = None
    if row[2] == "msg": row[2] = None
KCOL = {"digest": LBLUE, "collision": ORANGE, "callers": RED}
KT = {k: next(r[0] for r in ROWS if r[2] == k) for k in KCOL}

def terminal_image(pw, ph, r, zoom_focus=None):
    """returns a PIL image (pw*S x ph*S) of the terminal at recording time r"""
    img = Image.new("RGB", (pw * S, ph * S), (14, 14, 13)); c = Canvas(img)
    vis = [row for row in ROWS if row[0] <= r + 1e-6]
    n = int((ph - 24) // TLH)
    off = max(0, len(vis) - n)
    if vis:
        tops = [i for i, row in enumerate(vis) if row[3].startswith("[to ") or row[3].startswith("===")]
        st = tops[-1] if tops else 0
        if st < off:  # a long message: show its start first, scroll down after a moment
            off = int(round(lerp(st, off, e_io(prog(r, vis[-1][0] + 1.6, 1.0)))))
    show = vis[off:off + n]
    y0 = 14 + TLH / 2
    # glow bands first
    i = 0
    while i < len(show):
        k = show[i][2]
        if k:
            j = i
            while j + 1 < len(show) and show[j + 1][2] == k: j += 1
            a = e_out(prog(r, KT[k], 0.4))
            col = KCOL[k]
            c.glow(8, 14 + i * TLH - 2, pw - 16, (j - i + 1) * TLH + 4, col, 0.55 * a, 22, r=10)
            c.rect(8, 14 + i * TLH - 2, pw - 16, (j - i + 1) * TLH + 4, 10, fill=mix((14, 14, 13), col, 0.16 * a + 0.02), outline=mix((14, 14, 13), col, 0.7 * a), width=2)
            i = j + 1
        else: i += 1
    for i, (t, txt, k, full) in enumerate(show):
        col = WHITE if k else (GREEN if full.startswith("===") else MUTED if full.startswith("[to ") is False and not full.startswith(" ") and not full.startswith("-") else LBLUE)
        if full.startswith("===") or full.startswith("[to "): col = GREEN if full.startswith("===") else LBLUE
        elif not k: col = (200, 200, 196)
        c.text(24, y0 + i * TLH, txt, TFS, col, "b" if full.startswith("===") else "r", mono=True)
    return img, show

def paste_round(c, pil, x, y, w, h, r=12):
    im = pil.resize((int(w * S), int(h * S)), Image.LANCZOS)
    m = Image.new("L", im.size, 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, im.size[0] - 1, im.size[1] - 1), r * S, fill=255)
    c.img.paste(im, (int(x * S), int(y * S)), m)

def crop_box(box, aspect):
    x0, y0, w, h = box
    return (x0, y0, x0 + w, y0 + h)

# ---------- split screen ----------
LX, LW = 30, 780; RX, RW = 830, 1060; WY, WH = 108, 880
def lerp_box(a, b, k): return tuple(lerp(p, q, k) for p, q in zip(a, b))
BOARD = (390, 20, 1040, 811)
MEM_BOX = (385, 60, 860, 671); CODE_BOX = (350, 89, 1040, 811)

def label(c, x, y, text, col, alpha=1.0, anchor="l"):
    c.text(x, y, text, 38, col, "s", anchor=anchor, alpha=alpha)

def step_label(r):
    if r < 5.2: return "Two sessions start on one project"
    if r < 10.2: return "Session A edits shop/db.py"
    if r < 15.3: return "Session B is told what A changed"
    if r < 20.3: return "Session B is warned before editing"
    if r < 25.3: return "A next-day session starts informed"
    if r < 27.9: return "A wrong note is taken back"
    return "Callers elsewhere are named"

def scene_split(c, t):
    # recording time and phase
    if t < T_DEMO1 - 0.0: phase, r = "demo", R0 + (t - T_DEMO0) * SPEED
    elif t < T_MEM1: phase, r = "mem", 0
    else: phase, r = "code", 0
    r = min(r, 30.6) if phase == "demo" else 30.6
    # window frames
    window(c, LX, WY, LW, WH, "terminal: demo scenario" if phase != "x" else "")
    window(c, RX, WY, RW, WH, "127.0.0.1:7755  dashboard")
    cw, ch = RW - 4, WH - 56
    tw_, th_ = LW - 4, WH - 56
    # terminal with small zoom on a fresh warning
    timg, show = terminal_image(tw_, th_, r)
    focus = None; z = 1.0
    for k in ("digest", "collision", "callers"):
        d = r - KT[k]
        if phase == "demo" and 0.0 <= d < 3.2:
            z = 1 + 0.2 * e_out(prog(d, 0.1, 0.5)) * (1 - e_in(prog(d, 2.4, 0.8)))
            ys = [i for i, row in enumerate(show) if row[2] == k]
            if ys: focus = 14 + (ys[0] + ys[-1] + 1) / 2 * TLH
    if focus is not None and z > 1.001:
        cx, cy = 12 + tw_ / (2 * z), min(max(focus, th_ / (2 * z)), th_ - th_ / (2 * z))
        bw, bh = tw_ / z, th_ / z
        timg = timg.crop((int((cx - bw / 2) * S), int((cy - bh / 2) * S), int((cx + bw / 2) * S), int((cy + bh / 2) * S)))
    paste_round(c, timg, LX + 2, WY + 54, tw_, th_, 10)
    # dashboard
    if phase == "demo":
        Z = (390, 20, 780, 608)
        zk = e_io(prog(r, 9.6, 0.8)) * (1 - e_io(prog(r, 19.4, 0.8))) + e_io(prog(r, 27.2, 0.8))
        box = lerp_box(BOARD, Z, min(zk, 1.0))
        src = frame(F15, r, None)
        vlabel = "The board updates live"
        tag = ("Demo scenario on a sample project", ORANGE)
    elif phase == "mem":
        src = frame(F15, view_start(F15, "memory") + 0.6 + (t - T_LIVE1), "memory"); box = MEM_BOX; vlabel = "What the next session is told"
        tag = ("Demo scenario on a sample project", ORANGE)
    else:
        src = frame(F13, view_start(F13, "code") + 0.6 + (t - T_MEM1), "code"); box = CODE_BOX; vlabel = "Who calls what: Code view"
        tag = ("Demo scenario on a sample project", ORANGE)
    x0, y0, w, h = box
    paste_round(c, src.crop((int(x0), int(y0), int(x0 + w), int(y0 + h))), RX + 2, WY + 54, cw, ch, 10)
    # labels + caption
    label(c, LX + 6, 58, step_label(r) if phase == "demo" else ("Output of the same run" if phase == "mem" else "Output of the same run"), WHITE)
    label(c, RX + 6, 58, vlabel, GREEN)
    c.text(LX + 6, 1038, "Recorded from the running product", 34, MUTED, "m")
    c.text(W - 30, 1038, tag[0] + (" · waits shortened" if phase == "demo" else ""), 34, tag[1], "m", anchor="r")

# ---------- real Claude Code sessions ----------
def _load_take():
    notes = json.load(open(f"{TAKE}/notes.json")); proj = notes["project"]; t0 = notes["t0"]
    ev = {"A": [], "B": []}
    for w in "AB":
        for l in open(f"{TAKE}/{w}.jsonl"):
            r = json.loads(l); e = json.loads(r["ev"])
            if e.get("type") == "assistant":
                for cb in e["message"]["content"]:
                    if cb["type"] == "tool_use":
                        i = cb["input"]; nm = cb["name"]
                        if nm in ("Edit", "Write", "MultiEdit", "Read"): arg = os.path.relpath(os.path.realpath(i["file_path"]), os.path.realpath(proj))
                        else: arg = (i.get("command") or "").replace(proj, ".").split("\n")[0]
                        ev[w].append((r["t"], nm, arg))
                    elif cb["type"] == "text": ev[w].append((r["t"], "says", cb["text"]))
    hooks = []
    for l in open(f"{TAKE}/hooks.jsonl"):
        r = json.loads(l)
        if r["output"]: hooks.append((r["ts"] - t0, r["output"]["hookSpecificOutput"]["additionalContext"]))
    return ev, hooks
LEV, LHOOKS = _load_take()
MSG_T = LHOOKS[0][0]  # first injected message, goes to session B (about shop/audit.py)
MSG_TXT = LHOOKS[0][1]
B_SAY_T = next(t for t, k, a in LEV["B"] if k == "says")
B_SAY = next(a for t, k, a in LEV["B"] if k == "says").split("\n")[0]
def live_real(u):  # u = seconds into the block (8 s) -> real time of take
    pts = [(0, 5.0), (2.8, MSG_T - 0.2), (3.1, MSG_T + 0.1), (7.4, B_SAY_T + 0.2), (8.0, B_SAY_T + 1.0)]
    for (u0, r0), (u1, r1) in zip(pts, pts[1:]):
        if u <= u1: return lerp(r0, r1, clamp01((u - u0) / (u1 - u0)))
    return pts[-1][1]
def clip(s, n): return s if len(s) <= n else s[: n - 1] + "…"
def wrap_px(text, size, maxw, w="r", mono=False): return wrap(text, size, maxw, w, mono)

def scene_live(c, t):
    u = t - T_DEMO1; rt = live_real(u)
    label(c, 40, 58, "Real Claude Code sessions", GREEN)
    c.text(W - 40, 58, "Two sessions, same project, started together", 34, MUTED, "m", anchor="r")
    colw = 905
    for i, who in enumerate("AB"):
        x = 40 + i * (colw + 30)
        window(c, x, 108, colw, 880, "session " + who)
        c.text(x + 26, 190, "Session " + who, 34, A_COL if who == "A" else B_COL, "s")
        c.text(x + 26 + tw("Session X  ", 34, "s"), 190, "renames get_order" if who == "A" else "adds shop/audit.py", 34, MUTED, "m")
        evs = [e for e in LEV[who] if e[0] <= rt and e[1] != "says"]
        evs = evs[-5:]
        for j, (et, nm, arg) in enumerate(evs):
            y = 252 + j * 48
            c.text(x + 26, y, f"{et:4.1f}s", 30, DIM, "r", mono=True)
            c.text(x + 130, y, nm, 30, LBLUE if nm in ("Edit", "Write", "MultiEdit") else MUTED, "b", mono=True)
            c.text(x + 130 + tw(nm + " ", 30, "b", True), y, clip(arg, 33 - len(nm)), 30, (210, 210, 206), "r", mono=True)
    # injected message into B
    xb = 40 + colw + 30
    if rt >= MSG_T:
        a = e_out(prog(rt, MSG_T, 0.5)); 
        lines = []
        for part in MSG_TXT.split("\n"):
            lines += wrap(part, 30, colw - 70, "m")
        lines = lines[:9]
        hh = 60 + 42 * len(lines)
        y0 = 500
        c.glow(xb + 14, y0, colw - 28, hh, ORANGE, 0.6 * a, 24, r=14)
        c.rect(xb + 14, y0, colw - 28, hh, 14, fill=mix(PANEL, ORANGE, 0.14), outline=ORANGE, width=3, alpha=a)
        c.text(xb + 36, y0 + 28, "Injected into session B before its edit", 30, ORANGE, "s", alpha=a)
        for j, l in enumerate(lines): c.text(xb + 36, y0 + 82 + j * 42, l, 30, WHITE, "m", alpha=a)
    if rt >= B_SAY_T:
        a = e_out(prog(rt, B_SAY_T, 0.4))
        ls = wrap("B then says: " + B_SAY, 30, colw - 60, "m")[:4]
        for j, l in enumerate(ls): c.text(xb + 26, y0 + hh + 40 + j * 40, l, 30, GREEN, "m", alpha=a)
    c.text(W - 30, 1038, "Real Claude Code sessions · log of one take, sped up", 34, GREEN, "m", anchor="r")
    c.text(40, 1038, "Recorded from the running product", 34, MUTED, "m")

A_COL = (110, 168, 255); B_COL = (244, 114, 182)
try:
    from scenes_a import A_COL, B_COL
except Exception: pass

def seg_split(c, t):
    if t < T_DEMO1 - 0.0 or t >= T_LIVE1: scene_split(c, t)
    else: scene_live(c, t)

def s_hook(c, t): SS.s_hook(c, t)
def s_stats(c, t): SS.s_stats(c, t)
def s_end(c, t): SS.s_end(c, t)
SEGS = [(0.0, 6.0, lambda c, t: SS.s_hook(c, t)), (6.0, 36.0, lambda c, t: seg_split(c, t + 6.0)),
        (36.0, 48.0, lambda c, t: SS.s_stats(c, t)), (48.0, TOTAL, lambda c, t: SS.s_end(c, t))]

def scene_canvas(i, t):
    c = new_canvas(t); SEGS[i][2](c, max(t - SEGS[i][0], 0.0)); return c

def render(t):
    i = max(k for k, s in enumerate(SEGS) if s[0] <= t + 1e-9)
    img = scene_canvas(i, t).img
    if i + 1 < len(SEGS) and t > SEGS[i + 1][0] - XF:
        img = Image.blend(img, scene_canvas(i + 1, t).img, e_io((t - (SEGS[i + 1][0] - XF)) / XF))
    out = Canvas(img)
    out.rect(0, H - 6, W, 6, 0, fill=(26, 26, 24)); out.rect(0, H - 6, W * clamp01(t / TOTAL), 6, 0, fill=GREEN)
    return finish(out)

def _job(i): return render(i / FPS).tobytes()

def video(path):
    cmd = ["/opt/homebrew/bin/ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-an", "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p", "-movflags", "+faststart", path]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(10) as pool:
        for b in pool.imap(_job, range(int(TOTAL * FPS)), chunksize=4): p.stdin.write(b)
    p.stdin.close(); p.wait()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "frames":
        os.makedirs(f"{HERE}/tmp/live", exist_ok=True)
        ts = [float(x) for x in sys.argv[2:]]
        with Pool(10) as pool: ims = pool.map(render, ts)
        for t, im in zip(ts, ims): im.save(f"{HERE}/tmp/live/s{t:06.2f}.png")
    else:
        os.makedirs(f"{HERE}/out", exist_ok=True)
        out = f"{HERE}/out/MeshAgents-60s-live.mp4"; video(out)
        import shutil; shutil.copy(out, "/Users/dezloper/Desktop/MeshAgents-60s-live.mp4")
