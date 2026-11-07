"""核对教学图里用到的公差数值是否与项目自带 GB/T 1800 引擎一致。

用法： D:\\python\\python.exe kb\\figures\\_tools\\check_tolerance_values.py
只读，不写任何文件。数值单位换算成 μm 打印，直接对图上的标注。
"""
from __future__ import annotations

import sys
from pathlib import Path

API = Path(__file__).resolve().parents[3] / "apps" / "api"
sys.path.insert(0, str(API))

from app.domain.tolerance import solve_fit  # noqa: E402

CASES = [
    (30.0, "H7", "k6"),
    (30.0, "H7", "g6"),
    (30.0, "H7", "s6"),
]


def um(v: float) -> str:
    x = round(v * 1000, 3)
    return f"{x:+g}"


def main() -> int:
    print("基本尺寸 孔   轴   孔ES   孔EI   轴es   轴ei   类型      最大间隙  最小间隙  最大过盈")
    for phi, h, s in CASES:
        r = solve_fit(phi, h, s)
        hole, shaft = r["hole"], r["shaft"]
        fit = r.get("fit", {})
        print(
            f"Φ{phi:<6g} {h:<4} {s:<4} "
            f"{um(hole['ES']):>6} {um(hole['EI']):>6} "
            f"{um(shaft['es']):>6} {um(shaft['ei']):>6}  "
            f"{str(fit.get('type')):<8} "
            f"{um(fit['max_gap']):>8} {um(fit['min_gap']):>8} {um(fit['max_interference']):>8}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
