"""第二批图 13–18：平键连接、滚动轴承、齿轮啮合、AutoCAD 界面、明细栏与序号、读零件图五步。"""
from __future__ import annotations

import math

from fig2kit import (AMBER, BLUE, GREEN, INK, MUTED, ORANGE, RED, TEAL, VIOLET, Fig2,
                     fig_title, notes, panel_title)


# ---------------------------------------------------------------------------
# 13. 平键连接的画法
# ---------------------------------------------------------------------------
def fig_jianlianjie() -> Fig2:
    F = Fig2("FIG2-JIANLIANJIE", 1000, 620,
             "平键连接装配剖视画法",
             "轴、轮毂、键三个零件同时被剖切，剖面线方向各不相同；键两侧面是工作面（接触），"
             "键顶面与轮毂槽底留间隙。")
    fig_title(F, "图 2-13  平键连接的画法（垂直于轴线的剖视）",
              "键宽 b=40、键高 h=36、轴槽深 t=30、轮毂槽深 t1=8（图中像素），间隙夸大画出。")

    cx, cy = 400, 300
    Rs, Rh = 80, 120           # 轴半径、轮毂外半径
    hb = 16                    # 键宽的一半
    y_surf = cy - math.sqrt(Rs * Rs - hb * hb)   # 轴表面与键槽侧面的交点 y
    y_shaft_bot = y_surf + 24  # 轴槽底
    y_hub_bot = y_surf - 7     # 轮毂槽底
    h_key = 28
    y_key_top = y_shaft_bot - h_key

    # ---- 轴（下部+两侧）：圆弧 + 键槽，剖面线 45° ----
    a_half = math.degrees(math.asin(-(Rs * Rs - hb * hb) ** 0.5 / Rs))
    shaft_arc = F.ellipse_pts(0, 0, 0, 0)  # 占位避免未定义（不用）
    d_shaft = (f"M{cx + hb},{y_surf:.1f} ")
    pts = []
    a0 = math.degrees(math.atan2(y_surf - cy, hb))
    for i in range(0, 73):
        a = math.radians(a0 + (360 - 2 * abs(a0)) * i / 72)
        pts.append((cx + Rs * math.cos(a), cy + Rs * math.sin(a)))
    d_shaft += "L" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    d_shaft += f" L{cx - hb},{y_shaft_bot:.1f} L{cx + hb},{y_shaft_bot:.1f} Z"
    F.path(d_shaft, cls=None, fill="url(#hatch45)")
    F.path(d_shaft, cls="thick")

    # ---- 轮毂：外圆 - 内孔 - 键槽，用 evenodd 挖空 ----
    outer = F.ellipse_pts(cx, cy, Rh, Rh, 0, 96)
    inner = F.ellipse_pts(cx, cy, Rs, Rs, 0, 96)
    d_hub = ("M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in outer) + " Z "
             "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in inner) + " Z "
             f"M{cx - hb},{y_hub_bot:.1f} L{cx + hb},{y_hub_bot:.1f} "
             f"L{cx + hb},{y_surf:.1f} L{cx - hb},{y_surf:.1f} Z")
    F.path(d_hub, cls=None, fill="url(#hatch135)", extra='fill-rule="evenodd"')
    F.circle(cx, cy, Rh, cls="thick")
    F.circle(cx, cy, Rs, cls="thick")

    # ---- 键：矩形，剖面线加密且方向不同 ----
    F.rect(cx - hb, y_key_top, 2 * hb, y_shaft_bot - y_key_top, cls="thick", fill="url(#hatch45d)")

    # ---- 中心线 ----
    F.line(cx - Rh - 20, cy, cx + Rh + 20, cy, cls="center", color=MUTED)
    F.line(cx, cy - Rh - 20, cx, y_shaft_bot + 30, cls="center", color=MUTED)

    # ---- 标注 ----
    F.dim_v(cx - Rh - 34, y_key_top, y_shaft_bot, "h", ext_from=(cx - hb, cx - hb), color=BLUE)
    F.dim_v(cx + Rh + 40, y_surf, y_shaft_bot, "t", ext_from=(cx + hb, cx + hb), color=GREEN, left=False)
    F.dim_v(cx + Rh + 86, y_hub_bot, y_surf, "t₁", ext_from=(cx + hb, cx + hb), color=ORANGE, left=False)
    F.leader(cx - hb - 6, y_shaft_bot - 6, cx - Rh - 60, y_shaft_bot + 40, "b（键宽）", color=BLUE, anchor="end")

    F.leader(cx - Rh - 44, cy + 50, cx - Rh - 120, cy + 96, "轴", color=MUTED, anchor="start")
    F.leader(cx + Rh - 26, cy - Rh + 22, cx + Rh + 34, cy - Rh - 16, "轮毂", color=MUTED, anchor="start")
    F.leader(cx + hb - 4, (y_key_top + y_shaft_bot) / 2, cx + Rh + 46, y_key_top + 34, "键",
             color=VIOLET, anchor="start")

    # 间隙提示
    F.line_arrow(cx + hb + 54, y_hub_bot, cx + hb + 54, y_key_top, color=RED, both=True)
    F.text(cx + hb + 62, y_key_top - 4, "顶面留间隙（夸大）", size=11, color=RED, anchor="start")

    notes(F, 40, 470, [
        "① 三个零件同时被剖切，剖面线方向必须两两不同（本图：轴 45°、轮毂 135°、键 45° 加密）。",
        "② 键的两侧面是工作面，与轴槽、轮毂槽的侧面接触 —— 接触面只画一条线，不画间隙。",
        "③ 键的顶面与轮毂槽底之间留有间隙，图上必须画出这个间隙（不能贴死）。",
        "④ 尺寸 t 是轴槽深、t₁ 是轮毂槽深，都从各自零件的表面量起；查表取标准值，不要自行凑数。",
    ], size=11, lh=22)
    return F


# ---------------------------------------------------------------------------
# 14. 滚动轴承的简化画法
# ---------------------------------------------------------------------------
def fig_zhoucheng_huafaa() -> Fig2:
    F = Fig2("FIG2-ZHOUCHENG-HUAFAA", 1000, 560,
             "滚动轴承剖视的简化画法",
             "剖视图中只画内圈、外圈和滚动体，不画保持架；滚动体画十字线；对称件只画上半，标注 d、D、B。")
    fig_title(F, "图 2-14  滚动轴承的规定画法（简化画法）",
              "轴承型号 6208：d=40、D=80、B=18（图中按比例放大绘制）。")

    ax = 380          # 轴线
    x0, B = 300, 220  # 左端、宽度
    y_in_top, y_in_bot = ax - 60, ax - 36     # 内圈上下边
    y_out_top, y_out_bot = ax - 132, ax - 108  # 外圈上下边
    # 轴（下半，示意）
    F.rect(x0 - 30, ax - 36, B + 30, 36, cls="thick", fill="url(#hatch45d)")
    # 内圈
    F.rect(x0, y_in_bot, B, y_in_top - y_in_bot, cls="thick", fill="url(#hatch45)")
    # 外圈
    F.rect(x0, y_out_top, B, y_out_bot - y_out_top, cls="thick", fill="url(#hatch135)")
    # 滚动体：十字线（不画保持架）
    for bx in (x0 + 50, x0 + B - 50):
        cy_b = (y_in_top + y_out_bot) / 2
        F.circle(bx, cy_b, 15, cls="thin")
        F.line(bx - 15, cy_b, bx + 15, cy_b, cls="thin")
        F.line(bx, cy_b - 15, bx, cy_b + 15, cls="thin")
    # 轴线
    F.line(x0 - 80, ax, x0 + B + 80, ax, cls="center", color=MUTED)

    # 标注
    F.dim_v(x0 + B + 40, ax - 36, ax, "d/2", ext_from=(x0 + B, x0 + B), left=False, color=BLUE)
    F.dim_v(x0 + B + 86, ax - 132, ax, "D/2", ext_from=(x0 + B, x0 + B), left=False, color=RED)
    F.dim_h(x0, x0 + B, ax - 168, "B", ext_from=(y_out_top, y_out_top), color=GREEN)

    F.leader(x0 + 10, y_in_bot + 14, x0 - 46, y_in_bot + 52, "内圈", color=BLUE, anchor="end")
    F.leader(x0 + 10, y_out_top + 14, x0 - 46, y_out_top - 6, "外圈", color=RED, anchor="end")
    F.text(x0 + B / 2, ax + 34, "只画上半（对称件），下半省略不画", size=11, color=MUTED)

    notes(F, 40, 470, [
        "① 规定画法：剖视图中只画内圈、外圈和滚动体，保持架不画（这是“简化画法”的核心）。",
        "② 滚动体在剖视中画成圆圈并加十字线；内外圈画成矩形并画剖面线，两者剖面线方向相反。",
        "③ 轴承是对称件，一般只画轴线一侧（上半），另一半省略不画。",
        "④ 主要尺寸代号：d 内径、D 外径、B 宽度 —— 与轴承型号一起标注在明细栏或装配图上。",
        "⑤ 易错：把内圈和外圈的剖面线画成同一方向（相邻零件必须相反）；或把保持架也画出来。",
    ], size=11, lh=21)
    return F


# ---------------------------------------------------------------------------
# 15. 圆柱齿轮啮合画法
# ---------------------------------------------------------------------------
def fig_chilun_niehe() -> Fig2:
    F = Fig2("FIG2-CHILUN-NIEHE", 1000, 560,
             "圆柱齿轮啮合画法：啮合区的五条线",
             "两齿轮啮合时，分度线重合为一条细点画线；两齿顶线一条画粗实线、一条画虚线；"
             "两齿根线都画粗实线。")
    fig_title(F, "图 2-15  两圆柱齿轮啮合的画法（啮合区五条线）",
              "分度圆在图上变成一条细点画线；齿顶线一实一虚，用来表示谁在前、谁被挡住。")

    x1, xm, x2 = 120, 372, 620   # 齿1 左端、啮合分界、齿2 右端
    y_pitch = 300
    ha, hf = 40, 50              # 齿顶高、齿根高（px）
    # 分度线（细点画线，两分度圆相切）
    F.line(x1 - 20, y_pitch, x2 + 20, y_pitch, cls="center", color=MUTED)
    # 齿轮 1（左，画在前）：齿顶线 y_pitch+ha，齿根线 y_pitch-hf
    F.line(x1, y_pitch + ha, xm + 24, y_pitch + ha, cls="thick")
    F.line(x1, y_pitch - hf, xm + 24, y_pitch - hf, cls="thick")
    # 齿轮 2（右，被遮）：齿顶线画虚线，齿根线粗实线
    F.line(xm - 24, y_pitch - ha, x2, y_pitch - ha, cls="dash")
    F.line(xm - 24, y_pitch + hf, x2, y_pitch + hf, cls="thick")
    # 两端面 + 轴线
    F.line(x1, y_pitch - hf, x1, y_pitch + ha, cls="thick")
    F.line(x2, y_pitch - ha, x2, y_pitch + hf, cls="thick")
    F.line((x1 + xm) / 2, y_pitch - hf - 34, (x1 + xm) / 2, y_pitch + ha + 34, cls="center", color=MUTED)
    F.line((xm + x2) / 2, y_pitch - ha - 34, (xm + x2) / 2, y_pitch + hf + 34, cls="center", color=MUTED)

    # 标注
    F.text((x1 + xm) / 2 - 60, y_pitch - hf - 46, "齿轮 1（主动）", size=12, weight="600")
    F.text((xm + x2) / 2 + 40, y_pitch - ha - 46, "齿轮 2（从动）", size=12, weight="600")
    F.leader(xm + 60, y_pitch + 2, xm + 90, y_pitch + 46, "分度线：两分度圆相切，画细点画线", color=VIOLET,
             anchor="start")
    F.leader(x1 + 200, y_pitch + ha, x1 + 150, y_pitch + ha + 56, "齿顶线（齿轮 1）：粗实线", color=GREEN,
             anchor="start")
    F.leader(x2 - 60, y_pitch - ha, x2 - 40, y_pitch - ha - 44, "齿顶线（齿轮 2）：虚线（被齿轮 1 挡住）",
             color=RED, anchor="end")
    F.leader(x1 + 60, y_pitch - hf, x1 + 20, y_pitch - hf - 56, "齿根线：粗实线", color=BLUE, anchor="start")

    notes(F, 40, 430, [
        "① 啮合区共五条线：一条分度线（两齿轮分度线重合，画细点画线）+ 两条齿顶线（一粗实线、一虚线）"
        "+ 两条齿根线（都画粗实线）。",
        "② 分度线在啮合区不是两条线，而是重合为一条细点画线 —— 这是最容易画错的地方。",
        "③ 齿顶线一实一虚，表示一个齿轮的齿顶可见、另一个被挡住；齿根线都画粗实线（都可见）。",
        "④ 啮合区外，每个齿轮仍按单个齿轮的规定画法画（齿顶线粗实线、分度线点画线、齿根线细实线或粗实线）。",
    ], size=11, lh=22)
    return F


# ---------------------------------------------------------------------------
# 16. AutoCAD 界面分区
# ---------------------------------------------------------------------------
def fig_autocad_jiemian() -> Fig2:
    F = Fig2("FIG2-AUTOCAD-JIEMIAN", 1040, 620,
             "AutoCAD 界面分区与常用命令",
             "AutoCAD 窗口分六个区：标题栏、菜单栏、功能区、绘图区、命令行、状态栏；"
             "起步只要记住 L、C、O、TR、CO 五个命令。")
    fig_title(F, "图 2-16  AutoCAD 界面分区（示意）与起步常用命令",
              "绘图区里能看到 UCS 坐标系图标和十字光标 —— 所有命令都在命令行里回显。")

    L, R = 40, 1000
    # 标题栏
    F.rect(L, 70, R - L, 28, cls="thin")
    F.text(L + 10, 89, "AutoCAD 2024  -  [Drawing1.dwg]", size=11, anchor="start")
    # 菜单栏
    F.rect(L, 98, R - L, 24, cls="thin")
    F.text(L + 10, 115, "文件   编辑   视图   插入   格式   工具   绘图   标注   修改   帮助", size=11, anchor="start")
    # 功能区
    F.rect(L, 122, R - L, 62, cls="thin")
    F.text(L + 10, 140, "默认   插入   注释   参数化   视图   管理   输出", size=11, anchor="start", color=BLUE)
    for i in range(4):
        F.rect(L + 10 + i * 120, 148, 108, 28, cls="thin", extra='stroke-opacity="0.55"')
    # 绘图区
    F.rect(L, 184, 780, 320, cls="thin")
    F.line(L + 60, 430, L + 130, 430, cls="thin", color=GREEN)      # UCS X
    F.line(L + 60, 430, L + 60, 360, cls="thin", color=GREEN)       # UCS Y
    F.text(L + 136, 434, "X", size=11, color=GREEN, anchor="start")
    F.text(L + 56, 352, "Y", size=11, color=GREEN)
    F.path(f"M{L + 400},{330} L{L + 560},{330} L{L + 560},{400} L{L + 400},{400} Z", cls="thin", color=BLUE)
    F.path(f"M{L + 330},{250} L{L + 420},{250}", cls="thin", color=MUTED)
    F.line(L + 430, 300, L + 520, 300, cls="thin", color=MUTED)
    # 十字光标
    F.line(L + 520, 240, L + 520, 380, cls="thin", color=AMBER, extra='stroke-opacity="0.7"')
    F.line(L + 450, 310, L + 590, 310, cls="thin", color=AMBER, extra='stroke-opacity="0.7"')
    # 右侧面板
    F.rect(820, 184, 180, 320, cls="thin")
    F.text(830, 204, "特性 / 图层", size=11, anchor="start", color=MUTED)
    for i in range(4):
        F.line(830, 222 + i * 26, 990, 222 + i * 26, cls="thin", color=MUTED, extra='stroke-opacity="0.4"')
    # 命令行
    F.rect(L, 504, R - L, 46, cls="thin")
    F.text(L + 10, 522, "命令: _line", size=11, anchor="start", color=BLUE)
    F.text(L + 10, 540, "指定第一个点:  指定下一点或 [放弃(U)]:", size=11, anchor="start", color=MUTED)
    # 状态栏
    F.rect(L, 550, R - L, 22, cls="thin")
    F.text(L + 10, 565, "模型  栅格  捕捉  正交  极轴  对象捕捉  对象追踪  允许/禁止动态 UCS  线宽  模型", size=11,
           anchor="start", color=MUTED)

    # 区块标注（放在图框外，避免压在内容上）
    for y, txt in ((84, "① 标题栏"), (110, "② 菜单栏"), (156, "③ 功能区"),
                   (200, "④ 绘图区"), (520, "⑤ 命令行"), (566, "⑥ 状态栏")):
        F.text(1016, y, txt, size=10, anchor="start", color=RED)

    notes(F, 40, 596, [
        "起步五个命令：L = 直线（Line）/ C = 圆（Circle）/ O = 偏移（Offset）/ TR = 修剪（Trim）/ CO = 复制（Copy）。",
    ], size=11, lh=20)
    return F


# ---------------------------------------------------------------------------
# 17. 装配图的序号与明细栏
# ---------------------------------------------------------------------------
def fig_zhuangpei_mingxi() -> Fig2:
    F = Fig2("FIG2-ZHUANGPEI-MINGXI", 1040, 620,
             "装配图的序号与明细栏",
             "装配图右下角画明细栏，零件用指引线引出并编序号；明细栏按序号自下而上排列，与图上序号一一对应。")
    fig_title(F, "图 2-17  装配图的零件序号与明细栏",
              "序号指引线从零件可见轮廓内引出，端部画小圆点；明细栏紧接标题栏上方，自下而上填写。")

    # 图框
    F.rect(60, 80, 900, 470, cls="thick")
    # 装配体示意：轴 + 齿轮 + 端盖
    F.rect(150, 250, 420, 60, cls="thick")                 # 轴
    F.rect(430, 220, 90, 120, cls="thick")                 # 齿轮（轮毂）
    F.rect(520, 236, 60, 88, cls="thick")                  # 端盖
    F.line(150, 280, 700, 280, cls="center", color=MUTED)
    F.line(560, 236, 560, 324, cls="thick")
    F.text(330, 350, "装配体示意（轴 — 齿轮 — 端盖）", size=11, color=MUTED)

    # 序号：指引线 + 圆点 + 圆圈编号
    for (px, py, tx, ty, no) in ((200, 268, 200, 170, "1"), (470, 236, 470, 150, "2"), (548, 246, 620, 150, "3")):
        F.line(px, py, tx, ty - 12, cls="thin")
        F.dot(px, py, 2.4)
        F.circle(tx, ty - 24, 11, cls="thin")
        F.text(tx, ty - 20, no, size=12, weight="600")
        F.line(tx, ty - 13, tx, ty - 4, cls="thin")
        F.line(tx, ty - 4, tx + 14, ty - 4, cls="thin")

    # 明细栏（表格）
    tx0, ty0 = 600, 330
    cols = [44, 130, 150, 56, 90, 90]
    heads = ["序号", "代号", "名称", "数量", "材料", "备注"]
    rows = [("3", "Dg-03", "端盖", "1", "HT200", ""),
            ("2", "Dg-02", "圆柱齿轮", "1", "45", "m=2 z=40"),
            ("1", "Dg-01", "轴", "1", "45", "调质")]
    xs = [tx0]
    for w in cols:
        xs.append(xs[-1] + w)
    total_w = xs[-1] - tx0
    n_rows = len(rows)
    row_h = 26
    top = ty0
    # 横线：表头上下 + 每行
    for i in range(n_rows + 2):
        F.line(tx0, top + i * row_h, tx0 + total_w, top + i * row_h, cls="thin")
    # 竖线
    for x in xs:
        F.line(x, top, x, top + (n_rows + 1) * row_h, cls="thin")
    for i, h in enumerate(heads):
        F.text(xs[i] + 5, top + 18, h, size=10, anchor="start", weight="600")
    for r, row in enumerate(rows):
        for i, cell in enumerate(row):
            F.text(xs[i] + 5, top + row_h * (r + 2) - 8, cell, size=10, anchor="start")

    # 标题栏
    F.rect(tx0, top + (n_rows + 1) * row_h, total_w, 60, cls="thick")
    F.text(tx0 + total_w / 2, top + (n_rows + 2) * row_h + 24, "减速器装配图", size=12, weight="600")
    F.text(tx0 + total_w / 2, top + (n_rows + 2) * row_h + 42, "比例 1:1　　图号 Dg-00", size=10, color=MUTED)

    notes(F, 60, 578, [
        "① 序号用指引线从零件的可见轮廓内引出，端部画小圆点，再画横线，序号写在横线上方（或圆圈内）。",
        "② 明细栏紧接在标题栏上方，自下而上按序号排列；栏内项目与图上序号一一对应。",
    ], size=11, lh=20)
    return F


# ---------------------------------------------------------------------------
# 18. 读零件图五步
# ---------------------------------------------------------------------------
def fig_lingjian_wubu() -> Fig2:
    F = Fig2("FIG2-LINGJIAN-WUBU", 1040, 620,
             "读零件图的五个步骤",
             "读零件图按五步走：看标题栏、分析视图、想形体、找尺寸基准、读技术要求；箭头把五步串成流程。")
    fig_title(F, "图 2-18  读零件图的五个步骤（以轴类零件为例）",
              "五步的顺序不能颠倒：先看清是什么零件，再想形状，最后才读尺寸与技术要求。")

    # ---------- 零件图：阶梯轴 ----------
    ax = 250
    F.line(70, ax, 470, ax, cls="center", color=MUTED)
    # 轴轮廓（三段直径：Ø60 / Ø80 / Ø40）
    F.polyline([(90, ax - 30), (200, ax - 30), (200, ax - 40), (330, ax - 40), (330, ax - 20),
                (450, ax - 20), (450, ax + 20), (330, ax + 20), (330, ax + 40), (200, ax + 40),
                (200, ax + 30), (90, ax + 30)], cls="thick", close=True)
    # 键槽（主视图中的虚线）
    F.line(230, ax - 10, 300, ax - 10, cls="dash")
    F.line(230, ax + 10, 300, ax + 10, cls="dash")
    # 尺寸
    F.dim_h(90, 200, ax + 96, "40", ext_from=(ax + 30, ax + 30), color=BLUE)
    F.dim_h(200, 330, ax + 96, "65", ext_from=(ax + 40, ax + 40), color=BLUE)
    F.dim_h(330, 450, ax + 96, "60", ext_from=(ax + 20, ax + 20), color=BLUE)
    F.text(96, ax - 40, "Ø60", size=11, color=BLUE, anchor="start")
    F.text(388, ax - 32, "Ø40", size=11, color=BLUE, anchor="start")
    F.text(232, ax - 58, "Ø80", size=11, color=BLUE, anchor="middle")
    # 表面结构符号
    def ra(x, y):
        F.line(x, y, x - 8, y + 14, cls="thin")
        F.line(x, y, x + 18, y + 14, cls="thin")
        F.text(x + 24, y + 10, "Ra 3.2", size=10, anchor="start", color=MUTED)
    ra(118, ax - 62)
    ra(400, ax - 54)
    F.text(70, ax - 86, "零件图（轴）：先看视图，再读尺寸与技术要求", size=11, color=MUTED, anchor="start")

    # ---------- 五步卡片 ----------
    steps = [
        ("①", "看标题栏", "名称、材料、比例、图号", BLUE),
        ("②", "分析视图", "用了哪些视图、剖视、断面", GREEN),
        ("③", "想形体", "分块想象立体形状", ORANGE),
        ("④", "找尺寸基准", "长/宽/高基准在哪", VIOLET),
        ("⑤", "读技术要求", "尺寸公差、Ra、热处理", RED),
    ]
    x0, y0, w, h = 60, 430, 176, 76
    for i, (no, name, desc, col) in enumerate(steps):
        x = x0 + i * 192
        F.rect(x, y0, w, h, cls="thin", color=col, rx=6)
        F.text(x + 12, y0 + 26, f"{no} {name}", size=12, weight="600", anchor="start", color=col)
        F.text(x + 12, y0 + 48, desc, size=10, anchor="start", color=MUTED)
        if i < 4:
            F.line_arrow(x + w + 4, y0 + h / 2, x + w + 14, y0 + h / 2, color=MUTED, both=False)

    notes(F, 60, 560, [
        "① 五步读完，再回头核对：视图与尺寸是否对得上、技术要求和尺寸精度是否与结构相称。",
        "② 常见错误：跳过标题栏直接读尺寸（不知道材料和比例）；或只看主视图，不看其他视图就下结论。",
    ], size=11, lh=20)
    return F


ALL = [fig_jianlianjie, fig_zhoucheng_huafaa, fig_chilun_niehe,
       fig_autocad_jiemian, fig_zhuangpei_mingxi, fig_lingjian_wubu]
