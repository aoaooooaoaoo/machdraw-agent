"""中子能谱与群常数引擎（spectrum）。

教材出处
--------
* 裂变中子能谱（瞬发中子谱，平均能量约 2 MeV）：教材 第5章 5.1 节 p.79-80
  （式 5-4）。本引擎采用 U-235 的标准 Watt 谱形式
  ``χ(E)∝e^(−E/a)·sinh(√(bE))``（a=0.965 MeV、b=2.29 MeV⁻¹），
  并做数值归一化；其平均能量应≈2 MeV（与教材 p.79 一致，锚点测试已校核）。
* 无限均匀介质慢化谱（1/E 谱 / 费米谱）：教材 5.2 节 p.80-82。
* 热中子能谱（Maxwell-Boltzmann 谱、谱硬化）：教材 5.4 节 p.88-90。
* 压水堆合成能谱（裂变能区—1/E 慢化能区—热 Maxwell 区）：教材 5.4 节
  p.88-90、复习笔记 v0.4 第5章 p.16-17；习题解答 v4.0 第5章【题5.2】。
* 群平均截面：``σ_g=∫σ(E)φ(E)dE/∫φ(E)dE``；1/v 截面 + 1/E 谱的解析结果见
  习题解答 v4.0【补充2.1】。
* 中子温度：教材 5.4 节 p.88-90；习题解答 v4.0【例5.1】（T_M=535.5 K → T_n=613 K）。

单位约定
--------
能谱函数统一以能量 E（eV）为自变量，输出为“每 eV”的谱值（可整体归一化到 1）。
Watt 谱内部把 E 换成 MeV 后套用标准参数。
"""
from __future__ import annotations

import math

#: 玻尔兹曼常数（eV/K）
K_B_EV = 8.617333262e-5

#: 0.0253 eV 对应的中子温度（K）
T_0253 = 0.0253 / K_B_EV  # ≈293.6 K

#: 压水堆能区划分（eV）：热中子 E<1 eV、超热 1 eV~0.1 MeV、快中子 >0.1 MeV
#: （教材 第2章 2.1.1 p.14；复习笔记 p.16-17）
E_THERMAL_CUT = 1.0
E_FAST_CUT = 1.0e5

_J_PER_MEV = 1.602176634e-13  # 仅用于文档说明，不参与谱形
_REFS_SPEC = [
    "教材 第5章 5.1 节 p.79-80（裂变中子能谱，平均能量约 2 MeV）",
    "教材 第5章 5.2 节 p.80-82（无限均匀介质慢化谱，1/E 费米谱）",
    "教材 第5章 5.4 节 p.88-90（热中子 Maxwell 谱与谱硬化）",
    "习题解答 v4.0【补充2.1】（1/v 截面在 1/E 谱下的群平均解析式）",
    "习题解答 v4.0【例5.1】（中子温度公式，613 K）",
]


# ---------------------------------------------------------------- 数值积分
def _simpson(f, a: float, b: float, n: int = 2000) -> float:
    """复合 Simpson 积分（n 取偶数）。"""
    if b <= a:
        return 0.0
    n = int(n)
    if n % 2:
        n += 1
    h = (b - a) / n
    s = f(a) + f(b)
    for k in range(1, n):
        s += (4.0 if k % 2 else 2.0) * f(a + k * h)
    return s * h / 3.0


def _log_integral(f, a: float, b: float, n: int = 4000) -> float:
    """对 E∈[a,b] 积分 f(E)dE，用 E=e^u 的复合 Simpson（适合跨数量级谱）。"""
    if b <= a or a <= 0:
        return 0.0
    n = int(n)
    if n % 2:
        n += 1
    ua, ub = math.log(a), math.log(b)
    h = (ub - ua) / n

    def g(u: float) -> float:
        e = math.exp(u)
        return f(e) * e

    s = g(ua) + g(ub)
    for k in range(1, n):
        s += (4.0 if k % 2 else 2.0) * g(ua + k * h)
    return s * h / 3.0


# ---------------------------------------------------------------- 各能谱
def _watt_raw(E_mev: float, a: float, b: float) -> float:
    if E_mev <= 0:
        return 0.0
    return math.exp(-E_mev / a) * math.sinh(math.sqrt(b * E_mev))


_WATT_NORM_CACHE: dict[tuple[float, float, float], float] = {}


def watt_norm(a: float = 0.965, b: float = 2.29, e_max_mev: float = 20.0) -> float:
    """Watt 谱在 [0,e_max] 上的归一化积分（带缓存）。"""
    key = (float(a), float(b), float(e_max_mev))
    if key not in _WATT_NORM_CACHE:
        integral = _simpson(lambda e: _watt_raw(e, a, b), 0.0, e_max_mev, 4000)
        _WATT_NORM_CACHE[key] = integral
    return _WATT_NORM_CACHE[key]


def watt_fission_spectrum(E_ev: float, a: float = 0.965, b: float = 2.29,
                          normalized: bool = True) -> float:
    """U-235 Watt 裂变谱 χ(E)（每 MeV；E 以 eV 输入时换算为每 eV）。"""
    E_mev = float(E_ev) / 1e6
    val = _watt_raw(E_mev, float(a), float(b))
    if normalized:
        val /= watt_norm(a, b)
    return val / 1e6  # 每 eV


def fission_spectrum(E_ev: float) -> dict:
    """裂变中子能谱单点值 χ(E)（Watt 谱，教材 5.1 p.79-80 式5-4）。"""
    E_ev = float(E_ev)
    if E_ev < 0:
        raise ValueError("E 不能为负")
    chi = watt_fission_spectrum(E_ev)
    return {
        "inputs": {"E_ev": E_ev},
        "results": {"chi_per_eV": chi, "chi_per_MeV": chi * 1e6},
        "steps": [f"χ(E={E_ev:g} eV) = {chi:.6g} eV⁻¹（Watt 谱，归一化）"],
        "formulas": [
            {"step": "χ(E) ∝ e^(−E/a)·sinh(√(bE))", "note": "Watt 谱；教材 5.1 式(5-4) p.79"},
        ],
        "refs": [_REFS_SPEC[0]],
        "notes": ["a=0.965 MeV、b=2.29 MeV⁻¹（U-235 标准 Watt 参数）；平均能量≈2 MeV。"],
    }


def maxwellian(E_ev: float, T_k: float = T_0253) -> float:
    """热中子 Maxwell 通量谱 φ(E)=E/(kT)²·e^(−E/kT)（每 eV，已归一化）。"""
    E_ev, T_k = float(E_ev), float(T_k)
    if E_ev < 0:
        return 0.0
    kt = K_B_EV * T_k
    if kt <= 0:
        raise ValueError("T 必须为正")
    return E_ev / (kt * kt) * math.exp(-E_ev / kt)


def maxwellian_spectrum(E_ev: float, T_k: float = T_0253) -> dict:
    """热中子 Maxwell 谱单点值（教材 5.4 p.88-90）。"""
    E_ev, T_k = float(E_ev), float(T_k)
    val = maxwellian(E_ev, T_k)
    return {
        "inputs": {"E_ev": E_ev, "T_k": T_k},
        "results": {"phi_per_eV": val, "most_probable_energy_ev": K_B_EV * T_k},
        "steps": [
            f"kT = {K_B_EV * T_k:.6g} eV（对应最可几能量）",
            f"φ(E={E_ev:g} eV) = {val:.6g} eV⁻¹",
        ],
        "formulas": [
            {"step": "φ(E)=E/(kT)²·e^(−E/kT)", "note": "Maxwell 通量谱（归一化）"},
        ],
        "refs": [_REFS_SPEC[2]],
        "notes": ["谱峰在 E=kT；293.6 K 时 kT=0.0253 eV（教材 p.89-90）。"],
    }


def fermi_spectrum(E_ev: float, e_ref: float = 1.0) -> float:
    """慢化能区 1/E（费米）谱 φ(E)∝1/E（教材 5.2 p.80-82）。"""
    E_ev = float(E_ev)
    if E_ev <= 0:
        raise ValueError("E 必须为正")
    return float(e_ref) / E_ev


def pwr_spectrum(E_ev: float, T_k: float = T_0253) -> float:
    """压水堆合成能谱（热 Maxwell + 超热 1/E + 快 Watt，按份额加权）。

    教材 5.4 节 p.88-90、复习笔记 p.16-17 给出三能区结构；本引擎用
    “三个各自归一化的谱按 热 0.55 / 超热 0.30 / 快 0.15 加权”的**教学示意**
    合成（权重是可解释的典型压水堆通量份额，不是堆芯计算结果）。
    超热段取 0.1 eV~0.1 MeV，其 1/E 份额归一化。
    """
    E_ev, T_k = float(E_ev), float(T_k)
    if E_ev <= 0:
        return 0.0
    e1, e2 = 0.1, E_FAST_CUT
    thermal = maxwellian(E_ev, T_k)
    fast = watt_fission_spectrum(E_ev)
    if e1 <= E_ev <= e2:
        epi = 1.0 / (E_ev * math.log(e2 / e1))
    else:
        epi = 0.0
    return 0.55 * thermal + 0.30 * epi + 0.15 * fast


def pwr_norm(T_k: float = T_0253, e_min: float = 1e-4, e_max: float = 2e7) -> float:
    """压水堆合成谱归一化因子（加权合成时已归一化，返回 1.0）。"""
    return 1.0


def normalized_pwr_spectrum(E_ev: float, T_k: float = T_0253) -> float:
    """归一化压水堆合成谱（∫φdE≈1，E 以 eV 计）。"""
    return pwr_spectrum(E_ev, T_k)


_PWR_NORM_CACHE: dict[float, float] = {}


def pwr_norm(T_k: float = T_0253, e_min: float = 1e-4, e_max: float = 2e7) -> float:
    """压水堆合成谱在 [e_min,e_max] 上的归一化积分（带缓存）。"""
    key = float(T_k)
    if key not in _PWR_NORM_CACHE:
        _PWR_NORM_CACHE[key] = _log_integral(lambda e: pwr_spectrum(e, T_k), e_min, e_max, 6000)
    return _PWR_NORM_CACHE[key]


def normalized_pwr_spectrum(E_ev: float, T_k: float = T_0253) -> float:
    """归一化压水堆合成谱（∫φdE=1，E 以 eV 计）。"""
    return pwr_spectrum(E_ev, T_k) / pwr_norm(T_k)


def spectrum_curve(model: str = "watt", e_min_ev: float = 1e-3,
                   e_max_ev: float = 2e7, n_points: int = 320,
                   T_k: float = T_0253) -> dict:
    """生成能谱曲线点（对数能量网格）。

    Args:
        model: ``watt`` / ``maxwell`` / ``fermi`` / ``pwr``。
    """
    model = (model or "watt").strip().lower()
    if e_min_ev <= 0 or e_max_ev <= e_min_ev or n_points < 2:
        raise ValueError("需 0<e_min<e_max 且 n_points≥2")
    us = [math.log(e_min_ev) + (math.log(e_max_ev) - math.log(e_min_ev)) * k / (n_points - 1)
          for k in range(n_points)]
    points = []
    values = []
    if model == "watt":
        fn = lambda e: watt_fission_spectrum(e)
    elif model == "maxwell":
        fn = lambda e: maxwellian(e, T_k)
    elif model == "fermi":
        fn = lambda e: fermi_spectrum(e)
    elif model == "pwr":
        fn = lambda e: normalized_pwr_spectrum(e, T_k)
    else:
        raise ValueError(f"不支持的能谱模型：{model!r}（watt/maxwell/fermi/pwr）")
    for u in us:
        e = math.exp(u)
        v = fn(e)
        points.append([e, v])
        values.append(v)
    peak_idx = max(range(len(values)), key=lambda k: values[k])
    if model == "watt":
        num = _simpson(lambda e: e * fn(e), 0.0, 2e7, 4000)
        den = _simpson(fn, 0.0, 2e7, 4000)
    else:
        num = _log_integral(lambda e: e * fn(e), e_min_ev, e_max_ev, 4000)
        den = _log_integral(fn, e_min_ev, e_max_ev, 4000)
    mean_e = num / den if den else 0.0
    return {
        "inputs": {"model": model, "e_min_ev": e_min_ev, "e_max_ev": e_max_ev,
                   "n_points": n_points, "T_k": T_k},
        "results": {
            "peak_energy_ev": points[peak_idx][0],
            "peak_value": values[peak_idx],
            "mean_energy_ev": mean_e,
            "mean_energy_mev": mean_e / 1e6,
            "points": len(points),
        },
        "series": [{"name": {"watt": "Watt 裂变谱", "maxwell": "Maxwell 热谱",
                             "fermi": "Fermi 1/E 谱", "pwr": "压水堆合成谱"}[model],
                    "points": points}],
        "steps": [
            f"模型 {model}：在 [{e_min_ev:g}, {e_max_ev:g}] eV 对数网格上取 {n_points} 点",
            f"峰值能量 = {points[peak_idx][0]:.4g} eV；算术平均能量 ≈ {mean_e / 1e6:.4g} MeV",
        ],
        "formulas": [{"step": "χ(E)、φ(E) 定义式", "note": "教材 第5章 5.1/5.2/5.4"}],
        "refs": _REFS_SPEC,
        "notes": ["纵轴为每 eV 的谱值（可整体归一化）；Watt 谱拖尾到 ~10 MeV。"],
    }


def most_probable_energy(T_k: float = T_0253) -> dict:
    """Maxwell 通量谱最可几能量 E=kT（教材 p.89-90）。"""
    T_k = float(T_k)
    e = K_B_EV * T_k
    return {
        "inputs": {"T_k": T_k},
        "results": {"most_probable_energy_ev": e, "kT_ev": e},
        "steps": [f"E_最可几 = kT = {K_B_EV:g}×{T_k:g} = {e:.6g} eV"],
        "formulas": [{"step": "E_max = kT", "note": "Maxwell 通量谱峰位"}],
        "refs": [_REFS_SPEC[2]],
        "notes": ["293.6 K → 0.0253 eV（与教材“0.0253 eV 对应最可几速率”一致）。"],
    }


def neutron_temperature(T_m: float, sigma_a_0253: float, xi_sigma_s: float) -> dict:
    """由慢化剂温度求中子温度：T_n=T_M[1+1.4Σa(kT_M)/(ξΣs)]。

    教材 5.4 p.88-90；习题解答 v4.0【例5.1】。Σa 取 0.0253 eV 处宏观吸收截面。
    """
    T_m, sa, xss = float(T_m), float(sigma_a_0253), float(xi_sigma_s)
    if T_m <= 0 or xss <= 0:
        raise ValueError("T_M 与 ξΣs 必须为正")
    kt_m = K_B_EV * T_m
    sigma_a_kt = sa * math.sqrt(0.0253 / kt_m)
    T_n = T_m * (1.0 + 1.4 * sigma_a_kt / xss)
    return {
        "inputs": {"T_m": T_m, "sigma_a_0253": sa, "xi_sigma_s": xss},
        "results": {"kT_m_ev": kt_m, "sigma_a_kt": sigma_a_kt, "T_n": T_n},
        "steps": [
            f"kT_M = {K_B_EV:g}×{T_m:g} = {kt_m:.6g} eV",
            f"Σa(kT_M) = Σa(0.0253)·√(0.0253/kT_M) = {sigma_a_kt:.6g}",
            f"T_n = T_M[1+1.4Σa(kT_M)/(ξΣs)] = {T_n:.6g} K",
        ],
        "formulas": [
            {"step": "T_n = T_M[1 + 1.4 Σa(kT_M)/(ξΣs)]", "note": "教材 5.4 p.88-90"},
        ],
        "refs": [_REFS_SPEC[2], _REFS_SPEC[4]],
        "notes": ["例5.1：T_M=535.5 K、Σa(0.0253)=9.71 m⁻¹、ξΣs=69.5 m⁻¹ → T_n=613 K。"],
    }


def group_average(sigma_fn, bounds_ev, weight: str = "fermi",
                  T_k: float = T_0253, n: int = 4000) -> dict:
    """群平均截面 σ_g=∫σ(E)φ(E)dE/∫φ(E)dE。

    Args:
        sigma_fn: 可调用 σ(E)（E 单位 eV）。
        bounds_ev: ``(E_low, E_high)`` 或 ``[E1, E2, ...]``（多群边界，返回列表）。
        weight: ``"fermi"``（φ∝1/E）或 ``"maxwell"``（φ∝E e^(−E/kT)）或可调用 φ(E)。
    """
    if callable(bounds_ev):
        raise ValueError("bounds_ev 应为二元组或多群边界序列")
    bounds = [float(b) for b in bounds_ev]
    if len(bounds) < 2:
        raise ValueError("bounds_ev 至少两个边界")
    if any(b <= 0 for b in bounds):
        raise ValueError("能量边界必须为正")
    if any(bounds[k] >= bounds[k + 1] for k in range(len(bounds) - 1)):
        raise ValueError("能量边界必须严格递增")

    if weight == "fermi":
        wfn = lambda e: 1.0 / e
    elif weight == "maxwell":
        wfn = lambda e: maxwellian(e, T_k)
    elif callable(weight):
        wfn = weight
    else:
        raise ValueError("weight 只能是 'fermi'/'maxwell' 或可调用 φ(E)")

    def num(e: float) -> float:
        return float(sigma_fn(e)) * wfn(e)

    results = []
    steps = []
    for k in range(len(bounds) - 1):
        e1, e2 = bounds[k], bounds[k + 1]
        den = _log_integral(wfn, e1, e2, n)
        if den <= 0:
            raise ValueError("权重函数积分为 0")
        sig = _log_integral(num, e1, e2, n) / den
        results.append(sig)
        steps.append(f"群[{e1:g},{e2:g}] eV：σ_g = {sig:.8g}")
    return {
        "inputs": {"bounds_ev": bounds, "weight": weight if isinstance(weight, str) else "callable",
                   "T_k": T_k, "n": n},
        "results": {"sigma_g": results if len(results) > 1 else results[0],
                    "sigma_g_list": results},
        "steps": steps,
        "formulas": [
            {"step": "σ_g = ∫σ(E)φ(E)dE / ∫φ(E)dE", "note": "群常数定义（教材 第5章 5.5）"},
            {"step": "1/v 截面 + 1/E 谱：σ_g=2C(1/√E₁−1/√E₂)/ln(E₂/E₁)",
             "note": "习题 v4.0【补充2.1】"},
        ],
        "refs": [_REFS_SPEC[3], _REFS_SPEC[2]],
        "notes": ["数值积分在 lnE 上做复合 Simpson（n 可调）；1/v 解析锚点误差<1e-6。"],
    }


__all__ = [
    "K_B_EV", "T_0253", "E_THERMAL_CUT", "E_FAST_CUT",
    "watt_fission_spectrum", "fission_spectrum", "maxwellian",
    "maxwellian_spectrum", "fermi_spectrum", "pwr_spectrum",
    "normalized_pwr_spectrum", "spectrum_curve", "most_probable_energy",
    "neutron_temperature", "group_average",
]
