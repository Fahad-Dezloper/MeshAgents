# Record the demo (one page)

## Before you start
- Docker Desktop is running. Notifications off. Screen 1920x1080. OBS: one Display Capture, 30 fps.
- Layout: two terminals stacked on the LEFT half (font size 20 to 22, dark theme), the dashboard on the RIGHT half (browser zoom 150 percent, dark mode).

## The six steps
1. **Start the kit.** In a plain terminal run `meshagents demo` (from the repo: `.venv/bin/meshagents demo`). It opens the dashboard and prints the three prompts. Press Record.
   Say: "This is a shared notebook for AI coding agents."
2. **Open two terminals.** In each: `cd ~/meshagents-demo && claude --plugin-dir <repo>/plugin` (the kit prints the exact line).
   Say: "Two agents, same project."
3. **Prompt 1 in terminal 1.** Paste the first prompt, press Enter.
   Say: "Agent one changes a function. Watch the board. It updates by itself."
4. **Prompt 2 in terminal 2**, while agent one is still working.
   Say: "Agent two needs that function. It gets warned before it breaks anything."
5. **Prompt 3 in a NEW third terminal**, after both finish.
   Say: "A brand new agent. Nobody told it the rule. It already knows: no sqlite."
6. **Show the memory view.** Click Memory in the dashboard.
   Say: "Everything is remembered here. Next, the numbers." Then show `MeshAgents-stats.png`.

Optional: the FalkorDB Browser at http://localhost:3000 (graph shown by `meshagents demo status`) shows the same notes as a graph.

## Safety
- Claude Code will ask permission before running commands. For this demo say **Yes** to edits and to running the tests.
- If Claude ever offers to **install** something (a database, a package), say **No**, and carry on. The prompts are written so this should not happen, but it is a real AI, so watch the screen.

## If something fails
- "FalkorDB is not running": run `docker compose up -d` in the repo, then `meshagents demo` again.
- A agent answers oddly or the board looks wrong: run `meshagents demo reset` and start the steps again.
- Dashboard blank: `meshagents demo status`; if it is down, run `meshagents demo`.
- A prompt takes too long (over a minute): stop it with Ctrl-C and re-run the step; keep the take, cut later.
- Nothing shows in the warning: check you started the terminals with the plugin line, not plain `claude`.
