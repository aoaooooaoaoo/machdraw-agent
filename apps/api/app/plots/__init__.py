"""SVG 曲线渲染包（纯 stdlib，自包含，无 JS 依赖）。

``from app.plots.svg import line_chart`` 渲染 plot 画布所需的曲线图。
"""
from .svg import FONT_FAMILY, PALETTE, empty_chart, line_chart

__all__ = ["line_chart", "empty_chart", "PALETTE", "FONT_FAMILY"]
