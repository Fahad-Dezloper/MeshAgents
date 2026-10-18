# My AI helpers kept breaking each other's work, so I gave them a shared memory

I often run more than one AI coding session at once. Within days I saw the same three problems:

- Two sessions edited the same file without knowing.
- One session renamed a function while another kept calling the old name.
- The next day, a new session started knowing nothing. Even rules I had told the last one, like "never use sqlite, the server is read-only".

A recent study of about 33,000 pull requests written by AI helpers found that changes from *different* helpers conflict about twice as often as changes from the same helper. So it isn't just me.

## What I built

MeshAgents is a shared notebook for AI coding helpers, built for the WeMakeDevs x FalkorDB Graph Hacks hackathon (Track 2, Agent Memory and Coordination). It runs quietly as a Claude Code plugin, and you type nothing. It:

1. **Warns before a clash.** If another session is working on the file you're about to edit, you hear about it first. If you change how a function is called, it tells you which callers elsewhere may break.
2. **Remembers what changed and why.** If a note turns out to be wrong, it shows everything built on it.
3. **Hands over to the next session**, including rules people stated once in conversation.
4. **Shows it on a live board**, a simple page showing who's working on what.

## Why a graph?

Every question it answers is about connections. "Who holds a lease on this file?" "What was this decision based on, and what breaks if it's wrong?" "Which functions call the one I just changed?" "Which files usually change together?" I used FalkorDB for all of it. Claiming a task is one Cypher query, and FalkorDB's per-graph write ordering makes it race-free. "What depends on this wrong fact" is a variable-length traversal. Retracting a wrong note found exactly the notes built on it in 25 of 25 generated test graphs, in about 3 milliseconds, where a plain text search found only 65% when citations were worded differently.

## The numbers

I wrote my success criteria down *before* the memory test, so I couldn't cheat.

- **Fewer clashes:** **80%** of runs finished clean with MeshAgents, against **53%** without (180 runs).
- **The hardest test**, three helpers on one codebase: **9 out of 10** finished clean, against **0 out of 10**.
- **A smarter next session:** the second session finished its job **95%** of the time, against **45%** with no memory (150 runs). A hand-kept notes file got 92%.
- **One rule hidden among 20:** found **10 out of 10** times.
- **Cost:** about the same per run (+6%), and **29% cheaper** for every clean result.

## The mistake that taught me the most

My first version made things *cost 31% more*. I dug into the recordings and found the AI was calling optional tools that the plugin already did for it, 105 and 84 times across 125 sessions. I removed those tools from the default setup, and the extra cost disappeared. Measuring cost honestly turned a bad idea into a good default.

## What it doesn't prove

I'd rather tell you than have you find out:

- My collision tests are *built* to make helpers collide. Real projects will see fewer clashes. The research I read found only 1 in 417 real merged changes had this kind of breakage.
- It's one small test project. I replicated on a stronger model (Sonnet) and it held (83% vs 33% on three levels), but only after I fixed a gap: that model edits files through shell commands, which my first version couldn't see.
- A notes file that someone keeps perfectly does about as well on memory. MeshAgents' edge is that nobody has to maintain it, and it costs a little less.
- One of my tests, where two helpers add the same stock reservation, is still not fixed.

## What I learned

1. Measure cost before you celebrate accuracy. A tool that helps but costs 30% more is a hard sell.
2. Compare against the boring alternative. "Just keep a notes file" is a tough rival.
3. Write your success criteria before the test, and report the parts that didn't work.

I built this with a lot of help from an AI coding assistant (Claude Code). It's open source, with 245 automatic tests, a read-only dashboard and a full local setup in the README.

**Try it:** [repo link] · **Demo video:** [video link] · **Site:** [site link]

#AI #DeveloperTools #FalkorDB #GraphDatabase #ClaudeCode #Hackathon

---

Short post to go with it:

> I run several AI coding sessions at once, and they kept breaking each other's work. So I built MeshAgents, a shared memory for them, on FalkorDB. In 180 test runs, 80% finished clean with it against 53% without, and a new session finished its job 95% of the time against 45% with no memory. It started out costing 31% more, and I'll tell you how I fixed that. Honest limits included. [link]
