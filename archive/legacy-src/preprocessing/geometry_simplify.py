# geometry_simplify.py
# Tiny, dependency-free path simplifier: RDP → optional cubic smoothing.

from math import hypot, acos, degrees
from typing import Iterable, List, Sequence, Tuple

Pt = Tuple[float, float]
Cubic = Tuple[Pt, Pt, Pt, Pt]

def _dist_ps(p: Pt, a: Pt, b: Pt) -> float:
    ax, ay = a; bx, by = b; px, py = p
    vx, vy = bx - ax, by - ay
    wx, wy = px - ax, py - ay
    vv = vx * vx + vy * vy
    if vv == 0.0:
        return hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, (wx * vx + wy * vy) / vv))
    qx, qy = ax + t * vx, ay + t * vy
    return hypot(px - qx, py - qy)

def _rdp(pts: Sequence[Pt], eps: float, keep: set) -> List[Pt]:
    if len(pts) < 3:
        return list(pts)
    out: List[Pt] = []
    def rec(i0: int, i1: int):
        a, b = pts[i0], pts[i1]
        j, md = -1, -1.0
        for i in range(i0 + 1, i1):
            d = _dist_ps(pts[i], a, b)
            if d > md: md, j = d, i
        if md > eps or any(i in keep for i in range(i0 + 1, i1)):
            rec(i0, j); rec(j, i1)
        else:
            out.append(a)
    rec(0, len(pts) - 1)
    out.append(pts[-1])
    return out

def _collinear_merge(pts: Sequence[Pt], deg_tol: float) -> List[Pt]:
    if len(pts) <= 2: return list(pts)
    def turn(a: Pt, b: Pt, c: Pt) -> float:
        ax, ay = a; bx, by = b; cx, cy = c
        v1x, v1y = ax - bx, ay - by
        v2x, v2y = cx - bx, cy - by
        n1 = hypot(v1x, v1y) or 1.0
        n2 = hypot(v2x, v2y) or 1.0
        dot = max(-1.0, min(1.0, (v1x * v2x + v1y * v2y) / (n1 * n2)))
        return 180.0 - degrees(acos(dot))
    keep = [pts[0]]
    for i in range(1, len(pts) - 1):
        if abs(turn(pts[i - 1], pts[i], pts[i + 1])) > deg_tol:
            keep.append(pts[i])
    keep.append(pts[-1])
    return keep

def simplify_polyline(points: Sequence[Pt],
                      tolerance: float,
                      force_indices: Iterable[int] = (),
                      collinear_deg: float = 0.5) -> List[Pt]:
    """Return fewer points under max deviation 'tolerance' (units = input units)."""
    if len(points) < 2: return list(points)
    pts = list(points)
    keep = set(force_indices)
    pts = _rdp(pts, tolerance, keep)
    return _collinear_merge(pts, collinear_deg)

# --- Optional: quick cubic smoothing via Catmull–Rom → Bezier ----------------

def _cr2bez(p0: Pt, p1: Pt, p2: Pt, p3: Pt) -> Cubic:
    def add(a: Pt, b: Pt) -> Pt: return (a[0] + b[0], a[1] + b[1])
    def sub(a: Pt, b: Pt) -> Pt: return (a[0] - b[0], a[1] - b[1])
    def mul(a: Pt, s: float) -> Pt: return (a[0] * s, a[1] * s)
    # centripetal CR tangents (alpha=0.5), approximated locally
    t1 = mul(sub(p2, p0), 0.25)
    t2 = mul(sub(p3, p1), 0.25)
    P0 = p1
    P3 = p2
    P1 = add(P0, mul(t1, 1/3))
    P2 = sub(P3, mul(t2, 1/3))
    return (P0, P1, P2, P3)

def simplify_to_cubics(points: Sequence[Pt],
                       tolerance: float,
                       force_indices: Iterable[int] = (),
                       step: int = 2) -> List[Cubic]:
    """Simplify then emit overlapping CR→Bezier spans."""
    pl = simplify_polyline(points, tolerance, force_indices)
    if len(pl) < 4:  # not enough to smooth
        return [(pl[i], pl[i], pl[i+1], pl[i+1]) for i in range(len(pl)-1)]
    out: List[Cubic] = []
    i = 0
    while i + 3 < len(pl):
        p0 = pl[i - 1] if i > 0 else pl[i]
        p1, p2, p3 = pl[i], pl[i + 1], pl[i + 2]
        p4 = pl[i + 3] if i + 3 < len(pl) else pl[i + 2]
        # choose middle 4 for stability
        out.append(_cr2bez(p0, p1, p2, p3))
        i += step
    # ensure tail is covered
    if out and out[-1][3] != pl[-1]:
        out.append(_cr2bez(pl[-3], pl[-2], pl[-1], pl[-1]))
    return out

# --- Tiny demo (remove if you hate examples) ---------------------------------
if __name__ == "__main__":
    poly = [(0,0),(1,0.01),(2,0.02),(3,0.0),(4,1),(5,1.1),(6,1)]
    simp = simplify_polyline(poly, tolerance=0.1)
    cubs = simplify_to_cubics(poly, tolerance=0.1)
    print("in :", len(poly), "pts")
    print("out:", len(simp), "pts,", len(cubs), "cubics")