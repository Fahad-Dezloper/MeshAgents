"""Code symbol graph: who defines what, who calls what, and who is working near it.

Graph additions (all in the same per-workspace FalkorDB graph):
    (:Artifact)-[:DEFINES]->(:Symbol {id, name, qual, kind, path, sig, line})
    (:Symbol)-[:CALLS]->(:Symbol)

The graph answers one question the file-level view cannot: "I changed this function's call shape; which
callers elsewhere break, and which live sessions are working in those files right now?"
"""

from __future__ import annotations

import os
import time
from typing import Dict, Iterable, List, Optional

from baton.capture import symbols as sym
from baton.core.tasks import _now
from baton.graph import queries
from baton.graph.client import Store

DELETE_SYMBOLS = (
    "MATCH (a:Artifact)-[:DEFINES]->(s:Symbol) WHERE a.path IN $paths DETACH DELETE s"
)
CREATE_SYMBOLS = (
    "UNWIND $syms AS x MERGE (a:Artifact {path: x.path}) "
    "CREATE (s:Symbol {id: x.id, name: x.name, qual: x.qual, kind: x.kind, path: x.path, sig: x.sig,"
    " line: x.line, refs: x.refs}) CREATE (a)-[:DEFINES]->(s)"
)
SET_HASHES = "UNWIND $files AS f MERGE (a:Artifact {path: f.path}) SET a.indexed_hash = f.hash"
OUTGOING_EDGES = (
    "UNWIND $edges AS e MATCH (c:Symbol {id: e.src}) MATCH (s:Symbol {id: e.dst}) MERGE (c)-[:CALLS]->(s)"
)
INCOMING_EDGES = (
    "UNWIND $ids AS sid MATCH (s:Symbol {id: sid}) MATCH (c:Symbol) WHERE sid IN c.refs AND c.path <> s.path "
    "MERGE (c)-[:CALLS]->(s)"
)
INDEXED_HASHES = "MATCH (a:Artifact) WHERE a.indexed_hash IS NOT NULL RETURN a.path, a.indexed_hash"
CALLERS = (
    "MATCH (c:Symbol)-[:CALLS]->(s:Symbol) WHERE s.path = $path AND s.qual IN $quals AND c.path <> $path "
    "RETURN s.qual, c.path, c.qual ORDER BY c.path, c.qual LIMIT 40"
)
CALLS_FROM_FILE = (
    "MATCH (c:Symbol)-[:CALLS]->(s:Symbol) WHERE c.path = $path AND s.path <> $path "
    "RETURN s.path, s.qual, c.qual ORDER BY s.path, s.qual LIMIT 60"
)


def _write(store: Store, parsed: List[dict]) -> None:
    """Replace the symbols of these files in a few batched queries."""
    if not parsed:
        return
    store.query(DELETE_SYMBOLS, {"paths": [p["path"] for p in parsed]})
    syms, edges, ids = [], [], []
    for p in parsed:
        refs_by_src: Dict[str, List[str]] = {}
        for src, dst in p["edges"]:
            refs_by_src.setdefault(src, []).append(dst)
            edges.append({"src": src, "dst": dst})
        for d in p["defs"]:
            syms.append({"id": d["id"], "name": d["name"], "qual": d["qual"], "kind": d["kind"], "path": p["path"],
                         "sig": d["sig"], "line": d["line"], "refs": refs_by_src.get(d["id"], [])})
            ids.append(d["id"])
    store.query(CREATE_SYMBOLS, {"syms": syms})
    store.query(SET_HASHES, {"files": [{"path": p["path"], "hash": p["hash"]} for p in parsed]})
    if edges:
        store.query(OUTGOING_EDGES, {"edges": edges})
    store.query(INCOMING_EDGES, {"ids": ids})


def index_file(store: Store, project: str, rel: str, text: str) -> bool:
    """Re-index one edited file. Needs the project's module table, scanned from disk (cheap)."""
    if not rel.endswith(".py"):
        return False
    files = sym.scan_project(project, max_files=800)
    files[rel] = os.path.join(project, rel)
    parsed = sym.parse_file(text, rel, sym.module_table(list(files)))
    if parsed is None:
        return False
    _write(store, [parsed])
    return True


def index_project(store: Store, project: str, max_files: int = 600, budget_s: float = 2.0) -> Dict[str, int]:
    """Index files that are new or changed since last time. Time-boxed; the rest follows next session."""
    start = time.time()
    files = sym.scan_project(project, max_files=max_files)
    if not files:
        return {"indexed": 0, "skipped": 0}
    known = {r[0]: r[1] for r in store.rows(INDEXED_HASHES, read_only=True)}
    modules = sym.module_table(list(files))
    parsed: List[dict] = []
    skipped = 0
    for rel, ap in files.items():
        if time.time() - start > budget_s:
            break
        try:
            with open(ap, errors="ignore") as f:
                text = f.read()
        except OSError:
            continue
        if known.get(rel) == sym.content_hash(text):
            skipped += 1
            continue
        p = sym.parse_file(text, rel, modules)
        if p:
            parsed.append(p)
    # a few files per query keeps each statement small
    for i in range(0, len(parsed), 40):
        _write(store, parsed[i:i + 40])
    return {"indexed": len(parsed), "skipped": skipped}


def callers_of(store: Store, path: str, quals: Iterable[str]) -> List[dict]:
    rows = store.rows(CALLERS, {"path": path, "quals": list(quals)}, read_only=True)
    return [{"callee": r[0], "path": r[1], "caller": r[2]} for r in rows]


def callees_of_file(store: Store, path: str) -> List[dict]:
    rows = store.rows(CALLS_FROM_FILE, {"path": path}, read_only=True)
    return [{"path": r[0], "callee": r[1], "caller": r[2]} for r in rows]


def impact(store: Store, actor: str, path: str, breaking: List[Dict[str, str]],
           now: Optional[float] = None) -> Optional[str]:
    """Message for the editor of `path` about callers that break, or None when nothing is affected."""
    if not breaking:
        return None
    quals = [b["qual"] for b in breaking]
    callers = callers_of(store, path, quals)
    if not callers:
        return None
    t = _now(now)
    by_file: Dict[str, List[str]] = {}
    for c in callers:
        by_file.setdefault(c["path"], []).append("%s calls %s" % (c["caller"], c["callee"]))
    live = store.rows(queries.LIVE_LEASES_FOR_ARTIFACTS,
                      {"paths": list(by_file), "actor_id": actor, "now": t}, read_only=True)
    working: Dict[str, str] = {}
    for task, p in live:
        working.setdefault(p, str(task["owner"])[:8])
    lines = []
    for p, uses in list(by_file.items())[:6]:
        who = " (session %s is working in it now)" % working[p] if p in working else ""
        lines.append("- %s%s: %s" % (p, who, "; ".join(sorted(set(uses))[:3])))
    changed = "; ".join("%s: %s" % (b["name"], b["reason"]) for b in breaking[:3])
    return ("[MeshAgents] You changed how %s is called (%s). Callers elsewhere that may now break:\n%s\n"
            "Update them or keep the old call shape working." % (path, changed, "\n".join(lines)))
