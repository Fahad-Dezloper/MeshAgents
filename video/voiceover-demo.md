# Screen demo: what to say (matches the teleprompter)

Video: `MeshAgents-demo.mp4` (58 s, silent). The same words are in `teleprompter/teleprompter.html`.

| From | On screen | Say |
|---|---|---|
| 0:00 | Empty board | Hi, this is my submission for the FalkorDB hackathon. My name is Fahad, and here is what I built: MeshAgents. |
| 0:06 | Agent 1 starts | MeshAgents is a shared notebook for AI agents working on the same project. |
| 0:11 | Agent 1 job and rule; agent 2 starts | The problem: agents overwrite each other's work. And every new agent starts blank. It must reread the whole project before changing anything, and that burns tokens. |
| 0:21 | Agent 2 gets the heads-up | So I built MeshAgents on a FalkorDB graph. It stores who is working on what, every change, and every rule. Before agent two edits agent one's file, it gets a warning. No clash. |
| 0:33 | A brand new agent knows the rule | Then a brand new agent starts, and it already knows our rule: no sqlite. It reads one short note, not the whole project. |
| 0:43 | What the new agent was told | Setup is easy. Install the plugin, and it runs by itself. You do nothing. |
| 0:50 | The numbers | In 330 test runs, clean runs went from 53 to 80 percent, and each good result cost 29 percent less. Thanks for watching! |

About 152 words: intro, what it is, the problem, what I built and how it helps, it remembers, easy setup, results.
