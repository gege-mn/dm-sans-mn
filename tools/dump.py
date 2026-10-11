import sys, glyphsLib
f = glyphsLib.GSFont("upstream/Sans/Source/DMSans.glyphs")
mname = sys.argv[1]
m = [m for m in f.masters if m.name == mname][0]
for gn in sys.argv[2:]:
    l = f.glyphs[gn].layers[m.id]
    print(f"== {gn} w={l.width} anchors={[(a.name,int(a.position.x),int(a.position.y)) for a in l.anchors]} comps={[(c.name) for c in l.components]}")
    for p in l.paths:
        print("  ", " ".join(f"{int(n.position.x)},{int(n.position.y)}{'' if n.type=='offcurve' else n.type[0]+('s' if n.smooth else '')}" for n in p.nodes))
