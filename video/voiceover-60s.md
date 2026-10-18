# 60-second cut: voice-over cue sheet

Video: `MeshAgents-60s.mp4` (58.5 s, no audio). Pace about 2.3 words per second. About 135 words in total.

| Time | On screen | Say (simple words) |
|---|---|---|
| 0:00-0:05 | "Two AI helpers. One project." Helpers A and B, a crossed-out eye between them | "Say you run two AI helpers on one project. They cannot see each other." (14) |
| 0:05-0:15 | Helper A adds a new input to a function in shop/db.py. Helper B still calls it the old way in shop/api.py. Red FAILED, TypeError. "Nobody told anybody." | "Helper A changes a function. Helper B does not know, and calls it the old way. Nobody tells anybody. The test breaks." (23) |
| 0:15-0:22 | "The next day". New helper C knows nothing. The rule "never use sqlite, the server is read-only" is greyed out. C adds sqlite, red cross | "Next day, a new helper starts. It never heard the rule: no sqlite, the server is read-only. So it adds sqlite anyway." (23) |
| 0:22-0:28 | MeshAgents appears, a shared notebook joins both helpers. Beats: Warns, Remembers, Hands over. "Built on FalkorDB" | "So we built MeshAgents, a shared notebook for your helpers. It warns, it remembers, and it hands over." (18) |
| 0:28-0:37 | Graph scene: tasks, files, function, notes joined by TOUCHES, CALLS, ABOUT, BASED_ON. Questions: "Who is working on this file?", "What breaks if I change this function?", "What was this note based on?" Wrong note turns red with everything built on it. "Built on FalkorDB" | "Under the hood it is a graph in FalkorDB. Every warning is just a question the graph can answer: who is in this file, what breaks if I change this, and what was this note based on." (38) |
| 0:37-0:51 | "What you get": a bento grid. Big box: Fewer clashes, 80% of runs finish clean (was 53%). Four small boxes pop in one by one: 95% the next helper already knows the job (was 45%); 29% less cost for every good result; 10/10 hidden rules found, even among 20; 2 models. All boxes hold still from about 0:41. Footer: 330 real test runs | "Here is what you get. Fewer clashes: eight in ten runs finish clean. The next helper already knows the job. Every good result costs twenty-nine percent less. It finds the one rule that matters, ten times out of ten, and works on two AI models. Measured in three hundred thirty real test runs." (52, trim to fit 14 s if you speak slowly) |
| 0:51-0:58.5 | End card: MeshAgents, tagline, three commands, repo URL, WeMakeDevs x FalkorDB Graph Hacks, Track 2 | "Try it. Clone the repo, run mesh agents doctor, and start Claude Code with the plugin. The link is on screen." (21) |

The numbers match docs/RESULTS.md (rounds 6 and 7) and docs/RESULTS-RELAY.md.
