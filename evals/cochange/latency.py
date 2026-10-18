"""Index time, query time and added hook latency on a real repository (needs FalkorDB; uses a cc_* graph and drops it).

Usage: python -B evals/cochange/latency.py REPO_DIR   (REPO_DIR must be checked out so partner files exist)
"""
from __future__ import annotations

import json
import os
import statistics
import subprocess
import sys
import time
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "..", "src")
sys.path.insert(0, SRC)
from baton.core import cochange as cc  # noqa: E402
from baton.graph.client import Store  # noqa: E402


def pct(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(q * len(xs)))]


def hook_ms(env, payload, n=15):
    ts = []
    for _ in range(n):
        t = time.time()
        subprocess.run([sys.executable, "-B", "-m", "baton.cli", "pre-tool"], input=json.dumps(payload).encode(),
                       env=env, capture_output=True)
        ts.append((time.time() - t) * 1000)
    return ts


def main(repo):
    name = os.path.basename(repo.rstrip("/"))
    store = Store("cc_lat_%s_%s" % (name, uuid.uuid4().hex[:5]))
    out = {"repo": name}
    try:
        store.bootstrap()
        t = time.time()
        r = cc.index_project(store, repo, budget_s=60)
        out["first_index_s"] = round(time.time() - t, 2)
        out["first_index"] = r
        t = time.time()
        cc.index_project(store, repo, budget_s=2)
        out["noop_reindex_ms"] = round((time.time() - t) * 1000, 1)
        t = time.time(); cc.refresh_hot(store); out["refresh_hot_first_ms"] = round((time.time() - t) * 1000, 1)
        t = time.time(); cc.refresh_hot(store); out["refresh_hot_cached_ms"] = round((time.time() - t) * 1000, 1)
        # graph vs in-memory: identical counts?
        hist = cc.read_history(repo)
        files, pairs = cc.aggregate(hist)
        edges = cc.directed_edges(files, pairs)
        rows = store.rows("MATCH (a:Artifact)-[r:CO_CHANGED]->(b:Artifact) RETURN count(r)")
        out["edges_in_graph"] = rows[0][0]
        out["edges_in_memory"] = sum(len(v) for v in edges.values())
        mism = 0
        for f in sorted(files, key=lambda x: -files[x])[:40]:
            g = {p: (n, round(ra, 6)) for p, n, ra in cc.partners(store, f, 1, 0.0, limit=100000)["partners"]}
            m = {p: (n, round(ra, 6)) for p, n, ra in edges.get(f, [])}
            mism += g != m
        out["top40_files_mismatching"] = mism
        # query time
        hot = [f for f in sorted(files, key=lambda x: -files[x]) if os.path.exists(os.path.join(repo, f))][:30]
        qs = []
        for f in hot * 3:
            t = time.time(); cc.hint_for(store, repo, f); qs.append((time.time() - t) * 1000)
        out["hint_for_ms_p50_p95"] = [round(statistics.median(qs), 2), round(pct(qs, .95), 2)]
        out["files_with_hint_of_top30"] = sum(1 for f in hot if cc.hint_for(store, repo, f))
        # whole hook process, first edit of a file with partners
        f = next((f for f in hot if cc.hint_for(store, repo, f)), hot[0])
        env = dict(os.environ, PYTHONPATH=SRC, CLAUDE_PROJECT_DIR=repo, BATON_WORKSPACE=store.workspace)
        payload = lambda sid: {"session_id": sid, "cwd": repo, "tool_name": "Edit",
                               "tool_input": {"file_path": os.path.join(repo, f)}}
        on, off = [], []
        for i in range(15):  # new session id each time so the once-per-file rule never skips the query
            on += hook_ms(env, payload("lat-on-%s-%d" % (uuid.uuid4().hex[:6], i)), n=1)
            off += hook_ms(dict(env, BATON_COCHANGE="0"), payload("lat-off-%s-%d" % (uuid.uuid4().hex[:6], i)), n=1)
        out["file_edited"] = f
        out["hook_process_ms_cochange_on_p50_p95"] = [round(statistics.median(on)), round(pct(on, .95))]
        out["hook_process_ms_cochange_off_p50_p95"] = [round(statistics.median(off)), round(pct(off, .95))]
        out["added_p50_ms"] = round(statistics.median(on) - statistics.median(off))
    finally:
        store.drop()
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
