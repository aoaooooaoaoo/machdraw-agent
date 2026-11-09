"""工具层锚点：11 个工具注册、6 个确定性工具的 query 解析、artifact 契约、失败兜底。

这些测试不启动 FastAPI，只用假的 ``ToolContext(state=None)`` 直接调用 ``TOOL.run``，
验证 orchestrator 依赖的字段（calc/plot data 契约）与关键数值。
"""
import re

from app.tools import SPECS, TOOLS
from app.tools.base import ToolContext

CTX = ToolContext(state=None)

EXPECTED_TOOLS = {
    "kb_search", "kg_lookup", "critical_calc", "kinetics_calc", "poison_calc",
    "burnup_calc", "reactivity_calc", "spectrum_plot", "comparison_pick",
    "quiz_from_kb", "wrongbook_crud",
}

CALC_KEYS = {"title", "inputs", "formulas", "results", "verdict", "refs", "note"}
PLOT_KEYS = {"kind", "title", "x_label", "y_label", "series", "markers", "results",
             "note", "refs"}


def _close(actual, expected, tol, what=""):
    assert abs(actual - expected) <= tol, (
        f"{what}: 得到 {actual!r}，期望 {expected!r}（容差 {tol!r}）")


def test_tools_registration():
    """11 个工具全部注册；6 个确定性工具 TOOL.name==文件名且 parameters 含 query。"""
    assert set(SPECS) == EXPECTED_TOOLS, f"注册工具集合不符：{sorted(SPECS)}"
    for name in ("critical_calc", "kinetics_calc", "poison_calc", "burnup_calc",
                 "reactivity_calc", "spectrum_plot"):
        spec = SPECS[name]
        assert spec.name == name
        assert spec.description.strip()
        assert "query" in spec.parameters["properties"], f"{name} 缺少 query 参数"
        assert callable(spec.run)


def test_tool_critical_curvature_query():
    """回归：只求材料曲率时不反解尺寸 → B_m²≈3.33 m⁻²（k∞=1.06，M²=180 cm²）。"""
    out = TOOLS["critical_calc"](CTX, query="k∞=1.06，M2=180cm2，单群裸堆，求临界曲率")
    assert out.ok, out.detail
    assert out.artifact_type == "calc"
    data = out.artifact_data
    _close(out.payload["result"]["Bm2"], 0.06 / 0.018, 1e-6, "B_m²")
    assert data["verdict"]["level"] == "材料曲率", data["verdict"]
    names = [x["name"] for x in data["results"]]
    assert not any("临界 H" in n or "临界 R" in n for n in names), f"不应反解尺寸：{names}"


def test_tool_critical_cylinder_keff_query():
    """回归：圆柱 R=50cm、H=100cm → B_g²≈33.0 m⁻²、k_eff≈0.665。"""
    out = TOOLS["critical_calc"](
        CTX, query="k∞=1.06，L2=100cm2，τ=80cm2，圆柱，R=50cm，H=100cm，求k_eff")
    assert out.ok, out.detail
    res = out.payload["result"]
    _close(res["B"]["Bg2"], 33.01, 0.05, "B_g²")
    _close(res["B"]["k_eff"], 0.665, 2e-3, "k_eff")


def test_tool_critical_sphere_radius_query():
    """回归：裸球 R=50cm 应识别为球且带尺寸（算 k_eff，而不是求临界尺寸）。"""
    out = TOOLS["critical_calc"](
        CTX, query="裸球R=50cm，k∞=1.08，L2=0.02m2，τ=0.01m2，求k_eff")
    assert out.ok, out.detail
    res = out.payload["result"]
    assert res["geometry"] == "sphere"
    assert "k_eff" in res["B"], res["B"]


def test_tool_burnup_natural_days_query():
    """回归：功率3000MW，装料80tU，运行300天 → 燃耗 1.125×10⁴ MWd/tU。"""
    out = TOOLS["burnup_calc"](CTX, query="功率3000MW，装料80tU，运行300天，求燃耗深度")
    assert out.ok, out.detail
    _close(out.payload["result"]["burnup_mwd_tu"], 1.125e4, 1e-6, "燃耗深度")
    assert out.artifact_type == "calc"


def test_tool_kinetics_query():
    """回归：阶跃引入 +0.2$ → plot 画布、ρ/β=0.2、周期有限。"""
    out = TOOLS["kinetics_calc"](CTX, query="阶跃引入+0.2$反应性，l=1e-4s，β=0.0065")
    assert out.ok, out.detail
    assert out.artifact_type == "plot"
    res = out.payload["result"]
    _close(res["rho_dollar"], 0.2, 1e-9, "ρ($)")
    assert res["period_s"] > 1.0
    assert len(out.artifact_data["series"][0]["points"]) > 10


def test_tool_kinetics_period_ratio_query():
    """题8.5 回归：n2/n1=5/3、Δt=120s → T=234.91 s（plot 模式）。"""
    out = TOOLS["kinetics_calc"](CTX, query="n2/n1=1.6667，Δt=120s，求平均周期")
    assert out.ok, out.detail
    assert out.artifact_type == "plot"
    _close(out.payload["result"]["T_s"], 234.91, 0.5, "平均周期")


def test_tool_poison_query():
    """氙坑：运行 200 天、停堆 60 h → plot 画布，平衡 ρ_Xe 在 −0.04~−0.05。"""
    out = TOOLS["poison_calc"](
        CTX, query="满功率运行200天，突然停堆60小时，碘坑多深？Φ=3e13 cm-2 s-1")
    assert out.ok, out.detail
    assert out.artifact_type == "plot"
    res = out.payload["result"]
    assert -5000.0 <= res["rho_xe_eq_pcm"] <= -4000.0, res
    assert res["iodine_pit_depth_pcm"] < 0
    assert len(out.artifact_data["series"]) == 2


def test_tool_reactivity_query():
    """k=0.998 → ρ=−200.4 pcm（calc 画布）。"""
    out = TOOLS["reactivity_calc"](CTX, query="k=0.998 的反应性是多少 pcm")
    assert out.ok, out.detail
    assert out.artifact_type == "calc"
    _close(out.payload["result"]["rho_pcm"], -200.4, 0.5, "ρ (pcm)")


def test_tool_spectrum_query():
    """Maxwell 热谱 T=293.6K → 峰值≈0.0253 eV（plot 画布）。"""
    out = TOOLS["spectrum_plot"](CTX, query="Maxwell 热谱 T=293.6K，最可几能量是多少")
    assert out.ok, out.detail
    assert out.artifact_type == "plot"
    _close(out.payload["result"]["peak_energy_ev"], 0.0253, 1e-3, "热谱峰值")


def test_tool_failure_has_examples():
    """解析不到信息时 ok=False，detail 给出 2~3 个可用示例，不抛异常。"""
    for name in ("critical_calc", "kinetics_calc", "burnup_calc",
                 "reactivity_calc", "spectrum_plot"):
        out = TOOLS[name](CTX, query="")
        assert out.ok is False, f"{name} 空 query 应返回 ok=False"
        assert out.detail and ("示例" in out.detail or "例如" in out.detail), (
            f"{name} 失败时应给示例：{out.detail!r}")
    out = TOOLS["poison_calc"](CTX, query="")
    assert out.ok is False and out.detail


def test_artifact_contract_calc_and_plot():
    """6 个工具的 artifact_data 字段符合 SPEC 第4.1 节 calc/plot 契约。"""
    cases = [
        ("critical_calc", "k∞=1.06，L2=0.03m2，τ=0，平板H=2.5m，求k_eff", "calc"),
        ("burnup_calc", "功率3000MW，装料80tU，运行300天，求燃耗深度", "calc"),
        ("reactivity_calc", "k=0.998", "calc"),
        ("kinetics_calc", "ρ=200pcm", "plot"),
        ("poison_calc", "运行200天，停堆60小时，碘坑", "plot"),
        ("spectrum_plot", "压水堆合成能谱", "plot"),
    ]
    for name, query, kind in cases:
        out = TOOLS[name](CTX, query=query)
        assert out.ok, f"{name}: {out.detail}"
        assert out.artifact_type == kind, f"{name} 画布应为 {kind}"
        data = out.artifact_data
        if kind == "calc":
            missing = CALC_KEYS - set(data)
            assert not missing, f"{name} calc 缺字段 {missing}"
            assert isinstance(data["inputs"], list) and data["inputs"]
            assert isinstance(data["results"], list) and data["results"]
            assert isinstance(data["verdict"], dict) and "level" in data["verdict"]
            for row in data["results"]:
                assert {"name", "value", "unit", "note"} <= set(row), f"{name} results 行缺字段"
        else:
            missing = PLOT_KEYS - set(data)
            assert not missing, f"{name} plot 缺字段 {missing}"
            assert data["kind"] in ("curve", "spectrum", "distribution")
            assert isinstance(data["series"], list) and data["series"]
            for s in data["series"]:
                assert s["name"] and len(s["points"]) >= 2
                x, y = s["points"][0]
                assert isinstance(x, (int, float)) and isinstance(y, (int, float))
            assert isinstance(data["markers"], list)
            assert isinstance(data["results"], list)
        assert isinstance(data["refs"], list) and data["refs"]
        assert isinstance(data["note"], str)
        svg = data.get("svg", "")
        assert svg == "" or svg.startswith("<svg"), f"{name} svg 不合法"


def test_artifact_plot_svg_self_contained():
    """plot 的 svg 是自包含片段：有 xmlns、含曲线 path、无 script。"""
    out = TOOLS["kinetics_calc"](CTX, query="ρ=200pcm")
    svg = out.artifact_data["svg"]
    assert svg.startswith("<svg")
    assert 'xmlns="http://www.w3.org/2000/svg"' in svg
    assert "<path" in svg and "<script" not in svg
    assert "Microsoft YaHei" in svg


def test_tool_kinetics_dollar_units():
    """反应性单位自然写法：+0.2$、0.2 dollar、ρ=1$ 都应正确换算成 $。"""
    for q, expected in (("+0.2$", 0.2), ("0.2 dollar", 0.2), ("ρ=1$", 1.0),
                        ("阶跃引入0.2$反应性", 0.2)):
        out = TOOLS["kinetics_calc"](CTX, query=q)
        assert out.ok, f"{q}: {out.detail}"
        _close(out.payload["result"]["rho_dollar"], expected, 1e-9, f"{q} → $")


def test_tool_artifacts_json_serializable():
    """artifact_data 与 payload 必须严格 JSON 可序列化（禁止 NaN/Infinity）。"""
    import json
    cases = [
        ("critical_calc", "k∞=1.06，L2=0.03m2，τ=0，平板H=2.5m，求k_eff"),
        ("critical_calc", "k∞=1.06，M2=180cm2，求材料曲率"),
        ("kinetics_calc", "ρ=200pcm"),
        ("kinetics_calc", "ρ=1$"),
        ("poison_calc", "运行200天，停堆60小时，碘坑"),
        ("burnup_calc", "功率3000MW，装料80tU，运行300天，求燃耗深度"),
        ("reactivity_calc", "k=0.998"),
        ("spectrum_plot", "压水堆合成能谱"),
    ]
    for name, query in cases:
        out = TOOLS[name](CTX, query=query)
        assert out.ok, f"{name}: {out.detail}"
        json.dumps(out.artifact_data, ensure_ascii=False, allow_nan=False)
        json.dumps(out.payload, ensure_ascii=False, allow_nan=False)


def test_tool_kinetics_response_finite():
    """响应曲线数值稳定：ρ=200 pcm 时 n/n₀ 终值有限且 >1。"""
    out = TOOLS["kinetics_calc"](CTX, query="ρ=200pcm")
    final = out.payload["result"]["final_n_over_n0"]
    assert final == final and abs(final) != float("inf"), "响应曲线出现 nan/inf"
    assert final > 1.0
