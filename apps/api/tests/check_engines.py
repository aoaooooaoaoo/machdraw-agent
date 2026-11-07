"""引擎锚点验收：用老师会随口问的经典数值核对公差表、螺纹、圆弧。

    apps\\api\\.venv\\Scripts\\python.exe apps\\api\\tests\check_engines.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from app.domain.tolerance import parse_fit, solve_fit  # noqa: E402
from app.domain.thread import thread_drawing  # noqa: E402
from app.geometry.arc import build_steps  # noqa: E402

PASS = FAIL = 0


def check(label: str, got, want, tol: float = 1e-9) -> None:
    global PASS, FAIL
    if isinstance(want, tuple):
        ok = all(abs(g - w) <= tol for g, w in zip(got, want))
    elif isinstance(want, float):
        ok = abs(got - want) <= tol
    else:
        ok = got == want
    print(f"  {'OK ' if ok else 'BAD'} {label:26} want={want}  got={got}")
    if ok:
        PASS += 1
    else:
        FAIL += 1


def main() -> int:
    print("=== 1. 公差基本偏差锚点（GB/T 1800.1） ===")
    # (代号, 期望上偏差, 期望下偏差) —— 均为孔代号（大写）
    anchors = [
        ("Φ30 H7", 0.021, 0.0),
        ("Φ30 H8", 0.033, 0.0),
        ("Φ50 H7", 0.025, 0.0),
        ("Φ20 H8", 0.033, 0.0),
        ("Φ45 JS6", 0.008, -0.008),
        ("Φ30 K7", 0.006, -0.015),
        ("Φ30 N7", -0.007, -0.028),
        ("Φ30 P7", -0.014, -0.035),
    ]
    for spec, es, ei in anchors:
        p = parse_fit(spec)
        r = solve_fit(p["phi"], p["hole"], p.get("shaft") or "h6")
        h = r["hole"]
        check(f"{spec} 孔", (round(h["ES"], 6), round(h["EI"], 6)), (es, ei))

    print("\n=== 2. 轴基本偏差锚点 ===")
    shaft_anchors = [
        ("Φ30 h6", 0.0, -0.013),
        ("Φ30 k6", 0.015, 0.002),
        ("Φ30 f7", -0.020, -0.041),
        ("Φ50 h6", 0.0, -0.016),
        ("Φ20 f7", -0.020, -0.041),
        ("Φ45 js6", 0.008, -0.008),
        ("Φ30 p6", 0.035, 0.022),
    ]
    for spec, es, ei in shaft_anchors:
        p = parse_fit(spec)
        r = solve_fit(p["phi"], p.get("hole") or "H7", p["shaft"])
        s = r["shaft"]
        check(f"{spec} 轴", (round(s["es"], 6), round(s["ei"], 6)), (es, ei))

    print("\n=== 3. 配合类型判定 ===")
    cases = [
        ("Φ30 H7/k6", "过渡配合"),
        ("Φ30 H7/h6", "间隙配合"),
        ("Φ30 H7/f7", "间隙配合"),
        ("Φ50 H7/g6", "间隙配合"),
        ("Φ30 H7/s6", "过盈配合"),
        ("Φ30 H7/p6", "过盈配合"),
    ]
    for spec, want in cases:
        p = parse_fit(spec)
        r = solve_fit(p["phi"], p["hole"], p["shaft"])
        check(f"{spec} 类型", r["fit"]["type"], want)

    print("\n=== 4. 配合制判定 ===")
    p = parse_fit("Φ30 H7/k6")
    r = solve_fit(p["phi"], p["hole"], p["shaft"])
    check("Φ30 H7/k6 制", r["system"], "基孔制")
    r2 = solve_fit(30.0, "K7", "h6")
    check("Φ30 K7/h6 制", r2["system"], "基轴制")

    print("\n=== 5. 螺纹比例画法 ===")
    for spec, d, d1 in [("M10", 10.0, 8.5), ("M10×1.5", 10.0, 8.5), ("M20", 20.0, 17.0)]:
        out = thread_drawing(spec)
        check(f"{spec} d", float(out["d"]), d)
        check(f"{spec} d1", float(out["d1"]), d1)
    t = thread_drawing("M10×1.5")
    check("M10×1.5 螺距", float(t.get("pitch", 0)), 1.5)

    print("\n=== 6. 圆弧连接几何 ===")
    # R10 圆角连接两条沿 x/y 正方向的垂直直线：圆心 (10,10)，切点 (10,0)、(0,10)
    try:
        res = build_steps("line_line", r=10.0,
                          line1=[(0.0, 0.0), (100.0, 0.0)],
                          line2=[(0.0, 0.0), (0.0, 100.0)])
        steps = res.get("steps") or []
        print(f"  steps={len(steps)} summary={res.get('summary','')[:60]}")
        pts = []
        for s in steps:
            for d in (s.get("draw") or []):
                if d.get("op") == "point":
                    pts.append(tuple(round(x, 3) for x in d["p"]))
        print(f"  关键点: {pts[:6]}")
        ok = (10.0, 10.0) in pts
        print(f"  {'OK ' if ok else 'BAD'} 圆心应为 (10,10)")
        globals()["PASS"] = PASS + (1 if ok else 0)
        globals()["FAIL"] = FAIL + (0 if ok else 1)
    except Exception as exc:
        print(f"  BAD 圆弧连接报错：{type(exc).__name__}: {exc}")
        globals()["FAIL"] = FAIL + 1

    print(f"\n{'='*50}\n通过 {PASS} / 失败 {FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
