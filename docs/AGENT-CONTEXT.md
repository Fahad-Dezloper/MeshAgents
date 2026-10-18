# Briefing for anyone (person or AI helper) joining the MeshAgents project

Read this first. It is short on purpose. Last updated 2026-10-18 afternoon.

## What MeshAgents is
When several Claude Code sessions work on one project, they cannot see each other: they edit the same file,
build on a function another session just changed, and a new session starts knowing nothing. MeshAgents is a shared
notebook, kept as a graph in FalkorDB, that sessions read and write automatically (Claude Code hooks, no
commands typed). It warns before clashes, remembers what each session changed and why, and hands notes to the
next session. Repo: /Users/dezloper/Desktop/baton (GitHub Fahad-Dezloper/Baton, branch main).

## The competition we are in
WeMakeDevs x FalkorDB "Graph Hacks", Track 2 (Agent Memory and Coordination). Deadline: Sun 2026-10-18, 11:59 PM
IST. FalkorDB must be central ("if it works without FalkorDB the graph is decoration"). About 180 repos use
FalkorDB, ~50 are in Track 2, ~5 are very close to us: sushanshetty1/airspace, Lecrupus/hivemind,
Quantapixel/hivemind, tharunkumardeveloper/The-Final-Boss (Relay), tinniaru3005/custody. Several have a live
site, a demo video and benchmark claims. The user records the demo video and deploys at the end; do not spend
time on those.

## What exists (all pushed, 160 tests passing)
- Hooks-only Claude Code plugin (plugin/), MCP server optional. src/baton/{core,graph,capture,hooks,ui}.
- Graph: Actor, Task, Decision, Finding, Artifact, Handoff, Symbol; edges DEPENDS_ON, TOUCHES, DECIDED, ABOUT,
  BASED_ON, SUPERSEDES, INCLUDES, DEFINES, CALLS.
- Features: collision warnings before edits, decisions captured from edit payloads, handoff on stop with last
  test result, retraction with blast radius, code symbol graph with "these callers will break" warning,
  dashboard `meshagents ui`, CLI (status, why, retract, handoff, impact, doctor, gc), end-of-session check (off).
- Evaluation harness: evals/clash (10 levels L1-L10, checker check.py), evals/harbor (Harbor + Docker runner),
  evals/provenance (retraction/handoff benchmarks). Results: docs/RESULTS*.md.

## Honest results so far (do not overclaim)
- Collision avoidance: more runs finish clean with MeshAgents (about 8 in 10 vs 6 in 10) but never statistically
  clear; a held-out set gave 20/21 vs 15/21 (p=0.09, below our p<0.05 bar).
- Cost: first version used +31% more tokens (models called optional MCP tools redundantly). Hooks-only default
  is at parity with no plugin (cost 1.04x) and ~19% cheaper per clean result.
- Code graph warning fired once in 40 trials: mechanism verified, outcome benefit NOT shown.
- Level 5 cannot be passed by design. Retraction benchmark: graph exact; grep matches only when notes cite clearly.
- The user's verdict: the numbers are not compelling enough. The goal now is real, honest stats showing the
  product is worth keeping: saves tokens, money, time, and prevents breakage.

## Added after the first version of this briefing (2026-10-18 afternoon)
- Notes that carry over: handoff keeps the full original request (Task.spec); rules stated by the user in
  conversation are captured as Decision kind 'rule' (core/rules.py) and shown to the next session.
- "Files that change together": CO_CHANGED edges from git history (core/cochange.py); offline benchmark on 6
  real repos: hint right about 2 times in 3 when shown, shown for about a third of edits (docs/RESULTS-COCHANGE.md).
- Relay benchmark (evals/relay, docs/RESULTS-RELAY.md): sessions one after another, 3 arms (no memory, a plain
  HANDOFF.md notes file, MeshAgents), tasks R1-R5. Full run (150 trials) started 14:08 IST as prefix relay1.
- evals/harbor/stats.py gives pass rates with confidence intervals, exact tests and cost per success.
- Research notes: docs/research/01-05. Main rival: airspace (real-repo benchmark, 9/9 vs 0/9, live site, video).
- Plan: relay run (~3h), then re-run the clash suite with larger n, then write up real numbers. Product code is
  frozen while evaluations run (image baton-eval:latest is rebuilt only after changes).

## Rules for working here
- Simple words when talking to the user (they asked for this; see memory). Short, concrete.
- Never fabricate numbers; every claim needs a recorded run. Report negative results too.
- Commit messages must not contain the words claude, ai or agent; no co-author trailers. Do not push unless told.
- Shell facts: `rm` is blocked; no `timeout` on macOS; curl is blocked; tool output can garble digits (compute in
  scripts). Run tests: `.venv/bin/python -B -m unittest discover -s tests -t .` (check exit code). Use
  PYTHONPATH=$PWD/src when working in a git worktree. FalkorDB runs on localhost:6379 (use your own workspace
  names; never drop graphs you did not create; `baton_demo` belongs to the demo).
- Evaluation: Claude subscription (no API key), model claude-haiku-5-5, runner `evals/harbor/run_eval.sh`,
  image `baton-eval:latest` must be rebuilt after any src/ or plugin/ change (see evals/harbor/README.md).
  `.env.eval` holds the token (git-ignored; never print it).
