# Relay evaluation: does a NEW session start smarter because of baton?

Status: PRE-REGISTERED on 2026-10-18, before any scored trial. This file is not edited after results exist,
except that a "Results" section may be appended at the end. Pilot trials (6, harness check only, prefix
`pilot`) are not part of the analysis.

## Question
Sessions often run one after another in the same checkout (yesterday's session, then today's). Does a new
session do better because baton passed notes from the earlier one, compared with (a) no memory at all and
(b) the best-case manual alternative: a notes file the engineer is told to keep?

## Arms (only the agent class differs; same model `claude-haiku-5-5`, same prompts, same fixture)
| Arm | Agent class | What is different |
|---|---|---|
| baseline | `BatonClashBaseline` | no plugin, no notes |
| plugin | `BatonClashPlugin` | baton hooks-only plugin (the default product) |
| notes | `BatonClashNotes` | no plugin; session 1's prompt gets "before finishing, update HANDOFF.md at the repo root with what you did, what remains and any project rules"; session 2's prompt gets "start by reading HANDOFF.md at the repo root, if it exists" |

Sessions run strictly in order (session 1 finishes before session 2 starts) in one fresh container per trial,
on the same checkout. FalkorDB runs inside the container and lives across the two sessions (plugin arm).

## Tasks (evals/relay/tasks.json; deterministic checker evals/relay/check.py, validated in tests/test_relay_checkers.py)
In every task the key fact is stated ONLY in session 1's prompt and cannot be found in the code or guessed
from session 2's prompt.
| Task | Session 1 | Session 2 | What the checker demands of session 2 |
|---|---|---|---|
| R1 continue unfinished work | 6-step spec for an invoice feature; implement only steps 1-3 and stop | "Continue the previous engineer's work on the invoice numbering feature and finish it." | all six steps work (steps 4-6 exist only in session 1's prompt) |
| R2 constraint stated once | small task plus an aside: read-only deploy target, never sqlite, only write under shop/data/ | "Make orders survive process restarts." | orders persist across new processes, no sqlite, files written only under shop/data/ |
| R3 convention stated once | add `parse_sku`; new public functions must raise ShopError, never ValueError, with type hints | add `apply_coupon` | works, raises ShopError (not ValueError) on bad input, fully type-hinted |
| R4 failed approach | small task plus: `shop.batch` deadlocks under load, use the single-item path | bulk import feature | works and never imports or calls `shop.batch` |
| R5 negative control | add `slugify` | add `Order.item_count` (unrelated) | works, no regression |

Honest caveat: R1-R4 are built to need memory. They measure whether baton carries a stated fact across
sessions, not how often real work needs that. R5 measures the price of baton when memory is irrelevant.

## Hypotheses
- H1 (memory helps): on R1-R4 pooled, the session-2 pass rate of plugin is higher than baseline.
- H2 (vs manual notes): plugin's session-2 pass rate is not lower than notes, and plugin needs no manual step.
  Two-sided; we do not assume the direction.
- H3 (no price when irrelevant): on R5, plugin costs no more than 20% above baseline per trial and passes at
  least as often.
- H4 (cost per success): on R1-R4 pooled, plugin's cost per successful trial is not higher than baseline's.

## Metrics
Primary: session-2 checker pass (`relay_pass` in the Harbor reward; pass means every session-2 check holds).
Secondary (per trial, and per session where recorded): turns (session 2 and total), output tokens,
cache-read tokens, estimated cost (list-price estimate; the subscription is not billed per token),
wall time per session, cost per successful trial. Sanity (not a hypothesis): session-1 pass, hook errors,
whether session 2 was shown the earlier notes (hook log, plugin arm).

## Planned trials
10 per arm per task = 5 tasks x 3 arms x 10 = 150 trials (300 sessions), model `claude-haiku-5-5`,
subscription auth. Run as 15 jobs (`-k 10`) with `BATON_EVAL_CONCURRENCY=4` (4 trials at a time; each trial
runs its two sessions in sequence, so at most 4 live sessions). Jobs are ordered task by task with the three
arms adjacent, so time-of-day drift hits the arms equally. Command:
`BATON_EVAL_SUITE=relay BATON_EVAL_PREFIX=relay1 BATON_EVAL_CONCURRENCY=4 evals/harbor/run_eval.sh 10`.
Expected duration about 3 hours. If rate limits appear, lower concurrency and re-run; finished jobs are skipped.

## Statistics plan (fixed in advance; analysis script evals/relay/analyze.py)
- Pass rates: Fisher exact, two-sided, per task and pooled (R1-R4 pooled for H1/H2; R5 alone for H3).
  Confirmatory test: plugin vs baseline pooled over R1-R4 (alpha 0.05). Other pairs (plugin vs notes, notes vs
  baseline, each task alone) are secondary and reported with raw p; with 10 trials per cell, a single task
  can only show large effects.
- Cost per trial: difference of means with a permutation test (20,000 shuffles); the pooled test shuffles
  arm labels within task. Paired by attempt number is not meaningful (trials are independent), so the test
  is unpaired.
- Cost per successful trial: total cost / passes, with a bootstrap 95% interval (10,000 resamples of trials
  within arm). Reported per task and pooled; when an arm has no passes the value is reported as undefined.
- Every result is reported, including nulls. No stopping rule: the trial count is fixed, no peeking.

## Exclusions and sensitivity
- A trial counts as invalid only if infrastructure failed (no verifier reward, checker_error, container or
  auth failure, session 1 missing its output). Invalid trials are re-run once; the number is reported.
- Trials where session 1 itself failed its own check are kept in the primary analysis (the arm that makes
  session 1 worse is penalised honestly). A sensitivity analysis restricted to trials with session-1 pass is
  also reported.
- The task texts, checkers and prompt suffixes are frozen at the first scored trial. Pilot trials were
  allowed to reveal harness bugs; any harness fix after the pilot is listed in the Results section.

## What counts as success and as failure
- Success (memory works): H1 holds, plugin minus baseline pooled pass rate at least +30 points with p < 0.05,
  AND H3 holds (R5 cost ratio plugin/baseline at most 1.2, pass rate not lower), AND H4 holds.
- Strong success: additionally plugin's pass rate is higher than notes (p < 0.05), or equal within 15 points
  with a lower cost per success (the notes arm is the best case because it is explicitly instructed).
- Partial success: plugin beats baseline but is clearly below notes (more than 15 points), or the benefit
  shows only on some tasks; this will be reported as "baton helps but a notes file does it better".
- Failure: plugin minus baseline under +10 points or not significant, or the R5 cost ratio above 1.3, or
  hook errors in more than 5% of plugin trials. A failure will be reported as a failure.

## Known limits (stated before seeing data)
One model (cheap), one small fixture, tasks written by the author and designed to need memory, 10 trials per
cell, list-price cost estimates, and a notes arm that is told exactly what to do (an upper bound for a
manual habit). Baseline may pass by luck (guessing a convention); that is why R5 and the checkers' negative
variants exist.
