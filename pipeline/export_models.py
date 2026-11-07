"""把所有教学模型的三视图导出成 SVG / HTML 预览（离线检查用）。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "apps" / "api"
sys.path.insert(0, str(API))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from app.geometry.models import MODELS, build_model  # noqa: E402
from app.geometry.projection import build_three_view, to_svg  # noqa: E402

OUT = ROOT / "data" / "models"
OUT.mkdir(parents=True, exist_ok=True)


def main() -> int:
    cards = []
    for mid, meta in MODELS.items():
        d = build_three_view(build_model(mid), meta["name"], mid)
        svg = to_svg(d, width=640)
        (OUT / f"{mid}.svg").write_text(svg, encoding="utf-8")
        stats = d["stats"]
        cards.append(
            f'<div class="card"><h3>{meta["name"]} <small>{mid}</small></h3>{svg}'
            f'<p>主视 {stats["front"]["visible"]}实/{stats["front"]["hidden"]}虚 · '
            f'俯视 {stats["top"]["visible"]}实/{stats["top"]["hidden"]}虚 · '
            f'左视 {stats["left"]["visible"]}实/{stats["left"]["hidden"]}虚</p></div>'
        )
        print(f"{mid:14} {meta['name']:8} -> {mid}.svg  ({len(svg)} bytes)")
    html = (
        '<html><head><meta charset="utf-8"><style>'
        "body{background:#eef2f7;font-family:system-ui;margin:16px}"
        ".grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}"
        ".card{background:#fff;border-radius:10px;padding:8px;box-shadow:0 1px 4px rgba(0,0,0,.12)}"
        ".card h3{margin:4px 8px;font-size:15px;color:#111827}"
        ".card h3 small{color:#9ca3af;font-weight:400}"
        ".card p{margin:2px 8px 6px;font-size:12px;color:#6b7280}"
        "</style></head><body><div class='grid'>"
        + "".join(cards)
        + "</div></body></html>"
    )
    (OUT / "preview.html").write_text(html, encoding="utf-8")
    print(f"\n预览：{OUT / 'preview.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
