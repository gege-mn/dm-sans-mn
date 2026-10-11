"""Render glyph rows straight from a .glyphs source: show.py SRC OUT.png SIZE "master1|master2" "A B C" ["row2" ...]"""
import sys, glyphsLib, numpy as np
from PIL import Image, ImageDraw
from fontTools.pens.freetypePen import FreeTypePen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.recordingPen import DecomposingRecordingPen

_cache = {}
def load(path):
    if path not in _cache:
        _cache[path] = glyphsLib.GSFont(path)
    return _cache[path]

def draw_layer(font, layer, pen, t=(1,0,0,1,0,0)):
    from fontTools.misc.transform import Transform
    T = Transform(*t)
    for p in layer.paths:
        nodes = list(p.nodes)
        n = len(nodes)
        # find first oncurve
        start = next(i for i, nd in enumerate(nodes) if nd.type != "offcurve")
        seq = nodes[start:] + nodes[:start]
        pt = lambda nd: T.transformPoint((nd.position.x, nd.position.y))
        pen.moveTo(pt(seq[0]))
        buf = []
        for nd in seq[1:] + [seq[0]]:
            if nd.type == "offcurve":
                buf.append(pt(nd))
            elif buf:
                pen.curveTo(*buf, pt(nd)); buf = []
            else:
                pen.lineTo(pt(nd))
        pen.closePath()
    for c in layer.components:
        base = font.glyphs[c.name].layers[layer.associatedMasterId or layer.layerId]
        ct = Transform(*c.transform)
        draw_layer(font, base, pen, tuple(T.transform(ct)))

def render(src, out, size, masters, rows):
    font = load(src)
    scale = size / 1000
    imgs = []
    for mname in masters:
        m = [m for m in font.masters if m.name == mname][0]
        for row in rows:
            names = row.split()
            adv = sum(font.glyphs[n].layers[m.id].width for n in names)
            W = int(adv * scale) + 40; H = int(size * 1.25)
            pen = FreeTypePen(None)
            x = 20 / scale
            for n in names:
                l = font.glyphs[n].layers[m.id]
                draw_layer(font, l, pen, (1,0,0,1,x,280))
                x += l.width
            arr = pen.array(width=W, height=H, transform=(scale,0,0,scale,0,0), contain=False)
            im = Image.fromarray((255 - arr * 255).astype("uint8"), "L").convert("RGB")
            d = ImageDraw.Draw(im)
            for yv, col in ((0,(255,0,0)), (m.xHeight,(0,160,255)), (m.capHeight,(0,200,0)), (m.descender,(200,200,200))):
                yy = H - int((yv + 280) * scale)
                for xx in range(0, W, 6): d.point((xx, yy), fill=col)
            d.text((2, 2), mname, fill=(120,120,120))
            imgs.append(im)
    W = max(i.width for i in imgs); H = sum(i.height for i in imgs)
    sheet = Image.new("RGB", (W, H), "white"); y = 0
    for i in imgs: sheet.paste(i, (0, y)); y += i.height
    sheet.save(out); print(out, sheet.size)

if __name__ == "__main__":
    render(sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4].split("|"), sys.argv[5:])
