"""pairs_defs —— 10 组辨析对比图的几何与结构化数据。

每组一个 builder，返回 (PairFigure, 结构化记录)。局部坐标约定：
  * 单个图形区 = 380×420 的局部坐标系，A 区 ox=0、B 区 ox=380（pairkit 自动平移）；
  * 图形区纵向可用范围 y∈[76, 288]，小标题在 307，图例在 340/360/380/400；
  * 同一编号 ①②③ 在 A、B 两个图形区含义完全一致，位置尽量取相同局部坐标，
    这样左右对照时眼睛不用来回找。

几何自检要点（写代码时逐条守住）：
  * 半剖必须以细点画线为界；局部剖的波浪线遇到孔/空腔必须断开；
  * 剖面线只画在剖面区域内、45°（相邻零件才反向）；
  * 通孔的端面轮廓线在“被剖到”的位置要断开；
  * 截交线是平面图形，相贯线是两曲面共有点的连线（本例按大圆柱半径作简化圆弧，
    圆心在小圆柱轴线上，与两转向轮廓线交点严丝合缝）。
"""
from __future__ import annotations

import math

from pairkit import (BLUE, GREEN, INK, MUTED, RED, PairFigure, arc_pts, wave_pts)

MODULE = "projection"      # 全部属于「剖视与投影辨析」模块
LIC = "自绘"


def _ang(dx: float, dy: float) -> float:
    return math.degrees(math.atan2(dy, dx))


# =====================================================================
# 1. 半剖 vs 局部剖
# =====================================================================
def _sleeve(p, mode: str) -> None:
    """对称法兰套筒（Ø80/Ø60，内孔 Ø24，高 122）：mode='full' 全剖，'half' 半剖。

    左半永远画剖视；右半 full 也剖、half 画视图。
    """
    cx, yb = 190, 270          # 轴线 x、底面 y
    y_ft, y_tp = 240, 148      # 法兰顶面、筒体顶面
    xf0, xf1 = 125, 255        # 法兰（Ø80）
    xb0, xb1 = 142, 238        # 筒体（Ø60）
    xc0, xc1 = 171, 209        # 内孔（Ø24）

    # 左半：剖视
    p.polyline([(xf0, yb), (xf0, y_ft), (xb0, y_ft), (xb0, y_tp)], cls="thick")
    p.polyline([(xc0, y_tp), (xc0, yb)], cls="thick")          # 剖到的孔壁
    p.polyline([(xb0, y_tp), (xc0, y_tp)], cls="thick")        # 顶面（孔口处断开）
    p.polyline([(xf0, yb), (xc0, yb)], cls="thick")            # 底面（孔口处断开）
    p.hatch([(xf0, y_ft), (xb0, y_ft), (xb0, y_tp), (xc0, y_tp), (xc0, yb), (xf0, yb)])

    # 右半
    p.polyline([(xf1, yb), (xf1, y_ft), (xb1, y_ft), (xb1, y_tp)], cls="thick")
    p.polyline([(xc1, yb), (xf1, yb)], cls="thick")
    if mode == "full":
        p.polyline([(xc1, y_tp), (xc1, yb)], cls="thick")
        p.polyline([(xc1, y_tp), (xb1, y_tp)], cls="thick")
        p.hatch([(xf1, y_ft), (xb1, y_ft), (xb1, y_tp), (xc1, y_tp), (xc1, yb), (xf1, yb)])
    else:
        # 半剖的视图半：顶面连着画过去，不画孔壁、不画虚线
        p.polyline([(cx, y_tp), (xb1, y_tp)], cls="thick")

    p.line(cx, 132, cx, 286, cls="center", color=MUTED)


def _plate_local(p) -> list | list:
    """平板 + 竖直通孔，用波浪线作局部剖边界（波浪线在孔口断开）。"""
    px0, px1, py0, py1 = 90, 290, 160, 262
    hx0, hx1 = 168, 212                     # 通孔 Ø44
    yw = 212                                # 波浪线基准

    def yfun(x):
        return yw

    lw = wave_pts(hx0, px0, yfun)           # 从孔左壁向左端
    rw = wave_pts(hx1, px1, yfun)           # 从孔右壁向右端

    # 剖面区域（波浪线以上）
    p.hatch([(px0, py0), (hx0, py0)] + lw)
    p.hatch([(hx1, py0), (px1, py0)] + rw[::-1])

    # 板轮廓：顶边在孔口处断开
    p.polyline([(px0, py0), (hx0, py0)], cls="thick")
    p.polyline([(hx1, py0), (px1, py0)], cls="thick")
    p.polyline([(px0, py1), (px1, py1)], cls="thick")
    p.polyline([(px0, py0), (px0, py1)], cls="thick")
    p.polyline([(px1, py0), (px1, py1)], cls="thick")
    # 波浪线（细实线，手画）
    p.polyline(lw, cls="thin")
    p.polyline(rw, cls="thin")
    # 剖到的孔壁 / 未剖到的孔壁
    p.polyline([(hx0, py0), (hx0, yw)], cls="thick")
    p.polyline([(hx1, py0), (hx1, yw)], cls="thick")
    p.polyline([(hx0, yw), (hx0, py1)], cls="dash")
    p.polyline([(hx1, yw), (hx1, py1)], cls="dash")
    return [lw, rw]


def pair_pou_ban_jubu():
    fig = PairFigure(
        "PAIR-POU-BAN-JUBU",
        "半剖视图 与 局部剖视图",
        "同一个问题的两种分界：半剖靠对称中心线，局部剖靠波浪线",
        "半剖视图（对称法兰套筒）", "局部剖视图（平板 + 竖直通孔）",
    )
    a, b = fig.a, fig.b
    _sleeve(a, "half")
    a.callout(1, 190, 140, 190, 116)        # 分界线 = 对称中心线
    a.callout(2, 255, 255, 302, 262)        # 对称件才有“另一半”外形可看
    a.callout(3, 142, 220, 94, 224)         # 只剖左半

    _plate_local(b)
    b.callout(1, 120, 212, 58, 196)         # 分界线 = 波浪线
    b.callout(2, 290, 180, 326, 176)        # 不受对称限制、外形几乎全保留
    b.callout(3, 250, 250, 306, 246)        # 只剖一小块

    fig.leg(1, "分界线不同：A 用细点画线（对称中心线），B 用细实线波浪线，手画、不规则")
    fig.leg(2, "适用条件不同：A 只用于对称机件；B 不受对称限制，要保留大部分外形时首选")
    fig.leg(3, "剖切范围不同：A 恰好剖一半；B 只剖开要表达的那一小块，其余全按外形画")
    fig.leg(None, "波浪线不能与轮廓线重合、不能画在孔槽的空腔上；遇孔必须断开（B 图在孔口处断开）")
    return fig, {
        "title": "半剖视图 vs 局部剖视图",
        "chapter": "第七章 机件的常用表达方法",
        "kp_ids": ["KP-EXPR-010", "KP-EXPR-011"],
        "a": {"label": "A", "caption": "半剖视图", "正确性": "正确"},
        "b": {"label": "B", "caption": "局部剖视图", "正确性": "正确"},
        "differences": [
            {"no": 1, "name": "分界线", "a_desc": "以细点画线（对称中心线）为界",
             "b_desc": "以细实线波浪线为界，波浪线手画、不规则",
             "why": "半剖的分界线必须是对称中心线；局部剖的分界线是断裂边界，只能用波浪线"},
            {"no": 2, "name": "适用条件", "a_desc": "只用于对称机件",
             "b_desc": "不受对称限制，也用于不对称机件或需保留全部外形时",
             "why": "半剖靠“对称”把另一半补出来；机件不对称时没有可对应的另一半，只能局部剖"},
            {"no": 3, "name": "剖切范围", "a_desc": "恰好剖开一半，一半剖视一半视图",
             "b_desc": "只剖开需要表达内部结构的一小块",
             "why": "半剖范围固定为 1/2；局部剖范围可大可小，由波浪线位置决定"},
        ],
        "question": {
            "stem": "下面两张图分别是什么剖视？判断依据是什么？",
            "options": ["A 半剖、B 局部剖", "A 局部剖、B 半剖", "两张都是半剖", "两张都是局部剖"],
            "answer_index": 0,
            "explain": "看分界线：以对称中心线分界、一半剖一半视图的是半剖（A）；以波浪线分界、只剖开一块的是局部剖（B）。",
        },
        "source": "依据 GB/T 4458.6 自绘",
    }


# =====================================================================
# 2. 全剖 vs 半剖（同一零件）
# =====================================================================
def pair_pou_quan_ban():
    fig = PairFigure(
        "PAIR-POU-QUAN-BAN",
        "全剖视图 与 半剖视图",
        "同一对称零件、同一剖切位置：只差“剖多少”和“分不分界”",
        "全剖视图", "半剖视图",
    )
    a, b = fig.a, fig.b
    _sleeve(a, "full")
    a.callout(1, 190, 136, 190, 114)
    a.callout(2, 255, 255, 302, 262)
    a.callout(3, 142, 160, 98, 150)

    _sleeve(b, "half")
    b.callout(1, 190, 136, 190, 114)
    b.callout(2, 255, 255, 302, 262)
    b.callout(3, 142, 160, 98, 150)

    fig.leg(1, "分界不同：A 无分界（整个视图都剖开）；B 以对称中心线为界，一半剖一半视图")
    fig.leg(2, "外形信息不同：A 完全看不到外形；B 保留一半外形，一个视图兼顾内外")
    fig.leg(3, "适用条件不同：A 用于外形简单、内形复杂（可不对称）的机件；B 只能用于对称机件")
    fig.leg(None, "剖切面通过对称面、按投影关系配置时可省略标注；半剖不加标注，靠中心线识别")
    return fig, {
        "title": "全剖视图 vs 半剖视图",
        "chapter": "第七章 机件的常用表达方法",
        "kp_ids": ["KP-EXPR-009", "KP-EXPR-010"],
        "a": {"label": "A", "caption": "全剖视图", "正确性": "正确"},
        "b": {"label": "B", "caption": "半剖视图", "正确性": "正确"},
        "differences": [
            {"no": 1, "name": "分界线", "a_desc": "没有分界，整个视图都是剖视", "b_desc": "以对称中心线为界",
             "why": "全剖把机件完全剖开，不存在剖/不剖的分界；半剖必须有一条分界线"},
            {"no": 2, "name": "外形保留", "a_desc": "外形完全不画，只表达内部", "b_desc": "保留一半外形",
             "why": "全剖用剖切面把机件整个切开，外形投影已被移去；半剖视图半边仍是外形投影"},
            {"no": 3, "name": "适用条件", "a_desc": "外形简单、内形复杂且（可）不对称", "b_desc": "只用于对称机件",
             "why": "全剖适用范围比半剖宽；但对称件用全剖会丢掉全部外形信息，此时应选半剖"},
        ],
        "question": {
            "stem": "同一个对称法兰套筒，为什么右侧用半剖比左侧用全剖更合适？",
            "options": ["全剖不符合国标", "半剖既表达内孔又保留一半外形，全剖把外形全丢了",
                        "半剖画得快", "两种都可以，没有区别"],
            "answer_index": 1,
            "explain": "零件对称且有内孔：全剖（A）只看得见内形；半剖（B）一半剖视表达内孔、一半视图保留外形轮廓。",
        },
        "source": "依据 GB/T 4458.6 自绘",
    }


# =====================================================================
# 3. 断面图 vs 剖视图（同一切割位置）
# =====================================================================
def _section_shape(p, with_base: bool) -> None:
    """立柱 Ø64 + 肋板（221…262）在水平剖切面处的断面形状；with_base 时加底板轮廓。"""
    cx, cy, R = 190, 180, 32
    half = 8.0
    xa = cx + math.sqrt(R * R - half * half)          # 肋板与圆面的交点 x
    a0 = _ang(xa - cx, half)                          # 14.48°
    rib_x1 = 262

    # 剖面区域
    p.hatch(arc_pts(cx, cy, R, 0, 360))
    p.hatch([(xa, cy - half), (rib_x1, cy - half), (rib_x1, cy + half), (xa, cy + half)])

    # 底板轮廓（剖切面后方可见轮廓）：只画粗实线，不画剖面线
    if with_base:
        p.polyline([(110, 100), (270, 100), (270, 260), (110, 260)], cls="thick", close=True)

    # 断面轮廓：圆弧（肋板以外的那一段）+ 肋板三条边
    p.polyline(arc_pts(cx, cy, R, a0, 360 - a0), cls="thick")
    p.polyline([(xa, cy - half), (rib_x1, cy - half), (rib_x1, cy + half), (xa, cy + half)], cls="thick")


def pair_duanmian_poushi():
    fig = PairFigure(
        "PAIR-DUANMIAN-POUSHI",
        "断面图 与 剖视图",
        "同一零件、同一剖切位置（水平剖切、向下投射）：只差“后面的东西画不画”",
        "断面图（只画断面形状）", "剖视图（断面 + 后方轮廓）",
    )
    a, b = fig.a, fig.b
    _section_shape(a, with_base=False)
    _section_shape(b, with_base=True)
    for p in (a, b):
        p.text(190, 92, "A—A", size=11, color=MUTED)

    # ①② 在 A 图指向空白，正是“断面图里没有这些轮廓”的意思
    a.callout(1, 270, 120, 312, 120)        # 底板轮廓：A 无
    a.callout(2, 240, 110, 300, 90)         # 底板不画剖面线：A 无
    a.callout(3, 240, 180, 312, 228)        # 肋板要画剖面线
    b.callout(1, 270, 120, 312, 120)
    b.callout(2, 240, 110, 300, 90)
    b.callout(3, 240, 180, 312, 228)

    fig.leg(1, "图形内容不同：A 只画断面形状（圆 + 肋）；B 还要画出剖切面后方可见的底板轮廓")
    fig.leg(2, "底板轮廓的画法：A 没有；B 用粗实线画，但绝不能画剖面线")
    fig.leg(3, "剖面线的范围：两图都只画在被切到的断面内（圆与肋），肋板横向剖切必须画")
    fig.leg(None, "断面图轮廓用粗实线；不对称的移出断面必须标箭头，在剖切符号延长线上的对称断面可省略全部标注")
    return fig, {
        "title": "断面图 vs 剖视图",
        "chapter": "第七章 机件的常用表达方法",
        "kp_ids": ["KP-EXPR-019", "KP-EXPR-020", "KP-EXPR-022"],
        "a": {"label": "A", "caption": "断面图", "正确性": "正确"},
        "b": {"label": "B", "caption": "剖视图", "正确性": "正确"},
        "differences": [
            {"no": 1, "name": "图形内容", "a_desc": "只有剖切面切断机件得到的断面形状（圆 + 肋）",
             "b_desc": "断面形状 + 剖切面后方所有可见轮廓（底板方形）",
             "why": "断面图只回答“切断处长什么样”；剖视图还回答“后面还有什么”"},
            {"no": 2, "name": "底板轮廓的画法", "a_desc": "不出现", "b_desc": "画粗实线，但不画剖面线",
             "why": "剖面线只属于被剖切面切到的断面区域；后方可见轮廓是投影，不是断面"},
            {"no": 3, "name": "剖面线范围", "a_desc": "只画在断面形状内（含肋板）", "b_desc": "同样只画在断面形状内",
             "why": "肋板被横向剖切（剖切面垂直于肋板纵向对称面）时仍要画剖面线，两图一致"},
        ],
        "question": {
            "stem": "两图的剖切位置和投射方向完全相同，B 比 A 多画了什么？",
            "options": ["剖面线", "肋板的断面", "剖切面后方的底板轮廓", "中心线"],
            "answer_index": 2,
            "explain": "断面图（A）只有断面形状；剖视图（B）在此之外还要画出剖切面后方可见的底板轮廓，且底板只画粗实线、不画剖面线。",
        },
        "source": "依据 GB/T 4458.6 自绘",
    }


# =====================================================================
# 4. 截交线 vs 相贯线
# =====================================================================
def pair_jiejiao_xiangguan():
    fig = PairFigure(
        "PAIR-JIEJIAO-XIANGUAN",
        "截交线 与 相贯线",
        "一个是平面切出来的，一个是两个曲面碰出来的",
        "截交线（平面截圆柱）", "相贯线（两圆柱相贯）",
    )
    a, b = fig.a, fig.b

    # ---- A：立式圆柱被正垂面斜切 ----
    a.polyline([(150, 192), (150, 92), (230, 122), (230, 192)], cls="thick", close=True)
    a.line(128, 83.75, 252, 130.25, cls="center", color=MUTED)     # 截平面
    a.text(124, 80, "截平面", size=9.5, anchor="end", color=MUTED)
    a.polyline([(142, 244), (238, 244)], cls="center", color=MUTED)
    a.polyline([(190, 206), (190, 282)], cls="center", color=MUTED)
    a.circle(190, 244, 40, cls="thick")
    a.text(144, 184, "主视图", size=9.5, anchor="end", color=MUTED)
    a.text(144, 276, "俯视图", size=9.5, anchor="end", color=MUTED)
    a.callout(1, 240, 130, 292, 116)        # 截平面（平面）
    a.callout(2, 190, 107, 190, 78)         # 截交线（椭圆的积聚投影）
    a.callout(3, 150, 150, 100, 168)        # 素线：求截交线取素线上的点

    # ---- B：小圆柱竖直相贯到大圆柱上 ----
    b.polyline([(100, 168), (158, 168)], cls="thick")              # 大圆柱顶边（左段）
    b.polyline([(222, 168), (280, 168)], cls="thick")              # 大圆柱顶边（右段）
    b.polyline([(100, 168), (100, 248), (280, 248), (280, 168)], cls="thick")
    b.polyline([(158, 104), (158, 168)], cls="thick")              # 小圆柱左母线
    b.polyline([(222, 104), (222, 168)], cls="thick")
    b.polyline([(158, 104), (222, 104)], cls="thick")
    b.polyline(arc_pts(190, 144, 40, 143.13, 36.87), cls="thick")  # 相贯线（简化圆弧 R=R大）
    b.line(88, 225, 232, 225, cls="center", color=MUTED)           # 辅助平面
    for xx in (158, 222):
        b.dot(xx, 225, 2.0, MUTED)                                 # 辅助面与两曲面的交点
    b.text(84, 221, "辅助面", size=9.5, anchor="end", color=MUTED)
    b.callout(1, 158, 140, 72, 120)         # 两曲面相交
    b.callout(2, 216, 174, 250, 120)        # 相贯线
    b.callout(3, 94, 225, 72, 252)          # 辅助平面求共有点

    fig.leg(1, "交线来源不同：A 是平面与曲面相交（截交线）；B 是两曲面相交（相贯线）")
    fig.leg(2, "交线形状不同：A 一定是平面图形（垂直轴→圆、倾斜→椭圆、平行轴→矩形）；B 一般是空间曲线")
    fig.leg(3, "求法不同：A 求截平面与素线的交点；B 求两曲面共有点（积聚性取点 / 辅助平面法）")
    fig.leg(None, "两种交线都用粗实线画；相贯线总是向大直径回转体的轴线方向弯曲")
    return fig, {
        "title": "截交线 vs 相贯线",
        "chapter": "第四章 立体的投影",
        "kp_ids": ["KP-SOLID-010", "KP-SOLID-012", "KP-SOLID-016", "KP-SOLID-018"],
        "a": {"label": "A", "caption": "截交线", "正确性": "正确"},
        "b": {"label": "B", "caption": "相贯线", "正确性": "正确"},
        "differences": [
            {"no": 1, "name": "来源", "a_desc": "平面与回转体表面相交（截平面切出来的）",
             "b_desc": "两个回转体表面相交（两个曲面碰出来的）",
             "why": "截交线是“平面 ∩ 曲面”的公有线；相贯线是“曲面 ∩ 曲面”的公有线"},
            {"no": 2, "name": "形状", "a_desc": "一定是平面图形：垂直轴线为圆、倾斜为椭圆、平行轴线为矩形",
             "b_desc": "一般是空间曲线，特殊情况下才退化为平面曲线或直线",
             "why": "平面切回转体得到的图形必在平面内；两曲面相交一般不在同一平面内"},
            {"no": 3, "name": "求法", "a_desc": "求截平面与素线（或纬圆）的交点，连成截交线",
             "b_desc": "求两曲面的共有点：积聚性表面取点法，或作辅助平面求共有点",
             "why": "相贯线没有“现成的平面”可依据，必须先造一个能同时与两曲面交出直线的辅助面"},
        ],
        "question": {
            "stem": "下面两条交线，哪条是截交线？为什么？",
            "options": ["B 是截交线：两个圆柱相交得到", "两条都是相贯线", "两条都是截交线",
                        "A 是截交线：平面切圆柱得到，是平面图形（此处为椭圆）"],
            "answer_index": 3,
            "explain": "A 有明确的截平面（细点画线），圆柱被平面斜切得到椭圆，主视图上积聚成斜直线；B 是两个圆柱表面相交，交线是空间曲线，用辅助平面求共有点。",
        },
        "source": "依据 GB/T 16675.1 简化表示法与教材第四章自绘",
    }


# =====================================================================
# 5. 虚线 vs 粗实线（用错会怎样）
# =====================================================================
def pair_xushi_shixian():
    fig = PairFigure(
        "PAIR-XUSHI-SHIXIAN",
        "不可见轮廓：细虚线 与 粗实线",
        "同一块带阶梯孔的板：线型一改，读出来的形体就变了",
        "细虚线（正确）", "粗实线（错误）",
        a_ok=True, b_ok=False,
    )
    px0, px1, py0, py1 = 90, 290, 140, 250
    cx = 190
    big0, big1 = cx - 30, cx + 30          # Ø60 沉孔
    sm0, sm1 = cx - 16, cx + 16            # Ø32 通孔
    step = 176                             # 沉孔深度

    for p, cls in ((fig.a, "dash"), (fig.b, "thick")):
        p.polyline([(px0, py0), (px1, py0), (px1, py1), (px0, py1)], cls="thick", close=True)
        p.polyline([(big0, py0), (big0, step)], cls=cls)      # 沉孔壁
        p.polyline([(big1, py0), (big1, step)], cls=cls)
        p.polyline([(big0, step), (big1, step)], cls=cls)     # 沉孔肩部
        p.polyline([(sm0, step), (sm0, py1)], cls=cls)        # 通孔壁
        p.polyline([(sm1, step), (sm1, py1)], cls=cls)

    for p in (fig.a, fig.b):
        p.callout(1, 160, 158, 118, 118)      # 线型
        p.callout(2, 174, 224, 58, 190)       # 线宽
        p.callout(3, 206, 205, 322, 202)      # 读图结论

    fig.leg(1, "线型不同：A 内孔轮廓用细虚线（不可见轮廓）；B 画成粗实线，等于宣称它是可见轮廓")
    fig.leg(2, "线宽不同：A 虚线用细线 0.8（约粗实线的一半）；B 与外形同宽 2，粗细层次消失")
    fig.leg(3, "读图结论不同：A 孔在板后、外形完整；B 孔像是开在前面的槽，形体判断直接错")
    fig.leg(None, "内部结构复杂时的正确做法是改用剖视图（或局部剖），不是把虚线描粗")
    return fig, {
        "title": "虚线 vs 粗实线（不可见轮廓用错）",
        "chapter": "第一章 制图的基本知识和基本技能",
        "kp_ids": ["KP-BASIC-005", "KP-BASIC-006"],
        "a": {"label": "A", "caption": "细虚线（正确）", "正确性": "正确"},
        "b": {"label": "B", "caption": "粗实线（错误）", "正确性": "错误"},
        "differences": [
            {"no": 1, "name": "线型", "a_desc": "不可见轮廓用细虚线（6 4）",
             "b_desc": "同一组轮廓画成粗实线，表示成了可见轮廓",
             "why": "国标规定：粗实线只画可见轮廓线，不可见轮廓线必须用虚线"},
            {"no": 2, "name": "线宽", "a_desc": "虚线用细线，宽约 0.8，是粗实线的一半",
             "b_desc": "与外形轮廓同为 2，粗细分不出来",
             "why": "线型靠“形状 + 线宽”两重区分；虚线一旦和粗实线同宽，图面就失去层次"},
            {"no": 3, "name": "读图结论", "a_desc": "阶梯孔在板的背后，外形完整",
             "b_desc": "孔看起来开在前面、成了可见的槽，形体判断错",
             "why": "线型是形体的可见性信息，不是画图者的美观选择"},
        ],
        "question": {
            "stem": "同一块板、同一个阶梯孔，为什么 B 图的画法是错的？",
            "options": ["剖面线画少了", "把不可见轮廓画成了粗实线，把内部结构误表示成可见轮廓",
                        "中心线漏画", "尺寸标注位置不对"],
            "answer_index": 1,
            "explain": "粗实线表示可见轮廓线，虚线表示不可见轮廓线。B 图把后面的阶梯孔画成粗实线，读图时会误判为前面开口，属于典型的“虚实不分”。",
        },
        "source": "依据 GB/T 4457.4 自绘",
    }


# =====================================================================
# 6. 第一角 vs 第三角投影
# =====================================================================
def _three_views(p, first_angle: bool) -> None:
    """同一台阶块（底板 60×40×10 + 凸台 30×20×20）的三种视图配置。

    第一角：俯视图在主视图下方、左视图在主视图右方。
    第三角：俯视图在主视图上方、左视图在主视图左方。
    比例 1.3：长 78、深 52、总高 39、底板高 13、凸台宽 39、凸台深 26。
    """
    L, D, HT, HB, TW, TD = 78, 52, 39, 13, 39, 26

    def front(x0, y0):
        # L 形主视图（高的一侧在左）
        p.polyline([(x0, y0 + HT), (x0, y0), (x0 + TW, y0), (x0 + TW, y0 + HT - HB),
                    (x0 + L, y0 + HT - HB), (x0 + L, y0 + HT)], cls="thick", close=True)

    def top(x0, y0):
        p.polyline([(x0, y0), (x0 + L, y0), (x0 + L, y0 + D), (x0, y0 + D)], cls="thick", close=True)
        p.polyline([(x0 + TW, y0 + 13), (x0 + TW, y0 + 39)], cls="thick")
        p.polyline([(x0, y0 + 13), (x0 + TW, y0 + 13)], cls="thick")
        p.polyline([(x0, y0 + 39), (x0 + TW, y0 + 39)], cls="thick")

    def side(x0, y0):
        p.polyline([(x0, y0 + HT), (x0, y0 + HT - HB), (x0 + 13, y0 + HT - HB),
                    (x0 + 13, y0), (x0 + 13 + TD, y0), (x0 + 13 + TD, y0 + HT - HB),
                    (x0 + D, y0 + HT - HB), (x0 + D, y0 + HT)], cls="thick", close=True)

    if first_angle:
        front(100, 120)
        top(100, 180)
        side(200, 120)
        p.text(139, 112, "主视图", size=9.5, color=MUTED)
        p.text(139, 246, "俯视图", size=9.5, color=MUTED)
        p.text(226, 174, "左视图", size=9.5, color=MUTED)
    else:
        front(150, 182)
        top(150, 118)
        side(60, 182)
        p.text(189, 110, "俯视图", size=9.5, color=MUTED)
        p.text(189, 236, "主视图", size=9.5, color=MUTED)
        p.text(86, 236, "左视图", size=9.5, color=MUTED)


def pair_diyijiao_disanjiao():
    fig = PairFigure(
        "PAIR-DIYIJIAO-DISANJIAO",
        "第一角画法 与 第三角画法",
        "同一个台阶块、同样三个视图：只差视图摆在主视图的哪一侧",
        "第一角画法（我国采用）", "第三角画法（欧美部分国家）",
    )
    a, b = fig.a, fig.b
    _three_views(a, first_angle=True)
    _three_views(b, first_angle=False)

    # ① 俯视图位置 / ② 左视图位置 / ③ 靠近主视图那一侧的含义
    a.callout(1, 100, 206, 58, 206)
    a.callout(2, 252, 130, 306, 132)
    a.callout(3, 120, 180, 58, 168)
    b.callout(1, 228, 144, 300, 144)
    b.callout(2, 60, 200, 34, 200)
    b.callout(3, 215, 170, 300, 192)

    fig.leg(1, "俯视图位置：第一角在主视图下方；第三角在主视图上方（正好相反）")
    fig.leg(2, "左视图位置：第一角在主视图右方；第三角在主视图左方")
    fig.leg(3, "靠近主视图的一侧：第一角表示物体的后面；第三角表示物体的前面")
    fig.leg(None, "第一角＝观察者—机件—投影面（我国采用）；第三角＝观察者—投影面—机件（欧美部分国家）")
    return fig, {
        "title": "第一角投影 vs 第三角投影",
        "chapter": "第七章 机件的常用表达方法",
        "kp_ids": ["KP-EXPR-006", "KP-PROJ-004"],
        "a": {"label": "A", "caption": "第一角画法", "正确性": "正确"},
        "b": {"label": "B", "caption": "第三角画法", "正确性": "正确"},
        "differences": [
            {"no": 1, "name": "俯视图位置", "a_desc": "在主视图下方", "b_desc": "在主视图上方",
             "why": "第一角把俯视图投到机件下方的投影面；第三角把投影面放在观察者与机件之间，俯视图落在上方"},
            {"no": 2, "name": "左视图位置", "a_desc": "在主视图右方", "b_desc": "在主视图左方",
             "why": "第一角“视图与观察方向分居两侧”；第三角“视图与观察方向同侧”"},
            {"no": 3, "name": "靠近主视图一侧的含义", "a_desc": "表示物体的后面",
             "b_desc": "表示物体的前面",
             "why": "分界（折线）在机件的哪一侧，决定了靠近主视图的那条边对应物体的前面还是后面"},
        ],
        "question": {
            "stem": "一张图把俯视图画在主视图上方，它用的是哪种画法？",
            "options": ["第一角画法", "两种都可能", "第三角画法", "局部视图配置"],
            "answer_index": 2,
            "explain": "我国采用第一角画法，俯视图在主视图下方；俯视图在主视图上方是第三角画法的典型特征。",
        },
        "source": "依据 GB/T 4458.1 自绘",
    }


# =====================================================================
# 7. R 与 Ø 标注
# =====================================================================
def _wrong(p, cx: float, cy: float, r: float = 5.0) -> None:
    """错误标记：画一个红色小叉（不用 ✗ 字形，避免字体缺字变豆腐块）。"""
    p.line(cx - r, cy - r, cx + r, cy + r, cls="marker", color=RED)
    p.line(cx - r, cy + r, cx + r, cy - r, cls="marker", color=RED)


def _rounded_plate(p, ok: bool) -> None:
    """半圆头板（左端 R26、右端方头）+ Ø16 通孔；ok=False 时画错注法。"""
    cx, cy, R = 104, 196, 26
    x1 = 214
    y0, y1 = cy - R, cy + R                 # 170 / 222
    # 轮廓：左半圆（从 (cx,y0) 绕过左侧到 (cx,y1)）+ 三条直边
    p.polyline(arc_pts(cx, cy, R, -90, -270), cls="thick")
    p.polyline([(cx, y1), (x1, y1), (x1, y0), (cx, y0)], cls="thick")
    # 中心记号 + 孔
    p.line(cx - 5, cy, cx + 5, cy, cls="thin", color=MUTED)
    p.line(cx, cy - 5, cx, cy + 5, cls="thin", color=MUTED)
    hx, hy, hr = 176, 196, 10
    p.circle(hx, hy, hr, cls="thick")

    if ok:
        # R：尺寸线自圆心引向圆弧，只画一个箭头
        p.arrow_line(cx, cy, cx - R, cy, color=INK, both=False)
        p.text(72, 191, "R20", size=11, anchor="end")
        # Ø：尺寸线通过圆心，两端箭头指向圆周
        p.arrow_line(hx - hr, hy, hx + hr, hy, color=INK, both=True)
        p.text(hx, 181, "Ø16", size=11)
    else:
        # 错：用引出线标 Ø40（半圆），用 R8 标整圆
        p.arrow_line(cx - R, cy, 62, 176, color=INK, both=False)
        p.text(58, 172, "Ø40", size=11, anchor="end")
        _wrong(p, 30, 170)
        p.arrow_line(hx - hr, hy, hx + hr, hy, color=INK, both=True)
        p.text(hx, 181, "R8", size=11)
        _wrong(p, 196, 179)


def pair_banjing_zhijing():
    fig = PairFigure(
        "PAIR-BANJING-ZHIJING",
        "R（半径）与 Ø（直径）标注",
        "同一块板、同样两个尺寸：符号选错，意思就变了",
        "正确：圆弧注 R、整圆注 Ø", "错误：圆弧注 Ø、整圆注 R",
        a_ok=True, b_ok=False,
    )
    a, b = fig.a, fig.b
    _rounded_plate(a, ok=True)
    _rounded_plate(b, ok=False)

    for p in (a, b):
        p.callout(1, 66, 186, 96, 146)      # 半圆的符号
        p.callout(2, 180, 186, 262, 160)    # 整圆的符号
        p.callout(3, 78, 196, 60, 238)      # 尺寸线与圆心的关系

    fig.leg(1, "圆弧用 R：A 半圆弧注 R20；B 注成 Ø40 —— 直径符号只能用于整圆或大于半圆的弧")
    fig.leg(2, "整圆用 Ø：A 通孔注 Ø16；B 注成 R8 —— 半径符号不能标整圆")
    fig.leg(3, "尺寸线：R 的尺寸线必须通过圆心、只画一个箭头指向圆弧；Ø 的尺寸线通过圆心、两端箭头指向圆周")
    fig.leg(None, "口诀：整圆和大于半圆的弧注 Ø，半圆及小于半圆的弧注 R")
    return fig, {
        "title": "R 与 Ø 标注（半径 vs 直径）",
        "chapter": "第一章 制图的基本知识和基本技能",
        "kp_ids": ["KP-BASIC-010", "KP-BASIC-012"],
        "a": {"label": "A", "caption": "正确注法", "正确性": "正确"},
        "b": {"label": "B", "caption": "错误注法", "正确性": "错误"},
        "differences": [
            {"no": 1, "name": "圆弧的符号", "a_desc": "半圆弧注 R20（半径）", "b_desc": "注成 Ø40（直径）",
             "why": "半圆及小于半圆的圆弧必须注半径 R；注 Ø 会被理解成整圆或大于半圆的弧"},
            {"no": 2, "name": "整圆的符号", "a_desc": "通孔注 Ø16（直径）", "b_desc": "注成 R8（半径）",
             "why": "整圆必须注直径 Ø；注 R 无法唯一确定圆的形状"},
            {"no": 3, "name": "尺寸线画法", "a_desc": "R 的尺寸线通过圆心，只画一个箭头指向圆弧",
             "b_desc": "用引出线代替尺寸线，不通过圆心",
             "why": "半径尺寸的尺寸线必须从圆心量起；直径尺寸的尺寸线必须通过圆心、两端画箭头"},
        ],
        "question": {
            "stem": "一个半圆弧（半径 20）和一个整圆通孔（直径 16），应该怎么注？",
            "options": ["半圆弧注 Ø40，整圆注 R8", "两个都注 R", "两个都注 Ø",
                        "半圆弧注 R20，整圆注 Ø16"],
            "answer_index": 3,
            "explain": "圆弧（≤180°）注半径 R，整圆（或 >180° 的弧）注直径 Ø。图上标 Ø 表示直径，标 R 表示半径，不能互换。",
        },
        "source": "依据 GB/T 4458.4 自绘",
    }


# =====================================================================
# 8. 封闭尺寸链 vs 留开口
# =====================================================================
def _stepped_shaft(p, closed: bool) -> None:
    """三段阶梯轴（长 30/40/50），closed=True 时把总长 120 也注出来 → 封闭尺寸链。"""
    xs = [76, 124, 188, 268]          # 三段的四个分界面
    yc = 192
    hs = [48, 64, 48]                 # 三段的高度（视觉上的粗细）
    tops = [yc - h / 2 for h in hs]
    bots = [yc + h / 2 for h in hs]

    # 台阶轴轮廓（12 点闭合折线）：中间一段直径更大，两肩各有一条端面线
    pts = [(xs[0], bots[0]), (xs[0], tops[0]), (xs[1], tops[0]), (xs[1], tops[1]),
           (xs[2], tops[1]), (xs[2], tops[2]), (xs[3], tops[2]), (xs[3], bots[2]),
           (xs[2], bots[2]), (xs[2], bots[1]), (xs[1], bots[1]), (xs[1], bots[0])]
    p.polyline(pts, cls="thick", close=True)

    # 分段的链式尺寸（连续标注）
    ych = 246
    for i, (txt, ext) in enumerate(zip(("30", "40", "50"), bots)):
        p.dim_h(xs[i], xs[i + 1], ych, txt, ext_from=(ext, bots[i]))
    for xx, yy in ((xs[0], bots[0]), (xs[1], bots[1]), (xs[2], bots[1]), (xs[3], bots[2])):
        p.line(xx, yy + 3, xx, ych + 5, cls="thin")

    if closed:
        ytot = 142
        p.dim_h(xs[0], xs[3], ytot, "120", ext_from=(tops[0], tops[2]))
        for xx, yy in ((xs[0], tops[0]), (xs[3], tops[2])):
            p.line(xx, yy - 3, xx, ytot - 5, cls="thin")


def pair_chicunlian_fengbi():
    fig = PairFigure(
        "PAIR-CHICUNLIAN-FENGBI",
        "封闭尺寸链 与 留开口",
        "同一根三段轴：尺寸多注一个，还是少注一个？",
        "封闭尺寸链（错误）", "留一个开口环（正确）",
        a_ok=False, b_ok=True,
    )
    a, b = fig.a, fig.b
    _stepped_shaft(a, closed=True)
    _stepped_shaft(b, closed=False)

    for p in (a, b):
        p.callout(1, 241, 140, 302, 118)    # 总长注不注
        p.callout(2, 124, 246, 46, 262)     # 链是否首尾相接
        p.callout(3, 196, 246, 302, 266)    # 公差往哪儿跑

    fig.leg(1, "总长尺寸：A 注出 120，与 30+40+50 首尾相接；B 不注总长，把它留作开口环")
    fig.leg(2, "尺寸链状态：A 封闭 → 各尺寸公差互相挤压，加工检验必出矛盾；B 开口 → 各段独立")
    fig.leg(3, "开口环怎么选：留下的应是最次要、自然形成的尺寸（此例为总长），不能删关键装配尺寸")
    fig.leg(None, "同一方向的尺寸链只允许留一个开口环；总体尺寸与各段尺寸不要同时注出")
    return fig, {
        "title": "封闭尺寸链 vs 留开口",
        "chapter": "第五章 组合体的视图与形体构型",
        "kp_ids": ["KP-COMP-017", "KP-COMP-020"],
        "a": {"label": "A", "caption": "封闭尺寸链（错误）", "正确性": "错误"},
        "b": {"label": "B", "caption": "留开口环（正确）", "正确性": "正确"},
        "differences": [
            {"no": 1, "name": "总长尺寸", "a_desc": "注出总长 120，与三段 30+40+50 首尾相接",
             "b_desc": "总长不注，留作开口环",
             "why": "总长与各段同时注出，4 个尺寸互相制约，任何一个的公差都会顶掉其余三个"},
            {"no": 2, "name": "尺寸链状态", "a_desc": "封闭回路，误差无处可去", "b_desc": "留有开口，误差落在开口环上",
             "why": "封闭链在加工中必然出现“合不上”的矛盾，所以标注时不允许封闭"},
            {"no": 3, "name": "开口环的选择", "a_desc": "没有开口环", "b_desc": "去掉最次要、自然形成的总长",
             "why": "开口环应选不重要的、由加工自然形成的尺寸；关键装配尺寸必须直接注出"},
        ],
        "question": {
            "stem": "三段轴注 30、40、50，再注总长 120，问题出在哪？",
            "options": ["形成封闭尺寸链，各段公差互相挤压，加工检验必然出现矛盾",
                        "尺寸注得太少，工人看不懂", "应该注 30、40、50 就一定对", "总长必须注，错的是分段尺寸"],
            "answer_index": 0,
            "explain": "同一方向首尾相接的尺寸链一旦封闭，各环公差互相制约，累积误差必然造成某一尺寸超差。应去掉最次要的一环（此例为总长）留出开口。",
        },
        "source": "依据 GB/T 4458.4 自绘",
    }


# =====================================================================
# 9. 内螺纹 vs 外螺纹画法
# =====================================================================
def pair_luowen_neiwai():
    fig = PairFigure(
        "PAIR-LUOWEN-NEIWAI",
        "外螺纹 与 内螺纹（剖视）画法",
        "同样按比例画：粗细实线在内、外螺纹里正好互换",
        "外螺纹（M40）", "内螺纹剖视（M40）",
    )
    a, b = fig.a, fig.b
    # 外螺纹：d=80 画粗实线，d1=0.85d=68 画细实线
    ya, yb_ = 150, 230
    d1a, d1b = 156, 224
    a.polyline([(86, ya), (250, ya)], cls="thick")
    a.polyline([(86, yb_), (250, yb_)], cls="thick")
    a.polyline([(86, ya), (86, yb_)], cls="thick")            # 端面
    a.polyline([(250, ya), (250, yb_)], cls="thick")          # 螺纹终止线（粗实线）
    a.polyline([(86, d1a), (250, d1a)], cls="thin")           # 牙底：细实线
    a.polyline([(86, d1b), (250, d1b)], cls="thin")
    a.line(78, 190, 258, 190, cls="center", color=MUTED)

    # 内螺纹（剖视）：D1=40.8 画粗实线，D=48 画细实线；剖面线画到牙顶粗实线
    yt, ybo = 150, 230
    ya2, yb2 = 169.6, 210.4
    yD_a, yD_b = 166, 214
    b.hatch([(86, yt), (230, yt), (230, ya2), (86, ya2)])
    b.hatch([(86, yb2), (230, yb2), (230, ybo), (86, ybo)])
    b.polyline([(86, yt), (230, yt)], cls="thick")
    b.polyline([(86, ybo), (230, ybo)], cls="thick")
    b.polyline([(86, yt), (86, ya2)], cls="thick")            # 端面（孔口处断开）
    b.polyline([(86, yb2), (86, ybo)], cls="thick")
    b.polyline([(230, yt), (230, ya2)], cls="thick")
    b.polyline([(230, yb2), (230, ybo)], cls="thick")
    b.polyline([(86, ya2), (230, ya2)], cls="thick")          # 牙顶：粗实线
    b.polyline([(86, yb2), (230, yb2)], cls="thick")
    b.polyline([(86, yD_a), (230, yD_a)], cls="thin")         # 牙底：细实线
    b.polyline([(86, yD_b), (230, yD_b)], cls="thin")
    b.line(78, 190, 238, 190, cls="center", color=MUTED)

    # 同一编号在两图指的不是同一条线（粗细线互换），所以目标点分别给
    a.callout(1, 200, ya, 300, 142)         # 牙顶：A 在大径（外）
    a.callout(2, 200, d1b, 300, 242)        # 牙底：A 在小径（细线）
    a.callout(3, 215, 190, 300, 196)        # 剖面线：A 无
    b.callout(1, 200, ya2, 300, 142)        # 牙顶：B 在小径（内）
    b.callout(2, 190, yD_b, 300, 242)       # 牙底：B 在大径（细线）
    b.callout(3, 240, 224, 300, 196)        # 剖面线：B 画到牙顶为止

    fig.leg(1, "牙顶线型不同：A 外螺纹的牙顶在大径 d 上，画粗实线；B 内螺纹的牙顶在小径 D₁ 上，画粗实线")
    fig.leg(2, "牙底线型不同：A 牙底（小径 d₁≈0.85d）画细实线；B 牙底（大径 D）画细实线 —— 两图粗细线正好互换")
    fig.leg(3, "剖面线：A 是实心杆，不剖、无剖面线；B 剖面线画到牙顶粗实线为止，不越过牙底细实线")
    fig.leg(None, "端视图：外螺纹大径整圆粗实线、小径约 3/4 圈细实线；内螺纹相反（小径粗、大径细 3/4 圈）")
    return fig, {
        "title": "内螺纹 vs 外螺纹画法",
        "chapter": "第八章 螺纹、齿轮、常用标准件及其连接",
        "kp_ids": ["KP-STD-003", "KP-STD-006"],
        "a": {"label": "A", "caption": "外螺纹", "正确性": "正确"},
        "b": {"label": "B", "caption": "内螺纹（剖视）", "正确性": "正确"},
        "differences": [
            {"no": 1, "name": "牙顶线型", "a_desc": "牙顶在大径 d 上，画粗实线（最外一条）",
             "b_desc": "牙顶在小径 D₁ 上，画粗实线（最内一条）",
             "why": "牙顶是实际存在的牙尖，按国标一律画粗实线；外螺纹牙尖在外、内螺纹牙尖在内"},
            {"no": 2, "name": "牙底线型", "a_desc": "牙底（小径 d₁≈0.85d）画细实线",
             "b_desc": "牙底（大径 D）画细实线",
             "why": "牙底按比例画成细实线，所以内外螺纹的粗、细线位置正好互换"},
            {"no": 3, "name": "剖面线", "a_desc": "实心杆件不剖，没有剖面线", "b_desc": "剖面线画到牙顶粗实线为止",
             "why": "内螺纹剖视时剖面线只能画到牙顶（粗实线），画过牙底线是最常见的错误"},
        ],
        "question": {
            "stem": "内螺纹剖视图里，哪条线画粗实线？",
            "options": ["大径 D 画粗实线，小径 D₁ 画细实线", "两条都画粗实线",
                        "小径 D₁（牙顶）画粗实线，大径 D（牙底）画细实线", "两条都画细实线"],
            "answer_index": 2,
            "explain": "与外螺纹相反：内螺纹牙顶是小径 D₁，画粗实线；牙底是大径 D，画细实线，剖面线画到粗实线为止。",
        },
        "source": "依据 GB/T 4459.1 自绘",
    }


# =====================================================================
# 10. 相邻零件剖面线方向
# =====================================================================
def pair_poumainxian_fangxiang():
    fig = PairFigure(
        "PAIR-POUMAINXIAN-FANGXIANG",
        "相邻零件剖面线：同向 与 反向",
        "座 + 衬套同时被剖：方向一样就成了一块料",
        "剖面线同向（错误）", "剖面线反向（正确）",
        a_ok=False, b_ok=True,
    )
    a, b = fig.a, fig.b
    # 座：外壳 110…270 × 150…230，镗孔 Ø56（162…218），壁厚 12
    # 套：外径 Ø56（162…218）、内孔 Ø28（176…204），壁厚 14，两端各伸出 12
    seat_t = [(110, 150), (270, 150), (270, 162), (110, 162)]
    seat_b = [(110, 218), (270, 218), (270, 230), (110, 230)]
    bush_t = [(98, 162), (282, 162), (282, 176), (98, 176)]
    bush_b = [(98, 204), (282, 204), (282, 218), (98, 218)]

    for p, same in ((a, True), (b, False)):
        p.hatch(seat_t, "hatch45")
        p.hatch(seat_b, "hatch45")
        p.hatch(bush_t, "hatch45" if same else "hatch135")
        p.hatch(bush_b, "hatch45" if same else "hatch135")
        # 座：上下外表面 + 左右端面（端面只到配合面为止，160…220 处是套的壁，不能画通）
        p.polyline([(110, 150), (270, 150)], cls="thick")
        p.polyline([(110, 230), (270, 230)], cls="thick")
        for xx in (110, 270):
            p.polyline([(xx, 150), (xx, 162)], cls="thick")
            p.polyline([(xx, 218), (xx, 230)], cls="thick")
        # 套：外表面（与座孔是配合面，只画一条线）与内表面
        p.polyline([(98, 162), (282, 162)], cls="thick")
        p.polyline([(98, 218), (282, 218)], cls="thick")
        p.polyline([(98, 176), (282, 176)], cls="thick")
        p.polyline([(98, 204), (282, 204)], cls="thick")
        # 套的两个端面（环形，孔口处断开）
        for xx in (98, 282):
            p.polyline([(xx, 162), (xx, 176)], cls="thick")
            p.polyline([(xx, 204), (xx, 218)], cls="thick")
        p.line(88, 190, 292, 190, cls="center", color=MUTED)
        # 零件名
        p.text(54, 126, "座", size=11)
        p.leader(56, 132, 116, 156, color=MUTED)
        p.text(54, 250, "套", size=11)
        p.leader(56, 244, 116, 211, color=MUTED)

    for p in (a, b):
        p.callout(1, 250, 169, 318, 138)    # 套的剖面线方向
        p.callout(2, 245, 218, 318, 250)    # 套下壁与座下带的交界：分不分得清

    fig.leg(1, "方向不同：A 座与套的剖面线都是 45°（同向）；B 座 45°、套 135°（方向相反）")
    fig.leg(2, "辨认结果：A 两条带连成一片，看不出是两个零件；B 一眼分开，配合面（一条线）很清楚")
    fig.leg(None, "也可以方向相同而间距不同；关键是相邻零件必须能区分，同一零件在各视图中必须一致")
    fig.leg(None, "相邻零件的接触面、配合面只画一条线；有间隙才画两条线")
    return fig, {
        "title": "相邻零件剖面线同向 vs 反向",
        "chapter": "第十章 装配图",
        "kp_ids": ["KP-ASSY-005", "KP-EXPR-008"],
        "a": {"label": "A", "caption": "剖面线同向（错误）", "正确性": "错误"},
        "b": {"label": "B", "caption": "剖面线反向（正确）", "正确性": "正确"},
        "differences": [
            {"no": 1, "name": "剖面线方向", "a_desc": "座与套都画 45°，方向相同",
             "b_desc": "座画 45°、套画 135°，方向相反",
             "why": "相邻两零件同时被剖切时，剖面线方向相反（或间距不同）才能区分零件"},
            {"no": 2, "name": "辨认结果", "a_desc": "剖面线连成一片，读图时像一整块材料",
             "b_desc": "两个零件、配合面（一条线）清清楚楚",
             "why": "装配图里零件的界面全靠剖面线区分；方向相同就丢掉了装配关系信息"},
        ],
        "question": {
            "stem": "装配图里相邻两个零件同时被剖切，剖面线应该怎么画？",
            "options": ["方向必须相同", "方向相反（或用不同间距）", "只画其中一个零件", "都不画剖面线"],
            "answer_index": 1,
            "explain": "相邻零件的剖面线方向应相反或间距不同，否则分不清是两个零件；同一零件在各视图中的方向、间距则必须一致。",
        },
        "source": "依据 GB/T 4457.5、GB/T 4458.2 自绘",
    }


# ---------------------------------------------------------------- 注册表
ALL = [
    ("PAIR-POU-BAN-JUBU", pair_pou_ban_jubu),
    ("PAIR-POU-QUAN-BAN", pair_pou_quan_ban),
    ("PAIR-DUANMIAN-POUSHI", pair_duanmian_poushi),
    ("PAIR-JIEJIAO-XIANGUAN", pair_jiejiao_xiangguan),
    ("PAIR-XUSHI-SHIXIAN", pair_xushi_shixian),
    ("PAIR-DIYIJIAO-DISANJIAO", pair_diyijiao_disanjiao),
    ("PAIR-BANJING-ZHIJING", pair_banjing_zhijing),
    ("PAIR-CHICUNLIAN-FENGBI", pair_chicunlian_fengbi),
    ("PAIR-LUOWEN-NEIWAI", pair_luowen_neiwai),
    ("PAIR-POUMAINXIAN-FANGXIANG", pair_poumainxian_fangxiang),
]
