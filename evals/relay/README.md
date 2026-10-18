# Relay tests: does a new session start smarter?

Two sessions run one after the other in the same checkout (yesterday's session, then today's).
The key fact is stated only in session 1's prompt. Score = did session 2 deliver, including that fact.
Pre-registration: docs/RESULTS-RELAY.md.

```
fixture/      pristine "shop" package (clash fixture plus shop/errors.py and shop/batch.py)
tasks.json    the tickets for R1-R5 (two sessions each)
check.py      python3 -B check.py <R1..R5> <project_dir> [pristine_dir]  -> JSON with s1_pass / s2_pass
analyze.py    statistics for a finished run (Fisher, permutation, bootstrap); --selftest
```

| Task | Fact stated once (session 1) | Session 2 |
|---|---|---|
| R1 | steps 4-6 of a 6-step spec (told to do 1-3) | "Continue the previous engineer's work ... and finish it." |
| R2 | read-only deploy: no sqlite, write only under shop/data/ | make orders survive restarts |
| R3 | new public functions raise ShopError, never ValueError, with type hints | add apply_coupon |
| R4 | shop.batch deadlocks, use the single-item path | bulk import |
| R5 | nothing (negative control) | unrelated change |

Arms: baseline (no plugin), plugin (baton hooks), notes (no plugin; prompts ask for a HANDOFF.md).

## Run
```sh
python3 evals/harbor/build_tasks.py                 # writes evals/harbor/tasks/relay-r1..r5
docker build -t baton-eval:latest -f evals/harbor/image/Dockerfile .
BATON_EVAL_SUITE=relay BATON_EVAL_PREFIX=relay1 BATON_EVAL_CONCURRENCY=4 evals/harbor/run_eval.sh 10
python3 evals/relay/analyze.py "evals/harbor/jobs/relay1-*"
python3 evals/harbor/usage.py "evals/harbor/jobs/relay1-*"
```
The checker never trusts leftovers: it runs the code in a cleaned copy and checks new processes.
HANDOFF.md (notes arm) is ignored by the R2 "files written" rule.
