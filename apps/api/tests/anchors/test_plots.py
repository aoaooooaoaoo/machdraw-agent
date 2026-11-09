"""plots/svg 渲染锚点：自包含、轴/刻度/图例/对数坐标/转义。"""
from app.plots.svg import line_chart


def test_svg_basic_structure():
    svg = line_chart(
        [{"name": "功率响应", "points": [[0, 1.0], [0.1, 1.8], [0.2, 2.5]]}],
        x_label="t / s", y_label="n / n₀", title="阶跃反应性响应",
        width=900, height=520,
    )
    assert svg.startswith("<svg") and svg.endswith("</svg>")
    assert 'viewBox="0 0 900 520"' in svg
    assert 'xmlns="http://www.w3.org/2000/svg"' in svg
    assert "<path" in svg and "<text" in svg
    assert "阶跃反应性响应" in svg and "功率响应" in svg
    assert "Microsoft YaHei" in svg
    assert "<script" not in svg


def test_svg_multi_series_and_markers():
    svg = line_chart(
        [
            {"name": "I-135", "points": [[0, 1.0], [1, 2.0], [2, 3.0]]},
            {"name": "Xe-135", "points": [[0, 0.5], [1, 1.5], [2, 2.5]], "dash": True},
        ],
        x_label="t / h", y_label="N / cm⁻³", title="碘氙",
        markers=[{"x": 1.0, "y": 2.0, "label": "停堆"}],
    )
    assert svg.count("<path") >= 2
    assert "停堆" in svg
    assert svg.count("<circle") >= 1


def test_svg_log_axes():
    svg = line_chart(
        [{"name": "φ(E)", "points": [[1e-3, 1e2], [1e-1, 1e0], [1e2, 1e-3]]}],
        x_label="E / eV", y_label="φ", title="能谱", x_log=True, y_log=True,
    )
    assert "10^" in svg
    assert "<path" in svg


def test_svg_escapes_and_empty():
    svg = line_chart([], title="无 <数据> & 占位")
    assert "&lt;数据&gt;" in svg and "&amp;" in svg
    assert svg.startswith("<svg")
