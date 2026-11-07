"""图 10–15：公差带、圆弧连接、螺纹比例画法、表面结构、尺寸注法四要素、三种配合。

公差数值全部经 apps/api/app/domain/tolerance.py（GB/T 1800 引擎）核对：
  Φ30 H7 = 0 / +21 μm     Φ30 k6 = +2 / +15 μm
  Φ30 g6 = -20 / -7 μm    Φ30 s6 = +35 / +48 μm
"""
from __future__ import annotations

from svgkit import INK, PALETTE, Figure, arc_pts, fig_title

MUTED = PALETTE["muted"]
BLUE = PALETTE["blue"]
RED = PALETTE["red"]
GREEN = PALETTE["green"]
ORANGE = PALETTE["orange"]
AMBER = PALETTE["amber"]
TEAL = PALETTE["teal"]
VIOLET = PALETTE["violet"]


# ---------------------------------------------------------------------------
# 10. 公差带图（Φ30 H7/k6）
# ---------------------------------------------------------------------------
def fig_gongcha_dai() -> Figure:
    F = Figure(
        "FIG-GONGCHA-DAI",
        1000,
        660,
        "公差带图：Φ30 H7/k6",
        "零线、孔 H7 公差带（0～+21 μm）、轴 k6 公差带（+2～+15 μm），标出 ES/EI/es/ei "
        "与最大间隙、最大过盈。",
    )
    fig_title(
        F,
        "图 10  公差带图（Φ30 H7/k6，单位 μm）",
        "孔 H7：EI = 0、ES = +0.021；轴 k6：ei = +0.002、es = +0.015 —— 数值取自 GB/T 1800.1。",
    )

    ZERO = 430
    K = 6.0  # px / μm

    def Y(v: float) -> float:
        return ZERO - K * v

    # 零线 + 偏差轴
    F.line(112, ZERO, 900, ZERO, cls="axis")
    F.line(112, 500, 112, 286, cls="thin")
    for v in (0, 10, 20):
        F.line(106, Y(v), 118, Y(v), cls="thin")
        F.text(100, Y(v) + 4, "0" if v == 0 else f"+{v}", size=11, anchor="end")
    F.text(112, 276, "偏差 / μm", size=11, anchor="middle")
    F.text(906, ZERO + 4, "零线 0", size=11, anchor="start")

    # 孔 H7 公差带：0 ～ +21
    F.rect(210, Y(21), 160, Y(0) - Y(21), cls="thick", fill=BLUE, color=BLUE, extra='fill-opacity="0.14"')
    # 轴 k6 公差带：+2 ～ +15
    F.rect(430, Y(15), 160, Y(2) - Y(15), cls="thick", fill=ORANGE, color=ORANGE, extra='fill-opacity="0.14"')

    F.text(210, Y(21) - 8, "ES = +0.021", size=11, anchor="start", color=BLUE)
    F.text(210, Y(0) + 18, "EI = 0", size=11, anchor="start", color=BLUE)
    F.text(440, Y(15) + 18, "es = +0.015", size=11, anchor="start", color=ORANGE)
    F.text(440, Y(2) - 8, "ei = +0.002", size=11, anchor="start", color=ORANGE)
    F.text(290, 472, "孔 Φ30 H7", size=12, weight="600", color=BLUE)
    F.text(510, 472, "轴 Φ30 k6", size=12, weight="600", color=ORANGE)

    # 最大间隙 Xmax = ES - ei = 21 - 2 = 19
    F.line(370, Y(21), 650, Y(21), cls="dash", color=TEAL)
    F.line(590, Y(2), 650, Y(2), cls="dash", color=TEAL)
    F.line_arrow(650, Y(21), 650, Y(2), color=TEAL)
    F.text(662, 356, "Xmax", size=11, anchor="start", color=TEAL, weight="600")
    F.text(662, 374, "= +19 μm", size=11, anchor="start", color=TEAL)

    # 最大过盈 Ymax = es - EI = 15 - 0 = 15
    F.line(590, Y(15), 790, Y(15), cls="dash", color=VIOLET)
    F.line_arrow(790, Y(15), 790, Y(0), color=VIOLET)
    F.text(802, 356, "Ymax", size=11, anchor="start", color=VIOLET, weight="600")
    F.text(802, 374, "= 15 μm", size=11, anchor="start", color=VIOLET)

    F.text(210, 512, "孔公差带完全在零线上方（基孔制 H：EI = 0）", size=11, anchor="start", color=BLUE)
    F.text(210, 534, "轴 k6 的公差带（+2～+15）也全部在零线上方 → 过渡配合", size=11, anchor="start", color=ORANGE)

    notes = [
        "① 零线是基本尺寸对应的偏差为零的直线；零线以上为正偏差，以下为负偏差，单位一律 μm。",
        "② ES / EI 是孔的上、下偏差；es / ei 是轴的上、下偏差（大写对孔、小写对轴）。",
        "③ 配合性质看两带的位置关系：孔带全在轴带之上为间隙配合；两带有重叠为过渡配合；孔带全在轴带之下为过盈配合。",
        "④ 本例 Xmax = ES − ei = +19 μm（最大间隙），Ymax = es − EI = +15 μm（最大过盈）→ 过渡配合。",
        "⑤ 注意：k6 的 ei = +2 μm，轴公差带整体在零线上方，它并不跨零线；真正跨零线的是 js / j / J 这类对称偏差代号。",
    ]
    F.lines(40, 560, notes, size=11, lh=20)
    return F


# ---------------------------------------------------------------------------
# 11. 圆弧连接步骤图（R10 连接两条互相垂直的直线）
# ---------------------------------------------------------------------------
def fig_yuanhu_lianjie() -> Figure:
    F = Figure(
        "FIG-YUANHU-LIANJIE",
        1000,
        640,
        "圆弧连接步骤：R10 连接两条互相垂直的直线",
        "三个分步：① 以 R 为距离作两条平行线求圆心；② 过圆心作垂线求切点；③ 以圆心和半径画连接弧。",
    )
    fig_title(
        F,
        "图 11  圆弧连接的作图步骤（R10 连接两垂直直线，k = 3 px/mm）",
        "已知两条互相垂直的直线，用 R10 的圆弧光滑连接 —— 关键在于“先求圆心、再求切点、后画弧”。",
    )

    R = 30.0  # R10 × 3 px/mm
    CY = 250.0

    def panel(cx: float, label: str) -> None:
        F.text(cx, 186, label, size=13, weight="600")

    def corner(cx: float) -> None:
        """两条互相垂直的已知直线（粗实线）。"""
        F.path(f"M{cx - 140},{CY} L{cx},{CY} L{cx},{CY + 140}", cls="thick")

    # ---------- ① 求圆心 ----------
    cx1 = 190
    panel(cx1, "① 求圆心")
    corner(cx1)
    ox, oy = cx1 - R, CY + R
    F.line(cx1 - 150, CY + R, ox, CY + R, cls="dash", color=MUTED)  # 距水平线 R 的平行线
    F.line(ox, CY + R, ox, CY + 150, cls="dash", color=MUTED)  # 距竖直线 R 的平行线
    F.dot(ox, oy)
    F.text(ox - 10, oy + 16, "O", size=12, weight="600", anchor="end")
    F.line_arrow(ox - 52, CY + R, ox - 52, CY, color=BLUE, both=True)  # R 标注（两条平行线之间）
    F.text(ox - 60, CY + R / 2 + 4, "R10", size=11, anchor="end", color=BLUE)

    # ---------- ② 求切点 ----------
    cx2 = 500
    panel(cx2, "② 求切点")
    corner(cx2)
    ox2, oy2 = cx2 - R, CY + R
    F.line(ox2, oy2, ox2, CY, cls="thin", color=BLUE)  # 垂线 → 切点 T1
    F.line(ox2, oy2, cx2, oy2, cls="thin", color=BLUE)  # 垂线 → 切点 T2
    F.dot(ox2, oy2)
    F.dot(ox2, CY)
    F.dot(cx2, oy2)
    F.text(ox2 - 8, oy2 + 16, "O", size=12, weight="600", anchor="end")
    F.text(ox2 - 8, CY - 8, "T1", size=12, weight="600", anchor="end", color=BLUE)
    F.text(cx2 + 8, oy2 + 14, "T2", size=12, weight="600", anchor="start", color=BLUE)
    F.path(f"M{ox2},{CY + 9} L{ox2 + 9},{CY + 9} L{ox2 + 9},{CY}", cls="thin", color=MUTED)  # 直角标记
    F.path(f"M{cx2 - 9},{oy2} L{cx2 - 9},{oy2 - 9} L{cx2},{oy2 - 9}", cls="thin", color=MUTED)

    # ---------- ③ 画弧 ----------
    cx3 = 810
    panel(cx3, "③ 画弧")
    ox3, oy3 = cx3 - R, CY + R
    F.line(cx3 - 140, CY, ox3, CY, cls="thick")  # 水平线只画到切点 T1
    F.line(cx3, oy3, cx3, CY + 140, cls="thick")  # 竖直线从切点 T2 画到底
    F.dot(ox3, oy3)
    F.arc(ox3, oy3, R, -90, 0, cls="thick", n=32)  # T1 → T2 的连接弧
    F.text(ox3 - 8, oy3 + 16, "O", size=12, weight="600", anchor="end")
    F.tick(ox3, CY)
    F.tick(cx3, oy3)

    notes = [
        "① 求圆心：分别以 R（=10 mm）为距离，作两条已知直线的平行线，两平行线的交点 O 就是连接弧的圆心。",
        "② 求切点：过 O 分别向两条已知直线作垂线，垂足 T1、T2 就是连接点（切点）—— 不先求切点，弧与直线接不上。",
        "③ 画弧：以 O 为圆心、R 为半径，在两个切点之间画弧（粗实线），再把多余的作图线擦掉。",
        "④ 光滑连接的条件：连接弧与直线相切于切点，切点必须是“由圆心作垂线的垂足”，凭目测接弧是常见错误。",
    ]
    F.lines(40, 480, notes, size=11, lh=24)
    return F


# ---------------------------------------------------------------------------
# 12. 螺纹比例画法（外螺纹 / 内螺纹剖视）
# ---------------------------------------------------------------------------
def fig_luowen() -> Figure:
    F = Figure(
        "FIG-LUOWEN",
        1020,
        640,
        "螺纹的比例画法：外螺纹与内螺纹（剖视）对照",
        "外螺纹牙顶 d 画粗实线、牙底 d₁=0.85d 画细实线，端视图牙底圆画约 3/4 圈；"
        "内螺纹剖视牙顶 D₁ 画粗实线、牙底 D 画细实线；螺纹终止线用粗实线。",
    )
    fig_title(
        F,
        "图 12  螺纹的比例画法（外螺纹 / 内螺纹剖视，M40，d₁ = 0.85d）",
        "螺纹不按真实牙型画，只按比例画牙顶、牙底两条线 —— 这样画才能一眼区分内外螺纹。",
    )

    # ================= 左：外螺纹 =================
    AY = 210.0  # 轴线
    R_D, R_D1 = 44.0, 37.4  # d/2、d1/2（k = 2.2 px/mm）
    F.text(230, 96, "外螺纹", size=13, weight="600")
    F.line(76, AY, 470, AY, cls="center", color=MUTED)  # 轴线
    F.line(90, AY - R_D, 90, AY + R_D, cls="thick")  # 杆端面
    F.line(90, AY - R_D, 415, AY - R_D, cls="thick")  # 牙顶（大径）
    F.line(90, AY + R_D, 415, AY + R_D, cls="thick")
    F.line(415, AY - R_D, 430, AY - R_D + 15, cls="thick")  # 倒角
    F.line(415, AY + R_D, 430, AY + R_D - 15, cls="thick")
    F.line(430, AY - R_D + 15, 430, AY + R_D - 15, cls="thick")  # 端面
    F.line(170, AY - R_D1, 370, AY - R_D1, cls="thin")  # 牙底（小径）—— 细实线
    F.line(170, AY + R_D1, 370, AY + R_D1, cls="thin")
    F.line(370, AY - R_D, 370, AY + R_D, cls="thick")  # 螺纹终止线

    # d、d1 用尺寸线标出（细实线在粗实线内侧，引线会穿线，故用尺寸）
    F.dim_v(44, AY - R_D, AY + R_D, "d", ext_from=(90, 90))
    F.dim_v(70, AY - R_D1, AY + R_D1, "d₁", ext_from=(90, 90))

    # 端视图
    F.circle(560, AY, R_D, cls="thick")
    F.arc(560, AY, R_D1, 20, 290, cls="thin", n=48)  # 约 3/4 圈
    F.line(506, AY, 614, AY, cls="center", color=MUTED)
    F.line(560, AY - 52, 560, AY + 52, cls="center", color=MUTED)
    F.text(560, 300, "端视图：外圈粗实线 = d，内圈细实线 ≈ 3/4 圈 = d₁", size=11)

    # ================= 右：内螺纹剖视 =================
    BX = 800.0
    D, D1 = 88.0, 74.8
    F.text(BX, 96, "内螺纹（剖视）", size=13, weight="600")
    F.rect(BX - 88, 122, 176, 176, cls="thick")  # 外轮廓
    F.line(BX, 100, BX, 320, cls="center", color=MUTED)
    # 牙底 D：细实线（在实体一侧）
    F.line(BX - D / 2, 122, BX - D / 2, 298, cls="thin")
    F.line(BX + D / 2, 122, BX + D / 2, 298, cls="thin")
    # 牙顶 D1：粗实线（空腔边界，剖面线画到这里为止）
    F.line(BX - D1 / 2, 122, BX - D1 / 2, 298, cls="thick")
    F.line(BX + D1 / 2, 122, BX + D1 / 2, 298, cls="thick")
    # 剖面线：只画在实体上（牙顶粗实线以外）
    F.hatch_rect(BX - 88, 122, 88 - D1 / 2, 176)
    F.hatch_rect(BX + D1 / 2, 122, 88 - D1 / 2, 176)

    # 引注（外螺纹）
    F.leader(368, 256, 412, 340, "螺纹终止线（粗实线）", color=MUTED, anchor="start")

    # 引注（内螺纹）
    F.leader(BX - D1 / 2, 126, BX - 106, 116, "D₁：牙顶（粗实线）", color=RED, anchor="end")
    F.leader(BX + D / 2, 126, BX + 96, 116, "D：牙底（细实线）", color=BLUE, anchor="start")

    notes = [
        "① 外螺纹：牙顶（大径 d）画粗实线；牙底（小径 d₁ ≈ 0.85d）画细实线；端视图中牙底圆画约 3/4 圈细实线。",
        "② 内螺纹（剖视）：牙顶（小径 D₁）画粗实线，牙底（大径 D）画细实线；剖面线画到牙顶粗实线为止，空腔不画。",
        "③ 螺纹终止线用粗实线：外螺纹画在螺纹段结束处、从牙顶画到牙顶；不通孔内螺纹的终止线画到牙顶。",
        "④ 螺纹一律按比例画（d₁ ≈ 0.85d），不画真实牙型；45° 倒角在端视图上画成一个圆。",
        "⑤ 内螺纹不剖（外形视图）时：小径 D₁ 画粗实线、大径 D 画细实线（约 3/4 圈）；只有剖开后才按上面规则画实体一侧。",
    ]
    F.lines(40, 392, notes, size=11, lh=23)
    return F


# ---------------------------------------------------------------------------
# 13. 表面结构代号
# ---------------------------------------------------------------------------
def fig_biaomian() -> Figure:
    F = Figure(
        "FIG-BIAOMIAN",
        1000,
        660,
        "表面结构（Ra）代号与常用加工方法对照",
        "表面结构符号由基本符号、去材料/不去材料标记和 Ra 数值组成；右侧列出 Ra 0.4～12.5 的常用加工方法。",
    )
    fig_title(
        F,
        "图 13  表面结构代号（Ra）的组成与常用加工方法",
        "符号由两条与水平线成 60° 的细实线组成；数值写在横线上方，单位 μm 省略不写。",
    )

    def symbol(bx: float, by: float, kind: str = "basic", value: str = "") -> None:
        """在顶点 (bx,by) 处画表面结构符号。kind: basic / remove / no_remove"""
        F.line(bx, by, bx - 8, by - 13.86, cls="thin")  # 短边
        F.line(bx, by, bx + 16, by - 27.71, cls="thin")  # 长边
        if kind == "remove":
            F.line(bx - 8, by - 13.86, bx + 24, by - 13.86, cls="thin")
        elif kind == "no_remove":
            F.circle(bx, by - 10, 5, cls="thin")
        if value:
            F.text(bx + 8, by - 20, value, size=12, anchor="middle", weight="600")

    # 三种符号
    symbol(140, 250)
    F.text(200, 236, "基本符号", size=12, anchor="start", weight="600")
    F.text(200, 254, "两条与水平线成 60° 的细实线", size=11, anchor="start", color=MUTED)

    symbol(140, 400, "remove", "Ra 3.2")
    F.text(200, 386, "用去除材料方法获得的表面", size=12, anchor="start", weight="600")
    F.text(200, 404, "基本符号 + 短横线；Ra 数值写在横线上方", size=11, anchor="start", color=MUTED)

    symbol(140, 550, "no_remove")
    F.text(200, 536, "用不去除材料方法获得的表面", size=12, anchor="start", weight="600")
    F.text(200, 554, "基本符号 + 小圆；用于铸、锻等毛坯表面", size=11, anchor="start", color=MUTED)

    F.text(40, 614, "去掉材料（车、铣、磨）标注前两种符号；铸锻件毛坯、不加工表面用带小圆的符号。", size=11,
           anchor="start", color=MUTED)

    # 表格
    F.text(505, 118, "Ra / μm", size=11, anchor="start", weight="600")
    F.text(575, 118, "常用加工方法", size=11, anchor="start", weight="600")
    F.text(790, 118, "表面特征", size=11, anchor="start", weight="600")
    F.line(500, 128, 970, 128, cls="thin")
    rows = [
        ("0.4", "研磨、超精加工、精磨", "镜面，极光滑"),
        ("0.8", "精磨、精铰、金刚石车削", "很光滑"),
        ("1.6", "精车、精铣、精铰、磨削", "光滑，配合面常用"),
        ("3.2", "半精车、半精铣、精车", "较光滑，一般配合面"),
        ("6.3", "车、铣、钻、铰", "中等，非配合面"),
        ("12.5", "粗车、粗铣、钻孔", "粗糙，粗加工或非加工面"),
    ]
    for i, (ra, method, feat) in enumerate(rows):
        y = 158 + i * 40
        F.text(505, y, ra, size=12, anchor="start", weight="600")
        F.text(575, y, method, size=11, anchor="start")
        F.text(790, y, feat, size=11, anchor="start", color=MUTED)
    F.line(500, 402, 970, 402, cls="thin")

    F.text(500, 430, "Ra 越小表面越光滑；数值按优先数系（0.012～100）选取。", size=11, anchor="start")
    F.text(500, 452, "同一表面只注一次；无法加工的表面用带小圆的符号。", size=11, anchor="start", color=MUTED)
    return F


# ---------------------------------------------------------------------------
# 14. 尺寸注法四要素（正确 / 错误对照）
# ---------------------------------------------------------------------------
def fig_chicun_siyaosu() -> Figure:
    F = Figure(
        "FIG-CHICUN-SIYAOSU",
        1000,
        620,
        "尺寸注法四要素：尺寸界线、尺寸线、箭头、尺寸数字",
        "左侧为正确注法并用①②③④指出四要素，右侧列出两种常见错误注法。",
    )
    fig_title(
        F,
        "图 14  尺寸注法的四要素（正确注法 / 错误注法对照）",
        "尺寸界线、尺寸线用细实线；箭头画在尺寸线两端；尺寸数字写在尺寸线上方（水平尺寸字头朝上，垂直尺寸字头朝左）。",
    )

    def mark(x: float, y: float, s: str) -> None:
        F.circle(x, y, 9, cls="thin", color=TEAL)
        F.text(x, y + 4, s, size=11, anchor="middle", color=TEAL)

    # ---------- 正确 ----------
    F.text(90, 158, "正确注法", size=13, anchor="start", weight="600")
    F.rect(90, 200, 240, 100, cls="thick")
    F.dim_h(90, 330, 356, "40", ext_from=(300, 300))
    F.dim_v(400, 200, 300, "20", ext_from=(330, 330), left=False)

    mark(72, 330, "①")  # 尺寸界线
    mark(250, 380, "②")  # 尺寸线
    mark(348, 350, "③")  # 箭头
    mark(186, 336, "④")  # 尺寸数字

    # ---------- 错误 ----------
    F.text(600, 158, "错误注法（✗）", size=13, anchor="start", weight="600")
    F.rect(600, 200, 240, 100)
    # 错 1：尺寸数字被尺寸线穿过
    F.line_arrow(600, 344, 840, 344, color=INK)
    F.text(720, 348, "40", size=12)
    F.text(852, 340, "✗", size=15, anchor="start", color=RED, weight="600")
    F.text(600, 392, "✗ 尺寸数字被尺寸线穿过 —— 数字处应断开或写在线上方", size=11, anchor="start", color=RED)
    # 错 2：尺寸线画成粗实线
    F.dim_v(880, 200, 300, "20", ext_from=(840, 840), left=False, cls="thick")
    F.text(896, 244, "✗", size=15, anchor="start", color=RED, weight="600")
    F.text(600, 418, "✗ 尺寸线画成粗实线 —— 尺寸线、尺寸界线都用细实线", size=11, anchor="start", color=RED)

    legend = [
        "① 尺寸界线：由轮廓线、轴线或对称中心线引出，末端超出尺寸线 2～5 mm，用细实线。",
        "② 尺寸线：细实线，与被注线段平行，不能用轮廓线、轴线或对称中心线代替。",
        "③ 箭头：画在尺寸线两端，箭尖接触尺寸界线；位置不够时可画在外侧并用引线引出。",
        "④ 尺寸数字：写在尺寸线上方居中；水平尺寸字头朝上，垂直尺寸字头朝左，倾斜尺寸按斜线方向注写。",
    ]
    F.lines(40, 470, legend, size=11, lh=24)

    F.text(
        40,
        588,
        "口诀：界线细、线平行、箭头顶住界线、数字在上不被穿 —— 四条做到，尺寸就合规。",
        size=11,
        anchor="start",
    )
    return F


# ---------------------------------------------------------------------------
# 15. 三种配合的公差带对照
# ---------------------------------------------------------------------------
def fig_gongcha_peijian() -> Figure:
    F = Figure(
        "FIG-GONGCHA-PEIJIAN",
        1040,
        620,
        "三种配合的公差带对照：间隙、过渡、过盈",
        "同一基本尺寸 Φ30 下，H7/g6 为间隙配合、H7/k6 为过渡配合、H7/s6 为过盈配合；"
        "通过孔带与轴带的相对位置判断配合性质。",
    )
    fig_title(
        F,
        "图 15  三种配合的公差带对照（Φ30，单位 μm）",
        "孔 H7 = 0～+21；轴 g6 = −20～−7、k6 = +2～+15、s6 = +35～+48（GB/T 1800.1）。",
    )

    ZERO = 430.0
    K = 4.6  # px / μm

    def Y(v: float) -> float:
        return ZERO - K * v

    panels = [
        (40, "间隙配合 H7/g6", (0, 21), (-20, -7), "Xmax = +41，Xmin = +7", GREEN),
        (372, "过渡配合 H7/k6", (0, 21), (2, 15), "Xmax = +19，Ymax = 15", AMBER),
        (704, "过盈配合 H7/s6", (0, 21), (35, 48), "Ymax = 48，Ymin = 14", RED),
    ]
    for x0, name, hole, shaft, note, accent in panels:
        F.line(x0 + 20, ZERO, x0 + 310, ZERO, cls="axis")
        F.text(x0 + 300, ZERO + 16, "0", size=11, anchor="end", color=MUTED)
        # 孔带
        F.rect(x0 + 50, Y(hole[1]), 90, Y(hole[0]) - Y(hole[1]), cls="thick", fill=BLUE, color=BLUE,
               extra='fill-opacity="0.14"')
        # 轴带
        F.rect(x0 + 170, Y(shaft[1]), 90, Y(shaft[0]) - Y(shaft[1]), cls="thick", fill=ORANGE, color=ORANGE,
               extra='fill-opacity="0.14"')
        F.text(x0 + 95, Y(hole[1]) - 8, "孔 H7", size=11, color=BLUE)
        F.text(x0 + 215, Y(shaft[1]) - 8, f"轴 {name.split('/')[1][:2]}", size=11, color=ORANGE)
        F.text(x0 + 165, 96, name, size=13, weight="600", color=accent)
        F.text(x0 + 165, 120, note, size=11, color=accent)

    # 零线贯通 + 纵轴（纵轴放在最左，刻度数字留出边距，避免被裁掉）
    F.line(44, ZERO, 340, ZERO, cls="thin")
    F.line(44, 520, 44, 180, cls="thin")
    F.text(54, 176, "偏差 / μm（零线 = 0）", size=11, anchor="start")
    for v in (0, 20, 40):
        F.line(38, Y(v), 50, Y(v), cls="thin")
        F.text(34, Y(v) + 4, "0" if v == 0 else f"+{v}", size=11, anchor="end")

    notes = [
        "① 判断口诀：孔带（上）在轴带（下）之上 → 间隙；两带有重叠 → 过渡；孔带在轴带之下 → 过盈。",
        "② 间隙配合 Xmax = ES − ei、Xmin = EI − es；过盈配合 Ymax = es − EI、Ymin = ei − ES。",
        "③ 同一基本尺寸的孔、轴公差带画在同一条零线上，比高度、看位置就能一眼定配合类型。",
    ]
    F.lines(40, 548, notes, size=11, lh=22)
    return F


ALL = [
    fig_gongcha_dai,
    fig_yuanhu_lianjie,
    fig_luowen,
    fig_biaomian,
    fig_chicun_siyaosu,
    fig_gongcha_peijian,
]
