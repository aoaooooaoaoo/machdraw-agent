"""kinetics 引擎锚点：六组缓发中子表、题2.10、题8.5、倒时方程与响应不变量。

出处：
* 表2-3：教材 第2章 2.5.3 节 p.27（β=0.0065；各组产额与平均寿期）。
* 题2.10：v4.0 第2章（10⁵ 个缓发中子 → 1.528×10⁷ 个瞬发中子，β=0.0065）。
* 题8.5：v4.0 第8章（120 s 内功率 3×10⁻⁶%→5×10⁻⁶%FP → T=234.91 s）。
* 倒时方程：教材 第8章 8.2 节 p.130-131 式(8-17)；瞬发临界 ρ=β：p.132。
"""
import math

from app.domain import kinetics as k


def _close(actual, expected, tol, what=""):
    assert abs(actual - expected) <= tol, (
        f"{what}: 得到 {actual!r}，期望 {expected!r}（容差 {tol!r}）")


def test_kinetics_beta_total_from_table_2_3():
    """表2-3：六组产额之和 β=0.0065；Σβ_iτ_i≈0.083 s（教材 p.27）。"""
    data = k.delayed_data()
    _close(data["results"]["beta_total"], 0.0065, 1e-12, "β_total")
    assert len(data["results"]["groups"]) == 6
    # 点堆近似中的缓发项 Σβ_iτ_i（由表2-3“平均寿期”列计算，约 0.0828 s）
    tau = data["results"]["delayed_mean_life_s"]
    assert 0.080 < tau < 0.086, f"Σβ_iτ_i={tau} s 不在表2-3 合理范围"
    _close(data["results"]["mean_precursor_life_s"], 12.74, 0.05, "先驱核平均寿期")


def test_kinetics_prompt_neutrons_exercise_2_10():
    """题2.10：10⁵ 个缓发中子 → 1.528×10⁷ 个瞬发中子。"""
    r = k.prompt_neutrons_from_delayed(1.0e5)
    _close(r["results"]["n_prompt"], 1.528e7, 1e4, "瞬发中子数")


def test_kinetics_period_exercise_8_5():
    """题8.5：n₂/n₁=5/3、Δt=120 s → 平均周期 T=234.91 s。"""
    r = k.period_from_ratio(5.0 / 3.0, 120.0)
    _close(r["results"]["T_s"], 234.91, 0.01, "反应堆周期 T")


def test_kinetics_inhour_root_satisfies_equation():
    """倒时方程自洽：ρ = l s + Σβ_i s/(s+λ_i)，ρ=200 pcm 时残差 <1e-12。"""
    rho = 0.002
    res = k.inhour_roots(rho, 1e-4)
    s = res["results"]["dominant"]
    assert s > 0
    lhs = 1e-4 * s + sum(g["beta"] * s / (s + g["lambda"])
                         for g in k.delayed_data()["results"]["groups"])
    _close(lhs, rho, 1e-12, "倒时方程残差")
    assert len(res["results"]["roots"]) == 7, "六组缓发中子应有 7 个根"


def test_kinetics_zero_rho_is_critical():
    """ρ=0：s=0（功率不随时间变化）；题8.5 的指数关系 T→∞。"""
    res = k.inhour_roots(0.0, 1e-4)
    assert res["results"]["dominant"] == 0.0
    per = k.period(0.0, 1e-4)
    assert math.isinf(per["results"]["T_s"])


def test_kinetics_prompt_critical_and_jump():
    """瞬发临界：ρ=β 时 ρ/β=1，跳跃比发散；ρ=0 时跳跃比=1。"""
    beta = k.BETA_U235
    chk = k.prompt_critical_check(beta)
    assert chk["results"]["prompt_critical"] is True
    _close(chk["results"]["dollar"], 1.0, 1e-12, "ρ/β")
    jump0 = k.prompt_jump_ratio(0.0)
    _close(jump0["results"]["jump_ratio"], 1.0, 1e-12, "跳跃比(ρ=0)")
    jump_beta = k.prompt_jump_ratio(beta)
    assert jump_beta["results"]["jump_ratio"] == float("inf")


def test_kinetics_response_curve_invariants():
    """响应曲线不变量：ρ=0 时 n/n0≡1；ρ>0 时远后期相邻周期比值→e（指数增长）。"""
    flat = k.response_curve(0.0, 2.0, 1e-3)
    assert max(abs(v - 1.0) for v in flat["results"]["values"]) < 1e-9, "ρ=0 应保持恒定"
    rho = 0.002
    T = k.period(rho, 1e-4)["results"]["T_s"]
    resp = k.response_curve(rho, 5.0 * T, T / 400.0, max_points=600)
    pts = resp["series"][0]["points"]

    def _at(t_target):
        return min(pts, key=lambda p: abs(p[0] - t_target))[1]

    ratio = _at(5.0 * T) / _at(4.0 * T)
    _close(ratio, math.e, 0.05, "n(5T)/n(4T) → e")
