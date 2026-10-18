"""A record of every heads-up a session was given, so people can see what the product did for it.

(:Actor)-[:WAS_TOLD]->(:Notice {id, kind, summary, detail, files, at})

`summary` is one short plain sentence for people; `detail` is the exact message the session received.
Recording is best effort: it must never affect the session.
"""

from __future__ import annotations

import time
from typing import Iterable, Optional

from baton.core.safety import scrub
from baton.graph.client import Store, new_id

KINDS = ("collision", "nearby", "impact", "hint", "rule", "briefing", "duplicate")


def record(store: Store, actor: str, kind: str, summary: str, detail: str = "",
           files: Iterable[str] = (), now: Optional[float] = None) -> Optional[str]:
    """Store one notice for `actor`. Returns its id, or None if it could not be stored."""
    try:
        if kind not in KINDS:
            kind = "briefing"
        nid = new_id("ntc")
        store.query(
            "MERGE (a:Actor {id: $actor}) "
            "CREATE (a)-[:WAS_TOLD]->(:Notice {id: $id, kind: $kind, summary: $summary, detail: $detail,"
            " files: $files, at: $at})",
            {"actor": actor, "id": nid, "kind": kind, "summary": scrub(summary, 160),
             "detail": scrub(detail, 600), "files": [str(f)[:200] for f in list(files)[:6]],
             "at": time.time() if now is None else now},
        )
        return nid
    except Exception:
        return None


def names(paths: Iterable[str], limit: int = 3) -> str:
    """'db.py, api.py' for a short sentence."""
    base = []
    for p in paths:
        b = str(p).rsplit("/", 1)[-1]
        if b and b not in base:
            base.append(b)
    more = len(base) - limit
    out = ", ".join(base[:limit])
    return out + (" and %d more" % more if more > 0 else "")
