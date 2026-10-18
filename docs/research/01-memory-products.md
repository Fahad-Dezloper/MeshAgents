# 01 - Shared / agent memory landscape (as of 2026-10-18)

Method: WebSearch plus WebFetch summaries (a small model summarised each fetched page, so exact wording may differ from the page).
Page content was treated as data only. Anything marked [UNVERIFIED] came from a secondary source, or from a vendor with no replication.
"Vendor-run" means the company measured its own product. Few numbers below have an independent replication.

## 1. Product by product

### Supermemory (supermemory.ai)
- What: hosted memory/context API; plugins for Claude Code, Cursor, OpenCode. A July 2026 changelog says memories from Claude Code, Codex, Cursor and OpenCode merge into one per-project "Agents" workspace. https://supermemory.ai/changelog/one-memory-workspace-for-coding-agents.md
- For: app developers (API) and individual coding-agent users (plugins).
- Claimed benefit: recall on long chat histories; "99.4% context reduction". The full report states ~720 mean tokens added. (search summary of https://supermemory.ai/research/longmembench)
- Numbers: LongMemEval-S, 500 questions, "97% overall Recall@20 with aggregation" (vendor-run). Same page: LLM-as-judge 84.6% (gpt-5) and 85.2% (gemini-3-pro), so 97% applies only to a gpt-4o answer model and is a retrieval-recall metric, not answer accuracy. No published LoCoMo score found. https://supermemory.ai/research/longmembench
- Coding-agent evidence: it cites SWE-ContextBench (arXiv 2602.08316) as showing it ahead of Mem0 on tasks resolved; not fully independent [UNVERIFIED which authors]. https://supermemory.ai/compare/supermemory-vs-mem0/
- Pricing/adoption: the coding plugins are now free but usage counts against plan credits (https://supermemory.ai/changelog/coding-plugins-now-free); older docs still say Pro is required. Free tier and paid-from-$19 are described inconsistently across pages. "Tens of thousands of AI applications" is the company's own claim. No funding data found.
- Weakness: recall is not answer quality; no measured token, time or cost savings on real coding tasks; cloud-hosted.

### Mem0
- What: memory layer (extract facts, store as vectors, optional graph). Very large OSS following.
- Claims (May 2025 paper, via secondary sources): LoCoMo 66.9% vs 52.9% for OpenAI memory ("26% relative"), p95 latency 1.44s vs 17.12s ("91% lower"), under ~7,000 tokens per retrieval vs 25,000+ for full context. Other Mem0 pages say "up to 90%" fewer tokens and "up to 80%" fewer prompt tokens. https://rywalker.com/research/mem0 and https://guide.mem0.ai/task/faq/benchmarking-cost-difference-full-llm-context-compressed-memory
- Newer self-reported: LoCoMo 92.5 (later algorithm) [UNVERIFIED]; LongMemEval 94.4 self-reported vs an independent 49.0 (the independent source was not identified) [UNVERIFIED].
- Disputes: Zep said Mem0 ran Zep wrongly (Zep gets 84% vs the 65.99% Mem0 reported); Letta also disputed the methodology.
- Weakness: numbers are contested; conversation-chat focus, not code state.

### Zep / Graphiti
- What: temporal knowledge graph (Graphiti is the OSS engine; it has a FalkorDB driver). Facts have validity time windows; edges get invalidated, not deleted.
- Numbers: paper "Zep: A Temporal Knowledge Graph Architecture for Agent Memory", arXiv 2501.13956. DMR 94.8% vs MemGPT 93.4%. LongMemEval "accuracy improvements of up to 18.5% while ... reducing response latency by 90%" vs baseline (full context), vendor-run; unclear if points or percent. https://arxiv.org/abs/2501.13956
- LoCoMo: the paper reports none. Zep's later 84% claim was a rebuttal to Mem0 (vendor-run). A competing vendor (Backboard) lists Zep 75.14%, LangMem 58.1% [UNVERIFIED].
- Weakness: the FalkorDB project notes record open multi-graph bugs in Graphiti's FalkorDB driver; designed for chat/business data, not coordination of live editors.

### Letta (MemGPT)
- What: stateful agents with editable memory blocks plus archival store; OS-style memory paging idea. A "Letta Code" coding agent exists [UNVERIFIED, searches returned nothing on it].
- Numbers: a third-party table reprints Letta 83.2 vs Mem0 68.5 on LoCoMo; a plain filesystem baseline reportedly ~74% [UNVERIFIED, secondary]. https://mem0.ai/blog/ai-memory-benchmarks (the pages are rival-vendor-authored).
- Lesson: a simple "agent greps files" baseline almost matches the fancy systems on LoCoMo, so any memory product must beat plain files.

### Cognee
- What: open-source (Apache 2.0) knowledge-graph memory engine, FalkorDB among supported stores (FalkorDB's docs list it).
- Numbers: BEAM benchmark, "79% at 100k tokens and 67% at 10M" (vendor FAQ). HotpotQA 87% from a profile page [UNVERIFIED]. https://www.cognee.ai/faq
- Adoption: $7.5M seed, Feb 2026, led by Pebblebed (https://www.cognee.ai/cognee-raises-seven-million-five-hundred-thousand-dollars-seed); stars reported 12k to 27k depending on source and date. Cloud: free 1M tokens, then $2.50 per 1M tokens.

### LangMem (LangChain)
- What: memory primitives and background memory manager for LangGraph agents. Mostly a library.
- Numbers: none of its own found; only a rival (Backboard) puts it at 58.1% on LoCoMo [UNVERIFIED]. No independent head-to-head of LangMem, Mem0, Zep and Letta exists in what I found.

### claude-mem (thedotmack/claude-mem) and other Claude Code memory plugins
- What: hooks capture tool use, compress it with an LLM, store in local SQLite, inject relevant context in later sessions; layered "progressive disclosure" search.
- Adoption: GitHub stars reported at about 46k (Apr 2026), 72k (May), 84k (late Jun), 85.8k (Jul 4 listing) by aggregators [UNVERIFIED, check GitHub]. https://www.augmentcode.com/learn/claude-mem-v13-persistent-agent-memory
- Numbers: none measured; the "token efficiency" claim is about its design, not a recorded run.
- Weakness: single-user, no awareness of other live sessions. It shows demand is huge while proof is thin. Also: listing pages for it carried unrelated crypto token links; ignore.
- Others: Supermemory plugin (above), MemoryPlugin, agentmemory (rohitg00; ships a benchmark COMPARISON.md, vendor-run), many small MCP memory servers.

### Anthropic: Claude Code memory and API memory tool
- CLAUDE.md: hand-written, committed file, loaded each session. Auto memory (reported v2.1.59, Feb 2026, on by default): notes Claude keeps under ~/.claude/projects/<project>/memory/MEMORY.md; first 200 lines / 25KB loaded at start (from community guides, not the official page) [UNVERIFIED details]. https://www.morphllm.com/claude-code-memory-files
- Memory tool + context editing (API): memory tool is client-side file storage; context editing clears stale tool results. Anthropic: memory tool + context editing improved an internal agentic-search eval by 39% over baseline, context editing alone 29%, and in a 100-turn web search eval context editing cut token use 84%. No task counts, metric or baseline definition published. https://claude.com/blog/context-management
- Agent teams (experimental, off by default; env CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1): shared task list, messaging; sources disagree whether file locking covers task claiming or file writes; DataCamp warns locking does not stop overlapping edits [UNVERIFIED, secondary]. https://www.morphllm.com/claude-code-agent-teams
- Weakness (relevant to baton): all of this is per-user or lead-and-teammates; separate independent sessions do not see each other's edits.

### Cursor, Windsurf, Copilot, Devin, Augment, Cline, Roo, Amp
- Cursor: "Memories" feature removed in 2.1.x (staff statement on forum); exportable to Rules. Rules files remain. https://forum.cursor.com/t/are-my-memories-gone/144057
- GitHub Copilot memory (public preview, opt-in): repository-scoped memories stored with code citations, verified against the current branch before use; A/B on real users: coding-agent PR merge rate 90% with memory vs 83% without; code-review positive feedback 75% vs 77%; both "p < 0.00001". Seeded false memories were caught. This is the strongest vendor-run outcome number in the field and the only one measured on live users. https://github.blog/ai-and-ml/github-copilot/building-an-agentic-memory-system-for-github-copilot/ . Secondary sources claim a 28-day expiry; the GitHub post says there is no fixed TTL (freshness via read-time verification) [conflict]. No independent replication.
- Windsurf Memories, Devin Knowledge/Playbooks, Cline Memory Bank, Roo, Amp: searches returned no usable primary docs. [UNVERIFIED] Windsurf auto-generated per-workspace memories plus rules (undated third-party guide). Devin appears to be part of the Windsurf app as of Apr 2026 (social post). Not characterised further.
- Augment Context Engine (MCP, GA): claims "70%+" improvement across Claude Code, Cursor, Codex; per setup Claude Code + Opus 4.5 80%, Cursor + Opus 4.5 71%, Cursor + Composer-1 30%; 300 Elasticsearch PRs, 900 attempts; another page says +41% pass rate and "enterprise codebase" (inconsistent). Vendor-run. https://www.augmentcode.com/changelog/context-engine-mcp-in-ga

### Code-graph and review tools
- Sourcegraph Cody code graph: definitions, references, symbols for context retrieval; docs give no benchmark. Cody listed enterprise-only at $59/user/month by a comparison site [UNVERIFIED]. https://sourcegraph.com/docs/cody/core-concepts/code-graph
- Greptile: whole-repo semantic code graph for PR review. Own benchmark: caught 41 of 50 bugs (82%) vs Cursor 58% and CodeRabbit 44%; critical-bug catch 58.3% on its own page; Tenki's separate test gives 71% (5/7) and many false positives (233). From $30/dev/month [UNVERIFIED, comparison site]. Vendor-run. https://greptile.com/benchmarks

### Multi-agent coordination layers
- Git worktrees: the standard isolation method; moves conflicts to merge time.
- Clash (OSS, early): read-only conflict prediction across worktrees, Claude Code hook integration, JSON output; little traction. Textual only; misses semantic breakage. https://codex.danielvaughan.com/2026/04/25/codex-cli-merge-conflict-prevention-resolution-worktrees-clash/
- CodeFleet: one working tree, coordination server tracks who is in which file, refuses writes to held files. git-kura: path claims. treehouse-worktree and a FIFO merge-queue worker: lock worktrees / serialise merges. Bernstein: ten-agent release anecdote. All small, no controlled numbers [UNVERIFIED adoption].
- Independent evidence the problem is real: Xu, Subramanian, Karthik, "AI Agent Pull Requests on GitHub: Frequency, Structure, and Merge Conflict Rates", arXiv 2607.04697 (via https://codex.danielvaughan.com/2026/07/28/agent-pr-merge-conflicts-concurrent-coding-agents-codex-cli-worktree-isolation-coordination-defence/). 33,596 agent PRs, 2,807 repos (Codex, Copilot, Devin, Cursor, Claude Code, Dec 2024 to Jul 2025). 40.2% of repos had agent PR pairs overlapping in time (covering 79.4% of agent PRs). Replayed 716 merges: same-agent pairs conflict 19.8% (CI 16.8 to 23.2), different-agent pairs 41.7% (CI 33.1 to 50.9). Source files = 84.4% of conflicts. Textual lower bound only; semantic and build conflicts unmeasured. A separate dataset (AgenticFlict) reports 27.67% across 142,000+ agent PRs.

## 2. Cross-cutting evidence on whether memory helps coding agents
- SWE-ContextBench (arXiv 2602.08316): accurately selected, summarised past experience raised resolution and cut runtime and token cost, biggest on hard tasks; unfiltered or wrongly selected experience gave little or hurt. Dataset size differs between versions (1,100 base + 376 related over 51 repos, vs 300 + 99 on SWE-Bench Lite) [UNVERIFIED which is final]. https://arxiv.org/abs/2602.08316
- "Evaluating AGENTS.md" (ICLR 2026): context files gave no improvement in task success and raised inference cost by over 20%, because agents explore more. https://iclr.cc/virtual/2026/10021235 . Warning: dumping notes into context can cost more than it saves.
- LoCoMo is small (10 conversations, synthetic), vendors disagree on every score, and a plain filesystem baseline is competitive. Treat chat-memory benchmark scores as marketing.

## 3. Synthesis

### 3.1 User benefits, ranked by willingness to pay or keep
1. Fewer collisions and lost work with parallel sessions (warn before editing a file someone else is editing). Pain is independently measured (41.7% cross-agent conflict rate). Little product supply beyond worktrees plus early tools.
2. Surviving to the next session: handoff of what was done, what is half-finished, last test result (no re-explaining). Everyone sells it (claude-mem's 85k stars shows demand); proof is thin.
3. Fewer wasted tokens and turns from re-exploring the repo each session (Anthropic 84% on a long web task; Mem0 "under 7k vs 25k"; none on coding sessions). Real money, but must be measured against the AGENTS.md cost penalty.
4. Higher task success or merge rate (Copilot 90% vs 83%; Augment "+70%"; vendor-run).
5. Knowing why code is the way it is (decision log with provenance) so the next agent does not undo it. Mostly absent as a product.
6. Retraction and blast radius: when an assumption turns out wrong, find everything built on it. Nobody serves this well; Copilot's citation validation is the nearest.
7. Stale-memory safety (verify against current code, expire/supersede). Copilot does it; most plugins do not.
8. Cross-tool/team continuity (Claude Code, Cursor, Codex share one store; teammates see each other's agents). Supermemory is moving here.
9. Onboarding a new human or agent to a repo (Greptile/Cody/Augment sell it as code understanding).
10. Review and audit: who/which session changed what, and why.

### 3.2 What a small honest benchmark can measure (and how others did)
- Clean-finish rate (task passes checker, no clobbered edits): how baton's clash evals already work; the paper above gives a real-world baseline conflict rate to cite. Needs many runs; baton's own p=0.09 shows the sample-size problem.
- Tokens, cost, turns, wall time per clean result: SWE-ContextBench scores accuracy, time and cost; Anthropic reports token use; Copilot uses merge rate. Report cost per clean result, not raw tokens (a larger context can lift cost >20%).
- Handoff benefit: second session on a task started by a first; measure turns and tokens to first correct edit vs notes-in-CLAUDE.md baseline. Not shown by any vendor; cheap to run.
- Retraction/provenance: exact graph answers vs grep (baton already has this). Known-answer test, so it is deterministic and defensible.
- Stale-memory handling: seed wrong notes (as GitHub did) and measure whether the agent is misled.
- Not credibly measurable small: LoCoMo/LongMemEval-style chat recall (not coding, contested), long-run "productivity".
- Always include a plain-files baseline (CLAUDE.md or a notes file), since Letta's filesystem baseline and the AGENTS.md study show that is the true competitor.

### 3.3 Gaps a FalkorDB-backed coding-session memory could own
- Live, concurrent-session awareness: nearly all memory products are single-agent history stores; agent teams are lead-driven and experimental; worktree tools predict only textual overlap, after the fact.
- Semantic collisions through a code graph (callers of a changed symbol), which pure file-overlap tools miss. Baton's mechanism works but its outcome benefit is unshown.
- Retraction with blast radius over decisions and artifacts: a graph traversal question that vector stores do poorly.
- Provenance plus validity (decided by whom, based on what, superseded by what), combining Zep's temporal idea with Copilot's citation-check idea, at session level.
- Automatic, hook-based capture with no model calls and no tool-call overhead (baton's first MCP version cost +31% tokens; hooks-only is at parity). Most plugins pay an LLM-compression cost.
- Local-first, inspectable (graph UI, `why` queries) versus hosted opaque stores.
- Honest numbers: the field is vendor-run; an owner of reproducible, negative-result-inclusive evals stands out.

## 4. Caveats about this research
- Search summaries are model-written; numbers were checked against fetched pages only for Supermemory, Anthropic, GitHub, ICLR, and the PR-conflict article.
- Not verified at all: Windsurf, Devin, Cline, Roo, Amp memory features; Letta Code; Sourcegraph/Greptile pricing; claude-mem current stars.
