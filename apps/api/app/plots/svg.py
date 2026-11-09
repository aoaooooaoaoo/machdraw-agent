"""纯 stdlib 自包含 SVG 折线图渲染（核反应堆物理 AI 助教的 plot 画布）。

设计目标
--------
* 无第三方依赖（仅 math/typing），无 JS、无外链字体；
* 输出单个 ``<svg>`` 片段，直接可嵌入前端或 Markdown；
* 浅底深字，中文用 ``Microsoft YaHei, PingFang SC, Noto Sans CJK SC``；
* 支持多序列、对数坐标（能谱/分布图常用）、网格、刻度、图例、标注点。

主要入口
--------
``line_chart(series, x_label, y_label, title, ...) -> str``

``series`` 形如::

    [{"name": "n/n0", "points": [[0, 1.0], [0.1, 1.8]], "color": "#2563eb"}]
"""
from __future__ import annotations

import math
from typing import Any, Sequence

__all__ = ["line_chart", "PALETTE", "FONT_FAMILY"]

#: 调色板（色盲友好的蓝/红/绿/橙/紫/青/玫红/橄榄）
PALETTE = [
    "#2563eb", "#dc2626", "#059669", "#d97706",
    "#7c3aed", "#0891b2", "#be185d", "#4d7c0f",
]

FONT_FAMILY = "Microsoft YaHei, PingFang SC, Noto Sans CJK SC, sans-serif"

_BG = "#fbfcfe"
_PLOT_BG = "#ffffff"
_BORDER = "#e2e8f0"
_GRID = "#eef2f7"
_TEXT = "#1f2937"
_MUTED = "#64748b"


def _esc(text: Any) -> str:
    s = str(text)
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))


def _fmt(v: float, digits: int = 4) -> str:
    """刻度/数值格式化：过大过小用科学计数法。"""
    if v is None or not math.isfinite(v):
        return "—"
    av = abs(v)
    if av != 0 and (av >= 1e5 or av < 1e-3):
        return f"{v:.{digits - 1}e}".replace("e+0", "e+").replace("e-0", "e-")
    if av >= 100:
        return f"{v:.0f}"
    if av >= 1:
        return f"{v:.{min(digits, 3)}g}"
    return f"{v:.{digits}g}"


def _nice_step(span: float, target: int = 6) -> float:
    if span <= 0 or not math.isfinite(span):
        return 1.0
    raw = span / max(1, target)
    mag = 10.0 ** math.floor(math.log10(raw))
    for m in (1.0, 2.0, 5.0, 10.0):
        if raw <= m * mag:
            return m * mag
    return 10.0 * mag


def _ticks(lo: float, hi: float, target: int = 6) -> list[float]:
    if not (math.isfinite(lo) and math.isfinite(hi)) or hi <= lo:
        return [lo]
    step = _nice_step(hi - lo, target)
    start = math.ceil(lo / step) * step
    out = []
    v = start
    # 防止浮点误差导致死循环
    for _ in range(200):
        if v > hi + step * 1e-9:
            break
        out.append(0.0 if abs(v) < step * 1e-12 else v)
        v += step
    return out or [lo]


def _fmt_tick(v: float) -> str:
    return _fmt(v, 3)


def line_chart(series: Sequence[dict], x_label: str = "", y_label: str = "",
               title: str = "", markers: Sequence[dict] | None = None,
               annotations: Sequence[dict] | None = None,
               x_log: bool = False, y_log: bool = False,
               width: int = 900, height: int = 520,
               note: str = "", legend: bool = True) -> str:
    """把若干条曲线渲染成自包含 SVG 折线图。

    Args:
        series: ``[{"name": str, "points": [[x,y],...], "color"?: str,
                    "dash"?: bool, "width"?: float}]``。
        x_label / y_label: 轴标题（含单位）。
        title: 图题。
        markers: ``[{"x","y","label"}]``，画成小圆点+文字。
        annotations: ``[{"x","y","text"}]``，画成文字标注。
        x_log / y_log: 是否对数坐标（能谱常用）。
        width / height: 画布尺寸（viewBox 同尺寸，响应式由前端控制）。
        note: 图下方脚注。
        legend: 是否画图例。

    Returns:
        以 ``<svg`` 开头的自包含 SVG 字符串。
    """
    width = int(width) if width > 320 else 900
    height = int(height) if height > 240 else 520
    series = list(series or [])
    markers = list(markers or [])
    annotations = list(annotations or [])

    def tx(v: float) -> float:
        return math.log10(v) if x_log else v

    def ty(v: float) -> float:
        return math.log10(v) if y_log else v

    # ---------------- 收集数据范围
    xs: list[float] = []
    ys: list[float] = []
    clean_series = []
    for s in series:
        pts = []
        for p in (s.get("points") or []):
            try:
                x, y = float(p[0]), float(p[1])
            except (TypeError, ValueError, IndexError):
                continue
            if not (math.isfinite(x) and math.isfinite(y)):
                continue
            if (x_log and x <= 0) or (y_log and y <= 0):
                continue
            pts.append((x, y))
            xs.append(x)
            ys.append(y)
        if pts:
            clean_series.append({**s, "points": pts})
    for m in markers:
        try:
            mx, my = float(m.get("x")), float(m.get("y"))
        except (TypeError, ValueError):
            continue
        if math.isfinite(mx) and math.isfinite(my) and not (x_log and mx <= 0) and not (y_log and my <= 0):
            xs.append(mx)
            ys.append(my)
    for a in annotations:
        try:
            ax, ay = float(a.get("x")), float(a.get("y"))
        except (TypeError, ValueError):
            continue
        if math.isfinite(ax) and math.isfinite(ay):
            xs.append(ax)
            ys.append(ay)

    # ---------------- 布局
    margin_l, margin_r, margin_t, margin_b = 86, 30, 62, 64
    plot_w = max(10.0, width - margin_l - margin_r)
    plot_h = max(10.0, height - margin_t - margin_b)
    x0, y0 = margin_l, margin_t
    x1, y1 = width - margin_r, height - margin_b

    if not xs or not ys:
        xs, ys = [0.0, 1.0], [0.0, 1.0]

    txs = [tx(v) for v in xs]
    tys = [ty(v) for v in ys]
    tlo_x, thi_x = min(txs), max(txs)
    tlo_y, thi_y = min(tys), max(tys)
    if thi_x - tlo_x < 1e-12:
        tlo_x -= 0.5
        thi_x += 0.5
    if thi_y - tlo_y < 1e-12:
        pad = abs(tlo_y) * 0.1 if abs(tlo_y) > 1e-12 else 0.5
        tlo_y -= pad
        thi_y += pad
    pad_x = (thi_x - tlo_x) * 0.04
    pad_y = (thi_y - tlo_y) * 0.08
    tlo_x -= pad_x
    thi_x += pad_x
    tlo_y -= pad_y
    thi_y += pad_y
    if x_log and thi_x - tlo_x > 12:
        pass  # 允许跨多个数量级
    if y_log and thi_y - tlo_y > 12:
        pass

    def sx(v: float) -> float:
        t = tx(v)
        return x0 + (t - tlo_x) / (thi_x - tlo_x) * plot_w

    def sy(v: float) -> float:
        t = ty(v)
        return y1 - (t - tlo_y) / (thi_y - tlo_y) * plot_h

    # ---------------- 刻度
    if x_log:
        xticks = [10.0 ** k for k in range(math.floor(tlo_x), math.ceil(thi_x) + 1)]
    else:
        xticks = _ticks(tlo_x, thi_x, 7)
    if y_log:
        yticks = [10.0 ** k for k in range(math.floor(tlo_y), math.ceil(thi_y) + 1)]
    else:
        yticks = _ticks(tlo_y, thi_y, 6)

    parts: list[str] = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="{FONT_FAMILY}">'
    )
    parts.append(f'<rect x="0" y="0" width="{width}" height="{height}" fill="{_BG}"/>')
    parts.append(f'<rect x="{x0}" y="{y0}" width="{plot_w}" height="{plot_h}" '
                 f'fill="{_PLOT_BG}" stroke="{_BORDER}" stroke-width="1"/>')

    # 标题
    if title:
        parts.append(f'<text x="{width / 2:.1f}" y="34" text-anchor="middle" '
                     f'font-size="20" font-weight="700" fill="{_TEXT}">{_esc(title)}</text>')

    # 网格 + 刻度
    for v in xticks:
        X = sx(v)
        if not (x0 - 0.5 <= X <= x1 + 0.5):
            continue
        parts.append(f'<line x1="{X:.2f}" y1="{y0}" x2="{X:.2f}" y2="{y1}" '
                     f'stroke="{_GRID}" stroke-width="1"/>')
        label = (f"10^{int(round(math.log10(v)))}" if x_log else _fmt_tick(v))
        parts.append(f'<text x="{X:.2f}" y="{y1 + 18}" text-anchor="middle" '
                     f'font-size="12" fill="{_MUTED}">{_esc(label)}</text>')
    for v in yticks:
        Y = sy(v)
        if not (y0 - 0.5 <= Y <= y1 + 0.5):
            continue
        parts.append(f'<line x1="{x0}" y1="{Y:.2f}" x2="{x1}" y2="{Y:.2f}" '
                     f'stroke="{_GRID}" stroke-width="1"/>')
        label = (f"10^{int(round(math.log10(v)))}" if y_log else _fmt_tick(v))
        parts.append(f'<text x="{x0 - 10}" y="{Y + 4:.2f}" text-anchor="end" '
                     f'font-size="12" fill="{_MUTED}">{_esc(label)}</text>')

    # 轴
    parts.append(f'<line x1="{x0}" y1="{y1}" x2="{x1}" y2="{y1}" stroke="{_TEXT}" stroke-width="1.2"/>')
    parts.append(f'<line x1="{x0}" y1="{y0}" x2="{x0}" y2="{y1}" stroke="{_TEXT}" stroke-width="1.2"/>')

    # 轴标题
    if x_label:
        parts.append(f'<text x="{x0 + plot_w / 2:.1f}" y="{height - 18}" text-anchor="middle" '
                     f'font-size="14" fill="{_TEXT}">{_esc(x_label)}</text>')
    if y_label:
        cy = y0 + plot_h / 2
        parts.append(f'<text x="22" y="{cy:.1f}" text-anchor="middle" font-size="14" '
                     f'fill="{_TEXT}" transform="rotate(-90 22 {cy:.1f})">{_esc(y_label)}</text>')

    # 曲线
    for idx, s in enumerate(clean_series):
        color = s.get("color") or PALETTE[idx % len(PALETTE)]
        sw = float(s.get("width", 2.2))
        dash = ' stroke-dasharray="7 5"' if s.get("dash") else ""
        path = []
        for k, (px, py) in enumerate(s["points"]):
            cmd = "M" if k == 0 else "L"
            path.append(f"{cmd}{sx(px):.2f},{sy(py):.2f}")
        parts.append(f'<path d="{" ".join(path)}" fill="none" stroke="{color}" '
                     f'stroke-width="{sw:g}" stroke-linejoin="round" stroke-linecap="round"{dash}/>')

    # 标注点
    for m in markers:
        try:
            mx, my = float(m.get("x")), float(m.get("y"))
            label = str(m.get("label", ""))
        except (TypeError, ValueError):
            continue
        if not (math.isfinite(mx) and math.isfinite(my)):
            continue
        X, Y = sx(mx), sy(my)
        parts.append(f'<circle cx="{X:.2f}" cy="{Y:.2f}" r="4" fill="#f59e0b" '
                     f'stroke="#78350f" stroke-width="1"/>')
        if label:
            parts.append(f'<text x="{X + 7:.2f}" y="{Y - 8:.2f}" font-size="12" '
                         f'fill="#92400e">{_esc(label)}</text>')

    # 文字标注
    for a in annotations:
        try:
            ax, ay = float(a.get("x")), float(a.get("y"))
            txt = str(a.get("text", ""))
        except (TypeError, ValueError):
            continue
        X, Y = sx(ax), sy(ay)
        parts.append(f'<text x="{X:.2f}" y="{Y:.2f}" font-size="12" fill="{_MUTED}">'
                     f'{_esc(txt)}</text>')

    # 图例
    if legend and clean_series:
        lx = x1 - 16
        ly = y0 + 16
        items = []
        for idx, s in enumerate(clean_series):
            color = s.get("color") or PALETTE[idx % len(PALETTE)]
            name = s.get("name", f"序列{idx + 1}")
            items.append((color, name))
        box_w = max(90, 20 + max(len(str(n)) for _, n in items) * 8)
        box_h = 12 + len(items) * 20
        parts.append(f'<rect x="{lx - box_w:.1f}" y="{ly:.1f}" width="{box_w:.1f}" '
                     f'height="{box_h:.1f}" rx="6" fill="#ffffff" fill-opacity="0.92" '
                     f'stroke="{_BORDER}"/>')
        for k, (color, name) in enumerate(items):
            yy = ly + 18 + k * 20
            parts.append(f'<line x1="{lx - box_w + 10:.1f}" y1="{yy:.1f}" '
                         f'x2="{lx - box_w + 30:.1f}" y2="{yy:.1f}" '
                         f'stroke="{color}" stroke-width="3"/>')
            parts.append(f'<text x="{lx - box_w + 36:.1f}" y="{yy + 4:.1f}" '
                         f'font-size="13" fill="{_TEXT}">{_esc(name)}</text>')

    # 脚注
    if note:
        parts.append(f'<text x="{x0}" y="{height - 4}" font-size="11" fill="{_MUTED}">'
                     f'{_esc(note)}</text>')

    parts.append("</svg>")
    return "".join(parts)


def empty_chart(title: str = "暂无数据", width: int = 900, height: int = 520) -> str:
    """无数据占位图。"""
    return line_chart([], title=title, width=width, height=height)
