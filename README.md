# MeshAgents

**A shared memory for AI coding helpers.** Claude Code sessions that work on the same project share notes, so they stop stepping on each other.

(Formerly called baton. The Python package, the `baton` command and all `BATON_*` environment variables still work as aliases; `MESHAGENTS_*` names are the documented ones.)

Built on FalkorDB for the WeMakeDevs x FalkorDB "Graph Hacks" hackathon, Track 2 (Agent Memory and Coordination).

## The problem
- Two coding sessions work on one project and cannot see each other.
- One changes a function; the other keeps calling it the old way. Or both fix the same thing.
- When a session ends, the next one starts knowing nothing, even about rules you told the last one.

Example: you tell session 1 "never use sqlite, the server is read-only". Tomorrow, session 2 happily adds sqlite.

## What MeshAgents does
- **Warns before clashes.** If another session is working on the file you are about to edit, you are told first.
- **Remembers what changed and why.** Changes are noted automatically, including edits made through shell commands (`sed -i`, `cat > file`, small scripts), best effort. If a note turns out to be wrong, MeshAgents shows everything built on it.
- **Hands notes to the next session**, including rules people stated once in conversation ("never use sqlite").
- **Shows it on a live board**, a simple web page: who is working on what, and where trouble is.

Nothing to type while you work. It runs as a Claude Code plugin through hooks.

## See it in 2 minutes
No model and no API key needed. You need Docker and Python 3.10+.
```sh
git clone <repo-url> meshagents && cd meshagents
docker compose up -d && python3 -m venv .venv && .venv/bin/pip install -e .
.venv/bin/meshagents doctor && .venv/bin/python demo/run_demo.py
```
The demo plays out two sessions on a small shop project and prints what each one would be told. Then open
http://localhost:3000, pick the graph `baton_demo`, and paste in the queries from [`demo/queries.cypher`](demo/queries.cypher).
To see the live board: `.venv/bin/meshagents ui`, then open http://127.0.0.1:7777.

To use it on your own project:
```sh
claude --plugin-dir /path/to/meshagents/plugin
```
More help: [docs/QUICKSTART.md](docs/QUICKSTART.md).

## Does it work?
Short, honest answer: the machinery works; the proof that it makes your results better is not strong yet.

**Proven**
- **It also works on a second, stronger model.** On Sonnet, after we taught it to see edits made through shell commands, 20 of 24 runs came out clean with the product against 8 of 24 without (83% vs 33%, p = 0.001; three test levels, 8 runs each). Before that fix it did nothing on that model, because that model edits files only through the shell. Details: [docs/RESULTS.md](docs/RESULTS.md), round 7.
- **Fewer clashes when sessions collide.** In a fresh 180-run test, 72 of 90 runs came out clean with MeshAgents against 48 of 90 without (80% vs 53%; the gap is +27 points, 95% range +13 to +40, p < 0.001). Each clean run cost about 29% less ($0.0113 vs $0.0159) because fewer runs had to be redone. Details and limits: [docs/RESULTS.md](docs/RESULTS.md), round 6.
- Warnings really reach real concurrent sessions with nothing typed, with no hook errors in the evaluation runs.
- Taking back a wrong note finds exactly the notes built on it (25 generated test graphs, all found, none wrong, about 3 ms).
- The default setup costs about the same as using no plugin (tokens 1.00x, turns 0.99x, estimated cost 1.04x).

**Not proven**
- That this holds on real projects. The collision tests are built to make sessions collide; a 2026 study of real merged changes found only 1 in 417 with this kind of breakage. One small test project, one cheap model. One test (L6, two sessions both adding the same stock reservation) is not fixed.
- That the "these callers will break" warning helps: it fired once in 40 trials.
- That file-pair hints prevent bugs (they predict which files change together; they do not measure bugs avoided).

**Does a new session start smarter? Yes, when it needs a fact from an earlier session.**
We told a first session something once (the full job, a rule like "never use sqlite", a coding convention), then
started a second session that was not told. 150 test runs, three setups:

| Second session finished the job | No memory | A hand-kept notes file | **MeshAgents** |
|---|---|---|---|
| On the 4 tasks that need the fact (40 runs each) | 18 of 40 (45%) | 37 of 40 (92%) | **38 of 40 (95%)** |
| Cost for each run that succeeded | $0.0117 | $0.0068 | **$0.0058** |

- MeshAgents gives the same result as a notes file that a person keeps perfectly up to date, with nothing to maintain, and costs about 12% less.
- Where nothing needs remembering, MeshAgents costs about 7% more per run and results are the same.
- Honest limit: two of the four tasks are built so a session with no memory cannot know the fact, so the "no memory" number is low by design. We do not know how often real work needs a remembered fact.
- After the rules were made smarter, a re-run on the final code passed 40 of 40 on those tasks, and found one useful rule hidden among 20 irrelevant ones in 10 of 10 runs (a notes file: 9 of 10). That re-run is a post-hoc improvement, reported next to the original.
- Full method, numbers and limits: [docs/RESULTS-RELAY.md](docs/RESULTS-RELAY.md).

Small samples, one cheap model, one test project, tasks and scoring written by the same author. Details: [For the technical reader](#for-the-technical-reader).

Want to see how FalkorDB is used, and why the graph matters? Read [docs/FALKORDB-DEEP-DIVE.md](docs/FALKORDB-DEEP-DIVE.md).

---

# For the technical reader

## Why the graph matters
Without FalkorDB there is nothing to ask. The product answers graph questions:
- *Who holds a live lease on a file I am about to edit?* (Task - TOUCHES -> Artifact)
- *What changed in files near or imported by this one?* (Decision - ABOUT -> Artifact)
- *What was this decision based on, and what breaks if that fact is wrong?* (variable-length `BASED_ON` traversals, used for both `why` and retraction)
- *Which functions call the one I just changed, and who is working in those files?* (Symbol - CALLS -> Symbol, joined to leases)
- *Which files usually change with this one?* (Artifact - CO_CHANGED -> Artifact, learned from git history)
- *Which tasks are ready, with all dependencies done?* (DEPENDS_ON)
- Claims are atomic because FalkorDB serializes writes per graph (race test with a negative control: [docs/SPIKES.md](docs/SPIKES.md)).

In-depth page for each of these, with measurements: [docs/FALKORDB-DEEP-DIVE.md](docs/FALKORDB-DEEP-DIVE.md).

## What it does, by feature
- **Collision warnings** before edits (live leases and recent decisions on the same or nearby files). Policy `warn` by default; `ask`/`deny` opt-in.
- **Decisions captured from edits** (interface, config, storage, rename, dependency changes), derived deterministically from the edit payload, no model call.
- **Handoff on stop**, with the last test result; the next session is briefed on live sessions, recent decisions and the latest handoff.
- **Rules captured from conversation** (`src/baton/core/rules.py`): sentences with clear markers ("never", "from now on", "FYI", "we tried"...) in a user prompt are stored as `Decision {kind: 'rule'}` after secret redaction, at most 4 per prompt, and shown to later sessions for 30 days. Conservative regex, no model call. Effect on outcomes is being measured in [docs/RESULTS-RELAY.md](docs/RESULTS-RELAY.md).
- **Retraction with blast radius** (`meshagents retract`, `meshagents why`).
- **Code symbol graph** (Python only): definitions and call sites, resolved from imports and definitions, never guessed. After an edit that changes a call shape (new required parameter, reorder, removal, rename), the session is told which callers elsewhere will break and which live sessions are in those files. Compatible changes stay silent. `MESHAGENTS_CODE_GRAPH=0` turns it off.
- **Co-change hints from git history** (`core/cochange.py`): `(:Artifact)-[:CO_CHANGED {n, ratio}]->(:Artifact)` built from the newest 800 commits, incremental, time-boxed to 2 s. One line before an edit: "Files that usually change with X: ...". The hook uses ratio >= 0.7, n >= 3. Turn off with `MESHAGENTS_COCHANGE=0`. `meshagents together <path>` lists partners. A PageRank pass over `CALLS` (at most every 6 hours, never per hook) marks heavily depended-on files. Benchmark on six open-source repos: [docs/RESULTS-COCHANGE.md](docs/RESULTS-COCHANGE.md).
- **Dashboard** `meshagents ui` ([docs/UI.md](docs/UI.md)): read-only (`ro_query` only), localhost, standard library only. Board of live sessions, decision feed, provenance graph with retraction preview, code map, impact of recent changes.

## Commands
```sh
meshagents doctor                         # check the install, print the fix for anything missing
meshagents ui [--port 7777]               # read-only dashboard at http://127.0.0.1:7777
meshagents status [--json]                # live sessions, leases, shared files, latest decisions
meshagents why <id>                       # what a decision was based on, and what depends on it
meshagents retract <id> --reason "..."    # asks first, prints what became tainted
meshagents handoff                        # latest handoff briefing
meshagents impact <path>                  # callers of a file's public symbols, and who is in those files
meshagents together <path>                # files that usually change with this one
meshagents gc                             # prune old data
```
All commands pick the workspace the way the hooks do (`--workspace` or `MESHAGENTS_WORKSPACE` override).

## Hooks only by default, MCP optional
Everything is automatic through six hooks (session start, prompt, pre-tool, post-tool, stop, session end). Adding MCP tools made sessions call
them redundantly (about 1.4 extra tool calls per session) and cost 9-37% more tokens ([measurement](docs/RESULTS-TOKENS.md)), so they are off by default.
Optional tools for explicit use (13: create_task, get_ready_tasks, claim_task, renew_lease, complete_task, release_task, post_decision,
check_conflicts, add_finding, why, retract, handoff_export, handoff_import):
```sh
claude mcp add meshagents -- /path/to/meshagents/plugin/bin/baton-mcp
```
Settings (`.baton.json` in the project, or environment): `policy` = `warn` (default) | `ask` | `deny`; `enabled`; `lease_seconds`; `capture`;
`cochange`. `MESHAGENTS_DISABLED=1` turns it off. **Fails open:** if the store is unreachable, hooks print nothing and never block the session.
A hook call takes roughly 0.1-0.15 s (cold process); the graph part is a millisecond or two.

## Data model
One graph per workspace (`baton_<workspace>`), so one workspace cannot address another. Diagram and per-feature mapping: [docs/FALKORDB-DEEP-DIVE.md](docs/FALKORDB-DEEP-DIVE.md).

| Node | Key properties |
|---|---|
| `Actor` | id (session id), kind, started_at |
| `Task` | id, goal, goal_key, status (open/claimed/done/released), owner, lease_until, version |
| `Decision` | id, text, kind (interface/config/storage/rename/rule/note/...), status (open/superseded/retracted/tainted), author |
| `Finding` | id, text, source, confidence, status |
| `Artifact` | path (also `cc_commits`, `hot`, `indexed_hash` for the indexes) |
| `Handoff` | id, note, summary |
| `Symbol` | id (`path::qualified.name`), name, kind (function/method/class/module), sig, path, line |
| `CoChangeIndex` | bookkeeping for the git-history index (last commit, lock) |

| Relationship | Meaning |
|---|---|
| `(Task)-[:DEPENDS_ON]->(Task)` | ordering |
| `(Task)-[:TOUCHES]->(Artifact)` | a session's live footprint |
| `(Actor)-[:DECIDED]->(Decision)` | authorship |
| `(Decision)-[:ABOUT]->(Artifact)` | what a decision concerns |
| `(Decision)-[:BASED_ON]->(Decision \| Finding)` | provenance |
| `(Decision)-[:SUPERSEDES]->(Decision)` | replacement |
| `(Handoff)-[:INCLUDES]->(Task \| Decision \| Finding \| Artifact)` | session handoff packet |
| `(Artifact)-[:DEFINES]->(Symbol)` | what a file defines |
| `(Symbol)-[:CALLS]->(Symbol)` | resolved call sites |
| `(Artifact)-[:CO_CHANGED {n, ratio}]->(Artifact)` | changed in the same commit, from git history |

## Key Cypher
All coordination queries are named and parameterized in [`src/baton/graph/queries.py`](src/baton/graph/queries.py); the code-graph and
co-change queries sit beside the code that uses them (`core/codegraph.py`, `core/cochange.py`). Model output never becomes Cypher.

Atomic claim (at most one caller gets a row; expired leases can be taken over; dependencies must be done):
```cypher
MATCH (t:Task {id: $task_id})
WHERE t.status = 'open' OR (t.status = 'claimed' AND t.lease_until < $now)
OPTIONAL MATCH (t)-[:DEPENDS_ON]->(d:Task) WHERE d.status <> 'done'
WITH t, count(d) AS blockers WHERE blockers = 0
SET t.status = 'claimed', t.owner = $actor_id, t.lease_until = $lease_until, t.version = t.version + 1
RETURN t
```
Other sessions with a live lease on the files I am about to edit:
```cypher
MATCH (t:Task {status: 'claimed'})-[:TOUCHES]->(a:Artifact)
WHERE a.path IN $paths AND t.owner <> $actor_id AND t.lease_until >= $now
RETURN t, a.path
```
Callers elsewhere that a call-shape change breaks (code graph, used right after an edit):
```cypher
MATCH (c:Symbol)-[:CALLS]->(s:Symbol)
WHERE s.path = $path AND s.qual IN $changed AND c.path <> $path
RETURN s.qual, c.path, c.qual ORDER BY c.path
```
Blast radius of a wrong fact (everything derived from it, transitively), used by `retract`:
```cypher
MATCH (root:Finding {id: $id})<-[:BASED_ON*1..]-(d:Decision) RETURN DISTINCT d
```

## Evaluation (honest summary)
Parallel Claude Code sessions (cheap model, `claude-haiku-5-5`) are started at the same moment on one shared checkout with overlapping
tickets. A scripted checker scores whether the combined result is collision-free. Harness, tasks and checkers: [`evals/`](evals).
Write-ups with all caveats: [docs/RESULTS.md](docs/RESULTS.md), [docs/RESULTS-HELDOUT.md](docs/RESULTS-HELDOUT.md),
[docs/RESULTS-TOKENS.md](docs/RESULTS-TOKENS.md), [docs/RESULTS-PROVENANCE.md](docs/RESULTS-PROVENANCE.md),
[docs/RESULTS-COCHANGE.md](docs/RESULTS-COCHANGE.md), [docs/RESULTS-RELAY.md](docs/RESULTS-RELAY.md).

| Question | Result | Verdict |
|---|---|---|
| Collision avoidance, held-out L8-L10, clean runs (of 21) | baseline 15, plugin 20 (p = 0.093; failed checks per trial 0.48 vs 0.10, p = 0.108) | direction favourable, **not significant** (bar was p < 0.05) |
| Collision avoidance, 9 levels x 10 runs per side (fresh, same time, same code) | clean runs 72/90 (80%) vs 48/90 (53%); +27 points (95% CI +13 to +40), p < 0.001; cost per clean run $0.0113 vs $0.0159; L6 unsolved (1/10) | constructed collisions; tuned and untuned levels mixed; one cheap model |
| Cost, hooks-only vs no plugin, 56 trials per arm | cache-read 1.00x, turns 0.99x, cost 1.04x; clean runs 41/56 vs 32/56 (p = 0.11); about 19% lower estimated cost per clean result | parity; post-hoc comparison |
| Cost, first version with MCP tools | +37% cache-read tokens, +23% turns | why hooks-only is the default |
| Code graph "callers will break" warning | fired once in 40 trials | mechanism verified, **no outcome benefit shown** |
| Retraction, 25 generated graphs (~203 items each) | precision 1.000, recall 1.000, ~3 ms; grep over a flat file: recall 0.65 with mixed citations, 0 with paraphrased | exact if `based_on` links were recorded (recall 0.73 if 20% missing) |
| Co-change hints, 6 open-source repos, held-out 30% | hook setting (ratio 0.7, n 3): coverage 17.2%, precision@3 73.1%, noise 24.2%; the looser `meshagents together` default (0.5): 33.7%, 57.0%, 33.5%; same-directory guess: 29.8% precision | predicts co-changing files, not bugs avoided; about a third of hints miss; quality varies by repo |
| Does a new session start smarter? (150 runs, 3 setups) | on the 4 tasks that need a stated fact: MeshAgents 38/40, notes file 37/40, no memory 18/40; cost per success $0.0058 vs $0.0068 vs $0.0117; +7% cost when nothing needs remembering | pre-registered; strong success by our own criteria; two tasks are built to need memory |

Known defect: a live-session warning can make a session defer too much (in two L2 trials a session wrote code calling a function that
never existed). Duplicate-ticket tasks (L5) are not solved (0/5). The optional end-of-session re-check (`MESHAGENTS_STOP_CHECK=1`, off) did
not help L4 or L6 and costs extra turns.

Limits: small samples, one model, one fixture project, tasks and scorer written by the same author.

## Tests
`.venv/bin/python -B -m unittest discover -s tests -t .` runs 214 tests against a live FalkorDB (v4.22.1 pinned in `docker-compose.yml`; the claim test also passed on 6.0.2).

## Layout
```
src/baton/        core library, graph queries, capture, hook entry points, CLI
src/baton/ui/     read-only dashboard (stdlib only)
src/baton/mcp_server/  optional MCP server
plugin/           Claude Code plugin (manifest, hooks; optional-mcp.json for the MCP server)
demo/             scripted scenario and Browser queries
evals/            collision tasks and checker (clash), containerised runner (harbor), provenance, cochange, relay benchmarks
docs/             plan, architecture, spikes, results, FalkorDB deep dive
tests/            unit and integration tests
```

## AI assistance disclosure
This project was designed and built with substantial help from an AI coding assistant (Claude
Code), including code, tests, evaluation harness and documentation. The author directed the work and
reviewed the results; the evaluation numbers above come from runs recorded in this repository.
All data is synthetic (the `shop` fixture) or generated by the runs themselves, apart from the co-change
benchmark, which reads the public git history of six open-source repositories.

## Known limits
- Text from one session is shown to other sessions: secrets are redacted by pattern (best effort,
  not a guarantee) and text is flattened and clipped, but treat the shared graph as visible to every
  session in the workspace.
- Sessions in different project directories or git worktrees use separate graphs by default; set
  `MESHAGENTS_WORKSPACE` to share one. MCP tools expect project-relative paths.
- The code graph is Python only. Rule capture is keyword-based and misses unusual phrasing.
- FalkorDB password and TLS can be set with `MESHAGENTS_FALKORDB_PASSWORD` / `MESHAGENTS_FALKORDB_SSL`; not covered by tests, and docs/QUICKSTART.md still says they are not configurable.

## License
MIT, see [LICENSE](LICENSE).
