"""poison 引擎锚点：平衡氙/钐量级、钐平衡与通量无关、碘坑指标。

出处：
* 平衡氙中毒 0.04~0.05（GW 级压水堆）：教材 第6章 6.2.1 节 p.105。
* 平衡钐中毒约 0.007，且平衡浓度与通量无关：教材 6.2.2 节 p.108。
* 碘坑/强迫停堆/允许停堆/最大碘坑时间/碘坑深度定义：教材 6.2.1 p.106。
* 碘-氙平衡式(6-11)(6-12)：p.104；停堆解(6-17)(6-18)：p.106；
  钷-钐平衡式(6-24)(6-25)：p.108；习题 v4.0【题6.8】【题6.9】同式。

说明：本引擎的衰变常数/产额采用课程通用 ENDF/B 值（教材只给量级与公式），
见 ``app/domain/poison.py`` 顶部“核数据取值说明”；锚点校验的是**物理量级与
解析关系**（教材明文结论），而非某一核数据库的小数位。
"""
from app.domain import poison as p


def _close(actual, expected, tol, what=""):
    assert abs(actual - expected) <= tol, (
        f"{what}: 得到 {actual!r}，期望 {expected!r}（容差 {tol!r}）")


def test_poison_xenon_equilibrium_magnitude():
    """教材 p.105：GW 级压水堆平衡氙中毒约 0.04~0.05（默认教学栅元参数）。"""
    r = p.xenon_equilibrium()
    rho = r["results"]["rho_xe"]
    assert -0.050 <= rho <= -0.040, f"平衡氙反应性当量 {rho} 不在 -0.04~-0.05"
    # 平衡式自洽：N_Xe=(γI+γXe)ΣfΦ/(λXe+σXeΦ)
    flux = r["inputs"]["flux"]
    expected = ((p.I135["fission_yield"] + p.XE135["fission_yield"])
                * p.SIGMA_F_DEFAULT * flux
                / (p.XE135["lambda"] + p.XE135["sigma_a_b"] * 1e-24 * flux))
    _close(r["results"]["N_Xe_eq"], expected, expected * 1e-12, "N_Xe 平衡式")


def test_poison_samarium_equilibrium_magnitude():
    """教材 p.108：GW 级压水堆平衡钐中毒约 0.007（N_Sm=γPmΣf/σSm）。"""
    r = p.samarium_equilibrium()
    rho = r["results"]["rho_sm"]
    assert -0.010 <= rho <= -0.004, f"平衡钐反应性当量 {rho} 不在约 0.007 附近"
    expected = p.PM149["fission_yield"] * p.SIGMA_F_DEFAULT / (4.0e4 * 1e-24)
    _close(r["results"]["N_Sm_eq"], expected, expected * 1e-12, "N_Sm=γPmΣf/σSm")


def test_poison_samarium_equilibrium_flux_independent():
    """教材 p.108 明确结论：平衡钐浓度与中子通量水平无关。"""
    a = p.samarium_equilibrium(flux=1.0e13)["results"]["N_Sm_eq"]
    b = p.samarium_equilibrium(flux=1.0e14)["results"]["N_Sm_eq"]
    c = p.samarium_equilibrium(flux=5.0e14)["results"]["N_Sm_eq"]
    _close(a, b, a * 1e-12, "N_Sm(1e13) vs N_Sm(1e14)")
    _close(b, c, b * 1e-12, "N_Sm(1e14) vs N_Sm(5e14)")


def test_poison_xenon_increases_with_flux_and_saturates():
    """平衡氙浓度随通量增大并趋于饱和（教材 p.105 功率越大中毒越大）。"""
    n1 = p.xenon_equilibrium(flux=1.0e13)["results"]["N_Xe_eq"]
    n2 = p.xenon_equilibrium(flux=3.0e13)["results"]["N_Xe_eq"]
    n3 = p.xenon_equilibrium(flux=1.0e14)["results"]["N_Xe_eq"]
    assert n1 < n2 < n3, "平衡氙浓度应随通量单调增加"
    # 高通量饱和：N_Xe→(γI+γXe)Σf/σXe
    sat = ((p.I135["fission_yield"] + p.XE135["fission_yield"]) * p.SIGMA_F_DEFAULT
           / (p.XE135["sigma_a_b"] * 1e-24))
    n4 = p.xenon_equilibrium(flux=1.0e18)["results"]["N_Xe_eq"]
    _close(n4, sat, sat * 1e-3, "高通量饱和氙浓度")


def test_poison_iodine_pit_metrics():
    """停堆后碘坑：t_max 在数小时量级、坑深为负、Xe 先增后减（教材 p.106）。"""
    r = p.xenon_transient(flux=3.0e13, t_irr=4800.0, t_down=120.0,
                          time_unit="h", rho_ex0_pcm=3000.0)
    tmax = r["results"]["max_pit_time_h"]
    assert 4.0 < tmax < 15.0, f"最大碘坑时刻 {tmax} h 不在合理范围"
    depth = r["results"]["iodine_pit_depth_pcm"]
    assert depth < 0, f"碘坑深度应为额外负反应性，得到 {depth}"
    # 停堆时刻与 t_max 时刻的氙浓度比较
    shut_xe = r["results"]["N_Xe_at_shutdown"]
    assert max(r["results"]["N_Xe"]) > shut_xe, "停堆后氙浓度应先增加"
    # 足够长时间后氙衰变到接近 0
    tail = r["results"]["N_Xe"][-1]
    assert tail < 0.05 * shut_xe, "120 h 后氙应显著衰变"


def test_poison_samarium_after_shutdown_accumulates():
    """停堆后 Pm→Sm：N_Sm 单调增加到 N_Sm0+N_Pm0（教材 p.108-109）。"""
    r = p.samarium_transient(flux=3.0e13, t_irr=4800.0, t_down=60 * 24.0,
                             time_unit="h")
    shut = r["results"]["shutdown_time_h"]
    after = [(t, v) for t, v in zip(r["results"]["time_h"], r["results"]["N_Sm"]) if t >= shut]
    vals = [v for _, v in after]
    assert all(vals[k] <= vals[k + 1] + 1e-6 for k in range(len(vals) - 1)), "Sm 应单调增加"
    expected = r["results"]["N_Sm_after_full_decay"]
    _close(vals[-1], expected, expected * 1e-3, "长期停堆后 N_Sm")


def test_poison_reactivity_worth_linear():
    """毒物反应性当量 ρ≈−σN/Σa（教材 6.2 式6-5 一阶近似）。"""
    n = 5.0e15
    r = p.reactivity_worth(n)
    expected = -(p.XE135["sigma_a_b"] * 1e-24 * n) / p.SIGMA_A_FUEL_DEFAULT
    _close(r["results"]["rho"], expected, 1e-15, "ρ_Xe")
