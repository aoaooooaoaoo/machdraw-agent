"""第二批图 1–6：正等测、斜二测、圆的正等测、点的三面投影、直线的投影、平面的投影。"""
from __future__ import annotations

import math

from fig2kit import (AMBER, BLUE, GREEN, INK, MUTED, ORANGE, RED, TEAL, VIOLET, Fig2,
                     fig_title, notes, panel_title)

D = 0.866  # 标准等测的轴向系数（=√3/2）


# ---------------------------------------------------------------------------
# 1. 正等轴测图：轴间角 120° + 长方体三步画法
# ---------------------------------------------------------------------------
def fig_zhoudce_zhengdeng() -> Fig2:
    F = Fig2("FIG2-ZHOUDUCE-ZHENGDENG", 1040, 640,
             "正等轴测图的轴间角与长方体三步画法",
             "轴间角均为 120°，轴向伸缩系数 p=q=r≈0.82（简化取 1）；长方体按“定底面 → 竖高度 → 完成”三步画出。")
    fig_title(F, "图 2-1  正等轴测图的形成与画法（长方体 60×40×30）",
              "轴测轴三根互成 120°；轴向尺寸按 1:1 量取（简化系数），斜线不量取。")

    # ---------- 左：轴测轴 ----------
    ox, oy = 250, 400
    L = 150
    Xt = (ox - L * D, oy + L * 0.5)
    Yt = (ox + L * D, oy + L * 0.5)
    Zt = (ox, oy - L)
    F.line(ox, oy, *Xt, cls="thick")
    F.line(ox, oy, *Yt, cls="thick")
    F.line(ox, oy, *Zt, cls="thick")
    for a0, a1 in ((30, 150), (150, 270), (270, 390)):
        F.arc(ox, oy, 46, a0, a1, cls="thin", color=BLUE, n=32)
    for ang, txt in ((90, "120°"), (210, "120°"), (330, "120°")):
        r = 62
        F.text(ox + r * math.cos(math.radians(ang)), oy + r * math.sin(math.radians(ang)) + 4,
               txt, size=11, color=BLUE)
    F.text(Xt[0] - 6, Xt[1] + 18, "X", size=12, weight="600", anchor="end")
    F.text(Yt[0] + 6, Yt[1] + 18, "Y", size=12, weight="600", anchor="start")
    F.text(Zt[0], Zt[1] - 10, "Z", size=12, weight="600")
    F.text(ox - 10, oy + 20, "O", size=12, weight="600", anchor="end")
    panel_title(F, ox, 200, "轴测轴与轴间角")

    # ---------- 右：三步 ----------
    K = 1.75
    A, B, H = 60, 40, 30
    cells = [(600, 470, "① 定底面"), (800, 470, "② 竖高度"), (1000, 470, "③ 完成")]
    for i, (cx, cy, name) in enumerate(cells):
        panel_title(F, cx - 30, 392, name, size=12)
        if i == 0:
            # 轴测轴（简化为两条底轴）
            F.line(cx, cy, *F.iso(A, 0, 0, cx, cy, K), cls="thin", color=MUTED)
            F.line(cx, cy, *F.iso(0, B, 0, cx, cy, K), cls="thin", color=MUTED)
            F.iso_poly([(0, 0, 0), (A, 0, 0), (A, B, 0), (0, B, 0)], cx, cy, K, cls="thick")
        elif i == 1:
            F.iso_poly([(0, 0, 0), (A, 0, 0), (A, B, 0), (0, B, 0)], cx, cy, K, cls="thick")
            for p in ((0, 0), (A, 0), (A, B), (0, B)):
                F.line(*F.iso(p[0], p[1], 0, cx, cy, K), *F.iso(p[0], p[1], H, cx, cy, K), cls="thick")
        else:
            hidden = (A, B, H)
            edges = [
                ((0, 0, 0), (A, 0, 0)), ((A, 0, 0), (A, B, 0)), ((A, B, 0), (0, B, 0)), ((0, B, 0), (0, 0, 0)),
                ((0, 0, H), (A, 0, H)), ((A, 0, H), (A, B, H)), ((A, B, H), (0, B, H)), ((0, B, H), (0, 0, H)),
                ((0, 0, 0), (0, 0, H)), ((A, 0, 0), (A, 0, H)), ((A, B, 0), (A, B, H)), ((0, B, 0), (0, B, H)),
            ]
            vis = [(p, q) for p, q in edges if hidden not in (p, q)]
            F.iso_edges(vis, cx, cy, K, cls="thick")
            # 尺寸：长、宽、高
            F.text(*F.iso(A / 2, 0, 0, cx, cy, K), "60", size=11, anchor="middle", color=MUTED,
                   extra='dy="16"')
            F.text(*F.iso(0, B / 2, 0, cx, cy, K), "40", size=11, anchor="end", color=MUTED,
                   extra='dx="-8" dy="12"')
            F.text(*F.iso(0, 0, H / 2, cx, cy, K), "30", size=11, anchor="end", color=MUTED,
                   extra='dx="-10"')

    notes(F, 40, 566, [
        "① 定底面：沿 X、Y 方向按 1:1 量出长 60、宽 40，得底面菱形（轴测图里矩形画成平行四边形）。",
        "② 竖高度：从底面四个顶点向上引垂线，量高 30。",
        "③ 完成：连出顶面平行线，只画可见的 9 条棱 —— 被挡住的那个角（后下角）的 3 条棱不画，也不画虚线。",
        "口诀：轴向尺寸直接量，非轴向尺寸不能量（要按坐标求出两端点再连线）。",
    ], size=11, lh=21)
    return F


# ---------------------------------------------------------------------------
# 2. 斜二测
# ---------------------------------------------------------------------------
def fig_zhoudce_xieer() -> Fig2:
    F = Fig2("FIG2-ZHOUDUCE-XIEER", 1000, 560,
             "斜二轴测图：轴间角与轴向伸缩系数",
             "斜二测轴间角为 90°、135°、135°，X、Z 系数为 1、Y 系数为 0.5；"
             "同一长方体在斜二测中前面反映实形、宽取一半。")
    fig_title(F, "图 2-2  斜二轴测图（同一长方体 60×40×30）",
              "与正等测的区别：斜二测有一个面平行于轴测投影面，该面反映实形。")

    # ---------- 左：轴测轴 ----------
    ox, oy = 190, 360
    Xt = (ox + 130, oy)
    Zt = (ox, oy - 130)
    Yt = (ox - 92, oy - 92)  # 135°
    F.line(ox, oy, *Xt, cls="thick")
    F.line(ox, oy, *Zt, cls="thick")
    F.line(ox, oy, *Yt, cls="thick")
    F.arc(ox, oy, 40, -90, 0, cls="thin", color=BLUE, n=24)  # X-Z 之间 90°
    F.text(ox + 52, oy - 30, "90°", size=11, color=BLUE)
    F.text(Xt[0] + 4, Xt[1] + 18, "X", size=12, weight="600", anchor="start")
    F.text(Zt[0], Zt[1] - 10, "Z", size=12, weight="600")
    F.text(Yt[0] - 10, Yt[1] - 6, "Y", size=12, weight="600", anchor="end")
    F.text(ox + 12, oy + 18, "O", size=12, weight="600", anchor="start")
    F.text(ox, 190, "轴间角 90°、135°、135°", size=12, weight="600")
    F.text(ox, 208, "p = r = 1，q = 0.5", size=11, color=MUTED)

    # ---------- 右：长方体 ----------
    K = 2.0
    q = 0.5  # Y 向系数
    cx, cy = 470, 420
    A, B, H = 60, 40, 30

    def scr(x, y, z):
        return (cx + K * x - D * K * q * y, cy - K * z - D * K * q * y)

    pts = {(x, y, z): scr(x, y, z) for x in (0, A) for y in (0, B) for z in (0, H)}
    hidden = (A, B, 0)
    edges = [
        ((0, 0, 0), (A, 0, 0)), ((A, 0, 0), (A, B, 0)), ((A, B, 0), (0, B, 0)), ((0, B, 0), (0, 0, 0)),
        ((0, 0, H), (A, 0, H)), ((A, 0, H), (A, B, H)), ((A, B, H), (0, B, H)), ((0, B, H), (0, 0, H)),
        ((0, 0, 0), (0, 0, H)), ((A, 0, 0), (A, 0, H)), ((A, B, 0), (A, B, H)), ((0, B, 0), (0, B, H)),
    ]
    d = " ".join(
        f"M{pts[p][0]:.2f},{pts[p][1]:.2f} L{pts[q_][0]:.2f},{pts[q_][1]:.2f}"
        for p, q_ in edges if hidden not in (p, q_)
    )
    F.path(d, cls="thick")

    # 前面（XZ 面）是实形 —— 用淡色强调
    F.polyline([pts[(0, 0, 0)], pts[(A, 0, 0)], pts[(A, 0, H)], pts[(0, 0, H)]],
               cls="thin", close=True, color=BLUE, extra='stroke-dasharray="2 3"')
    fx, fy = scr(A / 2, 0, 0)
    F.text(fx, fy + 26, "前面：反映实形", size=11, color=BLUE, anchor="middle")

    # 宽度方向取一半的标注
    F.leader(*scr(A, B / 2, H), cx + 190, cy - 150,
             "宽 40 → 只画 20（q = 0.5）", color=RED, anchor="start")
    F.leader(*scr(A / 2, 0, H), cx + 60, cy - 120, "长 60 = 实长", color=MUTED, anchor="start")

    notes(F, 640, 300, [
        "① 斜二测：X、Z 轴仍成 90°（与正等测的 120° 不同），Y 轴与两者各成 135°。",
        "② X、Z 方向取实长（系数 1）；Y 方向只取一半（系数 0.5）。",
        "③ 平行于 XOZ 面的圆，在斜二测里仍画成圆（不用画椭圆）—— 这是斜二测最大的好处。",
        "④ 缺点：立体感不如正等测，故一般只用于“一个方向形状复杂、另两个方向简单”的零件。",
    ], size=11, lh=22)
    return F


# ---------------------------------------------------------------------------
# 3. 圆的正等测（椭圆 + 四心圆法）
# ---------------------------------------------------------------------------
def fig_zhoudce_yuan() -> Fig2:
    F = Fig2("FIG2-ZHOUDUCE-YUAN", 1000, 620,
             "圆的正等测：椭圆长短轴方向与四心圆法",
             "正等测中圆变成椭圆，长轴约 1.22d、短轴约 0.71d；四心圆法用四段圆弧近似作出椭圆。")
    fig_title(F, "图 2-3  圆的正等测画法（四心圆法，圆 Ø140）",
              "关键：椭圆长轴永远垂直于该圆所在平面法线的投影方向。")

    # ---------- 左：四心圆法 ----------
    cx, cy = 300, 330
    dia = 140.0
    p = D * dia            # 121.24
    q = dia / 2            # 70
    A = (cx, cy - q)       # 上顶点
    C = (cx, cy + q)       # 下顶点
    B = (cx + p, cy)       # 右顶点
    Dd = (cx - p, cy)      # 左顶点
    o3 = (cx - p / 3, cy)  # 左侧小弧圆心
    o4 = (cx + p / 3, cy)  # 右侧小弧圆心

    # 菱形（外切正方形的轴测）+ 两条对角线
    F.polyline([A, B, C, Dd], cls="thin", close=True, color=MUTED)
    F.path(f"M{A[0]},{A[1]} L{C[0]},{C[1]} M{Dd[0]},{Dd[1]} L{B[0]},{B[1]}", cls="thin", color=MUTED,
           extra='stroke-dasharray="6 4"')

    # 四段弧
    F.arc(C[0], C[1], p, -120, -60, cls="thick", n=40)   # 上弧（圆心 C）
    F.arc(A[0], A[1], p, 60, 120, cls="thick", n=40)     # 下弧（圆心 A）
    F.arc(o4[0], o4[1], p / 3, -60, 60, cls="thick", n=32)  # 右弧
    F.arc(o3[0], o3[1], p / 3, 120, 240, cls="thick", n=32)  # 左弧

    # 圆心与切点
    for pt in (A, C, o3, o4):
        F.dot(*pt, r=2.2)
    for pt, lbl, dx, dy, an in ((A, "O₁", 0, -12, "middle"), (C, "O₂", 0, 20, "middle"),
                                (o3, "O₃", -10, -8, "end"), (o4, "O₄", 10, 20, "start")):
        F.text(pt[0] + dx, pt[1] + dy, lbl, size=12, weight="600", color=BLUE, anchor=an)
    mids = [((A[0] + B[0]) / 2, (A[1] + B[1]) / 2), ((B[0] + C[0]) / 2, (B[1] + C[1]) / 2),
            ((C[0] + Dd[0]) / 2, (C[1] + Dd[1]) / 2), ((Dd[0] + A[0]) / 2, (Dd[1] + A[1]) / 2)]
    for i, m in enumerate(mids):
        F.tick(m[0], m[1], l=7, cls="thin", color=RED)

    F.text(cx, cy - 178, "四心圆法", size=12, weight="600")
    F.leader(o4[0] + 34, o4[1] - 12, cx + 150, cy - 108, "小弧半径 R₁ = ρ/3", color=RED, anchor="start")
    F.leader(C[0] + 60, C[1] - 24, cx + 150, cy + 128, "大弧半径 R₂ = ρ", color=RED, anchor="start")
    F.text(cx, cy + 176, "切点在菱形四边中点（红短线）；ρ = 0.866d 为菱形长半对角线", size=11, color=RED)

    # ---------- 右：三个面的椭圆方向 ----------
    dd = 100.0
    E = 0.611 * dd      # 半长轴 ≈1.22d/2
    e = 0.354 * dd      # 半短轴 ≈0.71d/2
    for (ex, ey, rot, name, note_) in (
        (700, 250, 0, "水平面上的圆", "长轴水平"),
        (850, 250, -60, "正平面上的圆", "长轴与水平成 120°"),
        (1000, 250, 60, "侧平面上的圆", "长轴与水平成 60°"),
    ):
        F.ellipse(ex, ey, E, e, rot, cls="thick")
        a = math.radians(rot)
        dx, dy = E * math.cos(a), E * math.sin(a)
        F.path(f"M{ex - dx:.1f},{ey - dy:.1f} L{ex + dx:.1f},{ey + dy:.1f}", cls="thin", color=BLUE,
               extra='stroke-dasharray="10 3 3 3"')
        b = math.radians(rot + 90)
        dx2, dy2 = e * math.cos(b), e * math.sin(b)
        F.path(f"M{ex - dx2:.1f},{ey - dy2:.1f} L{ex + dx2:.1f},{ey + dy2:.1f}", cls="thin", color=RED,
               extra='stroke-dasharray="10 3 3 3"')
        F.text(ex, ey + 96, name, size=11, weight="600")
        F.text(ex, ey + 113, note_, size=11, color=MUTED)
    F.text(850, 148, "长轴 ≈ 1.22d（蓝）、短轴 ≈ 0.71d（红）", size=11)

    notes(F, 40, 536, [
        "① 四心圆法是近似画法：四个圆心取在短对角线两端与长对角线上，四段弧在菱形各边中点相接。",
        "② 长轴近似 1.22d、短轴 0.71d（d 为圆的直径）；实际作图用四心法即可，不必量轴长。",
        "③ 三个坐标面上的圆，椭圆长轴方向不同 —— 长轴始终垂直于该面法线的轴测投影方向。",
    ], size=11, lh=21)
    return F


# ---------------------------------------------------------------------------
# 4. 点的三面投影
# ---------------------------------------------------------------------------
def fig_dian_sanmian() -> Fig2:
    F = Fig2("FIG2-DIAN-SANMIAN", 1000, 640,
             "点的三面投影与展开图",
             "点 A 向 V、H、W 三个投影面投射得 a′、a、a″；展开后 a′a ⊥ OX（长对正）、"
             "a′a″ ⊥ OZ（高平齐）、a 到 OX 的距离等于 a″ 到 OZ 的距离（宽相等）。")
    fig_title(F, "图 2-4  点的三面投影（A 距 V 面 90、距 H 面 70、距 W 面 110，单位 mm）",
              "左：三投影面体系立体图；右：三个投影面展开后的投影图。")

    # ---------- 左：展开图 ----------
    ox, oy = 300, 400
    xa, ya, za = 150, 80, 110
    F.line(ox, oy, ox + 240, oy, cls="thin")
    F.line(ox, oy, ox, oy - 260, cls="thin")
    F.line(ox, oy, ox + 130, oy + 130, cls="thin", color=MUTED, extra='stroke-dasharray="6 4"')
    F.text(ox + 244, oy + 14, "X", size=12, weight="600", anchor="start")
    F.text(ox - 14, oy - 262, "Z", size=12, weight="600", anchor="end")
    F.text(ox - 12, oy + 18, "O", size=12, weight="600", anchor="end")
    F.text(ox + 138, oy + 126, "45°", size=11, color=MUTED, anchor="start")

    ap = (ox + xa, oy - za)          # a′（V 面）
    ah = (ox + xa, oy + ya)          # a（H 面）
    aw = (ox + ya, oy - za)          # a″（W 面）
    for pt, lbl, dx, dy, an in ((ap, "a′", 10, -8, "start"), (ah, "a", 10, 16, "start"),
                                (aw, "a″", -10, -8, "end")):
        F.dot(*pt, r=2.6, color=BLUE)
        F.text(pt[0] + dx, pt[1] + dy, lbl, size=13, weight="600", color=BLUE, anchor=an)

    F.line(ap[0], ap[1], ah[0], ah[1], cls="dash", color=GREEN)        # 长对正
    F.line(aw[0], aw[1], ap[0], ap[1], cls="dash", color=ORANGE)       # 高平齐
    F.path(f"M{ah[0]},{ah[1]} L{ox + ya},{ah[1]} L{aw[0]},{aw[1]}", cls="dash", color=VIOLET)  # 宽相等

    F.text(ox + xa / 2, oy - 10, "x", size=12, color=GREEN)
    F.text(ox - 12, oy - za / 2, "z", size=12, color=ORANGE, anchor="end")
    F.text(ox + ya + 34, oy + ya - 8, "y", size=12, color=VIOLET, anchor="start")
    F.text(ox + 120, oy - 290, "展开图（三个投影面展开到一个平面）", size=12, weight="600")

    # ---------- 右：坐标关系 ----------
    rx = 620
    F.text(rx, 170, "投影与坐标的对应关系", size=12, weight="600", anchor="start")
    rows = [
        ("a′（正面投影 V）", "由 x、z 确定", GREEN),
        ("a（水平投影 H）", "由 x、y 确定", TEAL),
        ("a″（侧面投影 W）", "由 y、z 确定", VIOLET),
    ]
    for i, (name, coord, col) in enumerate(rows):
        y = 208 + i * 34
        F.text(rx, y, name, size=12, anchor="start", color=BLUE)
        F.text(rx + 170, y, coord, size=11, anchor="start", color=col)

    F.text(rx, 340, "三等规律（展开图上的三条线）", size=12, weight="600", anchor="start")
    rules = [
        ("长对正", "a′ 与 a 在同一条竖线上（x 相同）", GREEN),
        ("高平齐", "a′ 与 a″ 在同一条水平线上（z 相同）", ORANGE),
        ("宽相等", "a 到 OX 的距离 = a″ 到 OZ 的距离（都是 y）", VIOLET),
    ]
    for i, (k, v, col) in enumerate(rules):
        y = 372 + i * 26
        F.text(rx, y, k, size=11, weight="600", anchor="start", color=col)
        F.text(rx + 62, y, v, size=11, anchor="start")

    F.text(rx, 470, "点到投影面的距离", size=12, weight="600", anchor="start")
    F.text(rx + 8, 496, "到 V 面 = y　　到 H 面 = z　　到 W 面 = x", size=11, anchor="start", color=MUTED)
    F.text(rx, 534, "记住：投影面的名称决定了“用哪两个坐标”。", size=11, anchor="start", color=MUTED)

    notes(F, 40, 552, [
        "① a′（V 面）由 x、z 定；a（H 面）由 x、y 定；a″（W 面）由 y、z 定 —— 投影面名称决定坐标组合。",
        "② 长对正：a′ 与 a 在同一条竖线上（同 x）；高平齐：a′ 与 a″ 在同一条水平线上（同 z）。",
        "③ 宽相等：a 到 OX 的距离 = a″ 到 OZ 的距离（都是 y），展开图上靠 45° 线把 y 搬过来。",
        "④ 画图口诀：一竖（a′a）、一横（a′a″）、一搬（a → 45° 线 → a″）。",
    ], size=11, lh=21)
    return F


# ---------------------------------------------------------------------------
# 5. 直线的投影
# ---------------------------------------------------------------------------
def fig_xian_typical() -> Fig2:
    F = Fig2("FIG2-XIAN-TYPICAL", 1040, 620,
             "直线的三面投影：一般位置、投影面平行、投影面垂直",
             "三类直线在 V、H 面上的投影特征：一般位置三投影都小于实长；平行线有一个投影反映实长；"
             "垂直线有一个投影积聚成点。")
    fig_title(F, "图 2-5  直线的投影特征（三类直线对照）",
              "上为 V 面投影（a′b′），下为 H 面投影（ab），中间的横线是投影轴 OX。")

    def panel(ox, oy, a, b, title, tags):
        """a、b 为两端点 (x, y, z)，单位 px。"""
        panel_title(F, ox + 120, 150, title, size=12)
        F.line(ox - 10, oy, ox + 250, oy, cls="thin", color=MUTED)  # OX
        F.text(ox + 252, oy + 14, "OX", size=10, color=MUTED, anchor="start")
        F.text(ox - 16, oy - 60, "V", size=11, color=MUTED, anchor="end")
        F.text(ox - 16, oy + 60, "H", size=11, color=MUTED, anchor="end")
        ap, bp = (ox + a[0], oy - a[2]), (ox + b[0], oy - b[2])
        ah, bh = (ox + a[0], oy + a[1]), (ox + b[0], oy + b[1])
        F.line(*ap, *bp, cls="thick")
        F.line(*ah, *bh, cls="thick")
        for p, q in ((ap, ah), (bp, bh)):
            F.line(p[0], p[1], q[0], q[1], cls="dash", color=MUTED)
        F.dot(*ap, r=2.2)
        F.dot(*bp, r=2.2)
        F.dot(*ah, r=2.2)
        F.dot(*bh, r=2.2)
        F.text(ap[0] - 8, ap[1] - 4, "a′", size=11, weight="600", anchor="end")
        F.text(bp[0] + 8, bp[1] - 4, "b′", size=11, weight="600", anchor="start")
        F.text(ah[0] - 8, ah[1] + 14, "a", size=11, weight="600", anchor="end")
        F.text(bh[0] + 8, bh[1] + 14, "b", size=11, weight="600", anchor="start")
        for i, (txt, col) in enumerate(tags):
            F.text(ox + 130, 400 + i * 20, txt, size=11, color=col, anchor="middle")

    # ① 一般位置直线
    panel(50, 300, (30, 26, 70), (150, 60, 16), "① 一般位置直线",
          [("三个投影都小于实长，都倾斜于投影轴", RED), ("求实长要用直角三角形法", MUTED)])
    # ② 水平线（平行于 H）
    panel(390, 300, (30, 20, 50), (150, 26, 50), "② 投影面平行线（水平线）",
          [("a′b′ ∥ OX（正面投影水平）", RED), ("ab 反映实长，并反映与 V 面的夹角 β", BLUE)])
    # ③ 铅垂线（垂直于 H）
    panel(730, 300, (60, 26, 16), (60, 26, 96), "③ 投影面垂直线（铅垂线）",
          [("水平投影积聚成一点 a(b)", RED), ("a′b′ 反映实长，且垂直于 OX", BLUE)])

    notes(F, 40, 508, [
        "① 一般位置直线：三投影都倾斜于投影轴、都小于实长 —— 想求实长与倾角，只能用直角三角形法或换面法。",
        "② 投影面平行线：有一个投影平行于投影轴，另一个投影反映实长和真实倾角（本图水平线的 ab 即实长）。",
        "③ 投影面垂直线：有一个投影积聚成一点，另一个投影反映实长且垂直于投影轴。",
        "④ 读图时先看“有没有平行于投影轴”“有没有积聚成点”，就能立刻判断直线属于哪一类。",
    ], size=11, lh=21)
    return F


# ---------------------------------------------------------------------------
# 6. 平面的投影
# ---------------------------------------------------------------------------
def fig_pingmian_typical() -> Fig2:
    F = Fig2("FIG2-PINGMIAN-TYPICAL", 1040, 600,
             "平面的三面投影：一般位置、投影面平行、投影面垂直",
             "一般位置平面的三投影都是类似形（缩小）；平行面有一个投影反映真形；垂直面有一个投影积聚成斜线。")
    fig_title(F, "图 2-6  平面的投影特征（三类平面对照）",
              "三角形 ABC 分别处于三种位置；上为 V 面投影，下为 H 面投影。")

    def panel(ox, oy, X, Y, Z, title, tags):
        panel_title(F, ox + 115, 148, title, size=12)
        F.line(ox - 10, oy, ox + 240, oy, cls="thin", color=MUTED)
        F.text(ox - 16, oy - 55, "V", size=11, color=MUTED, anchor="end")
        F.text(ox - 16, oy + 55, "H", size=11, color=MUTED, anchor="end")
        # V 投影：用 (x, z)
        pv = [(ox + X[i], oy - Z[i]) for i in range(3)]
        ph = [(ox + X[i], oy + Y[i]) for i in range(3)]
        F.polyline(pv, cls="thick", close=True)
        F.polyline(ph, cls="thick", close=True)
        for i, (p, q) in enumerate(zip(pv, ph)):
            F.line(p[0], p[1], q[0], q[1], cls="dash", color=MUTED)
        for i, lbl in enumerate(["a′", "b′", "c′"]):
            F.text(pv[i][0], pv[i][1] - 7, lbl, size=11, weight="600", anchor="middle")
        for i, lbl in enumerate(["a", "b", "c"]):
            F.text(ph[i][0], ph[i][1] + 15, lbl, size=11, weight="600", anchor="middle")
        for i, (txt, col) in enumerate(tags):
            F.text(ox + 120, 392 + i * 20, txt, size=11, color=col, anchor="middle")

    # ① 一般位置平面
    panel(50, 288, [40, 160, 92], [20, 34, 72], [70, 20, 44], "① 一般位置平面",
          [("三个投影都是类似形（缩小）", RED), ("都不反映真形，也不积聚", MUTED)])
    # ② 水平面（平行于 H）
    panel(390, 288, [40, 160, 100], [34, 34, 34], [30, 30, 30], "② 投影面平行面（水平面）",
          [("正面投影积聚成一条水平线", RED), ("水平投影反映真形", BLUE)])
    # ③ 铅垂面（垂直于 H）
    panel(730, 288, [40, 40, 140], [20, 70, 44], [84, 20, 50], "③ 投影面垂直面（铅垂面）",
          [("水平投影积聚成一条斜线", RED), ("正面投影为类似形", MUTED)])

    notes(F, 40, 478, [
        "① 一般位置平面：三面投影都是“类似形”——形状相似但都比真形小，且不积聚。",
        "② 投影面平行面：与一个投影面平行 → 该面投影反映真形，另两个投影积聚成直线（且平行于相应投影轴）。",
        "③ 投影面垂直面：与一个投影面垂直 → 该面投影积聚成一条斜线，另两个投影是类似形。",
        "④ 判断口诀：先找“有没有积聚成一条线 / 有没有反映真形”，平面位置立刻定。",
    ], size=11, lh=21)
    return F


ALL = [fig_zhoudce_zhengdeng, fig_zhoudce_xieer, fig_zhoudce_yuan,
       fig_dian_sanmian, fig_xian_typical, fig_pingmian_typical]
