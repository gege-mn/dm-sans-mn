"""Render text with the built variable font: specimen.py OUT.png SIZE "wght,opsz;wght,opsz" [--italic] line...
"""
import sys
from PIL import Image, ImageDraw, ImageFont

args = sys.argv[1:]
italic = "--italic" in args
args = [a for a in args if a != "--italic"]
out, size, styles, lines = args[0], int(args[1]), args[2], args[3:]
path = "fonts/variable/DMSansMN-Italic[opsz,wght].ttf" if italic else "fonts/variable/DMSansMN[opsz,wght].ttf"
rows = []
for st in styles.split(";"):
    wght, opsz = map(float, st.split(","))
    f = ImageFont.truetype(path, size)
    order = [a["name"] for a in f.get_variation_axes()]
    f.set_variation_by_axes([opsz if "ptical" in str(n) else wght for n in order])
    for ln in lines:
        rows.append((f, ln))
W = max(int(f.getlength(ln)) for f, ln in rows) + 40
lh = int(size * 1.45)
im = Image.new("RGB", (W, lh * len(rows) + 20), "white")
d = ImageDraw.Draw(im)
for i, (f, ln) in enumerate(rows):
    d.text((20, 10 + i * lh), ln, font=f, fill="black")
im.save(out)
print(out, im.size)
