# 锚点测试清单（`apps/api/tests/anchors/`）

> 运行：`D:\python\python.exe apps/api/tests/run_anchors.py`
> 结果：**68/68 通过**（2026-11-09）。
>
> 约定：每条锚点写明「出处 / 输入 / 期望 / 容差」。数值期望来自教材例题、章末习题
> 或 v4.0 课后习题解答的原答案；教材答案本身保留有限位有效数字，因此容差按有效位
> 放宽。物理不变量类锚点（无原题数值）在“期望”列注明“不变量”，并在测试 docstring
> 写清依据。

## 1. critical（单群/修正单群临界，9 条）

| # | 测试函数 | 出处 | 输入 | 期望 | 容差 |
|---|---|---|---|---|---|
| 1 | `test_critical_example_4_1_1_bm2_and_thickness` | 教材例4.1 (4.2.1 p.59) | k∞=1.06, L²=0.03 m², λtr=0.0228 m | B_m²=2.0 m⁻²；实际临界厚度 H=2.190 m（含外推 2.222 m） | 1e-9；2e-3 |
| 2 | `test_critical_example_4_1_2_keff_and_rho` | 教材例4.1 (p.59-60) | H=2.5 m | B_g²=1.539 m⁻²；k=1.0132；ρ=0.01305 | 1e-3；1e-4；1e-5 |
| 3 | `test_critical_example_4_2_1_critical_radius` | 教材例4.2 (p.60) | k∞=1.072, L²=0.047, τ=0.0048 m², λtr=0.097 m, H=3.55 m | d=0.0689 m；B_m²=1.39 m⁻²；R=2.88 m | 1e-4；1e-3；0.01 |
| 4 | `test_critical_example_4_2_2_keff_and_rho` | 教材例4.2 (p.60) | R=3 m, H=3.55 m | B_g²=1.34 m⁻²；k=1.00242；ρ=0.00241 | 5e-3；1e-4；2e-5 |
| 5 | `test_critical_exercise_4_5_cuboid` | 题4.5 (v4.0 第4章) | a=b=0.5 m, c=0.6 m；L=0.0434 m, τ=6 cm² | B_g²=106.4 m⁻²；k∞=1.264 | 0.1；1e-3 |
| 6 | `test_critical_exercise_4_6_buckling_and_leakage` | 题4.6 (v4.0 第4章) | k∞=1.28, L²=1.8e-2, τ=1.2e-2 m² | 单群 B_m²=15.56；修正 9.333；P_L=0.7813 | 0.01；1e-4 |
| 7 | `test_critical_exercise_4_7_cylinder_and_reflector` | 题4.7 (v4.0 第4章) | R=0.5, H=1.0 m；k∞=1.19, L²=6.6e-4, τ=5e-3 m²；含 δr=0.07/δH=0.1 m | B_g²=33.01；k=1.003；临界 H=0.9726 m；含反射层 B_g²=2.654、k=1.172、ρ0=0.1468 | 0.02/1e-3/1e-3/5e-3/1e-3/1e-3 |
| 8 | `test_critical_four_factor_textbook_example` | 教材 3.1.2 p.32 算例 | ε=1.05, p=0.9, f=0.8824, η=1.3333；Ps=0.9524, Pd=0.9444 | k∞=1.1118；k_eff=1.000 | 1e-3 |
| 9 | `test_critical_four_factor_exercise_3_2` | 题3.2 (v4.0 第3章) | ε=1.05,p=0.9,f=0.882,η=1.335；Ps=0.952,Pd=0.94 | k∞=1.1127；k_eff=0.9957 | 1e-4 |

## 2. kinetics（点堆动力学，7 条）

| # | 测试函数 | 出处 | 输入 | 期望 | 容差 |
|---|---|---|---|---|---|
| 1 | `test_kinetics_beta_total_from_table_2_3` | 教材表2-3 (2.5.3 p.27) | 六组 β_i、平均寿期 τ_i | β=0.0065；Σβ_iτ_i≈0.0828 s；先驱核平均寿期 12.74 s | 1e-12；0.080~0.086；0.05 |
| 2 | `test_kinetics_prompt_neutrons_exercise_2_10` | 题2.10 (v4.0 第2章) | n_缓发=10⁵，β=0.0065 | n_瞬发=1.528×10⁷ | 1e4 |
| 3 | `test_kinetics_period_exercise_8_5` | 题8.5 (v4.0 第8章) | n₂/n₁=5/3，Δt=120 s | T=234.91 s | 0.01 |
| 4 | `test_kinetics_inhour_root_satisfies_equation` | 教材式8-17 (8.2 p.130) | ρ=200 pcm，l=1e-4 s | 倒时方程残差 <1e-12；7 个根 | 1e-12 |
| 5 | `test_kinetics_zero_rho_is_critical` | 临界定义 | ρ=0 | s=0，T=∞ | 精确 |
| 6 | `test_kinetics_prompt_critical_and_jump` | 教材 8.2 p.132 | ρ=β；ρ=0 | ρ/β=1、瞬发临界；跳跃比 1 / ∞ | 1e-12 |
| 7 | `test_kinetics_response_curve_invariants` | 点堆方程 8-13/8-14 | ρ=0；ρ=200 pcm | n/n₀≡1；n(5T)/n(4T)=e | 1e-9；0.05 |

## 3. poison（碘氙/钐，7 条）

| # | 测试函数 | 出处 | 输入 | 期望 | 容差 |
|---|---|---|---|---|---|
| 1 | `test_poison_xenon_equilibrium_magnitude` | 教材 6.2.1 p.105 | 默认教学栅元 Φ=3e13, Σf=0.28, Σa=0.35 | −0.050≤ρ_Xe≤−0.040；N_Xe 平衡式自洽 | 量级；1e-12 相对 |
| 2 | `test_poison_samarium_equilibrium_magnitude` | 教材 6.2.2 p.108 | 同上 | −0.010≤ρ_Sm≤−0.004；N_Sm=γPmΣf/σSm | 量级；1e-12 相对 |
| 3 | `test_poison_samarium_equilibrium_flux_independent` | 教材 p.108 结论 | Φ=1e13/1e14/5e14 | N_Sm 与 Φ 无关 | 1e-12 相对 |
| 4 | `test_poison_xenon_increases_with_flux_and_saturates` | 教材 p.105 | Φ=1e13…1e18 | N_Xe 单调增；饱和值 (γI+γXe)Σf/σXe | 1e-3 相对 |
| 5 | `test_poison_iodine_pit_metrics` | 教材 6.2.1 p.106 | Φ=3e13、运行 200 d、停堆 120 h | 4 h<t_max<15 h；坑深<0；Xe 先增后衰 | 量级 |
| 6 | `test_poison_samarium_after_shutdown_accumulates` | 教材 p.108-109 | 运行 200 d、停堆 60 d | N_Sm 单调 → N_Sm0+N_Pm0 | 1e-3 相对 |
| 7 | `test_poison_reactivity_worth_linear` | 教材式6-5 | N=5e15 cm⁻³ | ρ=−σ_Xe N/Σa | 1e-15 |

## 4. burnup（燃耗/铀消耗/循环长度，8 条）

| # | 测试函数 | 出处 | 输入 | 期望 | 容差 |
|---|---|---|---|---|---|
| 1 | `test_burnup_exercise_2_5_energy_to_mass` | 题2.5 (v4.0 第2章) | E=1 kW·h，α=0 | 4.390×10⁻⁸ kg | 1e-10 |
| 2 | `test_burnup_exercise_2_6_small_plant` | 题2.6 | Pe=150 MW、η=30% → P=500 MW，1 h，α=0.17 | 0.02568 kg | 1e-4 |
| 3 | `test_burnup_exercise_2_7_annual_consumption` | 题2.7 | Pe=1000 MW、ηe=0.32、LF=0.85、1 a、α=0.17 | 1.195 t | 5e-3 |
| 4 | `test_burnup_exercise_6_4_uranium_loading` | 题6.4 | Pe=1200 MW、ηe=0.30、LF=0.8、BU=15000、换 1/3 | 233.6 tU；P_th=3200 MW | 0.1；1e-6 |
| 5 | `test_burnup_textbook_daily_consumption` | 教材 3.1.3 p.33 | P=1 MW、1 d、α=0.169 | 1.23×10⁻³ kg | 2e-5 |
| 6 | `test_burnup_depth_definition` | 教材 6.1 p.98-99 | P=3000 MW、t=30 d、m=72 tU | 1250 MWd/tU（能量 90000 MWd 反算一致） | 1e-9 |
| 7 | `test_burnup_linear_reactivity_model` | 教材 9.2.1、题9.2 | ρ0=0.05、α=7e-4、n=3、m=72 tU、P=3000 MW | B_c=35.714、B_d=107.14、T=0.857 EFPD、ρ_EOC=0 | 1e-9 / 1e-12 |
| 8 | `test_burnup_conversion_ratio` | 教材 9.4.1 p.154 | CR=0.6 / 1.25 | 非增殖/增殖判定 | 1e-12 |

## 5. reactivity（反应性换算与系数，6 条）

| # | 测试函数 | 出处 | 输入 | 期望 | 容差 |
|---|---|---|---|---|---|
| 1 | `test_reactivity_exercise_8_8_pcm` | 题8.8 (v4.0 第8章) | k=0.97 / 0.994 | −3092.8 / −603.62 pcm；Δ=2489.2 pcm | 0.1/0.2 |
| 2 | `test_reactivity_exercise_7_6_combination` | 题7.6 | 五项 %Δk/k 叠加 | −3.208% = −3208 pcm；次临界 | 1e-9 |
| 3 | `test_reactivity_exercise_7_8_power_defect` | 题7.8 | α_P=−0.020%/%FP，100%→30%FP | +1.4% = +1400 pcm | 1e-12 |
| 4 | `test_reactivity_unit_definitions` | 题3.4 | 1$/1 mk/1%/200 pcm | 650/100/1000 pcm；0.002 Δk/k | 1e-9/1e-15 |
| 5 | `test_reactivity_k_rho_roundtrip` | ρ=(k−1)/k | k∈{0.95…1.05} | k→ρ→k 往返 | 1e-15 |
| 6 | `test_reactivity_temperature_coefficient` | 教材 7.1 p.116 | T 280→300 K、ρ 0→−0.001 | α=−5×10⁻⁵/K = −5 pcm/K | 1e-18/1e-12 |

## 6. spectrum（能谱与群常数，6 条）

| # | 测试函数 | 出处 | 输入 | 期望 | 容差 |
|---|---|---|---|---|---|
| 1 | `test_spectrum_group_average_1v_analytic` | 补充2.1 | σ=C/√E，1/E 谱，[1,1e5] eV | 解析 2C(1/√E₁−1/√E₂)/ln(E₂/E₁) | 1e-6 相对 |
| 2 | `test_spectrum_watt_mean_energy` | 教材 5.1 p.79 | Watt 谱 | 平均能量≈2 MeV | 1.9~2.1 |
| 3 | `test_spectrum_maxwell_peak_at_kt` | 教材 5.4 p.88-90 | T=293.6 K | E_max=0.0253 eV | 2e-4；2% |
| 4 | `test_spectrum_neutron_temperature_example_5_1` | 例5.1 | T_M=535.5 K、Σa=9.71、ξΣs=69.5 | T_n=613 K | 0.5 K |
| 5 | `test_spectrum_fermi_1_over_e` | 教材 5.2 p.80-82 | E₁=1 eV、E₂=1000 eV | φ(E₁)/φ(E₂)=E₂/E₁ | 1e-12 |
| 6 | `test_spectrum_normalized_curves` | Maxwell 归一化 | T=293.6 K | ∫φdE=1 | 1e-6 |

## 7. rod（控制棒/硼，5 条）

| # | 测试函数 | 出处 | 输入 | 期望 | 容差 |
|---|---|---|---|---|---|
| 1 | `test_rod_differential_worth_exercise_7_3` | 题7.3 (v4.0 第7章) | k 1.023→1.019，Δx=10 cm | 38.4 pcm/cm | 0.1 |
| 2 | `test_rod_boron_concentration_exercise_2_8` | 题2.8 | ΔΣa=0.1×0.0221 cm⁻¹、σ=756 b、A_B=10.82 | C_B=52.524 ppm | 0.05 |
| 3 | `test_rod_integral_worth_cosine_model` | 教材 7.4.1 p.122-123 | ρ_总=1000 pcm，f=0/0.5/1 | 0/500/1000 pcm | 1e-9 |
| 4 | `test_rod_differential_value_shape` | 教材图7-8 | f=0/0.5/1 | 0；2ρ_总/H；0 | 1e-9 |
| 5 | `test_rod_boron_worth_and_critical_boron` | 教材 7.4.3 p.125-126 | w=−10 pcm/ppm、C₀=500、补偿 +1000 pcm | C_crit=600 ppm；Δρ=−1000 pcm | 1e-12 |

## 8. 工具层与 SVG（16 + 4 条）

| 类别 | 测试函数 | 说明 |
|---|---|---|
| 注册 | `test_tools_registration` | 11 个工具、name==文件名、parameters 含 query |
| critical | `test_tool_critical_curvature_query` | “求临界曲率”→ B_m²=3.333 m⁻²，不反解尺寸 |
| critical | `test_tool_critical_cylinder_keff_query` | 圆柱 R=50 cm、H=100 cm → B_g²=33.0 m⁻²、k_eff=0.665 |
| critical | `test_tool_critical_sphere_radius_query` | “裸球R=50cm”识别为球并算 k_eff |
| burnup | `test_tool_burnup_natural_days_query` | “运行300天” → 1.125×10⁴ MWd/tU |
| kinetics | `test_tool_kinetics_query` | “+0.2$” → plot、ρ/β=0.2 |
| kinetics | `test_tool_kinetics_period_ratio_query` | n₂/n₁=5/3、Δt=120 s → T=234.91 s |
| kinetics | `test_tool_kinetics_dollar_units` | +0.2$ / 0.2 dollar / ρ=1$ 单位解析 |
| kinetics | `test_tool_kinetics_response_finite` | RK4 刚性稳定，无 nan/inf |
| poison | `test_tool_poison_query` | 碘坑：平衡 ρ_Xe∈[−0.05,−0.04] |
| reactivity | `test_tool_reactivity_query` | k=0.998 → −200.4 pcm |
| spectrum | `test_tool_spectrum_query` | Maxwell T=293.6 K → 峰值 0.0253 eV |
| 兜底 | `test_tool_failure_has_examples` | 空 query → ok=False + 示例，不抛异常 |
| 契约 | `test_artifact_contract_calc_and_plot` | calc/plot 字段、series 点、svg 前缀 |
| 契约 | `test_tool_artifacts_json_serializable` | 严格 JSON（无 NaN/Infinity） |
| 契约 | `test_artifact_plot_svg_self_contained` | 自包含 SVG、无 script、中文字体 |
| SVG | `test_svg_basic_structure` 等 4 条 | 900×520、viewBox、多序列、图例、对数轴、转义 |
