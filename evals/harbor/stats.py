#!/usr/bin/env python3
"""Honest statistics for evaluation arms: pass rate with Wilson interval, exact tests, cost per success.

Usage:
  python3 evals/harbor/stats.py --arm baseline "<job glob>" ... --arm plugin "<job glob>" ... [--ref baseline]
Each --arm takes one or more job-directory globs (Harbor jobs). Trials are read from verifier/reward.json and
result.json. Pass = reward clash_free == 1.0 (clash suite) or reward 'pass' == 1.0 (relay suite, if present).

Reports per arm: n, passes, Wilson 95% interval, mean output/cache tokens, turns, estimated cost,
cost per successful trial with a bootstrap 95% interval; and versus the reference arm: Fisher exact p,
risk difference with a bootstrap interval, and a permutation p for cost per trial.
Estimated costs are list-price numbers; a subscription is not billed per token.
"""
import argparse
import glob
import json
import math
import os
import random
import statistics as st
from math import comb


def load(p):
    try:
        with open(p) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def trials(globs):
    out = []
    for g in globs:
        for job in sorted(glob.glob(g)):
            for t in glob.glob(os.path.join(job, "*__*")):
                r = load(os.path.join(t, "result.json"))
                rw = load(os.path.join(t, "verifier", "reward.json"))
                if not r or not rw or not r.get("agent_result"):
                    continue
                ar = r["agent_result"]
                ok = rw.get("clash_free", rw.get("pass", 0)) == 1.0
                ws = (ar.get("metadata") or {}).get("workers") or []
                out.append({"ok": ok, "out": ar.get("n_output_tokens") or 0, "cache": ar.get("n_cache_tokens") or 0,
                            "cost": ar.get("cost_usd") or 0.0, "turns": sum(w.get("turns") or 0 for w in ws),
                            "level": (ar.get("metadata") or {}).get("level") or "?"})
    return out


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - m) / d, (c + m) / d)


def fisher(a, n1, b, n2):
    N, K = n1 + n2, a + b
    if N == 0:
        return 1.0
    p0 = comb(n1, a) * comb(n2, b) / comb(N, K)
    return min(1.0, sum(comb(n1, x) * comb(n2, K - x) / comb(N, K)
                        for x in range(max(0, K - n2), min(n1, K) + 1)
                        if comb(n1, x) * comb(n2, K - x) / comb(N, K) <= p0 + 1e-12))


def boot(fn, xs, n=4000, seed=7):
    rnd = random.Random(seed)
    vals = []
    for _ in range(n):
        s = [xs[rnd.randrange(len(xs))] for _ in xs]
        try:
            vals.append(fn(s))
        except ZeroDivisionError:
            pass
    vals.sort()
    return (vals[int(0.025 * len(vals))], vals[int(0.975 * len(vals))]) if vals else (float("nan"),) * 2


def cost_per_success(ts):
    ok = sum(t["ok"] for t in ts)
    return sum(t["cost"] for t in ts) / ok


def perm_p(a, b, n=10000, seed=3):
    rnd = random.Random(seed)
    obs = abs(st.mean(a) - st.mean(b))
    pool = a + b
    hit = 0
    for _ in range(n):
        rnd.shuffle(pool)
        if abs(st.mean(pool[:len(a)]) - st.mean(pool[len(a):])) >= obs - 1e-15:
            hit += 1
    return hit / n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", nargs="+", action="append", metavar="NAME GLOB", required=True)
    ap.add_argument("--ref", default=None)
    a = ap.parse_args()
    arms = {x[0]: trials(x[1:]) for x in a.arm}
    ref = a.ref or a.arm[0][0]
    print("| Arm | n | Passed | Pass rate (95% CI) | Output tok | Cache-read tok | Turns | Est. cost | Cost per success (95% CI) |")
    print("|---|---|---|---|---|---|---|---|---|")
    for name, ts in arms.items():
        if not ts:
            print("| %s | 0 | - | - | - | - | - | - | - |" % name)
            continue
        k = sum(t["ok"] for t in ts)
        lo, hi = wilson(k, len(ts))
        if k:
            cps = cost_per_success(ts)
            clo, chi = boot(cost_per_success, ts)
            cs = "$%.4f ($%.4f-$%.4f)" % (cps, clo, chi)
        else:
            cs = "n/a (no successes)"
        print("| %s | %d | %d | %.0f%% (%.0f-%.0f%%) | %.0f | %.3g | %.1f | $%.4f | %s |" % (
            name, len(ts), k, 100 * k / len(ts), 100 * lo, 100 * hi, st.mean(t["out"] for t in ts),
            st.mean(t["cache"] for t in ts), st.mean(t["turns"] for t in ts), st.mean(t["cost"] for t in ts), cs))
    print()
    base = arms.get(ref) or []
    for name, ts in arms.items():
        if name == ref or not ts or not base:
            continue
        k1, n1 = sum(t["ok"] for t in ts), len(ts)
        k0, n0 = sum(t["ok"] for t in base), len(base)
        diff = k1 / n1 - k0 / n0
        pooled = [(1, t["ok"]) for t in ts] + [(0, t["ok"]) for t in base]

        def rd(sample):
            x = [o for g, o in sample if g == 1]
            y = [o for g, o in sample if g == 0]
            return sum(x) / len(x) - sum(y) / len(y)
        dlo, dhi = boot(rd, pooled)
        print("%s vs %s: pass-rate difference %+.1f points (95%% CI %+.1f to %+.1f), Fisher exact p = %.3f; "
              "cost per trial permutation p = %.3f" % (
                  name, ref, 100 * diff, 100 * dlo, 100 * dhi, fisher(k1, n1, k0, n0),
                  perm_p([t["cost"] for t in ts], [t["cost"] for t in base])))


if __name__ == "__main__":
    main()
