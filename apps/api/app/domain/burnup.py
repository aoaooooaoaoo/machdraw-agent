"""燃耗、铀消耗、转换比与循环长度引擎（burnup）。

教材出处
--------
* 燃耗深度定义（单位质量燃料发出的能量，MWd/tU）：教材 第6章 6.1 节 p.98-99。
* 裂变能量 200 MeV/次、1 J = 3.12×10¹⁰ 次 ²³⁵U 裂变：教材 第2章 2.5.2 节 p.25-26。
* 燃耗引起的每日消耗量（含俘获-裂变比 α）：教材 第3章 3.1.3 节 p.33
  （式 3-15 及其后 1 MW → 1.23×10⁻³ kg/d、α=0.169 的算例）。
* 转换比定义：教材 第9章 9.4.1 节 p.154-155。
* 线性反应性模型（LRM）与循环长度：教材 第9章 9.2.1 节 p.145-147
  （式 9-9 及其后平衡循环关系）；习题解答 v4.0 第9章【题9.2】。

单位约定
--------
``power_mw`` 为热功率（MW），``mass_tu`` 为铀质量（tU），燃耗 MWd/tU，
循环长度 EFPD（等效满功率天）。
"""
from __future__ import annotations

#: 每次 ²³⁵U 裂变可利用能量（MeV），教材 2.5.2 p.25-26（表2-2）
ENERGY_PER_FISSION_MEV = 200.0
J_PER_MEV = 1.602176634e-13
N_A = 6.02214076e23
SECONDS_PER_DAY = 86400.0
M_U235 = 235.0439  # g/mol
M_U238 = 238.0508  # g/mol

_REFS_BURN = [
    "教材 第3章 3.1.3 节 p.33 式(3-15)（含俘获-裂变比 α 的消耗量；α=0.169 时 1 MW→1.23×10⁻³ kg/d）",
    "教材 第6章 6.1 节 p.98-99（燃耗深度 MWd/tU、卸料燃耗深度）",
    "教材 第9章 9.2.1 节 p.145-147（线性反应性模型与平衡循环）",
    "习题解答 v4.0：题2.5/2.6/2.7（铀消耗）、题6.4（铀装载量）、题9.2（线性反应性模型）",
]


def energy_per_fission(mev: float = ENERGY_PER_FISSION_MEV) -> dict:
    """单次裂变能量（J）：E = MeV × 1.602×10⁻¹³ J。"""
    mev = float(mev)
    e = mev * J_PER_MEV
    return {
        "inputs": {"mev": mev},
        "results": {"energy_j": e, "fissions_per_joule": 1.0 / e},
        "steps": [f"E = {mev:g} MeV × 1.602×10⁻¹³ J/MeV = {e:.6g} J",
                  f"1 J ≈ {1.0 / e:.4g} 次裂变"],
        "formulas": [{"step": "E_f = 200 MeV = 3.2×10⁻¹¹ J", "note": "教材 2.5.2 p.26"}],
        "refs": [_REFS_BURN[1]],
        "notes": ["工程近似取每次裂变可利用 200 MeV（教材 2.5.2 p.26）。"],
    }


def burnup_depth(power_mw: float, days: float, mass_tu: float) -> dict:
    """燃耗深度 BU=P·t/m（MWd/tU），教材 6.1 p.98-99。"""
    power_mw, days, mass_tu = float(power_mw), float(days), float(mass_tu)
    if mass_tu <= 0:
        raise ValueError("mass_tu 必须为正")
    bu = power_mw * days / mass_tu
    return {
        "inputs": {"power_mw": power_mw, "days": days, "mass_tu": mass_tu},
        "results": {"burnup_mwd_tu": bu, "energy_mwd": power_mw * days},
        "steps": [
            f"BU = P·t/m = {power_mw:g} MW × {days:g} d / {mass_tu:g} tU",
            f"   = {bu:.6g} MWd/tU",
        ],
        "formulas": [{"step": "BU = P·t / m_U", "note": "教材 6.1 p.98-99"}],
        "refs": [_REFS_BURN[1]],
        "notes": ["P 为热功率；t 为满功率运行天数（EFPD）。"],
    }


def burnup_from_energy(energy_mwd: float, mass_tu: float) -> dict:
    """由总能量（MWd）与铀装量（tU）求燃耗深度。"""
    energy_mwd, mass_tu = float(energy_mwd), float(mass_tu)
    if mass_tu <= 0:
        raise ValueError("mass_tu 必须为正")
    bu = energy_mwd / mass_tu
    return {
        "inputs": {"energy_mwd": energy_mwd, "mass_tu": mass_tu},
        "results": {"burnup_mwd_tu": bu},
        "steps": [f"BU = {energy_mwd:g} MWd / {mass_tu:g} tU = {bu:.6g} MWd/tU"],
        "formulas": [{"step": "BU = E / m_U", "note": "教材 6.1 p.98-99"}],
        "refs": [_REFS_BURN[1]],
        "notes": [],
    }


def u235_consumption(power_mw: float, days: float = 1.0, alpha: float = 0.169,
                     mev: float = ENERGY_PER_FISSION_MEV,
                     m_u235: float = M_U235) -> dict:
    """²³⁵U 消耗量：裂变量 + 辐射俘获量（(1+α) 修正）。

    ``m_裂变 = P·t·M/(E_f·N_A)``，``m_消耗 = (1+α)·m_裂变``。
    教材 3.1.3 p.33 式(3-15)：α=0.169、P=1 MW 时 1.23×10⁻³ kg/d。
    """
    power_mw, days, alpha, mev = float(power_mw), float(days), float(alpha), float(mev)
    if power_mw < 0 or days < 0 or alpha < 0:
        raise ValueError("P、t、α 不能为负")
    e_f = mev * J_PER_MEV
    energy_j = power_mw * 1e6 * days * SECONDS_PER_DAY
    fissions = energy_j / e_f
    mass_fission_kg = fissions * m_u235 / N_A / 1000.0
    mass_total_kg = mass_fission_kg * (1.0 + alpha)
    return {
        "inputs": {"power_mw": power_mw, "days": days, "alpha": alpha, "mev": mev},
        "results": {
            "energy_j": energy_j,
            "fissions": fissions,
            "fissioned_mass_kg": mass_fission_kg,
            "consumed_mass_kg": mass_total_kg,
            "consumed_mass_g": mass_total_kg * 1000.0,
            "consumed_mass_t": mass_total_kg / 1000.0,
        },
        "steps": [
            f"E = P·t = {power_mw:g} MW × {days:g} d = {energy_j:.6g} J",
            f"m_裂变 = E·M/(E_f·N_A) = {mass_fission_kg:.6g} kg",
            f"m_消耗 = (1+α)·m_裂变，α={alpha:g} → {mass_total_kg:.6g} kg",
        ],
        "formulas": [
            {"step": "m_消耗 = (1+α)·P·t·M/(E_f·N_A)", "note": "教材 3.1.3 式(3-15)"},
        ],
        "refs": [_REFS_BURN[0], _REFS_BURN[2]],
        "notes": [
            "α 为俘获-裂变比（教材 p.33 取 0.169 用于 ²³⁵U）；α=0 时只算裂变量。",
            "本函数 P 为热功率；电厂电功率需先除以效率。",
        ],
    }


def mass_for_energy(energy_kwh: float, alpha: float = 0.0,
                    mev: float = ENERGY_PER_FISSION_MEV) -> dict:
    """给定电能/热能（kW·h）求所需 ²³⁵U 质量（kg）。

    习题 v4.0 题2.5：1 kW·h（α=0）→ 4.390×10⁻⁸ kg。
    """
    energy_kwh = float(energy_kwh)
    energy_j = energy_kwh * 3.6e6
    e_f = float(mev) * J_PER_MEV
    fissions = energy_j / e_f
    mass_fission = fissions * M_U235 / N_A / 1000.0
    mass_total = mass_fission * (1.0 + float(alpha))
    return {
        "inputs": {"energy_kwh": energy_kwh, "alpha": alpha, "mev": mev},
        "results": {
            "energy_j": energy_j, "fissions": fissions,
            "fissioned_mass_kg": mass_fission, "consumed_mass_kg": mass_total,
            "fissioned_mass_g": mass_fission * 1e3,
        },
        "steps": [
            f"E = {energy_kwh:g} kW·h = {energy_j:.6g} J",
            f"m_裂变 = {mass_fission:.6g} kg；m_消耗 = {mass_total:.6g} kg",
        ],
        "formulas": [{"step": "m = E·M/(E_f·N_A)", "note": "教材 3.1.3 p.33；题2.5"}],
        "refs": [_REFS_BURN[0], "习题解答 v4.0 第2章【题2.5】"],
        "notes": [],
    }


def uranium_loading(power_e_mw: float, eta_e: float, load_factor: float,
                    burnup_mwd_tu: float, refuel_fraction: float = 1.0 / 3.0,
                    days: float = 365.0) -> dict:
    """由年发电量/换料策略估算铀装载量（tU）。

    习题解答 v4.0【题6.4】：Pe=1200 MW、ηe=0.30、负荷因子 0.8、
    BU=15000 MWd/tU、每年换 1/3 → 233.6 tU。
    """
    power_e_mw, eta_e, load_factor = float(power_e_mw), float(eta_e), float(load_factor)
    burnup, refuel_fraction, days = float(burnup_mwd_tu), float(refuel_fraction), float(days)
    if eta_e <= 0 or eta_e > 1 or burnup <= 0 or not (0 < refuel_fraction <= 1):
        raise ValueError("ηe∈(0,1]、BU>0、换料份额∈(0,1]")
    p_th_avg = power_e_mw * load_factor / eta_e
    annual_energy = p_th_avg * days
    batch_mass = annual_energy / burnup
    total_mass = batch_mass / refuel_fraction
    return {
        "inputs": {"power_e_mw": power_e_mw, "eta_e": eta_e, "load_factor": load_factor,
                   "burnup_mwd_tu": burnup, "refuel_fraction": refuel_fraction, "days": days},
        "results": {
            "P_th_avg_mw": p_th_avg,
            "annual_energy_mwd": annual_energy,
            "batch_mass_tu": batch_mass,
            "total_loading_tu": total_mass,
        },
        "steps": [
            f"平均热功率 = Pe·负荷因子/ηe = {power_e_mw:g}×{load_factor:g}/{eta_e:g} = {p_th_avg:.6g} MW",
            f"年发热量 = {p_th_avg:.6g} MW × {days:g} d = {annual_energy:.6g} MWd",
            f"每批换料量 = 年发热量/BU = {annual_energy:.6g}/{burnup:g} = {batch_mass:.6g} tU",
            f"总装载量 = 每批/换料份额 = {batch_mass:.6g}/{refuel_fraction:g} = {total_mass:.6g} tU",
        ],
        "formulas": [
            {"step": "m_U = (Pe·f/ηe·T)/BU ÷ (换料份额)", "note": "题6.4 平衡换料估算"},
        ],
        "refs": [_REFS_BURN[3]],
        "notes": ["假设平衡换料、平均卸料燃耗=给定 BU、负荷因子折算进平均热功率。"],
    }


def conversion_ratio(capture_in_fertile: float, absorption_in_fissile: float,
                     sigma_capture=None, sigma_absorption=None) -> dict:
    """转换比 CR = 增殖核素俘获数 / 易裂变核素吸收数（教材 9.4.1 p.154-155）。

    可传总反应率，或传截面（同种核密度下比值即截面比）。
    """
    if sigma_capture is not None and sigma_absorption is not None:
        num, den = float(sigma_capture), float(sigma_absorption)
    else:
        num, den = float(capture_in_fertile), float(absorption_in_fissile)
    if den <= 0:
        raise ValueError("易裂变核吸收率必须为正")
    cr = num / den
    kind = "增殖比 BR（CR>1）" if cr > 1 else "转换比 CR（CR≤1）"
    return {
        "inputs": {"numerator": num, "denominator": den},
        "results": {"CR": cr, "is_breeder": cr > 1, "kind": kind},
        "steps": [f"CR = {num:g}/{den:g} = {cr:.6g} → {kind}"],
        "formulas": [{"step": "CR = 新产生易裂变核数 / 消耗易裂变核数",
                      "note": "教材 9.4.1 p.154-155"}],
        "refs": [_REFS_BURN[2]],
        "notes": ["CR>1 称增殖比 BR；轻水堆 CR≈0.6，快堆 BR≈1.2~1.3（教材 p.155）。"],
    }


def cycle_length_from_burnup(burnup_mwd_tu: float, mass_tu: float,
                             power_mw: float) -> dict:
    """由循环燃耗求循环长度（EFPD）：T=B·m/P。"""
    bu, mass, power = float(burnup_mwd_tu), float(mass_tu), float(power_mw)
    if power <= 0:
        raise ValueError("功率必须为正")
    T = bu * mass / power
    return {
        "inputs": {"burnup_mwd_tu": bu, "mass_tu": mass, "power_mw": power},
        "results": {"cycle_length_efpd": T, "cycle_length_days": T},
        "steps": [f"T = BU·m/P = {bu:g}×{mass:g}/{power:g} = {T:.6g} EFPD"],
        "formulas": [{"step": "T = BU·m_U / P", "note": "燃耗深度定义反解"}],
        "refs": [_REFS_BURN[1]],
        "notes": [],
    }


def cycle_length_linear(rho0: float, alpha_per_mwd_tu: float, n_batches: int,
                        mass_tu: float, power_mw: float) -> dict:
    """线性反应性模型（LRM）下的循环燃耗、循环长度与卸料燃耗。

    教材 9.2.1 p.145-147；习题解答 v4.0【题9.2】：
    ``B_c = 2ρ0 / ((n+1)·α)``，卸料燃耗 ``B_d = n·B_c``，
    循环长度 ``T = B_c·m_U/P``（EFPD）。

    Args:
        rho0: 循环初堆芯剩余反应性（无量纲）。
        alpha_per_mwd_tu: 组件反应性随燃耗的斜率 α（1/(MWd/tU)）。
        n_batches: 批料数 n。
        mass_tu: 堆芯铀装量（tU）。
        power_mw: 热功率（MW）。
    """
    rho0, alpha = float(rho0), float(alpha_per_mwd_tu)
    n = int(n_batches)
    mass_tu, power_mw = float(mass_tu), float(power_mw)
    if n <= 0 or alpha <= 0 or power_mw <= 0 or mass_tu <= 0:
        raise ValueError("n>0、α>0、P>0、m>0")
    if rho0 <= 0:
        raise ValueError("初始剩余反应性 rho0 必须为正")
    Bc = 2.0 * rho0 / ((n + 1) * alpha)
    Bd = n * Bc
    T = Bc * mass_tu / power_mw
    return {
        "inputs": {"rho0": rho0, "alpha_per_mwd_tu": alpha, "n_batches": n,
                   "mass_tu": mass_tu, "power_mw": power_mw},
        "results": {
            "cycle_burnup_mwd_tu": Bc,
            "discharge_burnup_mwd_tu": Bd,
            "cycle_length_efpd": T,
            "reactivity_at_eoc": rho0 - alpha * Bc * (n + 1) / 2.0,
        },
        "steps": [
            f"B_c = 2ρ0/((n+1)α) = 2×{rho0:g}/(({n}+1)×{alpha:g}) = {Bc:.6g} MWd/tU",
            f"B_d = n·B_c = {n}×{Bc:.6g} = {Bd:.6g} MWd/tU",
            f"T = B_c·m/P = {Bc:.6g}×{mass_tu:g}/{power_mw:g} = {T:.6g} EFPD",
        ],
        "formulas": [
            {"step": "ρ_i(B)=ρ0,i − α_i·B", "note": "线性反应性模型 教材式(9-9)"},
            {"step": "B_c = 2ρ0/((n+1)α)", "note": "满功率循环末堆芯 ρ=0；题9.2"},
        ],
        "refs": [_REFS_BURN[2]],
        "notes": [
            "假设各批料反应性斜率 α 相同、功率份额相同、循环末堆芯反应性为 0。",
            "卸料燃耗 = 该批料在堆内停留 n 个循环的累积燃耗。",
        ],
    }


def burnup_percent(initial_fissile_mass_kg: float, consumed_fissile_mass_kg: float) -> dict:
    """以百分率表示的燃耗（消耗易裂变质量/初始易裂变质量）。"""
    m0, mc = float(initial_fissile_mass_kg), float(consumed_fissile_mass_kg)
    if m0 <= 0:
        raise ValueError("初始易裂变质量必须为正")
    pct = mc / m0 * 100.0
    return {
        "inputs": {"initial_fissile_mass_kg": m0, "consumed_fissile_mass_kg": mc},
        "results": {"burnup_percent": pct, "burnup_fraction": mc / m0},
        "steps": [f"燃耗 = {mc:g}/{m0:g} = {pct:.4g}%"],
        "formulas": [{"step": "燃耗% = 消耗易裂变质量 / 初始易裂变质量 ×100%",
                      "note": "教材 6.1 p.99"}],
        "refs": [_REFS_BURN[1]],
        "notes": [],
    }


__all__ = [
    "ENERGY_PER_FISSION_MEV", "J_PER_MEV", "N_A",
    "energy_per_fission", "burnup_depth", "burnup_from_energy",
    "u235_consumption", "mass_for_energy", "uranium_loading",
    "conversion_ratio", "cycle_length_from_burnup", "cycle_length_linear",
    "burnup_percent",
]
