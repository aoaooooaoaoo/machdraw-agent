"""第二批图（返工）：圆锥截交线拆成两张，截交线按真实解析几何求点后投影画在锥面上。

数学：设圆锥顶点在 (0,0,H)、底圆半径 R（z 轴为轴线）。锥面上一点
      P(s,θ) = (sR cosθ, sR sinθ, H(1-s)),  s∈[0,1]
截平面（与轴线成 α 角、过轴线上 z=zq 的点）：x cosα − z sinα = −zq sinα
代入得   s(θ) = (H−zq) sinα / (R cosα cosθ + H sinα)
按 θ 采样取 s∈[0,1] 的点即为截交线；再用外法线做可见性判断，可见段画粗实线、不可见段画虚线。

投影用斜投影：sx = ox + x + KY·y，sy = oy − z − KY·y（KY=0.42，深度向右上方退去）。
"""
from __future__ import annotations

import math

from fig2kit import (AMBER, BLUE, GREEN, INK, MUTED, ORANGE, RED, TEAL, VIOLET, Fig2,
                     fig_title, notes, panel_title)

KY = 0.42          # 斜投影的深度系数
BETA_NOTE = "β 为半锥角（≈25°）"


def proj(x: float, y: float, z: float, ox: float, oy: float):
    return (ox + x + KY * y, oy - z - KY * y)


def base_pts(R: float, n: int = 90):
    return [proj(R * math.cos(t), R * math.sin(t), 0.0, 0, 0) for t in
            [2 * math.pi * i / n for i in range(n)]]


def draw_cone(F: Fig2, ox: float, oy: float, R: float, H: float,
              apex_label: bool = False, ghost_up: bool = False) -> None:
    """画圆锥：底圆（前半实线、后半虚线）+ 两条转向轮廓线。"""
    n = 90
    front, back = [], []
    for i in range(n + 1):
        t = 2 * math.pi * i / n
        p = proj(R * math.cos(t), R * math.sin(t), 0.0, ox, oy)
        if math.sin(t) <= 0:
            front.append(p)
        else:
            back.append(p)
    F.polyline(front, cls="thick")
    F.polyline(back, cls="dash")
    for th in (math.atan(KY), math.atan(KY) + math.pi):
        bx, by = proj(R * math.cos(th), R * math.sin(th), 0.0, ox, oy)
        F.line(ox, oy - H, bx, by, cls="thick")
    if ghost_up:
        # 与锥顶对称的另一个锥面（虚线），用于说明双曲线的另一支
        gfront, gback = [], []
        for i in range(n + 1):
            t = 2 * math.pi * i / n
            p = proj(R * math.cos(t), R * math.sin(t), 2 * H, ox, oy)
            (gfront if math.sin(t) <= 0 else gback).append(p)
        F.polyline(gfront, cls="dash", color=MUTED)
        F.polyline(gback, cls="dash", color=MUTED)
        for th in (math.atan(KY), math.atan(KY) + math.pi):
            bx, by = proj(R * math.cos(th), R * math.sin(th), 2 * H, ox, oy)
            F.line(ox, oy - H, bx, by, cls="dash", color=MUTED)
    F.line(ox, oy - H - (40 if not ghost_up else 30), ox, oy + 18, cls="center", color=MUTED)


def draw_plane_trace(F: Fig2, ox: float, oy: float, R: float, H: float,
                     alpha_deg: float, zq: float, color=RED, label: str = "α") -> None:
    """截平面在 XZ 平面上的迹线（延长到锥体外）+ α 角弧。"""
    a = math.radians(alpha_deg)
    t = 1.35 * R
    x1, z1 = -t * math.sin(a), zq - t * math.cos(a)
    x2, z2 = t * math.sin(a), zq + t * math.cos(a)
    p1, p2 = proj(x1, 0, z1, ox, oy), proj(x2, 0, z2, ox, oy)
    F.line(p1[0], p1[1], p2[0], p2[1], cls="axis", color=color)
    # α 角：轴线上 (0,zq) 处，从竖直方向量到迹线方向
    if 6 < alpha_deg < 88:
        F.arc(ox, oy - zq, 52, -90, -90 + alpha_deg, cls="thin", color=color, n=24)
        mid = math.radians(-90 + alpha_deg / 2)
        F.text(ox + 66 * math.cos(mid), oy - zq + 66 * math.sin(mid) + 4, f"{label}={alpha_deg:g}°",
               size=11, color=color)


def draw_section(F: Fig2, ox: float, oy: float, R: float, H: float,
                 alpha_deg: float, zq: float, upper: bool = False,
                 color=None, only_dash: bool = False) -> int:
    """求截交线并画在锥面上；返回采样到的点数。"""
    a = math.radians(alpha_deg)
    sa, ca = math.sin(a), math.cos(a)
    vis, hid = [], []          # 每段是一串屏幕点
    cur_v, cur_h = [], []
    got = 0

    def flush():
        nonlocal cur_v, cur_h
        if len(cur_v) > 1:
            vis.append(cur_v)
        if len(cur_h) > 1:
            hid.append(cur_h)
        cur_v, cur_h = [], []

    for i in range(0, 721):
        th = math.radians(-180 + i * 0.5)
        den = R * ca * math.cos(th) - (H * sa if upper else -H * sa)
        if abs(den) < 1e-6:
            flush()
            continue
        s = (H - zq) * sa / den
        if not (-0.002 <= s <= 1.0):
            flush()
            continue
        got += 1
        z = H * (1 - s) if not upper else H * (1 + s)
        x, y = s * R * math.cos(th), s * R * math.sin(th)
        p = proj(x, y, z, ox, oy)
        # 可见性：外法线 (H cosθ, H sinθ, R) 与视向 −v=(KY,−1,KY) 点积 > 0 可见
        nd = KY * H * math.cos(th) - H * math.sin(th) + KY * R
        if nd > 0:
            cur_v.append(p)
            if cur_h:
                flush()
        else:
            cur_h.append(p)
            if cur_v:
                flush()
    flush()

    def seg_path(segs):
        return " ".join(
            "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in seg) for seg in segs
        )

    if vis and not only_dash:
        F.path(seg_path(vis), cls="cut", color=color)
    if hid:
        # 不可见段：同色、同粗，只改虚线 —— 否则细虚线在锥面轮廓旁几乎看不见，学生读不出曲线形状
        F.path(seg_path(hid), cls="cut", color=color, extra='stroke-dasharray="9 5"')
    return got


# ---------------------------------------------------------------------------
# 返工 1/2：圆 + 椭圆（闭合截交线）
# ---------------------------------------------------------------------------
def fig_jiejiao_yuanzhui_1() -> Fig2:
    F = Fig2("FIG2-JIEJIAO-YUANZHUI-1", 1120, 660,
             "圆锥截交线（一）：圆与椭圆",
             "截平面垂直于轴线得圆（α=90°），倾斜但大于半锥角得椭圆（α>β）；截交线按解析法求点后"
             "画在锥面上，前半可见画粗实线、后半不可见画虚线。")
    fig_title(F, "图 2-8a  圆锥截交线（一）：圆与椭圆 —— 曲线真实画在锥面上",
              "圆锥 R=100、H=210（半锥角 β≈25°）；截平面与轴线成 α 角，α=90° 得圆，α>β 得椭圆。")

    R, H = 100.0, 210.0
    # ---- ① 圆：α = 90° ----
    ox, oy, zq = 250, 560, 105
    panel_title(F, ox, 128, "① α = 90°（⊥ 轴线）→ 截交线是圆", size=12)
    draw_cone(F, ox, oy, R, H)
    draw_plane_trace(F, ox, oy, R, H, 90, zq, color=RED, label="α")
    draw_section(F, ox, oy, R, H, 90, zq, color=BLUE)
    F.text(ox, 620, "圆：α = 90° > β，截平面与所有素线正交", size=11, color=MUTED)

    # ---- ② 椭圆：α = 55° ----
    ox2, zq2 = 700, 105
    panel_title(F, ox2, 128, "② α > β（斜切）→ 截交线是椭圆", size=12)
    draw_cone(F, ox2, oy, R, H)
    draw_plane_trace(F, ox2, oy, R, H, 55, zq2, color=RED, label="α")
    draw_section(F, ox2, oy, R, H, 55, zq2, color=BLUE)
    F.text(ox2, 620, "椭圆：α = 55° > β≈25°，与所有素线都相交 → 闭合椭圆", size=11, color=MUTED)

    # ---- 右侧：判定表 ----
    rx = 900
    F.text(rx, 176, "α 与 β 的关系决定形状", size=12, weight="600", anchor="start")
    rows = [
        ("α = 90°", "圆", RED),
        ("α > β", "椭圆", BLUE),
        ("α = β", "抛物线", GREEN),
        ("α < β", "双曲线", VIOLET),
        ("过锥顶", "三角形", AMBER),
    ]
    for i, (k, v, col) in enumerate(rows):
        y = 214 + i * 30
        F.text(rx, y, k, size=12, weight="600", anchor="start", color=col)
        F.text(rx + 88, y, "→", size=12, anchor="start", color=MUTED)
        F.text(rx + 112, y, v, size=12, anchor="start")
    F.text(rx, 400, "β = 半锥角 = arctan(R/H) ≈ 25°", size=11, anchor="start", color=MUTED)
    F.text(rx, 422, "α = 截平面与轴线的夹角", size=11, anchor="start", color=MUTED)
    F.text(rx, 460, "读图要点", size=12, weight="600", anchor="start")
    F.lines(rx, 484, [
        "· 先看截平面与轴线的夹角 α；",
        "· 再和半锥角 β 比大小；",
        "· 大 → 椭圆，等 → 抛物线，小 → 双曲线。",
    ], size=11, lh=20)
    F.text(rx, 560, "本图两条曲线都是闭合的", size=11, anchor="start", color=BLUE)

    notes(F, 40, 636, [
        "① 圆：截平面垂直于轴线，截交线是圆；斜投影后看起来是椭圆，这是投影效果，不是形状变了。",
        "② 椭圆：截平面倾斜但仍与所有素线相交，截交线是闭合椭圆 —— 主视图里看到的那条斜直线只是它的投影。",
    ], size=11, lh=20)
    return F


# ---------------------------------------------------------------------------
# 返工 2/2：抛物线 + 双曲线 + 三角形（开口截交线）
# ---------------------------------------------------------------------------
def fig_jiejiao_yuanzhui_2() -> Fig2:
    F = Fig2("FIG2-JIEJIAO-YUANZHUI-2", 1180, 680,
             "圆锥截交线（二）：抛物线、双曲线与三角形",
             "α=β 时截平面平行于一条素线，截交线是抛物线且开口跑出轮廓线；α<β 时平行于轴线，"
             "得双曲线的一支（另一支在对称锥面上）；过锥顶得两条素线即三角形。")
    fig_title(F, "图 2-8b  圆锥截交线（二）：抛物线、双曲线、三角形",
              "圆锥 R=80、H=170（半锥角 β≈25°）；三条截交线都按解析法逐点求出后画在锥面上。")

    R, H = 80.0, 170.0
    oy = 500

    # ---- ① 抛物线：α = β ----
    ox = 210
    panel_title(F, ox, 250, "① α = β（平行于一条素线）→ 抛物线", size=12)
    draw_cone(F, ox, oy, R, H)
    draw_plane_trace(F, ox, oy, R, H, 25, 85, color=GREEN, label="α")
    draw_section(F, ox, oy, R, H, 25, 85, color=GREEN)
    F.text(ox, 566, "开口跑出转向轮廓线，两端落在底圆上", size=11, color=MUTED)
    # 真形小图
    px0, py0 = ox + 128, 336
    F.polyline([(px0 - 26, py0 - 14), (px0 - 16, py0 + 4), (px0, py0 + 15),
                (px0 + 16, py0 + 4), (px0 + 26, py0 - 14)], cls="cut", color=GREEN)
    F.text(px0, py0 + 36, "截交线真形", size=10, color=MUTED)

    # ---- ② 双曲线：α < β ----
    ox2 = 590
    panel_title(F, ox2, 250, "② α < β（接近平行于轴线）→ 双曲线", size=12)
    draw_cone(F, ox2, oy, R, H, ghost_up=True)
    draw_plane_trace(F, ox2, oy, R, H, 18, 95, color=VIOLET, label="α")
    draw_section(F, ox2, oy, R, H, 18, 95, color=VIOLET)              # 下锥一支（实线）
    draw_section(F, ox2, oy, R, H, 18, 95, upper=True, only_dash=True)  # 上锥另一支（虚线）
    F.text(ox2, 566, "下锥一支实线；对称锥面上的另一支画虚线", size=11, color=MUTED)
    # 真形小图（两支）
    hx0, hy0 = ox2 + 132, 330
    F.polyline([(hx0 - 10, hy0 - 20), (hx0 - 18, hy0 - 2), (hx0 - 30, hy0 + 18)], cls="cut", color=VIOLET)
    F.polyline([(hx0 + 10, hy0 - 20), (hx0 + 18, hy0 - 2), (hx0 + 30, hy0 + 18)], cls="cut", color=VIOLET)
    F.text(hx0, hy0 + 40, "完整双曲线（两支）", size=10, color=MUTED)

    # ---- ③ 过锥顶：三角形 ----
    ox3 = 970
    panel_title(F, ox3, 250, "③ 过锥顶 → 两条素线（三角形）", size=12)
    draw_cone(F, ox3, oy, R, H)
    th1, th2 = math.radians(140), math.radians(40)
    b1 = proj(R * math.cos(th1), R * math.sin(th1), 0, ox3, oy)
    b2 = proj(R * math.cos(th2), R * math.sin(th2), 0, ox3, oy)
    F.line(ox3, oy - H, b1[0], b1[1], cls="cut", color=AMBER)
    F.line(ox3, oy - H, b2[0], b2[1], cls="cut", color=AMBER)
    F.line(b1[0], b1[1], b2[0], b2[1], cls="cut", color=AMBER)
    F.text(ox3, 566, "截平面通过锥顶：截交线是两条相交的素线", size=11, color=MUTED)

    notes(F, 40, 606, [
        "① 抛物线（α=β）：截平面平行于一条素线，交线是不闭合的抛物线，开口沿那条素线方向跑出锥面，"
        "两端落在底圆上。",
        "② 双曲线（α<β）：截平面平行于轴线（或更陡），交线是双曲线的一支；完整双曲线的另一支在与锥顶"
        "对称的另一个锥面上（图中虚线）。",
        "③ 过锥顶：不论倾角多大，过的平面与锥面只交于两条素线，围成三角形 —— 这是“截交线退化为直线”的情形。",
    ], size=11, lh=21)
    return F


ALL = [fig_jiejiao_yuanzhui_1, fig_jiejiao_yuanzhui_2]
