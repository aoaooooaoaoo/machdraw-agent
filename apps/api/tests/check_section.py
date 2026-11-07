"""剖视图引擎验收 + 预览导出。"""
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
from app.geometry.section import build_section_view  # noqa: E402

OUT = ROOT / "data" / "models"
OUT.mkdir(parents=True, exist_ok=True)

CASES = [
    ("M-HOLE-BLOCK", "y", 0.5),   # 带通孔方块：前后剖，看孔
    ("M-HOLE-BLOCK", "z", 0.5),   # 俯视剖
    ("M-TUBE", "y", 0.5),         # 圆筒：全剖，看内孔
    ("M-CAP", "y", 0.5),          # 端盖
    ("M-L-BLOCK", "y", 0.5),      # L 形块（剖开后看接合）
    ("M-BRACKET", "y", 0.5),      # 支架
]


def main() -> int:
    cards = []
    for mid, axis, ratio in CASES:
        try:
            d = build_section_view(build_model(mid), model_name(mid), mid, axis, ratio)
        except Exception as exc:
            print(f"BAD {mid}/{axis}: {type(exc).__name__}: {exc}")
            continue
        nseg = len(d["segments"])
        nhatch = len(d["hatch"])
        tag = f"{mid}-{axis}"
        (OUT / f"SEC-{tag}.svg").write_text(to_svg(d, width=620), encoding="utf-8")
        print(f"OK  {tag:22} 线段 {nseg:4d}  剖面线 {nhatch:4d}  "
              f"剖切位置 {d['cut_at']:g}  viewBox={d['viewBox']}")
        cards.append(f"<div class='c'><h3>{d['name']} · 剖视（{tag}）</h3>"
                     f"{to_svg(d, width=600)}<p>{d['note']}</p></div>")

    html = (
        '<html><head><meta charset="utf-8"><style>'
        "body{background:#eef2f7;font-family:system-ui;margin:14px}"
        ".g{display:grid;grid-template-columns:1fr 1fr;gap:14px}"
        ".c{background:#fff;border-radius:10px;padding:8px}"
        "h3{margin:4px 8px;font-size:14px}.c p{margin:2px 8px;font-size:12px;color:#6b7280}"
        "</style></head><body><div class='g'>" + "".join(cards) + "</div></body></html>"
    )
    (OUT / "preview_section.html").write_text(html, encoding="utf-8")
    print(f"\n预览：{OUT / 'preview_section.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
