"""把 10 组辨析图内联成一张 QA 预览页（file:// 下 fetch 会被拦，只能内联）。

    D:\\python\\python.exe kb\\figures\\pairs\\_tools\\make_preview.py
产物：kb/figures/pairs/_tools/_qa/preview_pairs.html   ← 浏览器直接打开即可人工检查
深/浅色各看一遍（页面右上角按钮切换），检查剖面线方向、标号是否压线。
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAIR_DIR = HERE.parent
FIG_DIR = PAIR_DIR.parent
OUT = HERE / "_qa" / "preview_pairs.html"

CSS = """
*{box-sizing:border-box}
body{margin:0;padding:14px;background:#eef2f7;color:#0f172a;
     font-family:system-ui,-apple-system,'Segoe UI','Microsoft YaHei',sans-serif}
body.dark{background:#0b1220;color:#e2e8f0}
h1{font-size:15px;margin:0 0 10px;font-weight:600}
.card{background:#fff;border:1px solid #e3e9f1;border-radius:10px;padding:8px;margin:0 0 12px}
body.dark .card{background:#131c2e;border-color:#24324a}
.meta{font-size:11px;letter-spacing:.02em;opacity:.6;font-family:ui-monospace,monospace;margin-bottom:4px}
.cap{font-size:11px;line-height:1.5;opacity:.85;margin-top:4px}
svg.pair-svg{width:100%;height:auto;display:block}
.toolbar{position:fixed;right:12px;top:12px}
.toolbar button{font:inherit;font-size:12px;padding:6px 10px;border-radius:7px;
                border:1px solid #cfd9e6;background:#fff;cursor:pointer}
body.dark .toolbar button{background:#1c2840;color:#e2e8f0;border-color:#2c3b57}
"""


def main() -> None:
    rows = [json.loads(x) for x in (FIG_DIR / "pairs.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    cards = []
    for r in rows:
        svg = (FIG_DIR / r["file"]).read_text(encoding="utf-8")
        cards.append(
            f'<div class="card"><div class="meta">{r["pair_id"]} · {r["chapter"]} · '
            f'{" / ".join(r["kp_ids"])}</div>{svg}'
            f'<div class="cap">{r["title"]}｜A：{r["a"]["caption"]}（{r["a"]["正确性"]}）　'
            f'B：{r["b"]["caption"]}（{r["b"]["正确性"]}）</div></div>'
        )
    html = (
        '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
        f"<title>辨析对比图 QA 预览（{len(rows)} 组）</title><style>{CSS}</style></head><body>"
        '<div class="toolbar"><button id="t">切换深色</button></div>'
        f'<h1>机械制图 AI 助教 · 辨析对比图（{len(rows)} 组，成对 A/B + 差异编号）</h1>'
        + "".join(cards)
        + '<script>document.getElementById("t").onclick=()=>document.body.classList.toggle("dark");</script>'
        "</body></html>"
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(FIG_DIR.parent.parent)}")


if __name__ == "__main__":
    main()
