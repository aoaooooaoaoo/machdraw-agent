"""反应性（reactivity）换算与反应性系数引擎。

教材出处
--------
* 反应性定义 ``ρ = (k_eff - 1) / k_eff``：教材 第3章 3.1.1 节 p.33（式 3-3 后文）。
* 反应性单位 ``1 pcm = 10^-5``、``1 mk = 10^-3``、``1 $ = β``：教材 第8章 8.2 节
  p.130-132（"此时称引入了 1$ 的反应性"）；习题解答 v4.0 第3章【题3.4】。
* 缓发中子总份额 ``β = 0.0065``（235U 热中子裂变）：教材 第2章 2.5.3 节
  p.27 表 2-3；第8章 8.2 节 p.130。
* 温度系数 / 功率系数 / 功率亏损定义：教材 第7章 7.1 节 p.116、7.2 节 p.119。

实现约定
--------
* 反应性 ``ρ`` 一律用无量纲 ``Δk/k`` 表示（1 pcm = 1e-5）。
* 引擎是纯函数，不依赖 FastAPI / 工具层；每个公开函数返回 dict：
  ``inputs / results / steps / formulas / refs / notes``。
"""
from __future__ import annotations

import math

#: 235U 热中子裂变缓发中子总份额（教材 第2章 表2-3，p.27：β=0.0065）
BETA_U235 = 0.0065

#: 1 $ 对应的反应性（无量纲）
ONE_DOLLAR = BETA_U235

#: 单位别名 -> 该单位换算到无量纲 ρ 的“每单位倍数”
#: ``rho = value * factor``；``$`` 依赖 β，单独处理。
_UNIT_FACTOR = {
    "pcm": 1e-5,
    "mk": 1e-3,
    "dk/k": 1.0,
    "delta_k/k": 1.0,
    "delta_k_k": 1.0,
    "abs": 1.0,
    "": 1.0,
    "percent": 1e-2,
    "%": 1e-2,
}

_UNIT_CANON = {
    "pcm": "pcm", "mk": "mk", "dk/k": "dk/k", "delta_k/k": "dk/k",
    "delta_k_k": "dk/k", "abs": "dk/k", "": "dk/k",
    "percent": "%", "%": "%",
    "$": "$", "dollar": "$", "元": "$",
}

_REFS_RHO_K = [
    "教材 第3章 3.1.1 节 p.33：ρ=(k_eff−1)/k_eff，k_eff=1/(1−ρ)",
    "习题解答 v4.0 第3章【题3.4】：1 pcm=10⁻⁵、1 mk=10⁻³、1$=β",
]
_REFS_COEF = [
    "教材 第7章 7.1 节 p.116：温度系数 α_T=Δρ/ΔT",
    "教材 第7章 7.2 节 p.119：功率系数为单位功率变化引起的反应性变化",
    "习题解答 v4.0 第7章【题7.8】：功率亏损 Δρ=α_P·(P₂−P₁)",
]


def _canon_unit(unit: str) -> str:
    key = (unit or "").strip().lower().replace(" ", "")
    if key not in _UNIT_CANON:
        raise ValueError(f"不支持的反应性单位：{unit!r}（可用 pcm/mk/%/dk/k/$）")
    return _UNIT_CANON[key]


def rho_from_k(k: float) -> dict:
    """由有效增殖系数 k 求反应性 ρ=(k−1)/k。

    教材 第3章 3.1.1 节 p.33。
    """
    k = float(k)
    if k <= 0:
        raise ValueError("k 必须为正值")
    rho = (k - 1.0) / k
    return {
        "inputs": {"k": k},
        "results": {
            "rho": rho,
            "rho_pcm": rho * 1e5,
            "rho_percent": rho * 1e2,
            "rho_mk": rho * 1e3,
            "rho_dollar": rho / BETA_U235,
        },
        "steps": [
            f"ρ = (k−1)/k = ({k:.6g}−1)/{k:.6g} = {rho:.6g}",
            f"ρ = {rho * 1e5:.4g} pcm = {rho * 1e2:.4g}% Δk/k = {rho / BETA_U235:.4g} $",
        ],
        "formulas": [{"step": "ρ = (k_eff − 1) / k_eff", "note": "教材 3.1.1 p.33"}],
        "refs": list(_REFS_RHO_K),
        "notes": ["超临界 ρ>0；临界 ρ=0；次临界 ρ<0。"],
    }


def k_from_rho(rho: float) -> dict:
    """由反应性 ρ 反求 k_eff=1/(1−ρ)。"""
    rho = float(rho)
    if rho >= 1.0:
        raise ValueError("ρ 必须小于 1（k_eff 无有限正解）")
    k = 1.0 / (1.0 - rho)
    return {
        "inputs": {"rho": rho},
        "results": {"k_eff": k, "rho_pcm": rho * 1e5, "rho_dollar": rho / BETA_U235},
        "steps": [f"k_eff = 1/(1−ρ) = 1/(1−{rho:.6g}) = {k:.6g}"],
        "formulas": [{"step": "k_eff = 1 / (1 − ρ)", "note": "由 ρ=(k−1)/k 反解"}],
        "refs": list(_REFS_RHO_K),
        "notes": [],
    }


def unit_convert(value: float, from_unit: str = "pcm", to_unit: str = "dk/k",
                 beta: float = BETA_U235) -> dict:
    """反应性单位换算（pcm / mk / % / Δk·k⁻¹ / $）。"""
    value = float(value)
    src = _canon_unit(from_unit)
    dst = _canon_unit(to_unit)
    beta = float(beta)
    if beta <= 0:
        raise ValueError("β 必须为正")

    if src == "$":
        rho = value * beta
    else:
        rho = value * _UNIT_FACTOR[src]

    if dst == "$":
        out = rho / beta
    else:
        out = rho / _UNIT_FACTOR[dst]

    return {
        "inputs": {"value": value, "from_unit": src, "to_unit": dst, "beta": beta},
        "results": {
            "rho": rho,
            "converted": out,
            "rho_pcm": rho * 1e5,
            "rho_dollar": rho / beta,
        },
        "steps": [
            f"{value:g} {src} → ρ = {rho:.6g}（无量纲 Δk/k）",
            f"ρ = {out:g} {dst}",
        ],
        "formulas": [
            {"step": "1 pcm = 10⁻⁵；1 mk = 10⁻³；1% = 10⁻²；1$ = β",
             "note": "教材 8.2 节 p.130；习题 v4.0 题3.4"},
        ],
        "refs": list(_REFS_RHO_K),
        "notes": [f"本引擎取 β={beta:g}（235U 热中子裂变，教材 p.27 表2-3）。"],
    }


def rho_dollar(rho: float, beta: float = BETA_U235) -> dict:
    """把无量纲反应性换算成“元”（$ = ρ/β）。"""
    rho = float(rho)
    beta = float(beta)
    return {
        "inputs": {"rho": rho, "beta": beta},
        "results": {"dollar": rho / beta, "pcm": rho * 1e5},
        "steps": [f"$ = ρ/β = {rho:.6g}/{beta:g} = {rho / beta:.6g}"],
        "formulas": [{"step": "$ = ρ / β", "note": "教材 8.2 节 p.130-132"}],
        "refs": list(_REFS_RHO_K),
        "notes": ["ρ=β 即 1$，为瞬发临界条件。"],
    }


def temperature_coefficient(rho1: float, rho2: float, T1: float, T2: float,
                            name: str = "温度系数") -> dict:
    """由两温度点的反应性求温度系数 α_T=Δρ/ΔT（教材 7.1 节 p.116）。"""
    rho1, rho2, T1, T2 = float(rho1), float(rho2), float(T1), float(T2)
    if abs(T2 - T1) < 1e-12:
        raise ValueError("T1 与 T2 不能相同")
    alpha = (rho2 - rho1) / (T2 - T1)
    sign = "负（温度升高引入负反应性，安全）" if alpha < 0 else (
        "正（温度升高引入正反应性，不安全）" if alpha > 0 else "零")
    return {
        "inputs": {"rho1": rho1, "rho2": rho2, "T1": T1, "T2": T2},
        "results": {
            "alpha_dk_per_K": alpha,
            "alpha_pcm_per_K": alpha * 1e5,
            "alpha_percent_per_K": alpha * 1e2,
            "sign": sign,
        },
        "steps": [
            f"α = (ρ₂−ρ₁)/(T₂−T₁) = ({rho2:.6g}−{rho1:.6g})/({T2:g}−{T1:g})",
            f"α = {alpha:.6g} Δk·k⁻¹/K = {alpha * 1e5:.4g} pcm/K",
        ],
        "formulas": [{"step": "α_T = Δρ / ΔT", "note": "教材 7.1 节 p.116"}],
        "refs": list(_REFS_COEF),
        "notes": [
            "燃料温度系数由多普勒效应决定，恒为负（教材 7.1.1 p.117）；",
            "慢化剂温度系数符号取决于水铀比是否欠慢化（教材 7.1.2 p.118）。",
        ],
    }


def power_coefficient(rho1: float, rho2: float, P1: float, P2: float) -> dict:
    """由两功率点的反应性求功率系数 α_P=Δρ/ΔP（P 以 %FP 计）。教材 7.2 节 p.119。"""
    rho1, rho2, P1, P2 = float(rho1), float(rho2), float(P1), float(P2)
    if abs(P2 - P1) < 1e-12:
        raise ValueError("P1 与 P2 不能相同")
    alpha = (rho2 - rho1) / (P2 - P1)
    return {
        "inputs": {"rho1": rho1, "rho2": rho2, "P1": P1, "P2": P2},
        "results": {
            "alpha_dk_per_percentFP": alpha,
            "alpha_percent_per_percentFP": alpha * 1e2,
            "alpha_pcm_per_percentFP": alpha * 1e5,
        },
        "steps": [
            f"α_P = (ρ₂−ρ₁)/(P₂−P₁) = ({rho2:.6g}−{rho1:.6g})/({P2:g}−{P1:g})",
            f"α_P = {alpha * 1e2:.4g}% Δk/k per %FP",
        ],
        "formulas": [{"step": "α_P = Δρ / ΔP", "note": "教材 7.2 节 p.119"}],
        "refs": list(_REFS_COEF),
        "notes": ["功率系数是燃料温度、慢化剂温度、空泡等效应的总包（教材 7.2 p.119）。"],
    }


def power_defect(power_coefficient_percent: float, P1: float, P2: float) -> dict:
    """功率亏损（功率系数从 P1 到 P2 的积分）。

    简化线性模型：``Δρ = α_P · (P2 − P1)``，α_P 单位 %Δk/k per %FP。
    习题解答 v4.0 第7章【题7.8】：α_P=−0.020%/%FP，(30−100)%FP → +1.4%。

    Args:
        power_coefficient_percent: 总功率系数，%Δk/k per %FP（通常为负）。
        P1: 初功率（%FP）。
        P2: 末功率（%FP）。
    """
    a = float(power_coefficient_percent)
    P1, P2 = float(P1), float(P2)
    d_rho_percent = a * (P2 - P1)
    return {
        "inputs": {"alpha_percent_per_percentFP": a, "P1": P1, "P2": P2},
        "results": {
            "delta_rho_percent": d_rho_percent,
            "delta_rho_pcm": d_rho_percent * 1e3,
            "delta_rho": d_rho_percent * 1e-2,
        },
        "steps": [
            f"Δρ = α_P·(P₂−P₁) = {a:g}%/%FP × ({P2:g}−{P1:g})%FP",
            f"Δρ = {d_rho_percent:.4g}% Δk/k = {d_rho_percent * 1e3:.4g} pcm",
        ],
        "formulas": [{"step": "Δρ = ∫α_P dP ≈ α_P·(P₂−P₁)", "note": "教材 7.2 节 p.119"}],
        "refs": list(_REFS_COEF),
        "notes": [
            "降功率(P₂<P₁)且 α_P<0 时，功率亏损为正（释放正反应性），"
            "这正是题7.8 中 +1.4% 的由来。",
        ],
    }


def combine_terms(terms: list[dict]) -> dict:
    """把多项反应性贡献（控制棒/氙/功率亏损/硼/温度）代数求和。

    ``terms`` 每项形如 ``{"name": "控制棒", "value": -6.918, "unit": "%"}``，
    单位支持 pcm / mk / % / Δk·k⁻¹ / $。习题解答 v4.0 第7章【题7.6】。
    """
    if not terms:
        raise ValueError("terms 不能为空")
    total = 0.0
    rows = []
    for term in terms:
        name = str(term.get("name", "项"))
        value = float(term.get("value", 0.0))
        unit = _canon_unit(str(term.get("unit", "pcm")))
        rho = value * BETA_U235 if unit == "$" else value * _UNIT_FACTOR[unit]
        total += rho
        rows.append({"name": name, "value": value, "unit": unit, "rho_pcm": rho * 1e5})
    verdict = "临界" if abs(total) < 1e-9 else ("超临界" if total > 0 else "次临界")
    return {
        "inputs": {"terms": terms},
        "results": {
            "rho": total,
            "rho_pcm": total * 1e5,
            "rho_percent": total * 1e2,
            "verdict": verdict,
        },
        "steps": [
            "；".join(f"{r['name']}={r['value']:g}{r['unit']}({r['rho_pcm']:+.1f} pcm)" for r in rows),
            f"ΣΔρ = {total * 1e2:+.4g}% Δk/k = {total * 1e5:+.4g} pcm → {verdict}",
        ],
        "formulas": [{"step": "ρ_total = Σ ρ_i", "note": "反应性可代数叠加（小扰动）"}],
        "refs": [
            "习题解答 v4.0 第7章【题7.6】：−6.918%+2.675%+1.575%−1.040%+0.500% = −3.208%",
            "教材 第7章 7.4 节 p.120：反应性控制的叠加",
        ],
        "notes": ["次临界深度 = |ρ_total|；负值表示停堆状态。"],
    }


__all__ = [
    "BETA_U235",
    "ONE_DOLLAR",
    "rho_from_k",
    "k_from_rho",
    "unit_convert",
    "rho_dollar",
    "temperature_coefficient",
    "power_coefficient",
    "power_defect",
    "combine_terms",
]
