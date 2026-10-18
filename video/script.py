"""Narration script: scenes -> sentences. Single source for audio, timings, subtitles and narration.md.
Each sentence: (key, spoken text, extra pause in seconds after it).
Spoken text is tuned for the text-to-speech voice; SUB_FIX turns it back into the written names for subtitles."""

VOICE = "Samantha"
RATE = 170
LEAD = 0.55      # silence before the first sentence of a scene
GAP = 0.32       # silence between sentences
CROSSFADE = 0.45

SCENES = [
    dict(id="hook", title="Hook", tail=0.7, sentences=[
        ("h1", "Picture this. You are running two AI coding helpers on the same project.", 0.15),
        ("h2", "They are fast. But they cannot see each other.", 0.5),
    ]),
    dict(id="clash", title="The clash", tail=0.9, sentences=[
        ("c1", "Helper A changes a function. It now needs one more input: the tenant.", 0.4),
        ("c2", "Helper B is working in another file. It still calls the function the old way.", 0.4),
        ("c3", "Nobody tells anybody. And the test breaks.", 2.0),
        ("c4", "The next day, a new helper starts. It knows nothing.", 0.5),
        ("c5", "Yesterday you said: never use S Q lite, the server is read-only. The new helper adds S Q lite anyway.", 1.4),
    ]),
    dict(id="enter", title="Enter MeshAgents", tail=0.8, sentences=[
        ("e1", "This is Mesh Agents.", 0.35),
        ("e2", "A shared memory for AI coding helpers.", 0.6),
        ("e3", "It runs quietly as a Claude Code plugin. You type nothing.", 0.4),
    ]),
    dict(id="split", title="Same job, with MeshAgents", tail=0.5, sentences=[
        ("w1", "Same job, same two helpers. Without it on the left. With Mesh Agents on the right.", 0.9),
        ("w2", "Helper A's edit is written into the graph.", 1.3),
        ("w3", "Before B edits, it gets a warning. And A is told which callers may break.", 2.4),
        ("w4", "B adjusts its call. The tests pass.", 1.6),
        ("w5", "The next day, the new helper is briefed on the rule. So it uses a Jason file instead.", 1.2),
    ]),
    dict(id="board", title="The live board", tail=0.7, sentences=[
        ("b1", "You can watch it all on a live board.", 0.9),
        ("b2", "And see exactly what the next helper is told: about 370 tokens.", 0.8),
    ]),
    dict(id="graph", title="How it works, on FalkorDB", tail=0.7, sentences=[
        ("f1", "Under the hood it is a graph, built on Falkor D B.", 1.0),
        ("f2", "Every warning is a question asked of the graph. Who is working on this file?", 1.5),
        ("f3", "What breaks if I change this function?", 1.5),
        ("f4", "What was this note based on? If a note is wrong, you see everything built on it.", 1.8),
        ("f5", "One query claims a task safely. Taking back a wrong note takes about 3 milliseconds. And git history shows which files change together.", 0.8),
    ]),
    dict(id="numbers", title="The numbers", tail=0.8, sentences=[
        ("n1", "Does it work? In 180 runs, clean results went from 53 percent to 80.", 1.0),
        ("n2", "A new session finishing its job: 45 percent with no memory, 92 with a notes file, and 95 with Mesh Agents.", 1.0),
        ("n3", "One rule hidden among 20 others: found 10 times out of 10.", 0.8),
        ("n4", "Each clean result costs 29 percent less. A single run costs about the same.", 0.9),
        ("n5", "And on a second, stronger model: 33 percent to 83.", 0.5),
    ]),
    dict(id="honest", title="The honest part", tail=0.7, sentences=[
        ("g1", "Now, the honest part.", 0.5),
        ("g2", "The tests are built to make helpers collide, so real projects will see fewer clashes.", 0.8),
        ("g3", "A notes file does about as well on memory, but someone has to keep it up.", 0.8),
        ("g4", "And one test, two helpers adding the same stock reservation, is still not fixed.", 0.4),
    ]),
    dict(id="try", title="Try it", tail=4.8, sentences=[
        ("t1", "Try it. Clone the repo, run mesh agents doctor, and start Claude Code with the plugin.", 1.4),
        ("t2", "Mesh Agents. A shared memory for AI coding helpers. Built on Falkor D B.", 0.2),
    ]),
]

SUB_FIX = [("Mesh Agents", "MeshAgents"), ("mesh agents", "meshagents"), ("Falkor D B", "FalkorDB"),
           ("S Q lite", "sqlite"), ("Jason file", "JSON file")]

def sub_text(s):
    for a, b in SUB_FIX:
        s = s.replace(a, b)
    return s
