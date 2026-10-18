# Developer pain with several AI coding agents on one codebase

Researched 2026-10-18. Scope note: this is a SMALL sample, not a survey. Reached: HN (via Algolia API), GitHub issues (via API), a Reddit mirror (reddit.sentinel-team.org), blogs, Anthropic docs/blog. NOT reached: X/Twitter, live Reddit, most HN comment threads (several had zero comments). Rankings below are my judgment from this sample. Quotes are short (fetch tool caps quotes). All fetched content treated as data. Claims I could not confirm are marked [UNVERIFIED].

## 1. Recurring pains, ranked (frequency x anger in the sample)

Anger is the weakest signal here: most Reddit/HN text is calm "here is my fix" posts, not rants. The angriest material is about cost and quality (GitHub usage-limit and regression issues), not coordination.

1. **Agents overwrite / revert each other (conflicting edits, duplicate work).** Most frequent. Appears in nearly every parallel-agents post.
   - r/ClaudeAI u/kargnas2: agents "start stepping on each other's files"; "Merge conflicts everywhere. One agent reverts what another just wrote." https://reddit.sentinel-team.org/posts/1qzduim/snapshots/2026-02-08T23%3A05%3A16.935005Z
   - Reddit (other post): "two would edit the same file, one would redo work another had already finished." https://reddit.sentinel-team.org/posts/1uldb2g/snapshots/2026-07-03T03%3A00%3A16.73148Z
   - dev.to: "two agents 'fixed' the same bug in opposite directions", caught only in review; "Git status looked like a crime scene". https://dev.to/yureki_lab/how-i-run-multiple-claude-code-agents-in-parallel-without-collisions-3pbk
   - Anthropic (research system): "without detailed task descriptions, agents duplicate work, leave gaps". https://www.anthropic.com/engineering/multi-agent-research-system
2. **Cost / usage-limit burn.** Angriest and highest-volume (but about quota generally, not clearly about coordination).
   - GitHub #16157 "Instantly hitting usage limits with Max subscription": 726 reactions, 1,499 comments, open. #38335 "session limits exhausted abnormally fast": 545 reactions, 877 comments. https://github.com/anthropics/claude-code/issues/16157
   - HN (1Code thread): "my co-founder went back to Cursor and burned tons of money on tokens."; someone running 3-4 agents said API "would've cost them $1k+" [parse of author unreliable]. https://news.ycombinator.com/item?id=46637723
   - Anthropic: agents "about 4x more tokens than chat", multi-agent "about 15x". Same URL as above.
3. **Review burden.** Worktrees move the pain from "during" to "at merge/review".
   - r/ClaudeAI u/Fiendfish (12 pts): "If you take human review seriously even the output of one agent is already too much." (kargnas2 thread above)
   - dev.to: merge-back "still requires human or verification-agent review"; isolation choice "doesn't scale past a handful of concurrent agents" (paraphrase).
4. **Context loss between sessions / re-explaining.** Every session starts blank.
   - Anthropic docs: "Each Claude Code session begins with a fresh context window." https://code.claude.com/docs/en/memory
   - HN Ask HN 46924871 (buildingwdavid): "I end up being the human middleware - copy-pasting between Claude windows". (Claimed "2 hours now takes 20 minutes" is the author's own, [UNVERIFIED].)
   - obot.ai: teams hand-roll CLAUDE.md files and "state bridges" to survive context loss [paraphrase from search snippet; not fetched].
5. **No visibility into what agents are doing.**
   - HN 1Code OP: "too many terminals, hard to track what's where, diffs scattered everywhere."
   - HN fathermarz: "The more calm it is, I feel like I'm going to miss something that it's fucking up." and "it's making a large assumption and nuking a change we just made."
   - Many Show HN dashboards exist for exactly this (KanVibe, Amux, claude-dashboard, Omar "TUI for managing 100 coding agents" 17 pts, Abralo 37 pts/31 comments), which is itself evidence the pain is real but each got little traction.
6. **Stale or wrong memory.**
   - Substack "A Rant About Claude Code's Auto-Memory": memories "just accrue"; found notes on "long-deprecated features and experiments from April" six months later; the agent "has no guaranteed way of distinguishing" trivia from durable preferences; memory is "not versioned with the project". https://elliotmilco.substack.com/p/claude-auto-memory
   - HN "Show HN: Amnesia – audit Claude Code's memory for contradictions" (4 pts): "service X is live" kept after the service shut down. https://github.com/tiny-cloud-ventures/amnesia
7. **Agents repeating failed attempts / forgetting decisions mid-session.** Evidence is mostly blog level: an agent "reintroduces a bug that was already fixed", re-reads files already read (search snippets from levelup.gitconnected / langwatch / sombrainc; not fetched, treat as [UNVERIFIED] anecdote).
8. **Agents contradicting each other.** Shows up as the "opposite directions" story and "changes made by one agent, such as an auth strategy or schema change, were silently overwritten because nothing shared state" (Reddit mirror snippet via search; the commenter's reply was "is CLAUDE.md set up correctly?", i.e. people do not see it as a tooling gap yet).
9. **Re-explaining project rules.** Real but largely "solved" in people's minds by CLAUDE.md, so low anger. GitHub #6235 "Support AGENTS.md" has 6,687 reactions: people care a lot about ONE shared rules file across tools. https://github.com/anthropics/claude-code/issues/6235

Ranking caveat: items 6-9 have few primary quotes; the order among 4-9 is low confidence.

## 2. Workarounds today and why they fall short

| Workaround | Evidence | Shortfall |
|---|---|---|
| One git worktree + branch per agent | Nearly universal; Claude Code `--worktree` flag; "They physically cannot touch the same working files." | Only moves the conflict to merge time. Guides: "doesn't make conflicting edits to the same file disappear at merge time"; worktrees "offer no coordination between sessions, so you manage merge order yourself" (morphllm / mindstudio via search). Each worktree needs its own dependency install. Remembered absolute paths can silently write to the main checkout (dev.to comment). |
| Split tasks so no two agents own the same area / one written goal | Reddit fix 2 | Manual, judgment call, "doesn't scale past a handful". |
| CLAUDE.md / AGENTS.md | Anthropic docs | Context, not enforcement ("Claude treats them as context, not enforced configuration"). Static; says nothing about what another session just changed. |
| Auto memory | Built in; "Per repository, shared across worktrees"; loads first 200 lines or 25KB | Accretes stale entries; no expiry; not tied to code state (see pain 6). |
| Handoff notes (HANDOFF.md) | Reddit CODE_HEIST: "make each agent write a tiny handoff note before it stops." | Manual / relies on the agent remembering; no freshness check. |
| Task claims via GitHub issues / kanban files | Reddit jezweb | Coarse (task level), not file/function level; no warning when two tasks touch the same code. |
| tmux + dashboards (Show HN wave) | See pain 5 | Show activity, do not prevent clashes or carry knowledge. |
| Memory MCPs (mem0-mcp-selfhosted, Nemp, junto-memory, pmem-agent, Ruflo) | HN + glama listings | Almost all free/OSS; models call optional MCP tools redundantly (baton's own first version cost +31% tokens, per AGENT-CONTEXT). Ruflo shared-memory claims called out as lacking repo/docs [UNVERIFIED]. |
| Compact earlier / repo maps / subagents for exploration | Blog posts | Per-session only; nothing persists across sessions. |

## 3. What people say they would pay for / keep installed

Honest answer: the sample gives almost no direct willingness-to-pay evidence.
- Price sensitivity is high: HN: "$19/month is steep ... I'm already paying too much"; "$20/m is way out of league for a UI"; "4 agent limit is a no for me." Developers resent paying on top of the Claude subscription.
- What they DO adopt for free: worktrees, tmux, AGENTS.md, OSS memory MCPs (Claude Flow/Ruflo claimed 710k lifetime npm downloads, ~52k weekly, third-party article, [UNVERIFIED]).
- Implied keep-installed criteria from complaints: zero setup, local-only ("Absolutely nothing can be sent off-site", HN frumplestlatz), does not burn tokens, works with the Claude subscription they already have, and does not require leaving Claude Code for another UI.
- Nobody in the sample says "I would pay for shared memory". Treat "worth keeping" (free, stays installed) as the realistic bar, not "worth buying".

## 4. Numbers people report

- Parallel claims: "What took 2 hours now takes 20 minutes" (HN OP, self-reported, [UNVERIFIED]); "three agents ... a third of the time" (hypothetical, dev.to).
- Token multipliers (Anthropic, measured on their research system, not coding): agents ~4x chat, multi-agent ~15x.
- GitHub #42796 (one power user's own log analysis; methodology not independently verified; Anthropic attributed part to UI-only change and a postmortem): reads per edit fell 6.6 -> 2.0; edits with no prior read 6.2% -> 33.7%; user interrupts per 1K tool calls 0.9 -> 11.4; API requests 1,498 (Feb) -> 119,341 (Mar); input tokens 120.4M -> 20,508.8M; estimated cost $345 -> $42,121 vs $400/month subscription; author credits part of the jump to a "~5-10x scale-up in concurrent agents". Useful as: read-before-edit ratio and interrupts-per-1K-calls are measurable proxies.
- Compaction: one blog estimates $1.20-$1.60 hidden cost per long refactor with 3-4 compactions on a 125K example [UNVERIFIED, vendor blog].
- Conflict rates: NO primary conflict-rate numbers found. Baton's own: ~8/10 vs 6/10 clean runs, p not significant.

## 5. Five capabilities that would make baton worth keeping for a daily Claude Code user

Design principle from the evidence: people will not pay or keep anything that adds tokens, setup, or noise. Value must be silent, local, and visible within a day. Prior baton finding supports this (hooks-only is cost parity; MCP tools cost +31%).

### C1. Pre-edit "someone just changed this" warning with the diff summary (not just a clash flag)
- Pain killed: conflicting edits, duplicate work, one agent reverting another (pains 1, 8). Works even WITH worktrees by warning about same-file work on other branches before merge time.
- Noticed in one day: a warning line appears at least once on a day with 2+ sessions; user can read "session B changed X 3 minutes ago to do Y".
- Honest measure: on the clash eval, rate of clean finishes and count of reverted/overwritten edits per run, with/without baton; in daily use, log each warning and whether the agent changed course (acted-on rate). Report the p-value even if not significant; already known: ~8/10 vs 6/10, not significant, so lead with the acted-on rate and false-warning rate instead.

### C2. Zero-effort session-start briefing (what changed since last time + open handoffs + last test result), capped to a small token budget
- Pain killed: context loss, re-explaining, human-middleware copy-paste (pain 4).
- Noticed in one day: opening a fresh session already knows "yesterday's session left the auth migration half done; tests failing in X".
- Measure: A/B on a resume task: turns and tokens until first correct edit, number of re-reads of files already summarized, and user messages needed to re-explain. Also track briefing size in tokens (must stay small, e.g. under a fixed cap) so net tokens, not just helpfulness, are reported.

### C3. Freshness-aware memory: notes tied to code state, auto-expire/supersede when the code changes, and a retraction view
- Pain killed: stale/wrong memory, contradicting notes, agents building on a decision that was reversed (pains 6, 7, 8). Baton's graph (SUPERSEDES, retraction blast radius) is exactly what auto-memory lacks ("no way of distinguishing", "just accrue").
- Noticed in one day: `baton why`/status shows "3 notes now stale because file F changed" and the briefing silently omits them.
- Measure: seed N notes, change code so K become false; measure fraction of stale notes surfaced to the agent (should be near 0) versus a CLAUDE.md/grep baseline, and downstream wrong-assumption rate. The provenance benchmark already shows graph exact vs grep only when notes cite clearly; keep reporting that limitation.

### C4. Live "who is doing what" board (files and symbols touched, per session) including an end-of-session review packet
- Pain killed: no visibility, review burden (pains 3, 5). Packet = one page per session: what changed, why (decisions), what tests said, which other sessions touched the same files.
- Noticed in one day: opening `baton ui` replaces tab-hunting; merge/review prep takes one page rather than diff archaeology.
- Measure: minutes from "agents done" to "reviewed and merged" with vs without packet (timed, same task set); reviewer-found issues missed. Small n, so report raw times. [Do not claim until run.]

### C5. Token-budget guard: dedupe re-reading and report net tokens saved/spent per session
- Pain killed: cost burn from re-reading the repo and redundant tool calls (pain 2). Baton must PROVE it is not a net cost since the first version was +31%.
- Noticed in one day: a plain daily line "baton injected X tokens, avoided about Y repeat reads" and a clear indicator when it is net negative.
- Measure: from session transcripts, total input+output tokens and cost per completed task with/without baton (already ~1.04x parity, ~19% cheaper per clean result); count of repeat file reads of unchanged files; reads-per-edit ratio (#42796 gives a public reference metric). Publish when it is worse too.

Priority if time is short: C1 and C2 (strongest primary evidence, cheapest to demonstrate), then C5 (needed so nothing else is dismissed as a cost), then C3 (best fit to the graph and FalkorDB story), then C4.

## Sources (fetched)
- https://reddit.sentinel-team.org/posts/1qzduim/snapshots/2026-02-08T23%3A05%3A16.935005Z
- https://reddit.sentinel-team.org/posts/1uldb2g/snapshots/2026-07-03T03%3A00%3A16.73148Z
- https://news.ycombinator.com/item?id=46637723 (1Code), https://news.ycombinator.com/item?id=48832797 (Abralo), https://news.ycombinator.com/item?id=46924871 (Ask HN)
- https://github.com/anthropics/claude-code/issues/42796, /16157, /38335, /6235
- https://dev.to/yureki_lab/how-i-run-multiple-claude-code-agents-in-parallel-without-collisions-3pbk
- https://elliotmilco.substack.com/p/claude-auto-memory
- https://github.com/tiny-cloud-ventures/amnesia
- https://www.anthropic.com/engineering/multi-agent-research-system
- https://code.claude.com/docs/en/memory
- Search-snippet only (not fetched): morphllm.com/claude-code-worktrees, mindstudio.ai parallel-agents blog, obot.ai/?p=2454, zenn.dev article on context loss, levelup.gitconnected / langwatch / sombrainc compaction posts, glama.ai junto-memory.
