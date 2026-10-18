#!/usr/bin/env python3
"""Statistics for the relay evaluation, as pre-registered in docs/RESULTS-RELAY.md.

Usage: python3 evals/relay/analyze.py "<job dir glob>" ["<glob>" ...]     (e.g. "evals/harbor/jobs/relay1-*")
       python3 evals/relay/analyze.py --selftest

Per task and pooled, for each pair of arms (plugin vs baseline, plugin vs notes, notes vs baseline):
  - session-2 pass rate with Fisher exact two-sided p (pooled: Mantel-Haenszel style is NOT used; pooled
    Fisher on summed counts is reported, plus the per-task table, because tasks have equal trial counts)
  - mean estimated cost per trial, difference, permutation p (pooled: permutation within task)
  - cost per successful trial with a bootstrap 95% interval (resampling trials within an arm)
Also session-level means: turns, output tokens, cache-read tokens, wall seconds for S1 and S2.
Costs are list-price estimates; the subscription is not billed per token.
"""
import glob
import json
import math
import os
import random
import re
import statistics
import sys

ARMS = ("baseline", "plugin", "notes")
PAIRS = (("plugin", "baseline"), ("plugin", "notes"), ("notes", "baseline"))
SEED = 20261018
N_PERM = 20000
N_BOOT = 10000


# ---------------------------------------------------------------- statistics (stdlib only)
def _logchoose(n, k):
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)


def fisher_exact(a, b, c, d):
    """Two-sided Fisher exact p for [[a, b], [c, d]] (a,b = successes/failures in group 1)."""
    n1, n2, k = a + b, c + d, a + c
    n = n1 + n2
    if n == 0:
        return 1.0

    def p(x):
        return math.exp(_logchoose(k, x) + _logchoose(n - k, n1 - x) - _logchoose(n, n1))

    lo, hi = max(0, k - n2), min(k, n1)
    p_obs = p(a)
    return min(1.0, sum(p(x) for x in range(lo, hi + 1) if p(x) <= p_obs * (1 + 1e-9)))


def perm_test_mean_diff(x, y, strata_x=None, strata_y=None, rng=None, n=N_PERM):
    """Two-sided permutation p for mean(x) - mean(y); labels are shuffled within strata if given."""
    rng = rng or random.Random(SEED)
    if not x or not y:
        return float("nan")
    sx = strata_x or [0] * len(x)
    sy = strata_y or [0] * len(y)
    groups = {}
    for v, s in zip(x, sx):
        groups.setdefault(s, [[], []])[0].append(v)
    for v, s in zip(y, sy):
        groups.setdefault(s, [[], []])[1].append(v)
    obs = statistics.mean(x) - statistics.mean(y)
    hits = 0
    for _ in range(n):
        px, py = [], []
        for gx, gy in groups.values():
            pool = gx + gy
            rng.shuffle(pool)
            px += pool[:len(gx)]
            py += pool[len(gx):]
        d = (statistics.mean(px) - statistics.mean(py)) if px and py else 0.0
        if abs(d) >= abs(obs) - 1e-12:
            hits += 1
    return (hits + 1) / (n + 1)


def boot_cost_per_success(rows, rng=None, n=N_BOOT):
    """(point, lo, hi): total cost / number of passes, bootstrap over trials. None when no passes."""
    rng = rng or random.Random(SEED)
    if not rows:
        return None
    def cps(rs):
        s = sum(1 for r in rs if r["pass"])
        return (sum(r["cost"] for r in rs) / s) if s else None
    point = cps(rows)
    vals = []
    for _ in range(n):
        v = cps([rows[rng.randrange(len(rows))] for _ in rows])
        if v is not None:
            vals.append(v)
    if point is None or len(vals) < n * 0.5:
        return (point, None, None)
    vals.sort()
    return (point, vals[int(0.025 * len(vals))], vals[min(len(vals) - 1, int(0.975 * len(vals)))])


# ---------------------------------------------------------------- loading
def _load(p):
    try:
        with open(p) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def arm_of(job):
    cfg = _load(os.path.join(job, "config.json"))
    text = json.dumps(cfg) if cfg else os.path.basename(job)
    if "BatonClashNotes" in text or "notes" in os.path.basename(job):
        return "notes"
    if "BatonClashPlugin" in text or "plugin" in os.path.basename(job):
        return "plugin"
    return "baseline"


def load_trials(globs):
    rows = []
    for g in globs:
        for job in sorted(glob.glob(g)):
            if not os.path.isdir(job):
                continue
            arm = arm_of(job)
            for t in sorted(glob.glob(os.path.join(job, "*__*"))):
                m = re.search(r"relay-(r\d+)", os.path.basename(t))
                reward = _load(os.path.join(t, "verifier", "reward.json"))
                res = _load(os.path.join(t, "result.json")) or {}
                ar = res.get("agent_result") or {}
                ws = (ar.get("metadata") or {}).get("workers") or []
                if not m or reward is None:
                    continue
                s2 = ws[1] if len(ws) > 1 else {}
                rows.append({
                    "task": m.group(1).upper(), "arm": arm,
                    "pass": reward.get("relay_pass") == 1.0, "s1_pass": reward.get("s1_pass") == 1.0,
                    "cost": float(ar.get("cost_usd") or 0.0),
                    "turns": sum(w.get("turns") or 0 for w in ws), "s2_turns": s2.get("turns") or 0,
                    "output": ar.get("n_output_tokens") or 0, "cache": ar.get("n_cache_tokens") or 0,
                    "ws": ws,
                })
    return rows


# ---------------------------------------------------------------- report
def pm(rows, key):
    return statistics.mean(r[key] for r in rows) if rows else float("nan")


def fmt_p(p):
    return "n/a" if p != p else ("%.3f" % p)


def report(rows):
    out = []
    tasks = sorted({r["task"] for r in rows}) + ["ALL"]
    out.append("## Session-2 pass rate\n")
    out.append("| Task | " + " | ".join(ARMS) + " | " + " | ".join("p %s vs %s" % pr for pr in PAIRS) + " |")
    out.append("|---|" + "---|" * (len(ARMS) + len(PAIRS)))
    for t in tasks:
        sel = [r for r in rows if t == "ALL" or r["task"] == t]
        cnt = {a: (sum(1 for r in sel if r["arm"] == a and r["pass"]), sum(1 for r in sel if r["arm"] == a)) for a in ARMS}
        cells = ["%d/%d" % cnt[a] if cnt[a][1] else "-" for a in ARMS]
        ps = []
        for x, y in PAIRS:
            (px, nx), (py, ny) = cnt[x], cnt[y]
            ps.append(fmt_p(fisher_exact(px, nx - px, py, ny - py)) if nx and ny else "n/a")
        out.append("| %s | %s | %s |" % (t, " | ".join(cells), " | ".join(ps)))

    out.append("\n## Cost, turns, tokens, time (means per trial; cost is a list-price estimate)\n")
    out.append("| Task | Arm | n | Cost $ | Turns (all) | Turns S2 | Output tok | Cache-read tok | S1 wall s | S2 wall s |")
    out.append("|---|---|---|---|---|---|---|---|---|---|")
    for t in tasks:
        for a in ARMS:
            sel = [r for r in rows if r["arm"] == a and (t == "ALL" or r["task"] == t)]
            if not sel:
                continue
            w = lambda i: statistics.mean(((r["ws"][i].get("wall_s") or 0) if len(r["ws"]) > i else 0) for r in sel)
            out.append("| %s | %s | %d | %.4f | %.1f | %.1f | %.0f | %.0f | %.0f | %.0f |" % (
                t, a, len(sel), pm(sel, "cost"), pm(sel, "turns"), pm(sel, "s2_turns"), pm(sel, "output"), pm(sel, "cache"), w(0), w(1)))

    out.append("\n## Cost difference per trial (permutation test; pooled test shuffles within task)\n")
    out.append("| Task | Pair | Mean cost A | Mean cost B | A - B | p |")
    out.append("|---|---|---|---|---|---|")
    for t in tasks:
        for x, y in PAIRS:
            sx = [r for r in rows if r["arm"] == x and (t == "ALL" or r["task"] == t)]
            sy = [r for r in rows if r["arm"] == y and (t == "ALL" or r["task"] == t)]
            if not sx or not sy:
                continue
            p = perm_test_mean_diff([r["cost"] for r in sx], [r["cost"] for r in sy],
                                    [r["task"] for r in sx], [r["task"] for r in sy])
            out.append("| %s | %s vs %s | %.4f | %.4f | %+.4f | %s |" % (t, x, y, pm(sx, "cost"), pm(sy, "cost"), pm(sx, "cost") - pm(sy, "cost"), fmt_p(p)))

    out.append("\n## Cost per successful trial (total cost / passes, bootstrap 95% interval)\n")
    out.append("| Task | Arm | Passes | Cost per success $ | 95% CI |")
    out.append("|---|---|---|---|---|")
    for t in tasks:
        for a in ARMS:
            sel = [r for r in rows if r["arm"] == a and (t == "ALL" or r["task"] == t)]
            if not sel:
                continue
            res = boot_cost_per_success(sel)
            passes = sum(1 for r in sel if r["pass"])
            if res is None or res[0] is None:
                out.append("| %s | %s | %d/%d | no passes | - |" % (t, a, passes, len(sel)))
            else:
                ci = "%.4f - %.4f" % (res[1], res[2]) if res[1] is not None else "too few passes"
                out.append("| %s | %s | %d/%d | %.4f | %s |" % (t, a, passes, len(sel), res[0], ci))
    s1 = {a: (sum(1 for r in rows if r["arm"] == a and r["s1_pass"]), sum(1 for r in rows if r["arm"] == a)) for a in ARMS}
    out.append("\nSession-1 pass (sanity, not a metric): " + ", ".join("%s %d/%d" % (a, *s1[a]) for a in ARMS if s1[a][1]))
    return "\n".join(out)


def selftest():
    # Fisher: classic tea-tasting table [[3,1],[1,3]] -> 0.4857; [[10,0],[0,10]] tiny
    assert abs(fisher_exact(3, 1, 1, 3) - 0.4857) < 1e-3, fisher_exact(3, 1, 1, 3)
    assert fisher_exact(10, 0, 0, 10) < 1e-4
    assert abs(fisher_exact(5, 5, 5, 5) - 1.0) < 1e-6
    rng = random.Random(1)
    x = [1.0 + rng.random() * 0.1 for _ in range(30)]
    y = [2.0 + rng.random() * 0.1 for _ in range(30)]
    assert perm_test_mean_diff(x, y, n=2000) < 0.01
    assert perm_test_mean_diff(x, x[::-1], n=2000) > 0.9
    rows = [{"pass": i % 2 == 0, "cost": 1.0} for i in range(20)]
    pt, lo, hi = boot_cost_per_success(rows, n=2000)
    assert abs(pt - 2.0) < 1e-9 and lo <= pt <= hi
    fake = []
    for arm, rate in (("baseline", 0.1), ("plugin", 0.8), ("notes", 0.6)):
        for i in range(10):
            fake.append({"task": "R1", "arm": arm, "pass": rng.random() < rate, "s1_pass": True, "cost": 0.1 + rng.random() * 0.05,
                         "turns": 10, "s2_turns": 5, "output": 1000, "cache": 5000, "ws": [{"wall_s": 30}, {"wall_s": 40}]})
    txt = report(fake)
    assert "Session-2 pass rate" in txt and "Cost per successful trial" in txt
    print("selftest ok")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    elif len(sys.argv) < 2:
        print(__doc__)
    else:
        data = load_trials(sys.argv[1:])
        if not data:
            print("no scored relay trials found")
        else:
            print(report(data))
