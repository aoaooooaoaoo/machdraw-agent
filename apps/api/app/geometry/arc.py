"""圆弧连接（平面图形作图）几何计算引擎。

依据
----
* GB/T 4458.4-2003《机械制图 尺寸注法》中关于圆弧连接作图的规定；
* 教材"平面图形画法"中圆弧连接的四种基本类型：
  直线—直线（圆角）、直线—圆弧、圆弧—圆弧外切、圆弧—圆弧内切。

本模块只做"确定性的几何计算"：给定半径、直线、圆等要素，用解析几何求出圆心与切点，
并把作图过程拆成可逐帧播放的分步脚本（供前端"作图步骤动画"画布直接使用）。

核心几何依据
------------
1. 圆与直线相切：圆心到直线的距离等于半径 r，切点是圆心到直线的垂足。
2. 圆与圆外切：两圆心距等于两半径之和，切点在两圆心连线上。
3. 圆与圆内切：两圆心距等于两半径之差，切点也在两圆心连线上。
4. 两直线间圆弧连接（圆角）：圆心在角平分线上，距两直线均为 r，
   即距交点 V 的距离为 r / sin(θ/2)（θ 为两直线夹角）；切点为两条垂足。

坐标统一用 ``tuple[float, float]``，数值保留 6 位小数；所有结果都是纯数据（可 JSON 序列化），
不依赖网络、不依赖大模型、只用 Python 标准库 ``math``。

绘图指令（``draw`` 字段）格式
-----------------------------
* 直线：``{"op": "line", "a": [x, y], "b": [x, y]}``
* 圆弧：``{"op": "arc", "c": [x, y], "r": R, "start_angle": a, "end_angle": b}``
  角度单位为度，逆时针为正；本模块保证 start→end 逆时针为**劣弧**。
* 点：``{"op": "point", "p": [x, y], "label": "O"}``
"""
from __future__ import annotations

import math
from typing import Any, Sequence

__all__ = [
    "arc_to_line",
    "connect_arc_to_line",
    "connect_arc_to_arc",
    "build_steps",
    "fillet_two_lines",
]

Point = tuple[float, float]
Line = tuple[Point, Point]

_EPS = 1e-12


# ---------------------------------------------------------------------------
# 向量工具
# ---------------------------------------------------------------------------


def _pt(value: Sequence[float]) -> Point:
    if len(value) != 2:
        raise ValueError(f"坐标必须是 (x, y) 二元组，收到 {value!r}")
    try:
        x, y = float(value[0]), float(value[1])
    except (TypeError, ValueError) as exc:  # pragma: no cover - 防御式
        raise ValueError(f"坐标必须是数值，收到 {value!r}") from exc
    if not (math.isfinite(x) and math.isfinite(y)):
        raise ValueError(f"坐标必须是有限数值，收到 {value!r}")
    return (_r6(x), _r6(y))


def _r6(value: float) -> float:
    result = round(float(value), 6)
    return 0.0 if result == 0 else result


def _sub(a: Point, b: Point) -> Point:
    return (a[0] - b[0], a[1] - b[1])


def _add(a: Point, b: Point) -> Point:
    return (a[0] + b[0], a[1] + b[1])


def _mul(a: Point, k: float) -> Point:
    return (a[0] * k, a[1] * k)


def _dot(a: Point, b: Point) -> float:
    return a[0] * b[0] + a[1] * b[1]


def _cross(a: Point, b: Point) -> float:
    return a[0] * b[1] - a[1] * b[0]


def _norm(a: Point) -> float:
    return math.hypot(a[0], a[1])


def _unit(a: Point) -> Point:
    n = _norm(a)
    if n <= _EPS:
        raise ValueError("两点重合，无法确定方向")
    return (a[0] / n, a[1] / n)


def _dist(a: Point, b: Point) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _left_normal(u: Point) -> Point:
    """单位方向 u 的左法向（逆时针旋转 90°）。"""
    return (-u[1], u[0])


def _angle_deg(center: Point, point: Point) -> float:
    """point 相对 center 的方位角（度，[0, 360)）。"""
    angle = math.degrees(math.atan2(point[1] - center[1], point[0] - center[0]))
    return _r6(angle % 360.0)


def _arc_draw(center: Point, r: float, p_start: Point, p_end: Point) -> dict:
    """构造从 p_start 到 p_end、圆心 center、半径 r 的**劣弧**绘图指令。

    保证 start→end 逆时针扫过的圆心角 ≤ 180°。
    """
    start = _angle_deg(center, p_start)
    end = _angle_deg(center, p_end)
    delta = (end - start) % 360.0
    if delta > 180.0 + 1e-9:
        # 逆时针走劣弧需从另一端画起
        start, end = end, start
    return {
        "op": "arc",
        "c": [center[0], center[1]],
        "r": _r6(r),
        "start_angle": _r6(start),
        "end_angle": _r6(end),
    }


def _line_draw(a: Point, b: Point) -> dict:
    return {"op": "line", "a": [a[0], a[1]], "b": [b[0], b[1]]}


def _point_draw(p: Point, label: str = "") -> dict:
    return {"op": "point", "p": [p[0], p[1]], "label": label}


def _check_radius(r: float) -> float:
    try:
        value = float(r)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"圆弧半径必须是数值，收到 {r!r}") from exc
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"圆弧半径必须大于 0，收到 {r!r}")
    return value


def _perp_foot(point: Point, line_start: Point, line_dir_unit: Point) -> Point:
    """point 到直线（过 line_start、方向 line_dir_unit）的垂足。"""
    t = _dot(_sub(point, line_start), line_dir_unit)
    return _add(line_start, _mul(line_dir_unit, t))


# ---------------------------------------------------------------------------
# 基础要素函数
# ---------------------------------------------------------------------------


def arc_to_line(r: float, p1: Sequence[float], p2: Sequence[float], side: int = 1) -> dict:
    """求与已知直线相切、半径为 r 的圆弧圆心轨迹与代表圆心。

    参数
    ----
    r:    圆弧半径（>0）
    p1:   直线上一点
    p2:   直线上另一点
    side: +1 表示取直线"左侧"（沿 p1→p2 方向左手法向）的圆心，-1 取右侧

    返回
    ----
    ``{"r", "side", "line", "center_locus", "center", "tangent_on_line",
       "normal", "formula", "draw"}``

    几何依据
    --------
    与直线相切、半径 r 的圆，其圆心一定落在与已知直线平行且距离为 r 的
    两条平行线之一上；切点是圆心向已知直线所作垂线的垂足。本函数返回指定一侧
    的圆心轨迹（平行线）和一个代表圆心（取 p1、p2 中点对应的垂足再偏移 r）。
    """
    radius = _check_radius(r)
    if side not in (1, -1):
        raise ValueError(f"side 只能取 +1 或 -1，收到 {side!r}")
    a, b = _pt(p1), _pt(p2)
    if _dist(a, b) <= 1e-9:
        raise ValueError("直线两个端点重合，无法确定直线方向")
    u = _unit(_sub(b, a))
    normal = _left_normal(u)
    offset = _mul(normal, side * radius)

    locus_a = _add(a, offset)
    locus_b = _add(b, offset)
    mid = _mul(_add(a, b), 0.5)
    center = _add(mid, offset)
    tangent = mid

    return {
        "r": _r6(radius),
        "side": side,
        "line": [[a[0], a[1]], [b[0], b[1]]],
        "normal": [normal[0], normal[1]],
        "center_locus": [
            [locus_a[0], locus_a[1]],
            [locus_b[0], locus_b[1]],
        ],
        "center": center,
        "tangent_on_line": tangent,
        "formula": (
            "圆心到已知直线的距离等于 r，因此圆心轨迹是与已知直线平行、相距 r 的两条平行线；"
            "在指定一侧取其中一条。切点是圆心向已知直线所作垂线的垂足。"
        ),
        "draw": [
            _line_draw(a, b),
            _line_draw(locus_a, locus_b),
            _point_draw(center, "O"),
            _point_draw(tangent, "T"),
        ],
    }


def connect_arc_to_line(
    r: float,
    line_p1: Sequence[float],
    line_p2: Sequence[float],
    through_point: Sequence[float],
    side: int | None = None,
) -> dict:
    """用半径 r 的圆弧连接已知直线与已知点（圆弧与直线相切且通过该点）。

    参数
    ----
    r:             圆弧半径（>0）
    line_p1/p2:    已知直线上的两点
    through_point: 圆弧必须经过的点 P
    side:          可选，限定圆心在直线的哪一侧（+1 左 / -1 右）；None 时自动选择

    返回
    ----
    ``{"center", "tangent_on_line", "through_point", "r", "solutions",
       "formula", "draw"}``

    几何依据
    --------
    联立两个条件：
    ① 圆心 C 到已知直线的距离 = r  →  C 在距直线 r 的平行线上；
    ② |C − P| = r                  →  C 在以 P 为圆心、r 为半径的圆上。

    令 A′ 为平行线上一点、u 为直线单位方向，设 C = A′ + t·u，
    记 w = A′ − P，则②化为关于 t 的一元二次方程::

        t² + 2(w·u)t + |w|² − r² = 0

    判别式 ≥ 0 时有解；解出 t 即得圆心，再由垂足得直线上切点。
    """
    radius = _check_radius(r)
    a, b = _pt(line_p1), _pt(line_p2)
    p = _pt(through_point)
    if _dist(a, b) <= 1e-9:
        raise ValueError("直线两个端点重合，无法确定直线方向")
    u = _unit(_sub(b, a))
    normal = _left_normal(u)
    sides = (side,) if side in (1, -1) else (1, -1)

    solutions: list[dict] = []
    for s in sides:
        offset = _mul(normal, s * radius)
        a_prime = _add(a, offset)
        w = _sub(a_prime, p)
        half_b = _dot(w, u)
        c = _dot(w, w) - radius * radius
        disc = half_b * half_b - c
        if disc < -1e-9:
            continue
        disc = max(disc, 0.0)
        root = math.sqrt(disc)
        for t in (-half_b - root, -half_b + root):
            center = _add(a_prime, _mul(u, t))
            tangent = _add(a, _mul(u, t))
            solutions.append(
                {
                    "center": (_r6(center[0]), _r6(center[1])),
                    "tangent_on_line": (_r6(tangent[0]), _r6(tangent[1])),
                    "side": s,
                    "t": _r6(t),
                    "arc_svg": _arc_draw(center, radius, tangent, p),
                }
            )

    if not solutions:
        raise ValueError(
            f"半径 r={radius:g} 的圆弧无法同时与已知直线相切并通过点 "
            f"({p[0]:g}, {p[1]:g})：点到直线的距离小于 2r 时无解，请增大半径或调整位置"
        )

    # 去重（两侧重合的情况）并稳定排序：先按指定 side，再按 t 从小到大
    unique: list[dict] = []
    for item in solutions:
        if all(
            _dist(item["center"], other["center"]) > 1e-9 for other in unique
        ):
            unique.append(item)
    if side in (1, -1):
        unique.sort(key=lambda d: (0 if d["side"] == side else 1, d["t"]))
    else:
        unique.sort(key=lambda d: (0 if d["side"] == 1 else 1, d["t"]))

    best = unique[0]
    draw = [
        _line_draw(a, b),
        _point_draw(best["center"], "O"),
        _point_draw(best["tangent_on_line"], "T"),
        _point_draw(p, "P"),
        best["arc_svg"],
    ]
    return {
        "r": _r6(radius),
        "center": best["center"],
        "tangent_on_line": best["tangent_on_line"],
        "through_point": p,
        "solutions": unique,
        "formula": (
            "联立：① 圆心到直线距离 = r（圆心在距直线 r 的平行线上）；"
            "② 圆心到 P 点距离 = r（圆心在以 P 为圆心、r 为半径的圆上）。"
            "令圆心 C = A′ + t·u（A′ 为平行线上的起点），得一元二次方程 "
            "t² + 2(w·u)t + |w|² − r² = 0（w = A′ − P），解出 t 后作垂线即得切点。"
        ),
        "draw": draw,
    }


def connect_arc_to_arc(
    r: float,
    c1: Sequence[float],
    r1: float,
    c2: Sequence[float],
    r2: float,
    kind: str = "outer",
) -> dict:
    """用半径 r 的圆弧连接两个已知圆（外切或内切）。

    参数
    ----
    r:     连接圆弧半径（>0）
    c1/r1: 第一个已知圆的圆心与半径
    c2/r2: 第二个已知圆的圆心与半径
    kind:  ``"outer"``（外切，默认）或 ``"inner"``（内切）

    返回
    ----
    ``{"kind", "radius", "center", "centers", "tangent_points",
       "solutions", "formula", "svg_paths", "draw"}``

    几何依据
    --------
    * 外切：|C − O1| = r1 + r，|C − O2| = r2 + r；
    * 内切：|C − O1| = |r1 − r|，|C − O2| = |r2 − r|。

    即圆心 C 是"以 O1 为圆心、R1 为半径"与"以 O2 为圆心、R2 为半径"两圆的交点。
    切点位于两圆心连线上：T1 = O1 + (C−O1)/|C−O1| · r1，T2 同理。
    """
    radius = _check_radius(r)
    o1, o2 = _pt(c1), _pt(c2)
    rr1 = _check_radius(r1)
    rr2 = _check_radius(r2)
    kind_norm = _norm_arc_kind(kind)

    if kind_norm == "outer":
        big1, big2 = rr1 + radius, rr2 + radius
    else:
        big1, big2 = abs(rr1 - radius), abs(rr2 - radius)

    d = _dist(o1, o2)
    if d <= 1e-9:
        raise ValueError("两个已知圆的圆心重合，无法求连接弧圆心")
    if d > big1 + big2 + 1e-9:
        raise ValueError(
            f"两已知圆相距 {d:.6f}，大于所需半径之和 {big1 + big2:.6f}："
            "圆弧无法同时与两圆相切（请增大连接半径）"
        )
    if d < abs(big1 - big2) - 1e-9:
        raise ValueError(
            f"两已知圆相距 {d:.6f}，小于两半径之差 {abs(big1 - big2):.6f}："
            "一个圆完全包含另一个，圆弧无法同时相切（请调整半径）"
        )

    u = _unit(_sub(o2, o1))
    a = (big1 * big1 - big2 * big2 + d * d) / (2.0 * d)
    h_sq = big1 * big1 - a * a
    h = math.sqrt(max(h_sq, 0.0))
    base = _add(o1, _mul(u, a))
    n = _left_normal(u)

    centers = [base] if h <= 1e-9 else [_add(base, _mul(n, h)), _sub(base, _mul(n, h))]
    solutions: list[dict] = []
    for center in centers:
        u1 = _unit(_sub(center, o1))
        u2 = _unit(_sub(center, o2))
        t1 = _add(o1, _mul(u1, rr1))
        t2 = _add(o2, _mul(u2, rr2))
        solutions.append(
            {
                "center": (_r6(center[0]), _r6(center[1])),
                "tangent_points": [
                    (_r6(t1[0]), _r6(t1[1])),
                    (_r6(t2[0]), _r6(t2[1])),
                ],
                "arc_svg": _arc_draw(center, radius, t1, t2),
            }
        )

    best = solutions[0]
    draw: list[dict] = [
        _circle_draw(o1, rr1, "O1"),
        _circle_draw(o2, rr2, "O2"),
        _point_draw(best["center"], "O"),
        _point_draw(best["tangent_points"][0], "T1"),
        _point_draw(best["tangent_points"][1], "T2"),
        best["arc_svg"],
    ]
    return {
        "kind": kind_norm,
        "radius": _r6(radius),
        "center": best["center"],
        "centers": [solution["center"] for solution in solutions],
        "tangent_points": [solution["tangent_points"] for solution in solutions],
        "solutions": solutions,
        "formula": (
            "外切：|C−O1| = r1 + r，|C−O2| = r2 + r；内切：|C−O1| = |r1 − r|，"
            "|C−O2| = |r2 − r|。圆心 C 为以 O1、O2 为圆心、相应半径的两圆交点；"
            "切点位于两圆心连线上，即 T1 = O1 + (C−O1)/|C−O1|·r1。"
        ),
        "svg_paths": draw,
        "draw": draw,
    }


def _circle_draw(center: Point, r: float, label: str = "") -> dict:
    return {
        "op": "circle",
        "c": [center[0], center[1]],
        "r": _r6(r),
        "label": label,
    }


def _norm_arc_kind(kind: str) -> str:
    text = str(kind).strip().lower().replace("_", "").replace("-", "").replace(" ", "")
    if text in ("outer", "external", "外切", "外", "waigie", "waiqie"):
        return "outer"
    if text in ("inner", "internal", "内切", "内", "neiqie", "neiqie"):
        return "inner"
    raise ValueError(
        f"未知的圆弧连接类型 {kind!r}：kind 只支持 'outer'（外切）或 'inner'（内切）"
    )


# ---------------------------------------------------------------------------
# 两直线圆角
# ---------------------------------------------------------------------------


def fillet_two_lines(
    r: float,
    line1: Sequence[Sequence[float]],
    line2: Sequence[Sequence[float]],
) -> dict:
    """求两直线间半径为 r 的圆角（圆弧连接）的圆心与切点。

    参数
    ----
    r:     圆角半径
    line1: ``(p1, p2)`` 第一条直线上的两点（p1→p2 确定方向，也确定取哪一侧的圆角）
    line2: ``(p3, p4)`` 第二条直线上的两点

    返回
    ----
    ``{"r", "center", "tangents", "intersection", "angle_deg", "draw",
       "formula", "arc_svg"}``

    几何依据
    --------
    圆心须同时距两直线 r，因此圆心在两条角平分线上、距交点 V 的距离为
    ``r / sin(θ/2)``（θ 为两直线夹角）。对每个候选圆心，若它到两直线的垂足
    都落在给定射线方向上，即为所求圆角；垂足即切点。
    """
    radius = _check_radius(r)
    a, b = _pt(line1[0]), _pt(line1[1])
    c, d = _pt(line2[0]), _pt(line2[1])
    if _dist(a, b) <= 1e-9 or _dist(c, d) <= 1e-9:
        raise ValueError("直线端点重合，无法确定直线方向")
    u1 = _unit(_sub(b, a))
    u2 = _unit(_sub(d, c))

    denom = _cross(u1, u2)
    if abs(denom) <= 1e-12:
        raise ValueError("两条直线平行（或重合），不能作圆角连接")
    t = _cross(_sub(c, a), u2) / denom
    v = _add(a, _mul(u1, t))

    cos_theta = max(-1.0, min(1.0, _dot(u1, u2)))
    theta = math.acos(cos_theta)
    sin_theta = math.sin(theta)
    if sin_theta <= 1e-12:
        raise ValueError("两条直线夹角过小，无法作圆角连接")

    candidates: list[tuple[Point, Point, Point]] = []
    for sign in (1.0, -1.0):
        for base_vec in (_add(u1, u2), _sub(u1, u2)):
            direction = _mul(base_vec, sign * radius / sin_theta)
            center = _add(v, direction)
            t1 = _perp_foot(center, a, u1)
            t2 = _perp_foot(center, c, u2)
            candidates.append((center, t1, t2))

    chosen: tuple[Point, Point, Point] | None = None
    for center, t1, t2 in candidates:
        on_ray1 = _dot(_sub(t1, v), u1) >= -1e-9
        on_ray2 = _dot(_sub(t2, v), u2) >= -1e-9
        if on_ray1 and on_ray2:
            chosen = (center, t1, t2)
            break
    if chosen is None:
        raise ValueError(
            "给定的两条射线方向不能容纳该圆角：请检查直线端点的先后顺序（方向决定圆角在角的哪一侧）"
        )

    center, t1, t2 = chosen
    arc_svg = _arc_draw(center, radius, t1, t2)
    draw = [
        _line_draw(a, b),
        _line_draw(c, d),
        _point_draw(v, "V"),
        _point_draw(center, "O"),
        _point_draw(t1, "T1"),
        _point_draw(t2, "T2"),
        arc_svg,
    ]
    return {
        "r": _r6(radius),
        "center": (_r6(center[0]), _r6(center[1])),
        "tangents": [
            (_r6(t1[0]), _r6(t1[1])),
            (_r6(t2[0]), _r6(t2[1])),
        ],
        "intersection": (_r6(v[0]), _r6(v[1])),
        "angle_deg": _r6(math.degrees(theta)),
        "arc_svg": arc_svg,
        "draw": draw,
        "formula": (
            "圆心到两直线距离均为 r：圆心在角平分线上，距交点 V 的距离为 r/sin(θ/2)"
            "（θ 为两直线夹角，本处 θ={:.6f}°）。自圆心向两直线作垂线，垂足 T1、T2 即切点。"
        ).format(math.degrees(theta)),
    }


# ---------------------------------------------------------------------------
# 分步脚本
# ---------------------------------------------------------------------------


def _norm_step_kind(kind: str) -> str:
    text = str(kind).strip().lower().replace("_", "").replace("-", "").replace(" ", "")
    text = text.replace("－", "").replace("—", "")
    mapping = {
        "lineline": "line_line",
        "line2line": "line_line",
        "fillet": "line_line",
        "圆角": "line_line",
        "直线直线": "line_line",
        "直线与直线": "line_line",
        "linearc": "line_arc",
        "直线圆弧": "line_arc",
        "直线与圆弧": "line_arc",
        "arcarcouter": "arc_arc_outer",
        "arcarc外切": "arc_arc_outer",
        "外切": "arc_arc_outer",
        "圆弧圆弧外切": "arc_arc_outer",
        "arcarc": "arc_arc_outer",
        "arcarcinner": "arc_arc_inner",
        "内切": "arc_arc_inner",
        "圆弧圆弧内切": "arc_arc_inner",
    }
    if text in mapping:
        return mapping[text]
    raise ValueError(
        f"未知的圆弧连接类型 {kind!r}；支持："
        "line_line（直线-直线圆角）、line_arc（直线-圆弧）、"
        "arc_arc_outer（圆弧-圆弧外切）、arc_arc_inner（圆弧-圆弧内切）"
    )


def _get_r(kw: dict[str, Any]) -> float:
    for key in ("r", "radius", "R"):
        if key in kw and kw[key] is not None:
            return _check_radius(kw[key])
    raise ValueError("build_steps 需要参数 r（圆弧半径）")


def _as_line(value: Any, name: str) -> Line:
    if value is None or len(value) != 2:
        raise ValueError(f"{name} 必须是 (p1, p2) 两个点")
    return (_pt(value[0]), _pt(value[1]))


def build_steps(kind: str, **kw: Any) -> dict:
    """生成圆弧连接的分步作图脚本。

    支持的 ``kind``（不区分大小写、可用中文别名）::

        "line_line"     直线-直线（圆角）   参数：r, lines=((p1,p2),(p3,p4))
                                          或 p1,p2,p3,p4
        "line_arc"      直线-圆弧           参数：r, line=(p1,p2), circle=(c,R), side 可选
        "arc_arc_outer" 圆弧-圆弧外切       参数：r, c1,r1,c2,r2 或 circles=((c1,r1),(c2,r2))
        "arc_arc_inner" 圆弧-圆弧内切       同上

    返回
    ----
    ``{"kind", "steps": [{"n", "title", "detail", "draw"}...],
       "svg_paths": [...], "summary": "...", "result": {...}}``

    其中 ``draw`` 是单步绘图指令列表，``svg_paths`` 是完整图形的绘图指令列表，
    ``result`` 保存全部数值结果，供前端联动显示。
    """
    norm = _norm_step_kind(kind)
    r = _get_r(kw)

    if norm == "line_line":
        if "lines" in kw:
            lines = kw["lines"]
            if len(lines) != 2:
                raise ValueError("lines 必须是两条直线（两个 (p1, p2)）")
            line1 = _as_line(lines[0], "line1")
            line2 = _as_line(lines[1], "line2")
        elif all(key in kw for key in ("p1", "p2", "p3", "p4")):
            line1 = (_pt(kw["p1"]), _pt(kw["p2"]))
            line2 = (_pt(kw["p3"]), _pt(kw["p4"]))
        elif "line1" in kw and "line2" in kw:
            line1 = _as_line(kw["line1"], "line1")
            line2 = _as_line(kw["line2"], "line2")
        else:
            raise ValueError(
                "line_line 需要两条直线：lines=((p1,p2),(p3,p4)) 或 p1/p2/p3/p4"
            )
        data = fillet_two_lines(r, line1, line2)
        t1, t2 = data["tangents"]
        center = data["center"]
        v = data["intersection"]
        steps = [
            {
                "n": 1,
                "title": "分析已知条件",
                "detail": (
                    f"两条已知直线相交于 V({v[0]:.6f}, {v[1]:.6f})，夹角 "
                    f"{data['angle_deg']:.6f}°，圆角半径 R={r:.6f}。"
                ),
                "draw": [
                    _line_draw(*line1),
                    _line_draw(*line2),
                    _point_draw(v, "V"),
                ],
            },
            {
                "n": 2,
                "title": "确定圆心",
                "detail": (
                    "分别作与两直线相距 R 的平行线，两平行线的交点就是圆角圆心 O；"
                    "等价地，O 在角平分线上且距 V 为 R/sin(θ/2)。"
                    f"求得 O({center[0]:.6f}, {center[1]:.6f})。"
                ),
                "draw": [
                    _line_draw(*line1),
                    _line_draw(*line2),
                    _point_draw(center, "O"),
                ],
            },
            {
                "n": 3,
                "title": "求切点",
                "detail": (
                    "自圆心 O 分别向两条已知直线作垂线，垂足即切点："
                    f"T1({t1[0]:.6f}, {t1[1]:.6f})、T2({t2[0]:.6f}, {t2[1]:.6f})。"
                ),
                "draw": [
                    _line_draw(*line1),
                    _line_draw(*line2),
                    _point_draw(center, "O"),
                    _point_draw(t1, "T1"),
                    _point_draw(t2, "T2"),
                ],
            },
            {
                "n": 4,
                "title": "画连接圆弧",
                "detail": (
                    f"以 O 为圆心、R={r:.6f} 为半径，从 T1 画圆弧到 T2，即完成两直线的圆角连接。"
                ),
                "draw": [
                    _line_draw(*line1),
                    _line_draw(*line2),
                    data["arc_svg"],
                ],
            },
        ]
        summary = (
            f"圆心 O({center[0]:.6f}, {center[1]:.6f})，"
            f"切点 T1({t1[0]:.6f}, {t1[1]:.6f})、T2({t2[0]:.6f}, {t2[1]:.6f})，"
            f"圆弧半径 R={r:.6f}。"
        )
        return {
            "kind": norm,
            "steps": steps,
            "svg_paths": data["draw"],
            "summary": summary,
            "result": data,
        }

    if norm == "line_arc":
        line = kw.get("line")
        if line is None:
            if "line_p1" in kw and "line_p2" in kw:
                line = (kw["line_p1"], kw["line_p2"])
            elif "p1" in kw and "p2" in kw:
                line = (kw["p1"], kw["p2"])
            else:
                raise ValueError("line_arc 需要直线：line=(p1,p2) 或 line_p1/line_p2")
        line1 = _as_line(line, "line")

        circle = kw.get("circle")
        if circle is None:
            if "circle_center" in kw and "circle_r" in kw:
                circle = (kw["circle_center"], kw["circle_r"])
            elif "c" in kw and "R" in kw:
                circle = (kw["c"], kw["R"])
            else:
                raise ValueError(
                    "line_arc 需要已知圆：circle=(center, R) 或 circle_center/circle_r"
                )
        circle_center = _pt(circle[0])
        circle_r = _check_radius(circle[1])
        rel = _norm_arc_kind(kw.get("relation", "outer"))

        data = _line_arc_connect(r, line1, circle_center, circle_r, rel, kw.get("side"))
        center = data["center"]
        t_line = data["tangent_on_line"]
        t_circle = data["tangent_on_circle"]
        p_start, p_end = data["arc_points"]
        steps = [
            {
                "n": 1,
                "title": "分析已知条件",
                "detail": (
                    f"已知直线与圆（圆心 ({circle_center[0]:.6f}, {circle_center[1]:.6f})、"
                    f"R={circle_r:.6f}），用半径 R={r:.6f} 的圆弧与之连接。"
                ),
                "draw": [
                    _line_draw(*line1),
                    _circle_draw(circle_center, circle_r, "O1"),
                ],
            },
            {
                "n": 2,
                "title": "确定圆心",
                "detail": (
                    "圆心到直线距离 = R，且到已知圆圆心距离 = R±R₁（外切取和、内切取差），"
                    "两条轨迹的交点即连接弧圆心 O。"
                    f"求得 O({center[0]:.6f}, {center[1]:.6f})。"
                ),
                "draw": [
                    _line_draw(*line1),
                    _circle_draw(circle_center, circle_r, "O1"),
                    _point_draw(center, "O"),
                ],
            },
            {
                "n": 3,
                "title": "求切点",
                "detail": (
                    "自 O 向直线作垂线得直线上切点 T1；O 与已知圆圆心连线的延长线"
                    "与已知圆交点得 T2。"
                    f"T1({t_line[0]:.6f}, {t_line[1]:.6f})、T2({t_circle[0]:.6f}, {t_circle[1]:.6f})。"
                ),
                "draw": [
                    _line_draw(*line1),
                    _circle_draw(circle_center, circle_r, "O1"),
                    _point_draw(center, "O"),
                    _point_draw(t_line, "T1"),
                    _point_draw(t_circle, "T2"),
                ],
            },
            {
                "n": 4,
                "title": "画连接圆弧",
                "detail": f"以 O 为圆心、R={r:.6f} 为半径，从 T1 画圆弧到 T2，完成连接。",
                "draw": [
                    _line_draw(*line1),
                    _circle_draw(circle_center, circle_r, "O1"),
                    _arc_draw(center, r, p_start, p_end),
                ],
            },
        ]
        summary = (
            f"圆心 O({center[0]:.6f}, {center[1]:.6f})，直线上切点 "
            f"T1({t_line[0]:.6f}, {t_line[1]:.6f})，圆上切点 "
            f"T2({t_circle[0]:.6f}, {t_circle[1]:.6f})，圆弧半径 R={r:.6f}。"
        )
        return {
            "kind": norm,
            "steps": steps,
            "svg_paths": data["draw"],
            "summary": summary,
            "result": data,
        }

    # arc_arc_outer / arc_arc_inner
    circles = kw.get("circles")
    if circles is not None:
        if len(circles) != 2:
            raise ValueError("circles 必须是两个圆：((c1, r1), (c2, r2))")
        c1, r1 = circles[0]
        c2, r2 = circles[1]
    else:
        missing = [key for key in ("c1", "r1", "c2", "r2") if key not in kw]
        if missing:
            raise ValueError(
                "arc_arc_* 需要两圆参数：c1/r1/c2/r2 或 circles=((c1,r1),(c2,r2))；"
                f"缺少 {missing}"
            )
        c1, r1, c2, r2 = kw["c1"], kw["r1"], kw["c2"], kw["r2"]
    oc1, oc2 = _pt(c1), _pt(c2)
    or1, or2 = _check_radius(r1), _check_radius(r2)
    rel = "outer" if norm == "arc_arc_outer" else "inner"
    data = connect_arc_to_arc(r, oc1, or1, oc2, or2, rel)
    center = data["center"]
    tp = data["tangent_points"][0]
    t1, t2 = tp
    kind_cn = "外切" if rel == "outer" else "内切"
    rel_formula = (
        "|C−O1| = r1 + r，|C−O2| = r2 + r（外切）"
        if rel == "outer"
        else "|C−O1| = |r1 − r|，|C−O2| = |r2 − r|（内切）"
    )
    steps = [
        {
            "n": 1,
            "title": "分析已知条件",
            "detail": (
                f"已知两圆：O1({oc1[0]:.6f}, {oc1[1]:.6f})、R1={or1:.6f}；"
                f"O2({oc2[0]:.6f}, {oc2[1]:.6f})、R2={or2:.6f}。"
                f"用 R={r:.6f} 的圆弧作{kind_cn}连接。"
            ),
            "draw": [
                _circle_draw(oc1, or1, "O1"),
                _circle_draw(oc2, or2, "O2"),
            ],
        },
        {
            "n": 2,
            "title": f"确定圆心（{kind_cn}条件）",
            "detail": (
                f"{rel_formula}。分别以 O1、O2 为圆心、"
                "以对应和为半径画弧，两弧交点即连接弧圆心 O。"
                f"求得 O({center[0]:.6f}, {center[1]:.6f})。"
            ),
            "draw": [
                _circle_draw(oc1, or1, "O1"),
                _circle_draw(oc2, or2, "O2"),
                _point_draw(center, "O"),
            ],
        },
        {
            "n": 3,
            "title": "求切点",
            "detail": (
                "切点在两圆心连线上：O 与 O1 的连线与已知圆交点 T1，"
                "O 与 O2 的连线与已知圆交点 T2。"
                f"T1({t1[0]:.6f}, {t1[1]:.6f})、T2({t2[0]:.6f}, {t2[1]:.6f})。"
            ),
            "draw": [
                _circle_draw(oc1, or1, "O1"),
                _circle_draw(oc2, or2, "O2"),
                _point_draw(center, "O"),
                _point_draw(t1, "T1"),
                _point_draw(t2, "T2"),
            ],
        },
        {
            "n": 4,
            "title": "画连接圆弧",
            "detail": f"以 O 为圆心、R={r:.6f} 为半径，从 T1 画圆弧到 T2，完成{kind_cn}连接。",
            "draw": [
                _circle_draw(oc1, or1, "O1"),
                _circle_draw(oc2, or2, "O2"),
                data["solutions"][0]["arc_svg"],
            ],
        },
    ]
    summary = (
        f"{kind_cn}连接：圆心 O({center[0]:.6f}, {center[1]:.6f})，"
        f"切点 T1({t1[0]:.6f}, {t1[1]:.6f})、T2({t2[0]:.6f}, {t2[1]:.6f})，"
        f"圆弧半径 R={r:.6f}。"
    )
    return {
        "kind": norm,
        "steps": steps,
        "svg_paths": data["svg_paths"],
        "summary": summary,
        "result": data,
    }


def _line_arc_connect(
    r: float,
    line: Line,
    center: Point,
    radius: float,
    relation: str,
    side: int | None,
) -> dict:
    """直线—圆弧连接（内部实现）：求圆心、两切点与绘图指令。"""
    a, b = line
    u = _unit(_sub(b, a))
    normal = _left_normal(u)
    target = radius + r if relation == "outer" else abs(radius - r)

    sides = (side,) if side in (1, -1) else (1, -1)
    solutions: list[dict] = []
    for s in sides:
        offset = _mul(normal, s * r)
        a_prime = _add(a, offset)
        w = _sub(a_prime, center)
        half_b = _dot(w, u)
        c = _dot(w, w) - target * target
        disc = half_b * half_b - c
        if disc < -1e-9:
            continue
        disc = max(disc, 0.0)
        root = math.sqrt(disc)
        for t in (-half_b - root, -half_b + root):
            arc_center = _add(a_prime, _mul(u, t))
            tangent_line = _add(a, _mul(u, t))
            direction = _unit(_sub(arc_center, center))
            tangent_circle = _add(center, _mul(direction, radius))
            solutions.append(
                {
                    "center": (_r6(arc_center[0]), _r6(arc_center[1])),
                    "tangent_on_line": (_r6(tangent_line[0]), _r6(tangent_line[1])),
                    "tangent_on_circle": (_r6(tangent_circle[0]), _r6(tangent_circle[1])),
                    "side": s,
                    "arc_svg": _arc_draw(arc_center, r, tangent_line, tangent_circle),
                }
            )

    if not solutions:
        rel_cn = "外切" if relation == "outer" else "内切"
        raise ValueError(
            f"半径 r={r:g} 的圆弧无法与已知直线、已知圆同时{rel_cn}连接："
            "请检查半径与几何位置（直线到圆心的距离需满足相切条件）"
        )
    if side in (1, -1):
        solutions.sort(key=lambda d: (0 if d["side"] == side else 1))
    unique: list[dict] = []
    for item in solutions:
        if all(_dist(item["center"], other["center"]) > 1e-9 for other in unique):
            unique.append(item)
    best = unique[0]
    draw = [
        _line_draw(a, b),
        _circle_draw(center, radius, "O1"),
        _point_draw(best["center"], "O"),
        _point_draw(best["tangent_on_line"], "T1"),
        _point_draw(best["tangent_on_circle"], "T2"),
        best["arc_svg"],
    ]
    best = dict(best)
    best["draw"] = draw
    best["solutions"] = unique
    best["line"] = [[a[0], a[1]], [b[0], b[1]]]
    best["circle"] = {"center": [center[0], center[1]], "r": _r6(radius)}
    best["arc_draw"] = best.pop("arc_svg")
    best["arc_points"] = (
        best["tangent_on_line"],
        best["tangent_on_circle"],
    )
    best["formula"] = (
        "圆心到直线距离 = r；圆心到已知圆圆心的距离：外切取 R+r，内切取 |R−r|。"
        "以已知圆圆心为圆心、以该距离为半径画弧，与距直线 r 的平行线求交即得圆心；"
        "直线上切点为垂足，圆上切点在两圆心连线上。"
    )
    return best
