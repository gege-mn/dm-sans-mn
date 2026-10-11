"""Cyrillic glyph recipes for DM Sans.

STYLISTIC_SETS lists the extra substitutions appended to upstream's features.

Every recipe is a function of one master. It measures that master's Latin
(stems, bars, counters, curve weights) and builds the Cyrillic letter from
those measurements, reusing Latin outlines wherever a shape already exists.
Because each recipe emits the same structure in every master, the results
interpolate across the weight and optical-size axes.
"""
import math
from dataclasses import dataclass, field
from types import SimpleNamespace as NS

from geom import (affine, arc, bbox, ccw, cw, diag_h, flip_y, is_polygon, mirror_x,
                  oncurve, path, pl, poly, rect, remap, shift, uniq)

REF_MASTER = "24pt Regular"


@dataclass
class Shape:
    contours: list = field(default_factory=list)
    width: float = 0
    comps: list = field(default_factory=list)  # (glyph name, dx, dy)
    marks: list = field(default_factory=list)  # (mark glyph, x, y): its _top anchor lands on that point


class Ctx:
    """One master of the source font, plus the measurements the recipes share."""

    def __init__(self, font, master, ref_master, reader):
        self.font, self.master, self.ref_master, self._read = font, master, ref_master, reader
        self.asc, self.desc = master.ascender, master.descender
        self.cap_h, self.x_h = master.capHeight, master.xHeight
        self._measure()

    def src(self, name, master=None):
        return self._read(self.font.glyphs[name].layers[(master or self.master).id])

    def big(self, name):
        """Contours largest first, so [0] is the outer shape and [1] its main counter."""
        return sorted(self.src(name), key=lambda c: -abs(_area(c)))

    def w(self, name):
        return self.font.glyphs[name].layers[self.master.id].width

    def anchor(self, name, anchor):
        for a in self.font.glyphs[name].layers[self.master.id].anchors:
            if a.name == anchor:
                return a.position.x, a.position.y
        raise KeyError(anchor)

    def ref(self, name, x, y):
        """The point that sits at (x, y) in the reference master, as placed in this master."""
        here, there = self.src(name), self.src(name, self.ref_master)
        for ci, c in enumerate(there):
            for si, seg in enumerate(c):
                for pi, p in enumerate(seg):
                    if abs(p[0] - x) < 0.5 and abs(p[1] - y) < 0.5:
                        return here[ci][si][pi]
        raise KeyError(f"{name}: no point at {x},{y} in {REF_MASTER}")

    def _measure(self):
        h, xh = self.cap_h, self.x_h
        H = self.src("H")
        xs = uniq(p[0] for c in H for p in oncurve(c) if abs(p[1]) < 1)
        L, S, CW = xs[0], xs[1] - xs[0], xs[2] - xs[1]
        bar = min(H, key=lambda c: bbox(c)[3] - bbox(c)[1])
        _, by0, _, by1 = bbox(bar)
        ys = uniq(p[1] for p in oncurve(self.src("E")[0]))
        B = ys[-1] - ys[-2]
        # true thickness of the N diagonal: distance from one edge to the other
        (ax, ay), (bx, by), (cx, cy) = self.ref("N", 158, 561), self.ref("N", 531, 0), self.ref("N", 531, 139)
        t = abs((bx - ax) * (cy - ay) - (by - ay) * (cx - ax)) / math.hypot(bx - ax, by - ay)
        O = self.big("O")
        ob, ib = bbox(O[0]), bbox(O[1])
        self.cap = NS(h=h, S=S, B=B, Bm=by1 - by0, ybar=(by0 + by1) / 2, L=L, CW=CW, t=t,
                      dd=104 + 0.1 * S, side=ib[0] - ob[0], tb=ib[1] - ob[1], ov=-ob[1])
        n = self.src("n")[0]
        xs = uniq(p[0] for p in oncurve(n) if abs(p[1]) < 1)
        l, s, cw_ = xs[0], xs[1] - xs[0], xs[2] - xs[1]
        ys = uniq(p[1] for p in oncurve(self.src("z")[0]))
        b = ys[-1] - ys[-2]
        o = self.big("o")
        ob, ib = bbox(o[0]), bbox(o[1])
        # the e carries the lowercase's three-storey weights: outer curves and the lighter middle bar
        e_top = self.ref("e", 294, 508)[1] - self.ref("e", 292, 437)[1]
        e_bar = self.ref("e", 111, 294)[1] - self.ref("e", 111, 229)[1]
        self.lc = NS(h=xh, S=s, B=b, Bm=b * (by1 - by0) / B, ybar=xh * 0.51, L=l, CW=cw_ * 1.04,
                     t=t * s / S, dd=98 + 0.12 * s, side=ib[0] - ob[0], tb=ib[1] - ob[1], ov=-ob[1],
                     tb3=e_top, bar3=e_bar)


def _area(c):
    from geom import area
    return area(c)


# ---------------------------------------------------------------- straight letters

def ge(q):
    L, S, B, h = q.L, q.S, q.B, q.h
    x1 = L + S + 0.83 * q.CW + 0.63 * S
    return Shape([poly((L, 0), (L + S, 0), (L + S, h - B), (x1, h - B), (x1, h), (L, h))], x1 + 0.4 * L)


def pe(q):
    L, S, B, h = q.L, q.S, q.B, q.h
    xr = L + 2 * S + q.CW
    return Shape([poly((L, 0), (L + S, 0), (L + S, h - B), (xr - S, h - B), (xr - S, 0), (xr, 0),
                       (xr, h), (L, h))], xr + L)


def en(q):
    L, S, h = q.L, q.S, q.h
    xr = L + 2 * S + q.CW
    y0, y1 = q.ybar - q.Bm / 2, q.ybar + q.Bm / 2
    return Shape([poly((L, 0), (L + S, 0), (L + S, y0), (xr - S, y0), (xr - S, 0), (xr, 0), (xr, h),
                       (xr - S, h), (xr - S, y1), (L + S, y1), (L + S, h), (L, h))], xr + L)


def _tail(q, xr):
    """Descender tick for Ц Щ: points from the baseline, round the tick, back up to the stem."""
    e, st = 0.6 * q.S + 0.1 * q.L, 0.92 * q.S
    x1 = xr + e
    return [(x1 - st, 0), (x1 - st, -q.dd), (x1, -q.dd), (x1, q.B), (xr, q.B)], x1


def tse(q):
    L, S, B, h = q.L, q.S, q.B, q.h
    xr = L + 2 * S + q.CW
    tail, x1 = _tail(q, xr)
    return Shape([poly((L, 0), *tail, (xr, h), (xr - S, h), (xr - S, B), (L + S, B), (L + S, h), (L, h))],
                 x1 + 0.3 * L)


def sha(q, tailed=False):
    L, S, B, h = q.L, q.S, q.B, q.h
    c = 0.76 * q.CW
    x2 = L + 2 * S + c
    x3 = x2 + c + S
    tail, x1 = _tail(q, x3) if tailed else ([(x3, 0)], x3)
    pts = [(L, 0), *tail, (x3, h), (x3 - S, h), (x3 - S, B), (x2, B), (x2, h), (x2 - S, h), (x2 - S, B),
           (L + S, B), (L + S, h), (L, h)]
    return Shape([poly(*pts)], x1 + 0.3 * L if tailed else x3 + L)


def te(q, bar_w, sb):
    S, B, h = q.S, q.B, q.h
    x0, x1 = sb, sb + bar_w
    xc = (x0 + x1) / 2
    return Shape([poly((xc + S / 2, 0), (xc + S / 2, h - B), (x1, h - B), (x1, h), (x0, h), (x0, h - B),
                       (xc - S / 2, h - B), (xc - S / 2, 0))], x1 + sb)


def _solve(fn, lo, hi, target):
    flo = fn(lo) - target
    for _ in range(60):
        mid = (lo + hi) / 2
        fm = fn(mid) - target
        if (fm > 0) == (flo > 0):
            lo, flo = mid, fm
        else:
            hi = mid
    return (lo + hi) / 2


def ii(q):
    """И drawn like the Latin N with the diagonal running the other way."""
    L, S, h = q.L, q.S, q.h
    dx = 1.03 * q.CW
    xr = L + 2 * S + dx
    d = _solve(lambda d: d * dx / math.hypot(dx, h - d), 1, h * 0.8, q.t)
    return Shape([_ii_poly(L, S, h, xr, d)], xr + L)


def _ii_poly(L, S, h, xr, d):
    # left stem, diagonal rising to the top of the right stem, right stem
    return poly((L, 0), (L + S, 0), (xr - S, h - d), (xr - S, 0), (xr, 0), (xr, h), (xr - S, h),
                (L + S, d), (L + S, h), (L, h))


def em(q):
    L, S, h, t = q.L, q.S, q.h, q.t
    wi = 1.25 * (2 * S + q.CW) - 2 * S
    xr = L + 2 * S + wi
    xm = (L + xr) / 2
    v0, f, a = 0.143 * h, 0.75 * S, 1.17 * S

    def upper(y1):
        dx, dy = (xm - f / 2) - (L + S), v0 - y1
        n = math.hypot(dx, dy)
        px, py = L + S - dy / n * t, y1 + dx / n * t  # a point on the upper edge
        return px, py, dx, dy

    def x_top(y1):
        px, py, dx, dy = upper(y1)
        return px + (h - py) * dx / dy

    y1 = _solve(x_top, v0 + 5, h, L + a)
    px, py, dx, dy = upper(y1)
    y2 = py + (xm - px) * dy / dx
    return Shape([poly((L, 0), (L + S, 0), (L + S, y1), (xm - f / 2, v0), (xm + f / 2, v0), (xr - S, y1),
                       (xr - S, 0), (xr, 0), (xr, h), (xr - a, h), (xm, y2), (L + a, h), (L, h))], xr + L)


def el(q):
    L, S, B, h = q.L, q.S, q.B, q.h
    xa, lean = 0.4 * L, 0.21 * h
    th = diag_h(q.t * 1.03, lean, h)
    xit = xa + th + lean * (h - B) / h
    xr = xit + 0.7 * q.CW + S
    return Shape([poly((xa, 0), (xa + th, 0), (xit, h - B), (xr - S, h - B), (xr - S, 0), (xr, 0),
                       (xr, h), (xa + lean, h))], xr + L)


def de(q):
    L, S, B, h, dd = q.L, q.S, q.B, q.h, q.dd
    x0, ov, st = 0.3 * L, 0.25 * S + 28, 0.92 * S
    xa = x0 + ov
    lean = 0.16 * (h - B)
    th = diag_h(q.t * 1.03, lean, h - B)
    xit = xa + th + lean * (h - 2 * B) / (h - B)
    xr = xit + (0.68 - 0.00105 * S) * q.CW + S
    x1 = xr + ov
    outer = poly((x0, -dd), (x0 + st, -dd), (x0 + st, 0), (x1 - st, 0), (x1 - st, -dd), (x1, -dd), (x1, B),
                 (xr, B), (xr, h), (xa + lean, h), (xa, B), (x0, B))
    counter = cw(poly((xa + th, B), (xit, h - B), (xr - S, h - B), (xr - S, B)))
    return Shape([outer, counter], x1 + x0)


def che(q, wf=0.84):
    L, S, B, h = q.L, q.S, q.B, q.h
    wi = wf * q.CW
    xl, xr = L, L + 2 * S + wi
    yb = 0.385 * h
    rx = 0.5 * wi + 0.5 * S
    ry = 0.92 * rx
    rxi, ryi = rx - S, max(ry - B, 0.25 * B)
    c = path((xr, 0),
             (xr, h), (xr - S, h), (xr - S, yb + B), (xl + S + rxi, yb + B),
             arc((xl + S + rxi, yb + B), (xl + S, yb + B + ryi), (xl + S, yb + B)),
             (xl + S, h), (xl, h), (xl, yb + ry),
             arc((xl, yb + ry), (xl + rx, yb), (xl, yb)),
             (xr - S, yb), (xr - S, 0), (xr, 0))
    return Shape([ccw(c)], xr + L)


# ---------------------------------------------------------------- letters built on Latin outlines

def _rotate_to(contour, pred):
    pts = oncurve(contour)
    i = next(i for i, p in enumerate(pts) if pred(p))
    return pts[i:] + pts[:i]


def zhe_cap(c):
    q = c.cap
    K = ccw(c.src("K")[0])
    assert is_polygon(K, 12), "K changed shape upstream"
    sr = q.L + q.S
    pts = _rotate_to(K, lambda p: abs(p[0] - sr) < 1 and abs(p[1]) < 1)[:10]
    kx = 0.94
    reach = (max(p[0] for p in pts) - sr) * kx
    sb = c.w("K") - max(p[0] for p in pts)
    xs_l = sb + reach
    xs_r = xs_l + q.S
    right = [(xs_r + (x - sr) * kx, y) for x, y in pts]
    left = [(xs_l + xs_r - x, y) for x, y in reversed(right)]
    return Shape([poly(*right, *left)], xs_r + reach + sb)


def _k_parts(c):
    k = c.src("k")
    stem = next(x for x in k if is_polygon(x, 4))
    arms = [x for x in k if x is not stem]
    return bbox(stem), arms


def ka_lc(c):
    q = c.lc
    (x0, _, x1, _), arms = _k_parts(c)
    return Shape([rect(x0, 0, x1, q.h)] + arms, c.w("k"))


def zhe_lc(c):
    q = c.lc
    (x0, _, sr, _), arms = _k_parts(c)
    kx = 0.97
    reach = (bbox(arms)[2] - sr) * kx
    sb = c.w("k") - bbox(arms)[2]
    xs_l = sb + reach
    xs_r = xs_l + q.S
    right = remap(arms, fx=lambda x: xs_r + (x - sr) * kx)
    left = mirror_x(right, (xs_l + xs_r) / 2)
    return Shape([rect(xs_l, 0, xs_r, q.h)] + right + left, xs_r + reach + sb)


def u_cap(c):
    y = c.src("y")
    k = 1.04
    fy = pl((c.desc, 0), (c.x_h, c.cap_h))
    x0 = bbox(y)[0]
    out = remap(y, fx=lambda x: x0 + (x - x0) * k, fy=fy)
    return Shape(out, x0 + (c.w("y") - x0) * k + 0)


def _ring(c, name, x0, inner_w, side, y0=None, y1=None, tb=None):
    """The O or o redrawn at a new width and height with chosen stroke weights."""
    O = c.big(name)
    ob, ib = bbox(O[0]), bbox(O[1])
    fx = pl((ob[0], x0), (ib[0], x0 + side), (ib[2], x0 + side + inner_w), (ob[2], x0 + 2 * side + inner_w))
    fy = None
    if y0 is not None:
        fy = pl((ob[1], y0), (ib[1], y0 + tb), (ib[3], y1 - tb), (ob[3], y1))
    return remap(O[:2], fx, fy), x0 + 2 * side + inner_w


def _o_metrics(c, name):
    O = c.big(name)
    ob, ib = bbox(O[0]), bbox(O[1])
    return NS(ob=ob, ib=ib, lsb=ob[0], rsb=c.w(name) - ob[2], inner_w=ib[2] - ib[0], inner_h=ib[3] - ib[1],
              side=ib[0] - ob[0], tb=ib[1] - ob[1])


def ef_cap(c):
    q, o = c.cap, _o_metrics(c, "O")
    side, tb = 0.95 * o.side, 0.95 * o.tb
    inner = q.S + 2 * 0.42 * o.inner_w
    x0 = 0.9 * o.lsb
    ring, x1 = _ring(c, "O", x0, inner, side, 0.105 * q.h, 0.895 * q.h, tb)
    xc = (x0 + x1) / 2
    return Shape([rect(xc - q.S / 2, 0, xc + q.S / 2, q.h)] + ring, x1 + x0)


def ef_lc(c):
    q, o = c.lc, _o_metrics(c, "o")
    side = 0.95 * o.side
    inner = q.S + 2 * 0.55 * o.inner_w
    ring, x1 = _ring(c, "o", o.lsb, inner, side)
    xc = (o.lsb + x1) / 2
    return Shape([rect(xc - q.S / 2, c.desc, xc + q.S / 2, c.asc)] + ring, x1 + o.lsb)


def iu(c, q, name):
    o = _o_metrics(c, name)
    L, S, h = q.L, q.S, q.h
    xo = L + S + 0.3 * q.CW
    ring, x1 = _ring(c, name, xo, 0.88 * o.inner_w, o.side)
    xe = xo + o.side / 2
    y0, y1 = q.ybar - q.Bm / 2, q.ybar + q.Bm / 2
    stem = poly((L, 0), (L + S, 0), (L + S, y0), (xe, y0), (xe, y1), (L + S, y1), (L + S, h), (L, h))
    return Shape([stem] + ring, x1 + o.rsb)


def obarred(c, q, name):
    o = _o_metrics(c, name)
    O = c.src(name)[:2]
    bm = min(getattr(q, "bar3", 0.92 * q.Bm + 1.5), 0.4 * o.inner_h)
    yc = (o.ob[1] + o.ob[3]) / 2
    return Shape(O + [rect(o.ib[0] - o.side / 2, yc - bm / 2, o.ib[2] + o.side / 2, yc + bm / 2)], c.w(name))


def e_rev(c, q, name):
    C = c.src(name)
    w = c.w(name)
    x0, y0, x1, y1 = bbox(C)
    side = _o_metrics(c, "O" if name == "C" else "o").side
    out = mirror_x(C, w / 2)
    xr_in = w - x0 - side  # inner edge of the round stroke, now on the right
    xb0 = (w - x1) + 0.4 * (x1 - x0)
    bm = getattr(q, "bar3", 0.92 * q.Bm + 1.5)
    yc = (y0 + y1) / 2
    return Shape(out + [rect(xb0, yc - bm / 2, xr_in + side / 2, yc + bm / 2)], w)


def ze_cap(c):
    t = c.src("three")
    x0, _, x1, _ = bbox(t)
    dx = -0.2 * x0
    return Shape(shift(t, dx), x1 + dx + 0.75 * (c.w("three") - x1))


def ze_lc(c):
    q, R = c.lc, lambda x, y: c.ref("three", x, y)
    t = c.src("three")
    ov, tb, bm = q.ov, q.tb3, q.bar3
    ym = 0.54 * q.h
    k = q.side / c.cap.side  # keep the figure's own stroke weights, scaled to lowercase
    fy = pl((R(292, -12)[1], -ov), (R(292, 61)[1], -ov + tb), (R(268, 342)[1], ym - bm / 2),
            (R(216, 413)[1], ym + bm / 2), (R(292, 639)[1], q.h + ov - tb), (R(292, 712)[1], q.h + ov))
    xl0, xl1 = R(50, 208)[0], R(135, 208)[0]
    xr0, xr1, xr_in = R(413, 531)[0], R(526, 201)[0], R(441, 201)[0]
    x0 = 0.8 * xl0
    x1 = x0 + (0.81 + 0.0009 * q.S) * (xr1 - xl0)
    fx = pl((xl0, x0), (xl1, x0 + k * (xl1 - xl0)), (xr0, x1 - k * (xr1 - xr0)), (xr1, x1))
    return Shape(remap(t, fx, fy), x1 + 0.75 * (c.w("three") - xr1))


# ---------------------------------------------------------------- bowls: Ь Ъ Ы Б В Я

def _replace_node(contour, pt, new):
    out = []
    for seg in contour:
        if len(seg) == 1 and abs(seg[0][0] - pt[0]) < 0.5 and abs(seg[0][1] - pt[1]) < 0.5:
            out.extend((tuple(map(float, p)),) for p in new)
        else:
            out.append(seg)
    assert len(out) > len(contour) or len(new) == 1, f"node {pt} not found"
    return out


def _soft_parts(c, q):
    """Ь: the Latin P turned upside down, resized for lowercase when asked."""
    P = flip_y(c.big("P"), c.cap_h / 2)
    if q is c.cap:
        x0, _, x1, _ = bbox(P)
        return P, x1, c.w("P") - x1
    H, R = c.cap_h, lambda x, y: c.ref("P", x, y)
    frac = (H - R(304, 292)[1]) / H + 0.03
    yt = frac * q.h
    bb = min(0.97 * q.tb, 0.4 * yt)
    fy = pl((0, 0), (H - R(302, 630)[1], bb), (H - R(302, 363)[1], yt - bb), (H - R(304, 292)[1], yt), (H, q.h))
    xo = q.L + 0.87 * (R(543, 496)[0] - c.cap.L)
    fx = pl((c.cap.L, q.L), (c.cap.L + c.cap.S, q.L + q.S), (R(457, 496)[0], xo - q.side), (R(543, 496)[0], xo))
    return remap(P, fx, fy), xo, 0.85 * (c.w("P") - R(543, 496)[0])


def soft(c, q):
    P, xo, rsb = _soft_parts(c, q)
    return Shape(P, xo + rsb)


def yeru(c, q):
    P, xo, _ = _soft_parts(c, q)
    xs = xo + 0.27 * q.CW
    return Shape(P + [rect(xs, 0, xs + q.S, q.h)], xs + q.S + q.L)


def hard(c, q):
    P, xo, rsb = _soft_parts(c, q)
    fl, sb = 0.27 * (q.CW + q.S), 0.3 * q.L
    dx = sb + fl - q.L
    P = shift(P, dx)
    xs, h, B = q.L + dx, q.h, q.B
    P[0] = _replace_node(P[0], (xs, h), [(sb, h), (sb, h - B), (xs, h - B)])
    return Shape(P, xo + dx + rsb)


def be_cap(c):
    q = c.cap
    P, xo, rsb = _soft_parts(c, q)
    xs, h, B = q.L + q.S, q.h, q.B
    xe = xo - 0.09 * (xo - q.L)
    P[0] = _replace_node(P[0], (xs, h), [(xs, h - B), (xe, h - B), (xe, h)])
    return Shape(P, xo + rsb)


def ve_lc(c):
    q, C, R = c.lc, c.cap, lambda x, y: c.ref("B", x, y)
    Bc = c.src("B")
    bb = min(q.tb3, 0.26 * q.h)
    bmid = q.bar3
    ym = q.h * (R(317, 327)[1] + R(314, 394)[1]) / 2 / C.h
    fy = pl((0, 0), (R(319, 70)[1], bb), (R(317, 327)[1], ym - bmid / 2), (R(314, 394)[1], ym + bmid / 2),
            (R(311, 630)[1], q.h - bb), (C.h, q.h))
    xo_c, xi_bot, xi_top = R(555, 191)[0], R(469, 197)[0], R(453, 513)[0]
    x1 = q.L + 0.87 * (xo_c - C.L)
    fx = pl((C.L, q.L), (C.L + C.S, q.L + q.S), (xi_top, x1 - q.side * (xo_c - xi_top) / (xo_c - xi_bot)),
            (xo_c, x1))
    return Shape(remap(Bc, fx, fy), x1 + 0.85 * (c.w("B") - xo_c))


def ia_cap(c):
    return Shape(mirror_x(c.src("R"), c.w("R") / 2), c.w("R"))


def ia_lc(c):
    q, C, R = c.lc, c.cap, lambda x, y: c.ref("R", x, y)
    Rc = c.src("R")
    leg = next(x for x in Rc if is_polygon(x, 4))
    bowl = [x for x in Rc if x is not leg]
    frac = (C.h - R(296, 289)[1]) / C.h + 0.03
    yb = q.h * (1 - frac)
    bb = min(0.97 * q.tb, 0.4 * frac * q.h)
    fy = pl((0, 0), (R(296, 289)[1], yb), (R(294, 355)[1], yb + bb), (R(293, 629)[1], q.h - bb), (C.h, q.h))
    xo_c, xi_c = R(536, 495)[0], R(449, 494)[0]
    xo = q.L + 0.87 * (xo_c - C.L)
    fx = pl((C.L, q.L), (C.L + C.S, q.L + q.S), (xi_c, xo - q.side), (xo_c, xo))
    bowl = remap(bowl, fx, fy)
    # leg: keep its true thickness instead of letting the rescale thin it
    (bx1, _), (tx1, ty), (tx0, _), (bx0, _) = [R(543, 0), R(384, 313), R(290, 313), R(444, 0)]
    t_cap = (bx1 - bx0) * ty / math.hypot((bx0 + bx1) / 2 - (tx0 + tx1) / 2, ty)
    t = t_cap * q.S / C.S
    yt, xbr, xtc = fy(ty), fx(bx1), fx((tx0 + tx1) / 2)
    th = t / 0.89
    for _ in range(4):
        th = diag_h(t, (xbr - th / 2) - xtc, yt)
    legc = poly((xbr, 0), (xtc + th / 2, yt), (xtc - th / 2, yt), (xbr - th, 0))
    sb = 0.8 * (c.w("R") - bx1)
    return Shape(mirror_x(bowl + [legc], (xbr + sb) / 2), xbr + sb)


def be_lc(c):
    q, o = c.lc, _o_metrics(c, "o")
    O = c.src("o")[:2]
    x0, side, ow = o.ob[0], o.side, o.ob[2] - o.ob[0]
    ymid, top = (o.ob[1] + o.ob[3]) / 2, c.asc
    b = min(0.97 * o.tb, q.B)
    xe = x0 + 0.82 * ow
    rx = 0.64 * ow
    rxi = rx - side
    xi = x0 + side
    tail = path((xi, ymid),
                arc((xi, ymid), (xi + rxi, top - b), (xi, top - b)),
                (xe, top - b), (xe, top), (x0 + rx, top),
                arc((x0 + rx, top), (x0, ymid), (x0, top)),
                (xi, ymid))
    return Shape(O + [ccw(tail)], c.w("o"))


def ustraight_lc(c):
    q, C, R = c.lc, c.cap, lambda x, y: c.ref("Y", x, y)
    Y = c.src("Y")
    xl, xr = R(248, 0)[0], R(332, 0)[0]
    x0, x1 = R(20, 700)[0], R(559, 700)[0]
    k = 0.95
    n0 = 0.9 * x0
    ns0 = n0 + (xl - x0) * k
    ns1 = ns0 + q.S
    n1 = ns1 + (x1 - xr) * k
    fx = pl((x0, n0), (xl, ns0), (xr, ns1), (x1, n1))
    fy = pl((0, c.desc), (R(248, 266)[1], 0.03 * q.h), (C.h, q.h))
    return Shape(remap(Y, fx, fy), n1 + n0)


def tugrik(c):
    q = c.cap
    T = c.src("T")
    x0, _, x1, _ = bbox(T)
    xc = (x0 + x1) / 2
    hx = 0.34 * (x1 - x0)
    rise = 0.7 * hx
    tv = min(0.9 * q.B, 0.15 * q.h)
    gap = tv + 0.13 * q.h
    yc = 0.42 * q.h
    bars = []
    for y in (yc - gap / 2, yc + gap / 2):
        bars.append(poly((xc - hx, y - rise / 2 - tv / 2), (xc + hx, y + rise / 2 - tv / 2),
                         (xc + hx, y + rise / 2 + tv / 2), (xc - hx, y - rise / 2 + tv / 2)))
    return Shape(T + bars, c.w("T"))


# ---------------------------------------------------------------- the alphabet

def _comp(name):
    return lambda c: Shape(comps=[(name, 0, 0)], width=c.w(name))


def _breve(base_fn, comb, top):
    def fn(c):
        base = base_fn(c)
        base.marks.append((comb, base.width / 2, top(c)))
        return base
    return fn


def _te_lc(c):
    T = c.src("T")
    x0, _, x1, _ = bbox(T)
    return te(c.lc, 0.84 * (x1 - x0), 0.85 * x0)


def _numero(c):
    gap = -0.25 * c.cap.L
    return Shape(comps=[("N", 0, 0), ("ordmasculine", c.w("N") + gap, 0)],
                 width=c.w("N") + gap + c.w("ordmasculine"))


def _ii_cap(c):
    return Shape(mirror_x(c.src("N"), c.w("N") / 2), c.w("N"))


STYLISTIC_SETS = {"ss02": "sub a-cy by a-cy.ss02;", "ss05": "sub u-cy by u-cy.ss05;"}

# name: (unicode, recipe, left kerning group donor, right kerning group donor)
GLYPHS = {
    "A-cy": ("0410", _comp("A"), "A", "A"),
    "Be-cy": ("0411", be_cap, "H", None),
    "Ve-cy": ("0412", _comp("B"), "B", "B"),
    "Ge-cy": ("0413", lambda c: ge(c.cap), "H", "T"),
    "De-cy": ("0414", lambda c: de(c.cap), None, None),
    "Ie-cy": ("0415", _comp("E"), "E", "E"),
    "Io-cy": ("0401", _comp("Edieresis"), "E", "E"),
    "Zhe-cy": ("0416", zhe_cap, None, "K"),
    "Ze-cy": ("0417", ze_cap, None, "B"),
    "Ii-cy": ("0418", _ii_cap, "H", "H"),
    "Iishort-cy": ("0419", _breve(_ii_cap, "brevecomb.case", lambda c: c.cap_h), "H", "H"),
    "Ka-cy": ("041A", _comp("K"), "K", "K"),
    "El-cy": ("041B", lambda c: el(c.cap), None, "H"),
    "Em-cy": ("041C", _comp("M"), "M", "M"),
    "En-cy": ("041D", _comp("H"), "H", "H"),
    "O-cy": ("041E", _comp("O"), "O", "O"),
    "Pe-cy": ("041F", lambda c: pe(c.cap), "H", "H"),
    "Er-cy": ("0420", _comp("P"), "P", "P"),
    "Es-cy": ("0421", _comp("C"), "C", "C"),
    "Te-cy": ("0422", _comp("T"), "T", "T"),
    "U-cy": ("0423", u_cap, "Y", "Y"),
    "Ef-cy": ("0424", ef_cap, "O", "O"),
    "Ha-cy": ("0425", _comp("X"), "X", "X"),
    "Tse-cy": ("0426", lambda c: tse(c.cap), "H", None),
    "Che-cy": ("0427", lambda c: che(c.cap), None, "H"),
    "Sha-cy": ("0428", lambda c: sha(c.cap), "H", "H"),
    "Shcha-cy": ("0429", lambda c: sha(c.cap, True), "H", None),
    "Hardsign-cy": ("042A", lambda c: hard(c, c.cap), "T", None),
    "Yeru-cy": ("042B", lambda c: yeru(c, c.cap), "H", "H"),
    "Softsign-cy": ("042C", lambda c: soft(c, c.cap), "H", None),
    "Ereversed-cy": ("042D", lambda c: e_rev(c, c.cap, "C"), None, "O"),
    "Iu-cy": ("042E", lambda c: iu(c, c.cap, "O"), "H", "O"),
    "Ia-cy": ("042F", ia_cap, None, "H"),
    "Obarred-cy": ("04E8", lambda c: obarred(c, c.cap, "O"), "O", "O"),
    "Ustraight-cy": ("04AE", _comp("Y"), "Y", "Y"),

    "a-cy": ("0430", _comp("a"), "a", "a"),
    "be-cy": ("0431", be_lc, "o", "o"),
    "ve-cy": ("0432", ve_lc, "n", None),
    "ge-cy": ("0433", lambda c: ge(c.lc), "n", "r"),
    "de-cy": ("0434", lambda c: de(c.lc), None, None),
    "ie-cy": ("0435", _comp("e"), "e", "e"),
    "io-cy": ("0451", _comp("edieresis"), "e", "e"),
    "zhe-cy": ("0436", zhe_lc, None, "k"),
    "ze-cy": ("0437", ze_lc, None, None),
    "ii-cy": ("0438", lambda c: ii(c.lc), "n", "u"),
    "iishort-cy": ("0439", _breve(lambda c: ii(c.lc), "brevecomb", lambda c: c.x_h), "n", "u"),
    "ka-cy": ("043A", ka_lc, "n", "k"),
    "el-cy": ("043B", lambda c: el(c.lc), None, "u"),
    "em-cy": ("043C", lambda c: em(c.lc), "n", "u"),
    "en-cy": ("043D", lambda c: en(c.lc), "n", "u"),
    "o-cy": ("043E", _comp("o"), "o", "o"),
    "pe-cy": ("043F", lambda c: pe(c.lc), "n", "u"),
    "er-cy": ("0440", _comp("p"), "p", "p"),
    "es-cy": ("0441", _comp("c"), "c", "c"),
    "te-cy": ("0442", _te_lc, None, None),
    "u-cy": ("0443", _comp("y"), "y", "y"),
    "ef-cy": ("0444", ef_lc, "o", "o"),
    "ha-cy": ("0445", _comp("x"), "x", "x"),
    "tse-cy": ("0446", lambda c: tse(c.lc), "n", None),
    "che-cy": ("0447", lambda c: che(c.lc, 0.9), None, "u"),
    "sha-cy": ("0448", lambda c: sha(c.lc), "n", "u"),
    "shcha-cy": ("0449", lambda c: sha(c.lc, True), "n", None),
    "hardsign-cy": ("044A", lambda c: hard(c, c.lc), None, None),
    "yeru-cy": ("044B", lambda c: yeru(c, c.lc), "n", "u"),
    "softsign-cy": ("044C", lambda c: soft(c, c.lc), "n", None),
    "ereversed-cy": ("044D", lambda c: e_rev(c, c.lc, "c"), None, "o"),
    "iu-cy": ("044E", lambda c: iu(c, c.lc, "o"), "n", "o"),
    "ia-cy": ("044F", ia_lc, None, "u"),
    "obarred-cy": ("04E9", lambda c: obarred(c, c.lc, "o"), "o", "o"),
    "ustraight-cy": ("04AF", ustraight_lc, "y", "y"),

    # stylistic-set partners, so ss02 and ss05 change а and у together with Latin a and y
    "a-cy.ss02": (None, _comp("a.ss02"), "a.ss02", "a.ss02"),
    "u-cy.ss05": (None, _comp("y.ss05"), "y.ss05", "y.ss05"),

    "tugrik": ("20AE", tugrik, "T", "T"),
    "numero": ("2116", _numero, "H", None),
}
