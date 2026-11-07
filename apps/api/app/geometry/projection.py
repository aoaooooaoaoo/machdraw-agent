"""三视图真投影：隐藏线消除（HLR）+ 三视图排版 + 投影辅助线。

原理（标准做法，不是"画个样子"）：
  1. 从 CSG 实体中提取候选棱边：**锐边**（二面角 > 阈值）与**轮廓线**（相邻面一正一背）；
  2. 按视角把棱边投到视平面（第一角投影的三个方向）；
  3. 沿每条棱采样，从采样点朝**观察者**方向投射射线：若中途穿过实体 → 该段被遮挡 → 画虚线；
  4. 按「长对正、高平齐、宽相等」排版到同一张图纸坐标系（y 轴向下，前端可直接画）。

坐标约定：X 向右、Y 向后（远离观察者）、Z 向上；单位与模型一致（mm）。
"""
from __future__ import annotations

import math

from .solid import Solid, Vec, dot, edge_segments, norm, sub

# 三个视图的投射方向 d（射入屏幕）与上方向 u；右方向 right = d × u
VIEWS: dict[str, dict] = {
    "front": {"d": (0.0, 1.0, 0.0), "u": (0.0, 0.0, 1.0), "label": "主视图"},
    "top": {"d": (0.0, 0.0, -1.0), "u": (0.0, 1.0, 0.0), "label": "俯视图"},
    "left": {"d": (1.0, 0.0, 0.0), "u": (0.0, 0.0, 1.0), "label": "左视图"},
}


def _right(d: Vec, u: Vec) -> Vec:
    # right = d × u
    return (
        d[1] * u[2] - d[2] * u[1],
        d[2] * u[0] - d[0] * u[2],
        d[0] * u[1] - d[1] * u[0],
    )


def _occluded(solid: Solid, p: Vec, d: Vec, diag: float, steps: int = 48) -> bool:
    """从 p 沿 -d（朝观察者）走，是否有实体挡在前面。"""
    step = diag / steps
    t = step * 0.5
    x, y, z = p
    q = (x - d[0] * t, y - d[1] * t, z - d[2] * t)
    for _ in range(steps):
        if solid.inside(q):
            return True
        q = (q[0] - d[0] * step, q[1] - d[1] * step, q[2] - d[2] * step)
    return False


def _covers(v: dict, h: dict, tol: float = 5e-3) -> bool:
    """可见段 v 是否在投影上完全盖住隐藏段 h（同一直线且区间包含）。"""
    dx1, dy1 = v["u2"] - v["u1"], v["v2"] - v["v1"]
    dx2, dy2 = h["u2"] - h["u1"], h["v2"] - h["v1"]
    L1 = math.hypot(dx1, dy1)
    L2 = math.hypot(dx2, dy2)
    if L1 < 1e-9 or L2 < 1e-9:
        return False
    ux, uy = dx1 / L1, dy1 / L1
    if abs(ux * dy2 / L2 - uy * dx2 / L2) > 2e-3:
        return False
    for u, vv in ((h["u1"], h["v1"]), (h["u2"], h["v2"])):
        if abs((u - v["u1"]) * uy - (vv - v["v1"]) * ux) > tol:
            return False

    def t(u: float, vv: float) -> float:
        return (u - v["u1"]) * ux + (vv - v["v1"]) * uy

    t1, t2 = sorted((t(h["u1"], h["v1"]), t(h["u2"], h["v2"])))
    return t1 >= -tol and t2 <= L1 + tol


def _suppress_covered(segs: list[dict]) -> list[dict]:
    """被可见线完全盖住的隐藏线不画（工程图惯例：可见优先）。"""
    vis = [s for s in segs if not s["hidden"]]
    if not vis:
        return segs
    out = []
    for s in segs:
        if not s["hidden"]:
            out.append(s)
            continue
        if any(_covers(v, s) for v in vis):
            continue
        out.append(s)
    return out


def _merge_collinear(segs: list[dict], tol: float = 5e-3) -> list[dict]:
    """把共线且相接/重叠的同状态线段合并成一条（否则一条直线会被拆成好几段）。"""
    def key(s: dict) -> tuple:
        du, dv = s["u2"] - s["u1"], s["v2"] - s["v1"]
        L = math.hypot(du, dv)
        if L < 1e-9:
            return ("pt", round(s["u1"], 3), round(s["v1"], 3), s["hidden"])
        ux, uy = du / L, dv / L
        # 方向取同侧（避免 180° 不同组）
        if ux < -1e-9 or (abs(ux) <= 1e-9 and uy < 0):
            ux, uy = -ux, -uy
        off = (s["u1"] * uy - s["v1"] * ux)
        return (round(ux, 3), round(uy, 3), round(off, 3), s["hidden"])

    groups: dict[tuple, list[dict]] = {}
    for s in segs:
        groups.setdefault(key(s), []).append(s)

    out: list[dict] = []
    for k, group in groups.items():
        if k[0] == "pt":
            out.extend(group)
            continue
        ux, uy = k[0], k[1]
        # 以 (u,v)·dir 参数化区间
        spans = []
        for s in group:
            t1 = s["u1"] * ux + s["v1"] * uy
            t2 = s["u2"] * ux + s["v2"] * uy
            lo, hi = min(t1, t2), max(t1, t2)
            spans.append([lo, hi])
        spans.sort()
        merged = [spans[0]]
        for lo, hi in spans[1:]:
            if lo <= merged[-1][1] + tol:
                merged[-1][1] = max(merged[-1][1], hi)
            else:
                merged.append([lo, hi])
        # 由 (t) 反算点：取该组第一段起点作基点
        base = group[0]
        bu = base["u1"] * ux + base["v1"] * uy
        b_u, b_v = base["u1"], base["v1"]
        for lo, hi in merged:
            out.append({
                "u1": round(b_u + (lo - bu) * ux, 4),
                "v1": round(b_v + (lo - bu) * uy, 4),
                "u2": round(b_u + (hi - bu) * ux, 4),
                "v2": round(b_v + (hi - bu) * uy, 4),
                "hidden": k[3],
            })
    return out


def project_view(solid: Solid, view: str, edges: list[dict], samples: int = 14) -> list[dict]:
    """把一个视图的可见/不可见线段算出来（坐标为视图局部坐标 u/v）。"""
    cfg = VIEWS[view]
    d, u = cfg["d"], cfg["u"]
    r = _right(d, u)
    bb0, bb1 = solid.bbox()
    diag = norm(sub(bb1, bb0)) or 1.0

    polys = solid.adds + solid.subs
    out: list[dict] = []

    for e in edges:
        # 只有锐边或轮廓线才画
        is_sil = False
        for pi, fi in e["faces"]:
            if pi < len(polys):
                n = polys[pi].face_normal(fi)
                if abs(dot(n, d)) < 1e-6:
                    continue          # 与视线平行，不构成本视角轮廓
                facing_cam = dot(n, d) < 0
                # 该面在本视角是否"正面"由下面统计；这里先记录
        facings = []
        for pi, fi in e["faces"]:
            if pi >= len(polys):
                continue
            n = polys[pi].face_normal(fi)
            facings.append(dot(n, d) < 0)
        if len(facings) >= 2 and facings[0] != facings[1]:
            is_sil = True
        if not (e["sharp"] or is_sil):
            continue

        p, q = e["p"], e["q"]
        # 沿棱采样，逐点判遮挡
        hidden_flags: list[bool] = []
        for i in range(samples + 1):
            t = i / samples
            pt = (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t, p[2] + (q[2] - p[2]) * t)
            hidden_flags.append(_occluded(solid, pt, d, diag))

        # 合并同状态的连续区间
        start = 0
        for i in range(1, samples + 2):
            if i == samples + 1 or hidden_flags[i] != hidden_flags[start]:
                t0, t1 = start / samples, (i - 1) / samples
                if t1 - t0 > 1e-9:
                    a = (p[0] + (q[0] - p[0]) * t0, p[1] + (q[1] - p[1]) * t0, p[2] + (q[2] - p[2]) * t0)
                    b = (p[0] + (q[0] - p[0]) * t1, p[1] + (q[1] - p[1]) * t1, p[2] + (q[2] - p[2]) * t1)
                    out.append({
                        "u1": round(dot(a, r), 4), "v1": round(dot(a, u), 4),
                        "u2": round(dot(b, r), 4), "v2": round(dot(b, u), 4),
                        "hidden": hidden_flags[start],
                    })
                start = i
    # 投影成一点（沿视线方向的棱）不画
    out = [s for s in out if math.hypot(s["u2"] - s["u1"], s["v2"] - s["v1"]) > 1e-6]
    return _suppress_covered(_merge_collinear(_dedupe(out)))


def _dedupe(segs: list[dict]) -> list[dict]:
    """同一条线上重复的段去重（并集处两个体共享的棱会采到两次）。"""
    seen = set()
    out = []
    for s in segs:
        k = (
            min(s["u1"], s["u2"]), max(s["u1"], s["u2"]),
            min(s["v1"], s["v2"]), max(s["v1"], s["v2"]),
            s["hidden"],
        )
        key = tuple(round(x, 3) if isinstance(x, float) else x for x in k)
        if key in seen:
            continue
        seen.add(key)
        out.append(s)
    return out


def build_three_view(
    solid: Solid,
    name: str,
    model_id: str,
    unit: str = "mm",
    pad: int = 46,
    gap: int = 40,
    title_h: int = 22,
) -> dict:
    """生成三视图 artifact 的 data（坐标已排好版，y 轴向下，前端可直接画）。"""
    edges = edge_segments(solid)
    bb0, bb1 = solid.bbox()
    L, W, H = bb1[0] - bb0[0], bb1[1] - bb0[1], bb1[2] - bb0[2]

    # 三个视图的局部坐标 → 图纸坐标
    x0f = pad
    y0f = pad + title_h
    top_base = y0f + H + gap
    left_base = x0f + L + gap

    def to_sheet(view: str, u: float, v: float) -> tuple[float, float]:
        if view == "front":
            return (x0f + (u - bb0[0]), y0f + (bb1[2] - v))
        if view == "top":
            return (x0f + (u - bb0[0]), top_base + (bb1[1] - v))
        # left: u = -y
        return (left_base + (-v - (-bb1[1])), y0f + (bb1[2] - u))

    # 注意：left 视图的 u/v 含义与 front/top 不同（u=-y, v=z），上面已分别处理
    def left_sheet(u: float, v: float) -> tuple[float, float]:
        return (left_base + (bb1[1] + u), y0f + (bb1[2] - v))

    segments: list[dict] = []
    stats: dict[str, dict] = {}
    for view in ("front", "top", "left"):
        segs = project_view(solid, view, edges)
        stats[view] = {
            "total": len(segs),
            "visible": sum(1 for s in segs if not s["hidden"]),
            "hidden": sum(1 for s in segs if s["hidden"]),
        }
        for s in segs:
            if view == "left":
                a = left_sheet(s["u1"], s["v1"])
                b = left_sheet(s["u2"], s["v2"])
            else:
                a = to_sheet(view, s["u1"], s["v1"])
                b = to_sheet(view, s["u2"], s["v2"])
            segments.append({
                "view": view,
                "x1": round(a[0], 3), "y1": round(a[1], 3),
                "x2": round(b[0], 3), "y2": round(b[1], 3),
                "hidden": s["hidden"],
            })

    right_edge = left_base + W
    bottom = top_base + W
    vb_w = right_edge + pad
    vb_h = bottom + 34

    labels = [
        {"view": "front", "text": "主视图", "x": round(x0f + L / 2, 1), "y": round(y0f + H + 18, 1)},
        {"view": "top", "text": "俯视图", "x": round(x0f + L / 2, 1), "y": round(bottom + 18, 1)},
        {"view": "left", "text": "左视图", "x": round(left_base + W / 2, 1), "y": round(y0f + H + 18, 1)},
    ]

    # 投影辅助线：长对正（竖）、高平齐（横）、宽相等（45° 线 + 连接线）
    aux = [
        {"kind": "long", "color": "#2563eb", "x1": x0f, "y1": y0f, "x2": x0f, "y2": bottom,
         "label": "长对正"},
        {"kind": "long", "color": "#2563eb", "x1": x0f + L, "y1": y0f, "x2": x0f + L, "y2": bottom,
         "label": ""},
        {"kind": "height", "color": "#16a34a", "x1": x0f, "y1": y0f, "x2": right_edge, "y2": y0f,
         "label": "高平齐"},
        {"kind": "height", "color": "#16a34a", "x1": x0f, "y1": y0f + H, "x2": right_edge,
         "y2": y0f + H, "label": ""},
        # 45° 线过 (left_base, top_base)：深度 d 在俯视图是 Y=top_base+d，在左视图是 X=left_base+d
        {"kind": "width", "color": "#d97706", "x1": left_base, "y1": top_base,
         "x2": left_base + W, "y2": top_base + W, "label": "宽相等"},
        {"kind": "width", "color": "#d97706", "x1": x0f + L, "y1": top_base,
         "x2": left_base, "y2": top_base, "label": ""},
        {"kind": "width", "color": "#d97706", "x1": left_base, "y1": top_base,
         "x2": left_base, "y2": y0f + H, "label": ""},
        {"kind": "width", "color": "#d97706", "x1": x0f + L, "y1": bottom,
         "x2": left_base + W, "y2": bottom, "label": ""},
        {"kind": "width", "color": "#d97706", "x1": left_base + W, "y1": bottom,
         "x2": left_base + W, "y2": y0f + H, "label": ""},
    ]

    return {
        "model_id": model_id,
        "name": name,
        "unit": unit,
        "size": {"L": round(L, 3), "W": round(W, 3), "H": round(H, 3)},
        "bbox": [list(bb0), list(bb1)],
        "segments": segments,
        "stats": stats,
        "viewBox": [0, 0, round(vb_w, 1), round(vb_h, 1)],
        "labels": labels,
        "aux": aux,
        "view_boxes": {
            "front": [x0f, y0f, x0f + L, y0f + H],
            "top": [x0f, top_base, x0f + L, bottom],
            "left": [left_base, y0f, right_edge, y0f + H],
        },
        "projection": "第一角",
    }


# ---------------------------------------------------------------- SVG 导出（离线预览用）


def to_svg(data: dict, width: int = 720) -> str:
    vb = data["viewBox"]
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb[0]} {vb[1]} {vb[2]} {vb[3]}" '
        f'width="{width}" font-family="system-ui, sans-serif">',
        f'<rect x="0" y="0" width="{vb[2]}" height="{vb[3]}" fill="#ffffff"/>',
        '<g id="aux" opacity="0.75">',
    ]
    for a in data["aux"]:
        parts.append(
            f'<line x1="{a["x1"]}" y1="{a["y1"]}" x2="{a["x2"]}" y2="{a["y2"]}" '
            f'stroke="{a["color"]}" stroke-width="0.8" stroke-dasharray="5 4"/>'
        )
    # 标签单独一轮，避免与线条一起叠在左上角
    for a in data["aux"]:
        if not a.get("label"):
            continue
        kind = a.get("kind")
        if kind == "long":          # 竖线，标在底端
            lx, ly = a["x1"] + 5, a["y2"] - 6
        elif kind == "height":      # 横线，标在左端上方
            lx, ly = a["x1"] + 6, a["y1"] - 6
        else:                        # 45° 线，标在中点右侧
            lx, ly = (a["x1"] + a["x2"]) / 2 + 8, (a["y1"] + a["y2"]) / 2
        parts.append(
            f'<text x="{lx}" y="{ly}" font-size="10" fill="{a["color"]}" '
            f'opacity="0.95">{a["label"]}</text>'
        )
    parts.append("</g><g id=\"hatch\">")
    for h in data.get("hatch") or []:
        parts.append(
            f'<line x1="{h["x1"]}" y1="{h["y1"]}" x2="{h["x2"]}" y2="{h["y2"]}" '
            f'stroke="#6b7280" stroke-width="0.7"/>'
        )
    parts.append("</g><g id=\"views\">")
    for s in data["segments"]:
        dash = ' stroke-dasharray="6 4"' if s["hidden"] else ""
        color = "#94a3b8" if s["hidden"] else "#111827"
        w = 1.0 if s["hidden"] else 1.9
        parts.append(
            f'<line x1="{s["x1"]}" y1="{s["y1"]}" x2="{s["x2"]}" y2="{s["y2"]}" '
            f'stroke="{color}" stroke-width="{w}"{dash} stroke-linecap="round"/>'
        )
    parts.append("</g>")
    for lb in data["labels"]:
        parts.append(
            f'<text x="{lb["x"]}" y="{lb["y"]}" font-size="12" text-anchor="middle" '
            f'fill="#374151">{lb["text"]}</text>'
        )
    parts.append(
        f'<text x="12" y="20" font-size="12" fill="#6b7280">{data["name"]} · '
        f'{data["size"]["L"]:g}×{data["size"]["W"]:g}×{data["size"]["H"]:g} {data["unit"]} · '
        f'{data["projection"]}</text>'
    )
    parts.append("</svg>")
    return "\n".join(parts)
