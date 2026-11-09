"""spectrum 引擎锚点：补充2.1（1/v 群平均解析式）、Watt 平均能量、Maxwell 峰位、例5.1。

出处：
* 补充2.1：v4.0 第2章（σ∝1/√E、φ∝1/E ⇒ σ_g=2C(1/√E₁−1/√E₂)/ln(E₂/E₁)）。
* Watt 裂变谱平均能量约 2 MeV：教材 第5章 5.1 节 p.79。
* Maxwell 谱最可几能量 E=kT、293.6 K ↔ 0.0253 eV：教材 5.4 节 p.88-90。
* 例5.1：T_M=535.5 K、Σa(0.0253)=9.71 m⁻¹、ξΣs=69.5 m⁻¹ → T_n=613 K：
  v4.0 第5章【例5.1】；公式见教材 5.4 p.88-90。
"""
import math

from app.domain import spectrum as s


def _close(actual, expected, tol, what=""):
    assert abs(actual - expected) <= tol, (
        f"{what}: 得到 {actual!r}，期望 {expected!r}（容差 {tol!r}）")


def test_spectrum_group_average_1v_analytic():
    """补充2.1：1/v 截面在 1/E 谱下的群平均 = 2C(1/√E₁−1/√E₂)/ln(E₂/E₁)。"""
    C = 3.0
    e1, e2 = 1.0, 1.0e5
    r = s.group_average(lambda E: C / math.sqrt(E), (e1, e2), weight="fermi")
    analytic = 2.0 * C * (1.0 / math.sqrt(e1) - 1.0 / math.sqrt(e2)) / math.log(e2 / e1)
    _close(r["results"]["sigma_g"], analytic, analytic * 1e-6, "σ_g")


def test_spectrum_watt_mean_energy():
    """教材 p.79：裂变中子平均能量约 2 MeV（Watt 谱数值积分）。"""
    r = s.spectrum_curve("watt", n_points=200)
    mean = r["results"]["mean_energy_mev"]
    assert 1.9 <= mean <= 2.1, f"Watt 谱平均能量 {mean} MeV 不在约 2 MeV"


def test_spectrum_maxwell_peak_at_kt():
    """教材 p.89-90：Maxwell 通量谱峰在 E=kT；293.6 K 对应 0.0253 eV。"""
    r = s.most_probable_energy()
    _close(r["results"]["most_probable_energy_ev"], 0.0253, 2e-4, "E_max=kT")
    curve = s.spectrum_curve("maxwell", n_points=2000, e_min_ev=1e-4, e_max_ev=1.0)
    peak = curve["results"]["peak_energy_ev"]
    assert abs(peak - 0.0253) / 0.0253 < 0.02, f"热谱峰值 {peak} eV 应≈0.0253 eV"


def test_spectrum_neutron_temperature_example_5_1():
    """例5.1：T_M=535.5 K、Σa=9.71 m⁻¹、ξΣs=69.5 m⁻¹ → T_n=613 K。"""
    r = s.neutron_temperature(535.5, 9.71, 69.5)
    _close(r["results"]["T_n"], 613.0, 0.5, "中子温度 T_n")


def test_spectrum_fermi_1_over_e():
    """1/E 慢化谱：φ(E₁)/φ(E₂)=E₂/E₁（教材 5.2 p.80-82）。"""
    e1, e2 = 1.0, 1000.0
    _close(s.fermi_spectrum(e1) / s.fermi_spectrum(e2), e2 / e1, 1e-12, "φ 比值")


def test_spectrum_normalized_curves():
    """归一化检查：Maxwell 谱 ∫φdE≈1。"""
    import app.domain.spectrum as sp
    integral = sp._simpson(lambda e: sp.maxwellian(e), 0.0, 2.0, 4000)
    _close(integral, 1.0, 1e-6, "Maxwell 归一化积分")
