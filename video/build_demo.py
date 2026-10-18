"""Screen demo cut: .venv/bin/python video/build_demo.py [frames t...]  ->  video/out/MeshAgents-demo.mp4 (silent, 58 s)

Left: three terminals that replay plain-language lines derived from the stream events and hook log of three real
Claude Code sessions (record_screen.py, take TAKE). Right: the real dashboard, screenshots recorded during the same run.
Waiting time is removed with hard cuts (marked on screen). The last 9 s are the stats image (video/stats-bento.png).
"""
import bisect, json, os, shutil, subprocess, sys
from multiprocessing import Pool
from PIL import Image, ImageDraw
from gfx import *

HERE = os.path.dirname(os.path.abspath(__file__)); FPS = 30; TOTAL = 58.0
TAKE = os.environ.get("DEMO_TAKE", "2"); REC = f"{HERE}/rec/screen/take{TAKE}"
sys.path.insert(0, os.path.join(HERE, "..", "src"))
from baton import demo_kit
PROMPTS = demo_kit.PROMPTS

NOTES = json.load(open(f"{REC}/notes.json")); T0 = NOTES["t0"]; PROJ = NOTES["project"]
FR = json.load(open(f"{REC}/frames.json")); FT = [f["t"] for f in FR]
_img = {}
def frame(r):
    i = min(max(bisect.bisect_left(FT, r), 0), len(FT) - 1)
    p = f"{REC}/{FR[i]['file']}"
    if p not in _img:
        if len(_img) > 4: _img.clear()
        _img[p] = Image.open(p).convert("RGB")
    return _img[p]

# video time -> recording time. (video start, video end, recording start); hard cuts between rows
SEGS = [(0.0, 4.0, 0.05), (6.5, 23.5, 4.0), (23.5, 29.0, 34.0), (29.0, 37.0, 46.0), (37.0, 40.0, 71.0), (40.0, 43.0, 87.0), (43.0, 49.0, 91.5)]
CUTS = [23.5, 29.0, 37.0, 40.0, 43.0]
def v2rec(v):
    if 4.0 <= v < 6.5: return 3.9
    for vs, ve, rs in SEGS:
        if vs <= v < ve: return rs + (v - vs)
    return min(SEGS[-1][2] + (v - SEGS[-1][0]), FT[-1])
def rec2v(r):
    """first video time at which recording time r has been reached"""
    for vs, ve, rs in SEGS[1:]:
        if r <= rs + (ve - vs): return vs + max(r - rs, 0.0)
    return 1e9

# ---------- terminal lines from the real run ----------
def rel(p): return os.path.basename(p)
def load_events(k):
    ev = []
    for l in open(f"{REC}/{k}.jsonl"):
        r = json.loads(l); e = json.loads(r["ev"])
        if e.get("type") == "assistant":
            for c in e["message"]["content"]:
                if c["type"] == "tool_use": ev.append((r["t"], c["name"], c["input"]))
    return ev
EV = {k: load_events(k) for k in ("s1", "s2", "s3")}
HOOKS = []
for l in open(f"{REC}/hooks.jsonl"):
    r = json.loads(l); HOOKS.append((r["ts"] - T0, r["event"], (r["output"] or {}).get("hookSpecificOutput", {}).get("additionalContext")))
M = NOTES["marks"]
def first(k, name, pred=lambda i: True):
    return next(t for t, n, i in EV[k] if n == name and pred(i))
def cat_file(i):
    import re
    m = re.search(r"cat\s+(?:shop/)?([\w./]+\.py)", i.get("command", "")); return m.group(1).split("/")[-1] if m else None
# the first Bash that cats a file, per session
def first_read(k):
    for t, n, i in EV[k]:
        if n == "Bash" and cat_file(i): return t, cat_file(i)
LINES = {1: [], 2: [], 3: []}
t, f = first_read("s1"); LINES[1].append((t, "Reading " + f, "plain"))
t = first("s1", "Edit"); LINES[1].append((t, "Editing db.py", "plain"))
LINES[1].append((M["end_s1"], "Done", "done"))
t, f = first_read("s2"); LINES[2].append((t, "Reading " + f, "plain"))
tw_ = next(h[0] for h in HOOKS if h[2] and "Possible collision on shop/api.py" in h[2])  # the real heads-up that reached helper 2
LINES[2].append((tw_, "Heads-up: another helper changed api.py", "warn"))
LINES[2].append((first("s2", "Edit") if False else [t for t, n, i in EV["s2"] if n == "Edit"][-1], "Used the new signature", "plain"))
LINES[2].append((M["end_s2"], "Done", "done"))
rule_t = next(h[0] for h in HOOKS if h[2] and "never use sqlite" in h[2] and h[0] > M["start_s3"])  # session start briefing of helper 3
LINES[3].append((rule_t, "Heads-up: never use sqlite", "warn"))
t, f = first_read("s3"); LINES[3].append((t, "Reading " + f, "plain"))
tj = next(t for t, n, i in EV["s3"] if n == "Write" and "json" in i.get("content", "").lower() and i["file_path"].endswith("db.py"))
LINES[3].append((tj, "Saved orders to a JSON file", "plain"))
LINES[3].append((M["end_s3"], "Done", "done"))
ENTER = {1: M["start_s1"], 2: M["start_s2"], 3: M["start_s3"]}
VENTER = {1: 6.5, 2: rec2v(M["start_s2"]), 3: rec2v(M["start_s3"])}
VENTER[2] = VENTER[2] - 0.0
VLINE = {k: [(rec2v(t), txt, kind) for t, txt, kind in v] for k, v in LINES.items()}

# ---------- drawing ----------
FS, LH = 30, 36
def terminal(c, k, x, y, w, h, v):
    c.rect(x, y, w, h, 14, fill=(16, 16, 15), outline=(54, 54, 50), width=2)
    c.rect(x, y, w, 38, 14, fill=(30, 30, 28)); c.rect(x, y + 24, w, 14, 0, fill=(30, 30, 28))
    for i, col in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]): c.circle(x + 24 + i * 24, y + 19, 7, fill=col)
    c.text(x + w / 2, y + 19, f"Terminal {k}", 26, MUTED, "m", anchor="m")
    prompt = PROMPTS[k - 1]
    ve = VENTER[k]; vs = ve - 2.5
    n = int(len(prompt) * e_io_lin(prog(v, vs, 2.5))) if v < ve else len(prompt)
    typed = prompt[:n]
    maxw = w - 40 - 36 - tw("> ", FS, "r", True)
    lines = wrap(prompt, FS, maxw, "r", True)
    # box sized for the full prompt so nothing jumps
    bh = len(lines) * LH + 18; by = y + 48
    sent = v >= ve
    c.rect(x + 18, by, w - 36, bh, 10, fill=(20, 20, 19), outline=(120, 120, 114) if not sent else (70, 70, 66), width=2)
    shown = wrap(typed, FS, maxw, "r", True) if typed else [""]
    for j, ln in enumerate(shown):
        c.text(x + 36, by + 9 + LH / 2 + j * LH, ("> " if j == 0 else "  ") + ln, FS, WHITE if not sent else (190, 190, 186), "r", mono=True)
    if not sent and (v * 1.8) % 1.0 < 0.6:
        j = len(shown) - 1; cx = x + 36 + tw("> " + shown[-1], FS, "r", True)
        c.rect(cx + 2, by + 9 + j * LH + 5, 14, LH - 8, 0, fill=GREEN)
    y2 = by + bh + 12
    for t, txt, kind in VLINE[k]:
        if v >= t:
            col = ORANGE if kind == "warn" else GREEN if kind == "done" else WHITE
            bul = ORANGE if kind == "warn" else GREEN
            c.text(x + 30, y2 + LH / 2, "●" if kind != "done" else "✓", FS - 4, bul, "r", mono=True)
            c.text(x + 30 + 2 * tw("a", FS, "r", True), y2 + LH / 2, txt, FS, col, "r", mono=True)
            y2 += LH
def e_io_lin(p): return p
def term_height(k):
    maxw = 800 - 40 - 36 - tw("> ", FS, "r", True)
    n = len(wrap(PROMPTS[k - 1], FS, maxw, "r", True))
    return 48 + n * LH + 18 + 12 + len(LINES[k]) * LH + 14

def paste_round(c, pil, x, y, w, h, r=10):
    im = pil.resize((int(w * S), int(h * S)), Image.LANCZOS)
    m = Image.new("L", im.size, 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, im.size[0] - 1, im.size[1] - 1), r * S, fill=255)
    c.img.paste(im, (int(x * S), int(y * S)), m)

RX, RW = 826, 1084; CROPX = 348
# zoom 0 = the whole board with the feed; 1 = zoomed on the feed (when a heads-up lands)
FOCUS = [(0, 0.5), (6.6, 0.5), (7.4, 0), (13.2, 0), (13.9, 1), (18.6, 1), (19.3, 0), (23.8, 0), (24.4, 1), (28.4, 1), (29.1, 0), (33.6, 0), (34.2, 1), (36.4, 1), (37.0, 0), (49, 0)]
def focus(v):
    for (a, x), (b, y) in zip(FOCUS, FOCUS[1:]):
        if a <= v < b: return lerp(x, y, e_io(prog(v, a, b - a)))
    return 0.0
CW = 1000
def dash(c, v):
    ch = 940.0
    wy = 12; wh = 52 + ch + 4
    c.rect(RX, wy, RW, wh, 16, fill=PANEL, outline=BORDER, width=2)
    c.rect(RX, wy, RW, 52, 16, fill=PANEL2); c.rect(RX, wy + 30, RW, 22, 0, fill=PANEL2)
    for i, col in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]): c.circle(RX + 28 + i * 26, wy + 26, 8, fill=col)
    c.text(RX + RW / 2, wy + 26, "MeshAgents dashboard", 26, MUTED, "m", anchor="m")
    r = v2rec(v); i = min(max(bisect.bisect_left(FT, r), 0), len(FT) - 1)
    mem = FR[i]["view"] == "memory"
    x0 = int(lerp(CROPX, 800, 0 if mem else focus(v))); y0 = 40 if mem else 100
    src = frame(r).crop((x0, y0, x0 + CW, y0 + int(CW * ch / (RW - 4))))
    paste_round(c, src, RX + 2, wy + 52, RW - 4, ch, 10)
    for cv in CUTS:
        if 0 <= v - cv < 1.1:
            a = e_out(prog(v - cv, 0, 0.12)) * (1 - e_in(prog(v - cv, 0.8, 0.3)))
            pill(c, RX + RW - 24, wy + 26, "Waiting time cut", 26, BG, ORANGE, padx=18, h=40, anchor="r", alpha=a)
    return wy + wh

BENTO = Image.open(f"{HERE}/stats-bento.png").convert("RGB")
def scene(v):
    c = Canvas(Image.new("RGB", (W * S, H * S), BG))
    x = 10; y = 10
    for k in (1, 2, 3):
        h = term_height(k); terminal(c, k, x, y, 800, h, v); y += h + 8
    bottom = dash(c, v)
    c.text(RX + RW, bottom + 24, "Recorded from real Claude Code sessions. Waiting time cut.", 26, MUTED, "m", anchor="r")
    return c

def render(t):
    img = finish(scene(min(t, 48.9)))
    if t >= 48.75:
        k = e_io(prog(t, 48.75, 0.45)); img = Image.blend(img, BENTO, k)
    return img
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
        os.makedirs(f"{HERE}/tmp/demo", exist_ok=True)
        ts = [float(x) for x in sys.argv[2:]]
        with Pool(10) as pool: ims = pool.map(render, ts)
        for t, im in zip(ts, ims): im.save(f"{HERE}/tmp/demo/s{t:06.2f}.png")
    else:
        os.makedirs(f"{HERE}/out", exist_ok=True)
        out = f"{HERE}/out/MeshAgents-demo.mp4"; video(out)
        shutil.copy(out, "/Users/dezloper/Desktop/MeshAgents-demo.mp4")
