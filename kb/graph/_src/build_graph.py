# -*- coding: utf-8 -*-
"""构建知识图谱 nodes.jsonl / edges.jsonl。

- 节点按 key 引用 kp_index.json（由 build_kp.py 生成），避免手写 kp_id 错位
- 边四类：prereq 前置 / contrast 对比 / compose 组成 / cause 因果
- 自检：节点数、边数、各类边计数、source/target 存在性、无自环、无重复边、
        必备对比边、prereq 子图上“投影基础 → 装配图”的可达性
"""

import json
import os
import sys
from collections import defaultdict, deque

HERE = os.path.dirname(os.path.abspath(__file__))
IDX = os.path.normpath(os.path.join(HERE, "..", "..", "knowledge", "_src", "kp_index.json"))

with open(IDX, encoding="utf-8") as f:
    KP = json.load(f)

# ---------- 节点表：(key, tier, label) ----------
NODES = [
    # core：课程核心
    ("three_views", "core", "三视图形成"),
    ("view_rule", "core", "三等规律"),
    ("section_concept", "core", "剖视图"),
    ("combo_form", "core", "组合体"),

    # concept：跨链关键概念（用于对比与学情诊断）
    ("section_line", "concept", "截交线"),
    ("intersect_concept", "concept", "相贯线"),
    ("outline", "concept", "转向轮廓线"),
    ("form_analysis", "concept", "形体分析法"),
    ("line_face_analysis", "concept", "线面分析法"),
    ("dim_datum", "concept", "尺寸基准"),
    ("thread_five", "concept", "螺纹五要素"),
    ("hatch", "concept", "剖面线"),

    # ---------------- trackA：形体表达链 ----------------
    ("proj_method", "trackA", "投影基础"),
    ("ortho_feature", "trackA", "正投影特性"),
    ("three_planes", "trackA", "三面投影体系"),
    ("point_proj", "trackA", "点的三面投影"),
    ("point_coord", "trackA", "点的坐标"),
    ("point_visible", "trackA", "重影点与可见性"),
    ("line_general", "trackA", "一般位置直线"),
    ("line_parallel", "trackA", "投影面平行线"),
    ("line_perp", "trackA", "投影面垂直线"),
    ("line_point", "trackA", "直线上的点"),
    ("right_angle", "trackA", "直角投影定理"),
    ("two_lines", "trackA", "两直线相对位置"),
    ("plane_repr", "trackA", "平面的表示法"),
    ("plane_general", "trackA", "一般位置平面"),
    ("plane_parallel", "trackA", "投影面平行面"),
    ("plane_perp", "trackA", "投影面垂直面"),
    ("plane_point_line", "trackA", "平面上的点线"),
    ("line_plane_intersect", "trackA", "直线与平面相交"),
    ("plane_plane_intersect", "trackA", "两平面相交"),
    ("parallel_perp", "trackA", "平行与垂直关系"),
    ("change_plane", "trackA", "换面法"),
    ("change_rule", "trackA", "点的换面规律"),
    ("change_app", "trackA", "换面法应用"),
    ("rt_triangle", "trackA", "直角三角形法"),
    ("prism_proj", "trackA", "棱柱投影"),
    ("pyramid_proj", "trackA", "棱锥投影"),
    ("solid_point", "trackA", "平面立体表面取点"),
    ("cylinder", "trackA", "圆柱"),
    ("cone", "trackA", "圆锥"),
    ("sphere", "trackA", "圆球"),
    ("curve_point", "trackA", "曲面立体表面取点"),
    ("section_method", "trackA", "截交线求法"),
    ("cyl_section", "trackA", "圆柱截交线"),
    ("cone_section", "trackA", "圆锥截交线"),
    ("sphere_section", "trackA", "圆球截交线"),
    ("section_true", "trackA", "断面真形"),
    ("intersect_method", "trackA", "相贯线求法"),
    ("cyl_cyl_special", "trackA", "两圆柱正交相贯"),
    ("intersect_special", "trackA", "相贯线特殊情况"),
    ("intersect_visible", "trackA", "相贯线可见性"),
    ("cut_hole", "trackA", "切割与穿孔"),
    ("surface_relation", "trackA", "表面连接关系"),
    ("tangent_flush", "trackA", "相切与平齐画法"),
    ("feature_view", "trackA", "形状特征视图"),
    ("main_view_choice", "trackA", "主视图选择"),
    ("view_draw_step", "trackA", "画三视图步骤"),
    ("hidden_line", "trackA", "虚线处理"),
    ("frame_meaning", "trackA", "图线与线框含义"),
    ("read_step", "trackA", "读图步骤"),
    ("make_up_third", "trackA", "补画第三视图"),
    ("make_up_line", "trackA", "补画漏线"),
    ("choice_third", "trackA", "选择第三视图"),
    ("combo_add", "trackA", "叠加式读图"),
    ("combo_cut", "trackA", "切割式读图"),
    ("symmetry_draw", "trackA", "对称结构"),
    ("combo_check", "trackA", "三视图校核"),
    ("combo_error", "trackA", "组合体常见错误"),
    ("sketch", "trackA", "徒手草图"),
    ("config_design", "trackA", "构型设计"),
    ("dim_class", "trackA", "组合体尺寸分类"),
    ("dim_closed_chain", "trackA", "尺寸链不封闭"),
    ("dim_overall", "trackA", "总体尺寸"),
    ("dim_avoid", "trackA", "不注交线与相切尺寸"),
    ("unfold_prism", "trackA", "平面立体展开"),
    ("unfold_cyl", "trackA", "圆柱圆锥展开"),
    ("axo_concept", "trackA", "轴测图"),
    ("iso_angle", "trackA", "正等测"),
    ("iso_ellipse", "trackA", "正等测椭圆画法"),
    ("cavalier", "trackA", "斜二测"),
    ("axo_section", "trackA", "轴测剖视图"),
    ("axo_compare", "trackA", "轴测图与三视图比较"),
    ("axo_choose", "trackA", "轴测图选择"),
    ("six_views", "trackA", "六个基本视图"),
    ("partial_view", "trackA", "局部视图"),
    ("directional_view", "trackA", "向视图"),
    ("oblique_view", "trackA", "斜视图"),
    ("full_section", "trackA", "全剖视图"),
    ("half_section", "trackA", "半剖视图"),
    ("local_section", "trackA", "局部剖视图"),
    ("section_label", "trackA", "剖视图标注"),
    ("rib_rule", "trackA", "肋板纵剖规定"),
    ("step_section", "trackA", "阶梯剖"),
    ("revolved_section", "trackA", "旋转剖"),
    ("section_view", "trackA", "断面图"),
    ("removed_section", "trackA", "移出断面"),
    ("coincident_section", "trackA", "重合断面"),
    ("section_compare", "trackA", "断面与剖视区别"),
    ("enlarged_view", "trackA", "局部放大图"),

    # ---------------- trackB：工程规范链 ----------------
    ("figsize", "trackB", "图纸幅面"),
    ("frame", "trackB", "图框与留边"),
    ("titleblock", "trackB", "标题栏"),
    ("scale", "trackB", "比例"),
    ("linetypes", "trackB", "图线种类"),
    ("linewidth", "trackB", "线宽"),
    ("linedraw", "trackB", "图线画法规定"),
    ("wavyline", "trackB", "波浪线与双折线"),
    ("dim4", "trackB", "尺寸注法四要素"),
    ("dimnum", "trackB", "尺寸数字与符号"),
    ("dimlayout", "trackB", "尺寸清晰布置"),
    ("dimcircle", "trackB", "圆与圆弧注法"),
    ("slopetaper", "trackB", "斜度与锥度"),
    ("arcconnect", "trackB", "圆弧连接"),
    ("lineseg", "trackB", "线段分析"),
    ("thread_type", "trackB", "螺纹分类"),
    ("thread_draw", "trackB", "螺纹规定画法"),
    ("thread_mark", "trackB", "螺纹标记"),
    ("thread_blind", "trackB", "不通孔螺纹"),
    ("thread_error", "trackB", "螺纹画法错误"),
    ("fastener", "trackB", "螺纹紧固件"),
    ("proportional", "trackB", "比例画法"),
    ("bolt_connect", "trackB", "螺栓连接"),
    ("stud_connect", "trackB", "双头螺柱连接"),
    ("screw_connect", "trackB", "螺钉连接"),
    ("connect_error", "trackB", "连接画法错误"),
    ("gear_param", "trackB", "齿轮参数"),
    ("gear_formula", "trackB", "齿轮尺寸计算"),
    ("gear_draw", "trackB", "齿轮规定画法"),
    ("gear_mesh", "trackB", "齿轮啮合画法"),
    ("key_connect", "trackB", "键连接"),
    ("pin_connect", "trackB", "销连接"),
    ("bearing", "trackB", "滚动轴承"),
    ("spring", "trackB", "弹簧"),
    ("surface_structure", "trackB", "表面结构"),
    ("surface_symbol", "trackB", "表面结构代号"),
    ("fit_basic", "trackB", "基本尺寸与极限尺寸"),
    ("deviation", "trackB", "偏差与尺寸公差"),
    ("tolerance_grade", "trackB", "标准公差与基本偏差"),
    ("base_hole", "trackB", "基孔制"),
    ("base_shaft", "trackB", "基轴制"),
    ("clearance_fit", "trackB", "间隙配合"),
    ("interference_fit", "trackB", "过盈配合"),
    ("transition_fit", "trackB", "过渡配合"),
    ("fit_system", "trackB", "配合制度选用"),
    ("fit_type", "trackB", "配合类型判断"),
    ("fit_calc", "trackB", "配合计算"),
    ("tolerance_mark", "trackB", "公差与配合标注"),
    ("geo_tolerance", "trackB", "几何公差"),
    ("process_datum", "trackB", "工艺基准"),
    ("process_structure", "trackB", "工艺结构"),

    # ---------------- branch：零件图 / 装配图 ----------------
    ("part_content", "branch", "零件图"),
    ("part_express", "branch", "零件表达方案"),
    ("part_datum", "branch", "尺寸基准（零件图）"),
    ("part_dim_reasonable", "branch", "合理标注尺寸"),
    ("read_part", "branch", "读零件图"),
    ("draw_part", "branch", "画零件图"),
    ("assy_content", "branch", "装配图"),
    ("assy_view", "branch", "装配图表达方案"),
    ("assy_dim", "branch", "装配图尺寸"),
    ("assy_parts_list", "branch", "序号与明细栏"),
    ("assy_draw", "branch", "装配图规定画法"),
    ("assy_process", "branch", "装配工艺结构"),
    ("assy_read", "branch", "读装配图"),
    ("assy_disassemble", "branch", "拆画零件图"),
    ("assy_vs_part", "branch", "装配图与零件图区别"),
    ("assy_common", "branch", "常见装配体"),
    ("assy_tech", "branch", "装配图技术要求"),
    ("assy_explode", "branch", "装配体爆炸图"),
]

# ---------- 边表：(src, dst, rel, note) ----------
EDGES = [
    # ===== prereq：投影基础 → 点线面 → 立体 → 组合体 → 剖视 → 零件图 → 装配图 =====
    ("proj_method", "ortho_feature", "prereq", "先懂投影法分类，才能理解正投影的度量性"),
    ("proj_method", "three_planes", "prereq", "三面投影体系是投影法的具体落地"),
    ("three_planes", "three_views", "prereq", "有了三投影面才能得到三视图"),
    ("three_views", "view_rule", "prereq", "三等规律来自三视图的展开关系"),
    ("three_planes", "point_proj", "prereq", "点的三面投影建立在三投影面体系上"),
    ("point_proj", "point_coord", "prereq", "先会画投影，再理解投影与坐标的对应"),
    ("point_proj", "point_visible", "prereq", "重影点判断以点的投影规律为前提"),
    ("point_proj", "line_general", "prereq", "直线由两点确定，点的投影是基础"),
    ("line_general", "line_parallel", "prereq", "先认识一般位置直线，才能对比平行线的特殊性"),
    ("line_general", "line_perp", "prereq", "垂直线的积聚性需要与一般位置对比理解"),
    ("line_general", "line_point", "prereq", "直线上的点以一般位置直线的投影规律为基础"),
    ("line_general", "right_angle", "prereq", "直角投影定理讨论的是两直线的垂直关系"),
    ("line_general", "two_lines", "prereq", "两直线相对位置要先掌握单条直线的投影"),
    ("right_angle", "parallel_perp", "prereq", "垂直关系（线面、面面）以直角投影定理为工具"),
    ("plane_repr", "plane_general", "prereq", "先会表示平面，再讨论其投影特性"),
    ("plane_general", "plane_parallel", "prereq", "平行面的特征需与一般位置平面对比"),
    ("plane_general", "plane_perp", "prereq", "垂直面的积聚性需与一般位置平面对比"),
    ("plane_repr", "plane_point_line", "prereq", "面上取点取线以平面的表示法为前提"),
    ("plane_point_line", "line_plane_intersect", "prereq", "求交点要在平面内作辅助线"),
    ("line_plane_intersect", "plane_plane_intersect", "prereq", "两平面交线转化为求两个交点"),
    ("plane_point_line", "parallel_perp", "prereq", "平行与垂直的判断要用面上的直线"),
    ("line_general", "change_plane", "prereq", "一般位置直线的实长问题引出换面法"),
    ("change_plane", "change_rule", "prereq", "先懂换面原理，再学点的换面规律"),
    ("change_rule", "change_app", "prereq", "换面法的应用以点的换面规律为基本操作"),
    ("change_plane", "rt_triangle", "prereq", "直角三角形法与换面法同为求真长的方法"),
    ("three_planes", "prism_proj", "prereq", "平面立体投影要在三投影面体系中作出"),
    ("three_planes", "cylinder", "prereq", "曲面立体投影同样基于三投影面体系"),
    ("prism_proj", "solid_point", "prereq", "先会画棱柱投影，才能在表面上取点"),
    ("pyramid_proj", "solid_point", "prereq", "棱锥取点要先掌握棱锥的投影"),
    ("cylinder", "curve_point", "prereq", "圆柱的积聚性是曲面取点最常用的入口"),
    ("cone", "curve_point", "prereq", "圆锥取点需要素线法与纬圆法"),
    ("sphere", "curve_point", "prereq", "球面取点只能靠纬圆法"),
    ("prism_proj", "section_line", "prereq", "截交线要在立体投影的轮廓上求"),
    ("solid_point", "section_line", "prereq", "求截交点实质是在立体表面取点"),
    ("curve_point", "section_line", "prereq", "曲面立体截交线靠表面取点完成"),
    ("section_line", "section_method", "prereq", "先懂截交线性质，再学求法"),
    ("section_method", "cyl_section", "prereq", "圆柱截交线是截交线求法的第一个应用"),
    ("section_method", "cone_section", "prereq", "圆锥截交线要按截平面与轴线夹角分类"),
    ("section_method", "sphere_section", "prereq", "圆球截交线恒为圆，靠求圆半径作图"),
    ("section_line", "section_true", "prereq", "截交线的投影不是真形时要另求断面真形"),
    ("cyl_section", "section_true", "prereq", "斜截圆柱的断面真形要用换面法"),
    ("curve_point", "intersect_concept", "prereq", "相贯线要在两个曲面立体的表面上求点"),
    ("intersect_concept", "intersect_method", "prereq", "先懂相贯线性质，再学表面取点法与辅助平面法"),
    ("intersect_method", "cyl_cyl_special", "prereq", "两圆柱正交是相贯线求法的典型情形"),
    ("intersect_method", "intersect_special", "prereq", "特殊情况（同轴、等径）由求法中的规律推出"),
    ("intersect_method", "intersect_visible", "prereq", "求出相贯线后还要判别可见性"),
    ("cyl_section", "cut_hole", "prereq", "切口先作为截平面截切来处理"),
    ("intersect_method", "cut_hole", "prereq", "穿孔产生的交线要用相贯线方法求"),
    ("section_method", "combo_form", "prereq", "组合体的截切结构要用截交线知识读画"),
    ("intersect_concept", "combo_form", "prereq", "组合体的相贯结构要用相贯线知识读画"),
    ("prism_proj", "combo_form", "prereq", "组合体由基本几何体组合而成"),
    ("three_views", "combo_form", "prereq", "组合体是应用三视图规律的主要对象"),
    ("combo_form", "surface_relation", "prereq", "讲组合体先讲相邻表面的连接关系"),
    ("surface_relation", "tangent_flush", "prereq", "相切、平齐的画法由表面连接关系决定"),
    ("combo_form", "form_analysis", "prereq", "形体分析法是分解组合体的基本方法"),
    ("combo_form", "line_face_analysis", "prereq", "切割式组合体主要靠线面分析法"),
    ("form_analysis", "feature_view", "prereq", "形体分析先抓形状特征最明显的视图"),
    ("feature_view", "main_view_choice", "prereq", "主视图方向按形状特征等原则确定"),
    ("main_view_choice", "view_draw_step", "prereq", "定下主视图后才能布置并画出三视图"),
    ("form_analysis", "view_draw_step", "prereq", "形体分析是画图步骤的第一步"),
    ("line_face_analysis", "frame_meaning", "prereq", "线面分析的前提是读懂线与线框的含义"),
    ("frame_meaning", "read_step", "prereq", "读图步骤以线框含义分析为核心手段"),
    ("form_analysis", "read_step", "prereq", "读图主要用形体分析法分块"),
    ("read_step", "make_up_third", "prereq", "补第三视图必须先读懂已知两视图"),
    ("read_step", "make_up_line", "prereq", "补漏线同样要先读懂形体"),
    ("read_step", "choice_third", "prereq", "选择题要先确定两视图对应的形体"),
    ("form_analysis", "combo_add", "prereq", "叠加式组合体用形体分析法分块"),
    ("line_face_analysis", "combo_cut", "prereq", "切割式组合体用线面分析法逐面分析"),
    ("make_up_third", "combo_check", "prereq", "补完视图要用三等规律复核"),
    ("make_up_line", "combo_check", "prereq", "补完漏线要复核线型与投影关系"),
    ("view_draw_step", "combo_check", "prereq", "画完底稿必须校核后再描深"),
    ("combo_check", "combo_error", "prereq", "校核的重点正是常见错误"),
    ("combo_form", "sketch", "prereq", "徒手草图同样要先做形体分析"),
    ("combo_form", "config_design", "prereq", "构型设计以组合体的构形规律为基础"),
    ("combo_form", "symmetry_draw", "prereq", "对称结构是组合体的一种常见形式"),
    ("three_views", "symmetry_draw", "prereq", "对称中心线要符合三视图的线型规定"),
    ("combo_form", "dim_class", "prereq", "组合体标注先区分定形、定位、总体尺寸"),
    ("dim_class", "dim_datum", "prereq", "定位尺寸必须从尺寸基准出发"),
    ("dim_class", "dim_closed_chain", "prereq", "尺寸链不封闭是在分类标注时检查的"),
    ("dim_class", "dim_overall", "prereq", "总体尺寸属于三类尺寸之一"),
    ("dim_class", "dim_avoid", "prereq", "不注交线是在尺寸分类标注时的规定"),
    ("dim_datum", "dim_closed_chain", "prereq", "同一方向从同一基准标注才不会形成封闭链"),
    ("prism_proj", "unfold_prism", "prereq", "平面立体展开要先会画棱柱棱锥投影"),
    ("pyramid_proj", "unfold_prism", "prereq", "棱锥展开要放射线法与棱线实长"),
    ("cylinder", "unfold_cyl", "prereq", "圆柱展开要先理解圆柱面与底圆"),
    ("cone", "unfold_cyl", "prereq", "圆锥展开要用母线实长"),
    ("rt_triangle", "unfold_prism", "prereq", "展开图上的棱线实长要用直角三角形法求"),
    ("change_app", "unfold_prism", "prereq", "展开时常用换面法求实长"),
    ("three_views", "axo_concept", "prereq", "先懂三视图，才能理解轴测图的直观性"),
    ("axo_concept", "iso_angle", "prereq", "轴间角与伸缩系数是画正等测的前提"),
    ("axo_concept", "cavalier", "prereq", "斜二测与正等测共用轴测投影概念"),
    ("iso_angle", "iso_ellipse", "prereq", "正等测中圆的投影要先懂伸缩系数"),
    ("iso_ellipse", "axo_section", "prereq", "轴测剖视中的椭圆与剖面线要用椭圆画法"),
    ("iso_angle", "axo_section", "prereq", "轴测剖视的剖面线方向由轴测轴决定"),
    ("three_views", "axo_compare", "prereq", "比较轴测图与三视图需要先掌握三视图"),
    ("axo_concept", "axo_compare", "prereq", "比较的前提是理解轴测图的性质"),
    ("axo_compare", "axo_choose", "prereq", "懂得两者差异才能按形体选轴测图"),
    ("axo_choose", "axo_section", "prereq", "轴测剖视也要按形体特点选择轴测类型"),
    ("three_views", "six_views", "prereq", "六个基本视图是三视图的扩展"),
    ("six_views", "partial_view", "prereq", "局部视图是基本视图的局部化表达"),
    ("six_views", "directional_view", "prereq", "向视图是自由配置的基本视图"),
    ("six_views", "oblique_view", "prereq", "斜视图要用辅助投影面，须先懂基本视图"),
    ("combo_form", "section_concept", "prereq", "剖视是在组合体表达遇到内部结构时的处理方法"),
    ("hidden_line", "section_concept", "prereq", "虚线太多读图困难，才引入剖视图"),
    ("six_views", "section_concept", "prereq", "剖视图仍以基本视图的投射方向为基础"),
    ("section_concept", "hatch", "prereq", "剖视图必须画剖面符号"),
    ("section_concept", "full_section", "prereq", "全剖是剖视的基本形式之一"),
    ("section_concept", "half_section", "prereq", "半剖是对称机件的剖视形式"),
    ("section_concept", "local_section", "prereq", "局部剖用于局部内部结构"),
    ("full_section", "section_label", "prereq", "全剖视图要按规则标注剖切位置与名称"),
    ("half_section", "section_label", "prereq", "半剖视图的标注规则相同"),
    ("local_section", "section_label", "prereq", "局部剖视图也要标注剖切位置"),
    ("section_concept", "rib_rule", "prereq", "肋板纵剖不画剖面线是剖视的特殊规定"),
    ("section_concept", "step_section", "prereq", "阶梯剖是剖切面种类的扩展"),
    ("section_concept", "revolved_section", "prereq", "旋转剖是剖切面种类的扩展"),
    ("step_section", "revolved_section", "prereq", "先学平行剖切面，再学相交剖切面"),
    ("section_concept", "section_view", "prereq", "断面图与剖视图同源，只画断面形状"),
    ("section_view", "removed_section", "prereq", "移出断面是断面图的主要形式"),
    ("section_view", "coincident_section", "prereq", "重合断面是断面图的另一种配置"),
    ("section_view", "section_compare", "prereq", "分清断面与剖视的前提是两者都会画"),
    ("section_concept", "enlarged_view", "prereq", "局部放大图常用于剖视中的细小结构"),
    ("figsize", "frame", "prereq", "幅面确定后才知道图框与留边的取值"),
    ("frame", "titleblock", "prereq", "标题栏位置由图框决定"),
    ("figsize", "scale", "prereq", "幅面与比例一起决定图样的布置"),
    ("figsize", "linetypes", "prereq", "图线是幅面内表达形体的基本元素"),
    ("linetypes", "linewidth", "prereq", "先分线型，再定线宽"),
    ("linetypes", "linedraw", "prereq", "图线画法规定以线型分类为基础"),
    ("linetypes", "wavyline", "prereq", "波浪线是图线种类之一"),
    ("dim4", "dimnum", "prereq", "尺寸数字是四要素之一"),
    ("dim4", "dimlayout", "prereq", "尺寸布置是在四要素齐全后的清晰化处理"),
    ("dim4", "dimcircle", "prereq", "圆的尺寸注法是四要素在圆上的具体应用"),
    ("dimnum", "slopetaper", "prereq", "斜度、锥度用 1:n 形式标注，需先掌握尺寸数字与符号"),
    ("arcconnect", "lineseg", "prereq", "线段分析中连接线段靠圆弧连接的相切关系定形"),
    ("dimnum", "lineseg", "prereq", "线段分析要先会读定形、定位尺寸"),
    ("linetypes", "hatch", "prereq", "剖面线是细实线的一种具体用途"),
    ("wavyline", "local_section", "prereq", "局部剖的分界线用波浪线"),
    ("thread_five", "thread_type", "prereq", "五要素确定后才能按牙型和用途把螺纹分类"),
    ("thread_five", "thread_draw", "prereq", "规定画法要与五要素（大径、小径、螺距）对应"),
    ("thread_five", "thread_mark", "prereq", "标记的组成正是五要素加公差带与旋合长度"),
    ("thread_draw", "thread_blind", "prereq", "不通孔内螺纹的画法是螺纹画法的难点"),
    ("thread_draw", "thread_error", "prereq", "改错题以规定画法为判据"),
    ("thread_five", "fastener", "prereq", "紧固件的规格都用螺纹标记表示"),
    ("thread_mark", "fastener", "prereq", "读紧固件标记要先会读螺纹标记"),
    ("fastener", "proportional", "prereq", "紧固件连接图用比例画法绘制"),
    ("proportional", "bolt_connect", "prereq", "螺栓连接按比例画法作图"),
    ("proportional", "stud_connect", "prereq", "双头螺柱连接按比例画法作图"),
    ("proportional", "screw_connect", "prereq", "螺钉连接按比例画法作图"),
    ("bolt_connect", "connect_error", "prereq", "连接改错题覆盖三种连接画法"),
    ("stud_connect", "connect_error", "prereq", "双头螺柱旋入端是改错题高频点"),
    ("screw_connect", "connect_error", "prereq", "螺钉连接的螺纹终止线位置是高频错误"),
    ("fastener", "key_connect", "prereq", "键与螺纹紧固件同属标准件，先懂标准件表达习惯"),
    ("fastener", "pin_connect", "prereq", "销也属标准件，画法规则相同"),
    ("fastener", "bearing", "prereq", "滚动轴承是标准件，装配图中按不剖或简化画法"),
    ("fastener", "spring", "prereq", "弹簧属常用件，画法自有一套规定"),
    ("gear_param", "gear_formula", "prereq", "齿轮尺寸计算由模数与齿数推出"),
    ("gear_param", "gear_draw", "prereq", "齿轮画法要分出分度圆、齿顶圆、齿根圆"),
    ("gear_formula", "gear_draw", "prereq", "画齿轮前先算 d、da、df"),
    ("gear_draw", "gear_mesh", "prereq", "啮合画法以单个齿轮的画法为基础"),
    ("gear_param", "gear_mesh", "prereq", "啮合的中心距由模数与齿数决定"),
    ("surface_structure", "surface_symbol", "prereq", "先懂 Ra 参数，才能标注代号"),
    ("fit_basic", "deviation", "prereq", "偏差由极限尺寸减基本尺寸得到"),
    ("deviation", "tolerance_grade", "prereq", "标准公差与基本偏差共同确定公差带"),
    ("tolerance_grade", "base_hole", "prereq", "基孔制的基准孔基本偏差为 H"),
    ("tolerance_grade", "base_shaft", "prereq", "基轴制的基准轴基本偏差为 h"),
    ("base_hole", "clearance_fit", "prereq", "基准孔与不同轴配合得到各类配合"),
    ("base_hole", "interference_fit", "prereq", "过盈配合由基准孔与基本偏差靠上的轴形成"),
    ("base_hole", "transition_fit", "prereq", "过渡配合由基准孔与基本偏差中间的轴形成"),
    ("base_shaft", "clearance_fit", "prereq", "基轴制下改变孔的基本偏差得到间隙配合"),
    ("deviation", "fit_calc", "prereq", "配合计算要用上下偏差"),
    ("tolerance_grade", "fit_calc", "prereq", "极限偏差数值来自公差等级与基本偏差"),
    ("clearance_fit", "fit_type", "prereq", "判断配合类型要先认识三类配合"),
    ("interference_fit", "fit_type", "prereq", "判断配合类型要先认识三类配合"),
    ("transition_fit", "fit_type", "prereq", "判断配合类型要先认识三类配合"),
    ("base_hole", "fit_system", "prereq", "配合制度选用在基孔制、基轴制基础上进行"),
    ("base_shaft", "fit_system", "prereq", "特殊场合才改用基轴制"),
    ("fit_calc", "tolerance_mark", "prereq", "算出的极限偏差要按规则标注"),
    ("deviation", "geo_tolerance", "prereq", "先掌握尺寸公差的概念，再学几何公差（两者控制对象不同）"),
    ("part_content", "part_express", "prereq", "零件图第一项内容就是一组视图，需先定表达方案"),
    ("part_express", "part_datum", "prereq", "表达方案定下后才标注尺寸与基准"),
    ("part_datum", "part_dim_reasonable", "prereq", "合理标注以基准选择为前提"),
    ("part_dim_reasonable", "read_part", "prereq", "读零件图必须会分析尺寸基准与合理性"),
    ("surface_symbol", "read_part", "prereq", "读零件图要读懂表面结构代号"),
    ("geo_tolerance", "read_part", "prereq", "读零件图要读懂几何公差框格"),
    ("process_structure", "read_part", "prereq", "读零件图要识别退刀槽、倒角等工艺结构"),
    ("read_part", "draw_part", "prereq", "会读图才会按零件图要求画图"),
    ("combo_form", "part_content", "prereq", "零件图的视图表达建立在组合体表达之上"),
    ("six_views", "part_express", "prereq", "零件表达方案要从基本视图、剖视、断面中选取"),
    ("section_concept", "part_express", "prereq", "剖视是零件表达方案最常用的手段"),
    ("dim_class", "part_dim_reasonable", "prereq", "组合体尺寸分类是零件尺寸标注的起点"),
    ("dim_datum", "part_datum", "prereq", "零件图的尺寸基准概念由组合体尺寸基准延伸而来"),
    ("part_content", "assy_content", "prereq", "装配图由若干零件图对应的零件组成"),
    ("part_express", "assy_view", "prereq", "装配图表达方案以零件表达方法为基础"),
    ("assy_content", "assy_view", "prereq", "先明确装配图内容，再选表达方案"),
    ("assy_content", "assy_dim", "prereq", "装配图只注必要尺寸，须先知道内容范围"),
    ("assy_content", "assy_parts_list", "prereq", "序号与明细栏是装配图内容的组成部分"),
    ("assy_view", "assy_draw", "prereq", "表达方案确定后按装配图规定画法作图"),
    ("assy_draw", "assy_process", "prereq", "装配工艺结构要按规定画法表达"),
    ("assy_draw", "assy_read", "prereq", "读装配图必须熟悉规定画法"),
    ("assy_view", "assy_read", "prereq", "读装配图从分析视图开始"),
    ("assy_read", "assy_disassemble", "prereq", "读懂装配关系才能拆画零件图"),
    ("part_content", "assy_disassemble", "prereq", "拆画出的必须是合格的零件图"),
    ("part_datum", "assy_disassemble", "prereq", "拆画时要重选尺寸基准并移注尺寸"),
    ("tolerance_mark", "assy_disassemble", "prereq", "拆画时配合尺寸要查表注出极限偏差"),
    ("assy_read", "assy_common", "prereq", "读图方法要通过常见装配体反复练习"),
    ("assy_read", "assy_tech", "prereq", "读装配图要读懂技术要求"),
    ("assy_content", "assy_tech", "prereq", "技术要求是装配图内容之一"),
    ("assy_read", "assy_explode", "prereq", "爆炸图的装配顺序来自对装配关系的理解"),
    ("assy_draw", "assy_explode", "prereq", "爆炸图沿装配方向分离零件，需懂装配结构"),
    ("part_content", "assy_vs_part", "prereq", "比较两者差异要先明确零件图内容"),
    ("assy_content", "assy_vs_part", "prereq", "比较两者差异要先明确装配图内容"),

    # 跨链补边：把规范链各支线与主轴连通（转向轮廓线、尺寸注法、螺纹、齿轮）
    ("cylinder", "outline", "prereq", "圆柱的矩形轮廓就是转向轮廓线，先懂圆柱再抽象出概念"),
    ("cone", "outline", "prereq", "圆锥等腰三角形的两腰是转向轮廓线"),
    ("sphere", "outline", "prereq", "球的三视图圆就是三个方向的转向轮廓线"),
    ("outline", "curve_point", "prereq", "曲面取点必须先分清转向轮廓线与可见性分界"),
    ("linetypes", "dim4", "prereq", "尺寸线、尺寸界线都是细实线，先懂线型再学尺寸注法"),
    ("linetypes", "arcconnect", "prereq", "几何作图要求线型分明，作图前先掌握图线"),
    ("dimnum", "thread_mark", "prereq", "螺纹标记中的尺寸代号、公差带写法与尺寸数字规则同源"),
    ("hatch", "thread_draw", "prereq", "螺纹剖视中剖面线必须画到粗实线，前提是懂剖面线规则"),
    ("fastener", "gear_param", "prereq", "齿轮与紧固件同属标准件/常用件体系，规格都用标准代号表达"),
    ("gear_mesh", "assy_common", "prereq", "齿轮泵、减速器等常见装配体都含齿轮啮合，读图前先懂啮合"),
    ("fastener", "assy_draw", "prereq", "装配图中标准件纵剖按不剖画，需先掌握紧固件画法"),
    ("fastener", "assy_content", "prereq", "装配图中大量标准件，先懂紧固件表达才能读懂明细栏与装配关系"),
    ("tolerance_mark", "assy_content", "prereq", "配合代号是读懂装配关系的关键，须先掌握公差与配合标注"),

    # ===== contrast：易混淆对比（策划案点名的 6 组全部包含） =====
    ("section_line", "intersect_concept", "contrast", "截交线由平面截切立体产生，相贯线由两立体表面相交产生"),
    ("half_section", "local_section", "contrast", "半剖只能用于对称机件且以中心线分界，局部剖以波浪线分界、范围可大可小"),
    ("six_views", "section_concept", "contrast", "视图表达外形，剖视假想剖开后表达内部结构"),
    ("part_datum", "process_datum", "contrast", "尺寸（设计）基准按设计要求定，工艺基准按加工测量要求定，二者可能不重合"),
    ("base_hole", "base_shaft", "contrast", "基孔制固定 H 孔、改变轴；基轴制固定 h 轴、改变孔"),
    ("clearance_fit", "interference_fit", "contrast", "间隙配合孔在轴上方、始终有间隙；过盈配合孔在轴下方、始终有过盈"),
    ("full_section", "half_section", "contrast", "全剖牺牲外形表达，半剖用中心线分界兼顾内外"),
    ("full_section", "local_section", "contrast", "全剖完全剖开，局部剖只剖开一部分并用波浪线分界"),
    ("section_view", "section_concept", "contrast", "断面只画断面形状，剖视还要画剖切面后的可见轮廓"),
    ("removed_section", "coincident_section", "contrast", "移出断面画在视图外、轮廓粗实线；重合断面画在视图内、轮廓细实线"),
    ("step_section", "revolved_section", "contrast", "阶梯剖用平行剖切面，旋转剖用相交剖切面并需旋转后投射"),
    ("partial_view", "directional_view", "contrast", "局部视图只画局部并有断裂边界，向视图是完整基本视图的自由配置"),
    ("partial_view", "oblique_view", "contrast", "局部视图投向基本投影面，斜视图投向辅助投影面以得倾斜面实形"),
    ("six_views", "directional_view", "contrast", "按标准位置配置的基本视图不标注，向视图必须标注方向与名称"),
    ("iso_angle", "cavalier", "contrast", "正等测三轴 120°、系数均取 1；斜二测 90°/135°、Y 向取一半"),
    ("axo_concept", "three_views", "contrast", "轴测图直观但度量性差，三视图度量性好但需空间想象"),
    ("form_analysis", "line_face_analysis", "contrast", "形体分析法按基本体分块，线面分析法逐个面推敲，前者适合叠加式、后者适合切割式"),
    ("combo_add", "combo_cut", "contrast", "叠加式按分块拼合读图，切割式按原体切除读图"),
    ("make_up_third", "make_up_line", "contrast", "补第三视图要投影整个形体，补漏线只补局部缺失的图线"),
    ("make_up_third", "choice_third", "contrast", "补画第三视图自己画，选择题要从选项中排除矛盾项"),
    ("transition_fit", "clearance_fit", "contrast", "过渡配合公差带交叠、可能间隙可能过盈，间隙配合始终有间隙"),
    ("transition_fit", "interference_fit", "contrast", "过渡配合可能出现过盈也可能出现间隙，过盈配合始终有过盈"),
    ("bolt_connect", "stud_connect", "contrast", "螺栓连接两件都能钻通孔，双头螺柱用于一件较厚不便钻通孔"),
    ("bolt_connect", "screw_connect", "contrast", "螺栓连接用螺母紧固，螺钉连接直接旋入被连接件"),
    ("stud_connect", "screw_connect", "contrast", "双头螺柱上端用螺母，螺钉靠自身头部压紧且不常拆卸"),
    ("assy_content", "part_content", "contrast", "零件图表达单件并注全部尺寸，装配图表达装配关系且只注必要尺寸"),
    ("surface_structure", "geo_tolerance", "contrast", "表面结构控制表面微观不平度，几何公差控制形状、方向、位置误差"),
    ("deviation", "geo_tolerance", "contrast", "尺寸公差控制尺寸大小，几何公差控制形状位置，两者不可互相替代"),
    ("hatch", "rib_rule", "contrast", "一般剖切面画剖面线，但肋板纵剖时按不剖处理、不画剖面线"),
    ("thread_draw", "thread_blind", "contrast", "外螺纹大径粗实线，内螺纹小径粗实线，不通孔还要画出钻孔深度与锥顶"),

    # ===== compose：组成 / 包含 =====
    ("dim4", "dimnum", "compose", "尺寸四要素包含尺寸数字，本节按要素逐项展开"),
    ("section_concept", "hatch", "compose", "剖视图由剖面区域（剖面线）与剖切面后可见轮廓组成"),
    ("thread_mark", "thread_five", "compose", "螺纹标记由五要素信息加公差带、旋合长度、旋向组成"),
    ("combo_form", "combo_add", "compose", "组合体按形成方式包含叠加式"),
    ("combo_form", "combo_cut", "compose", "组合体按形成方式包含切割式"),
    ("tolerance_grade", "base_hole", "compose", "公差带由标准公差等级与基本偏差共同组成，基孔制即取 H"),
    ("tolerance_grade", "base_shaft", "compose", "基轴制即取基本偏差 h 与相应公差等级"),
    ("assy_content", "assy_parts_list", "compose", "装配图内容包含序号与明细栏"),
    ("assy_content", "assy_dim", "compose", "装配图内容包含必要的五类尺寸"),
    ("part_content", "part_express", "compose", "零件图内容包含一组视图，即表达方案"),
    ("gear_formula", "gear_param", "compose", "齿轮尺寸计算以模数、齿数等参数为输入"),
    ("fit_calc", "deviation", "compose", "配合计算由上下偏差与配合公差公式组成"),

    # ===== cause：因果 / 推导 =====
    ("hidden_line", "section_concept", "cause", "虚线过多导致读图困难，因此引入剖视图"),
    ("line_general", "change_plane", "cause", "一般位置直线投影不反映实长，因此需要换面法"),
    ("surface_structure", "surface_symbol", "cause", "先确定 Ra 参数值，才能写出表面结构代号"),
    ("view_rule", "view_draw_step", "cause", "三等规律决定了画三视图必须按长对正、高平齐、宽相等布置"),
    ("section_line", "dim_avoid", "cause", "交线由基本体尺寸自然形成，所以不注交线尺寸"),
    ("dim_class", "dim_closed_chain", "cause", "尺寸分类标注时若首尾相接就会形成封闭链，必须留开口环"),
    ("tolerance_grade", "fit_system", "cause", "孔加工比轴困难，因此优先采用基孔制"),
    ("intersect_method", "intersect_special", "cause", "两曲面共轴或等径时相贯线退化为圆或椭圆"),
    ("section_concept", "rib_rule", "cause", "肋板是薄壁结构，纵向剖切时若画剖面线会被误认为实心"),
    ("part_datum", "part_dim_reasonable", "cause", "基准选择直接决定尺寸能否合理标注与测量"),
    ("tangent_flush", "combo_error", "cause", "相切处、共面处多画线是组合体最常见错误，故单列为易错点"),
    ("symmetry_draw", "half_section", "cause", "机件对称才能用半剖，对称是半剖成立的前提"),
    ("assy_read", "assy_disassemble", "cause", "只有读懂装配关系与配合性质，才可能正确拆画零件图"),
    ("axo_compare", "axo_choose", "cause", "轴测图与三视图的差异决定了不同场合该选哪种图样"),
]

rel_names = {"prereq": "前置依赖", "contrast": "易混淆对比", "compose": "组成包含", "cause": "因果推导"}
errors = []

# ---------- 校验节点 ----------
node_by_key = {}
rows = []
for i, (key, tier, label) in enumerate(NODES, start=1):
    if key not in KP:
        errors.append("节点 key 不存在于 kp_index: %s" % key)
        continue
    kp_id = KP[key]["kp_id"]
    if key in node_by_key:
        errors.append("节点 key 重复: %s" % key)
    nid = "KN-%03d" % i
    node_by_key[key] = nid
    rows.append({
        "id": nid,
        "kp_id": kp_id,
        "label": label,
        "tier": tier,
        "chapter": KP[key]["chapter"],
        "state": "未学",
    })

# ---------- 校验边 ----------
erows = []
seen = set()
rel_count = defaultdict(int)
adj = defaultdict(list)          # prereq 有向图
undirected = defaultdict(set)    # 全图无向，用于连通性统计
for src, dst, rel, note in EDGES:
    if src not in node_by_key:
        errors.append("边 source 不存在: %s" % src)
        continue
    if dst not in node_by_key:
        errors.append("边 target 不存在: %s" % dst)
        continue
    if src == dst:
        errors.append("自环: %s" % src)
        continue
    if rel not in rel_names:
        errors.append("非法 rel: %s" % rel)
        continue
    k = (src, dst, rel)
    if k in seen:
        errors.append("重复边: %s" % (k,))
        continue
    seen.add(k)
    rel_count[rel] += 1
    erows.append({
        "source": node_by_key[src],
        "target": node_by_key[dst],
        "rel": rel,
        "note": note,
    })
    if rel == "prereq":
        adj[node_by_key[src]].append(node_by_key[dst])
    undirected[node_by_key[src]].add(node_by_key[dst])
    undirected[node_by_key[dst]].add(node_by_key[src])

# ---------- 必备对比边 ----------
required = [
    ("section_line", "intersect_concept", "截交线↔相贯线"),
    ("half_section", "local_section", "局部剖↔半剖"),
    ("six_views", "section_concept", "视图↔剖视"),
    ("part_datum", "process_datum", "尺寸基准↔工艺基准"),
    ("base_hole", "base_shaft", "基孔制↔基轴制"),
    ("clearance_fit", "interference_fit", "间隙配合↔过盈配合"),
]
required_report = []
for a, b, name in required:
    ok = ((a, b, "contrast") in seen) or ((b, a, "contrast") in seen)
    required_report.append((name, ok))
    if not ok:
        errors.append("缺少必备对比边: %s" % name)

# ---------- prereq 可达性：投影基础 -> 装配图 ----------
start = node_by_key.get("proj_method")
goal = node_by_key.get("assy_content")
path = None
if start and goal:
    prev = {start: None}
    q = deque([start])
    while q:
        u = q.popleft()
        if u == goal:
            break
        for v in adj[u]:
            if v not in prev:
                prev[v] = u
                q.append(v)
    if goal in prev:
        path = []
        cur = goal
        while cur is not None:
            path.append(cur)
            cur = prev[cur]
        path.reverse()

id2label = {r["id"]: r["label"] for r in rows}
path_labels = [id2label[p] for p in (path or [])]

# ---------- 弱连通分量统计 ----------
comps = 0
visited = set()
for nid in [r["id"] for r in rows]:
    if nid in visited:
        continue
    comps += 1
    q = deque([nid])
    visited.add(nid)
    while q:
        u = q.popleft()
        for v in undirected[u]:
            if v not in visited:
                visited.add(v)
                q.append(v)

# ---------- 写出 ----------
out_nodes = os.path.normpath(os.path.join(HERE, "..", "nodes.jsonl"))
out_edges = os.path.normpath(os.path.join(HERE, "..", "edges.jsonl"))
with open(out_nodes, "w", encoding="utf-8", newline="\n") as f:
    for r in rows:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")
with open(out_edges, "w", encoding="utf-8", newline="\n") as f:
    for r in erows:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

tier_count = defaultdict(int)
for r in rows:
    tier_count[r["tier"]] += 1

print("节点 %d -> %s" % (len(rows), out_nodes))
print("边   %d -> %s" % (len(erows), out_edges))
print("tier 分布:", dict(tier_count))
print("rel 分布:", {rel_names[k]: v for k, v in rel_count.items()})
print("必备对比边:", [(n, "OK" if ok else "MISSING") for n, ok in required_report])
print("prereq 路径（投影基础 → 装配图）:", " → ".join(path_labels) if path else "不可达")
print("弱连通分量数:", comps)
print("errors:", len(errors))
for e in errors:
    print("  !", e)
