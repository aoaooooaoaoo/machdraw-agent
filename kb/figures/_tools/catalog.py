"""图目录：figures.jsonl 的唯一数据源（与 SVG 生成代码一一对应）。

chapter 字符串与 kb/knowledge/kp.jsonl 中的 chapter 完全一致；
kp_ids 全部取自 kp.jsonl 实际存在的编号（_tools/build.py 会校验，写错就报错）。
"""
from __future__ import annotations

M = "自绘"

CATALOG = [
    {
        "figure_id": "FIG-LINETYPE",
        "title": "图线线型对照表（六种图线）",
        "chapter": "第一章 制图的基本知识和基本技能",
        "kp_ids": ["KP-BASIC-005", "KP-BASIC-006", "KP-BASIC-007"],
        "structure_tags": ["图线", "线型", "线宽", "波浪线"],
        "caption": "同一张图上并列六种图线的线型样本与线宽关系：粗实线取 d、细线取 d/2，虚线、点画线、"
                   "波浪线、双点画线各按国标画法，右侧逐条列出各自用途。",
        "license": M,
        "source": "依据 GB/T 17450、GB/T 4457.4 自绘",
    },
    {
        "figure_id": "FIG-SANSHITU-BASE",
        "title": "三视图的形成与三等规律",
        "chapter": "第三章 点、直线和平面的投影",
        "kp_ids": ["KP-PROJ-004", "KP-PROJ-005"],
        "structure_tags": ["三视图", "长对正", "高平齐", "宽相等", "第一角投影"],
        "caption": "L 形块按第一角投影展开得到三个视图，蓝、红、绿三色虚线分别示出长对正、高平齐、宽相等；"
                   "绿线配合 45° 辅助线完成俯视图到左视图的宽度搬移。",
        "license": M,
        "source": "依据 GB/T 17451、GB/T 4458.1 自绘",
    },
    {
        "figure_id": "FIG-SANSHITU-EXAMPLE",
        "title": "组合体三视图示例（台阶 + 通孔 + 尺寸基准）",
        "chapter": "第五章 组合体的视图与形体构型",
        "kp_ids": ["KP-COMP-006", "KP-COMP-015", "KP-COMP-016"],
        "structure_tags": ["组合体", "三视图", "尺寸基准", "台阶", "通孔"],
        "caption": "带台阶与竖直通孔的底板，三视图按标准位置排布，底面、左端面、对称中心面分别作为高度、"
                   "长度、宽度基准，虚线表示被遮挡的通孔。",
        "license": M,
        "source": "依据 GB/T 4458.1、GB/T 4458.4 自绘",
    },
    {
        "figure_id": "FIG-LIUGESHITU",
        "title": "六个基本视图的配置（第一角）",
        "chapter": "第七章 机件的常用表达方法",
        "kp_ids": ["KP-EXPR-001", "KP-EXPR-002"],
        "structure_tags": ["基本视图", "第一角", "视图配置"],
        "caption": "第一角画法六个基本视图的展开位置：仰视图在上、俯视图在下、右视图在左、左视图在右、"
                   "后视图在左视图之右，并给出长对正、高平齐、宽相等的对应范围。",
        "license": M,
        "source": "依据 GB/T 17451 自绘",
    },
    {
        "figure_id": "FIG-POUSHI-QUAN",
        "title": "全剖视图（带内孔的圆筒）",
        "chapter": "第七章 机件的常用表达方法",
        "kp_ids": ["KP-EXPR-008", "KP-EXPR-009", "KP-EXPR-012"],
        "structure_tags": ["全剖视图", "剖面线", "剖切符号", "内孔"],
        "caption": "圆筒的法兰与筒体用通过轴线的平面完全剖开：外形视图里内孔画虚线，全剖视图里内孔轮廓改为"
                   "粗实线、空腔不画剖面线，俯视图用粗短画与箭头标出 A—A 剖切位置。",
        "license": M,
        "source": "依据 GB/T 4458.6、GB/T 4457.4 自绘",
    },
    {
        "figure_id": "FIG-POUSHI-BAN",
        "title": "半剖视图（对称零件）",
        "chapter": "第七章 机件的常用表达方法",
        "kp_ids": ["KP-EXPR-008", "KP-EXPR-010"],
        "structure_tags": ["半剖视图", "对称中心线", "虚线不画"],
        "caption": "对称法兰套筒以对称中心线为界，左半剖视、右半画视图：剖视侧孔壁加粗、画剖面线，"
                   "视图侧不画虚线，一个视图同时表达内形与外形。",
        "license": M,
        "source": "依据 GB/T 4458.6 自绘",
    },
    {
        "figure_id": "FIG-POUSHI-JUBU",
        "title": "局部剖视图（波浪线分界）",
        "chapter": "第七章 机件的常用表达方法",
        "kp_ids": ["KP-BASIC-007", "KP-EXPR-008", "KP-EXPR-011"],
        "structure_tags": ["局部剖视图", "波浪线", "断裂边界"],
        "caption": "平板中间的通孔用波浪线围出局部剖切范围：剖到的孔壁画粗实线、区域外仍按外形画虚线，"
                   "说明波浪线不能与轮廓线重合也不能画在空腔上。",
        "license": M,
        "source": "依据 GB/T 4458.6、GB/T 17450 自绘",
    },
    {
        "figure_id": "FIG-DUANMIAN",
        "title": "断面图与剖视图的区别",
        "chapter": "第七章 机件的常用表达方法",
        "kp_ids": ["KP-EXPR-019", "KP-EXPR-020", "KP-EXPR-022"],
        "structure_tags": ["断面图", "移出断面", "剖视图", "对照"],
        "caption": "同一零件、同一剖切位置、同一投射方向的两种表达：断面图只有断面形状，剖视图还要画出"
                   "剖切面后方可见的底板轮廓，区别一眼可见。",
        "license": M,
        "source": "依据 GB/T 4458.6 自绘",
    },
    {
        "figure_id": "FIG-POUMAINXIAN",
        "title": "相邻零件剖面线方向应相反",
        "chapter": "第七章 机件的常用表达方法",
        "kp_ids": ["KP-EXPR-008", "KP-ASSY-005"],
        "structure_tags": ["剖面线", "相邻零件", "装配画法", "45°"],
        "caption": "两个相邻零件同时被剖切时，剖面线分别画成 45° 与 135°，方向相反便于区分；同一零件在"
                   "各剖视图中的方向与间距必须一致。",
        "license": M,
        "source": "依据 GB/T 4457.4、GB/T 4458.2 自绘",
    },
    {
        "figure_id": "FIG-GONGCHA-DAI",
        "title": "公差带图（Φ30 H7/k6）",
        "chapter": "第九章 零件图",
        "kp_ids": ["KP-PART-008", "KP-PART-009", "KP-PART-021", "KP-PART-023"],
        "structure_tags": ["公差带", "零线", "ES/EI/es/ei", "过渡配合"],
        "caption": "Φ30 H7/k6 的公差带图：零线以上画出孔 H7（0～+21）与轴 k6（+2～+15），标出 ES/EI/es/ei "
                   "及最大间隙 +19、最大过盈 15。",
        "license": M,
        "source": "自绘；偏差值取自 apps/api GB/T 1800 引擎（结果与 GB/T 1800.1 一致）",
    },
    {
        "figure_id": "FIG-YUANHU-LIANJIE",
        "title": "圆弧连接步骤图（R10 连接两垂直直线）",
        "chapter": "第一章 制图的基本知识和基本技能",
        "kp_ids": ["KP-BASIC-016"],
        "structure_tags": ["圆弧连接", "求圆心", "切点", "相切"],
        "caption": "R10 圆弧连接两条互相垂直直线的三个步骤：作平行线求圆心、作垂线求切点、以圆心和半径"
                   "画弧，每步都在图上标出 O 与 T1、T2。",
        "license": M,
        "source": "依据 GB/T 4457.4 细实线作图规定自绘",
    },
    {
        "figure_id": "FIG-LUOWEN",
        "title": "螺纹的比例画法（外螺纹 / 内螺纹剖视）",
        "chapter": "第八章 螺纹、齿轮、常用标准件及其连接",
        "kp_ids": ["KP-STD-003", "KP-STD-006", "KP-STD-008"],
        "structure_tags": ["螺纹", "比例画法", "牙顶牙底", "3/4 圈"],
        "caption": "外螺纹与内螺纹剖视的比例画法对照：外螺纹牙顶 d 画粗实线、牙底 d₁=0.85d 画细实线，"
                   "端视图牙底圆约 3/4 圈；内螺纹牙顶 D₁ 粗、牙底 D 细。",
        "license": M,
        "source": "依据 GB/T 4459.1 自绘",
    },
    {
        "figure_id": "FIG-BIAOMIAN",
        "title": "表面结构代号（Ra）的组成与常用加工方法",
        "chapter": "第九章 零件图",
        "kp_ids": ["KP-PART-005", "KP-PART-006"],
        "structure_tags": ["表面结构", "Ra", "去材料", "加工方法"],
        "caption": "表面结构代号的组成：基本符号、去掉材料（加短横线）与不去掉材料（加小圆）的区分、"
                   "Ra 数值写在横线上方；右侧对照 Ra 0.4～12.5 的常用加工方法。",
        "license": M,
        "source": "依据 GB/T 131、GB/T 3505 自绘",
    },
    {
        "figure_id": "FIG-CHICUN-SIYAOSU",
        "title": "尺寸注法四要素（正确 / 错误对照）",
        "chapter": "第一章 制图的基本知识和基本技能",
        "kp_ids": ["KP-BASIC-009", "KP-BASIC-010", "KP-BASIC-011"],
        "structure_tags": ["尺寸注法", "尺寸界线", "尺寸线", "箭头", "尺寸数字"],
        "caption": "尺寸注法四要素在同一尺寸上的位置关系，并对照两种常见错误：尺寸数字被尺寸线穿过、"
                   "尺寸线画成粗实线。",
        "license": M,
        "source": "依据 GB/T 4458.4 自绘",
    },
    {
        "figure_id": "FIG-GONGCHA-PEIJIAN",
        "title": "三种配合的公差带对照（间隙 / 过渡 / 过盈）",
        "chapter": "第九章 零件图",
        "kp_ids": ["KP-PART-011", "KP-PART-021", "KP-PART-022", "KP-PART-023"],
        "structure_tags": ["配合", "间隙配合", "过渡配合", "过盈配合", "公差带"],
        "caption": "同一基本尺寸 Φ30 下三种配合的公差带对照：H7/g6 为间隙、H7/k6 为过渡、H7/s6 为过盈，"
                   "看孔带与轴带的相对位置即可判断配合性质。",
        "license": M,
        "source": "自绘；偏差值取自 apps/api GB/T 1800 引擎（结果与 GB/T 1800.1 一致）",
    },
]
