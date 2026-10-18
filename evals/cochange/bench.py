"""Offline benchmark for the co-change hint. Deterministic: git history in, numbers out, no model calls.

Usage: python -B evals/cochange/bench.py REPO_DIR [REPO_DIR ...] [--window 1000] [--out evals/cochange/results.json]

For each repo: take the newest WINDOW non-merge commits, chronological split 70/30. The index is built from
the first 70% with the exact functions the hook uses (baton.core.cochange). Thresholds are chosen on the first
70% only (index on its first 70%, validate on its last 30%), then applied once to the held-out last 30%.

A "case" is (evaluation commit with 2..25 files after filtering, one of its files taken as the first edit).
A hint is shown when at least one partner passes the thresholds; it lists at most 3 partners. Correct = the
listed file was changed in the same commit.
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter
from typing import Dict, List, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src"))
from baton.core import cochange as cc  # noqa: E402

RATIOS = (0.3, 0.4, 0.5, 0.6, 0.7, 0.8)
NS = (2, 3, 4, 5)
NOISE_CAP = 0.30


def load_window(repo: str, window: int):
    out = cc._git(repo, ["log", "--no-merges", "--no-ext-diff", "--name-status", "-M", "--format=%x01%H",
                         "-n", str(window), "HEAD", "--"], timeout=300)
    if out is None:
        raise SystemExit("git log failed in %s" % repo)
    parsed = cc.parse_log(out)  # newest first
    parsed.reverse()            # oldest first
    return parsed


def split(parsed_oldest_first, frac: float):
    k = int(len(parsed_oldest_first) * frac)
    a, b = parsed_oldest_first[:k], parsed_oldest_first[k:]
    index_commits = cc.resolve_renames(list(reversed(a)), follow=True)   # names as of the end of the index window
    eval_commits = cc.resolve_renames(list(reversed(b)), follow=False)   # names as of each commit
    return index_commits, eval_commits


class Index:
    def __init__(self, commits):
        self.files, self.pairs = cc.aggregate(commits)
        self.edges = cc.directed_edges(self.files, self.pairs)
        self.by_dir: Dict[str, List[str]] = {}
        for f in sorted(self.files, key=lambda x: (-self.files[x], x)):
            self.by_dir.setdefault(os.path.dirname(f), []).append(f)
        self.top = sorted(self.files, key=lambda x: (-self.files[x], x))[:4]


def method_baton(ix: Index, f: str, min_n: int, min_ratio: float):
    return [p for p, _n, _r in cc.rank_partners(ix.edges.get(f, []), min_n, min_ratio)]


def method_baton_any(ix: Index, f: str):
    return [p for p, _n, _r in cc.rank_partners(ix.edges.get(f, []), 1, 0.0)]


def method_samedir(ix: Index, f: str):
    return [p for p in ix.by_dir.get(os.path.dirname(f), []) if p != f][:3]


def method_global(ix: Index, f: str):
    return [p for p in ix.top if p != f][:3]


def cases(eval_commits):
    for sha, fs in eval_commits:
        if 2 <= len(fs) <= cc.MAX_FILES_PER_COMMIT:
            for f in fs:
                yield sha, f, set(fs) - {f}


def run(ix: Index, eval_commits, fn):
    """-> list of (shown_count, correct_count) per case."""
    res = []
    for _sha, f, others in cases(eval_commits):
        shown = fn(f)
        res.append((len(shown), len([p for p in shown if p in others])))
    return res


def summarize(res, subset_mask=None):
    rows = [r for i, r in enumerate(res) if subset_mask is None or subset_mask[i]]
    total = len(rows)
    hinted = [r for r in rows if r[0] > 0]
    h = len(hinted)
    hits = sum(1 for r in hinted if r[1] > 0)
    prec = sum(r[1] / r[0] for r in hinted)
    return {"cases": total, "hinted": h, "hits": hits, "prec_sum": prec,
            "coverage": h / total if total else 0.0,
            "precision_at3": prec / h if h else 0.0,
            "hit_rate": hits / h if h else 0.0,
            "noise": 1 - hits / h if h else 0.0,
            "hit_rate_all_cases": hits / total if total else 0.0}


def pool(summaries):
    t = sum(s["cases"] for s in summaries)
    h = sum(s["hinted"] for s in summaries)
    hits = sum(s["hits"] for s in summaries)
    ps = sum(s["prec_sum"] for s in summaries)
    return {"cases": t, "hinted": h, "hits": hits, "prec_sum": ps, "coverage": h / t if t else 0.0,
            "precision_at3": ps / h if h else 0.0, "hit_rate": hits / h if h else 0.0,
            "noise": 1 - hits / h if h else 0.0, "hit_rate_all_cases": hits / t if t else 0.0}


def main(argv):
    window, out = 1000, os.path.join(os.path.dirname(os.path.abspath(__file__)), "results.json")
    repos = []
    i = 0
    while i < len(argv):
        if argv[i] == "--window":
            window = int(argv[i + 1]); i += 2
        elif argv[i] == "--out":
            out = argv[i + 1]; i += 2
        else:
            repos.append(argv[i]); i += 1
    data = {}
    for repo in repos:
        name = os.path.basename(repo.rstrip("/"))
        parsed = load_window(repo, window)
        train_parsed = parsed[:int(len(parsed) * 0.7)]
        idx_c, val_c = split(train_parsed, 0.7)
        vix = Index(idx_c)
        grid = {}
        for r in RATIOS:
            for n in NS:
                grid["%s|%d" % (r, n)] = summarize(run(vix, val_c, lambda f: method_baton(vix, f, n, r)))
        data[name] = {"commits": len(parsed), "val_grid": grid}
    # choose thresholds on validation, pooled
    best, best_key = None, None
    pooled_grid = {}
    for key in next(iter(data.values()))["val_grid"]:
        pooled_grid[key] = pool([d["val_grid"][key] for d in data.values()])
    ok = [(k, v) for k, v in pooled_grid.items() if v["noise"] <= NOISE_CAP]
    if ok:
        best_key = max(ok, key=lambda kv: (kv[1]["coverage"], kv[1]["precision_at3"], kv[0]))[0]
    else:
        best_key = min(pooled_grid, key=lambda k: pooled_grid[k]["noise"])
    ratio, n = best_key.split("|")
    chosen = (int(n), float(ratio))
    default = (cc.DEFAULT_MIN_N, cc.DEFAULT_MIN_RATIO)
    # held-out test
    test_summ = {}
    for repo in repos:
        name = os.path.basename(repo.rstrip("/"))
        parsed = load_window(repo, window)
        idx_c, ev_c = split(parsed, 0.7)
        ix = Index(idx_c)
        ncases = sum(len(fs) for _s, fs in ev_c if 2 <= len(fs) <= cc.MAX_FILES_PER_COMMIT)
        base = run(ix, ev_c, lambda f: method_baton(ix, f, chosen[0], chosen[1]))
        mask = [r[0] > 0 for r in base]
        entry = {"index_commits": len(idx_c), "eval_commits": len(ev_c),
                 "eval_commits_used": len([1 for _s, fs in ev_c if 2 <= len(fs) <= cc.MAX_FILES_PER_COMMIT]),
                 "index_files": len(ix.files), "index_pairs": len(ix.pairs)}
        methods = {
            "baton_chosen": base,
            "baton_default_0.5_3": run(ix, ev_c, lambda f: method_baton(ix, f, default[0], default[1])),
            "baton_strict_0.7_3": run(ix, ev_c, lambda f: method_baton(ix, f, 3, 0.7)),
            "baton_no_threshold_top3": run(ix, ev_c, lambda f: method_baton_any(ix, f)),
            "same_directory": run(ix, ev_c, lambda f: method_samedir(ix, f)),
            "global_most_changed": run(ix, ev_c, lambda f: method_global(ix, f)),
        }
        entry["all_cases"] = {m: summarize(r) for m, r in methods.items()}
        entry["on_baton_hinted_cases"] = {m: summarize(r, mask) for m, r in methods.items()}
        test_summ[name] = entry
    pooled_all = {m: pool([e["all_cases"][m] for e in test_summ.values()]) for m in test_summ[next(iter(test_summ))]["all_cases"]}
    pooled_cov = {m: pool([e["on_baton_hinted_cases"][m] for e in test_summ.values()]) for m in pooled_all}
    result = {"window": window, "chosen": {"min_n": chosen[0], "min_ratio": chosen[1]}, "noise_cap": NOISE_CAP,
              "validation_pooled": pooled_grid, "validation_per_repo": {k: v["val_grid"] for k, v in data.items()},
              "test": test_summ, "test_pooled_all_cases": pooled_all, "test_pooled_on_baton_hinted_cases": pooled_cov}
    with open(out, "w") as f:
        json.dump(result, f, indent=1, sort_keys=True)
    print("chosen", chosen, "written", out)
    write_tables(result, os.path.splitext(out)[0] + ".md")


def _row(label, v):
    return "| %s | %d | %.1f%% | %.1f%% | %.1f%% | %.1f%% | %.1f%% |" % (
        label, v["cases"], 100 * v["coverage"], 100 * v["precision_at3"], 100 * v["hit_rate"], 100 * v["noise"],
        100 * v["hit_rate_all_cases"])


HEAD = ("| method | cases | coverage | precision@3 | hit rate | noise | hit rate over all cases |\n"
        "|---|---|---|---|---|---|---|")


def write_tables(result, path):
    lines = ["Validation (index = first 49% of window, validated on the next 21%), pooled over repos:", "", HEAD]
    for k, v in result["validation_pooled"].items():
        r, n = k.split("|")
        lines.append(_row("ratio>=%s n>=%s" % (r, n), v))
    lines += ["", "Held-out test, pooled, all cases:", "", HEAD]
    for m, v in result["test_pooled_all_cases"].items():
        lines.append(_row(m, v))
    lines += ["", "Held-out test, pooled, only the cases where the chosen baton setting shows a hint:", "", HEAD]
    for m, v in result["test_pooled_on_baton_hinted_cases"].items():
        lines.append(_row(m, v))
    for name, e in sorted(result["test"].items()):
        lines += ["", "%s (%d index commits, %d evaluation commits used of %d):" % (
            name, e["index_commits"], e["eval_commits_used"], e["eval_commits"]), "", HEAD]
        for m, v in e["all_cases"].items():
            lines.append(_row(m, v))
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main(sys.argv[1:])
