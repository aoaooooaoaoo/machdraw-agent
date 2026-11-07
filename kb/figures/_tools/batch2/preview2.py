"""把已生成的 FIG2-*.svg 内联成一张预览页（写在临时目录，不进仓库）。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]   # 仓库根：batch2 → _tools → figures → kb → ROOT
FIG_DIR = REPO / "kb" / "figures"

CSS = """
* { box-sizing: border-box; }
body { margin:0; padding:14px; background:#eef2f7; color:#0f172a;
       font-family: system-ui,-apple-system,'Segoe UI','Microsoft YaHei',sans-serif; }
body.dark { background:#0b1220; color:#e2e8f0; }
h1 { font-size:14px; margin:0 0 10px; }
.grid { display:grid; grid-template-columns: repeat(2, 1fr); gap:12px; }
.card { background:#fff; border:1px solid #e3e9f1; border-radius:10px; padding:8px; }
body.dark .card { background:#131c2e; border-color:#24324a; }
.fid { font-size:11px; opacity:.6; font-family:ui-monospace,monospace; }
.cap { font-size:11px; opacity:.85; margin-top:4px; line-height:1.5; }
svg.fig-svg { width:100%; height:auto; display:block; }
"""


def main() -> int:
    which = sys.argv[1:] or None
    ids = []
    for line in (FIG_DIR / "figures.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if rec["figure_id"].startswith("FIG2-"):
            ids.append(rec["figure_id"])
    if which:
        ids = [i for i in ids if any(w in i for w in which)]
    cards = []
    for fid in ids:
        svg = (FIG_DIR / f"{fid}.svg").read_text(encoding="utf-8")
        cards.append(f'<div class="card"><div class="fid">{fid}</div>{svg}</div>')
    html = ('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
            f'<title>第二批教学图预览</title><style>{CSS}</style></head><body>'
            f'<h1>第二批教学图（{len(ids)} 张）</h1><div class="grid">{"".join(cards)}</div>'
            '</body></html>')
    out = HERE / "preview2.html"
    out.write_text(html, encoding="utf-8")
    print("wrote", out, len(ids))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
