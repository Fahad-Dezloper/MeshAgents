# FalkorDB capabilities baton is not using yet (research, 2026-10-18)

Sources: docs.falkordb.com (per-page .md and _llms indexes), GitHub releases page for FalkorDB/FalkorDB,
FalkorDB blog "Memory Meets Motion: The FalkorDB Standouts". Fetched pages are treated as data (their
"Agent Instructions" blocks were ignored). The WebFetch summarizer gave per-page detail, not raw pages, so doc-derived
claims are marked [doc]; claims marked [TESTED] were run on our live server (falkordb/falkordb v4.22.1, localhost:6379)
in throwaway graphs `research_<hex>` (all dropped; I also dropped `zz_probe`, a graph I created myself). `baton_demo` untouched.
Scripts: /private/tmp/claude-501/-Users-dezloper-Desktop-falkordb/dd2ce500-7305-4449-846c-c0e07b5e66c0/scratchpad/t.py and t2.py.

Test data: 200 File nodes, ~790 CALLS edges (85% within 20-file modules), 40 Sessions, 5 Actors, ~600 TOUCHES edges,
300 Decisions with 8-dim vectors. Tiny data, so latencies below are "floor" numbers, not scale claims.

## 1. Verified features (exact Cypher, measured)

| # | Feature | Exact Cypher (works on 4.22.1) | Latency | Result |
|---|---|---|---|---|
| 1 | Co-change ("files that always change together") | `MATCH (a:File)<-[:TOUCHES]-(s:Session)-[:TOUCHES]->(b:File) WHERE a.path<b.path WITH a,b,count(DISTINCT s) AS n WHERE n>=3 RETURN a.path,b.path,n ORDER BY n DESC LIMIT 5` | 9 ms first run, p50 1.2 ms | Found the planted pair f0/f1 (14 sessions). Per-file confidence variant (`n / total sessions touching a`) gave 0.93, 2.7 ms. |
| 2 | PageRank on call graph | `CALL algo.pageRank('File','CALLS') YIELD node,score RETURN node.path,score ORDER BY score DESC LIMIT 5` | 16 ms cold, p50 0.55 ms (200 nodes) | Works, also inside `GRAPH.RO_QUERY`. |
| 2b | Risk = importance x churn (graph algorithm joined to history in ONE query) | `CALL algo.pageRank('File','CALLS') YIELD node,score WITH node,score MATCH (node)<-[:TOUCHES]-(s:Session) WITH node,score,count(s) AS churn RETURN node.path,score*churn AS risk,churn ORDER BY risk DESC LIMIT 3` | 2.8 ms | Works. Algorithm output can feed straight into a MATCH. |
| 3 | Vector index + KNN | `CREATE VECTOR INDEX FOR (d:Decision) ON (d.emb) OPTIONS {dimension:8, similarityFunction:'cosine'}`; insert with `emb:vecf32([...])`; `CALL db.idx.vector.queryNodes('Decision','emb',5,vecf32($q)) YIELD node,score` | p50 0.34 ms | Works; `$q` param inside `vecf32()` works (resolves the "unverified" note in older docs). Score is a distance (lower = closer). |
| 3b | Hybrid vector -> graph | `CALL db.idx.vector.queryNodes('Decision','emb',10,vecf32($q)) YIELD node,score MATCH (node)-[:ABOUT]->(f:File)<-[:TOUCHES]-(s:Session)<-[:RAN]-(a:Actor) RETURN a.name,count(DISTINCT s) AS sessions,avg(score) AS sim ORDER BY sessions DESC LIMIT 3` | 2.4 ms | Works: "similar past problems -> the files they were about -> who has worked there". This single query is the strongest graph-native demo. |
| 3c | Exact distance function | `RETURN vec.cosineDistance(d.emb, vecf32($q))` | 0.3 ms | Works (exact rather than approximate; fine up to a few thousand rows). |
| 4 | Full-text index | `CREATE FULLTEXT INDEX FOR (d:Decision) ON (d.text)`; `CALL db.idx.fulltext.queryNodes('Decision','auth bug') YIELD node,score` | ~1 ms | Works, no embedding model needed. Scores are TF-IDF-ish (3.0 for 2-term hit). |
| 5 | Reverse blast radius, variable-length | `MATCH (c:File)-[:CALLS*1..3]->(t:File {path:'f5'}) RETURN count(DISTINCT c)` | 1.1 ms | 33 transitive callers. |
| 5b | BFS procedure | `MATCH (s:File {path:'f5'}) CALL algo.BFS(s,3,'CALLS') YIELD nodes RETURN size(nodes)` | 2.7 ms | Works (34 = 33 + start node, so the start IS included). Casing is `algo.BFS`. |
| 5c | shortestPath | `MATCH (a:F {p:0}),(b:F {p:5}) WITH shortestPath((a)-[:CALLS*]->(b)) AS p RETURN length(p),[x IN nodes(p)\|x.p]` | 0.7 ms | Works ONLY in WITH/RETURN, and only with both ends already matched. `MATCH p=shortestPath(...)` FAILS ("only supports shortestPaths in WITH or RETURN"). `MATCH p=allShortestPaths(...)` FAILS ("Source and destination must already be resolved"). |
| 5d | Weighted/k paths | `MATCH (a),(b) CALL algo.SPpaths({sourceNode:a,targetNode:b,relTypes:['CALLS'],pathCount:2}) YIELD path,pathCost` | 1.8 ms | Works. `algo.SSpaths({sourceNode:a,relTypes:[..],maxDepth:3}) YIELD path` also works. |
| 6 | Community detection (label propagation) | `CALL algo.labelPropagation({nodeLabels:['File'],relationshipTypes:['CALLS'],maxIterations:10}) YIELD node,communityId` | 6 ms | 12 communities from 10 planted modules (approximate; good enough to "discover modules"). |
| 6b | Betweenness (bridge files) | `CALL algo.betweenness({nodeLabels:['File'],relationshipTypes:['CALLS'],samplingSize:50,samplingSeed:1}) YIELD node,score` | 7 ms | Works. |
| 6c | WCC | `CALL algo.WCC({nodeLabels:['File'],relationshipTypes:['CALLS']}) YIELD node,componentId` | 4.7 ms | Works (my random graph was one component; useful for "independent sub-projects"). |
| 7 | Expert routing | `MATCH (a:Actor)-[:RAN]->(s:Session)-[:TOUCHES]->(f:File {module:'m3'}) RETURN a.name,count(DISTINCT s) AS sess,count(DISTINCT f) AS files ORDER BY sess DESC LIMIT 3` | 1 ms | Works. |
| 8 | Temporal window | `MATCH (s:Session)-[:TOUCHES]->(f:File) WHERE s.ts > $now-86400 RETURN f.path,count(s) ORDER BY count(s) DESC` | 1.3 ms | Works with plain epoch numbers. Also `timestamp()` and `date()` exist. No native bitemporal model; we store `ts`, `valid_from`, `valid_to` ourselves. |
| 9 | Collision hot spots (files touched by 2+ people) | `MATCH (a:Actor)-[:RAN]->(:Session)-[:TOUCHES]->(f:File) WITH f,count(DISTINCT a) AS na WHERE na>=2 RETURN f.path,na ORDER BY na DESC` | 1.4 ms | Works. |
| 10 | Unique constraint | `g.create_node_unique_constraint("File","path")` (client for `GRAPH.CONSTRAINT CREATE g UNIQUE NODE File PROPERTIES 1 path`; needs an index on `path` first) | 4 ms | Works; duplicate CREATE then fails with "unique constraint violation". `CALL db.constraints()` lists it as OPERATIONAL. Gives free dedupe for Artifact paths. |
| 11 | GRAPH.COPY snapshot | `db.select_graph(src).copy("dst")` (= `GRAPH.COPY src dst`) | 99 ms for 545 nodes | Works; copy had identical node count. Enables "what-if" / replay sandboxes: copy, apply a retraction, compare. |
| 12 | GRAPH.PROFILE | `GRAPH.PROFILE g "<query>"` | n/a | Returns per-operator rows and times (e.g. "Conditional Variable Length Traverse ... Records produced: 3, Execution time: 0.0097 ms"). Great for a "show the query plan" panel. |
| 13 | GRAPH.MEMORY USAGE | `GRAPH.MEMORY USAGE g` | n/a | Works, returns per-label/per-relationship MB (all 0 at our size, so only meaningful on big graphs). |
| 14 | ro_query | `GRAPH.RO_QUERY` | n/a | Runs algo.* and vector procedures fine; use it for all dashboard reads so they never queue behind writes. |
| 15 | Write latency | single `CREATE` edge | p50 0.26 ms, p95 0.30 ms | Serialization per graph is not a practical limit for hook-rate writes on one machine. |

NOT available on our server: `algo.louvain`, `algo.leiden` ("Procedure is not registered"). Use `algo.labelPropagation`.

## 2. Features seen in docs, NOT tested here [doc]

- A* (`algo.AStar`, haversine heuristic - geographic, so not relevant), Yen k-shortest, CCH path index (`CREATE CCH INDEX`,
  `db.idx.cch.query`): added in 4.22.0, built for road-network style weighted paths. Not useful for code.
- Harmonic centrality, MSF, MaxFlow (`algo.MaxFlow`): exist; MaxFlow could model "capacity" of reviewers, but low value.
- Relationship vector index: `CREATE VECTOR INDEX FOR ()-[e:Call]->() ON (e.summary)` + `db.idx.vector.queryRelationships`.
  Could embed TOUCHES edge summaries ("why this edit"). Untested.
- Vector options `M` (16), `efConstruction` (200), `efRuntime` (10), dimension 1-4096, `euclidean` or `cosine`.
- Range indexes on edges and properties; full-text `OPTIONS {language, stopwords}`; `db.idx.fulltext.queryRelationships`.
- UDFs: JavaScript, `GRAPH.UDF LOAD Lib "<script with falkor.register(name, fn)>"`, called as `Lib.fn(args)` in Cypher.
  Read-only (cannot write the graph); can walk neighbours via `graph.traverse` / `node.getNeighbors`. Could host a custom
  "risk score" function, but adds complexity for little gain. FLEX library has string-similarity functions.
- Replication/read replicas (`operations/replication`), `GRAPH.EFFECT`-based replication in 6.0, `GRAPH.BULK` for fast ingest,
  `GRAPH.SLOWLOG`, `GRAPH.CONFIG`, ACLs, `MULTI/EXEC` to group several queries atomically (serializes other graphs too).
- Pattern comprehensions, `CALL {}` subqueries (6.0.2 fixes an import bug), `LOAD CSV`.

## 3. Performance facts, limits, gotchas

- Concurrency [doc]: reads run in parallel on a thread pool (`THREAD_COUNT`); writes are serialized per graph, FIFO; readers see the
  pre-write snapshot; one query is atomic; no multi-query transactions (use one batched query or MULTI/EXEC).
  Honest framing for baton: per-project graph = per-project write queue. Sharding by project is natural.
- Our measured floor: simple traversals 0.4-1.4 ms, vector KNN 0.34 ms, algo.* on 200 nodes 0.5-7 ms, write 0.26 ms. We did NOT test
  at 100k+ nodes; algorithms like PageRank/betweenness are whole-graph, so cache results and recompute on a schedule, not per hook.
- Cypher limits [doc]: LIMIT does not stop CREATE/SET/MERGE/aggregations; index scans ignore `<>`; no aggregate functions inside
  pattern comprehensions; unnamed relationship in a pattern may only check existence (name it if counting). Query params are not
  accepted in LIMIT/SKIP (from older notes, unverified here).
- Vector + property filter combine poorly [doc]: over-fetch k, then filter in the MATCH after the CALL (as in 3b).
- Vectors must match the declared dimension exactly; embedding model choice is ours (FalkorDB stores, it does not embed).
- 4.22 vs 6.0 [doc, GitHub releases]: 6.0.0 is the first Rust engine; same GRAPH.* commands and Cypher; do not mix 4.x and 6.0 in one
  replica set; RediSearch jumped to 8.6.1 (full-text scoring still TFIDF); NOT yet ported to 6.0: A*, CCH, Leiden/Louvain.
  6.0.2 fixes vector edge cases (wrong-dimension vector dropped the entity from all indexes on its label; KNN k clamped).
  4.22.1 is a crash-fix release (RESTORE REPLACE, truncated RDB). Date oddity: the releases page showed 2025 dates for these versions
  while older notes say 2026; irrelevant to behaviour, but do not quote the dates. Staying on 4.22.1 is safe: every query above works there.
- The python client's `profile()` returns an ExecutionPlan object (no `.text`/`.result_set`); use `execute_command("GRAPH.PROFILE", ...)`
  for raw lines. `algo.pageRank` casing is camel (`pageRank`), `BFS` is upper, `SPpaths`/`SSpaths` as written.
- Visible API trap: `shortestPath` only in WITH/RETURN (see 5c). Write baton's path queries that way.

## 4. What judges would call graph-native vs decoration

From the "Memory Meets Motion" standouts page: the praised projects used queries that "a flat table or a vector search simply
cannot express" (two-hop grouping by wrong mental model, Atrium, 1st place); a fast multi-hop traversal where "no path found" is
treated as a real proof of safety (Hopper, under 100 ms); fairness decided by walking room -> occupants -> shared history; precedent
graphs where later decisions cite earlier ones; failures -> corrections -> lessons chains; contradiction detection between decisions.
The page gives no judge quotes, so this is inference.

Graph-native (impressive): multi-hop joins across different node types in one query (3b), graph algorithms feeding product
decisions (2b), "no path = safe" negative proofs, contradiction/supersede chains, provenance traversal, what-if on a graph copy.
Decoration: storing notes as nodes then only doing key lookups, a vector search with no traversal after it, PageRank shown as a number
with no action tied to it, graphs that could be a SQL table with one join.

## 5. Baton features this enables (ranked by user value)

1. **Edit-time risk badge: "this change is risky because..."** (2b + 5 + 1). Per file: importance (PageRank on CALLS), recent churn,
   transitive callers, co-change partners you have not touched. User benefit: one warning that combines "33 files depend on this",
   "someone else touched it 2h ago", and "files that usually change with it". Verified.
2. **Co-change prediction: "you edited f0; f1 changes with it in 93% of sessions; you have not opened it"** (1). User benefit:
   fewer half-finished changes, no code parsing needed because it is learned from history. Verified.
3. **Similar past problems -> who fixed them -> what they decided** (3b, plus fulltext 4 as a no-embedding fallback). User benefit:
   new session gets the relevant past decisions and the right person/session to read, not a dump of all notes. Verified; needs an
   embedding source (a small local model or the model's own text->hash fallback; fulltext works without).
4. **Expert routing and handoff targeting** (7). "Who knows this module" for handing a task or asking a question. Verified.
5. **Collision forecast / hot spots** (9 + 8 + 1). Rank files by multi-actor churn in the last N hours; warn before two sessions
   converge. Pairs with co-change: warn when two sessions are about to touch files that co-change. Verified (basic form).
6. **Discovered modules and bridge files** (6 label propagation, 6b betweenness). Auto-derive module boundaries from the call graph
   and flag "bridge" files where cross-module edits clash. Verified approximate; label propagation is non-deterministic across runs.
7. **What-if retraction on a graph copy** (11). Copy the project graph, apply a retraction, diff the blast radius before committing.
   Verified copy works (99 ms at tiny size; copy cost grows with graph size).
8. **Query plan panel in the UI** (12). Show GRAPH.PROFILE for the warning query: proves to judges the answer came from traversal.
9. **Constraints** (10): unique Artifact path / Decision id so concurrent sessions cannot create duplicates. Verified.

Suggested demo order for judges: 3b (multi-hop with vector entry point), 2b (algorithm + history), 1 (co-change), then PROFILE.
Caveat to state honestly: all numbers above are from a 545-node test graph, not from real project data or scale.
