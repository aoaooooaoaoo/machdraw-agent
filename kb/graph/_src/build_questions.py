# -*- coding: utf-8 -*-
"""构建问题图谱 kb/graph/questions.jsonl。

三层递进：layer1 基础理解 / layer2 识图分析 / layer3 综合绘图与工艺。
kp_ids 通过 kp_index.json 由 key 映射，避免手写编号。
"""

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
IDX = os.path.normpath(os.path.join(HERE, "..", "..", "knowledge", "_src", "kp_index.json"))
OUT = os.path.normpath(os.path.join(HERE, "..", "questions.jsonl"))

with open(IDX, encoding="utf-8") as f:
    KP = json.load(f)

# (keys, layer, bloom, question, hint)
QUESTIONS = [
    # ---------- layer 1：基础理解 ----------
    (["figsize"], 1, "记忆",
     "GB/T 14689 规定的 A0～A4 五种基本幅面之间是什么关系？A3 图纸的尺寸是多少（宽×长）？",
     "从 A0 起沿长边对折得到下一号；A3 为 297 mm×420 mm。"),
    (["view_rule"], 1, "理解",
     "三视图中的“长对正、高平齐、宽相等”分别说的是哪两个视图之间的关系？作图时常用什么辅助手段保证宽相等？",
     "主俯长对正、主左高平齐、俯左宽相等；用 45° 辅助线转移宽度。"),
    (["hatch"], 1, "记忆",
     "剖视图中金属材料的剖面线用什么线型、什么方向？同一零件在不同视图中的剖面线有什么要求？",
     "45° 等距细实线；同一零件方向与间距必须一致，相邻零件方向相反或间距不同。"),
    (["half_section"], 1, "理解",
     "半剖视图的分界线应该画成什么线？为什么不能画波浪线？",
     "细点画线（对称中心线）；波浪线表示断裂边界，而半剖是以对称面为界，并非断裂。"),
    (["thread_five"], 1, "记忆",
     "螺纹的五要素是哪五项？为什么只有五要素完全相同的内、外螺纹才能旋合？",
     "牙型、公称直径、螺距、线数、旋向；五要素决定牙型轮廓与螺旋参数，任何一项不同都旋合不上。"),
    (["surface_structure", "surface_symbol"], 1, "理解",
     "表面结构代号有哪三种图形符号？分别表示什么加工状态？Ra 数值越小说明表面什么性质越好？",
     "基本符号（未指定工艺）、加短横线（去除材料）、加小圆（不去除材料）；Ra 越小表面越光滑。"),
    (["tolerance_grade"], 1, "理解",
     "标准公差共有多少个等级？IT 后面的数字越大，公差值和加工精度分别怎么变化？",
     "IT01、IT0、IT1～IT18 共 20 级；数字越大公差越大、精度越低。"),
    (["iso_angle"], 1, "记忆",
     "正等轴测图的三个轴间角是多少？理论轴向伸缩系数是多少？实际作图取多少？图形因此放大了多少倍？",
     "均为 120°；理论 0.82，实用取 1，图形放大约 1.22 倍。"),
    (["section_line", "intersect_concept"], 1, "理解",
     "截交线和相贯线分别由什么相交产生？它们的共同性质是什么？",
     "截交线=平面截切立体；相贯线=两立体表面相交；共同点是交线为两者表面的公有线、交点为共有点。"),
    (["six_views"], 1, "理解",
     "按第一角画法展开后，俯视图、仰视图、左视图、右视图、后视图分别配置在主视图的什么方位？",
     "俯视在下、仰视在上、左视在右、右视在左、后视在最右。"),
    (["gear_formula"], 1, "记忆",
     "标准直齿圆柱齿轮的分度圆、齿顶圆、齿根圆直径计算公式分别是什么？中心距怎么算？",
     "d=mz、da=m(z+2)、df=m(z-2.5)、a=m(z1+z2)/2。"),

    # ---------- layer 2：识图分析 ----------
    (["read_step", "form_analysis", "make_up_third"], 2, "分析",
     "已知主、俯视图，要补画左视图，应该按什么步骤进行？为什么不能直接对着两视图“拼线条”？",
     "先想形体（分块—对投影—定形状位置—综合），再按三等规律逐块投影；拼线条容易把形体想错。"),
    (["frame_meaning", "surface_relation"], 2, "分析",
     "视图中相邻的两个线框可能表示什么关系？怎样判断它们是否共面？共面与相错在图上分别怎么画？",
     "两个不同表面（可能高低、前后或凹凸不同）；结合其他视图判断；共面不画分界线，相错必须画分界线。"),
    (["fit_calc", "fit_type", "base_hole"], 2, "应用",
     "已知一对配合 Φ30H7/k6，怎样判断它属于哪类配合？请说明计算最大间隙或最大过盈的公式与步骤。",
     "画出公差带比较位置：交叠即过渡配合；Xmax=ES-ei，Ymax=EI-es，Ymin=ES-ei。"),
    (["full_section", "half_section", "local_section"], 2, "应用",
     "机件外形简单、内部结构复杂且不对称，应选全剖、半剖还是局部剖？如果机件是对称的又该怎么选？",
     "不对称且外形简单选全剖；对称机件选半剖；只需表达局部内部结构时用局部剖。"),
    (["rib_rule", "hatch"], 2, "分析",
     "机件上有肋板，当剖切平面沿肋板的纵向对称面剖切时，剖视图中肋板应怎样画？为什么这样规定？",
     "按不剖绘制、不画剖面线；否则薄壁肋板会被误认为实心体块，与实际不符。"),
    (["removed_section", "coincident_section", "section_compare"], 2, "应用",
     "轴上有一个键槽，要表达它的截面形状应选断面图还是剖视图？移出断面与重合断面如何取舍？",
     "选断面图（只画断面形状）；视图外空间够、需清晰表达用移出断面，图形简单且不影响视图时用重合断面。"),
    (["surface_relation", "tangent_flush", "combo_error"], 2, "分析",
     "检查组合体三视图时，哪些位置的线最容易“多画”？哪些位置的线最容易“漏画”？",
     "多画：相切处、共面（平齐）处；漏画：相错处的分界线、转向轮廓线、截交/相贯线、虚线。"),
    (["cyl_cyl_special", "intersect_visible"], 2, "应用",
     "两圆柱正交相贯且直径相差较大时，相贯线可用什么简化画法？圆弧半径与圆心怎么定？相贯线弯向哪一侧？",
     "用一段圆弧代替；半径取大圆柱半径、圆心在小圆柱轴线上、过两转向轮廓线交点；弯向大圆柱轴线方向。"),

    # ---------- layer 3：综合绘图与工艺 ----------
    (["part_express", "main_view_choice", "section_concept"], 3, "综合",
     "要为一张 A3 图幅上的支架零件图确定完整表达方案：主视图怎么选、需要几个视图、哪些结构用剖视或断面？请说明理由。",
     "按形状特征/工作位置定主视图；剖视表达轴承孔与内腔；筋板、安装孔用局部视图或简化画法；以完整清晰为准。"),
    (["assy_disassemble", "assy_read", "tolerance_mark"], 3, "综合",
     "从齿轮泵装配图中拆画泵体零件图，需要经过哪几个步骤？装配图上已有的尺寸与配合代号各应如何处理？",
     "分离零件→重选表达方案→移注相关尺寸并补注定形尺寸→配合代号查表注极限偏差→补技术要求与标题栏。"),
    (["dim_class", "dim_datum", "dim_closed_chain", "dim_avoid"], 3, "综合",
     "标注组合体尺寸时怎样做到“完整、正确、清晰、合理”？尺寸链为什么不允许封闭？交线为什么不能注尺寸？",
     "定形/定位/总体尺寸齐全；基准统一、不封闭（留开口环）；交线由基本体尺寸自然形成，注了就矛盾。"),
    (["stud_connect", "proportional", "connect_error"], 3, "综合",
     "画双头螺柱连接图时，旋入深度 bm 应如何按材料取值？画法上必须遵守哪些规定（通孔、剖面线、标准件、终止线）？",
     "钢/青铜 bm=d、铸铁 1.25d~1.5d、铝 2d；通孔 1.1d 留间隙、相邻件剖面线相反、标准件不剖、旋入端终止线与孔口平齐。"),
    (["intersect_method", "intersect_special", "curve_point"], 3, "综合",
     "一个由圆柱与圆球同轴组合的形体，被一水平面截切后又与另一圆柱正交相贯。请安排作图顺序，并说明特殊点应怎么找。",
     "先按截交线求水平截切（球得圆、柱得圆/矩形），再按相贯线求正交部分；特殊点取转向轮廓线交点与最高最低最前最后点。"),
    (["cad_layer", "cad_dim", "cad_layout", "cad_plot"], 3, "综合",
     "用 AutoCAD 出一张符合国标的 A3 零件图，从绘图到打印需要设置哪些关键项？怎样保证线宽、比例与标注都正确？",
     "按图线建图层并设线宽线型；按标注样式统一样式；布局设视口比例；打印样式表控制线宽，图幅选 A3。"),
    (["base_shaft", "transition_fit", "surface_structure", "geo_tolerance"], 3, "综合",
     "设计一根与滚动轴承内圈配合的轴颈，应怎样选公差带、表面结构与几何公差？为什么这样选？",
     "用基轴制思路选 k6/m6 等过渡配合；配合面 Ra 取 0.8~1.6；注圆柱度或圆跳动控制形状位置，保证旋转精度。"),
]

rows = []
seen_q = set()
errors = []
for i, (keys, layer, bloom, question, hint) in enumerate(QUESTIONS, start=1):
    qid = "Q-%03d" % i
    if qid in seen_q:
        errors.append("qid 重复: %s" % qid)
    seen_q.add(qid)
    kp_ids = []
    for k in keys:
        if k not in KP:
            errors.append("%s 引用了不存在的 kp key: %s" % (qid, k))
            continue
        kp_ids.append(KP[k]["kp_id"])
    if layer not in (1, 2, 3):
        errors.append("%s layer 非法" % qid)
    rows.append({
        "qid": qid,
        "layer": layer,
        "question": question,
        "bloom": bloom,
        "kp_ids": kp_ids,
        "hint": hint,
    })

with open(OUT, "w", encoding="utf-8", newline="\n") as f:
    for r in rows:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

by_layer = {}
for r in rows:
    by_layer[r["layer"]] = by_layer.get(r["layer"], 0) + 1
print("问题 %d -> %s" % (len(rows), OUT))
print("分层:", dict(sorted(by_layer.items())))
print("errors:", len(errors))
for e in errors:
    print("  !", e)
