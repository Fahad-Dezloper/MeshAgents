"""Human-facing commands: `baton status | why | retract | handoff` (the hooks are the main product)."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import List, Optional, TextIO

from baton.core import provenance
from baton.core.tasks import clip_goal
from baton.graph.client import Store
from baton.ui import state

ACTOR = "human-cli"


class Out:
    def __init__(self, stream: TextIO, color: Optional[bool] = None):
        self.s = stream
        tty = hasattr(stream, "isatty") and stream.isatty()
        self.color = (tty and not os.environ.get("NO_COLOR")) if color is None else color

    def c(self, code: str, text: str) -> str:
        return "\033[%sm%s\033[0m" % (code, text) if self.color else text

    def p(self, text: str = "") -> None:
        self.s.write(text + "\n")


def _age(ts: Optional[float], now: float) -> str:
    if not ts:
        return "-"
    s = max(0, int(now - ts))
    return "%ds" % s if s < 60 else "%dm" % (s // 60) if s < 3600 else "%dh" % (s // 3600) if s < 86400 else "%dd" % (s // 86400)


def _clean(text: object) -> str:
    """Strip control characters (incl. escape codes) from text written by other sessions."""
    return "".join(ch if ch.isprintable() else " " for ch in str(text))


def _store(args) -> Store:
    from baton.service import default_workspace

    return Store(args.workspace or os.environ.get("BATON_WORKSPACE") or default_workspace())


def _parser(prog: str, desc: str) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="baton " + prog, description=desc)
    p.add_argument("--workspace", default=None, help="workspace id (default: like the hooks)")
    return p


def cmd_status(argv, out: Out) -> int:
    p = _parser("status", "Live sessions, leases, shared files and latest decisions.")
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)
    st = state.build_state(_store(a))
    if a.json:
        out.p(json.dumps(st, indent=2))
        return 0 if st["connected"] else 1
    if not st["connected"]:
        out.p(out.c("31", "FalkorDB unreachable: ") + st["error"])
        out.p("Start it with: docker compose up -d   (check with: baton doctor)")
        return 1
    now, c = st["now"], st["counts"]
    out.p(out.c("1", "baton") + " workspace %s: %d live session(s), %d open decision(s), %d tainted, %d handoff(s)"
          % (st["workspace"], c["live_sessions"], c["open_decisions"], c["tainted"], c["handoffs"]))
    try:
        cc = state.code_state(_store(a), base=st)["counts"]
        out.p("code graph: %d file(s) indexed, %d symbol(s), %d call edge(s)" % (cc["files"], cc["symbols"], cc["calls"]))
    except Exception:
        pass
    sess = [s for s in st["sessions"] if s["is_session"]]
    if not sess and not st["decisions"]:
        out.p("\nNothing recorded yet. Start a session with the plugin: claude --plugin-dir /path/to/baton/plugin")
        return 0
    out.p("\n" + out.c("1", "Sessions"))
    out.p("  %-13s %-8s %-9s %-9s %s" % ("id", "state", "lease", "last edit", "goal / files"))
    for s in sorted(sess, key=lambda s: (s["status"] != "live", -(s["last_edit_at"] or 0))):
        col = {"live": "32", "expired": "33"}.get(s["status"], "2")
        lease = "%dm%02ds" % divmod(int(s["lease_left"]), 60) if s["status"] == "live" else "-"
        out.p("  %-13s %s %-9s %-9s %s" % (_clean(s["short"]), out.c(col, "%-8s" % s["status"]), lease,
                                         _age(s["last_edit_at"], now), _clean(clip_goal(s["goal"], 70))))
        if s["files"]:
            out.p("  %s%s" % (" " * 42, out.c("2", _clean(", ".join(s["files"][:4])))))
    shared = [f for f in st["files"] if f["collision"]]
    out.p("\n" + out.c("1", "Shared files") + " (edited by 2+ live sessions)")
    if not shared:
        out.p("  none")
    for f in shared:
        out.p("  " + out.c("31", _clean(f["path"])) + "  " + ", ".join(_clean(x["short"]) for x in f["sessions"]))
    out.p("\n" + out.c("1", "Latest decisions"))
    if not st["decisions"]:
        out.p("  none")
    for d in st["decisions"][:8]:
        col = {"open": "32", "tainted": "33", "retracted": "31"}.get(d["status"], "2")
        out.p("  %s %-9s %-10s %s" % (out.c(col, "%-9s" % d["status"]), d["kind"], _clean(d["id"]), _clean(clip_goal(d["text"], 80))))
    return 0


def cmd_why(argv, out: Out) -> int:
    p = _parser("why", "Why-chain and blast radius of a decision or finding.")
    p.add_argument("id")
    a = p.parse_args(argv)
    try:
        v = state.provenance_view(_store(a), a.id)
    except Exception as e:
        out.p("cannot read the graph: %s" % type(e).__name__)
        return 1
    if v is None:
        out.p("not found: %s" % a.id)
        return 1
    r = v["root"]
    out.p(out.c("1", "%s %s" % (r["kind"], r["id"])) + "  [%s]" % r["status"])
    out.p("  " + _clean(r["text"]))
    if r.get("reason"):
        out.p("  retracted: " + _clean(r["reason"]))
    out.p("\n" + out.c("1", "Based on") + " (%d)" % len(v["upstream"]))
    for u in v["upstream"] or []:
        out.p("  <- %s %s [%s] %s" % (u["kind"], u["id"], u["status"], _clean(clip_goal(u["text"], 90))))
    if not v["upstream"]:
        out.p("  nothing: this is a root")
    out.p("\n" + out.c("1", "Blast radius") + " (%d)" % len(v["downstream"]))
    for d in v["downstream"]:
        out.p("  -> %s [%s] %s" % (d["id"], d["status"], _clean(clip_goal(d["text"], 90))))
    if not v["downstream"]:
        out.p("  nothing depends on this")
    return 0


def cmd_retract(argv, out: Out, stdin: Optional[TextIO] = None) -> int:
    p = _parser("retract", "Mark a decision or finding wrong and taint what was built on it.")
    p.add_argument("id")
    p.add_argument("--reason", required=True)
    p.add_argument("--yes", "-y", action="store_true", help="do not ask for confirmation")
    a = p.parse_args(argv)
    store = _store(a)
    try:
        v = state.provenance_view(store, a.id)
    except Exception as e:
        out.p("cannot read the graph: %s" % type(e).__name__)
        return 1
    if v is None:
        out.p("not found: %s" % a.id)
        return 1
    if v["root"]["status"] == "retracted":
        out.p("%s is already retracted." % a.id)
        return 0
    out.p("About to retract %s %s: %s" % (v["root"]["kind"], a.id, _clean(clip_goal(v["root"]["text"], 80))))
    out.p("This would taint %d decision(s):" % len(v["would_taint"]))
    for d in v["would_taint"]:
        out.p("  - %s %s" % (d["id"], _clean(clip_goal(d["text"], 80))))
    if not a.yes:
        stdin = stdin or sys.stdin
        out.s.write("Retract? [y/N] ")
        out.s.flush()
        if stdin.readline().strip().lower() not in ("y", "yes"):
            out.p("aborted, nothing changed.")
            return 1
    res = provenance.retract(store, a.id, ACTOR, reason=a.reason)
    out.p(out.c("32", "retracted %s" % a.id) + "; tainted %d decision(s):" % len(res["tainted"]))
    for d in res["tainted"]:
        out.p("  - %s %s" % (d["id"], _clean(clip_goal(d["text"], 80))))
    return 0


def cmd_handoff(argv, out: Out) -> int:
    p = _parser("handoff", "Print the latest handoff briefing.")
    a = p.parse_args(argv)
    from baton.core import handoff

    store = _store(a)
    try:
        rows = store.rows("MATCH (h:Handoff) RETURN h.id ORDER BY h.created_at DESC LIMIT 1", read_only=True)
        if not rows:
            out.p("No handoff yet. A session writes one when it stops.")
            return 0
        pk = handoff.import_handoff(store, ACTOR, rows[0][0])
    except Exception as e:
        out.p("cannot read the graph: %s" % type(e).__name__)
        return 1
    out.p(_clean_multiline(pk["text"]))
    return 0


def _clean_multiline(text: object) -> str:
    return "\n".join(_clean(l) for l in str(text).split("\n"))


def cmd_impact(argv, out: Out) -> int:
    p = _parser("impact", "Who calls the public symbols of a file, and which sessions are in those files.")
    p.add_argument("path", help="file path relative to the project root")
    a = p.parse_args(argv)
    from baton.core.paths import normalize_path

    path = normalize_path(a.path)
    try:
        r = state.impact_for_file(_store(a), path)
    except Exception as e:
        out.p("cannot read the graph: %s" % type(e).__name__)
        return 1
    out.p(out.c("1", path) + ": %d public symbol(s) indexed" % r["public_symbols"])
    if r["sessions_here"]:
        out.p("  sessions editing it now: " + ", ".join(_clean(x) for x in r["sessions_here"]))
    if not r["public_symbols"]:
        out.p("Nothing indexed for this file (Python only; indexing happens as sessions edit).")
        return 0
    if not r["callers"]:
        out.p("No callers in other files.")
        return 0
    out.p("\nCallers elsewhere:")
    for c in r["callers"]:
        who = out.c("31", "  <- being edited by " + ", ".join(_clean(x) for x in c["sessions"])) if c["sessions"] else ""
        out.p("  %s%s" % (_clean(c["file"]), who))
        for u in c["uses"][:4]:
            out.p("      " + _clean(u))
    return 0


def cmd_together(argv, out: Out) -> int:
    p = _parser("together", "Files that usually change together with a file, learned from git history.")
    p.add_argument("path", help="file path relative to the project root")
    p.add_argument("--min-n", type=int, default=2, help="least commits together (default 2)")
    p.add_argument("--min-ratio", type=float, default=0.3, help="least share of the file's commits (default 0.3)")
    a = p.parse_args(argv)
    from baton.core import cochange
    from baton.core.paths import normalize_path

    path = normalize_path(a.path)
    try:
        r = cochange.partners(_store(a), path, a.min_n, a.min_ratio, limit=15)
    except Exception as e:
        out.p("cannot read the graph: %s" % type(e).__name__)
        return 1
    out.p(out.c("1", path) + ": changed in %d indexed commit(s)" % r["total"])
    if not r["total"]:
        out.p("No history indexed for this file (index builds at session start from `git log`).")
        return 0
    if r["hot"]:
        out.p("  %d other files depend on it (top 10%% by PageRank)" % r["dep_files"])
    if not r["partners"]:
        out.p("No partner changes with it often enough.")
        return 0
    for f, n, ratio in r["partners"]:
        out.p("  %-50s %d of %d commits (%d%%)" % (_clean(f), n, r["total"], round(ratio * 100)))
    return 0


COMMANDS = {"together": cmd_together, "impact": cmd_impact, "status": cmd_status, "why": cmd_why, "retract": cmd_retract, "handoff": cmd_handoff}


def main(argv: List[str], stream: Optional[TextIO] = None) -> int:
    out = Out(stream or sys.stdout)
    try:
        return COMMANDS[argv[0]](argv[1:], out)
    except BrokenPipeError:
        return 0
