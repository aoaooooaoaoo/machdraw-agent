"""第二批教学图（FIG2-*）生成工具：复用第一批 kb/figures/_tools/svgkit.py，只做扩展不改它。

放在临时目录的原因：本批任务的写入范围只允许 kb\\figures\\FIG2-*.svg + figures.jsonl 追加
+ docs\\15-*.md，因此生成脚本不进仓库（需要留档时再经批准移入 _tools/）。
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent                     # kb/figures/_tools（svgkit.py 在这里）
FIG_DIR = TOOLS.parent                  # kb/figures
sys.path.insert(0, str(TOOLS))

import svgkit  # noqa: E402
from svgkit import INK, PALETTE, Figure, fig_title, panel_title  # noqa: E402

MUTED = PALETTE["muted"]
BLUE = PALETTE["blue"]
RED = PALETTE["red"]
GREEN = PALETTE["green"]
ORANGE = PALETTE["orange"]
AMBER = PALETTE["amber"]
VIOLET = PALETTE["violet"]
TEAL = PALETTE["teal"]


class Fig2(Figure):
    """在第一批 Figure 上加：椭圆、等轴测投影、表格线、编号圆标。"""

    # ---------------------------------------------------------------- 椭圆
    def ellipse(self, cx, cy, rx, ry, rot_deg=0.0, cls="thin", color=None, n=96, extra=""):
        """任意旋转椭圆（用折线采样，保证与第一批 viewBox 逻辑一致）。"""
        a = math.radians(rot_deg)
        ca, sa = math.cos(a), math.sin(a)
        pts = []
        for i in range(n):
            t = 2 * math.pi * i / n
            x, y = rx * math.cos(t), ry * math.sin(t)
            pts.append((cx + x * ca - y * sa, cy + x * sa + y * ca))
        self.polyline(pts, cls=cls, close=True, color=color, extra=extra)

    def ellipse_pts(self, cx, cy, rx, ry, rot_deg=0.0, n=64):
        a = math.radians(rot_deg)
        ca, sa = math.cos(a), math.sin(a)
        out = []
        for i in range(n):
            t = 2 * math.pi * i / n
            x, y = rx * math.cos(t), ry * math.sin(t)
            out.append((cx + x * ca - y * sa, cy + x * sa + y * ca))
        return out

    # ---------------------------------------------------------------- 轴测
    @staticmethod
    def iso(x, y, z, ox, oy, k=1.0, c=0.866):
        """正等测：(x,y,z)（mm）→ 屏幕坐标。c=0.866 为标准等测，c=1 为简化。"""
        return (ox + c * k * (y - x), oy + 0.5 * k * (x + y) - k * z)

    def iso_poly(self, pts, ox, oy, k=1.0, cls="thick", close=True, color=None, fill=None):
        self.polyline([self.iso(x, y, z, ox, oy, k) for x, y, z in pts], cls=cls, close=close, color=color, fill=fill)

    def iso_edges(self, edges, ox, oy, k=1.0, cls="thick", color=None):
        """把若干条 (p1,p2) 棱画成一条 path（省图元）。"""
        d = []
        for p1, p2 in edges:
            a = self.iso(*p1, ox, oy, k)
            b = self.iso(*p2, ox, oy, k)
            d.append(f"M{a[0]:.2f},{a[1]:.2f} L{b[0]:.2f},{b[1]:.2f}")
        self.path(" ".join(d), cls=cls, color=color)

    # ---------------------------------------------------------------- 杂项
    def badge(self, x, y, s, r=9, color=None, size=11):
        """带圈数字/字母标号（①②③ 或 O1）。"""
        c = color or INK
        self.circle(x, y, r, cls="thin", color=c)
        self.text(x, y + 4, s, size=size, anchor="middle", color=c)

    def hline(self, x1, x2, y, cls="thin", color=None):
        self.line(x1, y, x2, y, cls=cls, color=color)

    def table(self, x, y, cols, rows, row_h=24, size=11, head=True, col_w=None):
        """极简表格：cols=表头列名，rows=二维列表。只画横线与列分隔不需要。"""
        n = len(cols)
        col_w = col_w or [110] * n
        xs, acc = [], x
        for w in col_w:
            xs.append(acc)
            acc += w
        total = acc - x
        self.hline(x, x + total, y)
        for i, name in enumerate(cols):
            self.text(xs[i] + 6, y - 6, name, size=size, anchor="start", weight="600")
        self.hline(x, x + total, y + 4)
        yy = y + 4
        for r, row in enumerate(rows):
            yy += row_h
            for i, cell in enumerate(row):
                self.text(xs[i] + 6, yy - 6, str(cell), size=size, anchor="start")
        self.hline(x, x + total, yy)
        return yy


def notes(F: Figure, x, y, items, size=11, lh=22, color=None):
    F.lines(x, y, items, size=size, lh=lh, color=color)
