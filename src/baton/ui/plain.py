"""Plain-English wording for the dashboard. Pure functions; input is untrusted text, output is clipped text."""

from __future__ import annotations

import re
from typing import Iterable, List

KIND_LABEL = {"interface": "function changed", "storage": "storage changed", "config": "setting changed",
              "rename": "file moved", "rule": "rule", "note": "note", "other": "note"}

_LABEL = re.compile(r"^\s*(?:your\s+|the\s+)?(?:ticket|task|job|goal|request|issue|story)\s*#?[\w-]*\s*[:\-–]\s*", re.I)
_BOILER = re.compile(
    r"^(?:you are|you're|you will|you must|you should|act as|as an?\b|please (?:read|note|make sure|do not|don't)|"
    r"do not|don't|never\b|important|note:|rules?:|context:|background:|when (?:you are )?done|"
    r"the repo|this repo|the project|this project|work in|working in|stay in|only edit)", re.I)
_LEAD = re.compile(r"^(?:please|kindly|now|first|ok(?:ay)?|so|hey|hi)[, ]+", re.I)
_EMBED = re.compile(r"(?:your\s+(?:task|ticket|job|goal)\s+is(?:\s+to)?|(?:task|ticket|job)\s*#?[\w-]*\s*:)\s*(.+)$", re.I)


def _sentences(text: str) -> List[str]:
    out: List[str] = []
    for chunk in str(text).split(" || "):
        out.extend(p for p in re.split(r"(?<=[.!?])\s+(?=[A-Z\"'(])|\n+", chunk) if p.strip())
    return out


def clip_word(t: str, n: int) -> str:
    t = " ".join(str(t).split())
    if len(t) <= n:
        return t
    cut = t[: n - 1]
    if " " in cut[n // 2:]:
        cut = cut.rsplit(" ", 1)[0]
    return cut.rstrip(" ,;:-") + "…"


def plain_task(goal: str, has_goal: bool = True, n: int = 60) -> str:
    """The first meaningful sentence of a ticket: no shared preamble, no 'Ticket 12:' label, about `n` chars."""
    if not has_goal or not str(goal).strip():
        return "Waiting for its first task"
    first = ""
    for s in _sentences(goal):
        s = s.strip()
        if _BOILER.match(s):
            m = _EMBED.search(s)
            if not m:
                continue
            s = m.group(1)
        for _ in range(3):
            s2 = _LABEL.sub("", s)
            if s2 == s:
                break
            s = s2
        s = _LEAD.sub("", s).strip().rstrip(".!")
        if len(s) >= 6:
            first = s
            break
    if not first:
        whole = _LABEL.sub("", " ".join(str(goal).split())).strip()
        first = "Working on a task" if (not whole or _BOILER.match(whole)) else whole
    first = first[:1].upper() + first[1:]
    return clip_word(first, n)


def base(p: str) -> str:
    return str(p).rstrip("/").split("/")[-1]


def _arrow_added(pair: str) -> str:
    """'get_order(a) -> get_order(a, tenant)' -> ('get_order', 'tenant') as 'get_order|tenant'."""
    m = re.match(r"\s*([\w.]+)\s*\(([^)]*)\)[^>]*->\s*[\w.]+\s*\(([^)]*)\)", pair)
    if not m:
        return ""
    name = m.group(1).split(".")[-1]
    old = {x.strip().split("=")[0].split(":")[0].strip("* ") for x in m.group(2).split(",") if x.strip()}
    new = [x.strip().split("=")[0].split(":")[0].strip("* ") for x in m.group(3).split(",") if x.strip()]
    added = [x for x in new if x and x not in old and x not in ("self", "cls")]
    return name + "|" + (added[0] if added else "")


def plain_change(kind: str, text: str, files: Iterable[str] = ()) -> str:
    """A verb phrase for a recorded change, e.g. 'changed get_order: it now needs a tenant'."""
    text = " ".join(str(text).split())
    files = [base(f) for f in files if f]
    where = files[0] if files else ""
    if kind == "rule":
        return "noted a rule: " + clip_word(text, 70)
    if kind == "interface":
        m = re.search(r"signature changed:\s*(.+?)(?:;|$)", text)
        if m:
            parts = _arrow_added(m.group(1))
            if parts:
                name, extra = parts.split("|")
                return "changed %s: it now needs %s" % (name, ("a " + extra) if extra else "different inputs")
        m = re.search(r"removed:\s*([\w.]+)", text)
        if m:
            return "removed %s%s" % (m.group(1).split(".")[-1], " from " + where if where else "")
        m = re.search(r"added:\s*([\w.]+)", text)
        if m:
            return "added %s%s" % (m.group(1).split(".")[-1], " to " + where if where else "")
        if text.startswith("new module"):
            return "added a new file" + (": " + where if where else "")
        return "changed %s: %s" % (where or "a function", clip_word(text, 60))
    if kind == "storage":
        m = re.search(r"now uses\s+(.+)$", text)
        if m:
            return "now stores data with %s" % clip_word(m.group(1), 40)
        return "changed how data is stored: " + clip_word(text, 60)
    if kind == "config":
        m = re.search(r"keys:\s*(.+)$", text)
        return "changed settings%s%s" % (" in " + where if where else "", ": " + clip_word(m.group(1), 50) if m else "")
    if kind == "rename":
        m = re.match(r"renamed/moved\s+(\S+)\s*->\s*(\S+)", text)
        if m:
            return "moved %s to %s" % (base(m.group(1)), base(m.group(2)))
        return "moved a file"
    m = re.search(r"added dependency:\s*(.+)$", text)
    if m:
        return "started using %s%s" % (clip_word(m.group(1), 40), " in " + where if where else "")
    return "noted: " + clip_word(text, 70)


def cap_first(s: str) -> str:
    return s[:1].upper() + s[1:]
