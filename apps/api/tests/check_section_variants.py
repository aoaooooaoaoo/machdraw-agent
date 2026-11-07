"""半剖 / 局部剖 验收 + 预览导出。"""
from __future__ import annotations

import sys
from pathlib import Path

API = Path(__file__).resolve().parents[1]
ROOT = API.parents[1]
sys.path.insert(0, str(API))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from app.geometry.models import build_model, model_name  # noqa: E402
from app.geometry.projection import to_svg  # noqa: E402
from app.geometry.section import (  # noqa: E402
    build_half_section_view,
    build_local_section_view,
)

OUT = ROOT / "data" / "models"
OUT.mkdir(parents=True, exist_ok=True)

PASS = FAIL = 0


def check(label: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    print(f"  {'OK ' if cond else 'BAD'} {label} {detail}")
    if cond:
        PASS += 1
    else:
        FAIL += 1


def main() -> int:
    cards = []

    print("=== 1. 半剖视图（带通孔方块，对称机件） ===")
    d = build_half_section_view(build_model("M-HOLE-BLOCK"), "带通孔方块", "M-HOLE-BLOCK", "y")
    segs = d["segments"]
    outline = [s for s in segs if s["view"] == "outline"]
    section = [s for s in segs if s["view"] == "section"]
    center = [s for s in segs if s["kind"] == "centerline"]
    check("有视图侧与剖视侧", len(outline) > 0 and len(section) > 0,
          f"（视图 {len(outline)} / 剖视 {len(section)}）")
    check("有对称中心线", len(center) == 1)
    check("剖面线只在剖视侧", len(d["hatch"]) > 0, f"（{len(d['hatch'])} 条）")
    if center:
        cx = center[0]["x1"]
        left_out = all(s["x1"] <= cx + 0.5 and s["x2"] <= cx + 0.5 for s in outline)
        right_sec = all(s["x1"] >= cx - 0.5 and s["x2"] >= cx - 0.5 for s in section)
        check("视图在中心线左侧", left_out)
        check("剖视在中心线右侧", right_sec)
        check("剖面线都在剖视侧",
              all(h["x1"] >= cx - 0.5 and h["x2"] >= cx - 0.5 for h in d["hatch"]))
    cards.append(f"<div class='c'><h3>{d['name']} · 半剖（沿 Y）</h3>{to_svg(d, width=600)}"
                 f"<p>{d['note']}</p></div>")

    print("\n=== 2. 局部剖视图（带通孔方块） ===")
    d2 = build_local_section_view(build_model("M-HOLE-BLOCK"), "带通孔方块", "M-HOLE-BLOCK", "y")
    wave = [s for s in d2["segments"] if s["kind"] == "wave"]
    check("有波浪线边界", len(wave) > 10, f"（{len(wave)} 段折线）")
    check("有剖面线", len(d2["hatch"]) > 0, f"（{len(d2['hatch'])} 条）")
    check("有外形视图与剖视部分",
          any(s["view"] == "outline" for s in d2["segments"])
          and any(s["view"] == "section" for s in d2["segments"]))
    cards.append(f"<div class='c'><h3>{d2['name']} · 局部剖（沿 Y）</h3>{to_svg(d2, width=600)}"
                 f"<p>{d2['note']}</p></div>")

    print("\n=== 3. 圆筒：半剖 / 局部剖 ===")
    for name, fn in (("半剖", build_half_section_view), ("局部剖", build_local_section_view)):
        try:
            dd = fn(build_model("M-TUBE"), "圆筒", "M-TUBE", "y")
            print(f"  OK  {name}: 线段 {len(dd['segments'])}  剖面线 {len(dd['hatch'])}")
            cards.append(f"<div class='c'><h3>圆筒 · {name}</h3>{to_svg(dd, width=600)}"
                         f"<p>{dd['note']}</p></div>")
        except Exception as exc:
            print(f"  BAD {name}: {type(exc).__name__}: {exc}")

    html = (
        '<html><head><meta charset="utf-8"><style>'
        "body{background:#eef2f7;font-family:system-ui;margin:14px}"
        ".g{display:grid;grid-template-columns:1fr 1fr;gap:14px}"
        ".c{background:#fff;border-radius:10px;padding:8px}"
        "h3{margin:4px 8px;font-size:14px}.c p{margin:2px 8px;font-size:12px;color:#6b7280}"
        "</style></head><body><div class='g'>" + "".join(cards) + "</div></body></html>"
    )
    (OUT / "preview_halflocal.html").write_text(html, encoding="utf-8")
    print(f"\n预览：{OUT / 'preview_halflocal.html'}")
    print(f"\n{'='*50}\n通过 {PASS} / 失败 {FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
