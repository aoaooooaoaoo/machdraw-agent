"""单群/修正单群临界计算引擎（critical）。

教材出处
--------
* 四因子公式 ``k∞ = ε·p·f·η``：教材 第3章 3.1.2 节 p.31-32（式 3-11）。
* 有效裂变中子数 ``η = νΣf/Σa``：教材 第3章 3.1.2 节 p.32（式 3-8）。
* 不泄漏概率 ``P_L = 1/(1+M²B²)``、``P_s=1/(1+τB²)``、``P_d=1/(1+L²B²)``：
  教材 第4章 4.2.2 节 p.60-61（式 4-51~4-54）。
* 材料曲率 ``B_m²=(k∞−1)/M²``、``M²=L²+τ``：教材 第4章 4.2.1 节 p.57（式 4-49）。
* 几何曲率（平板/球/圆柱/长方体）：教材 第4章 表 4-2 p.57-58。
* 外推距离 ``d = 0.7104 λ_tr``：教材 第3章 3.3.3 节 p.42-43。
* 反射层节省与等效裸堆：教材 第4章 4.2.3 节 p.61-63（式 4-67~4-73）；
  习题解答 v4.0 第4章【题4.7】。

单位约定
--------
长度单位由调用方统一给出（默认 m），``L²``、``τ`` 用长度的平方，
``B²`` 用长度的负二次方；引擎不做隐式单位换算，只保证量纲一致。
"""
from __future__ import annotations

import math

#: 真空边界外推距离系数 d = 0.7104 λ_tr（教材 3.3.3 p.42-43）
EXTRAPOLATION_FACTOR = 0.7104

#: 圆柱径向几何曲率常数（J0 第一个零点，教材 表4-2 p.58）
CYLINDER_RADIAL_CONST = 2.405

_GEOMETRY_CN = {
    "slab": "无限平板",
    "sphere": "球",
    "cylinder": "圆柱",
    "cuboid": "长方体",
    "box": "长方体",
    "rectangular": "长方体",
    "plate": "无限平板",
}

_REFS_CRIT = [
    "教材 第3章 3.1.2 节 p.31-32（四因子公式 3-11、η=νΣf/Σa 式3-8）",
    "教材 第4章 4.2.1 节 p.56-58（临界方程 4-43、材料曲率 4-49、表4-2）",
    "教材 第4章 4.2.2 节 p.60-61（修正单群 4-51~4-54）",
    "教材 第3章 3.3.3 节 p.42-43（外推距离 d=0.7104λtr）",
]


def _cn(geometry: str) -> str:
    key = (geometry or "").strip().lower()
    return _GEOMETRY_CN.get(key, geometry or "未指定")


def _rho(k: float) -> float:
    return (k - 1.0) / k


def k_inf_from_four_factor(eps: float, p: float, f: float, eta: float) -> dict:
    """四因子公式 k∞ = ε·p·f·η（教材 3.1.2 p.31-32 式3-11）。"""
    eps, p, f, eta = float(eps), float(p), float(f), float(eta)
    for name, val in (("ε", eps), ("p", p), ("f", f), ("η", eta)):
        if val <= 0:
            raise ValueError(f"{name} 必须为正")
    k_inf = eps * p * f * eta
    return {
        "inputs": {"eps": eps, "p": p, "f": f, "eta": eta},
        "results": {"k_inf": k_inf},
        "steps": [
            "k∞ = ε·p·f·η",
            f"    = {eps:g} × {p:g} × {f:g} × {eta:g} = {k_inf:.6g}",
        ],
        "formulas": [{"step": "k∞ = ε·p·f·η", "note": "教材 3.1.2 p.31 式(3-11)"}],
        "refs": [_REFS_CRIT[0]],
        "notes": ["ε 快中子倍增系数、p 逃脱共振吸收概率、f 热中子利用系数、η 有效裂变中子数。"],
    }


def eta_from_nu_sigma(nu: float, sigma_f: float, sigma_a: float) -> dict:
    """有效裂变中子数 η = νΣf/Σa（教材 3.1.2 p.32 式3-8）。"""
    nu, sf, sa = float(nu), float(sigma_f), float(sigma_a)
    if sa <= 0:
        raise ValueError("Σa 必须为正")
    eta = nu * sf / sa
    return {
        "inputs": {"nu": nu, "sigma_f": sf, "sigma_a": sa},
        "results": {"eta": eta},
        "steps": [f"η = νΣf/Σa = {nu:g} × {sf:g} / {sa:g} = {eta:.6g}"],
        "formulas": [{"step": "η = νΣf / Σa", "note": "教材 3.1.2 p.32 式(3-8)"}],
        "refs": [_REFS_CRIT[0]],
        "notes": ["Σa 为燃料的宏观吸收截面（含俘获与裂变）。"],
    }


def four_factor(eps: float, p: float, f: float, eta: float,
                Ps: float | None = None, Pd: float | None = None) -> dict:
    """四因子 k∞ 及可选不泄漏修正后的 k_eff=k∞·Ps·Pd。"""
    base = k_inf_from_four_factor(eps, p, f, eta)
    k_inf = base["results"]["k_inf"]
    results = {"k_inf": k_inf}
    steps = list(base["steps"])
    if Ps is not None and Pd is not None:
        Ps, Pd = float(Ps), float(Pd)
        k_eff = k_inf * Ps * Pd
        results.update({"Ps": Ps, "Pd": Pd, "P_L": Ps * Pd, "k_eff": k_eff,
                        "rho": _rho(k_eff)})
        steps.append(f"k_eff = k∞·Ps·Pd = {k_inf:.6g}×{Ps:g}×{Pd:g} = {k_eff:.6g}")
        steps.append(f"ρ = (k_eff−1)/k_eff = {_rho(k_eff):.6g}")
    return {
        "inputs": {"eps": eps, "p": p, "f": f, "eta": eta, "Ps": Ps, "Pd": Pd},
        "results": results,
        "steps": steps,
        "formulas": [
            {"step": "k∞ = ε·p·f·η", "note": "教材 3.1.2 p.31 式(3-11)"},
            {"step": "k_eff = k∞·Ps·Pd", "note": "教材 3.1.1 p.30 式(3-9)"},
        ],
        "refs": [_REFS_CRIT[0]],
        "notes": ["Ps、Pd 可来自不泄漏概率计算或直接给定。"],
    }


def buckling_material(k_inf: float, L2: float, tau: float) -> dict:
    """材料曲率 B_m²=(k∞−1)/(L²+τ)（教材 4.2.1 p.57 式4-49）。"""
    k_inf, L2, tau = float(k_inf), float(L2), float(tau)
    if L2 < 0 or tau < 0:
        raise ValueError("L² 与 τ 不能为负")
    M2 = L2 + tau
    if M2 <= 0:
        raise ValueError("M²=L²+τ 必须为正")
    Bm2 = (k_inf - 1.0) / M2
    return {
        "inputs": {"k_inf": k_inf, "L2": L2, "tau": tau},
        "results": {"M2": M2, "Bm2": Bm2, "Bm": math.sqrt(Bm2) if Bm2 >= 0 else float("nan")},
        "steps": [
            f"M² = L² + τ = {L2:g} + {tau:g} = {M2:g}",
            f"B_m² = (k∞−1)/M² = ({k_inf:g}−1)/{M2:g} = {Bm2:.6g}",
        ],
        "formulas": [
            {"step": "B_m² = (k∞ − 1) / (L² + τ)", "note": "教材 4.2.1 p.57 式(4-49)"},
            {"step": "M² = L² + τ", "note": "徙动面积"},
        ],
        "refs": [_REFS_CRIT[1]],
        "notes": ["k∞≤1 时 B_m²≤0，任何有限裸堆都不能临界。"],
    }


def extrapolation_distance(lambda_tr: float) -> dict:
    """外推距离 d = 0.7104·λ_tr（教材 3.3.3 p.42-43）。"""
    lam = float(lambda_tr)
    if lam <= 0:
        raise ValueError("λ_tr 必须为正")
    d = EXTRAPOLATION_FACTOR * lam
    return {
        "inputs": {"lambda_tr": lam},
        "results": {"d": d, "factor": EXTRAPOLATION_FACTOR},
        "steps": [f"d = 0.7104·λtr = 0.7104 × {lam:g} = {d:.6g}"],
        "formulas": [{"step": "d = 0.7104 λ_tr", "note": "教材 3.3.3 p.42-43"}],
        "refs": [_REFS_CRIT[3]],
        "notes": ["λ_tr 为输运平均自由程；真空边界用外推边界 φ=0 代替。"],
    }


def _ext(dims: dict, d: float, delta: float, keys: tuple[str, ...]) -> dict:
    """把实际尺寸换成外推尺寸（每个方向 + 2(d+δ)）。"""
    out = {}
    for key in keys:
        if dims.get(key) is None:
            out[key] = None
        else:
            out[key] = float(dims[key]) + 2.0 * (d + delta)
    return out


def _delta_of(reflector_saving, key: str, geometry: str) -> float:
    """取某方向的反射层节省：支持标量（各方向相同）或 dict（R/H/a/b/c 分向）。"""
    if isinstance(reflector_saving, dict):
        if key in reflector_saving:
            return float(reflector_saving[key])
        return float(reflector_saving.get("all", reflector_saving.get("uniform", 0.0)))
    return float(reflector_saving)


def buckling_geometric(geometry: str, dims: dict, d: float = 0.0,
                       reflector_saving=0.0) -> dict:
    """几何曲率 B_g²（教材 表4-2 p.57-58）。

    Args:
        geometry: ``slab`` / ``sphere`` / ``cylinder`` / ``cuboid``。
        dims: 实际尺寸（不含外推距离），键：
            slab ``H``；sphere ``R``；cylinder ``R,H``；cuboid ``a,b,c``。
        d: 外推距离（m）。
        reflector_saving: 反射层节省（m）。标量表示各方向相同；也可传
            ``{"R": δr, "H": δH, "a":…, "b":…, "c":…}`` 分方向给（教材 4.2.3
            p.61-63 等效裸堆：径向 R+δr，轴向 H+2δH）。

    说明：球/圆柱径向的等效尺寸为 ``R + d + δ``，平板/圆柱轴向/长方体
    各方向为 ``L + 2(d+δ)``（教材 4.2.3 p.61-63 等效裸堆 4-70/4-71）。
    """
    g = (geometry or "slab").strip().lower()
    if g in ("box", "rectangular"):
        g = "cuboid"
    if g in ("plate",):
        g = "slab"
    if g not in _GEOMETRY_CN:
        raise ValueError(f"不支持的几何：{geometry!r}（slab/sphere/cylinder/cuboid）")
    d = float(d)
    delta_R = _delta_of(reflector_saving, "R", g)
    delta_H = _delta_of(reflector_saving, "H", g)
    delta_a = _delta_of(reflector_saving, "a", g)
    delta_b = _delta_of(reflector_saving, "b", g)
    delta_c = _delta_of(reflector_saving, "c", g)

    if g == "slab":
        H = dims.get("H")
        if H is None:
            raise ValueError("平板几何需要 H")
        H_eff = float(H) + 2.0 * (d + delta_H)
        Bg2 = (math.pi / H_eff) ** 2
        eff = {"H_eff": H_eff}
        formula = "B_g²=(π/H_eff)², H_eff=H+2(d+δ_H)"
    elif g == "sphere":
        R = dims.get("R")
        if R is None:
            raise ValueError("球形几何需要 R")
        R_eff = float(R) + d + delta_R
        Bg2 = (math.pi / R_eff) ** 2
        eff = {"R_eff": R_eff}
        formula = "B_g²=(π/R_eff)², R_eff=R+d+δ_R"
    elif g == "cylinder":
        R, H = dims.get("R"), dims.get("H")
        if R is None or H is None:
            raise ValueError("圆柱几何需要 R 与 H")
        R_eff = float(R) + d + delta_R
        H_eff = float(H) + 2.0 * (d + delta_H)
        Bg2 = (math.pi / H_eff) ** 2 + (CYLINDER_RADIAL_CONST / R_eff) ** 2
        eff = {"R_eff": R_eff, "H_eff": H_eff}
        formula = "B_g²=(π/H_eff)²+(2.405/R_eff)²（H_eff=H+2(d+δ_H)，R_eff=R+d+δ_R）"
    else:  # cuboid
        vals = [dims.get("a"), dims.get("b"), dims.get("c")]
        if any(v is None for v in vals):
            raise ValueError("长方体几何需要 a、b、c")
        effs = [float(vals[0]) + 2.0 * (d + delta_a),
                float(vals[1]) + 2.0 * (d + delta_b),
                float(vals[2]) + 2.0 * (d + delta_c)]
        Bg2 = sum((math.pi / x) ** 2 for x in effs)
        eff = {"a_eff": effs[0], "b_eff": effs[1], "c_eff": effs[2]}
        formula = "B_g²=(π/a_eff)²+(π/b_eff)²+(π/c_eff)²"

    return {
        "inputs": {"geometry": g, "dims": dict(dims), "d": d,
                   "reflector_saving": reflector_saving},
        "results": {"Bg2": Bg2, "Bg": math.sqrt(max(Bg2, 0.0)), "geometry": g, **eff},
        "steps": [
            f"几何：{_cn(g)}；外推距离 d={d:g}，反射层节省 δ={reflector_saving}",
            formula,
            f"B_g² = {Bg2:.6g}",
        ],
        "formulas": [{"step": formula, "note": "教材 表4-2 p.57-58；等效裸堆 4-70/4-71"}],
        "refs": [_REFS_CRIT[1]],
        "notes": ["d 与 δ 均为长度单位，须与尺寸同一单位；δ=0 即裸堆。"],
    }


def leakage_probabilities(k_inf: float, L2: float, tau: float, B2: float) -> dict:
    """不泄漏概率 P_s=1/(1+τB²)、P_d=1/(1+L²B²)、P_L≈1/(1+M²B²)。"""
    L2, tau, B2 = float(L2), float(tau), float(B2)
    Ps = 1.0 / (1.0 + tau * B2)
    Pd = 1.0 / (1.0 + L2 * B2)
    PL = 1.0 / (1.0 + (L2 + tau) * B2)
    return {
        "inputs": {"k_inf": k_inf, "L2": L2, "tau": tau, "B2": B2},
        "results": {"Ps": Ps, "Pd": Pd, "P_L": PL, "PsPd": Ps * Pd},
        "steps": [
            f"Ps = 1/(1+τB²) = 1/(1+{tau:g}×{B2:g}) = {Ps:.6g}",
            f"Pd = 1/(1+L²B²) = 1/(1+{L2:g}×{B2:g}) = {Pd:.6g}",
            f"P_L ≈ 1/(1+M²B²) = {PL:.6g}（Ps·Pd={Ps * Pd:.6g}）",
        ],
        "formulas": [
            {"step": "P_s = 1/(1+τB²)", "note": "教材 4.2.2 p.60 式(4-52)"},
            {"step": "P_d = 1/(1+L²B²)", "note": "教材 4.2.2 p.60 式(4-51)"},
            {"step": "P_L ≈ 1/(1+M²B²)", "note": "教材 4.2.2 p.61 式(4-53)(4-54)"},
        ],
        "refs": [_REFS_CRIT[2]],
        "notes": ["单群临界时 B²=B_m²，P_L=1/k∞。"],
    }


def k_eff_single_group(k_inf: float, L2: float, tau: float, B2: float) -> dict:
    """单群/修正单群有效增殖系数 k_eff=k∞/(1+M²B²) 与反应性。"""
    k_inf, L2, tau, B2 = float(k_inf), float(L2), float(tau), float(B2)
    M2 = L2 + tau
    keff = k_inf / (1.0 + M2 * B2)
    rho = _rho(keff)
    return {
        "inputs": {"k_inf": k_inf, "L2": L2, "tau": tau, "B2": B2},
        "results": {"M2": M2, "k_eff": keff, "rho": rho, "rho_pcm": rho * 1e5,
                    "P_L": 1.0 / (1.0 + M2 * B2)},
        "steps": [
            f"M² = L²+τ = {M2:g}",
            f"k_eff = k∞/(1+M²B²) = {k_inf:g}/(1+{M2:g}×{B2:g}) = {keff:.6g}",
            f"ρ = (k_eff−1)/k_eff = {rho:.6g}（{rho * 1e5:.4g} pcm）",
        ],
        "formulas": [
            {"step": "k_eff = k∞ / (1 + M²B²)", "note": "教材 4.2.2 p.61 式(4-54)"},
            {"step": "ρ = (k_eff − 1)/k_eff", "note": "教材 3.1.1 p.33"},
        ],
        "refs": [_REFS_CRIT[1], _REFS_CRIT[2]],
        "notes": ["临界条件 k_eff=1 等价于 B²=B_m²。"],
    }


def _bg2_with_unknown(geometry: str, unknown: str, value: float, dims: dict,
                      d: float, delta: float) -> float:
    merged = dict(dims)
    merged[unknown] = value
    return buckling_geometric(geometry, merged, d=d, reflector_saving=delta)["results"]["Bg2"]


def _bisect_size(geometry: str, unknown: str, target_B2: float, dims: dict,
                 d: float, delta: float, lo: float = 1e-6, hi: float = 1e4,
                 tol: float = 1e-12, max_iter: int = 200) -> tuple[float, int]:
    """二分求临界尺寸：解 B_g²(尺寸)=B_m²；B_g² 随尺寸单调递减。"""
    f_lo = _bg2_with_unknown(geometry, unknown, lo, dims, d, delta) - target_B2
    f_hi = _bg2_with_unknown(geometry, unknown, hi, dims, d, delta) - target_B2
    if f_lo * f_hi > 0:
        # 扩区间，直到包住根
        for _ in range(60):
            hi *= 10.0
            f_hi = _bg2_with_unknown(geometry, unknown, hi, dims, d, delta) - target_B2
            if f_lo * f_hi <= 0:
                break
        else:
            raise ValueError("二分失败：目标曲率超出可搜索尺寸范围")
        for _ in range(60):
            lo *= 0.1
            f_lo = _bg2_with_unknown(geometry, unknown, lo, dims, d, delta) - target_B2
            if f_lo * f_hi <= 0:
                break
    it = 0
    for it in range(1, max_iter + 1):
        mid = 0.5 * (lo + hi)
        f_mid = _bg2_with_unknown(geometry, unknown, mid, dims, d, delta) - target_B2
        if f_mid == 0 or (hi - lo) <= tol * max(1.0, abs(mid)):
            return mid, it
        if f_lo * f_mid <= 0:
            hi, f_hi = mid, f_mid
        else:
            lo, f_lo = mid, f_mid
    return 0.5 * (lo + hi), it


def critical_size(geometry: str, k_inf: float, L2: float, tau: float,
                  dims: dict | None = None, d: float = 0.0,
                  reflector_saving: float = 0.0) -> dict:
    """反解临界尺寸（二分法）。

    给定材料 (k∞, L², τ)，令 B_g²=B_m²，反解某一方向的实际尺寸：
    slab 求 H；sphere 求 R；cylinder 给 H 求 R（或给 R 求 H）；
    cuboid 给两个边求第三边。返回实际尺寸（已扣掉外推距离与反射层节省）。

    Args:
        geometry: slab/sphere/cylinder/cuboid。
        k_inf, L2, tau: 材料参数（单位一致）。
        dims: 已知尺寸，未知量置 ``None`` 或省略；如
            ``{"H": None}``、``{"R": None, "H": 3.55}``、``{"a":0.5,"b":0.5,"c":None}``。
        d: 外推距离；reflector_saving: 反射层节省。
    """
    g = (geometry or "slab").strip().lower()
    if g in ("box", "rectangular"):
        g = "cuboid"
    if g in ("plate",):
        g = "slab"
    dims = dict(dims or {})
    bm = buckling_material(k_inf, L2, tau)
    Bm2 = bm["results"]["Bm2"]
    if Bm2 <= 0:
        raise ValueError("B_m²≤0（k∞≤1），该材料无法达到临界")

    if g == "slab":
        dims.setdefault("H", None)
        unknown = "H"
    elif g == "sphere":
        dims.setdefault("R", None)
        unknown = "R"
    elif g == "cylinder":
        if dims.get("H") is None and dims.get("R") is not None:
            unknown = "H"
        elif dims.get("R") is None and dims.get("H") is not None:
            unknown = "R"
        else:
            raise ValueError("圆柱临界尺寸需要给定 H 或 R 之一（另一个置 None）")
    elif g == "cuboid":
        unknown = None
        for key in ("a", "b", "c"):
            if dims.get(key) is None:
                if unknown is not None:
                    raise ValueError("长方体只能有一个未知边")
                unknown = key
        if unknown is None:
            raise ValueError("长方体需有一个未知边（置 None）")
        dims.setdefault("a", None), dims.setdefault("b", None), dims.setdefault("c", None)
    else:
        raise ValueError(f"不支持的几何：{geometry!r}")

    L_actual, iterations = _bisect_size(g, unknown, Bm2, dims, float(d), float(reflector_saving))
    full = dict(dims)
    full[unknown] = L_actual
    bg = buckling_geometric(g, full, d=d, reflector_saving=reflector_saving)
    return {
        "inputs": {
            "geometry": g, "k_inf": float(k_inf), "L2": float(L2), "tau": float(tau),
            "dims": dims, "d": float(d), "reflector_saving": float(reflector_saving),
        },
        "results": {
            "Bm2": Bm2, "M2": bm["results"]["M2"],
            "critical_size": L_actual, "size_name": {"H": "H", "R": "R", "a": "a",
                                                     "b": "b", "c": "c"}[unknown],
            "Bg2_check": bg["results"]["Bg2"], "iterations": iterations,
            "dims_solved": full, "geometry": g,
        },
        "steps": [
            f"B_m² = (k∞−1)/(L²+τ) = {Bm2:.6g}",
            f"令 B_g²=B_m²，二分反解 {_cn(g)} 的临界尺寸 {unknown}",
            f"{unknown}（实际，含扣除外推距离 d={d:g}、反射层节省 δ={reflector_saving:g}）"
            f" = {L_actual:.6g}（二分 {iterations} 次）",
            f"校核 B_g² = {bg['results']['Bg2']:.6g}",
        ],
        "formulas": [
            {"step": f"B_g²({geometry}) = B_m²", "note": "临界条件 4-50"},
            {"step": "二分法解 B_g²(L)=B_m²（B_g² 随尺寸单调递减）", "note": "教材 4.2.1 p.56"},
        ],
        "refs": [_REFS_CRIT[1], _REFS_CRIT[2]],
        "notes": [
            "d、δ 与尺寸同单位；球/圆柱径向扣除 d+δ，平板/轴向扣除 2(d+δ)。",
            "教材例题 4.1/4.2 分别用解析式反解，本引擎用同一 B_g² 定义做二分，"
            "两者在数值上一致（锚点测试已校核）。",
        ],
    }


def reflector_saving_estimate(L_r: float, t: float) -> dict:
    """反射层节省的简化估算（教材 4.2.3 p.63 式4-73 的两个极限）。

    教材式(4-73)在抽取文本中为公式图，正文只给出两个可核对的极限：
    ``t→很大时 δ→常数``；``t→很小时 δ→t``。本引擎采用同时满足这两个
    极限的指数插值 ``δ = L_r·(1−e^{−t/L_r})``，常数取反射层扩散长度 L_r，
    仅用于教学估算；严格值需解两区扩散方程。

    Args:
        L_r: 反射层扩散长度。
        t: 反射层厚度。
    """
    L_r, t = float(L_r), float(t)
    if L_r <= 0 or t < 0:
        raise ValueError("L_r 必须为正、t 不能为负")
    delta = L_r * (1.0 - math.exp(-t / L_r))
    return {
        "inputs": {"L_r": L_r, "t": t},
        "results": {"delta": delta, "delta_over_Lr": delta / L_r},
        "steps": [
            "教材结论：t≫L_r 时 δ→常数；t≪L_r 时 δ→t",
            f"教学插值 δ = L_r(1−e^(−t/L_r)) = {delta:.6g}",
        ],
        "formulas": [{"step": "δ = L_r·(1 − e^(−t/L_r))", "note": "满足教材 (4-73) 两个极限的简化式"}],
        "refs": ["教材 第4章 4.2.3 节 p.63 式(4-73)（公式图为图片，正文给出两个极限）"],
        "notes": ["若要严格值，应求解堆芯+反射层两区扩散方程的临界方程（教材 4.2.3 p.61-63）。"],
    }


__all__ = [
    "EXTRAPOLATION_FACTOR",
    "CYLINDER_RADIAL_CONST",
    "k_inf_from_four_factor",
    "eta_from_nu_sigma",
    "four_factor",
    "buckling_material",
    "buckling_geometric",
    "extrapolation_distance",
    "leakage_probabilities",
    "k_eff_single_group",
    "critical_size",
    "reflector_saving_estimate",
]
