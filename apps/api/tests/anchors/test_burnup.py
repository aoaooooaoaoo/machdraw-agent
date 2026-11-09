"""burnup 引擎锚点：题2.5/2.6/2.7（铀消耗）、题6.4（装载量）、线性反应性模型。

出处：
* 题2.5：v4.0 第2章（1 kW·h，α=0 → 4.390×10⁻⁸ kg ²³⁵U 裂变）。
* 题2.6：v4.0 第2章（Pe=150 MW、η=30%、1 h、α=0.17 → 0.02568 kg ²³⁵U 消耗）。
* 题2.7：v4.0 第2章（Pe=1000 MW、ηe=32%、负荷因子 0.85、1 a → 1.195 t ²³⁵U）。
* 题6.4：v4.0 第6章（Pe=1200 MW、ηe=0.30、负荷因子 0.8、BU=15000 MWd/tU、
  每年换 1/3 → 铀装载量 233.6 tU）。
* 教材 3.1.3 p.33 式(3-15)：α=0.169、1 MW → 1.23×10⁻³ kg/d。
* 教材 9.2.1 p.145-147 / 题9.2：线性反应性模型 B_c=2ρ0/((n+1)α)、B_d=nB_c。
"""
from app.domain import burnup as b


def _close(actual, expected, tol, what=""):
    assert abs(actual - expected) <= tol, (
        f"{what}: 得到 {actual!r}，期望 {expected!r}（容差 {tol!r}）")


def test_burnup_exercise_2_5_energy_to_mass():
    """题2.5：1 kW·h（α=0）需要 4.390×10⁻⁸ kg ²³⁵U 裂变。"""
    r = b.mass_for_energy(1.0)
    _close(r["results"]["fissioned_mass_kg"], 4.390e-8, 1e-10, "²³⁵U 裂变质量")


def test_burnup_exercise_2_6_small_plant():
    """题2.6：Pe=150 MW、η=30%、1 h、α=0.17 → 0.02568 kg。"""
    P_th = 150.0 / 0.30
    r = b.u235_consumption(P_th, 1.0 / 24.0, alpha=0.17)
    _close(r["results"]["consumed_mass_kg"], 0.02568, 1e-4, "²³⁵U 消耗质量")


def test_burnup_exercise_2_7_annual_consumption():
    """题2.7：Pe=1000 MW、ηe=0.32、负荷因子 0.85、1 a → 1.195 t ²³⁵U。"""
    P_avg = 1000.0 * 0.85 / 0.32
    r = b.u235_consumption(P_avg, 365.0, alpha=0.17)
    _close(r["results"]["consumed_mass_t"], 1.195, 5e-3, "年消耗 ²³⁵U（t）")


def test_burnup_exercise_6_4_uranium_loading():
    """题6.4：平衡换料估算 → 铀装载量 233.6 tU。"""
    r = b.uranium_loading(1200.0, 0.30, 0.8, 15000.0, 1.0 / 3.0)
    _close(r["results"]["total_loading_tu"], 233.6, 0.1, "铀装载量")
    _close(r["results"]["P_th_avg_mw"], 3200.0, 1e-6, "平均热功率")


def test_burnup_textbook_daily_consumption():
    """教材 3.1.3 p.33：α=0.169、1 MW → 1.23×10⁻³ kg/d。"""
    r = b.u235_consumption(1.0, 1.0, alpha=0.169)
    _close(r["results"]["consumed_mass_kg"], 1.23e-3, 2e-5, "每日消耗量")


def test_burnup_depth_definition():
    """燃耗深度 BU=P·t/m（教材 6.1 p.98-99）：3000 MW、30 d、72 tU → 1250 MWd/tU。"""
    r = b.burnup_depth(3000.0, 30.0, 72.0)
    _close(r["results"]["burnup_mwd_tu"], 1250.0, 1e-9, "燃耗深度")
    r2 = b.burnup_from_energy(90000.0, 72.0)
    _close(r2["results"]["burnup_mwd_tu"], 1250.0, 1e-9, "由能量反算燃耗")


def test_burnup_linear_reactivity_model():
    """题9.2：B_c=2ρ0/((n+1)α)、B_d=n·B_c；T=B_c·m/P。"""
    rho0, alpha, n, m, P = 0.05, 7.0e-4, 3, 72.0, 3000.0
    r = b.cycle_length_linear(rho0, alpha, n, m, P)
    Bc_expected = 2.0 * rho0 / ((n + 1) * alpha)
    _close(r["results"]["cycle_burnup_mwd_tu"], Bc_expected, 1e-9, "B_c")
    _close(r["results"]["discharge_burnup_mwd_tu"], n * Bc_expected, 1e-9, "B_d")
    _close(r["results"]["cycle_length_efpd"], Bc_expected * m / P, 1e-9, "循环长度")
    # 循环末堆芯反应性应为 0
    _close(r["results"]["reactivity_at_eoc"], 0.0, 1e-12, "循环末堆芯 ρ")


def test_burnup_conversion_ratio():
    """转换比/增殖比定义（教材 9.4.1 p.154-155）。"""
    r = b.conversion_ratio(0.6, 1.0)
    _close(r["results"]["CR"], 0.6, 1e-12, "CR")
    assert r["results"]["is_breeder"] is False
    r2 = b.conversion_ratio(1.25, 1.0)
    assert r2["results"]["is_breeder"] is True
