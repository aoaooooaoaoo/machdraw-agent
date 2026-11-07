"""svgkit —— 教学图 SVG 最小工具箱（纯标准库，不依赖第三方）。

设计约束（来自项目规范）：
  * 每张图自带 viewBox / xmlns / width=100% / height=auto（style 覆盖）
  * 线条默认 stroke=currentColor：内联进页面时随主题变色，深/浅底色都能看
  * 不画不透明白底：填充只用 none / 剖面线 pattern / 半透明
  * 线宽按国标：粗实线 2、细实线 0.8；虚线 6 4；点画线 18 4 3 4；双点画线 20 4 3 4 3 4
  * 文字 11–13px，system-ui —— 中文走系统字体栈

计数口径：n_shape = 图形元素（line/rect/circle/path/polyline/polygon），
          n_text  = <text> 个数。校验脚本会分别打印。
"""
from __future__ import annotations

import math
import re
import unicodedata
from xml.sax.saxutils import escape

INK = "currentColor"

# 与 apps/web/src/app.css 的主题色一致（孔=蓝、轴=橙、间隙=绿、过盈=红、过渡=琥珀）
PALETTE = {
    "blue": "#2563eb",
    "red": "#dc2626",
    "green": "#16a34a",
    "orange": "#ea580c",
    "amber": "#b45309",
    "violet": "#7c3aed",
    "teal": "#0f766e",
    "muted": "#6b7280",
}

# 线型类（国标 GB/T 17450 / GB/T 4457.4）
STROKE = {
    "thick": 'stroke-width="2"',
    "thin": 'stroke-width="0.8"',
    "dash": 'stroke-width="0.8" stroke-dasharray="6 4"',
    "center": 'stroke-width="0.8" stroke-dasharray="18 4 3 4"',
    "dbl": 'stroke-width="0.8" stroke-dasharray="20 4 3 4 3 4"',
    "cut": 'stroke-width="3"',  # 剖切位置线：粗短画
    "axis": 'stroke-width="1.4"',  # 零线 / 基准线：比细线略重，但不是粗实线
    "wave": 'stroke-width="0.8"',
}

FONT = 'font-family="system-ui, sans-serif"'

# 箭头 marker：颜色写死，避免 currentColor 在 <marker> 里解析到 defs 而丢色
_ARROWS = {
    "ink": INK,
    "blue": PALETTE["blue"],
    "red": PALETTE["red"],
    "green": PALETTE["green"],
    "orange": PALETTE["orange"],
    "amber": PALETTE["amber"],
    "violet": PALETTE["violet"],
    "teal": PALETTE["teal"],
}
_COLOR_TO_ARROW = {v: k for k, v in _ARROWS.items()}
_COLOR_TO_ARROW[INK] = "ink"

#: 45° / 135° 剖面线（细实线，间距 6）、间距 4 的加密版
HATCH_DEFS = """
  <pattern id="hatch45" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
    <line x1="0" y1="0" x2="0" y2="6" stroke="currentColor" stroke-width="0.8"/>
  </pattern>
  <pattern id="hatch135" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(-45)">
    <line x1="0" y1="0" x2="0" y2="6" stroke="currentColor" stroke-width="0.8"/>
  </pattern>
  <pattern id="hatch45d" width="4" height="4" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
    <line x1="0" y1="0" x2="0" y2="4" stroke="currentColor" stroke-width="0.8"/>
  </pattern>
  <pattern id="hatch_solid" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
    <line x1="0" y1="0" x2="0" y2="6" stroke="#1f2937" stroke-width="0.8"/>
  </pattern>
  <pattern id="hatch_blue" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
    <rect width="6" height="6" fill="#2563eb" fill-opacity="0.10"/>
    <line x1="0" y1="0" x2="0" y2="6" stroke="#2563eb" stroke-width="1"/>
  </pattern>
  <pattern id="hatch_orange" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(-45)">
    <rect width="6" height="6" fill="#ea580c" fill-opacity="0.10"/>
    <line x1="0" y1="0" x2="0" y2="6" stroke="#ea580c" stroke-width="1"/>
  </pattern>
"""


def _arrow_defs(prefix: str = "") -> str:
    out = []
    for name, color in _ARROWS.items():
        out.append(
            f'  <marker id="{prefix}ar-{name}" viewBox="0 0 8 8" refX="7.2" refY="4" markerUnits="userSpaceOnUse" '
            f'markerWidth="8" markerHeight="8" orient="auto-start-reverse">'
            f'<path d="M0.6,0.9 L7.2,4 L0.6,7.1 Z" fill="{color}"/></marker>'
        )
    return "\n".join(out)


def f(v: float) -> str:
    """紧凑数字：去掉无意义的 .0，最多两位小数。"""
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def arc_pts(cx: float, cy: float, r: float, a0: float, a1: float, n: int = 48):
    """角度制取样圆弧点。0°=+x，角度增大 = 屏幕顺时针（y 轴向下）。

    a1 < a0 时反向走，适合"绕过左侧"的大弧。
    """
    pts = []
    for i in range(n + 1):
        a = math.radians(a0 + (a1 - a0) * i / n)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def wave_pts(x1: float, x2: float, yfun, amp: float = 3.0, period: float = 13.0, step: float = 2.0):
    """沿 x 取样的波浪线点集（手画断裂边界线用）。yfun(x) 给基准 y。

    幅度与相位都做轻微漂移 —— 国标要求波浪线是“徒手断裂线”，不能画成规则正弦曲线。
    """
    n = max(8, int(abs(x2 - x1) / step))
    pts = []
    for i in range(n + 1):
        x = x1 + (x2 - x1) * i / n
        k = (x - x1) / period
        a = amp * (0.55 + 0.45 * abs(math.sin(k * 0.83 + 1.1)))
        ph = 2 * math.pi * k + 0.5 * math.sin(k * 0.61)
        pts.append((x, yfun(x) + a * math.sin(ph)))
    return pts


def d_of_pts(pts, close: bool = False) -> str:
    if not pts:
        return ""
    d = f"M{f(pts[0][0])},{f(pts[0][1])}"
    d += "".join(f" L{f(x)},{f(y)}" for x, y in pts[1:])
    return d + (" Z" if close else "")


class Figure:
    """一张图的构建器。

    绘制时顺手记录内容包围盒，输出时把 viewBox 收紧到「真实内容 + 边距」——
    否则图四周大片空白会让前端按容器宽度缩放后字变得很小。
    """

    #: 各线型的名义线宽，用于包围盒外扩
    SW = {"thick": 2.0, "thin": 0.8, "dash": 0.8, "center": 0.8, "dbl": 0.8, "cut": 3.0,
          "axis": 1.4, "wave": 0.8}

    def __init__(self, fid: str, w: int, h: int, title: str, desc: str = ""):
        self.fid = fid
        self.w = w
        self.h = h
        self.title = title
        self.desc = desc or title
        self.body: list[str] = []
        self.n_shape = 0
        self.n_text = 0
        self._boxes: list[tuple[float, float, float, float]] = []

    # ---------------------------------------------------------------- 包围盒
    def _bb(self, x0, y0, x1, y1) -> None:
        self._boxes.append((min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)))

    def _bb_pts(self, pts, pad=0.6) -> None:
        if not pts:
            return
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        self._bb(min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad)

    def _bb_d(self, d: str, pad=0.6) -> None:
        nums = [float(t) for t in re.findall(r"-?\d+(?:\.\d+)?", d)]
        if len(nums) < 2:
            return
        xs, ys = nums[0::2], nums[1::2]
        self._bb(min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad)

    @staticmethod
    def _text_w(s: str, size: float) -> float:
        """粗估文字宽度：全角按 1.0em，半角按 0.55em。"""
        w = 0.0
        for ch in str(s):
            w += size * (1.0 if unicodedata.east_asian_width(ch) in ("W", "F") else 0.55)
        return w

    def bbox(self, pad: float = 18.0) -> tuple[int, int]:
        if not self._boxes:
            return self.w, self.h
        x0 = min(b[0] for b in self._boxes)
        y0 = min(b[1] for b in self._boxes)
        x1 = max(b[2] for b in self._boxes)
        y1 = max(b[3] for b in self._boxes)
        # 内容若从 (0,0) 之外开始，整体平移会改坐标；这里只收紧右/下边，左边保持 0 以留白
        w = max(360.0, x1 + pad)
        h = max(240.0, y1 + pad)
        return int(math.ceil(w)), int(math.ceil(h))

    # ---------------------------------------------------------------- 图元
    def _shape(self, s: str) -> None:
        self.body.append(s)
        self.n_shape += 1

    def raw(self, s: str) -> None:
        self.body.append(s)

    def line(self, x1, y1, x2, y2, cls="thin", color=None, extra="") -> None:
        c = color or INK
        sw = self.SW.get(cls, 0.8)
        self._bb(x1 - sw, y1 - sw, x2 + sw, y2 + sw)
        self._shape(
            f'<line x1="{f(x1)}" y1="{f(y1)}" x2="{f(x2)}" y2="{f(y2)}" '
            f'stroke="{c}" {STROKE[cls]}{(" " + extra) if extra else ""}/>'
        )

    def line_arrow(self, x1, y1, x2, y2, color=None, cls="thin", both=True, extra="") -> None:
        c = color or INK
        self._bb(x1 - 9, y1 - 9, x2 + 9, y2 + 9)  # 箭头 marker 会伸出端点数 px
        m = _COLOR_TO_ARROW.get(c, "ink")
        mk = f'marker-start="url(#ar-{m})" marker-end="url(#ar-{m})"' if both else f'marker-end="url(#ar-{m})"'
        self._shape(
            f'<line x1="{f(x1)}" y1="{f(y1)}" x2="{f(x2)}" y2="{f(y2)}" '
            f'stroke="{c}" {STROKE[cls]} {mk}{(" " + extra) if extra else ""}/>'
        )

    def path(self, d, cls=None, fill=None, color=None, extra="", shape=True) -> None:
        if not d:
            return
        self._bb_d(d, pad=self.SW.get(cls, 0.8) if cls else 0.4)
        c = color or INK
        stroke = f'stroke="{c}" {STROKE[cls]}' if cls else 'stroke="none"'
        fl = f'fill="{fill}"' if fill else ('fill="none"' if cls else 'fill="none"')
        s = f'<path d="{d}" {stroke} {fl}{(" " + extra) if extra else ""}/>'
        if shape:
            self._shape(s)
        else:
            self.body.append(s)

    def polyline(self, pts, cls="thin", close=False, fill=None, color=None, extra="") -> None:
        self.path(d_of_pts(pts, close), cls=cls, fill=fill, color=color, extra=extra)

    def rect(self, x, y, w, h, cls="thick", fill=None, color=None, rx=0, extra="") -> None:
        c = color or INK
        self._bb(x, y, x + w, y + h)
        stroke = f'stroke="{c}" {STROKE[cls]}' if cls else 'stroke="none"'
        fl = f'fill="{fill}"' if fill else 'fill="none"'
        rxs = f' rx="{f(rx)}"' if rx else ""
        self._shape(
            f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}"{rxs} {stroke} {fl}'
            f'{(" " + extra) if extra else ""}/>'
        )

    def circle(self, cx, cy, r, cls="thin", fill=None, color=None, extra="") -> None:
        c = color or INK
        self._bb(cx - r, cy - r, cx + r, cy + r)
        stroke = f'stroke="{c}" {STROKE[cls]}' if cls else 'stroke="none"'
        fl = f'fill="{fill}"' if fill else 'fill="none"'
        self._shape(
            f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(r)}" {stroke} {fl}'
            f'{(" " + extra) if extra else ""}/>'
        )

    def dot(self, cx, cy, r=2.4, color=None) -> None:
        self._bb(cx - r, cy - r, cx + r, cy + r)
        self._shape(f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(r)}" fill="{color or INK}" stroke="none"/>')

    def arc(self, cx, cy, r, a0, a1, cls="thin", color=None, n=48, extra="") -> None:
        self.polyline(arc_pts(cx, cy, r, a0, a1, n), cls=cls, color=color, extra=extra)

    def wave(self, x1, x2, yfun, amp=3.0, period=13.0, cls="wave", color=None, step=2.0):
        pts = wave_pts(x1, x2, yfun, amp, period, step)
        self.polyline(pts, cls=cls, color=color)

    def wave_pts(self, x1, x2, yfun, amp=3.0, period=13.0, step=2.0):
        return wave_pts(x1, x2, yfun, amp, period, step)

    def hatch(self, d, pat="hatch45") -> None:
        """剖面线填充区域（只填线，不遮底色）。"""
        self._bb_d(d)
        self._shape(f'<path d="{d}" fill="url(#{pat})" stroke="none"/>')

    def hatch_rect(self, x, y, w, h, pat="hatch45") -> None:
        self._bb(x, y, x + w, y + h)
        self._shape(
            f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" fill="url(#{pat})" stroke="none"/>'
        )

    # ---------------------------------------------------------------- 文字
    def text(self, x, y, s, size=12, anchor="middle", color=None, weight=None, italic=False, extra="") -> None:
        c = color or INK
        w = f' font-weight="{weight}"' if weight else ""
        i = ' font-style="italic"' if italic else ""
        tw = self._text_w(s, size)
        if anchor == "start":
            x0, x1 = x, x + tw
        elif anchor == "end":
            x0, x1 = x - tw, x
        else:
            x0, x1 = x - tw / 2, x + tw / 2
        self._bb(x0, y - size * 0.95, x1, y + size * 0.3)
        self.n_text += 1
        self.body.append(
            f'<text x="{f(x)}" y="{f(y)}" font-size="{size}" {FONT} text-anchor="{anchor}" '
            f'fill="{c}"{w}{i}{(" " + extra) if extra else ""}>{escape(str(s))}</text>'
        )

    def lines(self, x, y, rows, size=11, anchor="start", color=None, lh=17) -> None:
        for i, s in enumerate(rows):
            self.text(x, y + i * lh, s, size=size, anchor=anchor, color=color)

    # ---------------------------------------------------------------- 标注
    def dim_h(self, x1, x2, y, txt, ext_from=None, color=None, above=True, size=12, gap=5, cls="thin"):
        c = color or INK
        self.line_arrow(x1, y, x2, y, color=c, cls=cls)
        ty = y - gap if above else y + gap + size * 0.75
        self.text((x1 + x2) / 2, ty, txt, size=size, anchor="middle", color=c)
        if ext_from:
            for xx, y0 in ((x1, ext_from[0]), (x2, ext_from[1])):
                s = 1 if y > y0 else -1
                self.line(xx, y0 + s * 3, xx, y + s * 5, cls="thin", color=c)

    def dim_v(self, x, y1, y2, txt, ext_from=None, color=None, left=True, size=12, gap=5, cls="thin"):
        c = color or INK
        self.line_arrow(x, y1, x, y2, color=c, cls=cls)
        tx = x - gap if left else x + gap
        self.text(tx, (y1 + y2) / 2 + size * 0.35, txt, size=size, anchor="end" if left else "start", color=c)
        if ext_from:
            for yy, x0 in ((y1, ext_from[0]), (y2, ext_from[1])):
                s = 1 if x > x0 else -1
                self.line(x0 + s * 3, yy, x + s * 5, yy, cls="thin", color=c)

    def leader(self, x1, y1, x2, y2, txt=None, color=None, size=11, anchor="start", dot=False, gap=6):
        """引出线：从指向点 (x1,y1) 引到文字端 (x2,y2)。"""
        c = color or INK
        self.line_arrow(x1, y1, x2, y2, color=c, cls="thin", both=False)
        if dot:
            self.dot(x1, y1, 2.2, color=c)
        if txt:
            if anchor == "start":
                self.text(x2 + gap, y2 + 4, txt, size=size, anchor="start", color=c)
            elif anchor == "end":
                self.text(x2 - gap, y2 + 4, txt, size=size, anchor="end", color=c)
            else:
                self.text(x2, y2 - gap, txt, size=size, anchor="middle", color=c)

    def datum_tri(self, x, y, size=7, color=None) -> None:
        """基准/剖切符号用的实心小三角形（尖端朝上）。"""
        self.polyline(
            [(x, y - size), (x - size * 0.8, y), (x + size * 0.8, y)],
            cls=None,
            close=True,
            fill=color or INK,
        )

    def tick(self, x, y, l=6, cls="thick", color=None) -> None:
        self.line(x - l / 2, y, x + l / 2, y, cls=cls, color=color)

    # ---------------------------------------------------------------- 输出
    def svg(self) -> str:
        desc = escape(self.desc)
        title = escape(self.title)
        # 所有 defs 的 id 加图号前缀：同一页面上并排嵌多张图时不会互相抢 pattern / marker
        pfx = self.fid + "__"
        defs = HATCH_DEFS.replace('id="hatch', f'id="{pfx}hatch') + _arrow_defs(pfx)
        body = "\n    ".join(self.body).replace("url(#", f"url(#{pfx}")
        vb_w, vb_h = self.bbox()
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {vb_w} {vb_h}" '
            f'width="100%" height="100%" style="height:auto;display:block" '
            f'preserveAspectRatio="xMidYMid meet" role="img" '
            f'aria-labelledby="{self.fid}-t {self.fid}-d" class="fig-svg">\n'
            f'  <title id="{self.fid}-t">{title}</title>\n'
            f'  <desc id="{self.fid}-d">{desc}</desc>\n'
            f"  <defs>{defs}\n  </defs>\n"
            f'  <g stroke-linecap="round" stroke-linejoin="round">\n    ' + body + "\n  </g>\n</svg>\n"
        )


def panel_title(fig: Figure, x, y, s, color=None, anchor="middle", size=13) -> None:
    fig.text(x, y, s, size=size, weight="600", color=color, anchor=anchor)


def fig_title(fig: Figure, s, sub=None) -> None:
    fig.text(40, 32, s, size=13, anchor="start", weight="600")
    if sub:
        fig.text(40, 52, sub, size=11, anchor="start", color=PALETTE["muted"])
