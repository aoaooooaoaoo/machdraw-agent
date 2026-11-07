"""图 1–4：图线线型、三视图形成、组合体三视图、六个基本视图。

几何约定：比例 k = 2 px/mm；第一角投影。
长对正 —— 主、俯视图同 x 范围；高平齐 —— 主、左视图同 y 范围；宽相等 —— 俯视图的高 = 左视图的宽。
"""
from __future__ import annotations

from svgkit import INK, PALETTE, Figure, fig_title

MUTED = PALETTE["muted"]
BLUE = PALETTE["blue"]
RED = PALETTE["red"]
GREEN = PALETTE["green"]


# ---------------------------------------------------------------------------
# 1. 图线线型对照表
# ---------------------------------------------------------------------------
def fig_linetype() -> Figure:
    F = Figure(
        "FIG-LINETYPE",
        1000,
        600,
        "图线线型对照表：六种图线的线型、线宽与用途",
        "粗实线、细实线、虚线、细点画线、波浪线、双点画线画在同一张图上对照；"
        "线宽以粗实线 d 为基准，细线为 d/2。",
    )
    fig_title(
        F,
        "图 1  图线线型对照表（GB/T 17450、GB/T 4457.4）",
        "线宽关系：粗线 = d，细线 = d/2；本图取 d = 2 px（A3 图纸实际 d ≈ 0.7 mm）。",
    )

    hdr_y = 82
    for x, s in ((40, "线型（样本）"), (320, "线宽"), (400, "名称"), (520, "用途 —— 画什么线")):
        F.text(x, hdr_y, s, size=11, anchor="start", color=MUTED)

    rows = [
        (118, "thick", "粗 d", "粗实线", "可见轮廓线、可见过渡线；螺纹牙顶圆"),
        (182, "thin", "细 d/2", "细实线", "尺寸线、尺寸界线、剖面线、螺纹牙底圆、引出线"),
        (246, "dash", "细 d/2", "虚线", "不可见轮廓线、不可见过渡线（尽量少用，能用剖视就不用虚线）"),
        (310, "center", "细 d/2", "细点画线", "轴线、对称中心线、圆的中心线"),
        (374, "wave", "细 d/2", "波浪线", "断裂边界线、局部剖视图的分界线"),
        (438, "dbl", "细 d/2", "双点画线", "相邻辅助零件的轮廓、可动零件的极限位置、中断线"),
    ]
    for y, cls, width, name, use in rows:
        if cls == "wave":
            F.wave(40, 290, lambda _x, _y=y: _y, amp=3.6, period=16)
        else:
            F.line(40, y, 290, y, cls=cls)
        F.text(320, y + 4, width, size=12, anchor="start")
        F.text(400, y + 4, name, size=12, anchor="start", weight="600")
        F.text(520, y + 4, use, size=11, anchor="start")

    F.line(40, 468, 960, 468, cls="thin")

    notes = [
        "① 同一图样中同类图线的宽度应一致；虚线、点画线的线段长度与间隔应大致相等。",
        "② 点画线的首末两端应画成线段而不是点，并超出轮廓线 2～5 mm（图上约 4 px）。",
        "③ 虚线、点画线与实线重合时按实线画；虚线在实线的延长线上时应留出空隙。",
        "④ 波浪线、双折线都表示断裂边界：手绘用波浪线、CAD 用双折线；波浪线不得与轮廓线重合。",
    ]
    F.lines(40, 498, notes, size=11, lh=23)
    return F


# ---------------------------------------------------------------------------
# 2. 三视图形成（第一角）+ 三等规律
# ---------------------------------------------------------------------------
def fig_sanshitu_base() -> Figure:
    F = Figure(
        "FIG-SANSHITU-BASE",
        1000,
        700,
        "三视图的形成与三等规律",
        "L 形块按第一角投影得到主视图、俯视图、左视图；蓝色虚线示长对正，红色虚线示高平齐，"
        "绿色虚线加 45° 辅助线示宽相等。",
    )
    fig_title(
        F,
        "图 2  三视图的形成（第一角投影）与三等规律",
        "形体：L 形块 100×60×70（长×宽×高，mm）；投影比例 k = 2 px/mm。",
    )

    # 主视图：L 形（x 0..100 → 120..320；z 35..70 → 150..220）
    F.path("M120,290 L320,290 L320,220 L230,220 L230,150 L120,150 Z", cls="thick")
    F.text(220, 136, "主视图", size=12, weight="600")

    # 俯视图：100×60 → 200×120，长对正（x 一致）
    F.rect(120, 340, 200, 120, cls="thick")
    F.line(230, 340, 230, 460, cls="thick")
    F.text(220, 486, "俯视图", size=12, weight="600")

    # 左视图：60×70 → 120×140，高平齐（y 一致）；台阶面不可见 → 虚线
    F.rect(400, 150, 120, 140, cls="thick")
    F.line(400, 220, 520, 220, cls="dash")
    F.text(460, 136, "左视图", size=12, weight="600")

    # 长对正（蓝）：主视图底 → 俯视图顶
    for x in (120, 230, 320):
        F.line(x, 290, x, 340, cls="dash", color=BLUE)
    # 高平齐（红）：主视图右 → 左视图左
    for y in (150, 220, 290):
        F.line(320, y, 400, y, cls="dash", color=RED)
    # 宽相等（绿）：俯视图右缘 → 45° 辅助线 → 左视图
    F.path("M320,460 L520,460 L520,290", cls="dash", color=GREEN)
    F.path("M320,340 L400,340", cls="dash", color=GREEN)
    F.path("M400,340 L520,460", cls="dash", color=GREEN)

    # 图例
    lg = [
        (BLUE, "长对正：主视图与俯视图的 X 方向尺寸相同"),
        (RED, "高平齐：主视图与左视图的 Z 方向尺寸相同"),
        (GREEN, "宽相等：俯视图的高 = 左视图的宽（Y 方向相同）"),
    ]
    for i, (color, s) in enumerate(lg):
        y = 560 + i * 26
        F.line(390, y, 424, y, cls="dash", color=color)
        F.text(436, y + 4, s, size=11, anchor="start", color=color)

    # 尺寸
    F.dim_h(120, 320, 320, "100", ext_from=(290, 290))
    F.dim_v(96, 150, 290, "70", ext_from=(120, 120))
    F.dim_h(120, 230, 112, "55", ext_from=(150, 150))
    F.dim_v(345, 220, 290, "35", ext_from=(320, 320), left=False)
    F.dim_h(400, 520, 520, "60", ext_from=(290, 290))

    F.text(120, 640, "三等规律：长对正、高平齐、宽相等", size=13, anchor="start", weight="600")
    F.text(
        120,
        664,
        "第一角布置：主视图在左上，俯视图在其正下方，左视图在其正右方 —— 三个视图之间必然满足上述三条。",
        size=11,
        anchor="start",
        color=MUTED,
    )
    return F


# ---------------------------------------------------------------------------
# 3. 组合体三视图示例（台阶 + 通孔 + 尺寸基准）
# ---------------------------------------------------------------------------
def fig_sanshitu_example() -> Figure:
    F = Figure(
        "FIG-SANSHITU-EXAMPLE",
        1000,
        700,
        "组合体三视图示例：台阶与通孔",
        "带台阶和竖直通孔的底板，按第一角画出三视图，标出高度、长度、宽度三个尺寸基准，"
        "并注明长对正、高平齐、宽相等的对应关系。",
    )
    fig_title(
        F,
        "图 3  组合体三视图示例（台阶 + 通孔 + 尺寸基准）",
        "底板 90×50×20，左端台阶 40×50×25，Ø16 竖直通孔 —— 单位 mm，k = 2 px/mm。",
    )

    # 主视图：L 形轮廓（台阶在左）
    F.path("M80,210 L260,210 L260,170 L160,170 L160,120 L80,120 Z", cls="thick")
    # 通孔不可见 → 虚线（Ø16 → ±16 px）
    F.line(194, 170, 194, 210, cls="dash")
    F.line(226, 170, 226, 210, cls="dash")
    F.text(200, 106, "主视图", size=12, weight="600")

    # 俯视图
    F.rect(80, 260, 180, 100, cls="thick")
    F.line(160, 260, 160, 360, cls="thick")  # 台阶面（可见）
    F.circle(210, 310, 16, cls="thick")  # 通孔（俯视图可见）
    F.line(60, 310, 440, 310, cls="center", color=MUTED)  # 宽度方向对称中心线
    F.text(170, 386, "俯视图", size=12, weight="600")

    # 左视图
    F.rect(330, 120, 100, 90, cls="thick")
    F.line(330, 170, 430, 170, cls="dash")  # 底板顶面被台阶挡住
    F.line(364, 170, 364, 210, cls="dash")  # 通孔
    F.line(396, 170, 396, 210, cls="dash")
    F.text(380, 108, "左视图", size=12, weight="600")

    # 三等关系辅助线（与图 2 同一套颜色约定）
    for x in (80, 160, 260):
        F.line(x, 210, x, 260, cls="dash", color=BLUE, extra='stroke-opacity="0.75"')
    for y in (120, 170, 210):
        F.line(260, y, 330, y, cls="dash", color=RED, extra='stroke-opacity="0.75"')

    # 尺寸基准（文字放在图外空白处，引线指向基准面/中心面）
    F.text(40, 234, "高度基准", size=11, anchor="start", color=PALETTE["violet"], weight="600")
    F.text(40, 249, "（底面）", size=11, anchor="start", color=PALETTE["violet"])
    F.leader(140, 212, 96, 240, color=PALETTE["violet"])
    F.text(22, 322, "长度基准", size=11, anchor="start", color=PALETTE["violet"], weight="600")
    F.text(22, 337, "（左端面）", size=11, anchor="start", color=PALETTE["violet"])
    F.leader(82, 300, 74, 330, color=PALETTE["violet"])
    F.leader(440, 310, 470, 288, "宽度基准（对称中心面）", color=PALETTE["violet"], anchor="start")

    # 尺寸
    F.dim_h(80, 260, 424, "90", ext_from=(360, 360))
    F.dim_v(285, 260, 360, "50", ext_from=(260, 260), left=False)
    F.dim_v(58, 120, 210, "45", ext_from=(80, 80), left=True)
    F.dim_v(276, 170, 210, "20", left=False)
    F.dim_h(80, 160, 96, "40", ext_from=(120, 120), above=True)
    F.leader(232, 318, 300, 404, "Ø16 通孔", anchor="start")

    F.text(
        40,
        660,
        "读图顺序：先找形状特征视图（这里俯视图最清楚），再按长对正/高平齐/宽相等补出另两个视图；"
        "三个方向的尺寸基准各选一个面或中心面，同一方向的尺寸都从该基准出发。",
        size=11,
        anchor="start",
        color=MUTED,
    )
    return F


# ---------------------------------------------------------------------------
# 4. 六个基本视图
# ---------------------------------------------------------------------------
def fig_liugeshitu() -> Figure:
    F = Figure(
        "FIG-LIUGESHITU",
        1000,
        620,
        "六个基本视图的配置（第一角）",
        "第一角画法下六个基本视图的展开位置：仰视图在主视图上方，俯视图在下方，右视图在左方，"
        "左视图在右方，后视图在左视图右方。",
    )
    fig_title(
        F,
        "图 4  六个基本视图的配置（第一角画法）",
        "形体 80×40×50（长×宽×高），中间 Ø20 通孔；k = 2 px/mm。",
    )

    # 主视图（含可见圆孔）
    F.rect(300, 180, 160, 100, cls="thick")
    F.circle(380, 230, 20, cls="thick")
    F.text(380, 172, "主视图", size=12, weight="600")

    # 俯视图（在主视图下方），孔不可见
    F.rect(300, 300, 160, 80, cls="thick")
    F.line(360, 300, 360, 380, cls="dash")
    F.line(400, 300, 400, 380, cls="dash")
    F.text(380, 400, "俯视图", size=12, weight="600")

    # 仰视图（在主视图上方）
    F.rect(300, 70, 160, 80, cls="thick")
    F.line(360, 70, 360, 150, cls="dash")
    F.line(400, 70, 400, 150, cls="dash")
    F.text(290, 115, "仰视图", size=12, weight="600", anchor="end")

    # 左视图（在主视图右方）、右视图（在左方）
    F.rect(480, 180, 80, 100, cls="thick")
    F.line(480, 220, 560, 220, cls="dash")
    F.line(480, 240, 560, 240, cls="dash")
    F.text(520, 172, "左视图", size=12, weight="600")

    F.rect(180, 180, 80, 100, cls="thick")
    F.line(180, 220, 260, 220, cls="dash")
    F.line(180, 240, 260, 240, cls="dash")
    F.text(220, 172, "右视图", size=12, weight="600")

    # 后视图（在左视图右方）
    F.rect(580, 180, 160, 100, cls="thick")
    F.circle(660, 230, 20, cls="thick")
    F.text(660, 172, "后视图", size=12, weight="600")

    # 视图名称 + 关系说明
    notes = [
        "长对正：主、俯、仰三个视图左右对齐（同一 X 范围）。",
        "高平齐：主、左、右、后四个视图上下齐平（同一 Z 范围）。",
        "宽相等：俯、仰、左、右四个视图的宽都是同一 Y 范围；画图时常用 45° 辅助线把宽从俯视图搬到左视图。",
    ]
    F.lines(40, 470, notes, size=11, lh=24)
    F.text(
        40,
        560,
        "记忆口诀：绕主视图“上下左右”依次是仰、俯、右、左；后视图放在左视图的右边。"
        "六个基本视图一律不画虚线以外的多余线，也不标注“视图名称”以外的字样（本图为教学加注）。",
        size=11,
        anchor="start",
        color=MUTED,
    )
    return F


ALL = [fig_linetype, fig_sanshitu_base, fig_sanshitu_example, fig_liugeshitu]
