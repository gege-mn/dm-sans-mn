"""First-pass kerning for Cyrillic pairs that inherit none, calibrated on upstream's Latin kerning.

    .venv/bin/python tools/autokern.py            # report only
    .venv/bin/python tools/autokern.py --write    # merge into build/kerning.json (keeps pairs already there)

For a pair, the white space between the two letters is measured band by band (wide-open bands are
capped so the hollow under a Г or T arm cannot dominate) and compared with the space between two
straight stems. How strongly that difference should turn into kerning is not guessed: it is fitted
to the pairs upstream kerned by hand in the Latin, per weight.
"""
import json
import os
import sys

import glyphsLib
import numpy as np
from fontTools.pens.freetypePen import FreeTypePen

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "build"))
sys.path.insert(0, os.path.dirname(__file__))
from gen import KERN_WEIGHTS, ROOT, kern_now
from show import draw_layer

LATIN_UC, LATIN_LC = "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"
CYR_UC = "АБВГДЕЖЗИЙКЛМНОӨПРСТУҮФХЦЧШЩЪЫЬЭЮЯ"
CYR_LC = "абвгдежзийклмноөпрстуүфхцчшщъыьэюя"
SCALE = 0.25  # raster resolution: 4 font units per pixel
MIN_KERN = 12  # ignore anything smaller than this


def profiles(font, master, chars):
    """Per glyph: left and right margins for every band from the baseline up, plus its height class."""
    by_char = {chr(int(g.unicode, 16)): g for g in font.glyphs if g.unicode}
    rows = int(master.capHeight * SCALE)
    out = {}
    for ch in chars:
        glyph = by_char[ch]
        layer = glyph.layers[master.id]
        pen = FreeTypePen(None)
        draw_layer(font, layer, pen, (1, 0, 0, 1, 200, 0))
        width = int((layer.width + 400) * SCALE)
        arr = pen.array(width=width, height=rows, transform=(SCALE, 0, 0, SCALE, 0, 0), contain=False)[::-1] > 0.5
        left = np.full(rows, np.nan)
        right = np.full(rows, np.nan)
        for y in range(rows):
            xs = np.flatnonzero(arr[y])
            if len(xs):
                left[y] = xs[0] / SCALE - 200
                right[y] = layer.width - (xs[-1] + 1) / SCALE + 200
        top = master.capHeight if ch.isupper() else master.xHeight
        out[ch] = (glyph, left, right, int(top * SCALE))
    return out


def measure(prof, a, b, upper_ref):
    """(looseness, closest approach) of a pair, both relative to two straight stems of that case."""
    _, _, right, top_a = prof[a]
    _, left, _, top_b = prof[b]
    n = min(top_a, top_b)
    gap = right[:n] + left[:n]
    stem = upper_ref[a.isupper() and b.isupper()]
    capped = np.where(np.isnan(gap), 2 * stem, np.minimum(gap, 2 * stem))
    return float(capped.mean()) - stem, float(np.nanmin(gap)) - stem


def predict(loose, closest, slope, floor, stem):
    """Tighten in proportion to looseness, but never bring the nearest points closer than `floor` x stem gap."""
    room = closest + (1 - floor) * stem
    return -min(max(slope * loose, 0), max(room, 0))


def main():
    font = glyphsLib.GSFont(os.path.join(ROOT, "sources", "DMSansMN.glyphs"))
    result, report = {}, []
    latin = LATIN_UC + LATIN_LC
    for wght, coord in KERN_WEIGHTS.items():
        master = next(m for m in font.masters if m.axes == [100, coord])
        prof = profiles(font, master, latin + CYR_UC + CYR_LC)
        mid = lambda ch: float(prof[ch][2][5] + prof[ch][1][5])
        stems = {True: mid("H"), False: mid("n")}
        data = []
        for a in latin:
            for b in latin:
                if a.islower() and b.isupper():
                    continue
                k = kern_now(font, master.id, prof[a][0], prof[b][0])
                if k <= 0:  # the model only tightens, so fit it on pairs upstream left alone or tightened
                    data.append((*measure(prof, a, b, stems), stems[a.isupper() and b.isupper()], k))
        best = None
        for slope in np.arange(0.2, 1.01, 0.05):
            for floor in np.arange(0.3, 1.01, 0.05):
                err = np.sqrt(np.mean([(predict(l, c, slope, floor, st) - k) ** 2 for l, c, st, k in data]))
                if best is None or err < best[0]:
                    best = (float(err), float(slope), float(floor))
        err, slope, floor = best
        base = np.sqrt(np.mean([k ** 2 for *_, k in data]))
        report.append(f"wght {wght}: fitted on {len(data)} Latin pairs, slope {slope:.2f}, floor {floor:.2f}, "
                      f"typical miss {err:.1f} units (doing nothing would miss by {base:.1f})")
        if wght == "400":
            for pair in ("TA", "TH", "AV", "LT", "HH", "To", "Ty", "FA", "PA", "ГН", "ГД", "ГА", "ТД", "УЛ", "ГЛ", "РД", "Уд", "АЧ"):
                l, c = measure(prof, pair[0], pair[1], stems)
                st = stems[pair[0].isupper() and pair[1].isupper()]
                report.append(f"   {pair}: model {predict(l, c, slope, floor, st):6.0f}   font now {kern_now(font, master.id, prof[pair[0]][0], prof[pair[1]][0]):5.0f}")
        for a in CYR_UC + CYR_LC:
            for b in CYR_UC + CYR_LC:
                if a.islower() and b.isupper():
                    continue
                if kern_now(font, master.id, prof[a][0], prof[b][0]):
                    continue  # already kerned through an inherited group
                st = stems[a.isupper() and b.isupper()]
                k = predict(*measure(prof, a, b, stems), slope, floor, st)
                if k <= -MIN_KERN:
                    result.setdefault(a + b, {})[wght] = int(round(k / 5) * 5)
    print("\n".join(report))
    ranked = sorted(result.items(), key=lambda kv: kv[1].get("400", 0))
    print(len(result), "pairs. Strongest at Regular:", ", ".join(f"{p} {v.get('400', 0)}" for p, v in ranked[:40]))
    if "--write" in sys.argv:
        path = os.path.join(ROOT, "build", "kerning.json")
        existing = json.load(open(path, encoding="utf-8")).get("pairs", {}) if os.path.exists(path) else {}
        merged = {**result, **existing}  # hand-set pairs win
        with open(path, "w", encoding="utf-8") as fh:
            json.dump({"pairs": merged}, fh, ensure_ascii=False, indent=1, sort_keys=True)
            fh.write("\n")
        print("wrote", path, len(merged), "pairs")


if __name__ == "__main__":
    main()
