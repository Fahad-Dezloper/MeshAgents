"""One command: voice-over, frames, encode, mux.   python3 video/build.py   (uses the repo venv: .venv/bin/python video/build.py)"""
import json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
FF = "/opt/homebrew/bin/ffmpeg"
OUT = os.path.join(HERE, "out", "MeshAgents-explainer.mp4")

def main():
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True); os.makedirs(os.path.join(HERE, "tmp"), exist_ok=True)
    subprocess.run([PY, "-B", os.path.join(HERE, "make_audio.py")], check=True, cwd=HERE)
    total = json.load(open(os.path.join(HERE, "timing.json")))["total"]
    vid = os.path.join(HERE, "tmp", "video.mp4")
    subprocess.run([PY, "-B", os.path.join(HERE, "render.py"), "video", vid], check=True, cwd=HERE)
    subprocess.run([FF, "-y", "-loglevel", "error", "-i", vid, "-i", os.path.join(HERE, "tmp", "mix.wav"), "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", f"{total:.3f}", "-movflags", "+faststart", OUT], check=True)
    print("wrote", OUT)

if __name__ == "__main__":
    main()
