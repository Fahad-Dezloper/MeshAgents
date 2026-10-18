"""Voice-over: one file per sentence with macOS `say`, durations via ffprobe, timeline + timing.json, mixed track."""
import json, os, subprocess, wave, sys
import numpy as np
from script import *

HERE = os.path.dirname(os.path.abspath(__file__))
TMP = os.path.join(HERE, "tmp"); AUD = os.path.join(TMP, "audio")
FFMPEG = "/opt/homebrew/bin/ffmpeg"; SR = 44100

def run(*a):
    subprocess.run(a, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def make_sentence(key, text):
    aiff, wav = f"{AUD}/{key}.aiff", f"{AUD}/{key}.wav"
    if not os.path.exists(wav) or os.environ.get("REDO_VOICE"):
        run("say", "-v", VOICE, "-r", str(RATE), "-o", aiff, text)
        run(FFMPEG, "-y", "-i", aiff, "-ar", str(SR), "-ac", "1", "-sample_fmt", "s16", wav)
    with wave.open(wav) as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768

def main():
    os.makedirs(AUD, exist_ok=True)
    t = 0.0; scenes = []; chunks = []
    for sc in SCENES:
        start = t; cur = LEAD; sents = []
        for key, text, pad in sc["sentences"]:
            x = make_sentence(key, text); d = len(x) / SR
            sents.append(dict(key=key, text=sub_text(text), t=round(cur, 3), dur=round(d, 3)))
            chunks.append((start + cur, x))
            cur += d + GAP + pad
        length = cur - GAP + sc["tail"]
        scenes.append(dict(id=sc["id"], title=sc["title"], start=round(start, 3), length=round(length, 3), sentences=sents))
        t += length
    total = t
    json.dump(dict(total=round(total, 3), crossfade=CROSSFADE, scenes=scenes), open(f"{HERE}/timing.json", "w"), indent=1)
    n = int((total + 0.5) * SR)
    voice = np.zeros(n, np.float32)
    for st, x in chunks:
        i = int(st * SR); voice[i:i + len(x)] += x
    # ambient pad: soft chord with slow swell, about 28 dB under the voice
    tt = np.arange(n) / SR
    pad = sum(np.sin(2 * np.pi * f * tt + p) * a for f, p, a in
              [(110.0, 0, 1.0), (164.81, 1.3, 0.7), (220.0, 2.1, 0.6), (277.18, 0.4, 0.4), (329.63, 2.9, 0.3)])
    pad *= (0.65 + 0.35 * np.sin(2 * np.pi * tt / 11.0))
    fade = np.minimum(1, np.minimum(tt / 3.0, (total - tt).clip(0) / 3.0))
    pad = pad * fade
    rms = lambda v: float(np.sqrt(np.mean(v ** 2)) + 1e-9)
    mix = voice + pad * (rms(voice[voice != 0]) * 10 ** (-28 / 20) / rms(pad))
    pcm = (np.clip(mix, -1, 1) * 32767).astype(np.int16)
    with wave.open(f"{TMP}/mix_raw.wav", "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
    run(FFMPEG, "-y", "-i", f"{TMP}/mix_raw.wav", "-af", "loudnorm=I=-16:TP=-1.5:LRA=9", "-ar", "44100", f"{TMP}/mix.wav")
    print("total", round(total, 1), "s")
    for s in scenes: print(s["id"], s["start"], s["length"])

if __name__ == "__main__":
    main()
