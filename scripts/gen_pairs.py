"""生成 8 组概念辨析对（fallback 版）：自包含 SVG + pairs.jsonl + _pairs_link_terms.json。

背景：pairs 是 concept 模块 comparison 画布的唯一数据源，属于集成关键路径。
本脚本用 app/plots/svg.line_chart 与自写示意图生成，保证：
  · 每张 SVG 自包含、viewBox、中文标注、A/B 两栏；
  · pairs.jsonl 字段严格按 SPEC 3.6；
  · 不覆盖已有同名文件（若 figures2 已产出，同名文件跳过，并在报告中列出）。

用法（在 apps/api 下）：
    .\.venv\Scripts\python.exe ..\..\scripts\gen_pairs.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from app.plots.svg import line_chart  # noqa: E402

OUT = ROOT / "kb" / "figures" / "pairs"
OUT.mkdir(parents=True, exist_ok=True)
LIMIT = 4
_SVGS: dict[str, str] = {}


def _lin(a: float, b: float, n: int = 60) -> list[float]:
    return [a + (b - a) * i / (n - 1) for i in range(n)]


def _logspace(a: float, b: float, n: int = 80) -> list[float]:
    la, lb = math.log10(a), math.log10(b)
    return [10 ** (la + (lb - la) * i / (n - 1)) for i in range(n)]


# ------------------------------------------------------------------ 1. 快群 vs 热群
def pair_spectrum() -> dict:
    E = _logspace(1e-3, 1e7, 90)

    def fast(e):  # 快谱堆：裂变谱为主
        return (e / 1.0) * math.exp(-e / 1.4) / 3.0 if e > 1e3 else 0.0

    def thermal(e):  # 热谱堆：热 Maxwell 峰 + 1/E 慢化区 + 裂变峰
        maxwell = 0.0
        if e < 5:
            maxwell = (e / 0.0253 ** 2) * math.exp(-e / 0.0253) * 0.012
        return maxwell + 0.004 + (0.02 if e > 1e3 else 0.0)

    fa = [[e, fast(e)] for e in E]
    th = [[e, thermal(e)] for e in E]
    svg = line_chart(
        [{"name": "热群（热谱堆，φ~1/E + Maxwell）", "points": th, "color": "#2f6fb0"},
         {"name": "快群（快谱堆，φ~裂变谱）", "points": fa, "color": "#b0642f"}],
        x_label="中子能量 E / eV（对数轴）", y_label="φ(E)（归一化）",
        title="辨析 1　快群 vs 热群：同一坐标下的两种谱形",
        x_log=True, width=980, height=620,
        note="依据教材 第5章 5.1~5.4 自绘；能谱峰位与量级为示意，参数按压水堆/快堆典型值归一。",
    )
    _SVGS["PAIR-SPECTRUM"] = svg
    return {
        "pair_id": "PAIR-SPECTRUM", "file": "pairs/PAIR-SPECTRUM.svg",
        "title": "快群 vs 热群", "module": "concept",
        "chapter": "第五章 中子能谱与群常数计算",
        "a": {"label": "A", "caption": "快群（E ≳ 0.1 MeV，快谱堆为主）", "正确性": "对比项"},
        "b": {"label": "B", "caption": "热群（E ≲ 1 eV，热谱堆为主）", "正确性": "对比项"},
        "differences": [
            {"no": 1, "name": "能量范围", "a_desc": "约 0.1~10 MeV，裂变谱峰在 ~2 MeV",
             "b_desc": "约 0~1 eV，Maxwell 峰在 ~0.025 eV（20 ℃）",
             "why": "裂变中子的初始能量在 MeV 量级，经慢化才进入 eV 以下；能谱峰位由慢化与热化平衡决定。"},
            {"no": 2, "name": "截面量级", "a_desc": "σ 多为 1~10 b，以弹性散射为主",
             "b_desc": "σ 可达 10²~10⁴ b，吸收与裂变显著",
             "why": "低能区 1/v 律使吸收截面按 1/√E 增大，热群是吸收/裂变发生的主要能区。"},
            {"no": 3, "name": "在堆内的角色", "a_desc": "决定泄漏与快裂变倍增（ε），影响燃料温度系数",
             "b_desc": "决定热中子利用系数 f 与热裂变，是功率的主要来源",
             "why": "四因子/六因子把两类中子的贡献分开：ε 归快群，f、η 归热群。"},
        ],
        "question": {"stem": "压水堆内绝大多数裂变发生在哪一群中子？判断依据是什么？",
                     "options": ["快群，因为裂变中子能量高", "热群，因为热中子截面大、通量密度高",
                                 "两群各占一半", "取决于控制棒位置"],
                     "answer_index": 1,
                     "explain": "热群通量密度比快群高 1~2 个量级，且 ²³⁵U 热裂变截面约 580 b，远大于快群；故热谱堆的裂变主要发生在热群。"},
        "license": "自绘", "source": "依据教材 第5章 5.1~5.4 自绘",
    }


# ------------------------------------------------------------------ 2. 氙平衡 vs 停堆碘坑
def pair_xenon() -> dict:
    t = _lin(0, 120, 120)
    eq = [[x, 1.0 * (1 - math.exp(-x / 12.0))] for x in t]
    pmax = 1.35
    peak_t = 9.5
    shut = []
    for x in t:
        if x <= peak_t:
            v = 1.0 + (pmax - 1.0) * (1 - math.exp(-x / 6.0))
        else:
            v = 1.0 + (pmax - 1.0) * math.exp(-(x - peak_t) / 30.0)
        shut.append([x, v])
    svg = line_chart(
        [{"name": "连续满功率运行：趋于平衡", "points": eq, "color": "#2f6fb0"},
         {"name": "满功率后突然停堆：碘坑/氙峰", "points": shut, "color": "#b0642f"}],
        x_label="时间 t / h", y_label="N_Xe / N_Xe(平衡)",
        title="辨析 2　氙平衡 vs 停堆碘坑：浓度-时间曲线",
        width=980, height=620,
        markers=[{"x": peak_t, "y": pmax, "label": "停堆后约 9~10 h 氙峰"}],
        note="依据教材 第6章 6.2.1 自绘；峰位与峰高按典型压水堆量级示意。",
    )
    _SVGS["PAIR-XENON"] = svg
    return {
        "pair_id": "PAIR-XENON", "file": "pairs/PAIR-XENON.svg",
        "title": "氙平衡 vs 停堆碘坑", "module": "concept",
        "chapter": "第六章 燃耗与中毒",
        "a": {"label": "A", "caption": "连续运行：碘氙趋于平衡", "正确性": "对比项"},
        "b": {"label": "B", "caption": "停堆后：碘继续衰变生成氙，出现碘坑", "正确性": "对比项"},
        "differences": [
            {"no": 1, "name": "控制方程", "a_desc": "dN_Xe/dt=0，产生=消失，得平衡浓度",
             "b_desc": "停堆后 Φ=0，Xe 只靠 ¹³⁵I 衰变补充，自身衰变消耗",
             "why": "停堆后中子吸收项消失，¹³⁵I（T½≈6.6 h）仍在生成 ¹³⁵Xe，导致浓度先升后降。"},
            {"no": 2, "name": "时间尺度", "a_desc": "启动后约 40~50 h 接近平衡",
             "b_desc": "停堆后约 9~10 h 达峰值（碘坑最深）",
             "why": "峰值时刻由 I 的衰变常数与 Xe 的消耗共同决定，≈ln(λ_Xe/λ_I)/(λ_Xe−λ_I)。"},
            {"no": 3, "name": "工程含义", "a_desc": "决定稳态氙反应性惩罚（约 −2~−3 %Δk/k）",
             "b_desc": "决定停堆后能否立即再启动；碘坑期间需等待或提棒",
             "why": "碘坑深度与持续时间是换料/再启动窗口的关键约束。"},
        ],
        "question": {"stem": "为什么反应堆停堆后反而可能出现'氙毒加深'？",
                     "options": ["停堆后温度降低使截面增大", "停堆后 ¹³⁵I 继续衰变生成 ¹³⁵Xe，而氙只能靠自身衰变消失",
                                 "停堆后控制棒拔出引入正反应性", "停堆后中子通量升高"],
                     "answer_index": 1,
                     "explain": "停堆后 Φ≈0，¹³⁵Xe 的中子吸收消失，但 ¹³⁵I 仍以 6.6 h 半衰期生成氙，故氙浓度先升后降，形成碘坑。"},
        "license": "自绘", "source": "依据教材 第6章 6.2.1 自绘",
    }


# ------------------------------------------------------------------ 3. 负 vs 正温度系数
def pair_tempcoef() -> dict:
    T = _lin(300, 900, 70)
    neg = [[x, -1.0e-4 * (x - 300) * 100] for x in T]   # pcm
    pos = [[x, +0.5e-4 * (x - 300) * 100] for x in T]
    svg = line_chart(
        [{"name": "负温度系数：T↑ → ρ↓（稳定）", "points": neg, "color": "#2f6fb0"},
         {"name": "正温度系数：T↑ → ρ↑（不稳定）", "points": pos, "color": "#b0642f"}],
        x_label="温度 T / K", y_label="反应性变化 Δρ / pcm",
        title="辨析 3　负温度系数 vs 正温度系数：反馈方向",
        width=980, height=620,
        note="依据教材 第7章 7.1 自绘；斜率只为示意方向，量级随堆型/燃耗变化。",
    )
    _SVGS["PAIR-TEMPCOEF"] = svg
    return {
        "pair_id": "PAIR-TEMPCOEF", "file": "pairs/PAIR-TEMPCOEF.svg",
        "title": "负温度系数 vs 正温度系数", "module": "concept",
        "chapter": "第七章 反应性系数与反应性控制",
        "a": {"label": "A", "caption": "α_T < 0（负反馈，压水堆设计目标）", "正确性": "对比项"},
        "b": {"label": "B", "caption": "α_T > 0（正反馈，需避免）", "正确性": "对比项"},
        "differences": [
            {"no": 1, "name": "反馈方向", "a_desc": "温度升高 → 反应性下降 → 功率回落",
             "b_desc": "温度升高 → 反应性上升 → 功率继续升高",
             "why": "负反馈把扰动拉回平衡，正反馈会放大扰动，是安全性的分水岭。"},
            {"no": 2, "name": "物理来源", "a_desc": "多普勒展宽使 p↓；欠慢化设计使慢化剂温度系数为负",
             "b_desc": "过慢化或高硼浓度可使慢化剂温度系数变正",
             "why": "水铀比在 k∞ 峰值左侧（欠慢化）时慢化剂温度系数为负；高硼会压低热中子利用系数，改变符号。"},
            {"no": 3, "name": "设计约束", "a_desc": "要求为负，但绝对值不能过大（否则稳定性差）",
             "b_desc": "不允许在正常运行区间出现", "why": "负得太多会导致功率振荡/控制困难；正系数是事故分析重点。"},
        ],
        "question": {"stem": "压水堆为什么要求慢化剂温度系数为负，且要设计成'欠慢化'？",
                     "options": ["欠慢化可提高富集度", "欠慢化使慢化剂温度升高时反应性下降，形成负反馈",
                                 "欠慢化可减少控制棒数量", "欠慢化可提高燃耗深度"],
                     "answer_index": 1,
                     "explain": "水铀比在 k∞ 峰值左侧（欠慢化）时，慢化剂温度升高→密度下降→慢化能力下降→共振吸收增加，净效应为负。"},
        "license": "自绘", "source": "依据教材 第7章 7.1 自绘",
    }


# ------------------------------------------------------------------ 4. 无 vs 有反射层
def pair_reflector() -> dict:
    a = 100.0
    xs = _lin(-a / 2, a / 2, 80)
    bare = [[x, math.cos(math.pi * x / a)] for x in xs]
    ref = []
    for x in xs:
        ax = a * 1.25
        core = math.cos(math.pi * x / ax) if abs(x) <= a / 2 else 0.0
        if abs(x) <= a / 2:
            ref.append([x, core])
        else:
            ref.append([x, 0.35 * math.exp(-(abs(x) - a / 2) / 8.0)])
    svg = line_chart(
        [{"name": "无反射层（裸堆）：边界处 φ→0", "points": bare, "color": "#b0642f"},
         {"name": "有反射层：堆芯外有反射通量，临界尺寸更小", "points": ref, "color": "#2f6fb0"}],
        x_label="径向位置 x / cm", y_label="中子通量密度 φ(x)（归一化）",
        title="辨析 4　无反射层 vs 有反射层：通量分布与反射层节省",
        width=980, height=620,
        markers=[{"x": -a / 2, "y": 0.0, "label": "裸堆外推边界"}, {"x": a / 2, "y": 0.0, "label": ""}],
        note="依据教材 第4章 4.2.3 自绘；曲线为示意，反射层内按指数衰减近似。",
    )
    _SVGS["PAIR-REFLECTOR"] = svg
    return {
        "pair_id": "PAIR-REFLECTOR", "file": "pairs/PAIR-REFLECTOR.svg",
        "title": "无反射层 vs 有反射层", "module": "concept",
        "chapter": "第四章 中子扩散理论与计算",
        "a": {"label": "A", "caption": "裸堆（真空边界，φ 在外推边界为零）", "正确性": "对比项"},
        "b": {"label": "B", "caption": "有反射层（堆芯外有反射通量，临界尺寸更小）", "正确性": "对比项"},
        "differences": [
            {"no": 1, "name": "边界条件", "a_desc": "外推边界上 φ=0", "b_desc": "堆芯-反射层界面 φ、J 连续，外侧真空边界",
             "why": "反射层把逃逸中子部分送回，等效边界外移，堆芯尺寸可减小。"},
            {"no": 2, "name": "临界尺寸", "a_desc": "同样材料下临界尺寸最大", "b_desc": "临界尺寸更小，差值即反射层节省 δ",
             "why": "反射层节省是工程上评价反射层效果的直接指标。"},
            {"no": 3, "name": "功率分布", "a_desc": "余弦分布，中心峰值明显", "b_desc": "反射层使边缘通量抬高、分布更平坦",
             "why": "展平功率分布可提高平均功率密度与安全裕量。"},
        ],
        "question": {"stem": "同样材料组成下，加反射层后临界尺寸会怎样变化？",
                     "options": ["变大", "变小", "不变", "取决于控制棒"],
                     "answer_index": 1,
                     "explain": "反射层把部分泄漏中子反射回堆芯，等效减少了泄漏，因此达到临界所需尺寸更小（反射层节省）。"},
        "license": "自绘", "source": "依据教材 第4章 4.2.3 自绘",
    }


# ------------------------------------------------------------------ 5. 扩散 vs 输运（示意图）
def pair_diff_transport() -> dict:
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 980 640">
<rect width="980" height="640" fill="#fbfaf7"/>
<text x="30" y="42" font-family="Microsoft YaHei, SimHei, sans-serif" font-size="24" fill="#1f2328">辨析 5　扩散理论 vs 输运理论：假设与适用边界</text>
<rect x="30" y="70" width="440" height="500" rx="12" fill="#eef4fb" stroke="#2f6fb0" stroke-width="2"/>
<text x="52" y="106" font-family="Microsoft YaHei" font-size="20" fill="#2f6fb0">A　扩散理论</text>
<text x="52" y="150" font-family="Microsoft YaHei" font-size="16" fill="#1f2328">核心假设：</text>
<text x="60" y="182" font-family="Microsoft YaHei" font-size="15" fill="#1f2328">① 介质弱吸收；② 实验室系散射各向同性</text>
<text x="60" y="210" font-family="Microsoft YaHei" font-size="15" fill="#1f2328">③ φ 空间变化缓慢；④ 远离强吸收体/源/边界</text>
<text x="52" y="252" font-family="Microsoft YaHei" font-size="16" fill="#1f2328">数学形式：</text>
<text x="60" y="284" font-family="Consolas, monospace" font-size="17" fill="#1f2328">J = −D∇φ，  D = λ_tr/3</text>
<text x="60" y="312" font-family="Consolas, monospace" font-size="17" fill="#1f2328">∇²φ − φ/L² + S/D = 0</text>
<text x="52" y="354" font-family="Microsoft YaHei" font-size="16" fill="#1f2328">适用：</text>
<text x="60" y="386" font-family="Microsoft YaHei" font-size="15" fill="#1f2328">大堆芯、远离边界/控制棒/强吸收体</text>
<text x="52" y="428" font-family="Microsoft YaHei" font-size="16" fill="#1f2328">优点：</text>
<text x="60" y="460" font-family="Microsoft YaHei" font-size="15" fill="#1f2328">方程少、可解析求解、计算量小</text>
<text x="52" y="502" font-family="Microsoft YaHei" font-size="16" fill="#c0392b">局限：</text>
<text x="60" y="532" font-family="Microsoft YaHei" font-size="15" fill="#c0392b">各向异性/强吸收/小尺寸时误差大</text>
<rect x="510" y="70" width="440" height="500" rx="12" fill="#fbf1ea" stroke="#b0642f" stroke-width="2"/>
<text x="532" y="106" font-family="Microsoft YaHei" font-size="20" fill="#b0642f">B　输运理论</text>
<text x="532" y="150" font-family="Microsoft YaHei" font-size="16" fill="#1f2328">核心对象：</text>
<text x="540" y="182" font-family="Microsoft YaHei" font-size="15" fill="#1f2328">中子角通量 φ(r,E,Ω)，保留方向信息</text>
<text x="532" y="224" font-family="Microsoft YaHei" font-size="16" fill="#1f2328">数学形式：</text>
<text x="540" y="256" font-family="Consolas, monospace" font-size="16" fill="#1f2328">Ω·∇φ + Σ_t φ = ∫Σ_s φ dΩ′ + S</text>
<text x="540" y="284" font-family="Microsoft YaHei" font-size="15" fill="#1f2328">（玻尔兹曼方程，无"弱吸收"近似）</text>
<text x="532" y="326" font-family="Microsoft YaHei" font-size="16" fill="#1f2328">适用：</text>
<text x="540" y="358" font-family="Microsoft YaHei" font-size="15" fill="#1f2328">小堆芯、强吸收体附近、屏蔽、控制棒</text>
<text x="532" y="400" font-family="Microsoft YaHei" font-size="16" fill="#1f2328">优点：</text>
<text x="540" y="432" font-family="Microsoft YaHei" font-size="15" fill="#1f2328">精度高，能处理各向异性与边界效应</text>
<text x="532" y="474" font-family="Microsoft YaHei" font-size="16" fill="#c0392b">代价：</text>
<text x="540" y="506" font-family="Microsoft YaHei" font-size="15" fill="#c0392b">维度高、需数值方法（SN/离散纵标、MC）</text>
<text x="30" y="608" font-family="Microsoft YaHei" font-size="14" fill="#7a8288">依据教材 第4章 4.3.1 自绘　·　扩散是输运方程在"弱吸收、各向同性、缓变"下的近似</text>
</svg>'''
    _SVGS["PAIR-DIFF-TRANSPORT"] = svg
    return {
        "pair_id": "PAIR-DIFF-TRANSPORT", "file": "pairs/PAIR-DIFF-TRANSPORT.svg",
        "title": "扩散理论 vs 输运理论", "module": "concept",
        "chapter": "第四章 中子扩散理论与计算",
        "a": {"label": "A", "caption": "扩散理论：J=−D∇φ，假设强", "正确性": "对比项"},
        "b": {"label": "B", "caption": "输运理论：保留角分布，精度高", "正确性": "对比项"},
        "differences": [
            {"no": 1, "name": "未知量", "a_desc": "标量通量 φ(r)", "b_desc": "角通量 φ(r,E,Ω)",
             "why": "扩散对方位角做积分并假设各向同性，输运保留方向信息。"},
            {"no": 2, "name": "适用条件", "a_desc": "弱吸收、各向同性散射、φ 缓变", "b_desc": "无弱吸收/各向同性假设",
             "why": "强吸收体（控制棒）附近、小尺寸堆芯必须用输运。"},
            {"no": 3, "name": "计算代价", "a_desc": "解析解/少群数值，快", "b_desc": "SN/离散纵标/蒙特卡洛，慢",
             "why": "工程上大堆芯用扩散，局部强吸收与屏蔽用输运。"},
        ],
        "question": {"stem": "在下列哪种情形必须优先使用输运理论而不是扩散理论？",
                     "options": ["大型压水堆堆芯的功率分布", "控制棒附近的通量分布", "均匀裸堆临界尺寸估算", "燃耗计算中的通量平均"],
                     "answer_index": 1,
                     "explain": "控制棒是强吸收体，扩散理论'弱吸收'假设失效，必须用输运（或等效的扩散系数修正）处理。"},
        "license": "自绘", "source": "依据教材 第4章 4.3.1 自绘",
    }


# ------------------------------------------------------------------ 6. 控制棒 vs 可溶硼
def pair_rod_boron() -> dict:
    s = _lin(0, 1, 60)
    rod_int = [[x, 100 * (0.5 - 0.5 * math.cos(math.pi * x))] for x in s]  # 积分价值 S 形
    boron = [[x, 100 * x] for x in s]
    svg = line_chart(
        [{"name": "控制棒：积分价值 S 形，微分价值中部最大", "points": rod_int, "color": "#2f6fb0"},
         {"name": "可溶硼：价值随浓度近似线性", "points": boron, "color": "#b0642f"}],
        x_label="插入深度 / 硼浓度（归一化）", y_label="反应性价值 / %（归一化）",
        title="辨析 6　控制棒 vs 可溶硼：价值曲线与用途",
        width=980, height=620,
        note="依据教材 第7章 7.4 自绘；棒价值取余弦近似（微分 ∝ sin²），硼价值近似线性。",
    )
    _SVGS["PAIR-ROD-BORON"] = svg
    return {
        "pair_id": "PAIR-ROD-BORON", "file": "pairs/PAIR-ROD-BORON.svg",
        "title": "控制棒 vs 可溶硼", "module": "concept",
        "chapter": "第七章 反应性系数与反应性控制",
        "a": {"label": "A", "caption": "控制棒：局部、快速、S 形价值", "正确性": "对比项"},
        "b": {"label": "B", "caption": "可溶硼：均匀、慢速、近线性", "正确性": "对比项"},
        "differences": [
            {"no": 1, "name": "空间效应", "a_desc": "局部扰动通量，引起功率畸变", "b_desc": "溶于冷却剂，全堆均匀",
             "why": "棒插入造成局部通量凹陷，硼浓度改变是整体效应。"},
            {"no": 2, "name": "响应速度", "a_desc": "机械动作，秒级", "b_desc": "靠调硼/稀释，小时级",
             "why": "棒用于快速功率调节与停堆；硼用于长期反应性补偿（燃耗、氙）。"},
            {"no": 3, "name": "价值曲线", "a_desc": "积分价值 S 形，微分价值在堆芯中部最大", "b_desc": "价值与浓度近似线性",
             "why": "棒价值取决于插入位置处的通量水平，中部通量最高。"},
        ],
        "question": {"stem": "为什么控制棒的微分价值在插入堆芯中部时最大？",
                     "options": ["中部温度最高", "中部中子通量密度最高，单位插入长度扰动最大",
                                 "中部材料密度最大", "中部控制棒直径最大"],
                     "answer_index": 1,
                     "explain": "棒价值 ∝ 插入位置的通量水平（扰动理论），堆芯中部 φ 最高，故单位插入长度的微分价值最大。"},
        "license": "自绘", "source": "依据教材 第7章 7.4 自绘",
    }


# ------------------------------------------------------------------ 7. 单群 vs 双群
def pair_group() -> dict:
    E = _logspace(1e-3, 1e7, 80)
    single = [[e, 1.0] for e in E]
    two = [[e, 4.0 if e < 0.625 else 1.0] for e in E]
    svg = line_chart(
        [{"name": "单群：一个平均能量、一个方程", "points": single, "color": "#b0642f"},
         {"name": "双群：热群通量高、快群通量低（分界 ~0.625 eV）", "points": two, "color": "#2f6fb0"}],
        x_label="中子能量 E / eV（对数轴）", y_label="相对通量（示意）",
        title="辨析 7　单群 vs 双群：能群划分与通量形状",
        x_log=True, width=980, height=620,
        note="依据教材 第4章 4.3 自绘；分界能量与通量比为示意，实际由群常数计算给出。",
    )
    _SVGS["PAIR-GROUP"] = svg
    return {
        "pair_id": "PAIR-GROUP", "file": "pairs/PAIR-GROUP.svg",
        "title": "单群 vs 双群", "module": "concept",
        "chapter": "第四章 中子扩散理论与计算",
        "a": {"label": "A", "caption": "单群：全能量一个平均截面", "正确性": "对比项"},
        "b": {"label": "B", "caption": "双群（或多群）：按能群分别建方程", "正确性": "对比项"},
        "differences": [
            {"no": 1, "name": "能群数", "a_desc": "1 群，所有中子按同一平均能量处理", "b_desc": "2 群（快/热）或更多群",
             "why": "截面随能量变化剧烈（共振、1/v），单群只能做粗估。"},
            {"no": 2, "name": "方程数", "a_desc": "一个扩散方程", "b_desc": "每个能群一个方程，群间有慢化/散射耦合项",
             "why": "群间耦合来自慢化，双群把慢化源显式写出。"},
            {"no": 3, "name": "精度/用途", "a_desc": "临界尺寸量级估算、教学推导", "b_desc": "堆芯设计、功率分布、燃耗计算",
             "why": "工程计算常用少群（2~4 群）扩散，靠群常数把能量信息压缩进去。"},
        ],
        "question": {"stem": "双群扩散方程相比单群，多出来的关键物理项是什么？",
                     "options": ["泄漏项", "快群到热群的慢化源项", "裂变源项", "吸收项"],
                     "answer_index": 1,
                     "explain": "双群把快群慢化到热群的中子作为热群方程的源项 Σ_s1→2 φ_1，这是单群没有的。"},
        "license": "自绘", "source": "依据教材 第4章 4.3 自绘",
    }


# ------------------------------------------------------------------ 8. OUT-IN vs 低泄漏
def pair_reload() -> dict:
    r = _lin(0, 1, 60)
    out_in = [[x, 1.0 + 0.55 * x ** 2] for x in r]
    low_leak = [[x, 1.15 - 0.35 * x ** 2] for x in r]
    svg = line_chart(
        [{"name": "OUT-IN：新料放外圈，外圈功率高、泄漏大", "points": out_in, "color": "#b0642f"},
         {"name": "低泄漏：新料放内圈，功率内移、泄漏小", "points": low_leak, "color": "#2f6fb0"}],
        x_label="归一化半径 r/R", y_label="相对功率密度",
        title="辨析 8　OUT-IN 换料 vs 低泄漏换料：功率分布",
        width=980, height=620,
        note="依据教材 第9章 9.3 自绘；为示意曲线，实际由堆芯计算给出。",
    )
    _SVGS["PAIR-RELOAD"] = svg
    return {
        "pair_id": "PAIR-RELOAD", "file": "pairs/PAIR-RELOAD.svg",
        "title": "OUT-IN 换料 vs 低泄漏换料", "module": "concept",
        "chapter": "第九章 堆芯核燃料管理",
        "a": {"label": "A", "caption": "OUT-IN：新料装外圈，功率外移", "正确性": "对比项"},
        "b": {"label": "B", "caption": "低泄漏：新料装内圈，功率内移", "正确性": "对比项"},
        "differences": [
            {"no": 1, "name": "新料位置", "a_desc": "外圈（高泄漏区）", "b_desc": "内圈（低泄漏区）",
             "why": "新料富集度高、反应性强，放外圈可压平功率但泄漏大。"},
            {"no": 2, "name": "泄漏与效率", "a_desc": "泄漏份额大，燃料利用率低", "b_desc": "泄漏小，燃料利用率高",
             "why": "低泄漏装料把高反应性区域移到低泄漏位置，减少中子浪费。"},
            {"no": 3, "name": "压力容器辐照", "a_desc": "外圈功率高 → 压力容器快中子注量高", "b_desc": "外圈功率低 → 辐照损伤小",
             "why": "压力容器寿命受快中子注量限制，低泄漏换料有利于延寿。"},
        ],
        "question": {"stem": "低泄漏换料把新燃料放在堆芯内圈，主要好处是什么？",
                     "options": ["提高控制棒价值", "减少中子泄漏、降低压力容器辐照",
                                 "简化换料操作", "提高硼浓度"],
                     "answer_index": 1,
                     "explain": "高反应性燃料放内圈使功率内移，减少外圈泄漏与压力容器快中子注量，提高燃料利用率并利于延寿。"},
        "license": "自绘", "source": "依据教材 第9章 9.3 自绘",
    }


BUILDERS = [pair_spectrum, pair_xenon, pair_tempcoef, pair_reflector,
            pair_diff_transport, pair_rod_boron, pair_group, pair_reload]


def main() -> int:
    pairs_path = ROOT / "kb" / "figures" / "pairs.jsonl"
    existing: dict[str, dict] = {}
    if pairs_path.exists():
        for ln in pairs_path.read_text(encoding="utf-8").splitlines():
            ln = ln.strip()
            if ln:
                try:
                    rec = json.loads(ln)
                    existing[rec.get("pair_id", "")] = rec
                except json.JSONDecodeError:
                    continue

    rows, terms = [], {}
    for fn in BUILDERS:
        pair = fn()
        pid = pair["pair_id"]
        path = ROOT / "kb" / "figures" / pair["file"]
        path.parent.mkdir(parents=True, exist_ok=True)
        svg = _SVGS.get(pid)
        if path.exists():
            print(f"[keep svg] {pair['file']} 已存在（保留已有版本）")
        elif svg:
            path.write_text(svg, encoding="utf-8")
            print(f"[ok] {pair['file']} {len(svg)} B")
        else:
            print(f"[warn] {pair['file']} 既无文件也无生成内容，跳过")
            continue
        # 已由其他人生成过元数据（如 figures2）则保留其描述，避免图文不一致
        row = existing.get(pid) or pair
        row.setdefault("kp_ids", [])
        rows.append(row)
        terms[pid] = [row["title"]] + [d["name"] for d in row["differences"]]

    pairs_path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
                          encoding="utf-8")
    (ROOT / "kb" / "figures" / "_pairs_link_terms.json").write_text(
        json.dumps(terms, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"写出 {pairs_path}（{len(rows)} 组）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
