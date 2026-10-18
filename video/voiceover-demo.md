# Screen demo: cue sheet for the narrator

Video: `MeshAgents-demo.mp4` (58 s, no audio). Left: three terminals. Right: the live board. Waiting time is cut where the orange "Waiting time cut" tag flashes.
Beats 1 to 6 are recordings of three Claude Code sessions (Haiku) on a copy of the sample project; the board is the real dashboard from the same run.

| Time | On screen | Say (simple words) |
|---|---|---|
| 0:00-0:04 | Empty board, "Waiting for the first helper". Terminal 1 waiting. | "Here is an empty board. No helper is working yet." |
| 0:04-0:12 | Prompt 1 is typed in Terminal 1 and sent. Helper 1 appears on the board; feed: rule noted, got a task, started. | "Helper 1 gets a job. It also hears a rule: never use sqlite. The board shows it at once." |
| 0:12-0:24 | Prompt 2 in Terminal 2. Helper 2 appears; feed shows what it was told. Helper 1 finishes (Done). | "Helper 2 starts a second job while Helper 1 is still working. It is told what is going on." |
| 0:24-0:29 | Terminal 2 shows the orange heads-up about api.py; feed says Helper 2 was told another helper already changed it. | "Before Helper 2 edits a file that Helper 1 changed, it gets a heads-up. No clash." |
| 0:29-0:40 | Prompt 3 in Terminal 3, a new session. Feed: started knowing 1 rule. Terminal 3 shows "never use sqlite", then "Saved orders to a JSON file". | "A new helper starts the next day. It already knows the rule, so it saves to a file, not sqlite." |
| 0:40-0:49 | Next helper view: the rule and recent changes. | "This is exactly what the next helper will be told." |
| 0:49-0:58 | Stats: 80% clean (was 53%), 95%, 29% less cost, 10/10, 2 models. | "Fewer clashes, a smarter next helper, and lower cost per good result. Tested on 330 runs." |

About 100 words in total. The numbers match docs/RESULTS.md and docs/RESULTS-RELAY.md.
