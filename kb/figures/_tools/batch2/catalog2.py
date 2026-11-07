"""第二批图目录（figures.jsonl 追加行）。kp_id 已逐条核对 kb/knowledge/kp.jsonl。"""
from __future__ import annotations

M = "自绘"

CATALOG2 = [
    {
        "figure_id": "FIG2-ZHOUDUCE-ZHENGDENG",
        "title": "正等轴测图的形成与画法",
        "chapter": "第六章 轴测图",
        "kp_ids": ["KP-AXO-001", "KP-AXO-003", "KP-AXO-005"],
        "structure_tags": ["轴测图", "正等测", "轴间角", "轴向伸缩系数"],
        "caption": "轴测轴三根互成 120°，轴向系数 p=q=r≈0.82、简化取 1；长方体按定底面、竖高度、完成三步画出，"
                   "可见棱只画九条。",
        "license": M, "source": "依据 GB/T 4458.3 自绘",
    },
    {
        "figure_id": "FIG2-ZHOUDUCE-XIEER",
        "title": "斜二轴测图的轴间角与系数",
        "chapter": "第六章 轴测图",
        "kp_ids": ["KP-AXO-002", "KP-AXO-007"],
        "structure_tags": ["轴测图", "斜二测", "轴向伸缩系数"],
        "caption": "斜二测轴间角为 90°、135°、135°，X、Z 系数为 1、Y 系数为 0.5；同一长方体前面反映实形，"
                   "宽方向只画一半。",
        "license": M, "source": "依据 GB/T 4458.3 自绘",
    },
    {
        "figure_id": "FIG2-ZHOUDUCE-YUAN",
        "title": "圆的正等测与四心圆法",
        "chapter": "第六章 轴测图",
        "kp_ids": ["KP-AXO-004", "KP-AXO-006"],
        "structure_tags": ["轴测图", "椭圆", "四心圆法", "长轴短轴"],
        "caption": "圆的正等测是椭圆，长轴约 1.22d、短轴约 0.71d，四心圆法用四段圆弧近似；三个坐标面上椭圆"
                   "长轴方向各不相同。",
        "license": M, "source": "依据 GB/T 4458.3 自绘",
    },
    {
        "figure_id": "FIG2-DIAN-SANMIAN",
        "title": "点的三面投影与展开图",
        "chapter": "第三章 点、直线和平面的投影",
        "kp_ids": ["KP-PROJ-003", "KP-PROJ-004", "KP-PROJ-006", "KP-PROJ-007"],
        "structure_tags": ["点的投影", "三面投影体系", "长对正", "宽相等"],
        "caption": "点 A 向 V、H、W 三面投射得 a′、a、a″，展开后 a′a 竖对正、a′a″ 水平齐、a 与 a″ 的 y 相等，"
                   "靠 45° 线搬移。",
        "license": M, "source": "依据 GB/T 17451、GB/T 4458.1 自绘",
    },
    {
        "figure_id": "FIG2-XIAN-TYPICAL",
        "title": "直线的三面投影特征",
        "chapter": "第三章 点、直线和平面的投影",
        "kp_ids": ["KP-PROJ-009", "KP-PROJ-010", "KP-PROJ-011"],
        "structure_tags": ["直线投影", "一般位置直线", "投影面平行线", "投影面垂直线"],
        "caption": "三类直线的投影对照：一般位置三投影都小于实长；平行线一个投影反映实长；垂直线一个投影"
                   "积聚成点。",
        "license": M, "source": "依据 GB/T 17451、GB/T 4458.1 自绘",
    },
    {
        "figure_id": "FIG2-PINGMIAN-TYPICAL",
        "title": "平面的三面投影特征",
        "chapter": "第三章 点、直线和平面的投影",
        "kp_ids": ["KP-PROJ-016", "KP-PROJ-017", "KP-PROJ-018"],
        "structure_tags": ["平面投影", "一般位置平面", "投影面平行面", "投影面垂直面"],
        "caption": "三类平面的投影对照：一般位置三投影均为类似形；平行面一个投影反映真形；垂直面一个投影"
                   "积聚成斜线。",
        "license": M, "source": "依据 GB/T 17451、GB/T 4458.1 自绘",
    },
    {
        "figure_id": "FIG2-JIEJIAO-YUANZHU",
        "title": "圆柱截交线三例",
        "chapter": "第四章 立体的投影",
        "kp_ids": ["KP-SOLID-010", "KP-SOLID-011", "KP-SOLID-012"],
        "structure_tags": ["截交线", "圆柱", "椭圆", "积聚"],
        "caption": "圆柱被不同位置平面截切：垂直于轴线得圆、倾斜得椭圆、平行于轴线得矩形，三例并列标出"
                   "截交线的形状。",
        "license": M, "source": "依据 GB/T 4458.1、GB/T 16675.1 自绘",
    },
    {
        "figure_id": "FIG2-JIEJIAO-YUANZHUI-1",
        "title": "圆锥截交线（一）：圆与椭圆",
        "chapter": "第四章 立体的投影",
        "kp_ids": ["KP-SOLID-010", "KP-SOLID-013"],
        "structure_tags": ["截交线", "圆锥", "圆", "椭圆"],
        "caption": "截平面垂直轴线得圆、倾斜且 α>β 得椭圆；两条闭合截交线按解析法求点后真实画在锥面上，"
                   "可见段粗实线、不可见段虚线。",
        "license": M, "source": "依据 GB/T 4458.1 自绘",
    },
    {
        "figure_id": "FIG2-JIEJIAO-YUANZHUI-2",
        "title": "圆锥截交线（二）：抛物线、双曲线与三角形",
        "chapter": "第四章 立体的投影",
        "kp_ids": ["KP-SOLID-010", "KP-SOLID-013"],
        "structure_tags": ["截交线", "圆锥", "抛物线", "双曲线", "三角形"],
        "caption": "α=β 时抛物线开口跑出转向轮廓线，α<β 时得双曲线一支（另一支在对称锥面上画虚线），"
                   "过锥顶退化为两条素线围成的三角形。",
        "license": M, "source": "依据 GB/T 4458.1 自绘",
    },
    {
        "figure_id": "FIG2-XIANGUAN-JIANHUA",
        "title": "相贯线的简化画法",
        "chapter": "第四章 立体的投影",
        "kp_ids": ["KP-SOLID-018", "KP-SOLID-019"],
        "structure_tags": ["相贯线", "正交圆柱", "简化画法", "圆弧"],
        "caption": "正交异径圆柱的相贯线可用圆弧代替：圆弧半径取大圆柱半径、圆心落在小圆柱轴线上，三点共圆"
                   "即可画出。",
        "license": M, "source": "依据 GB/T 16675.1 自绘",
    },
    {
        "figure_id": "FIG2-ZUHETI-XINGTIFA",
        "title": "形体分析法读组合体",
        "chapter": "第五章 组合体的视图与形体构型",
        "kp_ids": ["KP-COMP-001", "KP-COMP-008"],
        "structure_tags": ["形体分析法", "组合体", "三视图"],
        "caption": "组合体用形体分析法拆成底板、圆柱、肋板三块，逐块对投影、定分界线，再合起来读三视图。",
        "license": M, "source": "依据 GB/T 4458.1 自绘",
    },
    {
        "figure_id": "FIG2-BUDI-SANSHITU",
        "title": "补画第三视图",
        "chapter": "第五章 组合体的视图与形体构型",
        "kp_ids": ["KP-COMP-011", "KP-COMP-012"],
        "structure_tags": ["补画第三视图", "读图", "三等规律"],
        "caption": "给出主视图与俯视图，左视图位置留虚线框提示补画；先做形体分析、逐块对投影，再按三等规律"
                   "补线。",
        "license": M, "source": "依据 GB/T 4458.1 自绘",
    },
    {
        "figure_id": "FIG2-CHICUN-JIZHUN",
        "title": "设计基准与工艺基准",
        "chapter": "第五章 组合体的视图与形体构型",
        "kp_ids": ["KP-COMP-015", "KP-COMP-016", "KP-PART-003"],
        "structure_tags": ["尺寸基准", "设计基准", "工艺基准", "定位尺寸"],
        "caption": "同一零件两种尺寸基准：设计基准与工艺基准；同一方向的定位尺寸必须从同一个基准出发，"
                   "避免尺寸链封闭。",
        "license": M, "source": "依据 GB/T 4458.4 自绘",
    },
    {
        "figure_id": "FIG2-JIANLIANJIE",
        "title": "平键连接的画法",
        "chapter": "第八章 螺纹、齿轮、常用标准件及其连接",
        "kp_ids": ["KP-STD-017"],
        "structure_tags": ["平键", "键连接", "装配画法", "剖面线"],
        "caption": "平键连接装配剖视：轴、轮毂、键同时被剖切，键两侧面为工作面接触、顶面留间隙，标出 b、h、"
                   "t、t1。",
        "license": M, "source": "依据 GB/T 4459.3、GB/T 1096 自绘",
    },
    {
        "figure_id": "FIG2-ZHOUCHENG-HUAFAA",
        "title": "滚动轴承的简化画法",
        "chapter": "第八章 螺纹、齿轮、常用标准件及其连接",
        "kp_ids": ["KP-STD-019"],
        "structure_tags": ["滚动轴承", "简化画法", "剖视", "d/D/B"],
        "caption": "滚动轴承剖视的简化画法：内外圈画矩形、滚动体画十字线、不画保持架，只画上半，标注 d、D、B。",
        "license": M, "source": "依据 GB/T 4459.7 自绘",
    },
    {
        "figure_id": "FIG2-CHILUN-NIEHE",
        "title": "圆柱齿轮啮合画法",
        "chapter": "第八章 螺纹、齿轮、常用标准件及其连接",
        "kp_ids": ["KP-STD-015", "KP-STD-016"],
        "structure_tags": ["齿轮啮合", "分度线", "齿顶线", "啮合区"],
        "caption": "两圆柱齿轮啮合画法：啮合区五条线——分度线重合为细点画线，齿顶线一实一虚，齿根线画粗实线。",
        "license": M, "source": "依据 GB/T 4459.2 自绘",
    },
    {
        "figure_id": "FIG2-AUTOCAD-JIEMIAN",
        "title": "AutoCAD 界面分区与常用命令",
        "chapter": "第二章 AutoCAD 基础",
        "kp_ids": ["KP-CAD-001", "KP-CAD-002", "KP-CAD-003", "KP-CAD-005"],
        "structure_tags": ["AutoCAD", "界面", "命令行", "快捷键"],
        "caption": "AutoCAD 界面分区：标题栏、菜单栏、功能区、绘图区、命令行与状态栏，附 L、C、O、TR、CO "
                   "常用命令。",
        "license": M, "source": "依据 AutoCAD 2024 界面自绘（示意图）",
    },
    {
        "figure_id": "FIG2-ZHUANGPEI-MINGXI",
        "title": "装配图的序号与明细栏",
        "chapter": "第十章 装配图",
        "kp_ids": ["KP-ASSY-004"],
        "structure_tags": ["装配图", "序号", "明细栏", "指引线"],
        "caption": "装配图右下角明细栏与零件序号：序号指引线从零件引出并编号，明细栏按序号自下而上一一对应。",
        "license": M, "source": "依据 GB/T 10609.2、GB/T 4458.2 自绘",
    },
    {
        "figure_id": "FIG2-LINGJIAN-WUBU",
        "title": "读零件图的五个步骤",
        "chapter": "第九章 零件图",
        "kp_ids": ["KP-PART-016", "KP-PART-017"],
        "structure_tags": ["零件图", "读图步骤", "尺寸基准", "技术要求"],
        "caption": "读零件图五步：看标题栏、分析视图、想形体、看尺寸基准、读技术要求与表面结构，五步卡片"
                   "用箭头串联。",
        "license": M, "source": "依据 GB/T 4458.4、GB/T 131 自绘",
    },
]
