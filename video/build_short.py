"""Silent short cut: .venv/bin/python video/build_short.py  ->  video/out/MeshAgents-60s.mp4 (no audio)"""
import os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); os.makedirs(f"{HERE}/out", exist_ok=True)
subprocess.run([sys.executable, "-B", f"{HERE}/render_short.py", "video", f"{HERE}/out/MeshAgents-60s.mp4"], check=True, cwd=HERE)
