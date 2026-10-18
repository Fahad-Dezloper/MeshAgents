import sys, glob, os
from PIL import Image, ImageDraw
files = sys.argv[2:]; out = sys.argv[1]
n = len(files); cols = 2; rows = (n + 1) // 2
sh = Image.new("RGB", (1920, 540 * rows), (0, 0, 0))
for i, f in enumerate(files):
    im = Image.open(f).resize((960, 540), Image.LANCZOS)
    sh.paste(im, ((i % 2) * 960, (i // 2) * 540))
    ImageDraw.Draw(sh).text(((i % 2) * 960 + 8, (i // 2) * 540 + 8), os.path.basename(f), fill=(255, 255, 0))
sh.save(out)
