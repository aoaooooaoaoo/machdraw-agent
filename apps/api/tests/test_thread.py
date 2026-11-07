"""thread.py 的回归测试（螺纹标记、比例画法、螺栓）。

运行方式（两种都可以）::

    D:\\python\\python.exe -m pytest apps/api/tests/test_thread.py -q
    D:\\python\\python.exe apps/api/tests/test_thread.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.domain.thread import bolt_drawing, parse_thread, thread_drawing  # noqa: E402

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
# parse_thread：题目要求的 5 种标记
# ---------------------------------------------------------------------------


def test_parse_m10() -> None:
    data = parse_thread("M10")
    assert data["type"] == "metric"
    _close(data["d"], 10.0)
    _close(data["pitch"], 1.5)
    assert data["series"] == "粗牙"
    assert data["direction"] == "右旋"
    assert data["tolerance"] is None


def test_parse_m10_fine() -> None:
    data = parse_thread("M10×1.5")
    assert data["type"] == "metric"
    _close(data["d"], 10.0)
    _close(data["pitch"], 1.5)


def test_parse_m20_tolerance() -> None:
    data = parse_thread("M20×2-6H")
    _close(data["d"], 20.0)
    _close(data["pitch"], 2.0)
    assert data["tolerance"] == "6H"
    assert data["series"] == "细牙"
    assert "6H" in data["spec"]


def test_parse_trapezoidal() -> None:
    data = parse_thread("Tr24×5")
    assert data["type"] == "trapezoidal"
    _close(data["d"], 24.0)
    _close(data["pitch"], 5.0)
    assert data["profile"] == "30°"


def test_parse_pipe() -> None:
    data = parse_thread("G1/2")
    assert data["type"] == "pipe"
    _close(data["d"], 20.955)      # 管螺纹大径须查表，不是 0.5×25.4
    _close(data["pitch"], 1.814)
    assert data["size_inch"] == "1/2"
    assert data["profile"] == "55°"


def test_parse_more_forms() -> None:
    left = parse_thread("Tr30x6-7e-LH")
    assert left["direction"] == "左旋"
    assert left["tolerance"] == "7e"

    pipe = parse_thread("G3/4")
    _close(pipe["d"], 26.441)

    fine = parse_thread("M20x1.5")
    assert fine["series"] == "细牙"


def test_parse_errors() -> None:
    _expect_value_error(parse_thread, "X10")
    _expect_value_error(parse_thread, "")
    _expect_value_error(parse_thread, "M7.5")         # 非首选粗牙序列
    _expect_value_error(parse_thread, "G1/3")         # 未内嵌的管螺纹尺寸
    _expect_value_error(parse_thread, "M10x")         # 缺螺距


# ---------------------------------------------------------------------------
# thread_drawing：比例画法
# ---------------------------------------------------------------------------


def test_thread_drawing_m10() -> None:
    data = thread_drawing("M10")
    _close(data["d"], 10.0)
    _close(data["d1"], 8.5)   # 0.85d
    _close(data["d2"], 8.5)   # 0.85d
    _close(data["pitch"], 1.5)
    assert data["type"] == "metric"
    assert len(data["points"]) >= 4
    assert data["table"]["standard"]
    assert data["spec"] == "M10"


def test_thread_drawing_m10_fine_pitch() -> None:
    data = thread_drawing("M10×1.5")
    _close(data["pitch"], 1.5)
    _close(data["d1"], 8.5)


def test_thread_drawing_trapezoidal() -> None:
    data = thread_drawing("Tr24×5")
    _close(data["d"], 24.0)
    _close(data["d2"], 21.5)  # d - 0.5P
    _close(data["d1"], 19.0)  # d - P
    assert data["type"] == "trapezoidal"


def test_thread_drawing_pipe() -> None:
    data = thread_drawing("G1/2")
    _close(data["d"], 20.955)
    _close(data["pitch"], 1.814)
    # 55° 牙型：d2 = d - 0.640327P
    _close(data["d2"], 20.955 - 0.640327 * 1.814, tol=1e-6)
    assert data["type"] == "pipe"


def test_thread_drawing_structure() -> None:
    data = thread_drawing("M20×2-6H")
    for key in ("spec", "type", "d", "d1", "d2", "pitch", "points", "table"):
        assert key in data, f"缺少字段 {key}"
    assert all(isinstance(point, str) and point for point in data["points"])
    assert data["table"]["tolerance"] == "6H"


# ---------------------------------------------------------------------------
# bolt_drawing：六角头螺栓比例画法
# ---------------------------------------------------------------------------


def test_bolt_drawing_m10() -> None:
    data = bolt_drawing("M10")
    _close(data["d"], 10.0)
    _close(data["k"], 7.0)              # 0.7d
    _close(data["e"], 20.0)             # 2d
    _close(data["s"], 17.320508, 1e-6)  # e·cos30°
    _close(data["r"], 15.0)             # 1.5d
    _close(data["l"], 40.0)             # 未给长度时默认 4d
    _close(data["b"], 26.0)             # 2d + 6
    assert data["head"]["form"] == "hex"
    assert data["head"]["simplified"] is True
    assert len(data["points"]) >= 4
    assert data["table"]["standard"] == "GB/T 5782-2016"


def test_bolt_drawing_with_length() -> None:
    data = bolt_drawing("M10x60")
    _close(data["l"], 60.0)
    _close(data["b"], 26.0)   # l ≤ 125 → b = 2d + 6

    long_bolt = bolt_drawing("M10x150")
    _close(long_bolt["b"], 2 * 10 + 12)  # 125 < l ≤ 200


def test_bolt_drawing_fine_thread() -> None:
    data = bolt_drawing("M10x1.5x60")
    _close(data["pitch"], 1.5)
    _close(data["l"], 60.0)
    _close(data["d"], 10.0)


def test_bolt_errors() -> None:
    _expect_value_error(bolt_drawing, "X10")
    _expect_value_error(bolt_drawing, "M7.5x50")
    _expect_value_error(bolt_drawing, "M10x0")


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
