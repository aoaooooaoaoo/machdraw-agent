"""裂变产物中毒引擎：碘-氙链、钷-钐链的平衡浓度与停堆/降功率暂态。

教材出处
--------
* I-135→Xe-135 简化燃耗链与燃耗方程：教材 第6章 6.2.1 节 p.101-107
  （图 6-7/6-8；式 6-6、6-7；启动解析解 6-9/6-10；平衡浓度 6-11/6-12；
  停堆解 6-13~6-18；碘坑/强迫停堆/允许停堆/最大碘坑时间/碘坑深度定义 p.106）。
* Pm-149→Sm-149 链：教材 6.2.2 节 p.107-109（式 6-19、6-20、6-24、6-25）。
* 中毒反应性当量（简易四因子模型）：教材 6.2 节 p.100-101（式 6-3~6-5）。
* 量级结论：GW 级堆平衡 Xe 中毒约 0.04~0.05（p.105）；平衡 Sm 中毒约 0.007
  且与通量无关（p.108）；热堆启动后约 2 天氙达平衡（p.105），钐约一周（p.108）。

核数据取值说明（重要）
----------------------
教材正文只给“135Xe 热中子吸收截面约 3×10⁶ b（p.102）”“149Sm 约 4×10⁴ b
（p.107）”等量级；衰变常数、裂变产额在教材中是公式图/未列表。本引擎采用
课程通用的 ENDF/B 评价数据（与教材量级一致）作为**可覆盖的默认参数**，
并在 ``notes`` 中逐项标注；调用方可传入教材/数据库精确值。
"""
from __future__ import annotations

import math

#: 碘-135：半衰期 6.7 h（ENDF/B-VII），λ=ln2/T½
I135 = {"name": "I-135", "half_life_s": 6.7 * 3600.0, "lambda": math.log(2) / (6.7 * 3600.0),
        "fission_yield": 0.0639, "sigma_a_b": 0.0}

#: 氙-135：半衰期 9.2 h；热中子吸收截面教材 p.102 约 3×10⁶ b
XE135 = {"name": "Xe-135", "half_life_s": 9.2 * 3600.0, "lambda": math.log(2) / (9.2 * 3600.0),
         "fission_yield": 0.00237, "sigma_a_b": 3.0e6}

#: 钷-149：半衰期 2.212 d
PM149 = {"name": "Pm-149", "half_life_s": 2.212 * 86400.0,
         "lambda": math.log(2) / (2.212 * 86400.0), "fission_yield": 0.0108,
         "sigma_a_b": 0.0}

#: 钐-149：稳定核素；热中子吸收截面教材 p.107 约 4×10⁴ b
SM149 = {"name": "Sm-149", "half_life_s": float("inf"), "lambda": 0.0,
         "fission_yield": 0.0, "sigma_a_b": 4.0e4}

#: 教学默认的压水堆栅元均匀化宏观截面（cm⁻¹），用于反应性当量换算。
#: 数值为典型 3% 富集度 UO₂ 栅元的教学取值；习题解答 v4.0 对 100%FP
#: 假设堆芯平均通量 3.0×10¹³ cm⁻²s⁻¹（第6章题6.7）。
SIGMA_F_DEFAULT = 0.28      # cm⁻¹
SIGMA_A_FUEL_DEFAULT = 0.35  # cm⁻¹
FLUX_DEFAULT = 3.0e13       # cm⁻² s⁻¹

_BARN = 1.0e-24  # cm²

_REFS_POISON = [
    "教材 第6章 6.2.1 节 p.101-107（碘-氙链、式6-6~6-18、碘坑定义）",
    "教材 第6章 6.2.2 节 p.107-109（钷-钐链、式6-19~6-25）",
    "教材 第6章 6.2 节 p.100-101（中毒反应性当量 式6-3~6-5）",
    "习题解答 v4.0 第6章【题6.8】【题6.9】（平衡浓度），【题6.7】通量假设",
]


def _sigma_cm2(sigma_b_b: float) -> float:
    return float(sigma_b_b) * _BARN


def _time_to_seconds(value: float, unit: str) -> float:
    u = (unit or "h").strip().lower()
    if u in ("s", "sec", "秒"):
        return float(value)
    if u in ("h", "hr", "小时"):
        return float(value) * 3600.0
    if u in ("d", "day", "天"):
        return float(value) * 86400.0
    raise ValueError(f"不支持的时间单位：{unit!r}（s/h/d）")


def _worth(n_xe: float, sigma_b_b: float, sigma_a_fuel: float) -> float:
    """毒物反应性当量（一阶近似 ρ≈−Σ_p/Σ_a,fuel）。"""
    sigma_p = _sigma_cm2(sigma_b_b) * n_xe
    return -sigma_p / float(sigma_a_fuel)


def xenon_equilibrium(flux: float = FLUX_DEFAULT,
                      sigma_f: float = SIGMA_F_DEFAULT,
                      sigma_a_fuel: float = SIGMA_A_FUEL_DEFAULT,
                      i135: dict = I135, xe135: dict = XE135) -> dict:
    """平衡碘/氙浓度与氙反应性当量（教材 式6-11、6-12，p.104-105）。

    ``N_I(∞)=γ_IΣfΦ/λ_I``；``N_Xe(∞)=(γ_I+γ_Xe)ΣfΦ/(λ_Xe+σ_XeΦ)``。
    """
    flux, sigma_f, sigma_a_fuel = float(flux), float(sigma_f), float(sigma_a_fuel)
    if flux < 0 or sigma_f <= 0 or sigma_a_fuel <= 0:
        raise ValueError("Φ≥0、Σf>0、Σa>0")
    lam_i, lam_xe = i135["lambda"], xe135["lambda"]
    n_i = i135["fission_yield"] * sigma_f * flux / lam_i
    n_xe = ((i135["fission_yield"] + xe135["fission_yield"]) * sigma_f * flux
            / (lam_xe + _sigma_cm2(xe135["sigma_a_b"]) * flux))
    rho = _worth(n_xe, xe135["sigma_a_b"], sigma_a_fuel)
    return {
        "inputs": {"flux": flux, "sigma_f": sigma_f, "sigma_a_fuel": sigma_a_fuel,
                   "sigma_xe_b": xe135["sigma_a_b"]},
        "results": {
            "N_I_eq": n_i, "N_Xe_eq": n_xe,
            "sigma_poison": _sigma_cm2(xe135["sigma_a_b"]) * n_xe,
            "rho_xe": rho, "rho_xe_pcm": rho * 1e5,
            "rho_xe_percent": rho * 1e2,
        },
        "steps": [
            f"N_I(∞) = γ_IΣfΦ/λ_I = {i135['fission_yield']:g}×{sigma_f:g}×{flux:g}/{lam_i:.4g} = {n_i:.6g}",
            f"N_Xe(∞) = (γ_I+γ_Xe)ΣfΦ/(λ_Xe+σ_XeΦ) = {n_xe:.6g}",
            f"ρ_Xe ≈ −σ_Xe N_Xe/Σa = {rho:.6g}（{rho * 1e5:.4g} pcm）",
        ],
        "formulas": [
            {"step": "N_I(∞) = γ_I Σf Φ / λ_I", "note": "教材 式(6-11) p.104"},
            {"step": "N_Xe(∞) = (γ_I+γ_Xe) Σf Φ / (λ_Xe+σ_XeΦ)", "note": "教材 式(6-12) p.104"},
            {"step": "ρ_Xe ≈ −σ_Xe N_Xe / Σa", "note": "教材 6.2 式(6-5) 一阶近似"},
        ],
        "refs": [_REFS_POISON[0], _REFS_POISON[2]],
        "notes": [
            "平衡氙浓度随功率（通量）增大而增大并趋于饱和（p.105）。",
            "GW 级压水堆平衡氙中毒约 0.04~0.05（教材 p.105）；",
            "默认 Σf=0.28 cm⁻¹、Σa=0.35 cm⁻¹、Φ=3×10¹³ cm⁻²s⁻¹ 时约 0.043。",
            "默认核数据：I-135 T½=6.7h、Xe-135 T½=9.2h、γ_I=0.0639、γ_Xe=0.00237、σ_Xe=3.0×10⁶ b。",
        ],
    }


def _n_i_irr(t: float, n_i0: float, a: float, lam_i: float) -> float:
    return n_i0 * math.exp(-lam_i * t) + a / lam_i * (1.0 - math.exp(-lam_i * t))


def _n_xe_irr(t: float, n_xe0: float, n_i0: float, a: float, gamma_xe_sf_flux: float,
              lam_i: float, lam_xe_eff: float) -> float:
    if abs(lam_xe_eff - lam_i) < 1e-18:
        lam_xe_eff = lam_i + 1e-18
    return (n_xe0 * math.exp(-lam_xe_eff * t)
            + (gamma_xe_sf_flux + a) / lam_xe_eff * (1.0 - math.exp(-lam_xe_eff * t))
            + (lam_i * n_i0 - a) * (math.exp(-lam_i * t) - math.exp(-lam_xe_eff * t))
            / (lam_xe_eff - lam_i))


def xenon_transient(flux: float = FLUX_DEFAULT, t_irr: float = 200.0, t_down: float = 60.0,
                    time_unit: str = "h", sigma_f: float = SIGMA_F_DEFAULT,
                    sigma_a_fuel: float = SIGMA_A_FUEL_DEFAULT,
                    start: str = "fresh", rho_ex0_pcm: float = 0.0,
                    n_points: int = 240, i135: dict = I135, xe135: dict = XE135) -> dict:
    """恒定通量照射 t_irr + 停堆 t_down 的碘/氙浓度与碘坑指标。

    解析解直接采用教材 6.2.1 的启动解（6-9/6-10）与停堆解（6-17/6-18）。
    返回曲线（时间单位 h）与碘坑指标：t_max、碘坑深度、强迫停堆时间、
    允许停堆时间（需要给定停堆前剩余反应性 ``rho_ex0_pcm``）。
    """
    flux, t_irr, t_down = float(flux), float(t_irr), float(t_down)
    if t_irr < 0 or t_down < 0:
        raise ValueError("t_irr、t_down 不能为负")
    t_irr_s = _time_to_seconds(t_irr, time_unit)
    t_down_s = _time_to_seconds(t_down, time_unit)
    lam_i, lam_xe = i135["lambda"], xe135["lambda"]
    a = i135["fission_yield"] * sigma_f * flux
    g = xe135["fission_yield"] * sigma_f * flux
    lam_xe_eff = lam_xe + _sigma_cm2(xe135["sigma_a_b"]) * flux

    eq = xenon_equilibrium(flux, sigma_f, sigma_a_fuel, i135, xe135)["results"]
    if str(start).lower().startswith("eq"):
        n_i0, n_xe0 = eq["N_I_eq"], eq["N_Xe_eq"]
    else:
        n_i0, n_xe0 = 0.0, 0.0

    # ---------------- 照射阶段
    n_pts_irr = max(2, n_points // 2)
    t_irr_list = [t_irr_s * k / (n_pts_irr - 1) for k in range(n_pts_irr)]
    irr_i = [_n_i_irr(t, n_i0, a, lam_i) for t in t_irr_list]
    irr_xe = [_n_xe_irr(t, n_xe0, n_i0, a, g, lam_i, lam_xe_eff) for t in t_irr_list]
    n_i_end, n_xe_end = irr_i[-1], irr_xe[-1]

    # ---------------- 停堆阶段（Φ=0）
    n_pts_down = max(2, n_points // 2)
    t_down_list = [t_down_s * k / (n_pts_down - 1) for k in range(n_pts_down)]
    dec_i = [n_i_end * math.exp(-lam_i * t) for t in t_down_list]
    dec_xe = [(n_xe_end * math.exp(-lam_xe * t))
              + (lam_i * n_i_end * (math.exp(-lam_i * t) - math.exp(-lam_xe * t))
                 / (lam_xe - lam_i) if abs(lam_xe - lam_i) > 1e-18 else 0.0)
              for t in t_down_list]

    # ---------------- 曲线上时间轴（小时）：照射段 + 停堆段
    t_irr_h = [t / 3600.0 for t in t_irr_list]
    t_down_h = [t_irr_s / 3600.0 + t / 3600.0 for t in t_down_list]
    time_h = t_irr_h + t_down_h
    n_i_all = irr_i + dec_i
    n_xe_all = irr_xe + dec_xe

    rho_xe0 = _worth(n_xe_end, xe135["sigma_a_b"], sigma_a_fuel)
    rho_xe_all = [_worth(v, xe135["sigma_a_b"], sigma_a_fuel) for v in n_xe_all]
    rho_ex0 = float(rho_ex0_pcm) * 1e-5
    rho_ex_all = [rho_ex0 + (r - rho_xe0) for r in rho_xe_all]

    # ---------------- 碘坑指标（停堆段）
    idx0 = n_pts_irr - 1
    down_t = t_down_h
    down_xe = dec_xe
    imax = max(range(len(down_xe)), key=lambda k: down_xe[k])
    t_max_h = down_t[imax] - t_irr_s / 3600.0
    pit_depth_pcm = (_worth(down_xe[imax], xe135["sigma_a_b"], sigma_a_fuel)
                     - rho_xe0) * 1e5

    rho_ex_down = [rho_ex0 + (_worth(v, xe135["sigma_a_b"], sigma_a_fuel) - rho_xe0)
                   for v in down_xe]
    # 找 ρ_ex=0 的交点（线性插值）
    zeros = []
    for k in range(1, len(rho_ex_down)):
        a0, a1 = rho_ex_down[k - 1], rho_ex_down[k]
        if a0 == 0:
            zeros.append(down_t[k - 1])
        elif a0 * a1 < 0:
            frac = a0 / (a0 - a1)
            zt = down_t[k - 1] + frac * (down_t[k] - down_t[k - 1])
            zeros.append(zt)
    zeros = [z - t_irr_s / 3600.0 for z in zeros]
    allowed = []
    forced = []
    if zeros:
        intervals = [0.0] + zeros + [down_t[-1] - t_irr_s / 3600.0]
        for k in range(0, len(intervals) - 1):
            ta, tb = intervals[k], intervals[k + 1]
            tm = 0.5 * (ta + tb)
            # 取该区间中点符号
            j = min(range(len(down_t)), key=lambda q: abs((down_t[q] - t_irr_s / 3600.0) - tm))
            if rho_ex_down[j] > 0:
                allowed.append((ta, tb))
            else:
                forced.append((ta, tb))

    series = [
        {"name": "N_I-135", "points": [[t, v] for t, v in zip(time_h, n_i_all)]},
        {"name": "N_Xe-135", "points": [[t, v] for t, v in zip(time_h, n_xe_all)]},
        {"name": "ρ_Xe (pcm)", "points": [[t, r * 1e5] for t, r in zip(time_h, rho_xe_all)]},
    ]
    return {
        "inputs": {
            "flux": flux, "t_irr": t_irr, "t_down": t_down, "time_unit": time_unit,
            "sigma_f": sigma_f, "sigma_a_fuel": sigma_a_fuel, "start": start,
            "rho_ex0_pcm": float(rho_ex0_pcm),
        },
        "results": {
            "time_h": time_h,
            "N_I": n_i_all,
            "N_Xe": n_xe_all,
            "rho_xe_pcm": [r * 1e5 for r in rho_xe_all],
            "shutdown_time_h": t_irr_s / 3600.0,
            "N_I_at_shutdown": n_i_end,
            "N_Xe_at_shutdown": n_xe_end,
            "rho_xe_eq_pcm": rho_xe0 * 1e5,
            "iodine_pit_depth_pcm": pit_depth_pcm,
            "max_pit_time_h": t_max_h,
            "rho_ex_zeros_h": zeros,
            "allowed_shutdown_intervals_h": allowed,
            "forced_shutdown_intervals_h": forced,
        },
        "series": series,
        "markers": [{"x": t_irr_s / 3600.0, "y": n_xe_end, "label": "停堆"}],
        "steps": [
            f"照射 {t_irr:g}{time_unit}（Φ={flux:g}），停堆 {t_down:g}{time_unit}",
            f"停堆时刻：N_I={n_i_end:.4g}，N_Xe={n_xe_end:.4g}，ρ_Xe={rho_xe0 * 1e5:.4g} pcm",
            f"最大碘坑时刻 t_max = {t_max_h:.4g} h；碘坑深度 Δρ = {pit_depth_pcm:.4g} pcm",
            f"ρ_ex 过零点（停堆后 h）：{[round(z, 3) for z in zeros]}",
        ],
        "formulas": [
            {"step": "N_I(t)=N_I0e^(−λ_I t)+γ_IΣfΦ/λ_I·(1−e^(−λ_I t))", "note": "教材 式(6-9)"},
            {"step": "N_Xe(t)=…（含 λ_I N_I 源项）", "note": "教材 式(6-10)"},
            {"step": "停堆：N_Xe(t)=N_Xe0e^(−λ_Xe t)+λ_I N_I0(e^(−λ_I t)−e^(−λ_Xe t))/(λ_Xe−λ_I)",
             "note": "教材 式(6-18)"},
        ],
        "refs": _REFS_POISON,
        "notes": [
            "碘坑指标依赖停堆前剩余反应性 ρ_ex0；ρ_ex0=0 时停堆即进入负反应性。",
            "碘坑深度 = ρ_Xe(t_max) − ρ_Xe(停堆时刻)，为负值（额外负反应性），报告取 pcm。",
            "光照/功率调节段用同一组解析解即可（教材 p.106-107）。",
        ],
    }


def samarium_equilibrium(flux: float = FLUX_DEFAULT,
                         sigma_f: float = SIGMA_F_DEFAULT,
                         sigma_a_fuel: float = SIGMA_A_FUEL_DEFAULT,
                         pm149: dict = PM149, sm149: dict = SM149) -> dict:
    """平衡钷/钐浓度与钐反应性当量（教材 式6-24、6-25，p.108）。"""
    flux, sigma_f, sigma_a_fuel = float(flux), float(sigma_f), float(sigma_a_fuel)
    n_pm = pm149["fission_yield"] * sigma_f * flux / pm149["lambda"]
    n_sm = pm149["fission_yield"] * sigma_f / _sigma_cm2(sm149["sigma_a_b"])
    rho = _worth(n_sm, sm149["sigma_a_b"], sigma_a_fuel)
    return {
        "inputs": {"flux": flux, "sigma_f": sigma_f, "sigma_a_fuel": sigma_a_fuel,
                   "sigma_sm_b": sm149["sigma_a_b"]},
        "results": {
            "N_Pm_eq": n_pm, "N_Sm_eq": n_sm,
            "sigma_poison": _sigma_cm2(sm149["sigma_a_b"]) * n_sm,
            "rho_sm": rho, "rho_sm_pcm": rho * 1e5,
        },
        "steps": [
            f"N_Pm(∞) = γ_PmΣfΦ/λ_Pm = {n_pm:.6g}",
            f"N_Sm(∞) = γ_PmΣf/σ_Sm = {n_sm:.6g}（与 Φ 无关）",
            f"ρ_Sm ≈ −σ_Sm N_Sm/Σa = {rho:.6g}（{rho * 1e5:.4g} pcm）",
        ],
        "formulas": [
            {"step": "N_Pm(∞) = γ_Pm Σf Φ / λ_Pm", "note": "教材 式(6-24)"},
            {"step": "N_Sm(∞) = γ_Pm Σf / σ_Sm", "note": "教材 式(6-25)"},
        ],
        "refs": [_REFS_POISON[1], _REFS_POISON[2]],
        "notes": [
            "平衡钐浓度与中子通量无关（教材 p.108 明确结论）；GW 级堆约 0.007。",
            "默认核数据：Pm-149 T½=2.212 d、γ_Pm=0.0108、σ_Sm=4.0×10⁴ b。",
        ],
    }


def samarium_transient(flux: float = FLUX_DEFAULT, t_irr: float = 200.0,
                       t_down: float = 60.0, time_unit: str = "h",
                       sigma_f: float = SIGMA_F_DEFAULT,
                       sigma_a_fuel: float = SIGMA_A_FUEL_DEFAULT,
                       start: str = "fresh",
                       n_points: int = 240, pm149: dict = PM149,
                       sm149: dict = SM149) -> dict:
    """恒定通量照射 + 停堆的 Pm/Sm 浓度暂态（教材 6.2.2 p.107-109）。"""
    flux, t_irr, t_down = float(flux), float(t_irr), float(t_down)
    if t_irr < 0 or t_down < 0:
        raise ValueError("t_irr、t_down 不能为负")
    t_irr_s = _time_to_seconds(t_irr, time_unit)
    t_down_s = _time_to_seconds(t_down, time_unit)
    lam_pm = pm149["lambda"]
    b = pm149["fission_yield"] * sigma_f * flux
    lam_sm = _sigma_cm2(sm149["sigma_a_b"]) * flux  # σ_Sm·Φ（吸收消失率）

    eq = samarium_equilibrium(flux, sigma_f, sigma_a_fuel, pm149, sm149)["results"]
    if str(start).lower().startswith("eq"):
        n_pm0, n_sm0 = eq["N_Pm_eq"], eq["N_Sm_eq"]
    else:
        n_pm0, n_sm0 = 0.0, 0.0

    n_pts_irr = max(2, n_points // 2)
    t_irr_list = [t_irr_s * k / (n_pts_irr - 1) for k in range(n_pts_irr)]

    def pm_irr(t: float) -> float:
        return n_pm0 * math.exp(-lam_pm * t) + b / lam_pm * (1.0 - math.exp(-lam_pm * t))

    def sm_irr(t: float) -> float:
        if abs(lam_sm - lam_pm) < 1e-18:
            lam_sm_ = lam_pm + 1e-18
        else:
            lam_sm_ = lam_sm
        return (n_sm0 * math.exp(-lam_sm_ * t)
                + b / lam_sm_ * (1.0 - math.exp(-lam_sm_ * t))
                + (lam_pm * n_pm0 - b) * (math.exp(-lam_pm * t) - math.exp(-lam_sm_ * t))
                / (lam_sm_ - lam_pm))

    irr_pm = [pm_irr(t) for t in t_irr_list]
    irr_sm = [sm_irr(t) for t in t_irr_list]
    n_pm_end, n_sm_end = irr_pm[-1], irr_sm[-1]

    n_pts_down = max(2, n_points // 2)
    t_down_list = [t_down_s * k / (n_pts_down - 1) for k in range(n_pts_down)]
    dec_pm = [n_pm_end * math.exp(-lam_pm * t) for t in t_down_list]
    dec_sm = [n_sm_end + n_pm_end * (1.0 - math.exp(-lam_pm * t)) for t in t_down_list]

    time_h = ([t / 3600.0 for t in t_irr_list]
              + [t_irr_s / 3600.0 + t / 3600.0 for t in t_down_list])
    pm_all = irr_pm + dec_pm
    sm_all = irr_sm + dec_sm
    rho_sm = [_worth(v, sm149["sigma_a_b"], sigma_a_fuel) for v in sm_all]

    series = [
        {"name": "N_Pm-149", "points": [[t, v] for t, v in zip(time_h, pm_all)]},
        {"name": "N_Sm-149", "points": [[t, v] for t, v in zip(time_h, sm_all)]},
        {"name": "ρ_Sm (pcm)", "points": [[t, r * 1e5] for t, r in zip(time_h, rho_sm)]},
    ]
    return {
        "inputs": {"flux": flux, "t_irr": t_irr, "t_down": t_down,
                   "time_unit": time_unit, "sigma_f": sigma_f,
                   "sigma_a_fuel": sigma_a_fuel, "start": start},
        "results": {
            "time_h": time_h, "N_Pm": pm_all, "N_Sm": sm_all,
            "rho_sm_pcm": [r * 1e5 for r in rho_sm],
            "N_Pm_at_shutdown": n_pm_end, "N_Sm_at_shutdown": n_sm_end,
            "rho_sm_eq_pcm": eq["rho_sm_pcm"],
            "N_Sm_after_full_decay": n_sm_end + n_pm_end,
            "shutdown_time_h": t_irr_s / 3600.0,
        },
        "series": series,
        "markers": [{"x": t_irr_s / 3600.0, "y": n_sm_end, "label": "停堆"}],
        "steps": [
            f"照射 {t_irr:g}{time_unit}，停堆 {t_down:g}{time_unit}",
            f"停堆时 N_Pm={n_pm_end:.4g}、N_Sm={n_sm_end:.4g}",
            f"钐平衡反应性当量 ρ_Sm={eq['rho_sm_pcm']:.4g} pcm（与通量无关）",
            f"停堆足够久后 N_Sm→N_Sm0+N_Pm0={n_sm_end + n_pm_end:.4g}",
        ],
        "formulas": [
            {"step": "dN_Pm/dt = γ_PmΣfΦ − λ_Pm N_Pm", "note": "教材 式(6-19)"},
            {"step": "dN_Sm/dt = λ_Pm N_Pm − σ_SmΦ N_Sm", "note": "教材 式(6-20)"},
            {"step": "N_Sm(∞) = γ_PmΣf/σ_Sm（与 Φ 无关）", "note": "教材 式(6-25)"},
        ],
        "refs": _REFS_POISON,
        "notes": ["钐为稳定核素，停堆后 Pm 全部衰变为 Sm，Sm 浓度只增不减（教材 p.108-109）。"],
    }


def reactivity_worth(xe_concentration: float, sigma_b_b: float = XE135["sigma_a_b"],
                     sigma_a_fuel: float = SIGMA_A_FUEL_DEFAULT) -> dict:
    """毒物反应性当量 ρ≈−σ_p N_p/Σa,fuel（教材 6.2 式6-5 一阶近似）。"""
    n = float(xe_concentration)
    rho = _worth(n, sigma_b_b, sigma_a_fuel)
    return {
        "inputs": {"N_poison": n, "sigma_b": sigma_b_b, "sigma_a_fuel": sigma_a_fuel},
        "results": {"rho": rho, "rho_pcm": rho * 1e5, "sigma_poison": _sigma_cm2(sigma_b_b) * n},
        "steps": [f"ρ = −σ_p N_p/Σa = {rho:.6g}（{rho * 1e5:.4g} pcm）"],
        "formulas": [{"step": "ρ_p ≈ −σ_p N_p / Σa,fuel", "note": "教材 6.2 式(6-5)"}],
        "refs": [_REFS_POISON[2]],
        "notes": ["一阶近似，忽略毒物对 Σa 分母的微小修正。"],
    }


__all__ = [
    "I135", "XE135", "PM149", "SM149",
    "SIGMA_F_DEFAULT", "SIGMA_A_FUEL_DEFAULT", "FLUX_DEFAULT",
    "xenon_equilibrium", "xenon_transient",
    "samarium_equilibrium", "samarium_transient", "reactivity_worth",
]
