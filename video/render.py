"""render(t) -> 1920x1080 frame. Deterministic; every frame is independent.
Usage: render.py frames t1 t2 ...   (PNG previews into tmp/prev)   |   render.py video out.mp4 [start end]"""
import json, os, subprocess, sys
from multiprocessing import Pool
from gfx import *
import scenes_a, scenes_b

HERE = os.path.dirname(os.path.abspath(__file__))
TIMING = json.load(open(f"{HERE}/timing.json"))
FPS = 30
FUNCS = {"hook": scenes_a.scene_hook, "clash": scenes_a.scene_clash, "enter": scenes_a.scene_enter,
         "split": scenes_b.scene_split, "board": scenes_b.scene_board, "graph": scenes_b.scene_graph,
         "numbers": scenes_b.scene_numbers, "honest": scenes_b.scene_honest, "try": scenes_b.scene_try}
SC = TIMING["scenes"]; TOTAL = TIMING["total"]; XF = TIMING["crossfade"]
TMS = [scenes_a.TM(s) for s in SC]

def scene_canvas(i, t):
    tl = t - SC[i]["start"]
    c = new_canvas(t)
    FUNCS[SC[i]["id"]](c, max(tl, 0.0), TMS[i])
    return c

def render(t):
    i = max(k for k, s in enumerate(SC) if s["start"] <= t + 1e-9)
    c = scene_canvas(i, t)
    img = c.img
    # crossfade: the end of scene i dips into the start of scene i+1
    if i + 1 < len(SC) and t > SC[i + 1]["start"] - XF:
        k = e_io((t - (SC[i + 1]["start"] - XF)) / XF)
        c2 = scene_canvas(i + 1, t)
        img = Image.blend(img, c2.img, k)
        c = Canvas(img)
    out = Canvas(img)
    # subtitles (sentences of the active scene, small fade in/out)
    sub, a = "", 0.0
    for j, sc in enumerate(SC):
        for s in sc["sentences"]:
            t0 = sc["start"] + s["t"]; t1 = t0 + s["dur"] + 0.25
            if t0 - 0.05 <= t <= t1:
                sub = s["text"]; a = min(1, (t - t0 + 0.05) / 0.2, (t1 - t) / 0.2)
    subtitle(out, sub, clamp01(a))
    # progress bar
    out.rect(0, H - 6, W, 6, 0, fill=(26, 26, 24))
    out.rect(0, H - 6, W * clamp01(t / TOTAL), 6, 0, fill=GREEN)
    return finish(out)

def _job(i):
    return render(i / FPS).tobytes()

def video(path, start=0.0, end=None):
    end = TOTAL if end is None else end
    n0, n1 = int(start * FPS), int(end * FPS)
    cmd = ["/opt/homebrew/bin/ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p", path]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(10) as pool:
        for k, b in enumerate(pool.imap(_job, range(n0, n1), chunksize=4)):
            p.stdin.write(b)
            if k % 300 == 0: print(f"frame {k}/{n1 - n0}", flush=True)
    p.stdin.close(); p.wait()

if __name__ == "__main__":
    if sys.argv[1] == "frames":
        os.makedirs(f"{HERE}/tmp/prev", exist_ok=True)
        ts = [float(x) for x in sys.argv[2:]]
        with Pool(min(10, len(ts))) as pool:
            ims = pool.map(render, ts)
        for t, im in zip(ts, ims): im.save(f"{HERE}/tmp/prev/t{t:07.2f}.png")
    else:
        video(sys.argv[2], *(float(x) for x in sys.argv[3:]))
