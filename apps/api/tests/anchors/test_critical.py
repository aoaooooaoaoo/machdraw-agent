"""critical 引擎锚点：教材例题 4.1/4.2、习题 4.5/4.6/4.7、3.1.2 四因子算例。

出处：
* 例题 4.1：教材 第4章 4.2.1 节 p.59-60（平板 k∞=1.06，L²=0.03 m²，λtr=0.0228 m；
  临界厚度含外推 2.222 m、实际 2.190 m；H=2.5 m 时 k=1.0132、ρ=0.01305）。
* 例题 4.2：教材 4.2.1 节 p.60（圆柱 k∞=1.072，L²=0.047 m²，τ=0.0048 m²，
  λtr=0.097 m；H=3.55 m → R=2.88 m；R=3 m → k=1.00242、ρ=0.00241）。
* 习题 4.5：v4.0 第4章（长方体 a=b=0.5 m，c=0.6 m，L=0.0434 m，τ=6 cm²
  → B_g²=106.4 m⁻²、k∞=1.264）。
* 习题 4.6：v4.0 第4章（k∞=1.28，L²=1.8×10⁻² m²，τ=1.20×10⁻² m²
  → 单群 B_m²=15.56、修正单群 9.333、P_L=0.7812/0.7813）。
* 习题 4.7：v4.0 第4章（圆柱 R=0.5 m，H=1.0 m，k∞=1.19，L²=6.6×10⁻⁴ m²，
  τ=0.50×10⁻² m² → k=1.003；临界 H=0.9726 m；含 δr=0.07/δH=0.1 m 时
  B_g²=2.654 m⁻²、k=1.172、ρ0=0.1468）。
* 教材 3.1.2 节 p.32 四因子算例（ε=1.05、Ps=0.9524、p=0.9、Pd=0.9444、
  f=0.8824、η=1.3333 → k∞=1.1118、k_eff=1.000）；习题 3.2（k∞=1.1127、k_eff=0.9957）。
"""
from app.domain import critical as c


def _close(actual, expected, tol, what=""):
    assert abs(actual - expected) <= tol, (
        f"{what}: 得到 {actual!r}，期望 {expected!r}（容差 {tol!r}）")


def test_critical_example_4_1_1_bm2_and_thickness():
    """例题4.1(1)：B_m²=2.0 m⁻²；临界厚度（含外推）2.222 m、实际 2.190 m。"""
    bm = c.buckling_material(1.06, 0.03, 0.0)
    _close(bm["results"]["M2"], 0.03, 1e-12, "M²")
    _close(bm["results"]["Bm2"], 2.0, 1e-9, "B_m²")
    d = c.extrapolation_distance(0.0228)["results"]["d"]
    _close(d, 0.7104 * 0.0228, 1e-12, "外推距离 d")
    cs = c.critical_size("slab", 1.06, 0.03, 0.0, {"H": None}, d=d)
    H = cs["results"]["critical_size"]
    # 教材把 B_m²=2.0 反解得 H(含外推)=2.222 m，再去掉 2d 得 2.190 m（保留 3 位）
    _close(H, 2.190, 2e-3, "平板临界厚度（实际）")
    _close(cs["results"]["Bg2_check"], 2.0, 1e-9, "临界时 B_g²=B_m²")


def test_critical_example_4_1_2_keff_and_rho():
    """例题4.1(2)：H=2.5 m → B_g²=1.539 m⁻²、k=1.0132、ρ=0.01305。"""
    d = 0.7104 * 0.0228
    bg = c.buckling_geometric("slab", {"H": 2.5}, d=d)
    _close(bg["results"]["Bg2"], 1.539, 1e-3, "B_g²")
    ke = c.k_eff_single_group(1.06, 0.03, 0.0, bg["results"]["Bg2"])
    _close(ke["results"]["k_eff"], 1.0132, 1e-4, "k_eff")
    _close(ke["results"]["rho"], 0.01305, 1e-5, "ρ")


def test_critical_example_4_2_1_critical_radius():
    """例题4.2(1)：圆柱 H=3.55 m → 临界半径 R=2.88 m。"""
    d = c.extrapolation_distance(0.097)["results"]["d"]
    _close(d, 0.0689, 1e-4, "外推距离 d")
    bm = c.buckling_material(1.072, 0.047, 0.0048)
    _close(bm["results"]["Bm2"], 1.39, 1e-3, "B_m²")
    cs = c.critical_size("cylinder", 1.072, 0.047, 0.0048, {"R": None, "H": 3.55}, d=d)
    _close(cs["results"]["critical_size"], 2.88, 0.01, "临界半径 R")


def test_critical_example_4_2_2_keff_and_rho():
    """例题4.2(2)：R=3 m → B_g²=1.34 m⁻²、k=1.00242、ρ=0.00241。"""
    d = 0.0689
    bg = c.buckling_geometric("cylinder", {"R": 3.0, "H": 3.55}, d=d)
    _close(bg["results"]["Bg2"], 1.34, 5e-3, "B_g²")
    ke = c.k_eff_single_group(1.072, 0.047, 0.0048, bg["results"]["Bg2"])
    _close(ke["results"]["k_eff"], 1.00242, 1e-4, "k_eff")
    _close(ke["results"]["rho"], 0.00241, 2e-5, "ρ")


def test_critical_exercise_4_5_cuboid():
    """题4.5：长方体 B_g²=106.4 m⁻²；k∞=B_g²(L²+τ)+1=1.264。"""
    bg = c.buckling_geometric("cuboid", {"a": 0.5, "b": 0.5, "c": 0.6})
    _close(bg["results"]["Bg2"], 106.4, 0.1, "B_g²")
    M2 = 0.0434 ** 2 + 6.0e-4
    k_inf = 1.0 + bg["results"]["Bg2"] * M2
    _close(k_inf, 1.264, 1e-3, "k∞")


def test_critical_exercise_4_6_buckling_and_leakage():
    """题4.6：单群 B_m²=15.56；修正单群 B_m²=9.333；P_L=0.7813。"""
    bm1 = c.buckling_material(1.28, 1.8e-2, 0.0)
    _close(bm1["results"]["Bm2"], 15.56, 0.01, "单群 B_m²")
    bm2 = c.buckling_material(1.28, 1.8e-2, 1.2e-2)
    _close(bm2["results"]["Bm2"], 9.333, 0.01, "修正单群 B_m²")
    pl = c.leakage_probabilities(1.28, 1.8e-2, 1.2e-2, bm2["results"]["Bm2"])
    _close(pl["results"]["P_L"], 0.7813, 1e-4, "P_L")


def test_critical_exercise_4_7_cylinder_and_reflector():
    """题4.7：k_eff=1.003；临界 H=0.9726 m；含反射层节省 ρ0=0.1468。"""
    bg = c.buckling_geometric("cylinder", {"R": 0.5, "H": 1.0})
    _close(bg["results"]["Bg2"], 33.01, 0.02, "B_g²")
    ke = c.k_eff_single_group(1.19, 6.6e-4, 0.5e-2, bg["results"]["Bg2"])
    _close(ke["results"]["k_eff"], 1.003, 1e-3, "k_eff")
    cs = c.critical_size("cylinder", 1.19, 6.6e-4, 0.5e-2, {"R": 0.5, "H": None})
    _close(cs["results"]["critical_size"], 0.9726, 1e-3, "临界水位 H")
    bg3 = c.buckling_geometric("cylinder", {"R": 1.66, "H": 3.5},
                               reflector_saving={"R": 0.07, "H": 0.1})
    _close(bg3["results"]["Bg2"], 2.654, 5e-3, "含反射层的 B_g²")
    ke3 = c.k_eff_single_group(1.19, 6.6e-4, 0.5e-2, bg3["results"]["Bg2"])
    _close(ke3["results"]["k_eff"], 1.172, 1e-3, "含反射层 k_eff")
    _close(ke3["results"]["rho"], 0.1468, 1e-3, "初始反应性 ρ0")


def test_critical_four_factor_textbook_example():
    """教材3.1.2 p.32 四因子算例：k∞=1.1118、k_eff=1.000。"""
    r = c.four_factor(1.05, 0.9, 0.8824, 1.3333, Ps=0.9524, Pd=0.9444)
    _close(r["results"]["k_inf"], 1.1118, 1e-3, "k∞")
    _close(r["results"]["k_eff"], 1.0, 1e-3, "k_eff")


def test_critical_four_factor_exercise_3_2():
    """题3.2：k∞=1.1127、k_eff=0.9957（ε=1.05,p=0.9,f=0.882,η=1.335,Ps=0.952,Pd=0.94）。"""
    r = c.four_factor(1.05, 0.9, 0.882, 1.335, Ps=0.952, Pd=0.94)
    _close(r["results"]["k_inf"], 1.1127, 1e-4, "k∞")
    _close(r["results"]["k_eff"], 0.9957, 1e-4, "k_eff")
