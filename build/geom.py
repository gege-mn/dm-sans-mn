"""Small outline toolkit used by the Cyrillic recipes.

A contour is a closed list of segments. A segment is a tuple of points:
one point for a line, three (two handles and the end point) for a cubic.
The contour starts at the end point of its last segment.
"""
import math


def from_layer(layer):
    contours = []
    for path in layer.paths:
        nodes = list(path.nodes)
        first = next(i for i, n in enumerate(nodes) if n.type != "offcurve")
        seq = nodes[first + 1:] + nodes[:first + 1]
        segs, buf = [], []
        for n in seq:
            p = (float(n.position.x), float(n.position.y))
            if n.type == "offcurve":
                buf.append(p)
            else:
                segs.append(tuple(buf) + (p,))
                buf = []
        contours.append(segs)
    return contours


def points(contour):
    return [p for seg in contour for p in seg]


def oncurve(contour):
    return [seg[-1] for seg in contour]


def bbox(contours):
    if contours and isinstance(contours[0], tuple):
        contours = [contours]
    xs = [p[0] for c in contours for p in oncurve(c)]
    ys = [p[1] for c in contours for p in oncurve(c)]
    return min(xs), min(ys), max(xs), max(ys)


def area(contour):
    pts = points(contour)
    return sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(pts, pts[1:] + pts[:1])) / 2


def reverse(contour):
    n = len(contour)
    ends = oncurve(contour)
    out = []
    for i in reversed(range(n)):
        seg = contour[i]
        prev = ends[i - 1]
        out.append((seg[1], seg[0], prev) if len(seg) == 3 else (prev,))
    return out


def ccw(contour):
    return contour if area(contour) > 0 else reverse(contour)


def cw(contour):
    return contour if area(contour) < 0 else reverse(contour)


def mapped(contours, fn):
    return [[tuple(fn(p) for p in seg) for seg in c] for c in contours]


def affine(contours, a=1, b=0, c=0, d=1, e=0, f=0):
    out = mapped(contours, lambda p: (a * p[0] + c * p[1] + e, b * p[0] + d * p[1] + f))
    if a * d - b * c < 0:
        out = [reverse(k) for k in out]
    return out


def shift(contours, dx=0, dy=0):
    return affine(contours, e=dx, f=dy)


def mirror_x(contours, axis):
    return affine(contours, a=-1, e=2 * axis)


def flip_y(contours, axis):
    return affine(contours, d=-1, f=2 * axis)


def pl(*knots):
    """Piecewise-linear map through (source, target) knots, extrapolating the end slopes."""
    knots = sorted(knots)

    def fn(v):
        for (s0, t0), (s1, t1) in zip(knots, knots[1:]):
            if v <= s1 or (s1, t1) == knots[-1]:
                if s1 == s0:
                    return t0
                return t0 + (v - s0) * (t1 - t0) / (s1 - s0)
    return fn


def remap(contours, fx=None, fy=None):
    """Stroke-preserving rescale: move stems and bars rigidly, stretch only what lies between."""
    ident = lambda v: v
    fx, fy = fx or ident, fy or ident
    return mapped(contours, lambda p: (fx(p[0]), fy(p[1])))


def poly(*pts):
    return ccw([(tuple(map(float, p)),) for p in pts])


def rect(x0, y0, x1, y1):
    return poly((x0, y0), (x1, y0), (x1, y1), (x0, y1))


def arc(p0, p1, corner, k=0.6):
    """Quarter-turn cubic from p0 to p1, handles aimed at the corner point."""
    c1 = (p0[0] + k * (corner[0] - p0[0]), p0[1] + k * (corner[1] - p0[1]))
    c2 = (p1[0] + k * (corner[0] - p1[0]), p1[1] + k * (corner[1] - p1[1]))
    return (c1, c2, p1)


def path(start, *segs):
    """Build a contour from a start point and segments; a bare point is a line."""
    out = []
    for s in segs:
        out.append(s if isinstance(s[0], tuple) else (tuple(map(float, s)),))
    assert all(abs(a - b) < 1e-6 for a, b in zip(out[-1][-1], start)), "contour is not closed"
    return out


def is_polygon(contour, n=None):
    return all(len(s) == 1 for s in contour) and (n is None or len(contour) == n)


def uniq(vals, tol=0.5):
    out = []
    for v in sorted(vals):
        if not out or v - out[-1] > tol:
            out.append(v)
    return out


def diag_h(t, dx, dy):
    """Horizontal width of a stroke of true thickness t running along (dx, dy)."""
    return t * math.hypot(dx, dy) / abs(dy)
