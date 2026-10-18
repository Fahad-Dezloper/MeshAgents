"""Writes narration.md (script with scene timings) from timing.json."""
import json, os
from script import SCENES, sub_text
HERE = os.path.dirname(os.path.abspath(__file__))
T = json.load(open(f"{HERE}/timing.json"))
def mmss(x): return f"{int(x // 60)}:{x % 60:05.2f}"
words = sum(len(sub_text(t).split()) for sc in SCENES for _, t, _ in sc["sentences"])
out = [f"# Narration script and timings\n",
       f"Total length {mmss(T['total'])}, about {words} spoken words. Voice used for the draft: macOS Samantha at rate 170.",
       "To record your own voice: read each line at the time shown (the picture is timed to these), or record each scene as one take and",
       "place it at the scene start. Times are `scene start + offset`. Numbers on screen match docs/RESULTS*.md and site/facts.js.\n"]
for sc, ts in zip(SCENES, T["scenes"]):
    out.append(f"## {ts['title']}  (starts {mmss(ts['start'])}, lasts {ts['length']:.1f} s)\n")
    out.append("| Time | Say |\n|---|---|")
    for s in ts["sentences"]:
        out.append(f"| {mmss(ts['start'] + s['t'])} | {s['text']} |")
    out.append("")
open(f"{HERE}/narration.md", "w").write("\n".join(out))
print("ok", words)
