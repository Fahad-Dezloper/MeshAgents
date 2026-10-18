# Narration script and timings

Total length 3:14.14, about 405 spoken words. Voice used for the draft: macOS Samantha at rate 170.
To record your own voice: read each line at the time shown (the picture is timed to these), or record each scene as one take and
place it at the scene start. Times are `scene start + offset`. Numbers on screen match docs/RESULTS*.md and site/facts.js.

## Hook  (starts 0:00.00, lasts 9.2 s)

| Time | Say |
|---|---|
| 0:00.55 | Picture this. You are running two AI coding helpers on the same project. |
| 0:05.41 | They are fast. But they cannot see each other. |

## The clash  (starts 0:09.17, lasts 29.7 s)

| Time | Say |
|---|---|
| 0:09.72 | Helper A changes a function. It now needs one more input: the tenant. |
| 0:14.87 | Helper B is working in another file. It still calls the function the old way. |
| 0:20.21 | Nobody tells anybody. And the test breaks. |
| 0:25.38 | The next day, a new helper starts. It knows nothing. |
| 0:29.79 | Yesterday you said: never use sqlite, the server is read-only. The new helper adds sqlite anyway. |

## Enter MeshAgents  (starts 0:38.84, lasts 10.9 s)

| Time | Say |
|---|---|
| 0:39.39 | This is MeshAgents. |
| 0:41.44 | A shared memory for AI coding helpers. |
| 0:44.95 | It runs quietly as a Claude Code plugin. You type nothing. |

## Same job, with MeshAgents  (starts 0:49.79, lasts 30.1 s)

| Time | Say |
|---|---|
| 0:50.34 | Same job, same two helpers. Without it on the left. With MeshAgents on the right. |
| 0:56.84 | Helper A's edit is written into the graph. |
| 1:00.81 | Before B edits, it gets a warning. And A is told which callers may break. |
| 1:08.30 | B adjusts its call. The tests pass. |
| 1:12.77 | The next day, the new helper is briefed on the rule. So it uses a JSON file instead. |

## The live board  (starts 1:19.90, lasts 10.3 s)

| Time | Say |
|---|---|
| 1:20.45 | You can watch it all on a live board. |
| 1:23.73 | And see exactly what the next helper is told: about 370 tokens. |

## How it works, on FalkorDB  (starts 1:30.19, lasts 31.4 s)

| Time | Say |
|---|---|
| 1:30.74 | Under the hood it is a graph, built on FalkorDB. |
| 1:35.18 | Every warning is a question asked of the graph. Who is working on this file? |
| 1:41.38 | What breaks if I change this function? |
| 1:45.32 | What was this note based on? If a note is wrong, you see everything built on it. |
| 1:52.04 | One query claims a task safely. Taking back a wrong note takes about 3 milliseconds. And git history shows which files change together. |

## The numbers  (starts 2:01.60, lasts 33.7 s)

| Time | Say |
|---|---|
| 2:02.15 | Does it work? In 180 runs, clean results went from 53 percent to 80. |
| 2:08.92 | A new session finishing its job: 45 percent with no memory, 92 with a notes file, and 95 with MeshAgents. |
| 2:18.34 | One rule hidden among 20 others: found 10 times out of 10. |
| 2:23.36 | Each clean result costs 29 percent less. A single run costs about the same. |
| 2:29.63 | And on a second, stronger model: 33 percent to 83. |

## The honest part  (starts 2:35.26, lasts 21.0 s)

| Time | Say |
|---|---|
| 2:35.81 | Now, the honest part. |
| 2:38.43 | The tests are built to make helpers collide, so real projects will see fewer clashes. |
| 2:44.56 | A notes file does about as well on memory, but someone has to keep it up. |
| 2:49.81 | And one test, two helpers adding the same stock reservation, is still not fixed. |

## Try it  (starts 2:56.22, lasts 17.9 s)

| Time | Say |
|---|---|
| 2:56.77 | Try it. Clone the repo, run meshagents doctor, and start Claude Code with the plugin. |
| 3:03.91 | MeshAgents. A shared memory for AI coding helpers. Built on FalkorDB. |
