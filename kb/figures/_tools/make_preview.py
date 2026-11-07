"""生成两张用于人工/浏览器检查的预览页（只写 _tools 目录，不进产品）。

  preview_all.html  —— 15 张图总览（3 列网格）
  preview_one.html  —— 单张放大（?f=FIG-XXX.svg 切换），用于细看几何
预览时深色/浅色各看一遍：页面提供 <body class="dark"> 切换按钮。
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIG_DIR = HERE.parent
sys.path.insert(0, str(HERE))
from catalog import CATALOG  # noqa: E402

CSS = """
* { box-sizing: border-box; }
body { margin: 0; padding: 18px; background: #eef2f7; color: #0f172a;
       font-family: system-ui, -apple-system, 'Segoe UI', 'Microsoft YaHei', sans-serif; }
body.dark { background: #0b1220; color: #e2e8f0; }
h1 { font-size: 15px; margin: 0 0 12px; font-weight: 600; }
.grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
.card { background: #ffffff; border: 1px solid #e3e9f1; border-radius: 10px; padding: 8px;
        display: flex; flex-direction: column; gap: 4px; }
body.dark .card { background: #131c2e; border-color: #24324a; }
.card .fid { font-size: 11px; letter-spacing: .02em; opacity: .65; font-family: ui-monospace, monospace; }
.card .cap { font-size: 11px; line-height: 1.45; opacity: .85; }
svg.fig-svg { width: 100%; height: auto; display: block; }
.toolbar { position: fixed; right: 14px; top: 14px; display: flex; gap: 8px; }
.toolbar button { font: inherit; font-size: 12px; padding: 6px 10px; border-radius: 7px;
                  border: 1px solid #cfd9e6; background: #fff; cursor: pointer; }
body.dark .toolbar button { background: #1c2840; color: #e2e8f0; border-color: #2c3b57; }
.one { max-width: 1180px; margin: 0 auto; }
"""

JS = """
document.getElementById('theme').onclick = () => document.body.classList.toggle('dark');
"""


def write_all() -> None:
    cells = []
    for c in CATALOG:
        svg = (FIG_DIR / f"{c['figure_id']}.svg").read_text(encoding="utf-8")
        cells.append(
            f'<div class="card"><div class="fid">{c["figure_id"]}</div>{svg}'
            f'<div class="cap">{c["caption"]}</div></div>'
        )
    html = (
        '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
        f"<title>教学图形库总览</title><style>{CSS}</style></head><body>"
        '<div class="toolbar"><button id="theme">切换深色</button></div>'
        f'<h1>机械制图 AI 助教 · 教学图形库（{len(CATALOG)} 张自绘 SVG）</h1>'
        f'<div class="grid">{"".join(cells)}</div><script>{JS}</script></body></html>'
    )
    (HERE / "preview_all.html").write_text(html, encoding="utf-8")
    print("wrote preview_all.html")


def write_one() -> None:
    """单张放大页：preview_one.html?f=FIG-LUOWEN.svg

    全部 SVG 直接内联、用 display 切换 —— file:// 下 fetch 会被 CORS 拦掉，不能靠它。
    """
    blocks = []
    for c in CATALOG:
        svg = (FIG_DIR / f"{c['figure_id']}.svg").read_text(encoding="utf-8")
        blocks.append(f'<div class="one" data-fid="{c["figure_id"]}.svg" hidden>{svg}</div>')
    names = "".join(f'<option value="{c["figure_id"]}.svg">{c["figure_id"]}</option>' for c in CATALOG)
    html = (
        '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
        f"<title>单图检查</title><style>{CSS}</style></head><body>"
        '<div class="toolbar"><select id="sel">' + names + "</select>"
        '<button id="theme">切换深色</button></div>'
        + "".join(blocks)
        + "<script>"
        "const p=new URLSearchParams(location.search);"
        "const f=p.get('f')||'FIG-LUOWEN.svg';"
        "document.getElementById('sel').value=f;"
        "document.querySelectorAll('[data-fid]').forEach(d=>{d.hidden=d.dataset.fid!==f;});"
        "document.getElementById('sel').onchange=e=>{location.search='?f='+e.target.value;location.reload();};"
        "document.getElementById('theme').onclick=()=>document.body.classList.toggle('dark');"
        "</script></body></html>"
    )
    (HERE / "preview_one.html").write_text(html, encoding="utf-8")
    print("wrote preview_one.html")


if __name__ == "__main__":
    write_all()
    write_one()
