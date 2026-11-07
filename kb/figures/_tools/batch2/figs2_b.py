"""第二批图 7–12：圆柱/圆锥截交线、相贯线简化、形体分析法、补画第三视图、尺寸基准。"""
from __future__ import annotations

import math

from fig2kit import (AMBER, BLUE, GREEN, INK, MUTED, ORANGE, RED, TEAL, VIOLET, Fig2,
                     fig_title, notes, panel_title)


# ---------------------------------------------------------------------------
# 7. 圆柱截交线三例
# ---------------------------------------------------------------------------
def fig_jiejiao_yuanzhu() -> Fig2:
    F = Fig2("FIG2-JIEJIAO-YUANZHU", 1040, 560,
             "圆柱截交线三例：圆、椭圆、矩形",
             "截平面垂直于轴线截得圆、倾斜截得椭圆、平行于轴线截得矩形；每例给出主视图与断面真形。")
    fig_title(F, "图 2-7  圆柱的截交线（圆柱 Ø80×100，单位 mm）",
              "关键：先看截平面与圆柱轴线的相对位置，再决定截交线是什么形状。")
    K = 1.2
    cases = [
        (40, "① 截平面 ⊥ 轴线", "截交线：圆", "圆是实形，正面投影积聚成一条直线", "circle"),
        (380, "② 截平面倾斜", "截交线：椭圆", "要按点求：先找长短轴两端点，再求中间点", "ellipse"),
        (720, "③ 截平面 ∥ 轴线", "截交线：矩形", "截交线是两条素线 + 上下两段圆弧", "rect"),
    ]
    for px, name, shape, tip, kind in cases:
        panel_title(F, px + 150, 150, name, size=12)
        # 主视图：圆柱 ø80×100
        cx0 = px + 26
        F.rect(cx0, 180, 80 * K, 100 * K, cls="thick")
        # 截平面迹线
        if kind == "circle":
            F.line(cx0 - 12, 240, cx0 + 80 * K + 12, 240, cls="cut", color=RED)
        elif kind == "ellipse":
            F.line(cx0 - 10, 200, cx0 + 80 * K + 10, 286, cls="cut", color=RED)
        else:
            F.line(cx0 + 18, 176, cx0 + 18, 304, cls="cut", color=RED)
            F.line(cx0 + 60, 176, cx0 + 60, 304, cls="cut", color=RED)
        F.text(cx0 + 40 * K, 322, "主视图", size=11, color=MUTED)
        # 断面真形
        sx, sy = px + 250, 240
        if kind == "circle":
            F.circle(sx, sy, 24, cls="thick")
        elif kind == "ellipse":
            F.ellipse(sx, sy, 30, 17, -18, cls="thick")
        else:
            F.rect(sx - 26, sy - 16, 52, 32, cls="thick")
        F.text(px + 250, 300, "断面真形", size=11, color=MUTED)
        F.text(px + 150, 348, shape, size=12, weight="600", color=BLUE)
        F.text(px + 150, 376, tip, size=10, color=MUTED)

    notes(F, 40, 430, [
        "① 截平面垂直于轴线 → 截交线是圆。正面投影积聚成一条直线，水平投影就是圆本身（实形）。",
        "② 截平面倾斜于轴线 → 截交线是椭圆。作图时先求长短轴端点（最低、最高素线处），再求若干个中间点。",
        "③ 截平面平行于轴线 → 截交线是两条素线加两段圆弧，围成矩形（注意：只有截平面切到两端面时才是完整矩形）。",
        "④ 判断顺序永远是：先看截平面与轴线的位置关系，再决定截交线的形状，最后才动笔画。",
    ], size=11, lh=21)
    return F


# ---------------------------------------------------------------------------
# 8. 圆锥截交线五种
# ---------------------------------------------------------------------------
def fig_jiejiao_yuanzhui() -> Fig2:
    F = Fig2("FIG2-JIEJIAO-YUANZHUI", 1040, 600,
             "圆锥截交线五种：随截平面与轴线的夹角变化",
             "设圆锥半锥角为 β、截平面与轴线的夹角为 α：α=90° 得圆，α>β 得椭圆，α=β 得抛物线，"
             "α<β 得双曲线，过锥顶得三角形。")
    fig_title(F, "图 2-8  圆锥的截交线（五类，随 α 与半锥角 β 的关系变化）",
              "β 为半锥角（本图 β≈24°）；α 为截平面与轴线的夹角。")

    # ---------- 左：圆锥 + 五条截平面迹线 ----------
    cx, apex_y, base_y, R = 250, 180, 400, 110
    F.ellipse(cx, base_y, R, R * 0.3, 0, cls="thick")          # 底圆
    F.line(cx - R, base_y, cx, apex_y, cls="thick")            # 两条转向轮廓线
    F.line(cx + R, base_y, cx, apex_y, cls="thick")
    F.line(cx, apex_y - 24, cx, base_y + 44, cls="center", color=MUTED)  # 轴线

    # 五条截平面迹线：按 α 与 β 的关系给不同斜度
    traces = [
        (RED, "①", (cx - 36, apex_y + 110), (cx + 36, apex_y + 110), "α = 90°（圆）"),
        (BLUE, "②", (cx - 68, apex_y + 100), (cx + 94, apex_y + 160), "α > β（椭圆）"),
        (GREEN, "③", (cx - 60, apex_y + 70), (cx + 16, base_y), "α = β（抛物线）"),
        (VIOLET, "④", (cx - 82, apex_y + 60), (cx - 49, base_y), "α < β（双曲线）"),
        (AMBER, "⑤", (cx, apex_y), (cx + 33, base_y), "过锥顶（三角形）"),
    ]
    for col, no, p1, p2, label in traces:
        F.line(p1[0], p1[1], p2[0], p2[1], cls="thin", color=col)
        lx = p2[0] + (12 if p2[0] >= cx else -12)
        F.text(lx, p2[1] + 4, no, size=11, weight="600", color=col,
               anchor="start" if p2[0] >= cx else "end")

    F.text(cx, apex_y - 40, "圆锥（β≈24°）", size=12, weight="600")
    F.text(cx, 500, "①②③④⑤ 为五种截平面位置", size=11, color=MUTED)

    # ---------- 右：五种截交线对照 ----------
    rx = 560
    F.text(rx, 168, "截交线形状对照", size=12, weight="600", anchor="start")
    rows = [
        ("①", "α = 90°", "圆", "截平面垂直于轴线", RED),
        ("②", "α > β", "椭圆", "截平面与所有素线都相交", BLUE),
        ("③", "α = β", "抛物线", "截平面平行于一条素线", GREEN),
        ("④", "α < β", "双曲线", "截平面平行于轴线或更陡", VIOLET),
        ("⑤", "过锥顶", "三角形", "截平面通过锥顶，交线为两素线", AMBER),
    ]
    for i, (no, ang, shape, desc, col) in enumerate(rows):
        y = 210 + i * 60
        F.text(rx, y, f"{no} {ang}", size=12, weight="600", anchor="start", color=col)
        F.text(rx + 96, y, shape, size=12, weight="600", anchor="start")
        F.text(rx + 160, y, desc, size=11, anchor="start", color=MUTED)
        # 小图标
        ix, iy = rx + 400, y - 6
        if shape == "圆":
            F.circle(ix, iy, 14, cls="thick")
        elif shape == "椭圆":
            F.ellipse(ix, iy, 20, 11, 0, cls="thick")
        elif shape == "抛物线":
            F.polyline([(ix - 22, iy - 10), (ix - 10, iy + 10), (ix, iy + 13), (ix + 10, iy + 10),
                        (ix + 22, iy - 10)], cls="thick")
        elif shape == "双曲线":
            F.polyline([(ix - 20, iy - 14), (ix - 6, iy - 2), (ix, iy), (ix + 6, iy - 2),
                        (ix + 20, iy - 14)], cls="thick")
        else:
            F.polyline([(ix, iy - 14), (ix - 16, iy + 12), (ix + 16, iy + 12)], cls="thick", close=True)
        F.line(rx, y + 22, rx + 470, y + 22, cls="thin", color="#e5e7eb" if False else MUTED,
               extra='stroke-opacity="0.35"')

    notes(F, 560, 520, [
        "① 判断口诀：截平面与轴线的夹角 α 和半锥角 β 比大小 —— 90° 是圆、比 β 大是椭圆、相等抛物线、比 β 小双曲线。",
        "② 过锥顶的截平面（不论倾角）截得三角形；截平面切到两个锥面时得到双曲线的两支。",
    ], size=11, lh=22)
    return F


# ---------------------------------------------------------------------------
# 9. 相贯线简化画法
# ---------------------------------------------------------------------------
def fig_xiangguan_jianhua() -> Fig2:
    F = Fig2("FIG2-XIANGUAN-JIANHUA", 1000, 520,
             "正交异径圆柱相贯线的简化画法",
             "两个垂直相交、直径不等的圆柱，相贯线可用一段圆弧代替：圆弧半径取大圆柱半径 R，"
             "圆心落在小圆柱轴线上，圆弧过三个点。")
    fig_title(F, "图 2-9  相贯线的简化画法（正交异径圆柱）",
              "大圆柱 Ø80（水平）、小圆柱 Ø50（竖直）；简化画法只适用于异径正交、且大圆柱直径明显较大的情况。")

    # ---------- 主视图 ----------
    by, R = 300, 40           # 大圆柱轴线高度、半径
    cx, r = 340, 25           # 小圆柱轴线 x、半径
    F.rect(160, by - R, 380, 2 * R, cls="thick")          # 大圆柱外形（左右端面省略）
    F.line(160, by, 540, by, cls="center", color=MUTED)   # 大圆柱轴线
    F.rect(cx - r, by - R - 90, 2 * r, 90, cls="thick")   # 小圆柱
    F.line(cx, by - R - 100, cx, by + 10, cls="center", color=MUTED)

    # 相贯线：以 R 为半径、圆心在小圆柱轴线上的圆弧
    oy = by - R - ((R * R - r * r) ** 0.5)
    a0 = math.degrees(math.atan2(by - R - oy, (cx - r) - cx))
    a1 = math.degrees(math.atan2(by - R - oy, (cx + r) - cx))
    F.arc(cx, oy, R, a0, a1, cls="cut", n=48)
    F.dot(cx, oy, r=2.4, color=RED)
    F.leader(cx, oy, cx + 96, oy - 34, "O（圆心，落在小圆柱轴线上）", color=RED, anchor="start")
    F.text(cx - r - 12, by - R - 6, "1", size=11, weight="600", color=BLUE, anchor="end")
    F.text(cx + r + 12, by - R - 6, "2", size=11, weight="600", color=BLUE, anchor="start")
    F.text(cx + 12, by - R + 16, "3（最低点）", size=11, weight="600", color=GREEN, anchor="start")
    F.text(200, by - R - 16, "大圆柱", size=12, weight="600", anchor="start")
    F.text(cx, by - R - 104, "小圆柱", size=12, weight="600")

    # 半径标注
    F.line_arrow(cx, oy, cx + R * math.cos(math.radians(40)), oy + R * math.sin(math.radians(40)), color=RED)
    F.text(cx + 52, oy + 30, "R = 大圆柱半径", size=11, color=RED, anchor="start")

    # ---------- 俯视图 ----------
    ty = 470
    F.rect(160, ty - R, 380, 2 * R, cls="thick")
    F.circle(cx, ty, r, cls="thick")
    F.line(160, ty, 540, ty, cls="center", color=MUTED)
    F.line(cx, ty - R - 14, cx, ty + R + 14, cls="center", color=MUTED)
    F.text(cx, ty + R + 34, "俯视图", size=11, color=MUTED)

    notes(F, 40, 560, [
        "① 三个点：1、2 是两个圆柱轮廓线的交点，3 是相贯线的最低点（在小圆柱轴线上）。",
        "② 圆弧半径取大圆柱半径 R，圆心必须落在小圆柱轴线上 —— 这两条是简化画法的硬性条件。",
        "③ 求圆心：以 R 为半径、过 1、2 两点画圆弧，圆心自然落在小圆柱轴线上。",
        "④ 只适用于“异径正交”：两圆柱直径相等时相贯线是两个相交的椭圆，不能这样简化。",
    ], size=11, lh=21)
    return F


# ---------------------------------------------------------------------------
# 10. 形体分析法
# ---------------------------------------------------------------------------
def fig_zuheti_xingtifa() -> Fig2:
    F = Fig2("FIG2-ZUHETI-XINGTIFA", 1000, 620,
             "形体分析法：把组合体拆成三个基本体",
             "组合体由底板、立圆柱、肋板三块基本体组成；读图时逐块对投影，再看它们的表面连接关系，最后合起来。")
    fig_title(F, "图 2-10  形体分析法（底板 + 圆柱 + 肋板）",
              "①②③ 分别对应底板、立圆柱、肋板；同一形体的三个投影必须互相对得上。")

    # ---------- 左：组合体的两视图 ----------
    F.text(220, 128, "组合体的视图", size=12, weight="600")
    # 主视图
    F.rect(100, 260, 240, 40, cls="thick")            # 底板
    F.rect(200, 160, 100, 100, cls="thick")           # 立圆柱
    F.polyline([(100, 260), (200, 260), (200, 200)], cls="thick", close=True)  # 肋板（三角）
    F.text(120, 300, "①", size=11, weight="600", color=BLUE, anchor="start")
    F.text(250, 214, "②", size=11, weight="600", color=RED)
    F.text(126, 246, "③", size=11, weight="600", color=GREEN, anchor="start")
    F.text(60, 285, "主视图", size=11, color=MUTED, anchor="end")
    # 俯视图
    F.rect(100, 340, 240, 160, cls="thick")
    F.circle(250, 420, 50, cls="thick")
    F.rect(100, 400, 100, 40, cls="thick")
    F.text(116, 366, "①", size=11, weight="600", color=BLUE, anchor="start")
    F.text(250, 424, "②", size=11, weight="600", color=RED)
    F.text(120, 424, "③", size=11, weight="600", color=GREEN, anchor="start")
    F.text(60, 370, "俯视图", size=11, color=MUTED, anchor="end")

    # ---------- 右：三个基本体 ----------
    bx = 430
    F.text(bx + 90, 128, "拆成三个基本体", size=12, weight="600", anchor="start")
    parts = [
        ("①", "长方体底板", "240×160×40", BLUE, "矩形", 210),
        ("②", "立圆柱", "Ø100×100", RED, "圆", 300),
        ("③", "三棱柱肋板", "100×40×60", GREEN, "三角形", 390),
    ]
    for no, name, size_, col, glyph, y in parts:
        F.text(bx, y, f"{no} {name}", size=12, weight="600", anchor="start", color=col)
        F.text(bx + 4, y + 20, size_, size=11, anchor="start", color=MUTED)
        gx, gy = bx + 230, y - 4
        if glyph == "矩形":
            F.rect(gx - 34, gy - 18, 68, 36, cls="thin")
        elif glyph == "圆":
            F.circle(gx, gy, 18, cls="thin")
            F.rect(gx - 26, gy - 20, 52, 40, cls="thin", extra='stroke-dasharray="4 3"')
        else:
            F.polyline([(gx - 30, gy + 18), (gx + 30, gy + 18), (gx + 30, gy - 18)], cls="thin", close=True)

    F.text(bx, 470, "读图三步", size=12, weight="600", anchor="start")
    F.text(bx + 4, 494, "① 分块：把组合体拆成几个基本体，标出每块的范围。", size=11, anchor="start")
    F.text(bx + 4, 516, "② 对投影：每块的三个投影都要对得上（长对正、高平齐、宽相等）。", size=11, anchor="start")
    F.text(bx + 4, 538, "③ 定关系：分清相切、平齐、相交、相贯，分界线该有的画、该无的不画。", size=11, anchor="start")
    return F


# ---------------------------------------------------------------------------
# 11. 补画第三视图
# ---------------------------------------------------------------------------
def fig_budi_sanshitu() -> Fig2:
    F = Fig2("FIG2-BUDI-SANSHITU", 1000, 620,
             "补画第三视图：由主视图与俯视图补出左视图",
             "已知主视图与俯视图，左视图位置留虚线框提示补画；先做形体分析、逐块对投影，再按三等规律补线。")
    fig_title(F, "图 2-11  补画第三视图（底板 + 圆柱凸台）",
              "左视图的位置用虚线框表示“待补”，补完后应满足高平齐与宽相等。")

    # 主视图：底板 90×20 + 凸台 Ø40×25
    F.rect(80, 240, 180, 40, cls="thick")
    F.rect(140, 190, 80, 50, cls="thick")
    F.text(170, 320, "主视图", size=12, weight="600")
    # 俯视图
    F.rect(80, 340, 180, 100, cls="thick")
    F.circle(170, 390, 40, cls="thick")
    F.line(80, 390, 260, 390, cls="center", color=MUTED)
    F.text(170, 468, "俯视图", size=12, weight="600")

    # 左视图占位
    F.rect(320, 190, 100, 90, cls="thin", color=RED, extra='stroke-dasharray="7 5"')
    F.text(370, 232, "?", size=26, anchor="middle", color=RED)
    F.text(370, 314, "左视图（要补）", size=12, weight="600", color=RED)
    F.text(370, 336, "宽 = 俯视图的高（宽相等）", size=10, color=MUTED)

    # 三等关系提示
    F.line(260, 200, 320, 200, cls="dash", color=ORANGE)
    F.line(260, 280, 320, 280, cls="dash", color=ORANGE)
    F.line(170, 300, 170, 340, cls="dash", color=GREEN)
    F.line(80, 300, 80, 340, cls="dash", color=GREEN)
    F.line(260, 310, 300, 310, cls="dash", color=VIOLET)
    F.line(300, 310, 300, 440, cls="dash", color=VIOLET)
    F.line(260, 440, 300, 440, cls="dash", color=VIOLET)

    notes(F, 470, 380, [
        "补图四步：",
        "① 形体分析：底板（长方体）+ 凸台（圆柱），共两块。",
        "② 逐块对投影：底板在主视图是 180×40 的矩形，俯视图是 180×100 的矩形。",
        "③ 想第三投影：左视图里底板是 100×40 的矩形（宽 = 俯视图的高）。",
        "④ 补线检查：凸台在左视图里是 80 宽 × 50 高的矩形，与主视图高平齐。",
        "易错：漏画凸台的转向轮廓线；或把“宽”画成俯视图的宽（≈ 长对正用错方向）。",
    ], size=11, lh=21)
    return F


# ---------------------------------------------------------------------------
# 12. 设计基准与工艺基准
# ---------------------------------------------------------------------------
def fig_chicun_jizhun() -> Fig2:
    F = Fig2("FIG2-CHICUN-JIZHUN", 1000, 600,
             "尺寸基准：设计基准与工艺基准",
             "同一零件两种标注方案：从设计基准出发与从工艺基准出发；同一方向的定位尺寸必须从同一个基准出发。")
    fig_title(F, "图 2-12  尺寸基准（设计基准 vs 工艺基准）",
              "零件形状相同，只是 180 与 60 两个定位尺寸的出发点不同。")

    def shape(ox: int) -> None:
        F.polyline([(ox, 220), (ox + 60, 220), (ox + 60, 200), (ox + 240, 200),
                    (ox + 240, 260), (ox, 260)], cls="thick", close=True)

    # ---------- 左：设计基准（右端面） ----------
    panel_title(F, 240, 160, "① 从设计基准出发", size=12, color=BLUE)
    shape(120)
    F.datum_tri(360, 276, size=7, color=BLUE)
    F.text(360, 296, "设计基准（右端面）", size=11, color=BLUE)
    F.dim_h(180, 360, 330, "180", ext_from=(260, 260), color=BLUE)
    F.dim_h(120, 180, 168, "60", ext_from=(200, 220), color=BLUE)
    F.text(240, 386, "定位尺寸都从右端面量起 → 与设计要求一致", size=11, color=BLUE)

    # ---------- 右：工艺基准（左端面） ----------
    panel_title(F, 740, 160, "② 从工艺基准出发", size=12, color=ORANGE)
    shape(620)
    F.datum_tri(620, 276, size=7, color=ORANGE)
    F.text(626, 296, "工艺基准（左端面）", size=11, color=ORANGE, anchor="start")
    F.dim_h(620, 800, 330, "180", ext_from=(260, 260), color=ORANGE)
    F.dim_h(800, 860, 168, "60", ext_from=(200, 220), color=ORANGE)
    F.text(740, 386, "定位尺寸改用左端面量起 → 便于装夹与测量", size=11, color=ORANGE)

    notes(F, 40, 430, [
        "① 尺寸基准：标注尺寸时用来确定尺寸位置的几何元素（面、线、点）。每个方向至少有一个主要基准。",
        "② 设计基准：设计时用来确定零件在部件中位置的面（装配面、端面、轴线）。",
        "③ 工艺基准：加工、测量、装夹时使用的基准（端面、中心孔、工艺凸台）。",
        "④ 标注原则：同一方向的定位尺寸必须从同一个基准出发；设计基准与工艺基准尽量重合，否则会产生基准不重合误差。",
        "⑤ 易错：把 180 从左端标、60 从右端标 —— 尺寸基准不统一，读图和加工都会出错。",
    ], size=11, lh=22)
    return F


ALL = [fig_jiejiao_yuanzhu, fig_xiangguan_jianhua,
       fig_zuheti_xingtifa, fig_budi_sanshitu, fig_chicun_jizhun]
