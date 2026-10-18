"""Silent 57.5 s cut.  render_short.py frames t...  |  render_short.py video out.mp4"""
import os, subprocess, sys
from multiprocessing import Pool
from gfx import *
from scenes_short import SEGS

HERE = os.path.dirname(os.path.abspath(__file__)); FPS = 30; XF = 0.25; TOTAL = SEGS[-1][1]

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
    if sys.argv[1] == "frames":
        os.makedirs(f"{HERE}/tmp/prev", exist_ok=True)
        ts = [float(x) for x in sys.argv[2:]]
        with Pool(10) as pool: ims = pool.map(render, ts)
        for t, im in zip(ts, ims): im.save(f"{HERE}/tmp/prev/s{t:06.2f}.png")
    else: video(sys.argv[2])
