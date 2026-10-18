"""One take of the screen demo: three real Claude Code sessions in a temp copy of the sample project, the dashboard
recorded through the DevTools Protocol the whole time.

    .venv/bin/python video/record_screen.py <take>   ->  video/rec/screen/take<N>/{frames/, frames.json, s1.jsonl, s2.jsonl, s3.jsonl, hooks.jsonl, notes.json}

Session 1 starts after a few idle seconds, session 2 six seconds later, session 3 once both are done. Workspace rec_screen
(never the demo's own). The dashboard is stopped and the graph dropped at the end.
"""
import asyncio, base64, json, os, shutil, subprocess, sys, tempfile, threading, time, urllib.request
import websockets

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
from baton import demo_kit  # noqa: E402

take = sys.argv[1]
OUT = os.path.join(ROOT, "video", "rec", "screen", "take" + take)
PORT, DBG, WS = 7756, 9334, "rec_screen"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PY = os.path.join(ROOT, ".venv", "bin", "python")
ZOOM = float(os.environ.get("REC_ZOOM", "1.5"))  # CSS 1200x720 (wide enough for the feed on the right), screenshots 1800x1080


async def main():
    shutil.rmtree(OUT, ignore_errors=True); os.makedirs(os.path.join(OUT, "frames"))
    tmp = tempfile.mkdtemp(prefix="rec_screen_")
    proj = os.path.join(tmp, "shop-demo")
    demo_kit.create_project(proj)
    hooklog = os.path.join(OUT, "hooks.jsonl")
    base = {k: v for k, v in os.environ.items() if not k.startswith("CLAUDE_CODE") and k != "CLAUDECODE"}
    base.update(BATON_WORKSPACE=WS, BATON_DEBUG_LOG=hooklog, CLAUDE_PROJECT_DIR=proj, PYTHONDONTWRITEBYTECODE="1")
    from baton.graph.client import Store
    Store(WS).drop(); Store(WS).bootstrap()  # like a fresh demo setup: an empty graph, not a missing one
    uienv = dict(base, PYTHONPATH=os.path.join(ROOT, "src"))
    ui = subprocess.Popen([PY, "-B", "-m", "baton.cli", "ui", "--workspace", WS, "--port", str(PORT)], env=uienv,
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
            await call("Emulation.setDeviceMetricsOverride", width=1200, height=720, deviceScaleFactor=ZOOM, mobile=False)
            await call("Emulation.setEmulatedMedia", features=[{"name": "prefers-color-scheme", "value": "dark"}])
            await call("Page.navigate", url=f"http://127.0.0.1:{PORT}/")
            await asyncio.sleep(1.5)
            t0 = time.time()
            frames, marks = [], {}
            state = {"phase": "idle", "s1": None, "s2": None, "s3": None}

            def session(k, prompt):
                cmd = ["claude", "-p", "--model", "claude-haiku-5-5", "--permission-mode", "acceptEdits", "--allowedTools", "Write", "Edit", "MultiEdit", "Bash",
                       "--plugin-dir", os.path.join(ROOT, "plugin"), "--output-format", "stream-json", "--verbose"]
                marks["start_" + k] = round(time.time() - t0, 3)
                p = subprocess.Popen(cmd, cwd=proj, env=base, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                p.stdin.write(prompt); p.stdin.close()
                with open(os.path.join(OUT, k + ".jsonl"), "w") as f:
                    for ln in p.stdout:
                        f.write(json.dumps({"t": round(time.time() - t0, 3), "ev": ln.rstrip("\n")}) + "\n"); f.flush()
                p.wait(); state[k] = p.returncode; marks["end_" + k] = round(time.time() - t0, 3)

            async def grab(seconds=None, until=None, view="board"):
                end = None if seconds is None else time.time() + seconds
                while True:
                    if end is not None and time.time() >= end: break
                    if until is not None and until(): break
                    r = await call("Page.captureScreenshot", format="jpeg", quality=90)
                    name = f"frames/{len(frames):05d}.jpg"
                    open(os.path.join(OUT, name), "wb").write(base64.b64decode(r["data"]))
                    frames.append({"t": round(time.time() - t0, 3), "file": name, "view": view})

            await grab(seconds=4.0)
            th1 = threading.Thread(target=session, args=("s1", demo_kit.PROMPTS[0])); th1.start()
            await grab(seconds=6.0)
            th2 = threading.Thread(target=session, args=("s2", demo_kit.PROMPTS[1])); th2.start()
            await grab(until=lambda: state["s1"] is not None and state["s2"] is not None)
            await grab(seconds=3.0)
            th3 = threading.Thread(target=session, args=("s3", demo_kit.PROMPTS[2])); th3.start()
            await grab(until=lambda: state["s3"] is not None)
            await grab(seconds=3.0)
            marks["click_next"] = round(time.time() - t0, 3)
            await call("Runtime.evaluate", expression="Array.from(document.querySelectorAll('a,button')).filter(e=>/Next helper/.test(e.textContent))[0].click()")
            await grab(seconds=5.0, view="memory")
            json.dump(frames, open(os.path.join(OUT, "frames.json"), "w"))
            span = frames[-1]["t"] - frames[0]["t"]
            json.dump({"t0": t0, "rc": {k: state[k] for k in ("s1", "s2", "s3")}, "marks": marks, "project": proj, "zoom": ZOOM}, open(os.path.join(OUT, "notes.json"), "w"))
            print("take", take, "frames", len(frames), "span %.1f" % span, "fps %.1f" % (len(frames) / span), marks, state)
    finally:
        chrome.terminate(); ui.terminate()
        shutil.rmtree(prof, ignore_errors=True)
        sys.path.insert(0, os.path.join(ROOT, "src"))
        from baton.graph.client import Store
        Store(WS).drop()


asyncio.run(main())
