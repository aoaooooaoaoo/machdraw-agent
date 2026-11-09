"""reactivity 引擎锚点：题8.8（pcm 换算）、题7.6（叠加）、题7.8（功率亏损）、题3.4（单位）。

出处：
* 题8.8：v4.0 第8章（k_eff,1=0.97 → ρ1=−3092.8 pcm；k_eff,2=0.994 → ρ2=−603.62 pcm；
  Δρ=2489.2 pcm）。
* 题7.6：v4.0 第7章（−6.918%+2.675%+1.575%−1.040%+0.500% = −3.208% Δk/k）。
* 题7.8：v4.0 第7章（总功率系数 −0.020%/1%FP，功率 100%→30%FP → +1.4% Δk/k）。
* 题3.4：v4.0 第3章（1 pcm=10⁻⁵、1 mk=10⁻³、1$=β=0.0065）。
* 反应性定义 ρ=(k−1)/k：教材 第3章 3.1.1 节 p.33；温度系数：7.1 节 p.116。
"""
from app.domain import reactivity as r


def _close(actual, expected, tol, what=""):
    assert abs(actual - expected) <= tol, (
        f"{what}: 得到 {actual!r}，期望 {expected!r}（容差 {tol!r}）")


def test_reactivity_exercise_8_8_pcm():
    """题8.8：k=0.97 → −3092.8 pcm；k=0.994 → −603.62 pcm；差 2489.2 pcm。"""
    a = r.rho_from_k(0.97)
    b = r.rho_from_k(0.994)
    _close(a["results"]["rho_pcm"], -3092.8, 0.1, "ρ1 (pcm)")
    _close(b["results"]["rho_pcm"], -603.62, 0.1, "ρ2 (pcm)")
    _close(b["results"]["rho_pcm"] - a["results"]["rho_pcm"], 2489.2, 0.2, "Δρ (pcm)")


def test_reactivity_exercise_7_6_combination():
    """题7.6：五项反应性叠加 = −3.208% Δk/k（停堆深度 3.208%）。"""
    terms = [
        {"name": "控制棒", "value": -6.918, "unit": "%"},
        {"name": "氙", "value": 2.675, "unit": "%"},
        {"name": "功率亏损", "value": 1.575, "unit": "%"},
        {"name": "硼", "value": -1.040, "unit": "%"},
        {"name": "温度", "value": 0.500, "unit": "%"},
    ]
    res = r.combine_terms(terms)
    _close(res["results"]["rho_percent"], -3.208, 1e-9, "ΣΔρ (%)")
    _close(res["results"]["rho_pcm"], -3208.0, 1e-6, "ΣΔρ (pcm)")
    assert res["results"]["verdict"] == "次临界"


def test_reactivity_exercise_7_8_power_defect():
    """题7.8：−0.020%/1%FP × (30−100)%FP = +1.4% Δk/k。"""
    res = r.power_defect(-0.020, 100.0, 30.0)
    _close(res["results"]["delta_rho_percent"], 1.4, 1e-12, "功率亏损 (%)")
    _close(res["results"]["delta_rho_pcm"], 1400.0, 1e-9, "功率亏损 (pcm)")


def test_reactivity_unit_definitions():
    """题3.4：1$=β=0.0065=650 pcm；1 mk=100 pcm；1%=1000 pcm。"""
    a = r.unit_convert(1.0, "$", "pcm")
    _close(a["results"]["rho_pcm"], 650.0, 1e-9, "1$ → pcm")
    b = r.unit_convert(1.0, "mk", "pcm")
    _close(b["results"]["rho_pcm"], 100.0, 1e-9, "1 mk → pcm")
    c = r.unit_convert(1.0, "%", "pcm")
    _close(c["results"]["rho_pcm"], 1000.0, 1e-9, "1% → pcm")
    d = r.unit_convert(200.0, "pcm", "dk/k")
    _close(d["results"]["converted"], 0.002, 1e-15, "200 pcm → Δk/k")


def test_reactivity_k_rho_roundtrip():
    """k↔ρ 互逆：ρ=(k−1)/k，k=1/(1−ρ)。"""
    for k in (0.95, 0.99, 0.998, 1.0, 1.002, 1.05):
        rho = r.rho_from_k(k)["results"]["rho"]
        back = r.k_from_rho(rho)["results"]["k_eff"]
        _close(back, k, 1e-15, f"k={k} 往返")


def test_reactivity_temperature_coefficient():
    """温度系数定义：T 280→300 K、ρ 0→−0.001 ⇒ α=−5×10⁻⁵/K=−5 pcm/K。"""
    res = r.temperature_coefficient(0.0, -0.001, 280.0, 300.0)
    _close(res["results"]["alpha_dk_per_K"], -5e-5, 1e-18, "α (Δk/k/K)")
    _close(res["results"]["alpha_pcm_per_K"], -5.0, 1e-12, "α (pcm/K)")
    assert "负" in res["results"]["sign"]
