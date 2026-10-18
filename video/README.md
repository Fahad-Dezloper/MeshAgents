# Explainer video

Renders the explainer video (1920x1080, 30 fps, about 3 minutes) with Pillow, numpy, macOS `say` and ffmpeg.

Re-render everything with one command (needs macOS, `/opt/homebrew/bin/ffmpeg`, and `pillow numpy` in the venv):

    .venv/bin/python video/build.py

The result is `video/out/MeshAgents-explainer.mp4`. Takes about 8 minutes on 10 cores.

- `script.py`: the narration, scene by scene (edit the words here). Voice and rate are set at the top.
- `make_audio.py`: one voice file per sentence, scene lengths from the voice lengths, quiet background pad, loudness normalised. Writes `timing.json`.
- `render.py`, `gfx.py`, `scenes_a.py`, `scenes_b.py`: the picture. `render(t)` returns one frame, so frames are independent.
- `narration.md`: the script with timings, for recording your own voice (`make_narration.py` regenerates it).
- Preview single frames: `.venv/bin/python video/render.py frames 12 45.5 90` (PNG files in `video/tmp/prev`).
- To use your own voice: replace `video/tmp/mix.wav` with your recording (same length as `timing.json` total) and run only the mux step, or change the timings in `script.py` to match your take.
