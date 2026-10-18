# Recording the demo video yourself (OBS, one take)

Goal: 60 to 75 seconds of real footage. Everything below runs on your Mac with the repo at `~/Desktop/baton`.
The scripted demo drives the same hook code the plugin uses, so say "demo scenario on a sample project" when you talk about it.

## Pre-flight checklist
- Docker Desktop is running. Nothing else uses port 6379, 7777 or 3000.
- Screen: 1920x1080, notifications off (Focus mode), Do Not Disturb on, desktop clean.
- Terminal: font size 20 to 22, dark theme, window about 900 px wide, on the LEFT half of the screen.
- Browser: one window on the RIGHT half, zoom 150 percent (Cmd and plus), two tabs: the dashboard and the FalkorDB Browser. Dark mode.
- OBS: one scene, "Display Capture" of the main screen, canvas 1920x1080, 30 fps, MP4 or MKV, no audio source if you add voice later; or enable the mic if you talk live.
- Dry run once. The demo drops and recreates its graph, so a dry run is harmless.

## Commands, in order
Terminal (left):
```sh
cd ~/Desktop/baton
docker compose up -d
.venv/bin/meshagents doctor
.venv/bin/meshagents ui --workspace demo --port 7777 &      # dashboard, prints http://127.0.0.1:7777
```
Browser (right), tab 1: open http://127.0.0.1:7777 (Board). Start the OBS recording now.

Seed with the paced demo (about 3 seconds between steps, about 70 seconds in total):
```sh
MESHAGENTS_DEMO_WORKSPACE=demo MESHAGENTS_DEMO_PACE=3 .venv/bin/python demo/run_demo.py
```
While it runs, keep the Board visible. When it ends, click Memory in the sidebar, then Code.

FalkorDB Browser, tab 2: http://localhost:3000, graph `baton_demo`. Paste two or three queries from `demo/queries.cypher`:
- query 1 (whole picture), run it and drag nodes a little;
- query 3 (decisions about shop/db.py);
- query 5 (blast radius of a retracted finding).
Stop the recording.

## What to say (about 120 words)
1. Board, before the demo (5 s): "Two coding helpers work on one project. They cannot see each other."
2. Steps 1 and 2 (10 s): "Session A changes a function in db.py. Nobody typed anything. The change is noted by itself, and the board shows it."
3. Steps 3 and 4 (15 s): "Session B is about to edit a file that depends on it. It is told first. Then it goes for the same file as A. It gets a collision warning before it edits."
4. Step 5 (8 s): "Next day a new session starts. It is handed the notes, the rules and the last status."
5. Steps 6 and 7 (12 s): "A wrong note can be taken back, and everything built on it is flagged. When A changes how a function is called, the callers are named."
6. Memory, then Code views (10 s): "This is exactly what the next session will be told. And here is who calls what."
7. FalkorDB Browser (10 s): "Under the hood it is a graph in FalkorDB. Every warning is a question the graph answers: who is in this file, what breaks if I change it, what was this note based on."

## OPTIONAL live part: two real Claude Code sessions (about 30 to 40 s)
Uses your subscription, a few cents of usage. Each session is told one ticket.
```sh
cd ~/Desktop/baton
P=$(mktemp -d)/project && cp -R evals/clash/fixture "$P" && git -C "$P" init -q && git -C "$P" add -A \
  && git -C "$P" -c user.name=rec -c user.email=rec@local commit -qm start
export BATON_WORKSPACE=live_rec BATON_DEBUG_LOG=/tmp/live_rec.log CLAUDE_PROJECT_DIR="$P"
.venv/bin/meshagents ui --workspace live_rec --port 7778 &    # optional second board at http://127.0.0.1:7778
```
Open two terminal windows (top and bottom of the left half). In each: `cd "$P"` after exporting the same variables, then start
`claude --plugin-dir ~/Desktop/baton/plugin --model claude-haiku-5-5 --permission-mode acceptEdits`.
Paste the prompts at the same moment (one in each window):

Session A:
```
In shop/db.py rename the function get_order to load_order (same behaviour). Update every caller in the project, including shop/api.py and the files under tests/, so that nothing refers to get_order any more. When done, reply in at most 4 lines.
```
Session B:
```
Add shop/audit.py with order_total(order_id): it returns the total_cents of the stored order, or None when no such order exists. Read the order with shop.db.get_order(order_id). When done, reply in at most 4 lines.
```
Afterwards show what was injected: `tail -n 5 /tmp/live_rec.log` (lines with `additionalContext` are the messages). It does not fire on every take; if the log shows no message, run it again (a fresh `$P`). Do not claim it as a result if it did not fire.
Clean up: `.venv/bin/python -c "import sys; sys.path.insert(0,'src'); from baton.graph.client import Store; Store('live_rec').drop()"`.

## If something fails
- `doctor` says FalkorDB not reachable: `docker compose up -d`, wait 5 seconds, run it again. Port 6379 busy: stop the other Redis.
- Board shows "Waiting for the database": the demo has not started yet, or the dashboard uses another workspace name. It must be `--workspace demo`.
- Board looks empty or old: reload the page. The page polls every 1.5 seconds; the demo uses the real clock, so leases are live right after it runs.
- Dashboard port in use: use `--port 7779` and the same in the browser.
- The demo is too fast or too slow: change `MESHAGENTS_DEMO_PACE` (seconds between steps; 0 prints everything at once).
- Graph Browser shows no `baton_demo`: run the demo first, then reload the page.
- Live Claude part: if `claude` asks to log in, run `claude` once alone and sign in. If no message appears, the sessions did not overlap; start both within a second of each other.
- Stop everything: `kill %1` for the dashboard, `docker compose down` (add `-v` to wipe data).
