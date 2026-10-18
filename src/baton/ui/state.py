"""Read-only snapshot of one workspace graph for the dashboard and the human CLI.

Every query goes through `ro_query`; nothing here can write. Text fields come from other
sessions and are returned as-is (raw JSON): consumers must treat them as untrusted.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from baton.core import provenance
from baton.core.tasks import clip_goal
from baton.graph.client import Store

MAX_TASKS = 60
MAX_DECISIONS = 100
MAX_FINDINGS = 40
MAX_FILES = 80
MAX_GRAPH_NODES = 150
TEXT_CAP = 600


def _s(v: Any, n: int = TEXT_CAP) -> str:
    return "" if v is None else str(v)[:n]


def _f(v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def task_status(t: dict, now: float) -> str:
    st = t.get("status", "")
    if st == "claimed":
        return "live" if _f(t.get("lease_until")) >= now else "expired"
    return {"done": "ended"}.get(st, st or "unknown")


def empty_state(workspace: str, now: float, error: str = "") -> dict:
    return {
        "workspace": workspace, "now": now, "connected": not error, "error": error,
        "counts": {"live_sessions": 0, "sessions": 0, "open_decisions": 0, "tainted": 0,
                   "retracted": 0, "handoffs": 0, "collisions": 0},
        "sessions": [], "files": [], "decisions": [], "findings": [],
        "graph": {"nodes": [], "edges": [], "truncated": False},
    }


def build_state(store: Store, now: Optional[float] = None) -> dict:
    now = time.time() if now is None else now
    ws = store.workspace
    try:
        task_rows = store.rows(
            "MATCH (t:Task) OPTIONAL MATCH (t)-[:TOUCHES]->(a:Artifact) "
            "RETURN t, collect(a.path) ORDER BY coalesce(t.last_edit_at, t.created_at) DESC",
            read_only=True)
        dec_rows = store.rows(
            "MATCH (d:Decision) OPTIONAL MATCH (d)-[:ABOUT]->(a:Artifact) "
            "WITH d, collect(DISTINCT a.path) AS paths OPTIONAL MATCH (d)-[:BASED_ON]->(s) "
            "RETURN d, paths, collect(DISTINCT s.id) "
            "ORDER BY coalesce(d.updated_at, d.created_at) DESC LIMIT %d" % MAX_DECISIONS,
            read_only=True)
        fnd_rows = store.rows(
            "MATCH (f:Finding) RETURN f ORDER BY f.created_at DESC LIMIT %d" % MAX_FINDINGS,
            read_only=True)
        hnd = store.rows("MATCH (h:Handoff) RETURN count(h)", read_only=True)
        dep_rows = store.rows(
            "MATCH (a:Task)-[:DEPENDS_ON]->(b:Task) RETURN a.id, b.id", read_only=True)
    except Exception as e:  # DB down, graph missing, timeout
        return empty_state(ws, now, "%s: %s" % (type(e).__name__, str(e)[:160]))

    # Sessions
    sessions: List[dict] = []
    for t, paths in task_rows[:MAX_TASKS]:
        status = task_status(t, now)
        sessions.append({
            "id": _s(t.get("id"), 80), "short": _s(t.get("owner") or t.get("id"), 80)[:12],
            "owner": _s(t.get("owner"), 80), "is_session": bool(t.get("session")),
            "goal": clip_goal(_s(t.get("goal")), 220), "status": status,
            "files": sorted(_s(p, 300) for p in paths)[:30], "file_count": len(paths),
            "last_edit_at": _f(t.get("last_edit_at")) or None,
            "last_edit_path": _s(t.get("last_edit_path"), 300),
            "created_at": _f(t.get("created_at")) or None,
            "lease_until": _f(t.get("lease_until")) or None,
            "lease_left": max(0.0, _f(t.get("lease_until")) - now) if status == "live" else 0.0,
            "collides_with": [],
        })
    # Collisions: live sessions sharing a file
    by_file: Dict[str, List[dict]] = {}
    for s in sessions:
        for p in s["files"]:
            by_file.setdefault(p, []).append(s)
    collisions = set()
    for p, ss in by_file.items():
        live = [s for s in ss if s["status"] == "live"]
        if len(live) > 1:
            collisions.add(p)
            for s in live:
                s["collides_with"].append({"file": p, "with": [o["short"] for o in live if o is not s]})
    files = []
    for p, ss in by_file.items():
        files.append({
            "path": p, "sessions": [{"short": s["short"], "status": s["status"]} for s in ss],
            "session_count": len(ss), "collision": p in collisions,
            "last_edit_at": max([s["last_edit_at"] or 0 for s in ss] or [0]) or None,
        })
    files.sort(key=lambda f: (-int(f["collision"]), -f["session_count"], -(f["last_edit_at"] or 0), f["path"]))
    files = files[:MAX_FILES]

    # Decisions / findings
    decisions = []
    for d, paths, based in dec_rows:
        decisions.append({
            "id": _s(d.get("id"), 80), "text": _s(d.get("text"), 2000), "kind": _s(d.get("kind") or "note", 20),
            "status": _s(d.get("status") or "open", 20), "author": _s(d.get("author"), 80),
            "created_at": _f(d.get("created_at")) or None, "files": [_s(p, 300) for p in paths][:20],
            "based_on": [_s(b, 80) for b in based if b], "tainted_by": _s(d.get("tainted_by"), 80),
            "retract_reason": _s(d.get("retract_reason"), 400),
        })
    findings = [{
        "id": _s(f.get("id"), 80), "text": _s(f.get("text"), 2000), "source": _s(f.get("source"), 300),
        "status": _s(f.get("status") or "open", 20), "author": _s(f.get("author"), 80),
        "created_at": _f(f.get("created_at")) or None, "retract_reason": _s(f.get("retract_reason"), 400),
    } for (f,) in fnd_rows]

    counts = {
        "live_sessions": sum(1 for s in sessions if s["is_session"] and s["status"] == "live"),
        "sessions": sum(1 for s in sessions if s["is_session"]),
        "open_decisions": sum(1 for d in decisions if d["status"] == "open"),
        "tainted": sum(1 for d in decisions if d["status"] == "tainted"),
        "retracted": sum(1 for d in decisions if d["status"] == "retracted") + sum(1 for f in findings if f["status"] == "retracted"),
        "handoffs": int(hnd[0][0]) if hnd else 0,
        "collisions": len(collisions),
    }
    return {"workspace": ws, "now": now, "connected": True, "error": "", "counts": counts,
            "sessions": sessions, "files": files, "decisions": decisions, "findings": findings,
            "graph": _graph(sessions, decisions, findings, dep_rows)}


def _graph(sessions, decisions, findings, deps) -> dict:
    """Nodes (task/artifact/decision/finding) and edges, capped. Layout is done client side."""
    nodes: Dict[str, dict] = {}
    edges: List[dict] = []

    def add(nid, kind, label, status=""):
        if nid not in nodes and len(nodes) < MAX_GRAPH_NODES:
            nodes[nid] = {"id": nid, "kind": kind, "label": _s(label, 80), "status": status}
        return nid in nodes

    for s in sessions:
        add("T:" + s["id"], "task", s["short"] + " " + s["goal"], s["status"])
    for d in decisions:
        add("D:" + d["id"], "decision", d["text"], d["status"])
    for f in findings:
        add("F:" + f["id"], "finding", f["text"], f["status"])
    for s in sessions:
        for p in s["files"]:
            if add("A:" + p, "artifact", p) and "T:" + s["id"] in nodes:
                edges.append({"from": "T:" + s["id"], "to": "A:" + p, "type": "TOUCHES"})
    for d in decisions:
        for p in d["files"]:
            if add("A:" + p, "artifact", p) and "D:" + d["id"] in nodes:
                edges.append({"from": "D:" + d["id"], "to": "A:" + p, "type": "ABOUT"})
        for b in d["based_on"]:
            for pre in ("D:", "F:"):
                if pre + b in nodes:
                    edges.append({"from": "D:" + d["id"], "to": pre + b, "type": "BASED_ON"})
    for a, b in deps:
        edges.append({"from": "T:" + str(a), "to": "T:" + str(b), "type": "DEPENDS_ON"})
    edges = [e for e in edges if e["from"] in nodes and e["to"] in nodes]
    return {"nodes": list(nodes.values()), "edges": edges, "truncated": len(nodes) >= MAX_GRAPH_NODES}


def _brief(x: dict, kind: str) -> dict:
    return {"id": _s(x.get("id"), 80), "kind": kind, "text": _s(x.get("text"), 2000),
            "status": _s(x.get("status"), 20), "author": _s(x.get("author"), 80),
            "dkind": _s(x.get("kind"), 20), "source": _s(x.get("source"), 300),
            "reason": _s(x.get("retract_reason"), 400)}


def provenance_view(store: Store, item_id: str) -> Optional[dict]:
    """Upstream why-chain, downstream blast radius and the read-only retraction preview."""
    item_id = item_id[:80]
    rows = store.rows("MATCH (d:Decision {id: $id}) RETURN d", {"id": item_id}, read_only=True)
    kind = "decision"
    if not rows:
        rows = store.rows("MATCH (f:Finding {id: $id}) RETURN f", {"id": item_id}, read_only=True)
        kind = "finding"
    if not rows:
        return None
    root = rows[0][0]
    up = {"decisions": [], "findings": []}
    if kind == "decision":
        up = provenance.why(store, item_id)
    down = provenance.blast_radius(store, item_id)
    ids = [item_id] + [d["id"] for d in up["decisions"]] + [f["id"] for f in up["findings"]] + [d["id"] for d in down]
    edges = [{"from": _s(r[0], 80), "to": _s(r[1], 80)} for r in store.rows(
        "MATCH (a:Decision)-[:BASED_ON]->(b) WHERE a.id IN $ids AND b.id IN $ids RETURN a.id, b.id",
        {"ids": ids[:300]}, read_only=True)]
    return {
        "root": _brief(root, kind),
        "upstream": [_brief(d, "decision") for d in up["decisions"]] + [_brief(f, "finding") for f in up["findings"]],
        "downstream": [_brief(d, "decision") for d in down],
        "would_taint": [_brief(d, "decision") for d in down if d.get("status") == "open"],
        "edges": edges,
    }


# ---------------------------------------------------------------- code graph (read-only)

MAX_CODE_FILES = 60
MAX_CODE_EDGES = 150
MAX_EDGE_ROWS = 4000
_NAME = None


def _names_in(text: str) -> set:
    import re

    return {m.split(".")[-1] for m in re.findall(r"([A-Za-z_][\w.]*)\(", text or "")} - {"interface"}


def code_state(store: Store, base: Optional[dict] = None, now: Optional[float] = None) -> dict:
    """Files indexed, symbols, call edges, a file-level dependency map and recent-change impact."""
    base = base if base is not None else build_state(store, now)
    out = {"workspace": store.workspace, "now": base["now"], "connected": base["connected"], "error": base["error"],
           "counts": {"files": 0, "symbols": 0, "calls": 0}, "files": [], "edges": [], "impact": [],
           "truncated": False}
    if not base["connected"]:
        return out
    try:
        nfiles = store.rows("MATCH (a:Artifact) WHERE a.indexed_hash IS NOT NULL RETURN count(a)", read_only=True)
        syms = store.rows("MATCH (s:Symbol) RETURN s.path, s.qual, s.name, s.sig, s.line, s.kind "
                          "ORDER BY s.path, s.line LIMIT 6000", read_only=True)
        calls = store.rows("MATCH (c:Symbol)-[:CALLS]->(s:Symbol) RETURN c.path, c.qual, s.path, s.qual LIMIT %d"
                           % MAX_EDGE_ROWS, read_only=True)
        ncalls = store.rows("MATCH (:Symbol)-[r:CALLS]->(:Symbol) RETURN count(r)", read_only=True)
    except Exception as e:
        out.update(connected=False, error="%s: %s" % (type(e).__name__, str(e)[:160]))
        return out
    out["counts"] = {"files": int(nfiles[0][0]) if nfiles else 0, "symbols": len(syms),
                     "calls": int(ncalls[0][0]) if ncalls else 0}

    live: Dict[str, List[str]] = {}
    for s in base["sessions"]:
        if s["status"] == "live":
            for p in s["files"]:
                live.setdefault(p, []).append(s["short"])
    iface: Dict[str, int] = {}
    for d in base["decisions"]:
        if d["status"] == "open" and d["kind"] == "interface":
            for p in d["files"]:
                iface[p] = iface.get(p, 0) + 1

    by_file: Dict[str, dict] = {}

    def node(p):
        return by_file.setdefault(p, {"path": _s(p, 300), "symbols": [], "called_from": {}, "calls_into": {},
                                      "in_weight": 0, "out_weight": 0})

    for path, qual, name, sig, line, kind in syms:
        n = node(path)
        if len(n["symbols"]) < 25:
            n["symbols"].append({"qual": _s(qual, 120), "sig": _s(sig, 200), "line": int(line or 0), "kind": _s(kind, 12)})
    weights: Dict[tuple, int] = {}
    for cpath, cqual, spath, squal in calls:
        if cpath == spath:
            continue
        weights[(cpath, spath)] = weights.get((cpath, spath), 0) + 1
        node(cpath)["out_weight"] += 1
        node(spath)["in_weight"] += 1
        node(spath)["called_from"].setdefault(cpath, []).append("%s -> %s" % (cqual, squal))
        node(cpath)["calls_into"].setdefault(spath, []).append("%s -> %s" % (cqual, squal))

    def rank(p):
        n = by_file[p]
        return (-(len(live.get(p, [])) > 0), -(n["in_weight"] + n["out_weight"]), p)

    paths = sorted(by_file, key=rank)
    out["truncated"] = len(paths) > MAX_CODE_FILES
    keep = set(paths[:MAX_CODE_FILES])
    for p in paths[:MAX_CODE_FILES]:
        n = by_file[p]
        out["files"].append({
            "path": n["path"], "symbols": n["symbols"], "in_weight": n["in_weight"], "out_weight": n["out_weight"],
            "called_from": [{"file": _s(f, 300), "uses": sorted(set(u))[:8]} for f, u in sorted(n["called_from"].items())[:12]],
            "calls_into": [{"file": _s(f, 300), "uses": sorted(set(u))[:8]} for f, u in sorted(n["calls_into"].items())[:12]],
            "live": live.get(p, []), "interface_decisions": iface.get(p, 0)})
    edges = sorted(((a, b, w) for (a, b), w in weights.items() if a in keep and b in keep), key=lambda e: (-e[2], e[0], e[1]))
    out["edges"] = [{"from": _s(a, 300), "to": _s(b, 300), "weight": w} for a, b, w in edges[:MAX_CODE_EDGES]]

    # Impact of recent interface changes: callers elsewhere, flagged when a live session is in that file.
    by_name: Dict[str, List[tuple]] = {}
    for path, qual, name, sig, line, kind in syms:
        by_name.setdefault(path, []).append((qual, name))
    callers_of: Dict[tuple, set] = {}
    for cpath, cqual, spath, squal in calls:
        if cpath != spath:
            callers_of.setdefault((spath, squal), set()).add((cpath, cqual))
    for d in base["decisions"]:
        low = d["text"].lower()
        if d["status"] != "open" or d["kind"] != "interface" or not ("signature changed" in low or "removed" in low):
            continue
        names = _names_in(d["text"])
        hits = []
        for fpath in d["files"]:
            for qual, name in by_name.get(fpath, []):
                if name in names or qual in names:
                    for cpath, cqual in sorted(callers_of.get((fpath, qual), ())):
                        hits.append({"symbol": _s(qual, 120), "file": _s(fpath, 300), "caller_file": _s(cpath, 300),
                                     "caller": _s(cqual, 120), "being_edited_by": live.get(cpath, [])})
        if hits:
            out["impact"].append({"decision_id": d["id"], "text": d["text"][:300], "author": d["author"],
                                  "created_at": d["created_at"], "callers": hits[:30],
                                  "affected_live": sorted({x for h in hits for x in h["being_edited_by"]})})
    return out


def impact_for_file(store: Store, path: str, base: Optional[dict] = None) -> dict:
    """Callers of a file's public symbols, grouped by calling file, with live sessions in those files."""
    base = base if base is not None else build_state(store)
    live: Dict[str, List[str]] = {}
    for s in base["sessions"]:
        if s["status"] == "live":
            for p in s["files"]:
                live.setdefault(p, []).append(s["short"])
    rows = store.rows(
        "MATCH (c:Symbol)-[:CALLS]->(s:Symbol) WHERE s.path = $p AND c.path <> $p AND NOT s.name STARTS WITH '_' "
        "RETURN c.path, c.qual, s.qual ORDER BY c.path, s.qual LIMIT 300", {"p": path}, read_only=True)
    groups: Dict[str, List[str]] = {}
    for cpath, cqual, squal in rows:
        groups.setdefault(cpath, []).append("%s calls %s" % (cqual, squal))
    own = store.rows("MATCH (s:Symbol {path: $p}) WHERE NOT s.name STARTS WITH '_' RETURN count(s)", {"p": path}, read_only=True)
    return {"path": path, "public_symbols": int(own[0][0]) if own else 0,
            "callers": [{"file": f, "uses": sorted(set(u)), "sessions": live.get(f, [])} for f, u in groups.items()],
            "sessions_here": live.get(path, [])}
