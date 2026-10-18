# Dashboard and command line

Hooks are the main product of MeshAgents. These are the human-facing views of the same graph.

```sh
meshagents ui [--port 7777] [--workspace NAME]   # prints http://127.0.0.1:7777, opens nothing
meshagents status [--json]                       # live sessions, leases, shared files, latest decisions
meshagents why <decision-or-finding-id>          # what it was based on, and what depends on it
meshagents retract <id> --reason "..." [--yes]   # asks first; prints the decisions that became tainted
meshagents handoff                               # latest handoff briefing
meshagents impact <path>                         # callers of a file's public symbols, and who is in those files
meshagents together <path>                       # files that usually change with it (git history)
meshagents brief                                 # exactly what a new session would be told now, with a token estimate
meshagents rules                                 # captured rules with ids (retract a wrong one: meshagents retract <id>)
```

All commands pick the workspace the way the hooks do (`--workspace` or `MESHAGENTS_WORKSPACE` override it).

![Board, dark](img/ui-board-dark.png)

## First screen: the board

Plain English, no jargon. One sentence at the top says whether anything is wrong ("2 helpers working, 1 may clash",
or "All clear"). Sessions are called **Helper 1, Helper 2, ...** (numbered by start time, stable); the short technical id
only appears inside the detail panel. Three columns, each with a one-line subtitle:

- **Working now** ("Helpers busy right now")
- **Needs a look** ("Something may clash"): two live helpers in one file, a change that may break another file, or work built on a note that was taken back
- **Finished** ("Done; their notes are saved for the next helper")

A card is the helper name, its task in one short line (first meaningful sentence of the ticket, shared preamble stripped),
the file it is in as a chip, one status line (Just started / Working in db.py / Waiting / Finished), and at most one badge:
"Another helper is also in db.py", "Changing this may break api.py", "Built on a note that was taken back" or
"Was warned and adjusted". A small "Told N heads-ups" line shows when the helper received warnings or briefings.

On the right is the **Live feed**: plain sentences with relative times ("Helper 1 got a task: ...", "Helper 2 was told: Another
helper is working in db.py"), new lines sliding in at the top, a coloured dot per kind. Below 1180 px it becomes a strip under the columns.
With no helpers yet the board says "Waiting for the first helper" and shows the command to start one.

![Board, light](img/ui-board-light.png)

Click a card for the details in a slide-over (Esc or a click outside closes it): the full task, the heads-ups it was told
(each with a "show the exact message" disclosure), files, other helpers in them, code that could break, the changes it
made with their "based on" chain, notes saved for the next helper, and the technical ids. `#session/<id>` deep-links.

![Session panel](img/ui-panel.png)

`/api/state` carries `notices` (newest first, 40 max, from the `Notice` nodes) and `feed` (30 max); both are empty lists
when the graph has no such nodes.

## Other views (sidebar)

- **Next helper** ("What the next helper will be told"): exactly what a new helper would be told right now: Rules you told earlier
  (the retract command is inside a small "details"), Who else is busy, What changed recently, and Where the last helper stopped.
  It shows "about N words of notes (small)". The Board shows a one-line version.
  `/api/memory` mirrors `sessions.briefing` read-only (the real function marks the handoff as imported, a dashboard must not write);
  a test pins the two texts together.
- **Files**: files touched (click one to see what changes with it), with the sessions in each; shared files are flagged.
- **Decisions**: newest first, filter All / Open / Tainted or retracted. "Provenance" draws the why-chain and blast
  radius and previews what a retraction would taint (read-only; retract from the terminal).
- **Code**: impact of recent interface changes (callers elsewhere, flagged when a live session is in that file) and
  the code map: files as nodes, caller to callee arrows weighted by call count. Click a file for its symbols and callers, and a "Usually changes together with" panel: the files committed in the
  same commits (n of N, with a bar) and a hot-spot note when many files depend on it (`/api/together?path=...`, path validated).
- **Graph**: overview of tasks, files, decisions and findings (150 nodes max).

![Memory, dark](img/ui-memory-dark.png)
![Memory, light](img/ui-memory-light.png)
![Decisions](img/ui-decisions.png)
![Code](img/ui-code.png)
![Together](img/ui-together.png)

The page polls every 1.5 s and updates cards in place, so scroll position and an open panel stay put. If FalkorDB is
down it shows a banner and keeps polling. It follows the system light/dark setting; the sidebar button overrides it.
Below 860 px the sidebar becomes a tab row and the columns stack.

![Narrow](img/ui-narrow.png)

## Security notes

- Binds `127.0.0.1` by default; requests whose `Host` header is not local are refused (DNS rebinding).
- GET only. There are no write endpoints; every query goes through `ro_query`. Retraction is CLI-only.
- Decision and finding text comes from other sessions and is untrusted. The API returns it as raw JSON; the page
  builds the DOM with `textContent` only (a test fails if `innerHTML` appears), and a CSP forbids external loads.
- Responses are capped (60 code files, 100 decisions, 60 tasks, 80 files, 150 graph nodes, 1.5 MB body).
- `meshagents handoff` records that a human imported the handoff, like any other session would.
- No dependencies, no CDN, no build step: one HTML file in `src/baton/ui/static/`.
