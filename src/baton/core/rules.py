"""Project rules people state in conversation ("FYI the server is read-only, never use sqlite").

These facts live in a chat, not in the code, so the next session cannot find them by reading files.
Extraction is deliberate and conservative (a few clear markers, no model call); a missed rule costs
nothing, a noisy rule costs tokens in every later session.
"""

from __future__ import annotations

import hashlib
import re
from typing import List, Optional

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
MAX_PER_PROMPT = 4


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


def rule_id(sentence: str) -> str:
    return "dec_rule_" + hashlib.sha1(sentence.lower().encode()).hexdigest()[:12]


def record(store: Store, actor: str, prompt: str, now: Optional[float] = None) -> List[str]:
    """Store the rules found in a prompt (idempotent per sentence). Returns the stored texts."""
    stored = []
    for s in extract(scrub(prompt)):
        decisions.upsert_decision(store, actor, rule_id(s) + "_" + hashlib.sha1(actor.encode()).hexdigest()[:6],
                                  s, artifacts=[], kind="rule", now=now)
        stored.append(s)
    return stored
