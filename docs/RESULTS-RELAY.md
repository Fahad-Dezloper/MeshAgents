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


# Results (run 2026-10-18, 14:07-14:37 IST, prefix relay1)

150 trials (5 tasks x 3 arms x 10), 4 trials at a time, model claude-haiku-5-5, 0 failed or invalid trials,
0 re-runs, 0 plugin hook errors. Plugin = the shipped hooks-only baton with full-request handoffs and rules
captured from conversation. Notes = best case: both sessions are told to write and read a HANDOFF.md.
Costs are list-price estimates (a subscription is not billed per token). Statistics: `evals/relay/analyze.py`
(per task) and `evals/harbor/stats.py` (pooled, with intervals).

## Did the second session finish the job? (session-2 pass, out of 10)

| Task | No memory | Notes file | Baton |
|---|---|---|---|
| R1 continue unfinished work | 0 | 9 | **10** |
| R2 a rule stated once (no sqlite) | 0 | 8 | **8** |
| R3 a convention stated once | 8 | 10 | **10** |
| R4 a failed approach to avoid | 10 | 10 | 10 |
| R5 control (nothing to remember) | 10 | 10 | 10 |

R4 did not discriminate: nobody took the trap, even without memory. It carries no evidence either way.

## Pooled over R1-R4 (the tasks that need a remembered fact), 40 trials per arm

| Arm | Passed | Pass rate (95% CI) | Cost per trial | Cost per success (95% CI) |
|---|---|---|---|---|
| No memory | 18/40 | 45% (31-60%) | $0.0053 | $0.0117 ($0.0086-$0.0177) |
| Notes file | 37/40 | 92% (80-97%) | $0.0063 | $0.0068 ($0.0063-$0.0076) |
| **Baton** | **38/40** | **95% (83-99%)** | **$0.0055** | **$0.0058 ($0.0054-$0.0064)** |

- Baton vs no memory: +50 points (95% CI +33 to +67), Fisher exact p < 0.001; cost per success cut roughly in half.
- Baton vs notes file: +2.5 points (95% CI -8 to +13), p = 1.0: the same pass rate. Baton costs about 12% less per
  trial than the notes file (p < 0.001) because it injects a short, relevant briefing instead of making every
  session write and read a file (the notes arm used 21% more turns than baton).
- Price when memory is irrelevant (R5): baton $0.0048 vs $0.0045 per trial (+7%, p = 0.006), same pass rate.
  Across all 50 trials baton costs +6% per trial over no memory, and used fewer turns (10.0 vs 10.6).

## Against the pre-registered criteria
- H1 (memory helps): met. +50 points pooled on R1-R4, p < 0.001.
- H2 (not worse than manual notes): met. 38/40 vs 37/40.
- H3 (no price when irrelevant, ratio at most 1.2 and pass not lower): met. Ratio 1.07, 10/10 vs 10/10.
- H4 (cost per success not higher): met. $0.0058 vs $0.0117.
- By the criteria written before the run this is a **strong success**: pass rate equal to notes within 15 points
  at a lower cost per success.

## What this does NOT show (read this before quoting the numbers)
- R1 and R2 are built so that a session without notes cannot know the key fact, so 0/10 is by construction.
  The honest reading is: when the needed fact lives only in an earlier conversation, baton carries it across
  as well as a perfectly maintained notes file does, with nothing to maintain.
- Where the fact is visible in the code (R3), no memory already passes 8 of 10. For real work the share of
  tasks that need a remembered fact is unknown; this run does not measure it.
- One cheap model, one small fixture, tasks written by the author, 10 trials per cell, and a notes arm that is
  explicitly told what to write (a notes file that people forget to update would do worse).
- The R1 pilot found that the first version cut the request off at 200 characters; this was fixed before the
  full run (full request now kept). The pilot trials are not part of these numbers.



# R6 addendum, written before running R6

Status: PRE-REGISTERED before any R6 trial. The R1-R5 results above are not changed. R6 tests whether memory
still works when there is a lot of it (a needle in a pile of rules). Nothing about R1-R5, the arms, the model
or the notes-arm prompt suffixes changes.

## Task (evals/relay/tasks.json, checker `check_R6` in evals/relay/check.py, validated in tests/test_relay_checkers.py)
- Session 1 ticket: add `initials(name)` in shop/utils.py (small, unrelated). Its prompt also pastes a block of
  20 one-sentence team conventions (emails, logging, CSV export, caching, naming, CLI flags, retries, pagination,
  webhooks and so on). 19 are about other modules and irrelevant to session 2. Exactly one, number 10 of 20
  (the middle), is decisive: "Refund amounts are always capped at the original order total and rounded
  half-even to whole cents; never negative."
- Session 2 ticket: add `shop.api.refund_order(order_id, amount_cents)` (amount may be fractional; returns
  `{'id', 'refunded_cents'}` as an int, or None for an unknown order). The ticket does not mention the cap, the
  rounding or the sign, and the rule cannot be inferred from the code.
- Checker (session 2): basic behaviour; cap (5000 and 1100.5 on an order of 1100 give 1100); half-even rounding
  (0.5, 1.5, 2.5, 1050.5, 1051.5, 1050.4, 1050.6 give 0, 2, 2, 1050, 1052, 1050, 1051); never negative (a
  negative amount gives 0 or raises, never a negative refund); project tests pass. Session 2 passes only if all
  hold. Python's built-in `round` is half-even, so a model that happens to use it passes the rounding check by
  habit; this is a known leak and is why the baseline is only a control.
- Before any trial the checker was validated: reference solution passes, pristine fails, and variants that break
  exactly one part of the rule fail exactly that check (no cap, half-up, truncation, negative passthrough,
  everything naive), while rejecting a negative amount with an error is accepted.
- Notes arm: unchanged generic suffixes (session 1 asked to record what it did and "any project rules" in
  HANDOFF.md, session 2 asked to start by reading HANDOFF.md). Whether session 1 chooses to record the one rule
  out of 20 is part of what is measured.

## Hypotheses
- H6a: baton's session-2 pass rate is not below the notes arm's (10 vs 10 trials, margin: at most 15 points lower).
- H6b: baton's cost per trial is below the notes arm's.
- Control: the baseline arm should fail by construction, apart from guessing by habit (see the `round` leak).
  It is reported as a control only and carries no hypothesis.

## Metrics
Primary: session-2 pass (`relay_pass`). Secondary: cost per trial and per success (list-price estimate), turns,
output tokens, session-1 pass, hook errors, and for the plugin arm whether session 2 was shown the refund rule.
Per-check failures are reported (cap, rounding, sign) so a partial miss is visible.

## Trials and statistics
10 trials per arm (30 trials, 60 sessions), model `claude-haiku-5-5`, run as one job per arm
(`BATON_EVAL_SUITE=relay ... run_eval.sh 10 "R6"`). Pass rates: Fisher exact, two-sided; cost: permutation test;
cost per success with bootstrap interval, all via evals/relay/analyze.py. With 10 per arm only large differences
can be shown; this is stated up front. No stopping rule, no peeking. Invalid (infrastructure) trials are
re-run once and counted in the report.

## Success and failure
- Success: baton passes at least as often as notes (not more than 15 points lower) AND costs less per trial
  than notes AND the baseline control passes clearly less than baton.
- Partial: baton matches notes on pass rate but is not cheaper, or beats baseline only weakly.
- Failure: baton passes more than 15 points below notes (a long pasted list dilutes what baton carries), or the
  baseline control passes as often as baton (the task does not need memory; it then carries no evidence).
  Any of these is reported as it is.

## Known limits
One more author-written task, one model, 10 trials per arm, the rule is a single clean sentence, and the
pasted list is only 20 lines. This is a small step toward "memory under volume", not a test of large memories.


# Re-check on the final code, and the R6 result (run 2026-10-18, 15:31-15:49 IST, prefix relay2)

After the first run, rules were made smarter (ranked by relevance to the request; a rule that names a file
also appears when that file is edited; up to 15 rules captured per prompt). That change was motivated by the
two R2 failures in the first run, so this re-run is a post-hoc improvement, reported next to the original.
Only the baton arm was re-run on R1-R5 (the other arms do not use baton code); R6 was run for all three arms.

| Task (10 runs each) | Baton, first run | Baton, final code |
|---|---|---|
| R1 continue unfinished work | 10 | 10 |
| R2 a rule stated once | 8 | **10** |
| R3 a convention stated once | 10 | 10 |
| R4 a failed approach (no signal) | 10 | 10 |
| R5 control, nothing to remember | 10 | 10 |
| R1-R4 pooled | 38/40 (95%, CI 83-99%) | **40/40 (100%, CI 91-100%)** |

Cost per successful run, R1-R4: $0.0056 on the final code ($0.0055-$0.0058), $0.0058 on the first run.

## R6: one useful rule hidden among 20 (pre-registered in the R6 addendum), 10 runs each
| Arm | Passed | Cost per success |
|---|---|---|
| No memory (control; cannot know the rule) | 0/10 | n/a |
| Notes file | 9/10 (90%, CI 60-98%) | $0.0070 ($0.0059-$0.0091) |
| **Baton** | **10/10 (100%, CI 72-100%)** | **$0.0058 ($0.0056-$0.0060)** |

Baton found the one relevant rule among 20 and cost about 17% less per success than the notes file. With 10
runs per cell the difference between baton and the notes file in pass rate is not significant (10/10 vs 9/10).
The baseline passes the rounding check by habit in places (Python's round is half-even), so it is a control only.

