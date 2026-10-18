"""Project rules people state in conversation ("FYI the server is read-only, never use sqlite").

These facts live in a chat, not in the code, so the next session cannot find them by reading files.
Extraction is deliberate and conservative (a few clear markers, no model call); a missed rule costs
nothing, a noisy rule costs tokens in every later session.
"""

from __future__ import annotations

import hashlib
import os
import re
from typing import Iterable, List, Optional, Set

from baton.core import decisions
from baton.core.safety import scrub
from baton.graph.client import Store

# Project-level markers: enough on their own.
_STRONG = re.compile(
    r"\b(never|always|from now on|going forward|convention|we decided|we've decided|we agreed|fyi|"
    r"heads up|in this (project|repo|codebase)|every new|all new|our (team|project|convention)|"
    r"we tried|rule:|must never|deploy target|in production|prod)\b", re.I)
# Task-level phrasing: only counts together with a strong marker or an explicit alternative.
_WEAK = re.compile(r"\b(do not|don'?t|avoid|must not|mustn'?t|only use|cannot|can'?t|doesn'?t work|deadlock\w*)\b", re.I)
_ALT = re.compile(r"\b(instead|rather than|use \S+ not|not \S+, use)\b", re.I)
_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+|;\s+")

MIN_CHARS, MAX_CHARS = 25, 260
MAX_PER_PROMPT = 15


def extract(prompt: str) -> List[str]:
    out: List[str] = []
    for raw in _SPLIT.split(str(prompt)):
        s = " ".join(raw.split()).strip(" -*#>`\"'")
        if not (MIN_CHARS <= len(s) <= MAX_CHARS) or s.endswith("?"):
            continue
        if _STRONG.search(s) or (_WEAK.search(s) and _ALT.search(s)):
            if s not in out:
                out.append(s)
        if len(out) >= MAX_PER_PROMPT:
            break
    return out


_STOP = set("""about after again all also always and any are because been before being both but can cannot could did does
doing done dont down each even ever every for from have here into its just like more most must never not now only other
our out over same should some such than that the their them then there these they this those through under until use
used using very was were what when where which while who will with without would you your we've fyi note""".split())
_WORD = re.compile(r"[a-z][a-z0-9_]{3,}")
_FILE = re.compile(r"[\w][\w./-]*\.(?:py|js|ts|tsx|jsx|go|rs|java|rb|json|toml|ya?ml|md)\b")
_DOTTED = re.compile(r"\b[a-z_]\w*(?:\.[a-z_]\w*)+\b")


def terms(text: str, limit: int = 40) -> List[str]:
    """Distinctive lowercase words of a sentence (path-like tokens are split), for relevance matching."""
    out: List[str] = []
    for w in _WORD.findall(str(text).lower().replace("/", " ").replace(".", " ")):
        if w not in _STOP and w not in out:
            out.append(w)
        if len(out) >= limit:
            break
    return out


def mentioned_paths(text: str, project: Optional[str]) -> List[str]:
    """Project files a sentence names: 'shop/batch.py' or the module form 'shop.batch' (only files that exist)."""
    if not project:
        return []
    cands: List[str] = [m for m in _FILE.findall(text)]
    for m in _DOTTED.findall(text):
        cands.append(m.replace(".", "/") + ".py")
    out: List[str] = []
    for c in cands:
        c = c.strip("./")
        if c and c not in out and os.path.isfile(os.path.join(project, c)):
            out.append(c)
    return out[:3]


def rule_id(sentence: str) -> str:
    return "dec_rule_" + hashlib.sha1(sentence.lower().encode()).hexdigest()[:12]


def record(store: Store, actor: str, prompt: str, now: Optional[float] = None,
           project: Optional[str] = None) -> List[str]:
    """Store the rules found in a prompt (idempotent per sentence). Returns the stored texts.

    A rule that names a project file is linked to it (ABOUT), so it surfaces when someone edits that file."""
    stored = []
    for s in extract(scrub(prompt)):
        did = rule_id(s) + "_" + hashlib.sha1(actor.encode()).hexdigest()[:6]
        decisions.upsert_decision(store, actor, did, s, artifacts=mentioned_paths(s, project), kind="rule", now=now)
        store.query("MATCH (d:Decision {id: $id}) SET d.terms = $terms", {"id": did, "terms": terms(s)})
        stored.append(s)
    return stored


RELEVANT = (
    "MATCH (d:Decision {kind: 'rule'}) WHERE d.status = 'open' AND d.author <> $actor AND d.created_at >= $since "
    "AND d.terms IS NOT NULL "
    "WITH d, size([t IN d.terms WHERE t IN $terms]) AS score WHERE score >= $min "
    "RETURN d.text, score ORDER BY score DESC, d.created_at DESC LIMIT $lim"
)


def relevant(store: Store, actor: str, prompt: str, now: float, exclude: Iterable[str] = (),
             since: float = 0.0, min_shared: int = 2, limit: int = 5) -> List[str]:
    """Rules stated earlier (by other sessions) that share distinctive words with this request, best first."""
    ts = terms(prompt)
    if len(ts) < min_shared:
        return []
    rows = store.rows(RELEVANT, {"actor": actor, "since": since, "terms": ts, "min": min_shared, "lim": limit + 8},
                      read_only=True)
    skip: Set[str] = set(exclude)
    out: List[str] = []
    for txt, _score in rows:
        if txt not in skip and txt not in out:
            out.append(txt)
        if len(out) >= limit:
            break
    return out
