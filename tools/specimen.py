"""Render text with the built variable font: specimen.py OUT.png SIZE "wght,opsz;wght,opsz" [--italic] line...
"""
import sys
from PIL import Image, ImageDraw, ImageFont

args = sys.argv[1:]
italic = "--italic" in args
args = [a for a in args if a != "--italic"]
out, size, styles, lines = args[0], int(args[1]), args[2], args[3:]
SS = 4  # draw oversized and scale down: PIL snaps each glyph to a whole pixel, which fakes uneven spacing
final, size = size, size * SS
path = "fonts/variable/DMSansMN-Italic[opsz,wght].ttf" if italic else "fonts/variable/DMSansMN[opsz,wght].ttf"
rows = []
for st in styles.split(";"):
    wght, opsz = map(float, st.split(","))
    f = ImageFont.truetype(path, size)
    order = [a["name"] for a in f.get_variation_axes()]
    f.set_variation_by_axes([opsz if "ptical" in str(n) else wght for n in order])
    for ln in lines:
        rows.append((f, ln))
W = max(int(f.getlength(ln)) for f, ln in rows) + 40 * SS
lh = int(size * 1.45)
im = Image.new("RGB", (W, lh * len(rows) + 20 * SS), "white")
d = ImageDraw.Draw(im)
for i, (f, ln) in enumerate(rows):
    d.text((20 * SS, 10 * SS + i * lh), ln, font=f, fill="black")
im = im.resize((im.width // SS, im.height // SS), Image.LANCZOS)
im.save(out)
print(out, im.size)
