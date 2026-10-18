"""One take of two real Claude Code sessions on a copy of evals/clash/fixture (tickets A and B of level L8).

    .venv/bin/python video/record_live.py <take-number>   -> video/rec/live/take<N>/{A,B}.jsonl, hooks.jsonl, notes.json
"""
import json, os, shutil, subprocess, sys, tempfile, threading, time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
take = sys.argv[1]
OUT = os.path.join(ROOT, "video", "rec", "live", "take" + take)
shutil.rmtree(OUT, ignore_errors=True); os.makedirs(OUT)
tasks = json.load(open(os.path.join(ROOT, "evals", "clash", "tasks.json")))
lvl = tasks["levels"]["L8"]
tmp = tempfile.mkdtemp(prefix="rec_live_proj_")
proj = os.path.join(tmp, "project")
shutil.copytree(os.path.join(ROOT, "evals", "clash", "fixture"), proj)
sh = lambda *a: subprocess.run(a, cwd=proj, check=True, capture_output=True)
sh("git", "init", "-q"); sh("git", "add", "-A"); sh("git", "-c", "user.name=rec", "-c", "user.email=rec@local", "commit", "-q", "-m", "start")
hooklog = os.path.join(OUT, "hooks.jsonl")
env = {k: v for k, v in os.environ.items() if not k.startswith("CLAUDE_CODE") and k != "CLAUDECODE"}
env.update(BATON_WORKSPACE="rec_live", BATON_DEBUG_LOG=hooklog, CLAUDE_PROJECT_DIR=proj, PYTHONDONTWRITEBYTECODE="1")
from_pr = lambda who: tasks["wrapper"].replace("{DIR}", proj).replace("{TICKET}", lvl["agents"][who])
t0 = time.time()
done = {}

def run(who):
    cmd = ["claude", "-p", "--model", "claude-haiku-5-5", "--permission-mode", "acceptEdits", "--allowedTools", "Write", "Edit", "MultiEdit", "Bash",
           "--plugin-dir", os.path.join(ROOT, "plugin"), "--output-format", "stream-json", "--verbose"]
    p = subprocess.Popen(cmd, cwd=proj, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    p.stdin.write(from_pr(who)); p.stdin.close()
    with open(os.path.join(OUT, who + ".jsonl"), "w") as f:
        for ln in p.stdout:
            f.write(json.dumps({"t": round(time.time() - t0, 3), "ev": ln.rstrip("\n")}) + "\n"); f.flush()
    p.wait(); done[who] = p.returncode
    open(os.path.join(OUT, who + ".err"), "w").write(p.stderr.read())

ths = [threading.Thread(target=run, args=(w,)) for w in "AB"]
for th in ths: th.start()
for th in ths: th.join()
json.dump({"t0": t0, "rc": done, "project": proj, "level": "L8", "tickets": "A,B"}, open(os.path.join(OUT, "notes.json"), "w"))
print("take", take, "rc", done, "secs %.0f" % (time.time() - t0))
