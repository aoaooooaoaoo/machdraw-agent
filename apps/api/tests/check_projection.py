"""三视图投影引擎验收：用可手算的形体核对结果。"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from app.geometry.models import MODELS, build_model  # noqa: E402
from app.geometry.projection import build_three_view, to_svg  # noqa: E402

PASS = FAIL = 0


def check(label: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    print(f"  {'OK ' if cond else 'BAD'} {label} {detail}")
    if cond:
        PASS += 1
    else:
        FAIL += 1


def span(segs, axis):
    vals = []
    for s in segs:
        vals += [s[axis + "1"], s[axis + "2"]]
    return (min(vals), max(vals)) if vals else (0, 0)


def main() -> int:
    print("=== 1. 长方体（三视图应各为一个矩形，无虚线） ===")
    t0 = time.time()
    d = build_three_view(build_model("M-BOX"), "长方体", "M-BOX")
    print(f"  用时 {time.time()-t0:.1f}s")
    for v in ("front", "top", "left"):
        segs = [s for s in d["segments"] if s["view"] == v]
        hidden = [s for s in segs if s["hidden"]]
        check(f"{v} 段数=4 且无虚线",
              len(segs) == 4 and not hidden,
              f"（实得 {len(segs)} 段，虚线 {len(hidden)}）")

    print("\n=== 2. 长方体三视图尺寸关系（长对正/高平齐/宽相等） ===")
    L, W, H = d["size"]["L"], d["size"]["W"], d["size"]["H"]
    f = [s for s in d["segments"] if s["view"] == "front"]
    t = [s for s in d["segments"] if s["view"] == "top"]
    lf = [s for s in d["segments"] if s["view"] == "left"]
    check("主视图宽 = L", abs((span(f, "x")[1] - span(f, "x")[0]) - L) < 0.01,
          f"{span(f,'x')} vs L={L}")
    check("主视图高 = H", abs((span(f, "y")[1] - span(f, "y")[0]) - H) < 0.01,
          f"{span(f,'y')} vs H={H}")
    check("俯视图宽与主视图长对正", abs(span(t, "x")[0] - span(f, "x")[0]) < 0.01
          and abs(span(t, "x")[1] - span(f, "x")[1]) < 0.01, f"{span(t,'x')} vs {span(f,'x')}")
    check("左视图高与主视图高平齐", abs(span(lf, "y")[0] - span(f, "y")[0]) < 0.01
          and abs(span(lf, "y")[1] - span(f, "y")[1]) < 0.01, f"{span(lf,'y')} vs {span(f,'y')}")
    top_h = span(t, "y")[1] - span(t, "y")[0]
    left_w = span(lf, "x")[1] - span(lf, "x")[0]
    check("宽相等：俯视图高 = 左视图宽", abs(top_h - left_w) < 0.01, f"{top_h} vs {left_w}")

    print("\n=== 3. L 形块（主视图应为 L 形，6 段） ===")
    d2 = build_three_view(build_model("M-L-BLOCK"), "L 形块", "M-L-BLOCK")
    f2 = [s for s in d2["segments"] if s["view"] == "front"]
    check("主视图 6 段", len(f2) == 6, f"（实得 {len(f2)}）")
    check("主视图无虚线（L 形全可见）", not any(s["hidden"] for s in f2))
    t2 = [s for s in d2["segments"] if s["view"] == "top"]
    print(f"  俯视图 {len(t2)} 段（含虚线 {sum(1 for s in t2 if s['hidden'])}）")

    print("\n=== 4. 带通孔方块（俯视图应有孔线，主视图应有虚线孔壁） ===")
    d3 = build_three_view(build_model("M-HOLE-BLOCK"), "带通孔方块", "M-HOLE-BLOCK")
    t3 = [s for s in d3["segments"] if s["view"] == "top"]
    f3 = [s for s in d3["segments"] if s["view"] == "front"]
    print(f"  俯视图 {len(t3)} 段（虚线 {sum(1 for s in t3 if s['hidden'])}）")
    print(f"  主视图 {len(f3)} 段（虚线 {sum(1 for s in f3 if s['hidden'])}）")
    # 俯视图里孔是可见圆（从上看能看见孔）→ 线段都在；主视图里孔壁不可见 → 应有虚线
    check("主视图存在虚线（内孔不可见）", any(s["hidden"] for s in f3))
    check("俯视图孔口可见（无隐藏线）", not any(s["hidden"] for s in t3))

    print("\n=== 5. 圆筒（主视图应为两竖线+两横线，内孔画虚线） ===")
    d4 = build_three_view(build_model("M-TUBE"), "圆筒", "M-TUBE")
    f4 = [s for s in d4["segments"] if s["view"] == "front"]
    print(f"  主视图 {len(f4)} 段（虚线 {sum(1 for s in f4 if s['hidden'])}）")
    check("主视图有虚线（内孔）", any(s["hidden"] for s in f4))
    check("主视图轮廓宽 = 外径 64",
          abs((span(f4, "x")[1] - span(f4, "x")[0]) - 64) < 0.5,
          f"{span(f4,'x')}")

    print("\n=== 6. 全模型清单 ===")
    rows = []
    for mid in MODELS:
        t = time.time()
        dd = build_three_view(build_model(mid), MODELS[mid]["name"], mid)
        rows.append((mid, MODELS[mid]["name"], dd["size"], len(dd["segments"]),
                     round(time.time() - t, 1)))
    for mid, nm, sz, n, sec in rows:
        print(f"  {mid:14} {nm:8} {sz['L']:5g}×{sz['W']:4g}×{sz['H']:4g}  "
              f"{n:4d} 段  {sec}s")

    print("\n=== 7. SVG 导出 ===")
    svg = to_svg(d2)
    out = Path(__file__).resolve().parents[1] / "_preview_L.html"
    out.write_text(f"<html><body style='background:#eef'>{svg}</body></html>", encoding="utf-8")
    print(f"  SVG {len(svg)} 字节 → {out}")

    print(f"\n{'='*52}\n通过 {PASS} / 失败 {FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
