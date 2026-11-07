"""tolerance.py 的回归测试（锚点 + 解析 + 配合 + 异常）。

运行方式（两种都可以）::

    D:\\python\\python.exe -m pytest apps/api/tests/test_tolerance.py -q
    D:\\python\\python.exe apps/api/tests/test_tolerance.py

本文件不依赖 pytest：测试函数都是普通函数，``__main__`` 下自行运行。
"""
from __future__ import annotations

import sys
from pathlib import Path

# 允许直接运行本文件：把 apps/api 加入 sys.path 以便 import app.*
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.domain.tolerance import (  # noqa: E402
    fundamental_deviation,
    it_tolerance,
    parse_fit,
    solve_fit,
)

TOL = 1e-9


def _close(actual: float, expected: float, tol: float = TOL) -> None:
    assert abs(actual - expected) <= tol, f"期望 {expected}，实际 {actual}"


def _expect_value_error(func, *args, **kwargs) -> None:
    try:
        func(*args, **kwargs)
    except ValueError:
        return
    raise AssertionError(f"{func.__name__}{args} 应当抛出 ValueError，但没有")


# ---------------------------------------------------------------------------
# 锚点：老师随口会问的经典值，必须与 GB/T 1800.1-2020 / 1800.2-2020 表一致
# ---------------------------------------------------------------------------


def test_it_tolerance_anchors() -> None:
    _close(it_tolerance(30, 7), 0.021)   # Φ30 IT7
    _close(it_tolerance(30, 6), 0.013)   # Φ30 IT6
    _close(it_tolerance(20, 8), 0.033)   # Φ20 IT8
    _close(it_tolerance(50, 7), 0.025)   # Φ50 IT7
    _close(it_tolerance(50, 6), 0.016)   # Φ50 IT6


def test_it_tolerance_boundaries() -> None:
    # 尺寸分段"上限包含、下限不含"：18 属于 (10,18]，50 属于 (30,50]
    _close(it_tolerance(18, 6), 0.011)
    _close(it_tolerance(3, 7), 0.010)
    _close(it_tolerance(30, 8), 0.033)
    _close(it_tolerance(500, 7), 0.063)
    _close(it_tolerance(0.5, 5), 0.004)


def test_anchor_h30_h7() -> None:
    result = solve_fit(30, "H7", "h6")
    _close(result["hole"]["ES"], 0.021)
    _close(result["hole"]["EI"], 0.0)


def test_anchor_k30_k6() -> None:
    result = solve_fit(30, "H7", "k6")
    _close(result["shaft"]["es"], 0.015)
    _close(result["shaft"]["ei"], 0.002)


def test_anchor_f30_f7() -> None:
    result = solve_fit(30, "H7", "f7")
    _close(result["shaft"]["es"], -0.020)
    _close(result["shaft"]["ei"], -0.041)


def test_anchor_h30_h6() -> None:
    result = solve_fit(30, "H7", "h6")
    _close(result["shaft"]["es"], 0.0)
    _close(result["shaft"]["ei"], -0.013)


def test_anchor_h50_h7() -> None:
    result = solve_fit(50, "H7", "h6")
    _close(result["hole"]["ES"], 0.025)
    _close(result["hole"]["EI"], 0.0)


def test_anchor_h50_h6() -> None:
    result = solve_fit(50, "H7", "h6")
    _close(result["shaft"]["es"], 0.0)
    _close(result["shaft"]["ei"], -0.016)


def test_anchor_h20_h8() -> None:
    result = solve_fit(20, "H8", "f7")
    _close(result["hole"]["ES"], 0.033)
    _close(result["hole"]["EI"], 0.0)


def test_anchor_f20_f7() -> None:
    result = solve_fit(20, "H8", "f7")
    _close(result["shaft"]["es"], -0.020)
    _close(result["shaft"]["ei"], -0.041)


def test_anchor_js45_js6() -> None:
    result = solve_fit(45, "H7", "js6")
    _close(result["shaft"]["es"], 0.008)
    _close(result["shaft"]["ei"], -0.008)
    _close(result["shaft"]["IT"], 0.016)


# ---------------------------------------------------------------------------
# 教材中其它高频数值
# ---------------------------------------------------------------------------


def test_classic_fit_h7_g6_at_18() -> None:
    result = solve_fit(18, "H7", "g6")
    _close(result["shaft"]["es"], -0.006)
    _close(result["shaft"]["ei"], -0.017)
    assert result["fit"]["type"] == "间隙配合"


def test_hole_k7_m7_n7_at_30() -> None:
    k7 = solve_fit(30, "K7", "h6")["hole"]
    _close(k7["ES"], 0.006)
    _close(k7["EI"], -0.015)

    m7 = solve_fit(30, "M7", "h6")["hole"]
    _close(m7["ES"], 0.0)
    _close(m7["EI"], -0.021)

    n7 = solve_fit(30, "N7", "h6")["hole"]
    _close(n7["ES"], -0.007)
    _close(n7["EI"], -0.028)


def test_hole_p7_r7_s7_at_30() -> None:
    p7 = solve_fit(30, "P7", "h6")["hole"]
    _close(p7["ES"], -0.014)
    _close(p7["EI"], -0.035)

    r7 = solve_fit(30, "R7", "h6")["hole"]
    _close(r7["ES"], -0.020)
    _close(r7["EI"], -0.041)

    s7 = solve_fit(30, "S7", "h6")["hole"]
    _close(s7["ES"], -0.027)
    _close(s7["EI"], -0.048)


def test_shaft_p6_r6_s6_at_50() -> None:
    p6 = solve_fit(50, "H7", "p6")["shaft"]
    _close(p6["es"], 0.042)
    _close(p6["ei"], 0.026)

    r6 = solve_fit(50, "H7", "r6")["shaft"]
    _close(r6["es"], 0.050)
    _close(r6["ei"], 0.034)

    s6 = solve_fit(50, "H7", "s6")["shaft"]
    _close(s6["es"], 0.059)
    _close(s6["ei"], 0.043)


def test_fundamental_deviation_direct() -> None:
    _close(fundamental_deviation(30, "f", False, 7), -0.020)
    _close(fundamental_deviation(30, "g", False, 6), -0.007)
    _close(fundamental_deviation(30, "k", False, 6), 0.002)
    _close(fundamental_deviation(30, "m", False, 6), 0.008)
    _close(fundamental_deviation(30, "n", False, 6), 0.015)
    _close(fundamental_deviation(30, "p", False, 6), 0.022)
    _close(fundamental_deviation(30, "r", False, 6), 0.028)
    _close(fundamental_deviation(30, "s", False, 6), 0.035)
    _close(fundamental_deviation(30, "h", False, 6), 0.0)
    _close(fundamental_deviation(30, "H", True, 7), 0.0)
    _close(fundamental_deviation(30, "K", True, 7), 0.006)
    _close(fundamental_deviation(30, "M", True, 7), 0.0)
    _close(fundamental_deviation(30, "N", True, 7), -0.007)
    _close(fundamental_deviation(30, "P", True, 7), -0.014)
    _close(fundamental_deviation(30, "R", True, 7), -0.020)
    _close(fundamental_deviation(30, "S", True, 7), -0.027)
    _close(fundamental_deviation(30, "J", True, 7), 0.012)


# ---------------------------------------------------------------------------
# parse_fit
# ---------------------------------------------------------------------------


def test_parse_fit_slash_form() -> None:
    expected = {
        "phi": 30.0,
        "hole": "H7",
        "shaft": "k6",
        "hole_letter": "H",
        "hole_grade": 7,
        "shaft_letter": "k",
        "shaft_grade": 6,
    }
    assert parse_fit("Φ30 H7/k6") == expected
    assert parse_fit("Ø30H7/k6") == expected
    assert parse_fit("30 H7 k6") == expected


def test_parse_fit_single_member() -> None:
    only_hole = parse_fit("Φ50H7")
    assert only_hole["phi"] == 50.0
    assert only_hole["hole"] == "H7"
    assert only_hole["shaft"] is None
    assert only_hole["shaft_grade"] is None

    only_shaft = parse_fit("Φ30h6")
    assert only_shaft["hole"] is None
    assert only_shaft["shaft"] == "h6"
    assert only_shaft["shaft_letter"] == "h"


def test_parse_fit_other_cases() -> None:
    h8f7 = parse_fit("Φ20 H8/f7")
    assert (h8f7["phi"], h8f7["hole"], h8f7["shaft"]) == (20.0, "H8", "f7")

    js6 = parse_fit("φ45 js6")
    assert (js6["phi"], js6["shaft"], js6["shaft_letter"]) == (45.0, "js6", "js")


def test_parse_fit_errors() -> None:
    _expect_value_error(parse_fit, "图纸")
    _expect_value_error(parse_fit, "")
    _expect_value_error(parse_fit, "30 H7 K6")  # 两个孔代号
    _expect_value_error(parse_fit, "Φ600 H7/k6")


# ---------------------------------------------------------------------------
# solve_fit 结构 / 配合性质
# ---------------------------------------------------------------------------


def test_solve_fit_required_fields() -> None:
    result = solve_fit(30, "H7", "k6")
    for key in (
        "basic_size",
        "system",
        "hole",
        "shaft",
        "fit",
        "tolerance_zone",
        "process_hint",
        "refs",
    ):
        assert key in result, f"缺少字段 {key}"
    for key in ("code", "IT", "ES", "EI", "max", "min"):
        assert key in result["hole"]
    for key in ("code", "IT", "es", "ei", "max", "min"):
        assert key in result["shaft"]
    for key in ("type", "max_gap", "min_gap", "max_interference", "note"):
        assert key in result["fit"]
    assert result["tolerance_zone"] == {"hole": ["EI", "ES"], "shaft": ["ei", "es"]}
    assert result["refs"] == ["GB/T 1800.1-2020", "GB/T 1800.2-2020"]
    assert result["hole"]["max"] == 30.021
    assert result["hole"]["min"] == 30.0
    assert result["shaft"]["max"] == 30.015
    assert result["shaft"]["min"] == 30.002


def test_solve_fit_transition() -> None:
    result = solve_fit(30, "H7", "k6")
    assert result["system"] == "基孔制"
    fit = result["fit"]
    assert fit["type"] == "过渡配合"
    _close(fit["max_gap"], 0.019)
    _close(fit["min_gap"], -0.015)
    _close(fit["max_interference"], 0.015)


def test_solve_fit_clearance() -> None:
    result = solve_fit(20, "H8", "f7")
    assert result["fit"]["type"] == "间隙配合"
    _close(result["fit"]["max_gap"], 0.074)
    _close(result["fit"]["min_gap"], 0.020)
    _close(result["fit"]["max_interference"], 0.0)


def test_solve_fit_interference() -> None:
    result = solve_fit(30, "H7", "p6")
    assert result["fit"]["type"] == "过盈配合"
    _close(result["fit"]["max_gap"], -0.001)
    _close(result["fit"]["max_interference"], 0.035)


def test_solve_fit_shaft_basis() -> None:
    result = solve_fit(30, "K7", "h6")
    assert result["system"] == "基轴制"


def test_solve_fit_non_basis() -> None:
    result = solve_fit(30, "K7", "k6")
    assert result["system"] == "非基准制"


# ---------------------------------------------------------------------------
# 异常与边界：不支持的情况必须显式抛 ValueError（中文原因）
# ---------------------------------------------------------------------------


def test_unsupported_inputs_raise() -> None:
    _expect_value_error(it_tolerance, 600, 7)          # 超出 500 mm
    _expect_value_error(it_tolerance, 30, 4)           # IT4 未覆盖
    _expect_value_error(it_tolerance, 30, 12)          # IT12 未覆盖
    _expect_value_error(it_tolerance, 0, 7)            # 非法尺寸
    _expect_value_error(fundamental_deviation, 30, "x", False, 7)   # 非标轴代号
    _expect_value_error(fundamental_deviation, 30, "X", True, 7)    # 非标孔代号
    _expect_value_error(solve_fit, 30, "h7", "k6")     # 孔代号用了小写
    _expect_value_error(solve_fit, 30, "H7", "K6")     # 轴代号用了大写
    _expect_value_error(solve_fit, 30, "H7", "j9")     # 轴 j9 非标准
    _expect_value_error(solve_fit, 30, "J5", "h6")     # 孔 J5 非标准
    _expect_value_error(solve_fit, 30, "K9", "h6")     # 孔 K9 非标准（≤500 mm）
    _expect_value_error(solve_fit, 30, "H7", None)     # 缺少轴代号


def test_size_and_grade_edges() -> None:
    # 最小/最大覆盖尺寸
    assert it_tolerance(0.1, 5) > 0
    assert it_tolerance(500, 11) > 0
    # 500 以内最大尺寸段 IT11 = 400 µm
    _close(it_tolerance(500, 11), 0.400)


# ---------------------------------------------------------------------------
# 直接运行入口
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    import traceback

    tests = [
        (name, obj)
        for name, obj in sorted(globals().items())
        if name.startswith("test_") and callable(obj)
    ]
    failed = 0
    for name, func in tests:
        try:
            func()
            print(f"PASS  {name}")
        except Exception:  # noqa: BLE001 - 测试入口需要打印完整堆栈
            failed += 1
            print(f"FAIL  {name}")
            traceback.print_exc()
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
