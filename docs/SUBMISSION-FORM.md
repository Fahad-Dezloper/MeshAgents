# Submission form answers (ready to paste)

Fill the three placeholders (video, blog, live demo) before you submit. Numbers match `docs/RESULTS.md`, `docs/RESULTS-RELAY.md` and `site/facts.js`.

## Project title
MeshAgents

## Description (about 130 words)
When you run several AI coding sessions on one project, they cannot see each other. One changes a function while another keeps calling it the old way. Tomorrow a new session knows nothing, even about a rule you gave the last one: "never use sqlite". MeshAgents is a shared notebook for Claude Code sessions, kept as a graph in FalkorDB. It runs through hooks, so nobody types anything. It warns before two sessions clash, says which callers elsewhere may break, hands notes to the next session, and shows everything built on a note that turns out wrong. It is for developers who run more than one coding session at once. Honest limits: our collision tests are built to collide, and a hand-kept notes file does about as well on memory (92% vs 95%).

## Track
Track 2: Agent Memory and Coordination

## Repository
https://github.com/Fahad-Dezloper/MeshAgents (public)

## Demo video
`<YOUTUBE_LINK>` (unlisted YouTube; see docs/VIDEO-SCRIPT.md)

## Live demo (optional)
The landing page in `site/` is a static page with no build step. Deploy it in 3 lines:
1. GitHub Pages: Settings > Pages > deploy from branch, folder `/site`.
2. Or Vercel: `cd site && npx vercel --prod` (framework: Other, no build command).
3. Or Netlify: `npx netlify deploy --dir=site --prod`. Then paste the URL here. The product itself runs locally (Docker + pip, see the README).

Live demo URL: `<SITE_URL>` (leave empty if not deployed; the video is the demo).

## How did you use FalkorDB (about 220 words)
The product is a graph, not a database with a graph on the side. There is one graph per workspace (`baton_<workspace>`) with Actor, Task, Decision, Finding, Artifact, Handoff and Symbol nodes. Claiming a task is one Cypher query; it is atomic because FalkorDB serialises writes per graph. We checked this with a 32-worker race test and a negative control that double-claimed (docs/SPIKES.md). A leases query finds live sessions on the files you are about to edit. Provenance and retraction use variable-length `BASED_ON*1..` traversals: on 25 generated graphs the result was exact (25/25) in about 3 ms, where grep over a flat file had recall 0.65 with mixed citations. A code graph (`DEFINES`, `CALLS`) is written with batched `UNWIND`, and one traversal names the callers elsewhere that a changed function breaks. `CO_CHANGED` edges learned from git history were tested on 6 real repositories; the query takes 0.3 ms. Rules people state are Decision nodes ranked by relevance in Cypher. All queries are parameterised, the dashboard uses only `ro_query`, and hooks add about 0.1 s and fail open if the database is down. Details: README and docs/FALKORDB-DEEP-DIVE.md.

## Blog link
`<BLOG_LINK>` (draft: docs/BLOG.md and docs/BLOG-LINKEDIN.md)

## What did you like about FalkorDB
- One Cypher statement that matches, checks and sets is atomic, and writes to a graph are serialised. That gave us race-free claims with no locks, and we could prove it with a test.
- It is fast and small: lookups and traversals took about a millisecond on our graphs, and the whole thing starts with one `docker compose up`.
- Variable-length traversals made "what is built on this wrong fact" a single short query, and `ro_query` let the dashboard read without ever being able to write.
- Graph algorithms (PageRank, BFS, weakly connected components, betweenness) are built in and can feed straight into a `MATCH`.

## What improvements would you like to see
Real things we hit while building this:
- `shortestPath` only works in `WITH` or `RETURN`, with both ends already matched. `MATCH p = shortestPath(...)` fails. A clearer error, or support in `MATCH`, would help.
- `algo.louvain` and `algo.leiden` are not registered on v4.22.1, and it is hard to tell which algorithms exist in which server version. A per-version algorithm table in the docs would help.
- Label propagation gave different communities between runs. A seed option, or a note in the docs, would help.
- The Python client keeps cached schema ids. They go stale when a graph is deleted and recreated while a process is running (we hit this re-seeding a demo graph).
- No multi-query transactions. A single query is atomic, so we kept anything that must be atomic in one query and made other writes safe to repeat.

## Pre-submit checklist
- [ ] Repo is public. Open it in a private window and check no secrets, tokens or personal paths are in the files or history (`.env.eval` must not be committed).
- [ ] Demo video link plays in a private window (YouTube unlisted).
- [ ] README renders on GitHub (tables, the data model, the Cypher blocks).
- [ ] The AI-assistance disclosure is in the README (section "AI assistance disclosure") and, if the form has room, repeated in the form.
- [ ] All links are filled: video, blog, live demo (if any). No `<...>` placeholders left in this file, the README or `site/config.js`.
- [ ] Re-read the rules page once more (they say rules may change).
- [ ] Submit before 6 PM IST on Oct 18. The official deadline is 11:59 PM IST, so this leaves a safe margin.
