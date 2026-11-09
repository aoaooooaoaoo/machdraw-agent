"""rod 引擎锚点：题7.3（控制棒微分价值 38.4 pcm/cm）、题2.8（硼浓度 52.524 ppm）、
余弦近似积分/微分价值不变量。

出处：
* 题7.3：v4.0 第7章（k_eff 1.023→1.019、插入 10 cm → 38.4 pcm/cm，答案 D）。
* 题2.8：v4.0 第2章（ΔΣa=0.1×0.0221 cm⁻¹、σ=756 b、A_B=10.82 → 52.524 ppm）。
* 控制棒积分/微分价值定义与“中部最大、两端平缓”：教材 第7章 7.4.1 节
  p.121-123（图7-7/7-8）。
* 硼微分价值/临界硼浓度定义：教材 7.4.3 节 p.125-126。
"""
from app.domain import rod as r


def _close(actual, expected, tol, what=""):
    assert abs(actual - expected) <= tol, (
        f"{what}: 得到 {actual!r}，期望 {expected!r}（容差 {tol!r}）")


def test_rod_differential_worth_exercise_7_3():
    """题7.3：k_eff 1.023→1.019、Δx=10 cm → 微分价值 38.4 pcm/cm。"""
    res = r.rod_differential_worth(1.023, 1.019, 10.0)
    _close(res["results"]["differential_pcm_per_unit"], 38.4, 0.1, "微分价值")


def test_rod_boron_concentration_exercise_2_8():
    """题2.8：ΔΣa=0.1×0.0221 cm⁻¹、σ_硼酸=756 b、A_B=10.82 → C_B=52.524 ppm。"""
    res = r.boron_concentration_from_absorption(0.1 * 0.0221)
    _close(res["results"]["boron_ppm"], 52.524, 0.05, "天然硼浓度 C_B")


def test_rod_integral_worth_cosine_model():
    """余弦近似积分价值：f=0→0；f=0.5→ρ总/2；f=1→ρ总（教材图7-7 S 形）。"""
    total = 1000.0
    _close(r.rod_integral_worth(total, 0.0)["results"]["integral_worth_pcm"], 0.0, 1e-9, "f=0")
    _close(r.rod_integral_worth(total, 0.5)["results"]["integral_worth_pcm"], 500.0, 1e-9, "f=0.5")
    _close(r.rod_integral_worth(total, 1.0)["results"]["integral_worth_pcm"], 1000.0, 1e-9, "f=1")


def test_rod_differential_value_shape():
    """余弦近似微分价值：两端为 0、中部最大 2ρ总/H（教材图7-8）。"""
    total, H = 1000.0, 3.0
    assert abs(r.rod_differential_value(total, H, 0.0)["results"]["differential_pcm_per_unit"]) < 1e-9
    assert abs(r.rod_differential_value(total, H, 1.0)["results"]["differential_pcm_per_unit"]) < 1e-9
    mid = r.rod_differential_value(total, H, 0.5)["results"]["differential_pcm_per_unit"]
    _close(mid, 2.0 * total / H, 1e-9, "中部微分价值")


def test_rod_boron_worth_and_critical_boron():
    """硼价值线性化与临界硼浓度：w=−10 pcm/ppm，补偿 +1000 pcm ⇒ C 降 100 ppm。"""
    w = r.boron_worth(100.0, -10.0)
    _close(w["results"]["delta_rho_pcm"], -1000.0, 1e-12, "硼价值 Δρ")
    cb = r.critical_boron(500.0, 1000.0, -10.0)
    _close(cb["results"]["critical_boron_ppm"], 600.0, 1e-12, "临界硼浓度")
