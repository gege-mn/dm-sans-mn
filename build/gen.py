"""Add Mongolian/Russian Cyrillic to the DM Sans sources and write the renamed family.

    python build/gen.py            # writes sources/*.glyphs
"""
import json
import math
import os
import sys

import glyphsLib
from glyphsLib import GSComponent, GSGlyph, GSLayer, GSNode, GSPath

sys.path.insert(0, os.path.dirname(__file__))
import geom
from recipes import GLYPHS, REF_MASTER, STYLISTIC_SETS, Ctx

FAMILY = "DM Sans MN"
REPO = "https://github.com/gege-mn/dm-sans-mn"
MAKER = "L'Atelier Gege LLC"
VERSION = (1, 0)  # this family's own version, independent of upstream DM Sans
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPSTREAM = os.path.join(ROOT, "upstream", "Sans", "Source")
OUT = os.path.join(ROOT, "sources")


def to_path(contour):
    path = GSPath()
    ends = geom.oncurve(contour)
    nodes = []
    for i, seg in enumerate(contour):
        for p in seg[:-1]:
            nodes.append(GSNode((round(p[0]), round(p[1])), "offcurve"))
        node = GSNode((round(seg[-1][0]), round(seg[-1][1])), "curve" if len(seg) == 3 else "line")
        nxt = contour[(i + 1) % len(contour)]
        if len(seg) == 3 or len(nxt) == 3:
            a = seg[-2] if len(seg) == 3 else ends[i - 1]
            b = nxt[0]
            p = seg[-1]
            v1, v2 = (p[0] - a[0], p[1] - a[1]), (b[0] - p[0], b[1] - p[1])
            n1, n2 = math.hypot(*v1), math.hypot(*v2)
            node.smooth = bool(n1 and n2 and abs(v1[0] * v2[1] - v1[1] * v2[0]) / (n1 * n2) < 0.02
                               and v1[0] * v2[0] + v1[1] * v2[1] > 0)
        nodes.append(node)
    path.nodes = nodes
    path.closed = True
    return path


def anchor(font, master, name, anchor_name):
    for a in font.glyphs[name].layers[master.id].anchors:
        if a.name == anchor_name:
            return a.position.x, a.position.y
    raise KeyError(f"{name} has no {anchor_name} anchor")


def new_glyph(font, name):
    uni, _, lgroup, rgroup = GLYPHS[name]
    glyph = GSGlyph(name)
    if uni:
        glyph.unicode = uni
    glyph.leftKerningGroup = font.glyphs[lgroup].leftKerningGroup if lgroup else None
    glyph.rightKerningGroup = font.glyphs[rgroup].rightKerningGroup if rgroup else None
    font.glyphs.append(glyph)
    return glyph


def build_italic(font, shapes):
    """Italic Cyrillic: direct Latin reuses stay components of the italic Latin; every drawn
    letter is the upright drawing slanted the way upstream slanted its own (about half x-height)."""
    for name in GLYPHS:
        glyph = new_glyph(font, name)
        for m in font.masters:
            shape = shapes[name, tuple(m.axes)]
            k = math.tan(math.radians(m.italicAngle))
            y0 = m.xHeight / 2
            skew = lambda x, y: (x + k * (y - y0), y)
            contours = geom.mapped(shape.contours, lambda p: skew(*p))
            add_layer(font, glyph, m, shape, contours, skew)


def build_upright(font):
    ref = next(m for m in font.masters if m.name == REF_MASTER)
    ctxs = {m.id: Ctx(font, m, ref, geom.from_layer) for m in font.masters}
    shapes = {}
    for name, (_, recipe, _, _) in GLYPHS.items():
        glyph = new_glyph(font, name)
        for m in font.masters:
            shape = recipe(ctxs[m.id])
            shapes[name, tuple(m.axes)] = shape
            add_layer(font, glyph, m, shape, shape.contours, lambda x, y: (x, y))
    return shapes


def add_layer(font, glyph, master, shape, contours, place):
    layer = GSLayer()
    layer.layerId = layer.associatedMasterId = master.id
    layer.width = round(shape.width)
    layer.paths = [to_path(c) for c in contours]
    comps = list(shape.comps)
    for mark, x, y in shape.marks:
        ax, ay = anchor(font, master, mark, "_top")
        px, py = place(x, y)
        comps.append((mark, px - ax, py - ay))
    for cname, dx, dy in comps:
        comp = GSComponent(cname)
        comp.position = (round(dx), round(dy))
        layer.components.append(comp)
    glyph.layers.append(layer)


def finish(font, style_suffix=""):
    font.familyName = FAMILY
    font.versionMajor, font.versionMinor = VERSION
    # credits: upstream's copyright and designers stay; this version's maker is added beside them
    edits = {
        "copyrights": lambda text: f"{text}. Copyright 2026 The {FAMILY} Project Authors ({REPO})",
        "designers": lambda text: f"{text}; Cyrillic by {MAKER}",
        "manufacturers": lambda text: MAKER,
        "manufacturerURL": lambda text: REPO,
        "vendorID": lambda text: "NONE",
    }
    for prop in font.properties:
        if prop.key in edits:
            if prop._localized_values:
                prop._localized_values = {lang: edits[prop.key](text)
                                          for lang, text in prop._localized_values.items()}
            else:
                prop._value = edits[prop.key](prop._value)
    for instance in font.instances:  # upstream gives some instances their own family name
        for prop in instance.properties:
            if prop.key == "familyNames":
                prop._localized_values = {lang: text.replace("DM Sans", FAMILY)
                                          for lang, text in prop._localized_values.items()}
    for feature in font.features:
        if feature.name in STYLISTIC_SETS:
            feature.code = feature.code.rstrip() + "\n" + STYLISTIC_SETS[feature.name] + "\n"
            feature.automatic = False
    for p in font.customParameters:
        if p.name == "unicodeRanges" and 9 not in p.value:
            p.value = sorted(list(p.value) + [9])
    for prefix in font.featurePrefixes:
        if "languagesystem" in prefix.code and "cyrl" not in prefix.code:
            prefix.code = prefix.code.rstrip() + "\nlanguagesystem cyrl dflt;\n"


KERN_WEIGHTS = {"100": 20, "300": 70, "400": 84, "1000": 171}  # tool's wght -> master coordinate


def kern_now(font, master_id, left, right):
    """The kerning a pair gets today, resolving groups the way the font does."""
    table = font.kerning.get(master_id, {})
    lkeys = [left.name] + ([f"@MMK_L_{left.rightKerningGroup}"] if left.rightKerningGroup else [])
    rkeys = [right.name] + ([f"@MMK_R_{right.leftKerningGroup}"] if right.leftKerningGroup else [])
    for lk in lkeys:
        for rk in rkeys:
            if rk in table.get(lk, {}):
                return table[lk][rk]
    return 0


def apply_kerning(font):
    """Add the pair adjustments made in tools/kerning.html (build/kerning.json) on top of inherited kerning."""
    path = os.path.join(ROOT, "build", "kerning.json")
    if not os.path.exists(path):
        return 0
    with open(path, encoding="utf-8") as fh:
        pairs = json.load(fh).get("pairs", {})
    by_char = {chr(int(g.unicode, 16)): g for g in font.glyphs if g.unicode}
    coord = {v: k for k, v in KERN_WEIGHTS.items()}
    n = 0
    for pair, values in pairs.items():
        if len(pair) != 2 or pair[0] not in by_char or pair[1] not in by_char:
            continue
        left, right = by_char[pair[0]], by_char[pair[1]]
        for m in font.masters:
            delta = values.get(coord.get(m.axes[1], ""), 0)
            if delta:
                font.setKerningForPair(m.id, left.name, right.name, kern_now(font, m.id, left, right) + delta)
                n += 1
    return n


def write_config(stem):
    """gftools-builder config: upstream's, pointed at the renamed sources."""
    import yaml
    with open(os.path.join(UPSTREAM, "config.yaml")) as fh:
        cfg = yaml.safe_load(fh)
    cfg["sources"] = [stem + ".glyphs", stem + "-Italic.glyphs"]
    cfg["familyName"] = FAMILY
    cfg["stat"] = {k.replace("DMSans", stem): v for k, v in cfg["stat"].items()}
    cfg["outputDir"] = "../fonts"
    cfg["buildOTF"] = False  # variable and static TTF only; build.sh adds WOFF2 of the variable fonts
    cfg["buildWebfont"] = False
    with open(os.path.join(OUT, "config.yaml"), "w") as fh:
        yaml.safe_dump(cfg, fh, sort_keys=False)


def main():
    os.makedirs(OUT, exist_ok=True)
    stem = FAMILY.replace(" ", "")
    font = glyphsLib.GSFont(os.path.join(UPSTREAM, "DMSans.glyphs"))
    shapes = build_upright(font)
    italic = glyphsLib.GSFont(os.path.join(UPSTREAM, "DMSans-Italic.glyphs"))
    build_italic(italic, shapes)
    for f, name in ((font, stem), (italic, stem + "-Italic")):
        apply_kerning(f)
        finish(f)
        out = os.path.join(OUT, name + ".glyphs")
        f.save(out)
        print("wrote", out, len(f.glyphs), "glyphs")
    write_config(stem)


if __name__ == "__main__":
    main()
