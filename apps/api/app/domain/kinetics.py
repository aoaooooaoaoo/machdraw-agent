"""点堆中子动力学引擎（kinetics）。

教材出处
--------
* 六组缓发中子数据（半衰期、能量、产额、平均寿期，235U 热中子裂变）：
  教材 第2章 2.5.3 节 p.27 表 2-3。由表中数据得 β=0.0065。
* 点堆动力学方程与反应性（倒时）方程：
  教材 第8章 8.1 节 p.128、8.2 节 p.129-132（式 8-11~8-17）。
* 反应堆周期定义 T=1/ω（中子密度增至 e 倍所需时间）：教材 8.1 节 p.128。
* 瞬发临界条件 ρ=β（"1$"）：教材 8.2 节 p.132。
* 习题解答 v4.0 第8章【题8.5】（周期 234.91 s）；第2章【题2.10】（瞬发/缓发中子数）。

实现约定
--------
* ``rho`` 为无量纲 Δk/k；也可通过 ``rho_in(value, unit)`` 传入 pcm / $ / mk。
* 单群点堆方程（教材 8.2 式 8-13/8-14）：

    dn/dt  = (ρ−β)/Λ·n + Σ_i λ_i C_i
    dC_i/dt = β_i/Λ·n − λ_i C_i,   i=1..6

  其中 Λ 取中子代时间（临界附近 Λ=l，l 为热中子寿期），
  λ_i = 1/平均寿期（表 2-3 的“平均寿期/秒”列）。
"""
from __future__ import annotations

import math

#: 235U 热中子裂变六组缓发中子（教材 第2章 表2-3 p.27）。
#: ``beta`` 为该组缓发中子产额（= β_i），``mean_life_s`` 为平均寿期；
#: 衰变常数 λ_i = 1/mean_life_s。
SIX_GROUP_U235 = (
    {"group": 1, "half_life_s": "54–56", "energy_kev": 250, "beta": 0.000247, "mean_life_s": 78.64},
    {"group": 2, "half_life_s": "21–23", "energy_kev": 560, "beta": 0.001385, "mean_life_s": 31.51},
    {"group": 3, "half_life_s": "5–6", "energy_kev": 430, "beta": 0.001222, "mean_life_s": 8.66},
    {"group": 4, "half_life_s": "1.9–2.3", "energy_kev": 630, "beta": 0.002645, "mean_life_s": 3.22},
    {"group": 5, "half_life_s": "0.5–0.6", "energy_kev": 420, "beta": 0.000832, "mean_life_s": 0.716},
    {"group": 6, "half_life_s": "0.17–0.27", "energy_kev": None, "beta": 0.000169, "mean_life_s": 0.258},
)

#: 235U 热中子裂变缓发中子总份额（教材 p.27：β=0.0065）
BETA_U235 = 0.0065

#: 典型压水堆热中子寿期 l（s）：教材 8.1 p.128 例题取值的量级（~10⁻⁴ s）
PWR_NEUTRON_LIFETIME = 1.0e-4

_REFS_KIN = [
    "教材 第2章 2.5.3 节 p.27 表2-3（235U 六组缓发中子数据，β=0.0065）",
    "教材 第8章 8.1 节 p.128（反应堆周期 T=1/ω）",
    "教材 第8章 8.2 节 p.129-132（点堆方程 8-11~8-17、瞬发临界 ρ=β）",
]


def delayed_data(beta_groups=SIX_GROUP_U235) -> dict:
    """返回六组缓发中子常数（含 λ_i、β_total、平均缓发中子寿期）。"""
    groups = []
    beta_total = 0.0
    mean_life_weighted = 0.0
    for g in beta_groups:
        beta = float(g["beta"])
        lam = 1.0 / float(g["mean_life_s"])
        beta_total += beta
        mean_life_weighted += beta * float(g["mean_life_s"])
        groups.append({
            "group": int(g["group"]),
            "half_life_s": g.get("half_life_s"),
            "energy_kev": g.get("energy_kev"),
            "beta": beta,
            "lambda": lam,
            "mean_life_s": float(g["mean_life_s"]),
        })
    return {
        "inputs": {"groups": [g["group"] for g in beta_groups]},
        "results": {
            "groups": groups,
            "beta_total": beta_total,
            "delayed_mean_life_s": mean_life_weighted,
            "mean_precursor_life_s": (mean_life_weighted / beta_total) if beta_total else 0.0,
            "prompt_fraction": 1.0 - beta_total,
        },
        "steps": [
            f"β = Σβ_i = {beta_total:.6g}",
            "λ_i = 1/平均寿期：",
            "  " + "，".join(f"λ{i}={g['lambda']:.5g}" for i, g in
                             zip(range(1, 7), groups)),
            f"Σβ_iτ_i = {mean_life_weighted:.6g} s（点堆近似中的缓发项）",
        ],
        "formulas": [
            {"step": "β = Σ_i β_i；λ_i = 1/τ_i", "note": "τ_i 取表2-3“平均寿期”列"},
        ],
        "refs": [_REFS_KIN[0]],
        "notes": ["表 2-3 给出的是平均寿期而非半衰期；半衰期区间仅作对照。"],
    }


def rho_in(value: float, unit: str = "dk/k", beta: float = BETA_U235) -> float:
    """把 pcm / mk / % / $ 统一换算成无量纲 Δk/k。"""
    u = (unit or "dk/k").strip().lower().replace(" ", "")
    v = float(value)
    if u == "pcm":
        return v * 1e-5
    if u == "mk":
        return v * 1e-3
    if u in ("%", "percent"):
        return v * 1e-2
    if u in ("$", "dollar", "元"):
        return v * float(beta)
    if u in ("dk/k", "delta_k/k", "abs", ""):
        return v
    raise ValueError(f"不支持的反应性单位：{unit!r}（pcm/mk/%/dk/k/$）")


def prompt_neutrons_from_delayed(n_delayed: float, beta: float = BETA_U235) -> dict:
    """由缓发中子数求瞬发中子数：n_prompt = n_delayed·(1−β)/β。

    出处：习题解答 v4.0 第2章【题2.10】（β=0.0065，10⁵ 个缓发中子 →
    1.528×10⁷ 个瞬发中子）；教材 2.5.3 p.27。
    """
    n_delayed = float(n_delayed)
    beta = float(beta)
    if beta <= 0:
        raise ValueError("β 必须为正")
    n_prompt = n_delayed * (1.0 - beta) / beta
    return {
        "inputs": {"n_delayed": n_delayed, "beta": beta},
        "results": {"n_prompt": n_prompt, "ratio": (1.0 - beta) / beta},
        "steps": [
            f"n_瞬发 = n_缓发·(1−β)/β = {n_delayed:g}×(1−{beta:g})/{beta:g}",
            f"       = {n_prompt:.6g}",
        ],
        "formulas": [{"step": "n_prompt = n_delayed·(1−β)/β", "note": "缓发中子份额定义"}],
        "refs": [_REFS_KIN[0], "习题解答 v4.0 第2章【题2.10】"],
        "notes": ["热中子堆 β≈0.0065，即瞬发中子约占总裂变中子的 99.35%。"],
    }


def _inhour_f(s: float, rho: float, l: float, groups: list[dict]) -> float:
    return l * s + sum(g["beta"] * s / (s + g["lambda"]) for g in groups) - rho


def inhour_roots(rho: float, l: float = PWR_NEUTRON_LIFETIME,
                 beta_groups=SIX_GROUP_U235) -> dict:
    """解倒时（反应性）方程 ρ = l·s + Σ β_i s/(s+λ_i)，返回全部实根。

    教材 8.2 节 p.130-131 式(8-17)。方程在 s>-λ_1 及各极点之间单调，
    用“极点分区间 + 二分”求 7 个根；``dominant`` 为最大的根。
    """
    delta = delayed_data(beta_groups)
    groups = delta["results"]["groups"]
    beta_total = delta["results"]["beta_total"]
    rho = float(rho)
    l = float(l)
    if l <= 0:
        raise ValueError("中子寿命 l 必须为正")
    if abs(rho) < 1e-15:
        return {
            "inputs": {"rho": rho, "l": l},
            "results": {"roots": [0.0], "dominant": 0.0, "root_count": 1,
                        "beta_total": beta_total, "period_s": float("inf"),
                        "prompt_critical": False, "rho_pcm": 0.0,
                        "rho_dollar": 0.0},
            "steps": ["ρ=0 → s=0 是精确根（临界，功率不随时间变化）"],
            "formulas": [{"step": "ρ = l·s + Σ β_i s/(s+λ_i)", "note": "教材 8.2 式(8-17)"}],
            "refs": [_REFS_KIN[2]],
            "notes": ["ρ=0 时 7 个根中只有 s=0 非负。"],
        }

    lams = sorted((g["lambda"] for g in groups), reverse=True)  # λ1>λ2>...>λ6
    # 极点 s=-λ_i，按升序（越负越靠前）排列；f(s) 在相邻极点之间严格单调递增
    poles = sorted(-lam for lam in lams)          # 升序，如 -3.876 … -0.0127
    roots: list[float] = []

    def _bisect(a: float, b: float) -> float:
        fa = _inhour_f(a, rho, l, groups)
        fim = _inhour_f(b, rho, l, groups)
        if fa == 0:
            return a
        if fim == 0:
            return b
        for _ in range(400):
            mid = 0.5 * (a + b)
            fm = _inhour_f(mid, rho, l, groups)
            if fm == 0 or (b - a) <= 1e-14 * max(1.0, abs(mid)):
                return mid
            if fa * fm <= 0:
                b = mid
            else:
                a, fa = mid, fm
        return 0.5 * (a + b)

    def _inside(a: float, b: float) -> float | None:
        """区间 (a,b) 两端为极点或 ±∞；两端符号相反则二分求根。"""
        scale = max(1.0, abs(a) if not math.isinf(a) else 0.0,
                    abs(b) if not math.isinf(b) else 0.0)
        eps = 1e-12 * scale
        if math.isinf(a):
            lo_a = b * 1e3 - 1.0
        else:
            lo_a = a + eps
        if math.isinf(b):
            hi_b = max(1.0, abs(rho) / l + beta_total / l + 10.0)
        else:
            hi_b = b - eps
        fa = _inhour_f(lo_a, rho, l, groups)
        fb = _inhour_f(hi_b, rho, l, groups)
        if fa * fb > 0 or fa == 0 or fb == 0:
            return None
        return _bisect(lo_a, hi_b)

    # 区域 1：(-∞, 最小极点)
    r = _inside(float("-inf"), poles[0])
    if r is not None:
        roots.append(r)
    # 区域 2：相邻极点之间
    for a, b in zip(poles, poles[1:]):
        r = _inside(a, b)
        if r is not None:
            roots.append(r)
    # 区域 3：(最大极点, 0)
    r = _inside(poles[-1], 0.0)
    if r is not None:
        roots.append(r)
    # 区域 4：(0, +∞)
    r = _inside(0.0, float("inf"))
    if r is not None:
        roots.append(r)

    roots.sort(reverse=True)
    dominant = roots[0] if roots else float("nan")
    return {
        "inputs": {"rho": rho, "rho_pcm": rho * 1e5, "l": l,
                   "rho_dollar": rho / beta_total},
        "results": {
            "roots": roots,
            "dominant": dominant,
            "root_count": len(roots),
            "beta_total": beta_total,
            "period_s": (1.0 / dominant) if dominant not in (0.0,) and
                        abs(dominant) > 1e-15 else float("inf"),
            "prompt_critical": rho >= beta_total,
        },
        "steps": [
            f"ρ = {rho:.6g}（{rho * 1e5:.4g} pcm，{rho / beta_total:.4g} $）",
            f"解 ρ = l·s + Σ β_i s/(s+λ_i)，得 {len(roots)} 个实根",
            f"主导根 s₁ = {dominant:.6g} s⁻¹，周期 T=1/s₁ = {1.0 / dominant if dominant else float('inf'):.6g} s",
        ],
        "formulas": [{"step": "ρ = l·s + Σ_i β_i s/(s+λ_i)", "note": "教材 8.2 式(8-17)"}],
        "refs": [_REFS_KIN[1], _REFS_KIN[2]],
        "notes": [
            "ρ>0 时只有一个正根，其余为负；ρ<0 时 7 根全负，主导根最接近 0。",
            "ρ≥β 时进入瞬发临界/瞬发超临界。",
        ],
    }


def inhour_root(rho: float, l: float = PWR_NEUTRON_LIFETIME,
                beta_groups=SIX_GROUP_U235) -> dict:
    """倒时方程主导根 s₁（教材 8.2 p.130-131）。"""
    all_roots = inhour_roots(rho, l, beta_groups)
    s = all_roots["results"]["dominant"]
    return {
        "inputs": all_roots["inputs"],
        "results": {
            "s": s,
            "period_s": 1.0 / s if abs(s) > 1e-15 else float("inf"),
            "roots": all_roots["results"]["roots"],
            "prompt_critical": all_roots["results"]["prompt_critical"],
        },
        "steps": all_roots["steps"],
        "formulas": all_roots["formulas"],
        "refs": all_roots["refs"],
        "notes": all_roots["notes"],
    }


def period(rho: float, l: float = PWR_NEUTRON_LIFETIME,
           beta_groups=SIX_GROUP_U235) -> dict:
    """反应堆周期 T=1/s₁；负反应性时 T<0（表示衰减）。"""
    r = inhour_root(rho, l, beta_groups)
    s = r["results"]["s"]
    T = 1.0 / s if abs(s) > 1e-15 else float("inf")
    return {
        "inputs": r["inputs"],
        "results": {"T_s": T, "s": s, "rho": float(rho), "rho_dollar": float(rho) / BETA_U235},
        "steps": [
            f"由倒时方程得主导根 s₁ = {s:.6g} s⁻¹",
            f"T = 1/s₁ = {T:.6g} s",
        ],
        "formulas": [{"step": "T = 1/s₁", "note": "教材 8.1 p.128；8.2 式(8-17)"}],
        "refs": [_REFS_KIN[1], _REFS_KIN[2]],
        "notes": ["T>0 表示功率按 e^{t/T} 上升；T<0 表示按 e^{−|t/T|} 下降。"],
    }


def period_from_ratio(ratio: float, dt: float) -> dict:
    """由功率比与时间间隔求平均周期：T=Δt/ln(n₂/n₁)。

    出处：习题解答 v4.0 第8章【题8.5】（120 s 内 3×10⁻⁶%→5×10⁻⁶%FP，
    答案 T=234.91 s）。
    """
    ratio, dt = float(ratio), float(dt)
    if ratio <= 0:
        raise ValueError("功率比必须为正")
    if ratio == 1.0:
        raise ValueError("功率比=1 时周期无限大")
    T = dt / math.log(ratio)
    return {
        "inputs": {"ratio": ratio, "dt": dt},
        "results": {"T_s": T, "growth_factor_per_s": math.log(ratio) / dt},
        "steps": [
            f"n₂/n₁ = e^(Δt/T) ⇒ T = Δt/ln(n₂/n₁)",
            f"T = {dt:g}/ln({ratio:g}) = {T:.6g} s",
        ],
        "formulas": [{"step": "T = Δt / ln(n₂/n₁)", "note": "周期定义 n(t)=n₀e^{t/T}"}],
        "refs": [_REFS_KIN[1], "习题解答 v4.0 第8章【题8.5】"],
        "notes": [],
    }


def prompt_jump_ratio(rho: float, beta: float = BETA_U235) -> dict:
    """瞬发跳跃比（阶跃反应性后功率的瞬时跳变） n₁/n₀ = β/(β−ρ)。

    ρ≥β（瞬发临界及以上）时无有限跳跃，返回 ``inf``。
    """
    rho, beta = float(rho), float(beta)
    if rho >= beta:
        ratio = float("inf")
        note = "ρ≥β：瞬发临界/瞬发超临界，瞬发跳跃比发散（无缓发中子约束）。"
    else:
        ratio = beta / (beta - rho)
        note = "瞬发跳跃近似：忽略缓发先驱核在跳变瞬间的变化。"
    return {
        "inputs": {"rho": rho, "beta": beta, "rho_dollar": rho / beta},
        "results": {"jump_ratio": ratio, "rho_dollar": rho / beta},
        "steps": [
            f"n₁/n₀ = β/(β−ρ) = {beta:g}/({beta:g}−{rho:g}) = {ratio:.6g}",
        ],
        "formulas": [{"step": "n₁/n₀ = β/(β−ρ)", "note": "点堆瞬发跳跃近似"}],
        "refs": [_REFS_KIN[2]],
        "notes": [note],
    }


def prompt_critical_check(rho: float, beta: float = BETA_U235) -> dict:
    """瞬发临界判定：ρ≥β（教材 8.2 p.132）。"""
    rho, beta = float(rho), float(beta)
    level = "瞬发超临界" if rho > beta else ("瞬发临界" if abs(rho - beta) < 1e-12 else "缓发临界")
    return {
        "inputs": {"rho": rho, "beta": beta},
        "results": {
            "dollar": rho / beta,
            "prompt_critical": rho >= beta,
            "level": level,
        },
        "steps": [
            f"ρ = {rho:.6g} = {rho / beta:.4g} $；β = {beta:g}",
            f"ρ {'≥' if rho >= beta else '<'} β ⇒ {level}",
        ],
        "formulas": [{"step": "瞬发临界条件 ρ = β", "note": "教材 8.2 p.132"}],
        "refs": [_REFS_KIN[2]],
        "notes": ["工程规定单次引入阶跃反应性不得超过 0.5$（保守），教材 8.2 p.132。"],
    }


def response_curve(rho: float, t_end: float, dt: float = 1e-3,
                   l: float = PWR_NEUTRON_LIFETIME,
                   beta_groups=SIX_GROUP_U235, n0: float = 1.0,
                   max_points: int = 400) -> dict:
    """阶跃反应性后的中子密度响应 n(t)/n0：六组缓发中子点堆方程 RK4 数值积分。

    教材 8.2 节 p.129-130 式(8-11)~(8-14)。初始取临界平衡：
    ``C_i(0)=β_i n0/(λ_i Λ)``（Λ=l，临界时 k=1）。

    Args:
        rho: 阶跃反应性（无量纲 Δk/k）。
        t_end: 积分总时间（s）。
        dt: 时间步长（s）。
        l: 热中子寿期（s），用作中子代时间 Λ。
        n0: 初始中子密度（归一化输出 n/n0，n0 只影响绝对量）。
    """
    rho, t_end, dt, l, n0 = float(rho), float(t_end), float(dt), float(l), float(n0)
    if t_end <= 0 or dt <= 0:
        raise ValueError("t_end 与 dt 必须为正")
    delta = delayed_data(beta_groups)
    groups = delta["results"]["groups"]
    beta = delta["results"]["beta_total"]
    lams = [g["lambda"] for g in groups]
    betas = [g["beta"] for g in groups]
    Lam = l

    # 刚性稳定步长：快（瞬发）模时间常数 ~Λ/(β−ρ)，RK4 稳定域 |z|<2.785；
    # 取 0.5Λ/β 作为上限，避免步长过大导致数值发散（nan/inf）。
    dt_eff = min(dt, 0.5 * Lam / beta)
    max_steps = 200_000
    n_steps = int(round(t_end / dt_eff))
    clamped = False
    if n_steps > max_steps:
        t_end = max_steps * dt_eff
        n_steps = max_steps
        clamped = True
    dt = dt_eff

    # 状态 y = [n, C1..C6]
    y = [n0] + [b * n0 / (lam * Lam) for b, lam in zip(betas, lams)]

    def f(yv: list[float]) -> list[float]:
        n = yv[0]
        out = [(rho - beta) / Lam * n + sum(lam * c for lam, c in zip(lams, yv[1:]))]
        for i in range(6):
            out.append(betas[i] / Lam * n - lams[i] * yv[i + 1])
        return out

    n_steps = int(round(t_end / dt))
    stride = max(1, n_steps // max_points)
    times = [0.0]
    values = [1.0]
    ydot = f(y)
    for step in range(1, n_steps + 1):
        # RK4
        k1 = ydot
        y2 = [yi + 0.5 * dt * ki for yi, ki in zip(y, k1)]
        k2 = f(y2)
        y3 = [yi + 0.5 * dt * ki for yi, ki in zip(y, k2)]
        k3 = f(y3)
        y4 = [yi + dt * ki for yi, ki in zip(y, k3)]
        k4 = f(y4)
        y = [yi + dt / 6.0 * (a + 2 * b + 2 * c + d)
             for yi, a, b, c, d in zip(y, k1, k2, k3, k4)]
        ydot = f(y)
        if step % stride == 0 or step == n_steps:
            times.append(step * dt)
            values.append(y[0] / n0)

    s = inhour_roots(rho, l, beta_groups)["results"]["dominant"]
    series = [{"name": f"n/n₀（ρ={rho:g}）", "points": list(zip(times, values))}]
    return {
        "inputs": {"rho": rho, "rho_pcm": rho * 1e5, "l": l, "t_end": t_end,
                   "dt": dt, "n0": n0, "beta": beta},
        "results": {
            "times": times,
            "values": values,
            "final_n_over_n0": values[-1],
            "max_n_over_n0": max(values),
            "period_s": 1.0 / s if abs(s) > 1e-15 else float("inf"),
            "dominant_root": s,
            "prompt_critical": rho >= beta,
            "beta": beta,
            "points": len(times),
            "dt_used": dt,
            "t_end_used": t_end,
        },
        "series": series,
        "steps": [
            f"Λ = l = {l:g} s；β = {beta:g}",
            "初值：n(0)=n0，C_i(0)=β_i·n0/(λ_i·Λ)",
            f"RK4 积分 0→{t_end:g} s，步长 {dt:g} s，输出 {len(times)} 点",
            f"n/n₀ 终值 = {values[-1]:.6g}；由倒时方程 T = "
            f"{1.0 / s if abs(s) > 1e-15 else float('inf'):.6g} s",
        ],
        "formulas": [
            {"step": "dn/dt = (ρ−β)/Λ·n + Σλ_iC_i", "note": "教材 8.2 式(8-13)"},
            {"step": "dC_i/dt = β_i/Λ·n − λ_iC_i", "note": "教材 8.2 式(8-14)"},
        ],
        "refs": [_REFS_KIN[0], _REFS_KIN[2]],
        "notes": [
            "本曲线是不含温度反馈的点堆响应；工程瞬态还需耦合反应性反馈。",
            "ρ<β 时曲线先出现瞬发跳跃，随后按倒时方程周期缓发上升。",
            (f"为满足刚性方程 RK4 稳定域，实际步长取 {dt:g} s"
             + ("；积分时长已限制为 200000 步。" if clamped else "。")),
        ],
    }


__all__ = [
    "SIX_GROUP_U235",
    "BETA_U235",
    "PWR_NEUTRON_LIFETIME",
    "delayed_data",
    "rho_in",
    "prompt_neutrons_from_delayed",
    "inhour_roots",
    "inhour_root",
    "period",
    "period_from_ratio",
    "prompt_jump_ratio",
    "prompt_critical_check",
    "response_curve",
]
