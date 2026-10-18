"""Record real footage of the dashboard while the paced demo runs.

    .venv/bin/python video/record_capture.py          -> video/rec/board/*.jpg, video/rec/stdout.jsonl, video/rec/frames.json

Starts `meshagents ui` for workspace rec_demo on port 7755, headless Chrome (DevTools Protocol), then runs the
demo with MESHAGENTS_DEMO_PACE=2.5 while polling Page.captureScreenshot. Afterwards it opens the Memory view and the
Code view (page's own hash routes). Nothing here is drawn or faked: frames are screenshots of the running page.
"""
import asyncio, base64, json, os, shutil, subprocess, sys, tempfile, threading, time, urllib.request
import websockets

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "video", "rec")
PORT, DBG, WS = 7755, 9333, "rec_demo"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PY = os.path.join(ROOT, ".venv", "bin", "python")


async def main():
    shutil.rmtree(os.path.join(OUT, "frames"), ignore_errors=True)
    os.makedirs(os.path.join(OUT, "frames"))
    env = dict(os.environ, PYTHONPATH=os.path.join(ROOT, "src"), PYTHONDONTWRITEBYTECODE="1")
    ui = subprocess.Popen([PY, "-B", "-m", "baton.cli", "ui", "--workspace", WS, "--port", str(PORT)], env=env,
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    prof = tempfile.mkdtemp(prefix="rec_chrome_")
    chrome = subprocess.Popen([CHROME, "--headless=new", f"--remote-debugging-port={DBG}", "--window-size=1440,900",
                               f"--user-data-dir={prof}", "--hide-scrollbars", "--no-first-run", "about:blank"],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(60):
            try:
                tabs = json.load(urllib.request.urlopen(f"http://127.0.0.1:{DBG}/json"))
                page = [t for t in tabs if t["type"] == "page"][0]
                urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/state").read()
                break
            except Exception:
                time.sleep(0.5)
        async with websockets.connect(page["webSocketDebuggerUrl"], max_size=None) as ws:
            n = 0
            async def call(method, **params):
                nonlocal n
                n += 1
                await ws.send(json.dumps({"id": n, "method": method, "params": params}))
                while True:
                    m = json.loads(await ws.recv())
                    if m.get("id") == n:
                        return m.get("result", {})
            zoom = float(os.environ.get("REC_ZOOM", "1.5"))  # browser zoom 150%: page lays out at 960x600 CSS px, screenshots are 1440x900
            await call("Emulation.setDeviceMetricsOverride", width=int(1440 / zoom), height=int(900 / zoom), deviceScaleFactor=zoom, mobile=False)
            await call("Emulation.setEmulatedMedia", features=[{"name": "prefers-color-scheme", "value": "dark"}])
            await call("Page.navigate", url=f"http://127.0.0.1:{PORT}/")
            await asyncio.sleep(2.0)
            t0 = time.monotonic()
            frames, lines = [], []
            done = {"demo": False}

            def run_demo():
                e = dict(env, MESHAGENTS_DEMO_PACE="2.5", MESHAGENTS_DEMO_WORKSPACE=WS, PYTHONUNBUFFERED="1")
                p = subprocess.Popen([PY, "-B", os.path.join(ROOT, "demo", "run_demo.py")], env=e, stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT, text=True, bufsize=1)
                for ln in p.stdout:
                    lines.append({"t": round(time.monotonic() - t0, 3), "line": ln.rstrip("\n")})
                p.wait(); done["demo"] = True

            async def grab_for(seconds=None, until=None, tag="board"):
                end = None if seconds is None else time.monotonic() + seconds
                while True:
                    if end is not None and time.monotonic() >= end: break
                    if until is not None and until(): break
                    r = await call("Page.captureScreenshot", format="jpeg", quality=88)
                    t = time.monotonic() - t0
                    name = f"frames/{len(frames):05d}.jpg"
                    open(os.path.join(OUT, name), "wb").write(base64.b64decode(r["data"]))
                    frames.append({"t": round(t, 3), "file": name, "view": tag})

            th = threading.Thread(target=run_demo, daemon=True); th.start()
            await grab_for(until=lambda: done["demo"], tag="board")
            await grab_for(seconds=1.5, tag="board")
            await call("Page.navigate", url=f"http://127.0.0.1:{PORT}/#memory")
            await asyncio.sleep(0.4)
            await grab_for(seconds=4.0, tag="memory")
            await call("Page.navigate", url=f"http://127.0.0.1:{PORT}/#code/shop/db.py")
            await asyncio.sleep(0.4)
            await grab_for(seconds=5.0, tag="code")
            json.dump(frames, open(os.path.join(OUT, "frames.json"), "w"))
            with open(os.path.join(OUT, "stdout.jsonl"), "w") as f:
                for l in lines: f.write(json.dumps(l) + "\n")
            span = frames[-1]["t"] - frames[0]["t"]
            print("frames", len(frames), "span %.1fs" % span, "fps %.1f" % (len(frames) / span), "lines", len(lines))
    finally:
        chrome.terminate(); ui.terminate()
        shutil.rmtree(prof, ignore_errors=True)


asyncio.run(main())
