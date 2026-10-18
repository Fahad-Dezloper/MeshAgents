"""A before/after snapshot of a project's source-like files, to see what a shell command changed.

Does not depend on parsing the command: before a write-like shell command we record (mtime_ns, size, text)
of up to MAX_FILES small source files; after it, files whose (mtime_ns, size) differ are the edits.
Everything here is best effort and never raises; when the project is too big or the scan too slow it
declines (returns False / None) and the caller falls back to the command's own target paths.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from typing import Dict, List, Optional, Tuple

SRC_EXT = {".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".rb", ".json", ".toml", ".yaml",
           ".yml", ".md", ".cfg", ".ini"}
SKIP_DIRS = {"node_modules", "venv", ".venv", "__pycache__", "build", "dist"}
MAX_FILES = 600
MAX_FILE_BYTES = 100 * 1024
MAX_TOTAL_BYTES = 12 * 1024 * 1024
SCAN_BUDGET_S = 0.08
DIFF_BUDGET_S = 0.15
STALE_DELETE_S = 24 * 3600
STALE_IGNORE_S = 2 * 3600

Entry = list  # [mtime_ns, size, text or None]


def snap_path(directory: str, actor: str) -> str:
    return os.path.join(directory, "shellsnap-%s.json" % hashlib.sha1(actor.encode()).hexdigest()[:10])


def scan(project: str, with_content: bool, budget_s: float = SCAN_BUDGET_S) -> Optional[Dict[str, Entry]]:
    """{relative path: [mtime_ns, size, text]} for source-like files; None when over budget or too many files."""
    start = time.monotonic()
    found: Dict[str, Entry] = {}
    total = 0
    stack: List[Tuple[str, str]] = [(project, "")]
    n = 0
    while stack:
        absdir, reldir = stack.pop()
        try:
            it = os.scandir(absdir)
        except OSError:
            continue
        with it:
            for e in it:
                n += 1
                if not n & 15 and time.monotonic() - start > budget_s:
                    return None
                name = e.name
                try:
                    if e.is_dir(follow_symlinks=False):
                        if name in SKIP_DIRS or name.startswith("."):
                            continue
                        stack.append((e.path, reldir + name + "/"))
                        continue
                    if not e.is_file(follow_symlinks=False):
                        continue
                    if os.path.splitext(name)[1].lower() not in SRC_EXT:
                        continue
                    st = e.stat(follow_symlinks=False)
                except OSError:
                    continue
                if st.st_size > MAX_FILE_BYTES:
                    continue
                if len(found) >= MAX_FILES:
                    return None
                text = None
                if with_content and total + st.st_size <= MAX_TOTAL_BYTES:
                    text = _read(e.path)
                    total += st.st_size
                found[reldir + name] = [st.st_mtime_ns, st.st_size, text]
    return found


def _read(path: str) -> Optional[str]:
    try:
        with open(path, "rb") as f:
            return f.read(MAX_FILE_BYTES + 1).decode("utf-8", errors="replace")
    except OSError:
        return None


def forget(directory: str, actor: str) -> None:
    try:
        os.remove(snap_path(directory, actor))
    except OSError:
        pass


def _prune(directory: str, now: float) -> None:
    try:
        for name in os.listdir(directory):
            if name.startswith("shellsnap-"):
                p = os.path.join(directory, name)
                try:
                    if now - os.path.getmtime(p) > STALE_DELETE_S:
                        os.remove(p)
                except OSError:
                    pass
    except OSError:
        pass


def take(project: str, directory: str, actor: str) -> bool:
    """Record the project's state for `actor`. False (and no snapshot left behind) when declined."""
    try:
        files = scan(project, with_content=True)
        if files is None:
            forget(directory, actor)
            return False
        now = time.time()
        os.makedirs(directory, mode=0o700, exist_ok=True)
        path = snap_path(directory, actor)
        tmp = "%s.%d.tmp" % (path, os.getpid())
        with open(tmp, "w") as f:
            json.dump({"project": project, "at": now, "files": files}, f)
        os.replace(tmp, path)
        _prune(directory, now)
        return True
    except Exception:
        return False


def diff(project: str, directory: str, actor: str) -> Optional[List[Tuple[str, Optional[str], str, bool]]]:
    """Changed files since `take`: [(path, old_text, new_text, existed)]; old_text is None for a new file or when it was not stored. The snapshot is
    consumed. None when there is no usable snapshot (the caller then falls back to the command's targets)."""
    path = snap_path(directory, actor)
    try:
        with open(path) as f:
            snap = json.load(f)
    except (OSError, ValueError):
        return None
    forget(directory, actor)
    try:
        if snap.get("project") != project or time.time() - float(snap.get("at", 0)) > STALE_IGNORE_S:
            return None
        before = snap["files"]
        after = scan(project, with_content=False, budget_s=DIFF_BUDGET_S)
        if after is None:
            return None
        out: List[Tuple[str, Optional[str], str, bool]] = []
        for rel in sorted(after):
            mt, size, _ = after[rel]
            old = before.get(rel)
            if old is not None and old[0] == mt and old[1] == size:
                continue
            new = _read(os.path.join(project, rel))
            if new is None:
                continue
            out.append((rel, old[2] if old is not None else None, new, old is not None))
        return out
    except Exception:
        return None
