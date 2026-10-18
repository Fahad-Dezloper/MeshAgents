# Co-change hint: "files that usually change with this one"

Offline, deterministic benchmark on six real open-source repositories. No model calls. This measures whether
git history predicts which files change together in later commits. It does not measure bug prevention.

## What was built
- `src/baton/core/cochange.py`: reads `git log --name-status -M --no-merges` (newest 800 commits, commits with more
  than 25 files skipped, lockfiles / generated / vendored / changelog / image paths skipped, renames followed).
  Writes `(:Artifact)-[:CO_CHANGED {n, ratio}]->(:Artifact)` in batched UNWIND queries (n = commits touching both,
  ratio = n / commits touching the source file). Incremental by last indexed commit sha, time-boxed to 2 s (the rest
  is picked up next session), guarded by a short lock so two sessions do not count twice, rebuilt if history was rewritten.
- Pre-edit hint (one line, max 3 files, once per session and file, skips files the session already touched and
  files that no longer exist): `Files that usually change with shop/db.py: tests/test_db.py (9 of 11 commits), shop/api.py (7 of 11 commits).`
  Config flag `cochange` (default on, `.baton.json`), env `BATON_COCHANGE=0` turns it off. It never turns a call
  into an `ask`/`deny`; it only adds context. All failures are swallowed.
- `baton together <path>` lists the partners (default view is looser than the hint: n>=2, ratio>=0.3).
- PageRank note (cheap, so included): at most every 6 hours, from the session-start hook, `algo.pageRank('Symbol','CALLS')`
  is summed per file; the top 10% with at least 4 dependent files get `hot=true`. The pre-edit line then adds
  "N other files depend on X". Never runs per hook. Needs the Python code graph; it is NOT part of the benchmark below.
- Code: `evals/cochange/bench.py` (benchmark), `evals/cochange/latency.py` (latency + graph-vs-memory check),
  raw output `evals/cochange/results.json`, all tables `evals/cochange/results.md`.

## Method
Repos (full history, cloned 2026-10-18): pallets/flask, pallets/click, pallets/jinja, psf/requests, encode/httpx,
tiangolo/fastapi. Per repo: newest 1000 non-merge commits, chronological 70/30 split. The index is built from the first
700 with the same functions the hook uses. A case is: one evaluation commit with 2 to 25 files, one of its files taken as
the first edit. Correct = a listed file was changed in the same commit. Per repo 83 to 134 evaluation commits were used
(2716 cases pooled).
- coverage: share of cases where a hint would be shown at all.
- precision@3: of the files listed (at most 3), the share that were really in the commit; averaged over hinted cases.
- hit rate: hinted cases where at least one listed file was really in the commit.
- noise: hinted cases where no listed file was in the commit (1 - hit rate).
- Baselines (always show 3 files): same directory (most-changed first), globally most-changed files.
- Thresholds were swept on the first 700 commits only (index on the first 49% of the window, validate on the next 21%).
  Rule written before looking at the test split: highest coverage with pooled noise <= 30%. Grid: ratio 0.3..0.8, n 2..5.

## Threshold choice
The rule picked ratio>=0.5, n>=2 (validation: coverage 37.6%, noise 29.6%). n=2 and n=3 were indistinguishable on
validation (noise 29.6% vs 29.8%; coverage 37.6% vs 32.8%). I shipped the more conservative **ratio >= 0.5, n >= 3**
(the original prior) because "2 of 3 commits" is thin evidence; the test split happened to agree slightly, but the choice
was made for that reason, not from the test numbers. Both are reported. Stricter settings trade coverage for quality
(validation, ratio>=0.7 n>=3: coverage 15.5%, noise 15.8%).

## Held-out results (last 30%), pooled over 6 repos

| setting | coverage | precision@3 | hit rate | noise |
|---|---|---|---|---|
| baton ratio>=0.5, n>=3 (shipped) | 33.7% | 57.0% | 66.5% | 33.5% |
| baton ratio>=0.5, n>=2 (rule's pick) | 36.5% | 54.8% | 64.9% | 35.1% |
| baton ratio>=0.7, n>=3 (quiet) | 17.2% | 73.1% | 75.8% | 24.2% |
| baton, no threshold, top 3 | 78.1% | 35.1% | 63.7% | 36.3% |
| same directory | 90.2% | 29.8% | 48.2% | 51.8% |
| globally most-changed | 100% | 17.4% | 39.1% | 60.9% |

Fairer comparison, only the 991 cases where the rule's setting (n>=2) shows a hint (baselines always have something to show):
baton precision@3 54.8% / hit 64.9%; same directory 36.2% / 56.0%; most-changed 23.0% / 53.1%.
So on the same cases baton's listed files are right about 1.5x as often as the same-directory guess, and the
hit-rate edge is smaller (about 9 points over same-directory).

## Per repo, shipped setting (0.5, n>=3)

| repo | coverage | precision@3 | hit rate | noise |
|---|---|---|---|---|
| fastapi | 40.4% | 73.8% | 85.2% | 14.8% |
| jinja | 23.4% | 68.3% | 79.8% | 20.2% |
| flask | 40.8% | 62.4% | 72.3% | 27.7% |
| click | 29.5% | 62.2% | 68.1% | 31.9% |
| httpx | 56.5% | 38.0% | 47.9% | 52.1% |
| requests | 5.4% | 38.9% | 38.9% | 61.1% |

## Latency (flask and fastapi, real checkouts, local FalkorDB)
- First index of 800 commits: 0.3 s (flask), 0.16 s (fastapi), inside the 2 s budget. Re-run with no new commits: 12 to 16 ms.
- Graph matches an in-memory recount exactly (3992 and 3418 edges; top-40 files' partner lists identical).
- Hint query plus filesystem check: p50 0.3 ms, p95 0.4 ms. PageRank refresh 2 to 4 ms, cached check 0.2 to 0.5 ms.
- Whole `baton pre-tool` process, 15 runs each with and without the feature: about 140 to 200 ms either way, difference
  within noise (+22 ms and -10 ms at p50). Expect the added cost to be around 1 ms (hint query + the session-touched query).

## Honest caveats
- It predicts which files land in the same commit, not that skipping a partner causes a bug. A "miss" may be a correct
  decision to leave a partner alone; a "hit" may be a commit that was simply big.
- About a third of hints list no file that the commit actually changed. Quality varies a lot by repo: requests (few
  active files, 5% coverage) and httpx (many small commits across files) were poor; fastapi and jinja good.
- Case weighting: files in larger commits contribute more cases. Cold files (new, or never in the 800-commit window) get no hint.
- Thresholds that look best on one split may not transfer; six Python libraries by few maintainers, one 300-commit
  test window each, no confidence intervals. Recent releases and dependency-bump files (CI workflows) count as pairs.
- Showing more partners (no threshold) finds a partner more often over all cases (49.7% vs 22.4% hit over all cases),
  at the price of more wrong lines. The thresholds buy precision and silence, not recall.
- Partner files deleted before the evaluation commit are not filtered in the benchmark (the hook filters them), so the
  benchmark is slightly pessimistic. Renames in the evaluation period are not followed (new name = no history).
- The PageRank note was only checked for mechanism (unit test with a synthetic call graph), not benchmarked.
