"""arc.py 的回归测试（圆弧连接几何）。

运行方式（两种都可以）::

    D:\\python\\python.exe -m pytest apps/api/tests/test_arc.py -q
    D:\\python\\python.exe apps/api/tests/test_arc.py
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.geometry.arc import (  # noqa: E402
    arc_to_line,
    build_steps,
    connect_arc_to_arc,
    connect_arc_to_line,
    fillet_two_lines,
)

TOL = 1e-6


def _close(actual: float, expected: float, tol: float = TOL) -> None:
    assert abs(actual - expected) <= tol, f"期望 {expected}，实际 {actual}"


def _close_pt(actual, expected, tol: float = TOL) -> None:
    assert len(actual) == 2 and len(expected) == 2
    _close(actual[0], expected[0], tol)
    _close(actual[1], expected[1], tol)


def _expect_value_error(func, *args, **kwargs) -> None:
    try:
        func(*args, **kwargs)
    except ValueError:
        return
    raise AssertionError(f"{func.__name__}{args} 应当抛出 ValueError，但没有")


# ---------------------------------------------------------------------------
# 核心锚点：R10 圆角连接两条互相垂直、沿 x/y 正方向的直线
# ---------------------------------------------------------------------------


def test_fillet_r10_anchor() -> None:
    data = fillet_two_lines(
        10,
        ((0.0, 0.0), (10.0, 0.0)),
        ((0.0, 0.0), (0.0, 10.0)),
    )
    _close_pt(data["center"], (10.0, 10.0))
    _close_pt(data["tangents"][0], (10.0, 0.0))
    _close_pt(data["tangents"][1], (0.0, 10.0))
    _close(data["angle_deg"], 90.0)


def test_build_steps_line_line_anchor() -> None:
    steps = build_steps(
        "line_line",
        r=10,
        p1=(0, 0),
        p2=(10, 0),
        p3=(0, 0),
        p4=(0, 10),
    )
    assert steps["kind"] == "line_line"
    result = steps["result"]
    _close_pt(result["center"], (10.0, 10.0))
    _close_pt(result["tangents"][0], (10.0, 0.0))
    _close_pt(result["tangents"][1], (0.0, 10.0))
    # 分步脚本结构
    assert len(steps["steps"]) == 4
    for index, step in enumerate(steps["steps"], start=1):
        assert step["n"] == index
        assert step["title"]
        assert step["detail"]
        assert isinstance(step["draw"], list) and step["draw"]
    arcs = [item for item in steps["svg_paths"] if item.get("op") == "arc"]
    assert len(arcs) == 1
    arc = arcs[0]
    _close_pt(arc["c"], (10.0, 10.0))
    _close(arc["r"], 10.0)
    # 圆弧圆心角为 90°（劣弧），从 180° 逆时针画到 270°
    start = arc["start_angle"] % 360.0
    end = arc["end_angle"] % 360.0
    _close(((end - start) % 360.0), 90.0)
    assert "10.000000" in steps["summary"]


def test_build_steps_chinese_alias() -> None:
    steps = build_steps("圆角", r=10, lines=(((0, 0), (10, 0)), ((0, 0), (0, 10))))
    _close_pt(steps["result"]["center"], (10.0, 10.0))


# ---------------------------------------------------------------------------
# 直线—圆弧
# ---------------------------------------------------------------------------


def test_connect_arc_to_line_anchor() -> None:
    data = connect_arc_to_line(5, (-10, 0), (10, 0), (0, 10))
    _close_pt(data["center"], (0.0, 5.0))
    _close_pt(data["tangent_on_line"], (0.0, 0.0))
    _close(data["r"], 5.0)


def test_arc_to_line_locus() -> None:
    data = arc_to_line(3, (0, 0), (10, 0), side=1)
    assert data["side"] == 1
    _close_pt(data["tangent_on_line"], (5.0, 0.0))
    _close_pt(data["center"], (5.0, 3.0))  # side=+1 为直线左（上）侧
    # 圆心轨迹为与已知直线相距 3 的平行线
    _close(data["center_locus"][0][1], 3.0)
    _close(data["center_locus"][1][1], 3.0)
    assert "圆心" in data["formula"]


def test_build_steps_line_arc() -> None:
    steps = build_steps(
        "line_arc",
        r=5,
        line=((-10, 0), (10, 0)),
        circle=((0, 10), 2),
        relation="outer",
    )
    result = steps["result"]
    center = result["center"]
    t_line = result["tangent_on_line"]
    t_circle = result["tangent_on_circle"]
    # 圆心到直线距离 = r
    _close(abs(center[1]), 5.0)
    # 圆心到已知圆圆心距离 = R + r
    _close(math.hypot(center[0] - 0.0, center[1] - 10.0), 7.0)
    # 切点在直线与已知圆上
    _close(t_line[1], 0.0)
    _close(math.hypot(t_circle[0] - 0.0, t_circle[1] - 10.0), 2.0)
    assert len(steps["steps"]) == 4


# ---------------------------------------------------------------------------
# 圆弧—圆弧 外切 / 内切
# ---------------------------------------------------------------------------


def test_connect_arc_to_arc_outer_anchor() -> None:
    data = connect_arc_to_arc(5, (0, 0), 10, (30, 0), 10, kind="outer")
    assert data["kind"] == "outer"
    assert len(data["centers"]) == 1
    _close_pt(data["center"], (15.0, 0.0))
    _close_pt(data["tangent_points"][0][0], (10.0, 0.0))
    _close_pt(data["tangent_points"][0][1], (20.0, 0.0))
    assert "外切" in data["formula"]


def test_connect_arc_to_arc_inner_anchor() -> None:
    data = connect_arc_to_arc(5, (0, 0), 10, (5, 0), 10, kind="inner")
    assert data["kind"] == "inner"
    assert len(data["centers"]) == 2
    for center in data["centers"]:
        _close(math.hypot(center[0] - 0.0, center[1] - 0.0), 5.0)   # |r1 - r|
        _close(math.hypot(center[0] - 5.0, center[1] - 0.0), 5.0)   # |r2 - r|
    t1, t2 = data["tangent_points"][0]
    _close(math.hypot(t1[0] - 0.0, t1[1] - 0.0), 10.0)  # 切点在圆 1 上
    _close(math.hypot(t2[0] - 5.0, t2[1] - 0.0), 10.0)  # 切点在圆 2 上


def test_build_steps_arc_arc() -> None:
    outer = build_steps("arc_arc_outer", r=5, c1=(0, 0), r1=10, c2=(30, 0), r2=10)
    inner = build_steps("arc_arc_inner", r=5, circles=(((0, 0), 10), ((5, 0), 10)))
    _close_pt(outer["result"]["center"], (15.0, 0.0))
    assert len(outer["steps"]) == 4
    assert len(inner["steps"]) == 4
    assert inner["kind"] == "arc_arc_inner"
    for step in outer["steps"]:
        assert set(step) >= {"n", "title", "detail", "draw"}


# ---------------------------------------------------------------------------
# 异常与边界
# ---------------------------------------------------------------------------


def test_errors() -> None:
    _expect_value_error(fillet_two_lines, 10, ((0, 0), (10, 0)), ((0, 5), (10, 5)))  # 平行
    _expect_value_error(fillet_two_lines, 0, ((0, 0), (10, 0)), ((0, 0), (0, 10)))   # r<=0
    _expect_value_error(arc_to_line, 3, (0, 0), (0, 0))                              # 退化直线
    _expect_value_error(connect_arc_to_line, 1, (-10, 0), (10, 0), (0, 100))         # 无解
    _expect_value_error(connect_arc_to_arc, 5, (0, 0), 1, (30, 0), 1, "outer")       # 够不着
    _expect_value_error(connect_arc_to_arc, 5, (0, 0), 10, (30, 0), 10, "unknown")   # 类型错
    _expect_value_error(build_steps, "未知类型", r=5)


def test_svg_draw_schema() -> None:
    steps = build_steps("line_line", r=10, p1=(0, 0), p2=(10, 0), p3=(0, 0), p4=(0, 10))
    for item in steps["svg_paths"]:
        assert item["op"] in {"line", "arc", "point", "circle"}
        if item["op"] == "line":
            assert len(item["a"]) == 2 and len(item["b"]) == 2
        elif item["op"] == "arc":
            assert len(item["c"]) == 2 and item["r"] > 0
            assert 0.0 <= item["start_angle"] < 360.0
            assert 0.0 <= item["end_angle"] < 360.0
        elif item["op"] == "point":
            assert len(item["p"]) == 2


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
        except Exception:  # noqa: BLE001
            failed += 1
            print(f"FAIL  {name}")
            traceback.print_exc()
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
