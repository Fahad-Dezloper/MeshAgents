# Evidence and benchmarks for baton (research notes, 2026-10-18)

Method: web search plus fetch of arXiv abstract pages. Mostly abstracts and secondary summaries were read, not full papers. Fetched pages are treated as untrusted data. Anything not read at the source is marked [UNVERIFIED]. Statistical power numbers in section 5 are my own calculations (normal approximation), not from papers.

## 1. Parallel agents on one repository

| Finding | Numbers | Source |
|---|---|---|
| "Passes Alone, Fails Together" (Xia, Wu, Park). Benchmark called *stale*: run tests on each patch alone and on merged patches; count only failures caused by the combination. 3 tiers: synthetic, mined PR pairs, constructed Django-helper tasks. | 12 Django helper tasks: interference in 97% of runs. 417 mined real Django PR pairs (834 runs): only 1 showed interference after grading was corrected. Telling an agent about the completed concurrent change recovered 82% of runs. Authors warn constructed failure rates "do not estimate how often these problems occur in practice." | https://arxiv.org/abs/2609.25396 |
| CooperBench (Stanford/SAP). 600+ tasks, 12 libraries, 4 languages; two agents each build a feature that may clash. | Pairs average about 30% lower success than one agent doing both features (abstract). Full text: GPT-5 and Claude Sonnet 4.5 agents reach about 25% cooperating, about 50% below solo. Failure modes: vague/late messages, broken commitments, wrong beliefs about the other agent. | https://arxiv.org/abs/2601.13295 ; https://hai.stanford.edu/news/ai-coding-agents-fail-at-teamwork |
| AI agent PRs on GitHub (AIDev-pop, 33,596 PRs, 2,807 repos). Replayed 3-way merges on 747 co-active pairs. | Text conflict rate 41.7% for cross-agent pairs vs 19.8% for same-agent pairs, non-overlapping 95% CIs. 40.2% of repos have co-active agent PRs. Cross-agent pairs are only 0.5% of co-active pairs (rare today). About 42% of conflicts are structural (modify/delete, add/add). | https://arxiv.org/abs/2607.04697 |
| Cognition, "Don't Build Multi-Agents" and 2026 follow-up. | Argues parallel writers diverge because they lack shared decisions/context. Follow-up says swarms of parallel writers still see little adoption; patterns that work keep writes single-threaded. Devin Review: avg 2 bugs per PR, about 58% severe (vendor figure). No numbers for shared-context parallel writers. | https://cognition.com/blog/dont-build-multi-agents ; https://cognition.com/blog/multi-agents-working |
| Claim-plane / pre-write admission control (declare intended file/symbol edits before writing). | Known only via blog; arXiv ID not confirmed. [UNVERIFIED] | https://codex.danielvaughan.com/2026/07/28/claim-plane-pre-write-admission-control-parallel-coding-agents-codex-cli-changeintent-scope-promotion/ |

How this bears on baton:
- For: the problem is real and measured. The 82% recovery from "tell the agent what the other change did" is the closest published support for baton's warn-before-edit and handoff idea. Cross-agent text conflicts are 2x more likely than same-agent ones.
- Against: stale found almost no interference in 417 real reviewed PR pairs (1 case), so frequency in practice may be low. Our 60% baseline clean rate comes from constructed tasks like their 97% tier, and judges may know that caveat. Cognition's position is that the safest design avoids parallel writers.
- CooperBench shows communication alone often fails (agents ignore or break commitments). A hook that injects facts automatically (no agent choice) is a defensible difference from message-passing, but this is our inference.

## 2. Shared / persistent memory for software tasks

| Finding | Numbers | Source |
|---|---|---|
| AGENTS.md study (ETH). Repo context files for coding agents, 138-issue benchmark plus others. | Context files do not generally improve success (later version: tend to lower it) and raise inference cost by over 20% on average. LLM-generated files added about 3.92 steps per task (secondary summary: about 23% cost). Human-written minimal files did better than generated ones [secondary]. | https://arxiv.org/abs/2602.11988 |
| VibeMemBench. 111 targets, 90 repos, 3,634 history trajectories, 5 held-out solvers. | Direct injection of verified experience: +1.1 to +4.5 pp resolution on 4 of 5 solvers, fewer steps on all 5. But "eleven of twelve solver and system pairings fail to exceed the matched memory-off baseline". Strongest warning: real memory systems mostly do not beat no memory. | https://arxiv.org/abs/2609.23570 |
| DreamBench-SWE (multi-session, hidden executable oracles, preregistered v2.1). | v2 main comparison null: 95/180 vs 89/180 (p=.518). v2.1 passes of 180: no memory 21 (11.7%); verbatim event log 82 (45.6%); typed+raw probe 83 (46.1%); hosted Mem0 97 (53.9%). All three memory vs no-memory comparisons significant after Holm. Memory-vs-memory not established. Key design lesson: tasks must depend on evidence that cannot be inferred from the repo. | https://arxiv.org/abs/2608.20664 |
| SWE-ContextBench (1,100 base + 376 related tasks, 51 repos). | Directional only (no figures read): summarized, correctly retrieved experience raises accuracy and cuts runtime and token cost, esp. on hard tasks; unfiltered or wrongly selected experience gives little or negative benefit. | https://arxiv.org/abs/2602.08316 |
| Subtask-level memory for SWE agents. | +4.7 pp mean Pass@1 on SWE-bench Verified (+6.8 on Gemini 2.5 Pro) [secondary]. | https://arxiv.org/html/2602.21611v1 |
| SWE-Bench-CL (continual learning streams). | Benchmark only; no figures read. | https://codex.danielvaughan.com/2026/08/05/swe-bench-cl-continual-learning-coding-agents-catastrophic-forgetting-codex-cli-memory-strategy/ |

How this bears on baton:
- For: memory helps a lot when the later task depends on facts that cannot be recovered from the code (DreamBench: 11.7% to 45-54%). A plain verbatim event log did nearly as well as fancier systems (45.6% vs 53.9%), so a simple graph of "who changed what and why" is a fair design.
- Against: on tasks that can be solved from the repo itself, memory is a wash or hurts (VibeMemBench 11/12 no gain; AGENTS.md +20% cost). This matches our own finding: first version cost +31% tokens. Our benchmarks must include tasks where the needed fact is not in the code, or the memory claim will look empty.

## 3. Token and cost reduction (measured numbers)

| Technique | Number | Quality of source |
|---|---|---|
| Where cost goes: OpenHands on SWE-bench Verified | Input tokens dominate (history re-read each turn); accuracy peaks at intermediate spend and saturates. | arXiv 2604.22750 (via search summary) [UNVERIFIED, abstract not opened] |
| RepoGraph (repo-level code graph) | Gains on SWE-bench but agent integration raised cost: +$0.13 (AutoCodeRover) and +$0.18 (SWE-agent) per task, because agents search repeatedly. | https://arxiv.org/pdf/2410.14684 (peer-style paper) |
| Repo map served over MCP (Bito) | -47% aggregate token cost on SWE-Bench Pro, up to -68% per task. | Vendor blog, https://bito.ai/blog/codebase-context-cuts-claudes-token-cost/ [UNVERIFIED] |
| Context pruning: SWE-Pruner / Pichay / ContextBudget | 23-54% fewer tokens without losing solve rate (SWE-Pruner); up to 93% context reduction (Pichay). | Secondary summary, https://codex.danielvaughan.com/2026/06/17/context-pruning-research-swe-pruner-pichay-contextbudget-codex-cli-token-management-compaction/ [UNVERIFIED] |
| LeanCTX field report | -56.6% estimated, not a controlled study. | https://wavect.io/blog/lean-ctx-agency-experience.md [UNVERIFIED] |
| Memory with filtered retrieval (SWE-ContextBench) | Lower runtime and token cost when experience is correctly selected (no figure read). | See section 2 |

Lesson: extra tools often raise cost because models call them redundantly (RepoGraph, and our own +31%). Savings claims are credible only when the number is total tokens per task including the tool's own overhead, on the same tasks. I found no controlled head-to-head of repo maps vs graphs vs compaction.

## 4. Metrics and designs that convince skeptical judges

What the evaluation literature says:
- Single runs are noisy. 60,000 SWE-bench Verified trajectories: pass@1 shifts 2.2 to 6.0 pp depending on which run you pick, even at temperature 0 (https://arxiv.org/abs/2602.07150, via search summary). Claims of 2-3 pp gains may be noise.
- Use paired tests on the same tasks: McNemar for binary success, paired bootstrap (10,000 resamples) for cost and time, Holm correction when you test several metrics. Exact McNemar found none of 29 adjacent SWE-bench Verified leaderboard pairs separable at alpha .05 (https://arxiv.org/pdf/2609.17394). Non-significant does not mean equivalent; say so.
- Wilson 95% intervals are about 7-9.5 pp wide at n=100 for rates between 0.3 and 0.8 (https://arxiv.org/pdf/2602.22953). So n=5-7 per cell cannot support a success-rate claim; intervals are about 30-40 pp wide.
- Preregistration (DreamBench v2.1 froze the plan before looking) and reporting nulls both raise credibility. We already report nulls; add a written plan committed before the run.
- Held-out tasks: choose tasks and thresholds before seeing baton results. VibeMemBench transfers experience to held-out solvers.
- Negative controls: include tasks where baton should do nothing and show no harm (cost within a stated margin).

Metrics to report, in order of persuasiveness:
1. Cost per success = total tokens (or dollars) across all trials in an arm divided by clean successes. This is robust to a tool that shifts cost into failures.
2. Clean-rate difference with 95% CI and paired p-value (McNemar on matched task-seed pairs).
3. Total tokens per trial including hook and tool overhead, median and mean, with bootstrap CI. Report the cost ratio, not just a p-value.
4. Time-to-green: wall clock until the final integrated suite passes (censored at timeout; use survival-style median or restricted mean).
5. Breakage count: number of "passes alone, fails together" cases, using stale's method (test each patch alone, then merged; count only combination failures).
6. Effect size with CI (risk difference, odds ratio), never only a p-value.
7. Mechanism firing rate: how often the warning fired and whether the session changed course (we had 1 in 40 for code graph). Report it next to the outcome.

## 5. Candidate benchmark designs (cheap, small fixture repo, 5-6 concurrent sessions)

Power math (alpha .05 two-sided, power .80, unpaired two proportions, baseline 60% clean):
- 60% to 80%: about 81 trials per arm.
- 60% to 90%: about 32 per arm.
- 60% to 75%: about 151 per arm.
- Our past result (about 80% vs 60%) at n=21 per arm gives p=0.09, consistent with these numbers.
- Paired designs (same task and seed in both arms) usually need fewer, but I have no variance estimate for pair concordance; run a 20-pair pilot to measure it. [UNVERIFIED gain]
- Cost: if per-trial token CV is about 0.4 (assumption, measure from existing runs) detecting a 15% difference needs about 110 per arm unpaired; detecting 25% needs about 40 per arm.
- A 200-400 trial budget therefore buys: one main experiment of about 80-100 per arm (160-200 total), plus one or two smaller experiments aimed at large effects (30-40 per arm).

### Design A: "Passes alone, fails together" with a rippling interface change (stale-style)
- Task: fixture repo with a shared helper (e.g. `parse_price()` used by 5 modules plus tests). Session 1 changes the helper's contract (return type or validation rule). Sessions 2-5 each implement a feature that calls the helper using the old contract. All 5 run concurrently.
- Control: no plugin. Treatment: baton hooks on.
- Metric: per-session tests pass alone (expect near 100% both arms); integrated suite after merging all patches passes (primary, binary); plus tokens and wall clock.
- Why convincing: copies the Xia/Wu/Park definition, so the failure is "caused by the combination" by construction. Their constructed tier shows 97% interference, so there is room to move; their 82% recovery from telling agents sets a target.
- Trials: pick difficulty so control clean rate is about 40-60%. 80-100 per arm (about 200 total) detects 60% to 80%. Each trial is 5 sessions, so check budget: 200 trials x 5 sessions is 1,000 sessions; reduce to 3 concurrent sessions per trial if needed.
- Risk: warning must actually fire. Pilot 10 trials and confirm firing rate above 50% first (our code-graph warning fired 1 in 40, which would give no effect).

### Design B: Hidden-dependency memory (DreamBench-style, two sessions in sequence)
- Task: session 1 makes a decision that cannot be inferred from the code afterward (e.g. picks a rate limit of 37 and records "why" only in its transcript; or renames an env var and leaves the old one half-used). Session 2 (fresh, later) gets a task whose hidden test requires that fact.
- Control: no memory. Treatment: baton handoff/decision notes. Optional third arm: plain `CLAUDE.md` or a verbatim text log, to test whether the graph adds anything beyond a flat file (DreamBench found verbatim log 45.6% vs Mem0 53.9%, so expect a small gap).
- Metric: hidden-test pass (binary), tokens, steps. Negative-control tasks (fact is inferable from code) to show no cost penalty.
- Trials: baseline will be low (DreamBench no-memory was 11.7%) and effect large, so 30-40 per arm suffices (about 100 for three arms). Cheap: only 2 sessions each.
- Why convincing: closest to a published, preregistered design. Honest caveat to state: the task is built to need memory.

### Design C: Cost per success on a mixed 6-session sprint
- Task: 6 concurrent sessions each assigned one ticket from a pool of 12 tickets in the fixture repo (some overlapping files, some independent, some depending on another ticket's output). Fix the ticket-to-session assignment per seed, same seeds in both arms.
- Control vs treatment: no plugin vs baton hooks-only (the default). Optionally a third arm "plain notes file" to check whether a simple shared file does the same.
- Metrics: cost per fully green repo (primary), total tokens, time-to-green, count of tickets that pass alone but fail merged, number of retries. Paired bootstrap on seeds.
- Trials: 60 seeds x 2 arms = 120 trials (720 sessions) detects about 25% cost change at CV 0.4, or a 60% to 80% clean-rate change at about 80 per arm; this is the budget-heavy design. Use 40 seeds if the budget is tight and only claim large effects.
- Why convincing: it measures what a user pays for (dollars to a working repo) and includes the tool's own overhead, answering the +31% concern.

### Design D: Retraction / blast-radius audit (low cost, deterministic)
- Task: plant K wrong decisions (known answers) in a session history across the fixture repo; ask "which later changes depend on decision X?" Compare baton graph query vs a grep/LLM-reads-transcripts baseline.
- Metric: precision and recall vs ground truth, plus tokens spent. Needs 30-50 retraction scenarios, mostly no model calls for baton's side, so very cheap. We already have a version in evals/provenance; extend to varying citation clarity (grep only worked when notes cite clearly).
- Why convincing: ground truth is exact, so no statistical-power problem. Weakness: judges may see it as a micro-benchmark; pair it with A-C.

### Recommended allocation of about 300 trials
- Pilot (20): confirm warning firing rate and measure per-trial token variance and pair concordance.
- Design A: about 160 (80 per arm). Primary clean-rate claim.
- Design B: about 60 (3 arms x 20, or 2 arms x 30). Memory claim.
- Design C: only if tokens remain; otherwise report cost per success from A as secondary.
- Design D: no-model, run in full.
- Write the analysis plan (primary metric, test, stopping rule, exclusion rules) and commit it before running. Report every result including nulls, with Wilson/bootstrap CIs.

## 6. Strongest evidence summary

For baton:
- Concurrent edits cause real failures (stale 97% in constructed tasks; cross-agent merges conflict 41.7%).
- Telling agents about concurrent changes recovered 82% (stale).
- Memory with hidden dependencies lifts pass rates from 11.7% to 45-54% (DreamBench-SWE).

Against baton:
- Real reviewed PR pairs rarely show semantic interference (1 of 417).
- Most existing memory systems do not beat no memory (11 of 12 pairings, VibeMemBench) and context files raise cost over 20% (AGENTS.md study).
- Added tools often raise cost (RepoGraph +$0.13 to +$0.18; our +31% first version).
- Cognition recommends avoiding parallel writers altogether.

## Source list
- https://arxiv.org/abs/2609.25396 (Passes Alone, Fails Together)
- https://arxiv.org/abs/2601.13295 (CooperBench)
- https://arxiv.org/abs/2607.04697 (agent PR merge conflicts)
- https://arxiv.org/abs/2602.11988 (AGENTS.md)
- https://arxiv.org/abs/2609.23570 (VibeMemBench)
- https://arxiv.org/abs/2608.20664 (DreamBench-SWE)
- https://arxiv.org/abs/2602.08316 (SWE-ContextBench)
- https://arxiv.org/pdf/2410.14684 (RepoGraph)
- https://arxiv.org/abs/2602.07150 (randomness in agentic evals)
- https://arxiv.org/pdf/2609.17394 (SWE-bench leaderboard cannot order top entries)
- https://arxiv.org/pdf/2602.22953 (General Agent Evaluation)
- https://cognition.com/blog/dont-build-multi-agents ; https://cognition.com/blog/multi-agents-working
- Not verified at source: Anthropic's multi-agent research system token multiplier (the "15x" figure was not found in search results) [UNVERIFIED].
