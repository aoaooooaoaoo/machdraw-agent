"""剖视图：平面剖切 + 剖面线。

做的是**真剖切**，不是"盖一层阴影"：
  1. 用轴对齐剖切平面把 CSG 实体裁掉靠近观察者的一半（凸多面体被平面裁剪仍是凸多面体）；
  2. 裁剪时新生成的"切面"就是剖面（轮廓 + 内部孔洞）；
  3. 剖面按国标画 45° 细实线，间距可调；相邻零件的方向相反由调用方决定。

坐标：与 projection.py 一致（X 右、Y 后、Z 上，单位 mm）。
"""
from __future__ import annotations

import math

from .solid import Poly, Solid, Vec, box
from .projection import VIEWS, _right, build_three_view

_EPS = 1e-7


# ---------------------------------------------------------------- 凸多面体裁剪


def _clip_poly(poly: Poly, axis_idx: int, value: float, keep_ge: bool) -> Poly | None:
    """用半空间裁剪凸多面体；返回新 Poly（含新生成的切面），全在外侧则 None。"""
    sign = 1.0 if keep_ge else -1.0
    d = [sign * (v[axis_idx] - value) for v in poly.verts]
    if all(x >= -_EPS for x in d):
        return poly
    if all(x <= _EPS for x in d):
        return None

    reg: dict[tuple, int] = {}
    verts: list[Vec] = []

    def vid(p: Vec) -> int:
        key = (round(p[0], 7), round(p[1], 7), round(p[2], 7))
        if key not in reg:
            reg[key] = len(verts)
            verts.append(key)
        return reg[key]

    faces: list[list[int]] = []
    cap_pts: list[Vec] = []

    for f in poly.faces:
        newf: list[int] = []
        m = len(f)
        for i in range(m):
            a = poly.verts[f[i]]
            b = poly.verts[f[(i + 1) % m]]
            da = sign * (a[axis_idx] - value)
            db = sign * (b[axis_idx] - value)
            if da >= -_EPS:
                newf.append(vid(a))
            if (da > _EPS and db < -_EPS) or (da < -_EPS and db > _EPS):
                t = da / (da - db)
                pt = [a[k] + (b[k] - a[k]) * t for k in range(3)]
                pt[axis_idx] = value
                ptv = (pt[0], pt[1], pt[2])
                idx = vid(ptv)
                newf.append(idx)
                cap_pts.append(ptv)
        # 去重相邻重复
        dedup: list[int] = []
        for idx in newf:
            if not dedup or dedup[-1] != idx:
                dedup.append(idx)
        if len(dedup) >= 3:
            if dedup[0] == dedup[-1]:
                dedup.pop()
            if len(dedup) >= 3:
                faces.append(dedup)

    if len(verts) < 4 or not faces:
        return None

    # 切面：把落在剖切平面上的点按极角排序成凸多边形
    uniq: dict[int, Vec] = {}
    for p in cap_pts:
        uniq[vid(p)] = p
    if len(uniq) >= 3:
        pts = list(uniq.values())
        c = [sum(p[k] for p in pts) / len(pts) for k in range(3)]
        ax = [k for k in range(3) if k != axis_idx]
        o = (pts[0][ax[0]], pts[0][ax[1]])
        ordered = sorted(
            pts,
            key=lambda p: math.atan2(p[ax[1]] - c[ax[1]], p[ax[0]] - c[ax[0]]),
        )
        cap_ids = [vid(p) for p in ordered]
        if len(set(cap_ids)) >= 3:
            faces.append(cap_ids)
    return Poly(verts, faces)


def clip_solid(solid: Solid, axis: str, value: float, keep_ge: bool) -> tuple[Solid, list[Poly], list[Poly]]:
    """裁剪实体，返回 (裁剪后的实体, 补面(实体材料), 补面(被挖除的孔))。"""
    ai = {"x": 0, "y": 1, "z": 2}[axis]

    def caps(polys: list[Poly], src: list[Poly]) -> tuple[list[Poly], list[Poly]]:
        kept: list[Poly] = []
        cap_polys: list[Poly] = []
        for p in polys:
            q = _clip_poly(p, ai, value, keep_ge)
            if q is None:
                continue
            kept.append(q)
            # 只有真的被切到的体才有切面
            d = [(-1 if keep_ge else 1) * (v[ai] - value) for v in p.verts]
            if any(abs(x) < _EPS for x in d):
                cap_polys.append(q)     # 剖切面正好贴在该体上：整面都是剖面
            elif any(x < 0 for x in d):
                cap_polys.append(q)     # 被切到：q 里已含切面
        return kept, cap_polys

    adds, add_caps = caps(solid.adds, solid.adds)
    subs, sub_caps = caps(solid.subs, solid.subs)
    return Solid(adds, subs), add_caps, sub_caps


# ---------------------------------------------------------------- 剖面线


def _cap_face_in_plane(poly: Poly, axis_idx: int, value: float) -> list[tuple[float, float]]:
    """取出该体落在剖切平面上的那个面，投成平面二维多边形（u,v 为另两个轴）。"""
    ax = [k for k in range(3) if k != axis_idx]
    best: list[tuple[float, float]] | None = None

    # 找法向平行于裁剪轴、且位于剖切平面上的面
    for fi, f in enumerate(poly.faces):
        pts = [poly.verts[i] for i in f]
        if not all(abs(p[axis_idx] - value) < 1e-5 for p in pts):
            continue
        poly2 = [(p[ax[0]], p[ax[1]]) for p in pts]
        if best is None or _area(poly2) > _area(best):
            best = poly2
    # 没有正好在平面上的面时，用所有平面上的点做凸包近似
    if best is None:
        pts = [(v[ax[0]], v[ax[1]]) for v in poly.verts if abs(v[axis_idx] - value) < 1e-5]
        if len(pts) >= 3:
            best = _convex_hull(pts)
    return best or []


def _area(poly: list[tuple[float, float]]) -> float:
    a = 0.0
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        a += x1 * y2 - x2 * y1
    return abs(a) / 2


def _convex_hull(pts: list[tuple[float, float]]) -> list[tuple[float, float]]:
    pts = sorted(set(pts))
    if len(pts) <= 2:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def _clip_interval_to_convex(
    p0: tuple[float, float], p1: tuple[float, float], poly: list[tuple[float, float]]
) -> tuple[float, float] | None:
    """线段被凸多边形截出的参数区间 [t0,t1]；无交集返回 None。"""
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    t0, t1 = 0.0, 1.0
    n = len(poly)
    # 保证多边形逆时针
    if _signed_area(poly) < 0:
        poly = list(reversed(poly))
    for i in range(n):
        ax, ay = poly[i]
        bx, by = poly[(i + 1) % n]
        # 内侧：left of edge
        ex, ey = bx - ax, by - ay
        # f(t) = cross(e, p0 + t*d - a) >= 0
        f0 = ex * (p0[1] - ay) - ey * (p0[0] - ax)
        fd = ex * dy - ey * dx
        if abs(fd) < 1e-12:
            if f0 < -1e-9:
                return None
            continue
        t = -f0 / fd
        if fd > 0:
            t0 = max(t0, t)
        else:
            t1 = min(t1, t)
        if t0 > t1 + 1e-12:
            return None
    return (t0, t1)


def _signed_area(poly: list[tuple[float, float]]) -> float:
    a = 0.0
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        a += x1 * y2 - x2 * y1
    return a / 2


def hatch_segments(
    add_faces: list[list[tuple[float, float]]],
    sub_faces: list[list[tuple[float, float]]] | None = None,
    spacing: float = 5.0,
    angle_deg: float = 45.0,
) -> list[tuple[float, float, float, float]]:
    """生成剖面线（45° 细实线），孔洞处自动断开。"""
    subs = sub_faces or []
    if not add_faces:
        return []
    xs = [p[0] for f in add_faces for p in f]
    ys = [p[1] for f in add_faces for p in f]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)

    a = math.radians(angle_deg)
    dx, dy = math.cos(a), math.sin(a)
    # 法向
    nx, ny = -dy, dx
    corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    dvals = [nx * c[0] + ny * c[1] for c in corners]
    dmin, dmax = min(dvals), max(dvals)

    out: list[tuple[float, float, float, float]] = []
    d = dmin + spacing
    guard = 0
    while d < dmax and guard < 4000:
        guard += 1
        # 直线：nx*x + ny*y = d，参数化为 base + t*(dx,dy)
        base = (nx * d, ny * d)
        # 截到整体包围盒确定的粗区间
        p0 = (base[0] + dx * (-4000), base[1] + dy * (-4000))
        p1 = (base[0] + dx * 4000, base[1] + dy * 4000)
        for face in add_faces:
            iv = _clip_interval_to_convex(p0, p1, face)
            if not iv:
                continue
            segs = [iv]
            for hole in subs:
                nxt = []
                for (t0, t1) in segs:
                    q0 = (p0[0] + (p1[0] - p0[0]) * t0, p0[1] + (p1[1] - p0[1]) * t0)
                    q1 = (p0[0] + (p1[0] - p0[0]) * t1, p0[1] + (p1[1] - p0[1]) * t1)
                    hv = _clip_interval_to_convex(q0, q1, hole)
                    if not hv:
                        nxt.append((t0, t1))
                        continue
                    h0, h1 = hv
                    if h0 > 1e-9:
                        nxt.append((t0, t0 + (t1 - t0) * h0))
                    if h1 < 1 - 1e-9:
                        nxt.append((t0 + (t1 - t0) * h1, t1))
                segs = nxt
            for (t0, t1) in segs:
                if t1 - t0 < 1e-6:
                    continue
                ax0 = p0[0] + (p1[0] - p0[0]) * t0
                ay0 = p0[1] + (p1[1] - p0[1]) * t0
                ax1 = p0[0] + (p1[0] - p0[0]) * t1
                ay1 = p0[1] + (p1[1] - p0[1]) * t1
                out.append((round(ax0, 3), round(ay0, 3), round(ax1, 3), round(ay1, 3)))
        d += spacing
    return out


# ---------------------------------------------------------------- 组成剖视图


_SECTION_VIEW = {"y": "front", "z": "top", "x": "left"}


def build_section_view(
    solid: Solid,
    name: str,
    model_id: str,
    axis: str,
    ratio: float = 0.5,
    unit: str = "mm",
    pad: int = 46,
    gap: int = 26,
    title_h: int = 22,
    hatch_spacing: float = 6.0,
) -> dict:
    """生成剖视图 artifact：左边外形视图 + 右边剖视图（含剖面线）。"""
    from .projection import project_view, edge_segments

    bb0, bb1 = solid.bbox()
    ai = {"x": 0, "y": 1, "z": 2}[axis]
    value = bb0[ai] + (bb1[ai] - bb0[ai]) * ratio

    clipped, add_caps, sub_caps = clip_solid(solid, axis, value, keep_ge=True)

    view = _SECTION_VIEW[axis]
    cfg = VIEWS[view]
    d, u = cfg["d"], cfg["u"]
    r = _right(d, u)

    # 剖视图：裁剪后实体的投影
    seg_cut = project_view(clipped, view, edge_segments(clipped))

    # 外形视图：完整实体的投影
    seg_full = project_view(solid, view, edge_segments(solid))

    # 剖面：切面二维多边形（平面坐标 = 另两轴）
    ax = [k for k in range(3) if k != ai]
    add_faces = []
    for p in add_caps:
        f = _cap_face_in_plane(p, ai, value)
        if f:
            add_faces.append(f)
    sub_faces = []
    for p in sub_caps:
        f = _cap_face_in_plane(p, ai, value)
        if f:
            sub_faces.append(f)

    hatch2d = hatch_segments(add_faces, sub_faces, spacing=hatch_spacing)

    # 平面 (u_plane, v_plane) 与视图坐标 (u_view, v_view) 的对应：
    #   y 剖（主视）：平面轴 = (x, z) → 视图 (u=x, v=z)
    #   z 剖（俯视）：平面轴 = (x, y) → 视图 (u=x, v=y)
    #   x 剖（左视）：平面轴 = (y, z) → 视图 (u=-y, v=z)
    def plane_to_view(pu: float, pv: float) -> tuple[float, float]:
        if axis == "y":
            return (pu, pv)
        if axis == "z":
            return (pu, pv)
        return (-pu, pv)

    # 排版：左外形、右剖视
    def view_span(segs: list[dict]) -> tuple[float, float, float, float]:
        us, vs = [], []
        for s in segs:
            us += [s["u1"], s["u2"]]
            vs += [s["v1"], s["v2"]]
        return (min(us), max(us), min(vs), max(vs))

    fu0, fu1, fv0, fv1 = view_span(seg_full)
    cu0, cu1, cv0, cv1 = view_span(seg_cut)
    u0 = min(fu0, cu0)
    vmax = max(fv1, cv1)

    L1 = fu1 - fu0
    L2 = cu1 - cu0
    x_left = pad
    x_right = pad + L1 + gap
    y_top = pad + title_h

    def place(seg: dict, dx: float) -> dict:
        return {
            "x1": round(dx + (seg["u1"] - u0), 3),
            "y1": round(y_top + (vmax - seg["v1"]), 3),
            "x2": round(dx + (seg["u2"] - u0), 3),
            "y2": round(y_top + (vmax - seg["v2"]), 3),
            "hidden": seg["hidden"],
        }

    segments: list[dict] = []
    for s in seg_full:
        p = place(s, x_left)
        if math.hypot(p["x2"] - p["x1"], p["y2"] - p["y1"]) >= 1.2:
            segments.append({"view": "outline", **p})
    for s in seg_cut:
        p = place(s, x_right)
        if math.hypot(p["x2"] - p["x1"], p["y2"] - p["y1"]) >= 1.2:
            segments.append({"view": "section", **p})

    hatch = []
    for (hu1, hv1, hu2, hv2) in hatch2d:
        vu1, vv1 = plane_to_view(hu1, hv1)
        vu2, vv2 = plane_to_view(hu2, hv2)
        hatch.append({
            "x1": round(x_right + (vu1 - u0), 3),
            "y1": round(y_top + (vmax - vv1), 3),
            "x2": round(x_right + (vu2 - u0), 3),
            "y2": round(y_top + (vmax - vv2), 3),
        })

    vb_w = x_right + L2 + pad
    vb_h = y_top + (vmax - min(fv0, cv0)) + 40

    return {
        "model_id": model_id,
        "name": name,
        "unit": unit,
        "mode": "section",
        "axis": axis,
        "cut_at": round(value, 3),
        "size": {"L": round(bb1[0] - bb0[0], 3), "W": round(bb1[1] - bb0[1], 3),
                 "H": round(bb1[2] - bb0[2], 3)},
        "segments": segments,
        "hatch": hatch,
        "hatch_spacing": hatch_spacing,
        "viewBox": [0, 0, round(vb_w, 1), round(vb_h, 1)],
        "labels": [
            {"view": "outline", "text": "外形视图", "x": round(x_left + L1 / 2, 1),
             "y": round(y_top + (vmax - fv0) + 20, 1)},
            {"view": "section", "text": "剖视图（A—A）", "x": round(x_right + L2 / 2, 1),
             "y": round(y_top + (vmax - cv0) + 20, 1)},
        ],
        "aux": [],
        "view_boxes": {
            "outline": [x_left, y_top, x_left + L1, y_top + (vmax - fv0)],
            "section": [x_right, y_top, x_right + L2, y_top + (vmax - cv0)],
        },
        "projection": "第一角",
        "note": f"沿 {'XYZ'[ai]} 方向在 {value:g} mm 处剖切（保留剖切面后方材料），"
                f"剖面线 45°/间距 {hatch_spacing:g} mm",
    }


# ---------------------------------------------------------------- 半剖 / 局部剖


def _clip_seg_half(p0, p1, axis_u: bool, value: float, keep_ge: bool):
    """线段按半平面裁剪，返回 (q0, q1) 或 None。axis_u=True 按 u 剪，否则按 v。"""
    a0 = p0[0] if axis_u else p0[1]
    a1 = p1[0] if axis_u else p1[1]
    d0 = (a0 - value) if keep_ge else (value - a0)
    d1 = (a1 - value) if keep_ge else (value - a1)
    if d0 >= 0 and d1 >= 0:
        return (p0, p1)
    if d0 < 0 and d1 < 0:
        return None
    t = d0 / (d0 - d1)
    q = (p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t)
    return (q, p1) if d0 < 0 else (p0, q)


def _clip_seg_circle(p0, p1, c, r):
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    fx, fy = p0[0] - c[0], p0[1] - c[1]
    A = dx * dx + dy * dy
    if A < 1e-12:
        return (p0, p1) if (fx * fx + fy * fy <= r * r) else None
    B = 2 * (fx * dx + fy * dy)
    C = fx * fx + fy * fy - r * r
    disc = B * B - 4 * A * C
    if disc < 0:
        return (p0, p1) if C <= 0 else None
    s = math.sqrt(disc)
    t0 = (-B - s) / (2 * A)
    t1 = (-B + s) / (2 * A)
    lo, hi = max(0.0, t0), min(1.0, t1)
    if lo > hi:
        return None
    return (
        (p0[0] + dx * lo, p0[1] + dy * lo),
        (p0[0] + dx * hi, p0[1] + dy * hi),
    )


def _wavy_circle(c, r, amp: float = 2.2, waves: int = 14, seg: int = 72) -> list[tuple[float, float]]:
    """画一条手绘感的波浪线（局部剖的断裂边界）。"""
    pts = []
    for i in range(seg + 1):
        th = 2 * math.pi * i / seg
        rr = r + amp * math.sin(waves * th)
        pts.append((c[0] + rr * math.cos(th), c[1] + rr * math.sin(th)))
    return pts


def build_half_section_view(
    solid: Solid,
    name: str,
    model_id: str,
    axis: str = "y",
    unit: str = "mm",
    pad: int = 46,
    gap: int = 34,
    title_h: int = 22,
    hatch_spacing: float = 6.0,
    section_side: str = "right",
) -> dict:
    """半剖视图：以对称中心线为界，一半画视图、一半画剖视。"""
    from .projection import edge_segments, project_view

    bb0, bb1 = solid.bbox()
    ai = {"x": 0, "y": 1, "z": 2}[axis]
    value = (bb0[ai] + bb1[ai]) / 2.0

    clipped, add_caps, sub_caps = clip_solid(solid, axis, value, keep_ge=True)
    view = _SECTION_VIEW[axis]
    seg_full = project_view(solid, view, edge_segments(solid))
    seg_cut = project_view(clipped, view, edge_segments(clipped))

    # 对称中心线：取整个图形的 u 中点
    us = [s[k] for s in seg_full for k in ("u1", "u2")]
    vs = [s[k] for s in seg_full for k in ("v1", "v2")]
    u_mid = (min(us) + max(us)) / 2.0
    u0, u1, v0, v1 = min(us), max(us), min(vs), max(vs)

    # 剖面（切面多边形）+ 剖面线
    ax = [k for k in range(3) if k != ai]
    add_faces, sub_faces = [], []
    for p in add_caps:
        f = _cap_face_in_plane(p, ai, value)
        if f:
            add_faces.append(f)
    for p in sub_caps:
        f = _cap_face_in_plane(p, ai, value)
        if f:
            sub_faces.append(f)
    hatch2d = hatch_segments(add_faces, sub_faces, spacing=hatch_spacing)

    def plane_to_view(pu: float, pv: float) -> tuple[float, float]:
        return (pu, pv) if axis != "x" else (-pu, pv)

    keep_section_right = section_side == "right"
    segments: list[dict] = []
    hatch: list[dict] = []

    def place(u: float, v: float) -> tuple[float, float]:
        return (pad + (u - u0), pad + title_h + (v1 - v))

    # 视图侧
    for s in seg_full:
        r = _clip_seg_half((s["u1"], s["v1"]), (s["u2"], s["v2"]), True, u_mid,
                           keep_ge=not keep_section_right)
        if r:
            a, b = place(*r[0]), place(*r[1])
            segments.append({"view": "outline", "kind": "outline",
                             "x1": round(a[0], 3), "y1": round(a[1], 3),
                             "x2": round(b[0], 3), "y2": round(b[1], 3),
                             "hidden": s["hidden"]})
    # 剖视侧
    for s in seg_cut:
        r = _clip_seg_half((s["u1"], s["v1"]), (s["u2"], s["v2"]), True, u_mid,
                           keep_ge=keep_section_right)
        if r:
            a, b = place(*r[0]), place(*r[1])
            segments.append({"view": "section", "kind": "outline",
                             "x1": round(a[0], 3), "y1": round(a[1], 3),
                             "x2": round(b[0], 3), "y2": round(b[1], 3),
                             "hidden": s["hidden"]})
    for (hu1, hv1, hu2, hv2) in hatch2d:
        vu1, vv1 = plane_to_view(hu1, hv1)
        vu2, vv2 = plane_to_view(hu2, hv2)
        r = _clip_seg_half((vu1, vv1), (vu2, vv2), True, u_mid, keep_ge=keep_section_right)
        if r:
            a, b = place(*r[0]), place(*r[1])
            hatch.append({"x1": round(a[0], 3), "y1": round(a[1], 3),
                          "x2": round(b[0], 3), "y2": round(b[1], 3)})

    # 对称中心线（细点画线）
    ct = place(u_mid, v0)
    cb = place(u_mid, v1)
    segments.append({"view": "center", "kind": "centerline",
                     "x1": round(ct[0], 3), "y1": round(ct[1] - 8, 3),
                     "x2": round(cb[0], 3), "y2": round(cb[1] + 8, 3), "hidden": False})

    vb_w = pad * 2 + (u1 - u0)
    vb_h = pad * 2 + title_h + (v1 - v0) + 30
    return {
        "model_id": model_id, "name": name, "unit": unit, "mode": "half_section",
        "axis": axis, "cut_at": round(value, 3),
        "size": {"L": round(bb1[0] - bb0[0], 3), "W": round(bb1[1] - bb0[1], 3),
                 "H": round(bb1[2] - bb0[2], 3)},
        "segments": segments, "hatch": hatch, "hatch_spacing": hatch_spacing,
        "viewBox": [0, 0, round(vb_w, 1), round(vb_h, 1)],
        "labels": [{"view": "mixed", "text": "半剖视图（左视图 / 右剖视）",
                    "x": round(pad + (u1 - u0) / 2, 1),
                    "y": round(pad + title_h + (v1 - v0) + 20, 1)}],
        "aux": [],
        "view_boxes": {"mixed": [pad, pad + title_h, pad + (u1 - u0),
                                 pad + title_h + (v1 - v0)]},
        "projection": "第一角",
        "note": f"在 {value:g} mm 处剖开，以对称中心线为界："
                f"{'左半' if keep_section_right else '右半'}画视图、"
                f"{'右半' if keep_section_right else '左半'}画剖视。半剖只用于对称机件。",
    }


def build_local_section_view(
    solid: Solid,
    name: str,
    model_id: str,
    axis: str = "y",
    unit: str = "mm",
    pad: int = 46,
    title_h: int = 22,
    hatch_spacing: float = 5.0,
) -> dict:
    """局部剖视图：只把需要表达内部结构的一小块剖开，用波浪线分界。"""
    from .projection import edge_segments, project_view

    bb0, bb1 = solid.bbox()
    ai = {"x": 0, "y": 1, "z": 2}[axis]
    value = (bb0[ai] + bb1[ai]) / 2.0

    clipped, add_caps, sub_caps = clip_solid(solid, axis, value, keep_ge=True)
    view = _SECTION_VIEW[axis]
    seg_full = project_view(solid, view, edge_segments(solid))
    seg_cut = project_view(clipped, view, edge_segments(clipped))

    us = [s[k] for s in seg_full for k in ("u1", "u2")]
    vs = [s[k] for s in seg_full for k in ("v1", "v2")]
    u0, u1, v0, v1 = min(us), max(us), min(vs), max(vs)

    # 剖开区域：以被挖除体（孔）在视图上的位置为中心，半径取特征尺寸的 1.8 倍，
    # 太小看不清、太大会把整个视图都吃掉（那样就退化成全剖了）
    center = ((u0 + u1) / 2, (v0 + v1) / 2)
    rad = max((u1 - u0), (v1 - v0)) * 0.22
    if solid.subs:
        sb0, sb1 = solid.subs[0].bbox
        ax = [k for k in range(3) if k != ai]
        cu = (sb0[ax[0]] + sb1[ax[0]]) / 2
        cv = (sb0[ax[1]] + sb1[ax[1]]) / 2
        if axis == "x":
            cu = -cu
        center = (cu, cv)
        half = max((sb1[ax[0]] - sb0[ax[0]]) / 2, (sb1[ax[1]] - sb0[ax[1]]) / 2)
        rad = max(half * 1.8, max(u1 - u0, v1 - v0) * 0.10)

    def place(u: float, v: float) -> tuple[float, float]:
        return (pad + (u - u0), pad + title_h + (v1 - v))

    def plane_to_view(pu: float, pv: float) -> tuple[float, float]:
        return (pu, pv) if axis != "x" else (-pu, pv)

    segments: list[dict] = []
    hatch: list[dict] = []

    def push(kind_view: str, a, b, hidden: bool) -> None:
        pa, pb = place(*a), place(*b)
        if math.hypot(pb[0] - pa[0], pb[1] - pa[1]) < 1.2:
            return
        segments.append({"view": kind_view, "kind": "outline",
                         "x1": round(pa[0], 3), "y1": round(pa[1], 3),
                         "x2": round(pb[0], 3), "y2": round(pb[1], 3),
                         "hidden": hidden})

    # 圆外 = 外形视图；圆内 = 剖开后的可见轮廓（原来看不见的内部结构变成实线）
    for s in seg_full:
        p0, p1 = (s["u1"], s["v1"]), (s["u2"], s["v2"])
        for seg in _subtract_circle(p0, p1, center, rad):
            push("outline", seg[0], seg[1], s["hidden"])
        ins = _clip_seg_circle(p0, p1, center, rad)
        if ins:
            push("section", ins[0], ins[1], False)
    # 剖面线
    ax2 = [k for k in range(3) if k != ai]
    add_faces, sub_faces = [], []
    for p in add_caps:
        f = _cap_face_in_plane(p, ai, value)
        if f:
            add_faces.append(f)
    for p in sub_caps:
        f = _cap_face_in_plane(p, ai, value)
        if f:
            sub_faces.append(f)
    for (hu1, hv1, hu2, hv2) in hatch_segments(add_faces, sub_faces, spacing=hatch_spacing):
        vu1, vv1 = plane_to_view(hu1, hv1)
        vu2, vv2 = plane_to_view(hu2, hv2)
        r = _clip_seg_circle((vu1, vv1), (vu2, vv2), center, rad - 1.0)
        if r:
            a, b = place(*r[0]), place(*r[1])
            hatch.append({"x1": round(a[0], 3), "y1": round(a[1], 3),
                          "x2": round(b[0], 3), "y2": round(b[1], 3)})

    # 波浪线
    wave_uv = _wavy_circle(center, rad)
    for i in range(len(wave_uv) - 1):
        a, b = place(*wave_uv[i]), place(*wave_uv[i + 1])
        segments.append({"view": "wave", "kind": "wave",
                         "x1": round(a[0], 3), "y1": round(a[1], 3),
                         "x2": round(b[0], 3), "y2": round(b[1], 3), "hidden": False})

    vb_w = pad * 2 + (u1 - u0)
    vb_h = pad * 2 + title_h + (v1 - v0) + 30
    return {
        "model_id": model_id, "name": name, "unit": unit, "mode": "local_section",
        "axis": axis, "cut_at": round(value, 3),
        "region": {"u": round(center[0], 3), "v": round(center[1], 3), "r": round(rad, 3)},
        "size": {"L": round(bb1[0] - bb0[0], 3), "W": round(bb1[1] - bb0[1], 3),
                 "H": round(bb1[2] - bb0[2], 3)},
        "segments": segments, "hatch": hatch, "hatch_spacing": hatch_spacing,
        "viewBox": [0, 0, round(vb_w, 1), round(vb_h, 1)],
        "labels": [{"view": "local", "text": "局部剖视图（波浪线分界）",
                    "x": round(pad + (u1 - u0) / 2, 1),
                    "y": round(pad + title_h + (v1 - v0) + 20, 1)}],
        "aux": [],
        "view_boxes": {"local": [pad, pad + title_h, pad + (u1 - u0),
                                 pad + title_h + (v1 - v0)]},
        "projection": "第一角",
        "note": "只在需要表达内部结构的一小块剖开，波浪线是断裂边界；"
                "波浪线不能与其他图线重合，也不能画进孔内。",
    }


def _dist(p, c) -> float:
    return math.hypot(p[0] - c[0], p[1] - c[1])


def _subtract_circle(p0, p1, c, r) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    """线段减去圆内部分，返回剩下的若干段。"""
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    A = dx * dx + dy * dy
    if A < 1e-12:
        return []
    fx, fy = p0[0] - c[0], p0[1] - c[1]
    B = 2 * (fx * dx + fy * dy)
    C = fx * fx + fy * fy - r * r
    disc = B * B - 4 * A * C
    if disc < 0:
        return [((p0[0], p0[1]), (p1[0], p1[1]))]
    s = math.sqrt(disc)
    t0 = max(0.0, (-B - s) / (2 * A))
    t1 = min(1.0, (-B + s) / (2 * A))
    out = []
    if t0 > 1e-9:
        out.append(((p0[0], p0[1]), (p0[0] + dx * t0, p0[1] + dy * t0)))
    if t1 < 1 - 1e-9:
        out.append(((p0[0] + dx * t1, p0[1] + dy * t1), (p1[0], p1[1])))
    return out
