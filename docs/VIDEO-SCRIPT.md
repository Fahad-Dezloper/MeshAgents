# Demo video script (target 2:30)

One person, one screen recorder, no face cam needed. Speak like you are telling a friend. Short sentences.
Every number below is copied from `docs/RESULTS.md` (rounds 6 and 7), `docs/RESULTS-RELAY.md` and `site/facts.js`.
The words in the "Say" column are a guide. Say them your own way, but keep the numbers.

## Pre-flight checklist (do this 10 minutes before you press record)
- [ ] Docker Desktop is running. `docker compose up -d`, then `docker ps` shows FalkorDB on ports 6379 and 3000.
- [ ] `.venv/bin/meshagents doctor` says everything is fine.
- [ ] Seed the demo graph **right before recording**: `.venv/bin/python -B demo/run_demo.py` (it rebuilds graph `baton_demo`).
      Live badges on the board ("working now") fade after about 15 minutes. If you wait longer, run it again.
- [ ] Start the board in a second terminal tab: `.venv/bin/meshagents ui --workspace demo`, then open http://127.0.0.1:7777.
      Without `--workspace demo` the board reads the graph of the folder you are in, and it will look empty.
- [ ] Browser tab 1: `site/index.html` opened from disk (`open site/index.html`). Add `?static` to the address to show
      everything at once with no scroll animations.
- [ ] Browser tab 2: the board at http://127.0.0.1:7777 (the sidebar has **Memory**).
- [ ] Browser tab 3: FalkorDB Browser at http://localhost:3000, graph `baton_demo` selected. Paste query 5 from
      `demo/queries.cypher` (blast radius) into the box, ready to run.
- [ ] Terminal with a clean screen and the demo command typed but not run: `.venv/bin/python -B demo/run_demo.py`.
- [ ] Browser zoom 125% to 150%. Terminal font 18 to 20 pt, about 100 columns, dark theme.
- [ ] Do Not Disturb on. Close Slack, Messages, Mail. Hide the bookmarks bar and the dock.
- [ ] Nothing personal on screen: no home path in the prompt (`cd` to the repo, then `clear`), no tokens, no email.
- [ ] Mic test: record 5 seconds and play it back. Record at 1080p.
- [ ] Do one full dry run with a timer, then re-seed the graph (step 3) just before the real take.

## Shots

| Time | Screen | Say | On-screen text |
|---|---|---|---|
| 0:00 to 0:20 | Landing page, top (the headline). Scroll slowly to the live board picture. | "Say you run two AI coding sessions on one project. You tell the first one: never use sqlite. Tomorrow, another session adds sqlite. They can't see each other, and they forget. That's the problem." | "Tell one session: never use sqlite" / "Tomorrow another adds sqlite" |
| 0:20 to 0:35 | Stay on the landing page. | "MeshAgents is a shared notebook for AI coding sessions. They read and write it on their own. It lives in a FalkorDB graph." | "MeshAgents: a shared memory for AI coding sessions" |
| 0:35 to 1:20 | Terminal, then the board. Steps below. | Steps below. | Short labels (below) |
| 1:20 to 1:45 | Browser tab 3, FalkorDB Browser. Run query 5. Hover the finding. | "Why FalkorDB? A graph answers four questions fast. Who is working on this file? What changed near it? What was this note based on, and what breaks if it's wrong? And who calls the function I just changed? This query finds everything built on one wrong note." | "4 questions a graph answers" |
| 1:45 to 2:10 | Landing page, the "Measured, not promised" section. | "Does it work? In 180 runs, 80% finished clean with it, and 53% without. For memory, in 150 runs, the second session did its job 95% of the time with it, and 45% with no memory. A notes file got 92%. Each clean result cost 29% less. On a second model it was 83% against 33%, after we fixed how it sees shell edits." | "80% vs 53% clean (180 runs)" / "95% vs 45% memory (150 runs)" / "29% cheaper per clean result" / "83% vs 33% (second model)" |
| 2:10 to 2:25 | Landing page, "What this does not prove." | "Now the honest part. Our tests are built to make sessions collide. And a plain notes file does about as well on memory. The win is that nobody has to keep it up." | "Limits: built collisions. A notes file is close on memory." |
| 2:25 to 2:30 | Landing page closer. | "It's open source. Try it. The link is below." | repo URL, "Track 2: Agent Memory and Coordination" |

### The demo, step by step (0:35 to 1:20)
The demo prints seven numbered sections. These are the real lines it prints (copied from a real run).

1. **0:35 to 0:45, session A (terminal).** Press Enter on the demo. "Session A changes a function and starts using sqlite.
   Nobody typed anything. The notebook wrote it down by itself." Point at
   `[interface] ... signature changed: get_order(order_id) -> get_order(order_id, include_cancelled=False)` and
   `[storage] shop/db.py now uses sqlite3`. Label: "Written down automatically".
2. **0:45 to 0:58, the warning (section 4).** "Now session B goes for the same file. It's told first." Point at
   `[MeshAgents] Possible collision on shop/db.py:` and
   `sess-A-storag is working on 'Ticket 12: ...' touching shop/db.py, last edit 1s ago`. Label: "Warned before the edit".
3. **0:58 to 1:04, the break message (section 7).** "A session changes how a function is called. It's told who else may break." Point at
   `You changed how shop/db.py is called (get_order: new required parameter tenant). Callers elsewhere that may now break:` and
   `shop/api.py (session sess-B-e is working in it now)`. Label: "Callers elsewhere may break".
4. **1:04 to 1:09, next day (section 5).** "The next day, a new session gets a briefing, not a blank page." Point at
   `Latest handoff from a previous session:` and `Next: migrate save_order.`
5. **1:09 to 1:16, the Memory view (board tab).** Click **Memory** in the sidebar. "This page shows exactly what a new session is told right now: rules people said, other sessions working, recent decisions, the last handoff." Label: "What a new session is told".
6. **1:16 to 1:20, taking back a wrong note.** Click back to the terminal and scroll to section 6. "If a note turns out to be wrong, one command takes it back. It lists everything built on it."
   Point at `retracted finding ... -> tainted 2 decision(s)`. Label: "Wrong note taken back: 2 decisions flagged".
   (This already happened in the seeded run. Do not retract again on camera, so the graph stays the same for the FalkorDB shot.)

If the board looks empty or says nothing is working, the live badges have faded. Run the demo again and refresh the page.

## What to click, in order
1. Landing page tab (hook and what it is). 2. Terminal: Enter on the demo. 3. Board tab: **Memory** in the sidebar.
4. Terminal: scroll to section 6. 5. FalkorDB Browser tab: run query 5. 6. Landing page tab: numbers, limits, closer.

## 30-second fallback cut
- 0:00 to 0:08. "Two AI coding sessions on one project can't see each other. MeshAgents is a shared notebook for them."
- 0:08 to 0:22. Run the demo. Point at the collision warning, then the "Callers elsewhere that may now break" message.
- 0:22 to 0:30. "In 180 runs, 80% finished clean with it, against 53% without. It's open source. Link below."

## How to record and upload
- **Record:** QuickTime Player > File > New Screen Recording (or Cmd+Shift+5). Pick the mic, record the whole thing in one go.
  Do two takes. Small slips are fine. Trim the start and end in QuickTime (Edit > Trim).
- **Check:** watch it once with sound. Is the terminal text readable? Does any home path, token or email show?
- **Upload:** YouTube Studio > Create > Upload videos. Set visibility to **Unlisted**. Title: "MeshAgents demo (WeMakeDevs x FalkorDB, Track 2)".
  Put the repo link in the description. Copy the link and open it in a private window to be sure it plays.
- Paste the link into `docs/SUBMISSION-FORM.md` ("Demo video"), the README, and `site/config.js`.

## Number check
| In the script | Source |
|---|---|
| 80% vs 53%, 180 runs (72/90 vs 48/90) | RESULTS.md round 6; facts.js `collision` |
| 29% cheaper per clean result ($0.0113 vs $0.0159) | RESULTS.md round 6; facts.js `collision` |
| 95% vs 45%, 150 runs; notes file 92% | RESULTS-RELAY.md; facts.js `memory` |
| 83% vs 33% on the second model (20/24 vs 8/24) | RESULTS.md round 7, part 2; facts.js `second` |
