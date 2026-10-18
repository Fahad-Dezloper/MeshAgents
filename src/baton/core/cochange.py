"""Files that change together, learned from git history (no cold start).

Graph additions (same per-workspace FalkorDB graph):
    (:Artifact)-[:CO_CHANGED {n, ratio}]->(:Artifact)
        n     = commits in which both files changed
        ratio = n / commits that changed the source file (so a->b and b->a differ)
    (:Artifact {cc_commits})            commits (inside the indexed window) that changed the file
    (:Artifact {hot, dep_files})        cached "many files depend on this one" flag (PageRank, refreshed rarely)
    (:CoChangeIndex {id:'main', sha})   last commit folded in, so each session only reads what is new

The pure functions (parse_log, resolve_renames, aggregate, rank_partners) are shared with the offline benchmark
in evals/cochange, so the benchmark measures exactly the logic the hook uses. Everything touching git or the
database fails soft: callers wrap it, and the session never waits on it for long.
"""

from __future__ import annotations

import fnmatch
import os
import posixpath
import subprocess
import time
from collections import Counter
from itertools import combinations
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from baton.graph.client import Store

MAX_COMMITS = 800          # newest commits considered
MAX_FILES_PER_COMMIT = 25  # bigger commits are sweeps (renames, formatting, releases), not "changed together"
DEFAULT_MIN_N = 3          # tuned by evals/cochange; see docs/RESULTS-COCHANGE.md
DEFAULT_MIN_RATIO = 0.5
HOOK_MIN_RATIO = 0.7       # what the hook uses: 73% precision / 24% noise offline (0.5 gives more hints, 33% noise)
HINT_MAX_FILES = 3
CHUNK_COMMITS = 150        # commits folded in per write round (the time box is checked between rounds)
GIT_TIMEOUT_S = 4.0
LOCK_SECONDS = 20
HOT_REFRESH_SECONDS = 6 * 3600
HOT_FRACTION = 0.10
HOT_MIN_DEP_FILES = 4

# Paths that change in lockstep with everything and say nothing about coupling.
_SKIP_NAMES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock", "pipfile.lock", "cargo.lock", "gemfile.lock",
    "composer.lock", "go.sum", "uv.lock", "bun.lockb", "npm-shrinkwrap.json", "mix.lock", "pubspec.lock",
    "podfile.lock", "flake.lock", "packages.lock.json", "gradle.lockfile",
}
_SKIP_DIRS = {"node_modules", "vendor", "vendored", "third_party", "third-party", "dist", "build", "__pycache__",
              ".git", ".venv", "venv", "site-packages", "bower_components", ".next", "coverage", "target"}
_SKIP_GLOBS = ("*.min.js", "*.min.css", "*.map", "*.pyc", "*.snap", "*_pb2.py", "*_pb2_grpc.py", "*.pb.go",
               "*.generated.*", "*_generated.*", "*.gen.go", "*.svg", "*.png", "*.jpg", "*.gif", "*.ico", "*.pdf")
# Release-notes files are edited by almost every commit of some projects.
_CHANGELOG_STEMS = ("changelog", "changes", "history", "news", "release_notes", "releasenotes")


def skip_path(path: str, changelog: bool = True) -> bool:
    p = path.replace("\\", "/")
    parts = p.split("/")
    base = parts[-1]
    low = base.lower()
    if low in _SKIP_NAMES or low.endswith(".lock"):
        return True
    if any(d in _SKIP_DIRS for d in parts[:-1]):
        return True
    if any(fnmatch.fnmatch(low, g) for g in _SKIP_GLOBS):
        return True
    if changelog and len(parts) <= 2 and posixpath.splitext(low)[0] in _CHANGELOG_STEMS:
        return True
    return False


# -- pure logic -----------------------------------------------------------------
Commit = Tuple[str, List[str]]  # (sha, files)


def parse_log(text: str) -> List[Tuple[str, List[Tuple[str, str, Optional[str]]]]]:
    """Parse `git log --format=%x01%H --name-status -M` output (newest first).

    Returns [(sha, [(status, path, old_path_or_None)])]; deleted files are kept with status 'D'."""
    out: List[Tuple[str, List[Tuple[str, str, Optional[str]]]]] = []
    cur: Optional[Tuple[str, list]] = None
    for line in text.splitlines():
        if line.startswith("\x01"):
            if cur:
                out.append(cur)
            cur = (line[1:].strip(), [])
            continue
        if not line.strip() or cur is None:
            continue
        cols = line.split("\t")
        st = cols[0][:1]
        if st in ("R", "C") and len(cols) >= 3:
            cur[1].append((st, cols[2], cols[1]))
        elif st in ("A", "M", "T", "D") and len(cols) >= 2:
            cur[1].append((st, cols[1], None))
    if cur:
        out.append(cur)
    return out


def resolve_renames(parsed_newest_first, follow: bool = True) -> List[Commit]:
    """Turn parsed log entries into (sha, files) oldest-first.

    With `follow`, a file renamed later is credited under its newest name in older commits (rename-aware).
    Deleted files and filtered paths are dropped."""
    mapping: Dict[str, str] = {}
    result: List[Commit] = []
    for sha, entries in parsed_newest_first:  # newest first so later renames are known
        files: List[str] = []
        for st, path, old in entries:
            name = mapping.get(path, path) if follow else path
            if st == "R" and old is not None and follow:
                mapping[old] = name
            if st == "D":
                continue
            if not skip_path(name) and name not in files:
                files.append(name)
        result.append((sha, files))
    result.reverse()
    return result


def aggregate(commits: Iterable[Commit], max_files: int = MAX_FILES_PER_COMMIT):
    """(files, pairs): files[f] = commits touching f; pairs[(a, b)] = commits touching both (a < b)."""
    files: Counter = Counter()
    pairs: Counter = Counter()
    for _sha, fs in commits:
        if not fs or len(fs) > max_files:
            continue
        files.update(fs)
        for a, b in combinations(sorted(fs), 2):
            pairs[(a, b)] += 1
    return files, pairs


def directed_edges(files: Dict[str, int], pairs: Dict[Tuple[str, str], int]) -> Dict[str, List[Tuple[str, int, float]]]:
    """src -> [(dst, n, ratio)] sorted best first (ratio, then n, then name for determinism)."""
    out: Dict[str, List[Tuple[str, int, float]]] = {}
    for (a, b), n in pairs.items():
        out.setdefault(a, []).append((b, n, n / files[a]))
        out.setdefault(b, []).append((a, n, n / files[b]))
    for v in out.values():
        v.sort(key=lambda t: (-t[2], -t[1], t[0]))
    return out


def rank_partners(cands: Sequence[Tuple[str, int, float]], min_n: int = DEFAULT_MIN_N,
                  min_ratio: float = DEFAULT_MIN_RATIO, limit: int = HINT_MAX_FILES,
                  exclude: Iterable[str] = ()) -> List[Tuple[str, int, float]]:
    skip = set(exclude)
    keep = [c for c in cands if c[1] >= min_n and c[2] >= min_ratio and c[0] not in skip]
    keep.sort(key=lambda t: (-t[2], -t[1], t[0]))
    return keep[:limit]


def format_hint(path: str, partners: Sequence[Tuple[str, int, float]], total: int) -> str:
    bits = ["%s (%d of %d commits)" % (p, n, total) for p, n, _r in partners]
    return "Files that usually change with %s: %s." % (path, ", ".join(bits))


# -- git ---------------------------------------------------------------------------
def _git(project: str, args: List[str], timeout: float = GIT_TIMEOUT_S) -> Optional[str]:
    env = dict(os.environ, GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0")
    try:
        r = subprocess.run(["git", "-c", "core.quotepath=off", "-C", project] + args, capture_output=True,
                           timeout=timeout, env=env)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    return r.stdout.decode("utf-8", "replace")


def head_sha(project: str) -> Optional[str]:
    out = _git(project, ["rev-parse", "--verify", "-q", "HEAD"])
    return out.strip() if out else None


def is_ancestor(project: str, sha: str) -> bool:
    return _git(project, ["merge-base", "--is-ancestor", sha, "HEAD"]) is not None


def read_history(project: str, since: Optional[str] = None, limit: int = MAX_COMMITS,
                 timeout: float = GIT_TIMEOUT_S) -> Optional[List[Commit]]:
    """Commits oldest-first, or None when git is unavailable / `since` is no longer in history."""
    args = ["log", "--no-merges", "--no-ext-diff", "--name-status", "-M", "--format=%x01%H", "-n", str(limit)]
    args.append("%s..HEAD" % since if since else "HEAD")
    args.append("--")
    out = _git(project, args, timeout=timeout)
    if out is None:
        return None
    return resolve_renames(parse_log(out))


# -- graph -------------------------------------------------------------------------
STATE_LOCK = (
    "MERGE (s:CoChangeIndex {id: 'main'}) WITH s WHERE coalesce(s.lock_until, 0) < $now "
    "SET s.lock_until = $until RETURN coalesce(s.sha, '')"
)
STATE_SET = "MATCH (s:CoChangeIndex {id: 'main'}) SET s.sha = $sha, s.indexed = coalesce(s.indexed, 0) + $k, s.at = $now"
STATE_UNLOCK = "MATCH (s:CoChangeIndex {id: 'main'}) SET s.lock_until = 0"
FILE_COUNTS = "UNWIND $files AS x MERGE (a:Artifact {path: x.p}) SET a.cc_commits = coalesce(a.cc_commits, 0) + x.c"
EDGE_COUNTS = (
    "UNWIND $rows AS x MATCH (a:Artifact {path: x.a}) MATCH (b:Artifact {path: x.b}) "
    "MERGE (a)-[r:CO_CHANGED]->(b) SET r.n = coalesce(r.n, 0) + x.n"
)
RATIOS = (
    "UNWIND $paths AS p MATCH (a:Artifact {path: p})-[r:CO_CHANGED]->(:Artifact) "
    "SET r.ratio = toFloat(r.n) / a.cc_commits"
)
RESET = (
    "MATCH ()-[r:CO_CHANGED]->() DELETE r"
)
RESET_COUNTS = "MATCH (a:Artifact) WHERE a.cc_commits IS NOT NULL SET a.cc_commits = null"
PARTNERS = (
    "MATCH (a:Artifact {path: $path}) OPTIONAL MATCH (a)-[r:CO_CHANGED]->(b:Artifact) "
    "WHERE r.n >= $min_n AND r.ratio >= $min_ratio "
    "RETURN a.cc_commits, a.hot, a.dep_files, b.path, r.n, r.ratio ORDER BY r.ratio DESC, r.n DESC, b.path LIMIT $lim"
)
TOUCHED_BY = "MATCH (t:Task {id: $id})-[:TOUCHES]->(a:Artifact) RETURN a.path"


def _batches(seq: list, size: int):
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


def _fold(store: Store, commits: List[Commit]) -> None:
    files, pairs = aggregate(commits)
    if not files:
        return
    for b in _batches([{"p": p, "c": c} for p, c in files.items()], 400):
        store.query(FILE_COUNTS, {"files": b})
    rows = []
    for (a, b), n in pairs.items():
        rows.append({"a": a, "b": b, "n": n})
        rows.append({"a": b, "b": a, "n": n})
    for b in _batches(rows, 500):
        store.query(EDGE_COUNTS, {"rows": b})
    for b in _batches(list(files), 400):
        store.query(RATIOS, {"paths": b})


def index_project(store: Store, project: str, budget_s: float = 2.0, max_commits: int = MAX_COMMITS,
                  now: Optional[float] = None) -> Dict[str, object]:
    """Fold new commits into the graph. Time-boxed: stops between chunks and resumes next session."""
    start = time.time()
    t = time.time() if now is None else now
    res: Dict[str, object] = {"commits": 0, "remaining": 0, "status": "ok"}
    head = head_sha(project)
    if not head:
        res["status"] = "no-git"
        return res
    rows = store.rows(STATE_LOCK, {"now": t, "until": t + LOCK_SECONDS})
    if not rows:
        res["status"] = "busy"  # another session is indexing right now
        return res
    since = rows[0][0] or None
    try:
        if since == head:
            res["status"] = "up-to-date"
            return res
        if since and not is_ancestor(project, since):
            # history was rewritten: start again from scratch
            store.query(RESET)
            store.query(RESET_COUNTS)
            store.query("MATCH (s:CoChangeIndex {id: 'main'}) SET s.sha = ''")
            since = None
        commits = read_history(project, since=since, limit=max_commits, timeout=max(0.5, budget_s))
        if commits is None:
            res["status"] = "git-failed"
            return res
        done = 0
        for chunk in _batches(commits, CHUNK_COMMITS):
            if done and time.time() - start > budget_s:
                break
            _fold(store, chunk)
            done += len(chunk)
            store.query(STATE_SET, {"sha": chunk[-1][0], "k": len(chunk), "now": t})
        res["commits"] = done
        res["remaining"] = len(commits) - done
        if res["remaining"]:
            res["status"] = "partial"
        return res
    finally:
        try:
            store.query(STATE_UNLOCK)
        except Exception:
            pass


def partners(store: Store, path: str, min_n: int = DEFAULT_MIN_N, min_ratio: float = DEFAULT_MIN_RATIO,
             limit: int = 10) -> Dict[str, object]:
    rows = store.rows(PARTNERS, {"path": path, "min_n": min_n, "min_ratio": min_ratio, "lim": limit},
                      read_only=True)
    if not rows:
        return {"total": 0, "hot": False, "dep_files": 0, "partners": []}
    total = int(rows[0][0] or 0)
    plist = [(r[3], int(r[4]), float(r[5])) for r in rows if r[3]]
    return {"total": total, "hot": bool(rows[0][1]), "dep_files": int(rows[0][2] or 0), "partners": plist}


def touched_paths(store: Store, task_id: str) -> set:
    return {r[0] for r in store.rows(TOUCHED_BY, {"id": task_id}, read_only=True)}


def hint_for(store: Store, project: str, path: str, already_touched: Iterable[str] = (),
             min_n: int = DEFAULT_MIN_N, min_ratio: float = DEFAULT_MIN_RATIO) -> Optional[str]:
    """One short line for the pre-edit context, or None when there is nothing worth saying."""
    info = partners(store, path, min_n, min_ratio, limit=12)
    cands = [p for p in info["partners"] if os.path.exists(os.path.join(project, p[0]))]  # type: ignore[union-attr]
    shown = rank_partners(cands, min_n, min_ratio, HINT_MAX_FILES, exclude=already_touched)
    parts: List[str] = []
    if shown:
        parts.append(format_hint(path, shown, int(info["total"])))  # type: ignore[arg-type]
    if info["hot"]:
        parts.append("%d other files depend on %s (top 10%% of the code graph by PageRank), so check its callers." % (
            int(info["dep_files"]), path))  # type: ignore[arg-type]
    return " ".join(parts) or None


# -- PageRank "many files depend on this" (cached, never run per hook) -------------------
DEP_FILES = (
    "MATCH (c:Symbol)-[:CALLS]->(s:Symbol) WHERE c.path <> s.path "
    "RETURN s.path, count(DISTINCT c.path)"
)
PAGERANK = "CALL algo.pageRank('Symbol', 'CALLS') YIELD node, score RETURN node.path, sum(score)"
HOT_SET = "UNWIND $rows AS x MATCH (a:Artifact {path: x.p}) SET a.hot = x.hot, a.dep_files = x.d"
HOT_CLEAR = "MATCH (a:Artifact) WHERE a.hot = true SET a.hot = false"
HOT_STAMP = "MERGE (s:CoChangeIndex {id: 'main'}) SET s.hot_at = $now"
HOT_AT = "MATCH (s:CoChangeIndex {id: 'main'}) RETURN s.hot_at"


def refresh_hot(store: Store, now: Optional[float] = None, force: bool = False) -> bool:
    """Flag files in the top 10% of PageRank (with enough dependants). Recomputed at most every few hours."""
    t = time.time() if now is None else now
    if not force:
        r = store.rows(HOT_AT, read_only=True)
        if r and r[0][0] and t - float(r[0][0]) < HOT_REFRESH_SECONDS:
            return False
    ranks = {r[0]: float(r[1]) for r in store.rows(PAGERANK, read_only=True) if r[0]}
    deps = {r[0]: int(r[1]) for r in store.rows(DEP_FILES, read_only=True)}
    store.query(HOT_CLEAR)
    if ranks:
        ordered = sorted(ranks, key=lambda p: (-ranks[p], p))
        top = set(ordered[:max(1, int(len(ordered) * HOT_FRACTION))])
        rows = [{"p": p, "hot": p in top and deps.get(p, 0) >= HOT_MIN_DEP_FILES, "d": deps.get(p, 0)}
                for p in ordered]
        for b in _batches(rows, 400):
            store.query(HOT_SET, {"rows": b})
    store.query(HOT_STAMP, {"now": t})
    return True
