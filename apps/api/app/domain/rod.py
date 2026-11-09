"""控制棒与可溶硼价值引擎（rod）。

教材出处
--------
* 控制棒价值 / 积分价值 / 微分价值定义：教材 第7章 7.4.1 节 p.121-123。
* “控制棒价值与当地中子通量密度平方（中子价值）成正比”、积分价值两端平缓、
  微分价值中部最大：教材 7.4.1 节 p.122-123（图 7-7、7-8）。
* 硼微分价值（单位硼浓度变化引起的反应性变化）与临界硼浓度定义：
  教材 7.4.3 节 p.125-126。
* 硼浓度换算（含 10% 吸收截面增量）：习题解答 v4.0 第2章【题2.8】（52.524 ppm）；
  教师版 2013 第2章同一题。
* 控制棒微分价值数值锚点：习题解答 v4.0 第7章【题7.3】
  （k_eff 1.023→1.019、插入 10 cm → 38.4 pcm/cm）。

模型假设（写清）
----------------
* 单群余弦通量近似 ``φ(z)∝cos(πz/H)``（教材 4.2.1 表4-2 裸堆基模），
  控制棒价值元 ``dρ∝φ²dz``，从而
  ``ρ(x)=ρ_总[x/H − sin(2πx/H)/(2π)]``、
  ``dρ/dx=(ρ_总/H)[1−cos(2πx/H)]``（x 为从堆芯一端插入的深度）。
  该式给出教材图 7-7/7-8 的形状：x=0、H 处微分为 0，x=H/2 处最大。
* 硼价值按给定 ``pcm/ppm`` 的线性价值处理（教材 7.4.3：硼微分价值随浓度变化，
  工程上在局部范围内线性化）。
"""
from __future__ import annotations

import math

N_A = 6.02214076e23
BARN = 1.0e-24

_REFS_ROD = [
    "教材 第7章 7.4.1 节 p.121-123（控制棒价值、积分/微分价值；图7-7/7-8）",
    "教材 第7章 7.4.3 节 p.125-126（硼微分价值、临界硼浓度）",
    "习题解答 v4.0 第7章【题7.3】（微分价值 38.4 pcm/cm）",
    "习题解答 v4.0 第2章【题2.8】（硼浓度 52.524 ppm）",
]


def _rho_from_k(k: float) -> float:
    return (float(k) - 1.0) / float(k)


def rod_total_worth(k_before: float, k_after: float) -> dict:
    """由插棒前后 k_eff 求控制棒总价值（pcm）。"""
    r1, r2 = _rho_from_k(k_before), _rho_from_k(k_after)
    worth = r1 - r2
    return {
        "inputs": {"k_before": float(k_before), "k_after": float(k_after)},
        "results": {"worth_pcm": worth * 1e5, "worth": worth,
                    "worth_percent": worth * 1e2},
        "steps": [
            f"ρ₁=(k₁−1)/k₁={r1:.6g}，ρ₂=(k₂−1)/k₂={r2:.6g}",
            f"控制棒价值 = ρ₁−ρ₂ = {worth * 1e5:.4g} pcm",
        ],
        "formulas": [{"step": "ρ_棒 = ρ_插前 − ρ_插后", "note": "教材 7.4.1 p.121"}],
        "refs": [_REFS_ROD[0]],
        "notes": [],
    }


def rod_differential_worth(k1: float, k2: float, dx: float) -> dict:
    """由两棒位 k_eff 求控制棒微分价值（pcm/单位长度）。

    习题解答 v4.0【题7.3】：k 1.023→1.019、Δx=10 cm → 38.4 pcm/cm。
    """
    k1, k2, dx = float(k1), float(k2), float(dx)
    if dx <= 0:
        raise ValueError("dx 必须为正")
    r1, r2 = _rho_from_k(k1), _rho_from_k(k2)
    worth = (r1 - r2) / dx
    return {
        "inputs": {"k1": k1, "k2": k2, "dx": dx},
        "results": {"differential_pcm_per_unit": worth * 1e5, "slot_worth_pcm": (r1 - r2) * 1e5},
        "steps": [
            f"Δρ = ρ₁−ρ₂ = {r1:.6g}−{r2:.6g} = {(r1 - r2):.6g}",
            f"微分价值 = Δρ/Δx = {worth * 1e5:.4g} pcm/单位长度",
        ],
        "formulas": [{"step": "dρ/dx = Δρ/Δx", "note": "教材 7.4.1 p.121 微分价值定义"}],
        "refs": [_REFS_ROD[2]],
        "notes": ["k 与 Δx 需同一长度单位；题7.3 为 10 cm → 38.4 pcm/cm。"],
    }


def rod_integral_worth(total_worth_pcm: float, insertion_fraction: float) -> dict:
    """余弦通量近似下的控制棒积分价值（pcm）。

    ``ρ(f)=ρ_总[f − sin(2πf)/(2π)]``，f=x/H∈[0,1] 为插入深度份额。
    f=0→0；f=1→ρ_总；f=0.5→ρ_总/2。
    """
    total = float(total_worth_pcm)
    f = float(insertion_fraction)
    if not (0.0 <= f <= 1.0):
        raise ValueError("insertion_fraction 必须在 [0,1]")
    rho = total * (f - math.sin(2.0 * math.pi * f) / (2.0 * math.pi))
    return {
        "inputs": {"total_worth_pcm": total, "insertion_fraction": f},
        "results": {"integral_worth_pcm": rho,
                    "fraction_of_total": rho / total if total else 0.0},
        "steps": [
            f"ρ(f) = ρ_总[f − sin(2πf)/(2π)]，f={f:g}",
            f"     = {rho:.6g} pcm（占总价值 {rho / total * 100 if total else 0:.4g}%）",
        ],
        "formulas": [
            {"step": "ρ(x)=ρ_总[x/H − sin(2πx/H)/(2π)]",
             "note": "φ∝cos(πz/H)、价值元∝φ² 积分；教材 7.4.1 p.122-123"},
        ],
        "refs": [_REFS_ROD[0]],
        "notes": ["余弦近似适合裸堆基模；真实堆芯需用三维扩散/输运计算。"],
    }


def rod_differential_value(total_worth_pcm: float, height: float,
                           insertion_fraction: float) -> dict:
    """余弦通量近似下控制棒微分价值（pcm/长度）。

    ``dρ/dx=(ρ_总/H)[1−cos(2πx/H)]``：两端为 0、中部最大（教材图 7-8）。
    """
    total = float(total_worth_pcm)
    H = float(height)
    f = float(insertion_fraction)
    if H <= 0:
        raise ValueError("堆芯高度必须为正")
    if not (0.0 <= f <= 1.0):
        raise ValueError("insertion_fraction 必须在 [0,1]")
    d = total / H * (1.0 - math.cos(2.0 * math.pi * f))
    return {
        "inputs": {"total_worth_pcm": total, "height": H, "insertion_fraction": f},
        "results": {"differential_pcm_per_unit": d,
                    "max_differential_pcm_per_unit": 2.0 * total / H},
        "steps": [
            f"dρ/dx = (ρ_总/H)[1−cos(2πf)]，f={f:g}",
            f"      = {d:.6g} pcm/单位长度（最大值 2ρ_总/H={2 * total / H:.6g}，在 f=0.5）",
        ],
        "formulas": [
            {"step": "dρ/dx=(ρ_总/H)[1−cos(2πx/H)]",
             "note": "余弦近似；教材 7.4.1 p.123 图7-8"},
        ],
        "refs": [_REFS_ROD[0]],
        "notes": ["微分价值最大值出现在堆芯中部（中子通量最大处）。"],
    }


def rod_worth_curve(total_worth_pcm: float, height: float,
                    n_points: int = 101) -> dict:
    """生成积分价值与微分价值随插入深度的曲线（供 plot 画布）。"""
    total, H = float(total_worth_pcm), float(height)
    n = int(n_points)
    if n < 2 or H <= 0:
        raise ValueError("n_points≥2 且 height>0")
    xs = [H * k / (n - 1) for k in range(n)]
    integral = []
    differential = []
    for x in xs:
        f = x / H
        integral.append([x, total * (f - math.sin(2.0 * math.pi * f) / (2.0 * math.pi))])
        differential.append([x, total / H * (1.0 - math.cos(2.0 * math.pi * f))])
    return {
        "inputs": {"total_worth_pcm": total, "height": H, "n_points": n},
        "results": {"total_worth_pcm": total, "height": H,
                    "max_differential_pcm_per_unit": 2.0 * total / H},
        "series": [
            {"name": "积分价值 (pcm)", "points": integral},
            {"name": "微分价值 (pcm/单位长度)", "points": differential},
        ],
        "steps": [
            f"ρ(x)=ρ_总[x/H−sin(2πx/H)/(2π)]；dρ/dx=(ρ_总/H)[1−cos(2πx/H)]",
            f"x∈[0,{H:g}]，取 {n} 点；最大微分价值 {2 * total / H:.6g} pcm/单位长度",
        ],
        "formulas": [{"step": "积分/微分价值余弦近似", "note": "教材 7.4.1 p.122-123"}],
        "refs": [_REFS_ROD[0]],
        "notes": ["积分价值曲线呈 S 形；微分价值中部最大、两端为 0。"],
    }


def boron_worth(delta_c_ppm: float, worth_per_ppm_pcm: float = -10.0) -> dict:
    """硼浓度变化引起的反应性变化（线性化）：Δρ = w·ΔC。

    习题解答 v4.0【题7.8】取硼价值 −0.010%Δk/k/ppm（= −10 pcm/ppm）。
    """
    dc = float(delta_c_ppm)
    w = float(worth_per_ppm_pcm)
    drho = w * dc
    return {
        "inputs": {"delta_c_ppm": dc, "worth_per_ppm_pcm": w},
        "results": {"delta_rho_pcm": drho, "delta_rho": drho * 1e-5,
                    "delta_rho_percent": drho * 1e-3},
        "steps": [
            f"Δρ = w·ΔC = {w:g} pcm/ppm × {dc:g} ppm = {drho:.4g} pcm",
        ],
        "formulas": [{"step": "Δρ_B = (dρ/dC_B)·ΔC_B", "note": "教材 7.4.3 p.125-126"}],
        "refs": [_REFS_ROD[1], _REFS_ROD[3]],
        "notes": ["硼微分价值为负且随硼浓度变化；工程上在局部范围线性化。"],
    }


def critical_boron(c0_ppm: float, excess_reactivity_pcm: float,
                   worth_per_ppm_pcm: float = -10.0) -> dict:
    """由初始硼浓度与需补偿的剩余反应性求临界硼浓度。

    ``Δρ_B + ρ_剩余 = 0 ⇒ C_crit = C₀ − ρ_剩余/w``。
    """
    c0 = float(c0_ppm)
    rho = float(excess_reactivity_pcm)
    w = float(worth_per_ppm_pcm)
    if w == 0:
        raise ValueError("硼价值不能为 0")
    c_crit = c0 - rho / w
    return {
        "inputs": {"c0_ppm": c0, "excess_reactivity_pcm": rho,
                   "worth_per_ppm_pcm": w},
        "results": {"critical_boron_ppm": c_crit, "delta_c_ppm": c_crit - c0},
        "steps": [
            f"需补偿 ρ_剩余={rho:.4g} pcm，硼价值 w={w:g} pcm/ppm",
            f"C_crit = C₀ − ρ_剩余/w = {c0:g} − ({rho:.4g})/({w:g}) = {c_crit:.6g} ppm",
        ],
        "formulas": [{"step": "C_crit = C₀ − ρ_excess / (dρ/dC_B)",
                      "note": "临界硼浓度定义 教材 7.4.3 p.126"}],
        "refs": [_REFS_ROD[1]],
        "notes": ["简化模型：假设硼价值为常数、无控制棒插入、可燃毒物状态固定。"],
    }


def boron_concentration_from_absorption(delta_sigma_a: float,
                                        sigma_b_b: float = 756.0,
                                        m_b: float = 10.82,
                                        rho_water: float = 1.0,
                                        n_a: float = N_A) -> dict:
    """由宏观吸收截面增量反求天然硼浓度 C_B（ppm，1 ppm=1 mg B/kg 水）。

    习题解答 v4.0【题2.8】：ΔΣa=0.1×0.0221 cm⁻¹、σ_硼酸=756 b、A_B=10.82
    → C_B=52.524 ppm（硼酸浓度≈300.2 ppm H₃BO₃）。
    """
    dsa = float(delta_sigma_a)
    sig = float(sigma_b_b) * BARN
    m_b = float(m_b)
    rho = float(rho_water)
    n_a = float(n_a)
    if dsa <= 0 or sig <= 0:
        raise ValueError("ΔΣa 与 σ 必须为正")
    n_b = dsa / sig  # cm^-3
    c_ppm = (n_b / n_a) * m_b / rho * 1e6
    return {
        "inputs": {"delta_sigma_a_cm1": dsa, "sigma_b_b": float(sigma_b_b),
                   "m_b": m_b, "rho_water": rho},
        "results": {"N_B_cm3": n_b, "boron_ppm": c_ppm},
        "steps": [
            f"N_B = ΔΣa/σ = {dsa:g}/({sigma_b_b:g}×10⁻²⁴) = {n_b:.6g} cm⁻³",
            f"C_B = (N_B/N_A)·M_B/ρ×10⁶ = {c_ppm:.6g} ppm",
        ],
        "formulas": [{"step": "C_B[ppm] = (N_B/N_A)·M_B/ρ_水×10⁶",
                      "note": "1 ppm = 1 mg 天然硼/kg 水；题2.8"}],
        "refs": [_REFS_ROD[3]],
        "notes": ["σ_硼酸=756 b 已按每分子 H₃BO₃ 计；天然硼原子量 A_B=10.82。"],
    }


__all__ = [
    "rod_total_worth", "rod_differential_worth", "rod_integral_worth",
    "rod_differential_value", "rod_worth_curve", "boron_worth",
    "critical_boron", "boron_concentration_from_absorption",
]
