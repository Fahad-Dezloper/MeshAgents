# 60-second cut: voice-over cue sheet

Video: `MeshAgents-60s.mp4` (58.5 s, no audio). Pace about 2.3 words per second. About 120 words in total.

| Time | On screen | Say (simple words) |
|---|---|---|
| 0:00-0:05 | "Two AI helpers. One project." Helpers A and B, a crossed-out eye between them | "Say you run two AI helpers on one project. They cannot see each other." (14) |
| 0:05-0:15 | Helper A adds a new input to a function in shop/db.py. Helper B still calls it the old way in shop/api.py. Red FAILED, TypeError. "Nobody told anybody." | "Helper A changes a function. Helper B does not know, and calls it the old way. Nobody tells anybody. The test breaks." (23) |
| 0:15-0:22 | "The next day". New helper C knows nothing. The rule "never use sqlite, the server is read-only" is greyed out. C adds sqlite, red cross | "Next day, a new helper starts. It never heard the rule: no sqlite, the server is read-only. So it adds sqlite anyway." (23) |
| 0:22-0:28 | MeshAgents appears, a shared notebook joins both helpers. Beats: Warns, Remembers, Hands over. "Built on FalkorDB" | "So we built MeshAgents, a shared notebook for your helpers. It warns, it remembers, and it hands over." (18) |
| 0:28-0:37 | Graph scene: tasks, files, function, notes joined by TOUCHES, CALLS, ABOUT, BASED_ON. Questions: "Who is working on this file?", "What breaks if I change this function?", "What was this note based on?" Wrong note turns red with everything built on it. "Built on FalkorDB" | "Under the hood it is a graph in FalkorDB. Every warning is just a question the graph can answer: who is in this file, what breaks if I change this, and what was this note based on." (38) |
| 0:37-0:51 | "What you get": three big cards pop in one by one and then hold still (about 5 s). 80% of runs finish clean (was 53%). 95% of next sessions finish the job (was 45% with no memory). 29% less cost per clean result ($0.0159 to $0.0113). Footer: measured in 330 real test runs, tests built to make helpers collide | "Three numbers. Fewer clashes: eight in ten runs finish clean, up from five. The next helper already knows the job: ninety-five percent, up from forty-five. And every good result costs twenty-nine percent less. Measured in three hundred thirty real test runs." (40) |
| 0:51-0:58.5 | End card: MeshAgents, tagline, three commands, repo URL, WeMakeDevs x FalkorDB Graph Hacks, Track 2 | "Try it. Clone the repo, run mesh agents doctor, and start Claude Code with the plugin. The link is on screen." (21) |

The numbers match docs/RESULTS.md (rounds 6 and 7) and docs/RESULTS-RELAY.md.
