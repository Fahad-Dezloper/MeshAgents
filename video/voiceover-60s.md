# 60-second cut: voice-over cue sheet

Video: `MeshAgents-60s.mp4` (57.5 s, no audio). Pace about 2.3 words per second. About 125 words in total.

| Time | On screen | Say (simple words) |
|---|---|---|
| 0:00-0:05 | "Two AI helpers. One project." Helpers A and B, a crossed-out eye between them | "Say you run two AI helpers on one project. They cannot see each other." (14) |
| 0:05-0:17 | Helper A adds a new input to a function in shop/db.py. Helper B still calls it the old way in shop/api.py. Red FAILED, TypeError. "Nobody told anybody." | "Helper A changes a function, so it needs one more input. Helper B does not know, and still calls it the old way. Nobody tells anybody. The test breaks." (30) |
| 0:17-0:25 | "The next day". New helper C knows nothing. The rule "never use sqlite, the server is read-only" is greyed out. C adds sqlite, red cross | "The next day, a new helper starts. Yesterday you told the first one: never use sqlite. This one never heard it, and adds sqlite anyway." (26) |
| 0:25-0:33 | MeshAgents appears, a shared notebook joins both helpers. Beats: Warns, Remembers, Hands over. "Built on FalkorDB", graph dots light up | "So we built MeshAgents. It is a shared notebook for your helpers. It warns them before a clash, remembers what changed, and hands it all to the next helper. It is built on FalkorDB." (36) |
| 0:33-0:50 | "Measured, not promised": the stats board counts up, then holds (about 10 s). Fine print about tests built to collide | "Does it work? Clean runs went from 53 to 80 percent. A new session finishes its job 95 percent of the time, with a plain notes file at 92 and no memory at 45. Each clean result costs 29 percent less. The tests make helpers collide on purpose, so real projects will see fewer clashes." (50, you can stop earlier, the board stays) |
| 0:50-0:57 | End card: MeshAgents, tagline, three commands, repo URL, WeMakeDevs x FalkorDB Graph Hacks, Track 2 | "Try it. Clone the repo, run mesh agents doctor, and start Claude Code with the plugin. The link is on screen." (21) |

The numbers match docs/RESULTS.md (rounds 6 and 7) and docs/RESULTS-RELAY.md.
