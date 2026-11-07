"""pairkit —— 辨析对比图（A / B 成对）的 SVG 工具箱。纯标准库。

视觉语言沿用 kb/figures/_tools/svgkit.py（同一套线宽、字体栈），但针对「左右并排
两个图形 + 差异点编号」做了三处扩充：

  1. 固定画布 760×420，左右各一个 380 宽的图形区，中间一条竖分隔线；
     每区上方 A/B 徽标、下方一行小标题、底部图例区（≤4 条）。
  2. 差异标号：半径 10 的圆圈内写 ①②③④，红色 #dc2626，细引线指向差异处；
     同一编号在 A、B 两个图形区里含义完全相同 —— 这是辨析图的核心约定。
  3. 图元带 data-* 标记：<g data-panel="a|b">、标号带 class="diff-marker"
     data-diff="n"、图例行带 data-diff="n"，供前端按差别编号联动高亮。

与 svgkit 的两处故意不同：
  * 线条颜色写死 #1f2937（任务书要求），不再用 currentColor；
  * 不做 40 图元上限（成对图天然图元多），改由 build_pairs.py 按成对图口径校验。
"""
from __future__ import annotations

import math
from xml.sax.saxutils import escape

# ---------------------------------------------------------------- 颜色 / 线宽
INK = "#1f2937"      # 线条深色（任务书指定）
RED = "#dc2626"      # 差异标号
BLUE = "#2563eb"
GREEN = "#16a34a"
MUTED = "#6b7280"
RULE = "#d7dde6"     # 分隔线 / 图例分隔线
ARROW = "#1f2937"

# 国标（GB/T 17450、GB/T 4457.4）线宽：粗实线 2、细实线 0.8
STROKE = {
    "thick": 'stroke-width="2"',
    "thin": 'stroke-width="0.8"',
    "dash": 'stroke-width="0.8" stroke-dasharray="6 4"',
    "center": 'stroke-width="0.8" stroke-dasharray="18 4 3 4"',
    "dbl": 'stroke-width="0.8" stroke-dasharray="20 4 3 4 3 4"',
    "marker": 'stroke-width="1.2"',    # 差异标号圆圈，比细实线略重才看得见
}

FONT = 'font-family="system-ui, sans-serif"'
CIRCLED = "①②③④⑤⑥"

# ---------------------------------------------------------------- 画布布局
W, H = 760, 420
PW = 380                 # 单个图形区宽度
Y_TITLE = 23             # 对比图总标题
Y_SUB = 41               # 一句话副标题（同一零件 / 同一剖切位置之类）
Y_BADGE = 64             # A / B 徽标中心
G_TOP, G_BOT = 76, 288   # 图形区上下界
Y_CAP = 307              # 小标题："A：半剖视图"
Y_RULE = 318             # 图例上方的细横线
LEG_Y0, LEG_DY = 340, 20  # 图例行（最多 4 行：340 / 360 / 380 / 400）

HATCH_DEFS = f"""
  <pattern id="hatch45" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
    <line x1="0" y1="0" x2="0" y2="6" stroke="{INK}" stroke-width="0.8"/>
  </pattern>
  <pattern id="hatch135" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(-45)">
    <line x1="0" y1="0" x2="0" y2="6" stroke="{INK}" stroke-width="0.8"/>
  </pattern>
  <pattern id="hatch45d" width="4" height="4" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
    <line x1="0" y1="0" x2="0" y2="4" stroke="{INK}" stroke-width="0.8"/>
  </pattern>"""

ARROW_DEFS = f"""
  <marker id="ar-ink" viewBox="0 0 8 8" refX="7.2" refY="4" markerUnits="userSpaceOnUse"
          markerWidth="8" markerHeight="8" orient="auto-start-reverse">
    <path d="M0.6,0.9 L7.2,4 L0.6,7.1 Z" fill="{ARROW}"/>
  </marker>
  <marker id="ar-red" viewBox="0 0 8 8" refX="7.2" refY="4" markerUnits="userSpaceOnUse"
          markerWidth="8" markerHeight="8" orient="auto-start-reverse">
    <path d="M0.6,0.9 L7.2,4 L0.6,7.1 Z" fill="{RED}"/>
  </marker>"""


def f(v: float) -> str:
    """紧凑数字：去掉无意义的 .0，最多两位小数。"""
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def arc_pts(cx, cy, r, a0, a1, n=40):
    """角度制采样圆弧（0°=+x，角度增大 = 屏幕顺时针，y 轴向下）。a1<a0 时反向走。"""
    return [
        (cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
         cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / n)))
        for i in range(n + 1)
    ]


def wave_pts(x1, x2, yfun, amp=3.0, period=13.0, step=2.0):
    """沿 x 取样的波浪线（手画断裂边界）：幅度与相位都轻微漂移，不做规则正弦。"""
    n = max(8, int(abs(x2 - x1) / step))
    pts = []
    for i in range(n + 1):
        x = x1 + (x2 - x1) * i / n
        k = (x - x1) / period
        a = amp * (0.55 + 0.45 * abs(math.sin(k * 0.83 + 1.1)))
        ph = 2 * math.pi * k + 0.5 * math.sin(k * 0.61)
        pts.append((x, yfun(x) + a * math.sin(ph)))
    return pts


def d_of_pts(pts, close=False) -> str:
    if not pts:
        return ""
    d = f"M{f(pts[0][0])},{f(pts[0][1])}"
    d += "".join(f" L{f(x)},{f(y)}" for x, y in pts[1:])
    return d + (" Z" if close else "")


class Panel:
    """一个图形区（局部坐标 0..380，写盘时整体平移 ox）。"""

    def __init__(self, fig: "PairFigure", key: str, ox: float):
        self.fig = fig
        self.key = key          # "a" / "b"
        self.ox = ox
        self.items: list[str] = []

    # ------------------------------------------------------------ 基础图元
    def _add(self, s: str) -> None:
        self.items.append(s)

    def line(self, x1, y1, x2, y2, cls="thin", color=INK, extra="") -> None:
        self._add(
            f'<line x1="{f(x1 + self.ox)}" y1="{f(y1)}" x2="{f(x2 + self.ox)}" y2="{f(y2)}" '
            f'stroke="{color}" {STROKE[cls]}{(" " + extra) if extra else ""}/>'
        )

    def arrow_line(self, x1, y1, x2, y2, color=INK, cls="thin", both=True, marker="ink", extra="") -> None:
        mk = (f'marker-start="url(#ar-{marker})" marker-end="url(#ar-{marker})"' if both
              else f'marker-end="url(#ar-{marker})"')
        self._add(
            f'<line x1="{f(x1 + self.ox)}" y1="{f(y1)}" x2="{f(x2 + self.ox)}" y2="{f(y2)}" '
            f'stroke="{color}" {STROKE[cls]} {mk}{(" " + extra) if extra else ""}/>'
        )

    def path(self, d, cls="thick", fill=None, color=INK, extra="") -> None:
        if not d:
            return
        stroke = f'stroke="{color}" {STROKE[cls]}' if cls else 'stroke="none"'
        self._add(
            f'<path d="{d}" {stroke} fill="{fill or "none"}"'
            f'{(" " + extra) if extra else ""}/>'
        )

    def polyline(self, pts, cls="thick", close=False, color=INK, fill=None, extra="") -> None:
        """注意：平移只作用于 x —— 先对点集做 ox 平移，再序列化。"""
        if not pts:
            return
        d = d_of_pts([(x + self.ox, y) for x, y in pts], close)
        self.path(d, cls=cls, fill=fill, color=color, extra=extra)

    def rect(self, x, y, w, h, cls="thick", fill=None, color=INK, extra="") -> None:
        self._add(
            f'<rect x="{f(x + self.ox)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" '
            f'stroke="{color}" {STROKE[cls]} fill="{fill or "none"}"'
            f'{(" " + extra) if extra else ""}/>'
        )

    def circle(self, cx, cy, r, cls="thin", fill=None, color=INK, extra="") -> None:
        self._add(
            f'<circle cx="{f(cx + self.ox)}" cy="{f(cy)}" r="{f(r)}" '
            f'stroke="{color}" {STROKE[cls]} fill="{fill or "none"}"'
            f'{(" " + extra) if extra else ""}/>'
        )

    def dot(self, cx, cy, r=2.2, color=INK) -> None:
        self._add(
            f'<circle cx="{f(cx + self.ox)}" cy="{f(cy)}" r="{f(r)}" fill="{color}" stroke="none"/>'
        )

    def hatch(self, pts, pat="hatch45") -> None:
        """剖面线：只填线，不填色（背景保持透明）。"""
        if not pts:
            return
        d = d_of_pts([(x + self.ox, y) for x, y in pts], True)
        self._add(f'<path d="{d}" fill="url(#{pat})" stroke="none"/>')

    # ------------------------------------------------------------ 复合图元
    def arc(self, cx, cy, r, a0, a1, cls="thick", color=INK, n=40) -> None:
        self.polyline(arc_pts(cx, cy, r, a0, a1, n), cls=cls, color=color)

    def wave(self, x1, x2, yfun, amp=3.0, period=13.0, cls="thin", color=INK, step=2.0):
        pts = wave_pts(x1, x2, yfun, amp, period, step)
        self.polyline(pts, cls=cls, color=color)
        return pts

    def text(self, x, y, s, size=11, anchor="middle", color=INK, weight=None, extra="") -> None:
        w = f' font-weight="{weight}"' if weight else ""
        self._add(
            f'<text x="{f(x + self.ox)}" y="{f(y)}" font-size="{size}" {FONT} '
            f'text-anchor="{anchor}" fill="{color}"{w}'
            f'{(" " + extra) if extra else ""}>{escape(str(s))}</text>'
        )

    def leader(self, x1, y1, x2, y2, txt=None, color=MUTED, size=10, anchor="start",
               marker=None, gap=4, dot=False) -> None:
        """引出线：从指向点 (x1,y1) 引到文字端 (x2,y2)，可选箭头/端点小圆点。"""
        if marker:
            self.arrow_line(x1, y1, x2, y2, color=color, both=False, marker=marker)
        else:
            self.line(x1, y1, x2, y2, cls="thin", color=color)
        if dot:
            self.dot(x1, y1, 1.7, color)
        if txt:
            if anchor == "start":
                self.text(x2 + gap, y2 + 3.6, txt, size=size, anchor="start", color=color)
            elif anchor == "end":
                self.text(x2 - gap, y2 + 3.6, txt, size=size, anchor="end", color=color)
            else:
                self.text(x2, y2 - gap, txt, size=size, anchor="middle", color=color)

    def dim_h(self, x1, x2, y, txt, ext_from=None, color=INK, above=True, size=11, gap=4) -> None:
        """水平尺寸：尺寸线 + 两端箭头 + 尺寸界线；数字写在尺寸线上方。"""
        self.arrow_line(x1, y, x2, y, color=color, both=True)
        ty = y - gap if above else y + gap + size * 0.8
        self.text((x1 + x2) / 2, ty, txt, size=size, color=color)
        if ext_from:
            for xx, y0 in ((x1, ext_from[0]), (x2, ext_from[1])):
                s = 1 if y > y0 else -1
                self.line(xx, y0 + s * 3, xx, y + s * 5, cls="thin", color=color)

    def dim_v(self, x, y1, y2, txt, ext_from=None, color=INK, left=True, size=11, gap=4) -> None:
        self.arrow_line(x, y1, x, y2, color=color, both=True)
        tx = x - gap if left else x + gap
        self.text(tx, (y1 + y2) / 2 + size * 0.35, txt, size=size,
                  anchor="end" if left else "start", color=color)
        if ext_from:
            for yy, x0 in ((y1, ext_from[0]), (y2, ext_from[1])):
                s = 1 if x > x0 else -1
                self.line(x0 + s * 3, yy, x + s * 5, yy, cls="thin", color=color)

    # ------------------------------------------------------------ 差异标号
    def callout(self, no: int, tx: float, ty: float, mx: float, my: float) -> None:
        """在 (mx,my) 画半径 10 的编号圆圈，用细引线指向差异处 (tx,ty)。

        编号 1..4 → ①②③④，与图例行、pairs.jsonl 的 differences[].no 一一对应。
        """
        dx, dy = tx - mx, ty - my
        dist = math.hypot(dx, dy) or 1.0
        ux, uy = dx / dist, dy / dist
        self.line(mx + ux * 11, my + uy * 11, tx, ty, cls="thin", color=RED)
        self.dot(tx, ty, 1.7, RED)
        self.circle(mx, my, 10, cls="marker", color=RED,
                    extra=f'class="diff-marker" data-diff="{no}"')
        self.text(mx, my + 3.7, CIRCLED[no - 1], size=11, color=RED,
                  extra=f'class="diff-no" data-diff="{no}"')


class PairFigure:
    """一张辨析对比图。"""

    def __init__(self, pair_id: str, title: str, subtitle: str,
                 a_caption: str, b_caption: str, a_ok=True, b_ok=True):
        self.pair_id = pair_id
        self.title = title
        self.subtitle = subtitle
        self.captions = {"a": a_caption, "b": b_caption}
        self.ok = {"a": a_ok, "b": b_ok}
        self.a = Panel(self, "a", 0)
        self.b = Panel(self, "b", PW)
        self.legend: list[tuple[int | None, str]] = []

    # ------------------------------------------------------------ 图例
    def leg(self, no: int | None, txt: str) -> None:
        """图例行：no=1..4 前缀 ①②③④；no=None 为“注：”行。"""
        if len(self.legend) >= 4:
            raise ValueError(f"{self.pair_id} 图例超过 4 条")
        self.legend.append((no, txt))

    # ------------------------------------------------------------ 组装
    def svg(self) -> str:
        p = self.pair_id
        out: list[str] = []

        # 总标题 + 副标题
        out.append(f'<text x="380" y="{Y_TITLE}" font-size="13.5" {FONT} text-anchor="middle" '
                   f'fill="{INK}" font-weight="600">{escape(self.title)}</text>')
        out.append(f'<text x="380" y="{Y_SUB}" font-size="10.5" {FONT} text-anchor="middle" '
                   f'fill="{MUTED}">{escape(self.subtitle)}</text>')

        # A / B 图形区
        for panel in (self.a, self.b):
            key = panel.key
            cap = escape(self.captions[key])
            out.append(f'<g data-panel="{key}" data-caption="{cap}">')
            bx = 32 + panel.ox
            out.append(f'  <circle cx="{f(bx)}" cy="{Y_BADGE}" r="11" stroke="{INK}" '
                       f'stroke-width="1.2" fill="none"/>')
            out.append(f'  <text x="{f(bx)}" y="{Y_BADGE + 4.4}" font-size="12" {FONT} '
                       f'text-anchor="middle" fill="{INK}" font-weight="700">{key.upper()}</text>')
            out.extend("  " + s for s in panel.items)
            out.append("</g>")
            # 小标题（图形下方一行）：正确用墨色、错误用红色，不加 ✓/✗ 字形
            # （✓ U+2713 / ✗ U+2717 在部分中文字体里缺字，会变成豆腐块）
            tone = INK if self.ok[key] else RED
            out.append(f'<text x="{f(190 + panel.ox)}" y="{Y_CAP}" font-size="12" {FONT} '
                       f'text-anchor="middle" fill="{tone}" font-weight="600">'
                       f'{escape(key.upper() + "：" + self.captions[key])}</text>')

        # 竖分隔线
        out.append(f'<line x1="{PW}" y1="{G_TOP}" x2="{PW}" y2="{Y_RULE - 4}" '
                   f'stroke="{RULE}" stroke-width="1"/>')
        # 图例上方的细横线
        out.append(f'<line x1="20" y1="{Y_RULE}" x2="740" y2="{Y_RULE}" '
                   f'stroke="{RULE}" stroke-width="1"/>')

        # 图例
        out.append('<g data-legend="1">')
        for i, (no, txt) in enumerate(self.legend):
            y = LEG_Y0 + i * LEG_DY
            if no is None:
                pre, body = "注：", txt
                out.append(f'  <text x="20" y="{y}" font-size="10.5" {FONT} text-anchor="start" '
                           f'fill="{MUTED}" data-diff="0">{escape(pre + body)}</text>')
            else:
                out.append(f'  <text x="20" y="{y}" font-size="10.5" {FONT} text-anchor="start" '
                           f'fill="{INK}" data-diff="{no}">{escape(CIRCLED[no - 1] + " " + txt)}</text>')
        out.append("</g>")

        desc = self.subtitle + " | A：" + self.captions["a"] + "；B：" + self.captions["b"]
        body = "\n  ".join(out)
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
            f'width="100%" height="100%" style="height:auto;display:block" '
            f'preserveAspectRatio="xMidYMid meet" role="img" '
            f'aria-labelledby="{self.pair_id}-t {self.pair_id}-d" class="fig-svg pair-svg" '
            f'data-pair-id="{self.pair_id}">\n'
            f'  <title id="{self.pair_id}-t">{escape(self.title)}</title>\n'
            f'  <desc id="{self.pair_id}-d">{escape(desc)}</desc>\n'
            f"  <defs>{HATCH_DEFS}{ARROW_DEFS}\n  </defs>\n"
            f'  <g stroke-linecap="round" stroke-linejoin="round">\n  {body}\n  </g>\n</svg>\n'
        )
