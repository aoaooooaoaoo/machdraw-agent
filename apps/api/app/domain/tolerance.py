"""极限与配合计算引擎（GB/T 1800.1-2020 / GB/T 1800.2-2020）。

本模块把《极限与配合》标准中的公差表与基本偏差数据固化为纯 Python 数据 + 公式，
对外提供 4 个纯函数：

    it_tolerance(phi, grade)                          基本尺寸 phi 的 IT{grade} 公差（mm）
    fundamental_deviation(phi, letter, is_hole, grade) 基本偏差（mm，带符号）
    parse_fit(spec)                                   解析配合代号字符串
    solve_fit(phi, hole_code, shaft_code)             完整求解极限偏差 / 极限尺寸 / 配合性质

设计原则（与项目"零幻觉"原则一致）：
* 不依赖网络、不依赖大模型、不依赖第三方库（只用 ``math`` / ``typing``）。
* 标准公差值按 GB/T 1800.1-2020 表 1 的尺寸分段逐档内嵌，保证与标准表逐值一致；
  同时给出标准公差因子公式 ``i = 0.45·D^(1/3) + 0.001·D``（µm）用于教学解释与自检
  （D 为尺寸分段的几何平均值；IT5=7i、IT6=10i、IT7=16i、IT8=25i、IT9=40i、
  IT10=64i、IT11=100i）。个别档位标准表取整后与公式略有出入，以标准表为准。
* 基本偏差按"表格 + Δ 修正"实现：
    - 轴 d/e/f/g/h：直接取标准表 es；
    - 轴 js：es=+IT/2、ei=-IT/2；
    - 轴 j：查表（ei），仅 IT5~IT8 为标准公差带；
    - 轴 k：ei=+0.6·D^(1/3)（IT5~IT7），IT8 及以上 ei=0，≤3 mm 时 ei=0；
    - 轴 m：ei=IT7-IT6（≤3 mm 取标准表特殊值 2 µm）；
    - 轴 n：ei=+5·D^0.34（µm，主尺寸段表值）；
    - 轴 p/r/s：取标准表 ei（p 按主尺寸段；r/s 按中间尺寸段细分）；
    - 孔 H：EI=0；孔 JS：ES=+IT/2、EI=-IT/2；孔 J：查表 ES；
    - 孔 K/M/N：ES = -ei(同名轴) + Δ（等级 ≤IT8），等级 >IT8 时按标准表规则；
    - 孔 P/R/S：ES = -ei(同名轴) + Δ（等级 ≤IT7），等级 >IT7 时 ES = -ei。
  其中 Δ = IT_n - IT_(n-1)，按 GB/T 1800.2-2020 表 3 逐尺寸段取表值。
* 无法计算的非标准组合一律抛 ``ValueError``（中文原因），绝不静默返回错误数值。

尺寸分段约定：上限包含、下限不包含（ISO 语义 "over a, up to and including b"），
因此基本尺寸 30 属于 (18, 30] 段、50 属于 (30, 50] 段，与教材例题一致。

已知限制（详见 docs/08-确定性引擎说明.md）：
* 仅覆盖基本尺寸 (0, 500] mm、公差等级 IT5~IT11；
* 仅覆盖常用基本偏差：轴 d/e/f/g/h/js/j/k/m/n/p/r/s，孔 H/JS/J/K/M/N/P/R/S；
* 孔 J 仅 IT6~IT8、轴 j 仅 IT5~IT7（j8 仅 ≤3 mm）为标准公差带，
  孔 K 仅 ≤IT8，其余组合抛 ValueError。
"""
from __future__ import annotations

import math
import re
import unicodedata
from typing import Final

__all__ = [
    "it_tolerance",
    "fundamental_deviation",
    "solve_fit",
    "parse_fit",
    "IT_GRADES",
    "SIZE_RANGES",
    "SUPPORTED_SHAFT_LETTERS",
    "SUPPORTED_HOLE_LETTERS",
]

# ---------------------------------------------------------------------------
# 常量：标准公差（GB/T 1800.1-2020 表 1，单位 µm）
# ---------------------------------------------------------------------------

IT_GRADES: Final[tuple[int, ...]] = (5, 6, 7, 8, 9, 10, 11)

#: 主尺寸段（用于 IT 公差与 k/m/n/p 等主段基本偏差）
SIZE_RANGES: Final[tuple[tuple[float, float], ...]] = (
    (0.0, 3.0),
    (3.0, 6.0),
    (6.0, 10.0),
    (10.0, 18.0),
    (18.0, 30.0),
    (30.0, 50.0),
    (50.0, 80.0),
    (80.0, 120.0),
    (120.0, 180.0),
    (180.0, 250.0),
    (250.0, 315.0),
    (315.0, 400.0),
    (400.0, 500.0),
)

#: 中间尺寸段（GB/T 1800.2 基本偏差表使用；用于 d/e/f/g/r/s 与 Δ 修正）
FD_RANGES: Final[tuple[tuple[float, float], ...]] = (
    (0.0, 3.0),
    (3.0, 6.0),
    (6.0, 10.0),
    (10.0, 14.0),
    (14.0, 18.0),
    (18.0, 24.0),
    (24.0, 30.0),
    (30.0, 40.0),
    (40.0, 50.0),
    (50.0, 65.0),
    (65.0, 80.0),
    (80.0, 100.0),
    (100.0, 120.0),
    (120.0, 140.0),
    (140.0, 160.0),
    (160.0, 180.0),
    (180.0, 200.0),
    (200.0, 225.0),
    (225.0, 250.0),
    (250.0, 280.0),
    (280.0, 315.0),
    (315.0, 355.0),
    (355.0, 400.0),
    (400.0, 450.0),
    (450.0, 500.0),
)

#: IT5~IT11 公差值（µm），键为主尺寸段
_IT_TABLE: Final[dict[tuple[float, float], tuple[float, ...]]] = {
    (0.0, 3.0): (4, 6, 10, 14, 25, 40, 60),
    (3.0, 6.0): (5, 8, 12, 18, 30, 48, 75),
    (6.0, 10.0): (6, 9, 15, 22, 36, 58, 90),
    (10.0, 18.0): (8, 11, 18, 27, 43, 70, 110),
    (18.0, 30.0): (9, 13, 21, 33, 52, 84, 130),
    (30.0, 50.0): (11, 16, 25, 39, 62, 100, 160),
    (50.0, 80.0): (13, 19, 30, 46, 74, 120, 190),
    (80.0, 120.0): (15, 22, 35, 54, 87, 140, 220),
    (120.0, 180.0): (18, 25, 40, 63, 100, 160, 250),
    (180.0, 250.0): (20, 29, 46, 72, 115, 185, 290),
    (250.0, 315.0): (23, 32, 52, 81, 130, 210, 320),
    (315.0, 400.0): (25, 36, 57, 89, 140, 230, 360),
    (400.0, 500.0): (27, 40, 63, 97, 155, 250, 400),
}

#: 轴基本偏差 es（µm，负值），按中间尺寸段；d/e/f/g 为"上偏差"
_SHAFT_ES: Final[dict[str, dict[tuple[float, float], float]]] = {
    "d": {
        (0.0, 3.0): -20, (3.0, 6.0): -30, (6.0, 10.0): -40,
        (10.0, 14.0): -50, (14.0, 18.0): -50, (18.0, 24.0): -65,
        (24.0, 30.0): -65, (30.0, 40.0): -80, (40.0, 50.0): -80,
        (50.0, 65.0): -100, (65.0, 80.0): -100, (80.0, 100.0): -120,
        (100.0, 120.0): -120, (120.0, 140.0): -145, (140.0, 160.0): -145,
        (160.0, 180.0): -145, (180.0, 200.0): -170, (200.0, 225.0): -170,
        (225.0, 250.0): -170, (250.0, 280.0): -190, (280.0, 315.0): -190,
        (315.0, 355.0): -210, (355.0, 400.0): -210, (400.0, 450.0): -230,
        (450.0, 500.0): -230,
    },
    "e": {
        (0.0, 3.0): -14, (3.0, 6.0): -20, (6.0, 10.0): -25,
        (10.0, 14.0): -32, (14.0, 18.0): -32, (18.0, 24.0): -40,
        (24.0, 30.0): -40, (30.0, 40.0): -50, (40.0, 50.0): -50,
        (50.0, 65.0): -60, (65.0, 80.0): -60, (80.0, 100.0): -72,
        (100.0, 120.0): -72, (120.0, 140.0): -85, (140.0, 160.0): -85,
        (160.0, 180.0): -85, (180.0, 200.0): -100, (200.0, 225.0): -100,
        (225.0, 250.0): -100, (250.0, 280.0): -110, (280.0, 315.0): -110,
        (315.0, 355.0): -125, (355.0, 400.0): -125, (400.0, 450.0): -135,
        (450.0, 500.0): -135,
    },
    "f": {
        (0.0, 3.0): -6, (3.0, 6.0): -10, (6.0, 10.0): -13,
        (10.0, 14.0): -16, (14.0, 18.0): -16, (18.0, 24.0): -20,
        (24.0, 30.0): -20, (30.0, 40.0): -25, (40.0, 50.0): -25,
        (50.0, 65.0): -30, (65.0, 80.0): -30, (80.0, 100.0): -36,
        (100.0, 120.0): -36, (120.0, 140.0): -43, (140.0, 160.0): -43,
        (160.0, 180.0): -43, (180.0, 200.0): -50, (200.0, 225.0): -50,
        (225.0, 250.0): -50, (250.0, 280.0): -56, (280.0, 315.0): -56,
        (315.0, 355.0): -62, (355.0, 400.0): -62, (400.0, 450.0): -68,
        (450.0, 500.0): -68,
    },
    "g": {
        (0.0, 3.0): -2, (3.0, 6.0): -4, (6.0, 10.0): -5,
        (10.0, 14.0): -6, (14.0, 18.0): -6, (18.0, 24.0): -7,
        (24.0, 30.0): -7, (30.0, 40.0): -9, (40.0, 50.0): -9,
        (50.0, 65.0): -10, (65.0, 80.0): -10, (80.0, 100.0): -12,
        (100.0, 120.0): -12, (120.0, 140.0): -14, (140.0, 160.0): -14,
        (160.0, 180.0): -14, (180.0, 200.0): -15, (200.0, 225.0): -15,
        (225.0, 250.0): -15, (250.0, 280.0): -17, (280.0, 315.0): -17,
        (315.0, 355.0): -18, (355.0, 400.0): -18, (400.0, 450.0): -20,
        (450.0, 500.0): -20,
    },
}

#: 轴基本偏差 ei（µm，正值），按中间尺寸段：r、s
_SHAFT_EI: Final[dict[str, dict[tuple[float, float], float]]] = {
    "r": {
        (0.0, 3.0): 10, (3.0, 6.0): 15, (6.0, 10.0): 19,
        (10.0, 14.0): 23, (14.0, 18.0): 23, (18.0, 24.0): 28,
        (24.0, 30.0): 28, (30.0, 40.0): 34, (40.0, 50.0): 34,
        (50.0, 65.0): 41, (65.0, 80.0): 43, (80.0, 100.0): 51,
        (100.0, 120.0): 54, (120.0, 140.0): 63, (140.0, 160.0): 65,
        (160.0, 180.0): 68, (180.0, 200.0): 77, (200.0, 225.0): 80,
        (225.0, 250.0): 84, (250.0, 280.0): 94, (280.0, 315.0): 98,
        (315.0, 355.0): 108, (355.0, 400.0): 114, (400.0, 450.0): 126,
        (450.0, 500.0): 132,
    },
    "s": {
        (0.0, 3.0): 14, (3.0, 6.0): 19, (6.0, 10.0): 23,
        (10.0, 14.0): 28, (14.0, 18.0): 28, (18.0, 24.0): 35,
        (24.0, 30.0): 35, (30.0, 40.0): 43, (40.0, 50.0): 43,
        (50.0, 65.0): 53, (65.0, 80.0): 59, (80.0, 100.0): 71,
        (100.0, 120.0): 79, (120.0, 140.0): 92, (140.0, 160.0): 100,
        (160.0, 180.0): 108, (180.0, 200.0): 122, (200.0, 225.0): 130,
        (225.0, 250.0): 140, (250.0, 280.0): 158, (280.0, 315.0): 170,
        (315.0, 355.0): 190, (355.0, 400.0): 208, (400.0, 450.0): 232,
        (450.0, 500.0): 252,
    },
}

#: 轴基本偏差 ei（µm），按主尺寸段：k / m / n / p
#: k：IT5~IT7 用表值（0.6·D^(1/3) 取整）；k 在 IT8 及以上、≤3 mm 时 ei=0。
_SHAFT_K: Final[dict[tuple[float, float], float]] = {
    (0.0, 3.0): 0, (3.0, 6.0): 1, (6.0, 10.0): 1, (10.0, 18.0): 1,
    (18.0, 30.0): 2, (30.0, 50.0): 2, (50.0, 80.0): 2, (80.0, 120.0): 3,
    (120.0, 180.0): 3, (180.0, 250.0): 4, (250.0, 315.0): 4,
    (315.0, 400.0): 4, (400.0, 500.0): 5,
}
_SHAFT_M: Final[dict[tuple[float, float], float]] = {
    (0.0, 3.0): 2, (3.0, 6.0): 4, (6.0, 10.0): 6, (10.0, 18.0): 7,
    (18.0, 30.0): 8, (30.0, 50.0): 9, (50.0, 80.0): 11, (80.0, 120.0): 13,
    (120.0, 180.0): 15, (180.0, 250.0): 17, (250.0, 315.0): 20,
    (315.0, 400.0): 21, (400.0, 500.0): 23,
}
_SHAFT_N: Final[dict[tuple[float, float], float]] = {
    (0.0, 3.0): 4, (3.0, 6.0): 8, (6.0, 10.0): 10, (10.0, 18.0): 12,
    (18.0, 30.0): 15, (30.0, 50.0): 17, (50.0, 80.0): 20, (80.0, 120.0): 23,
    (120.0, 180.0): 27, (180.0, 250.0): 31, (250.0, 315.0): 34,
    (315.0, 400.0): 37, (400.0, 500.0): 40,
}
_SHAFT_P: Final[dict[tuple[float, float], float]] = {
    (0.0, 3.0): 6, (3.0, 6.0): 12, (6.0, 10.0): 15, (10.0, 18.0): 18,
    (18.0, 30.0): 22, (30.0, 50.0): 26, (50.0, 80.0): 32, (80.0, 120.0): 37,
    (120.0, 180.0): 43, (180.0, 250.0): 50, (250.0, 315.0): 56,
    (315.0, 400.0): 62, (400.0, 500.0): 68,
}

#: 轴 j 的下偏差 ei（µm），按主尺寸段；仅 IT5/IT6、IT7、IT8 三档
_SHAFT_J56: Final[dict[tuple[float, float], float]] = {
    (0.0, 3.0): -2, (3.0, 6.0): -2, (6.0, 10.0): -2, (10.0, 18.0): -3,
    (18.0, 30.0): -4, (30.0, 50.0): -5, (50.0, 80.0): -7, (80.0, 120.0): -9,
    (120.0, 180.0): -11, (180.0, 250.0): -13, (250.0, 315.0): -16,
    (315.0, 400.0): -18, (400.0, 500.0): -20,
}
_SHAFT_J7: Final[dict[tuple[float, float], float]] = {
    (0.0, 3.0): -4, (3.0, 6.0): -4, (6.0, 10.0): -5, (10.0, 18.0): -6,
    (18.0, 30.0): -8, (30.0, 50.0): -10, (50.0, 80.0): -12, (80.0, 120.0): -15,
    (120.0, 180.0): -18, (180.0, 250.0): -20, (250.0, 315.0): -26,
    (315.0, 400.0): -28, (400.0, 500.0): -32,
}

#: 孔 J 的上偏差 ES（µm），按主尺寸段；仅 IT6、IT7、IT8
_HOLE_J: Final[dict[tuple[float, float], tuple[float, float, float]]] = {
    (0.0, 3.0): (2, 4, 6),
    (3.0, 6.0): (5, 6, 10),
    (6.0, 10.0): (5, 8, 12),
    (10.0, 18.0): (6, 10, 15),
    (18.0, 30.0): (8, 12, 20),
    (30.0, 50.0): (10, 14, 24),
    (50.0, 80.0): (13, 18, 28),
    (80.0, 120.0): (16, 22, 34),
    (120.0, 180.0): (18, 26, 41),
    (180.0, 250.0): (22, 30, 47),
    (250.0, 315.0): (25, 36, 55),
    (315.0, 400.0): (29, 39, 60),
    (400.0, 500.0): (33, 43, 66),
}

#: Δ = ITn - IT(n-1)（µm），按中间尺寸段，依次对应 IT3~IT8
_DELTA: Final[dict[tuple[float, float], tuple[float, ...]]] = {
    (0.0, 3.0): (0, 0, 0, 0, 0, 0),
    (3.0, 6.0): (1, 1.5, 1, 3, 4, 6),
    (6.0, 10.0): (1, 1.5, 2, 3, 6, 7),
    (10.0, 14.0): (1, 2, 3, 3, 7, 9),
    (14.0, 18.0): (1, 2, 3, 3, 7, 9),
    (18.0, 24.0): (1.5, 2, 3, 4, 8, 12),
    (24.0, 30.0): (1.5, 2, 3, 4, 8, 12),
    (30.0, 40.0): (1.5, 3, 4, 5, 9, 14),
    (40.0, 50.0): (1.5, 3, 4, 5, 9, 14),
    (50.0, 65.0): (2, 3, 5, 6, 11, 16),
    (65.0, 80.0): (2, 3, 5, 6, 11, 16),
    (80.0, 100.0): (2, 4, 5, 7, 13, 19),
    (100.0, 120.0): (2, 4, 5, 7, 13, 19),
    (120.0, 140.0): (3, 4, 6, 7, 15, 23),
    (140.0, 160.0): (3, 4, 6, 7, 15, 23),
    (160.0, 180.0): (3, 4, 6, 7, 15, 23),
    (180.0, 200.0): (3, 4, 6, 9, 17, 26),
    (200.0, 225.0): (3, 4, 6, 9, 17, 26),
    (225.0, 250.0): (3, 4, 6, 9, 17, 26),
    (250.0, 280.0): (4, 4, 7, 9, 20, 29),
    (280.0, 315.0): (4, 4, 7, 9, 20, 29),
    (315.0, 355.0): (4, 5, 7, 11, 21, 32),
    (355.0, 400.0): (4, 5, 7, 11, 21, 32),
    (400.0, 450.0): (5, 5, 7, 13, 23, 34),
    (450.0, 500.0): (5, 5, 7, 13, 23, 34),
}

SUPPORTED_SHAFT_LETTERS: Final[tuple[str, ...]] = (
    "d", "e", "f", "g", "h", "js", "j", "k", "m", "n", "p", "r", "s",
)
SUPPORTED_HOLE_LETTERS: Final[tuple[str, ...]] = (
    "H", "JS", "J", "K", "M", "N", "P", "R", "S",
)


# ---------------------------------------------------------------------------
# 内部工具
# ---------------------------------------------------------------------------


def _find_range(
    phi: float, ranges: tuple[tuple[float, float], ...]
) -> tuple[float, float]:
    """返回包含 phi 的尺寸段（上限包含、下限不包含）。"""
    for lo, hi in ranges:
        if lo < phi <= hi:
            return (lo, hi)
    raise ValueError(
        f"基本尺寸 {phi:g} mm 超出 GB/T 1800 常用尺寸范围 (0, 500] mm，"
        "本引擎不予计算（标准表仅覆盖至 500 mm）"
    )


def _check_phi(phi: float) -> float:
    try:
        value = float(phi)
    except (TypeError, ValueError) as exc:  # pragma: no cover - 防御式
        raise ValueError(f"基本尺寸必须是数值，收到 {phi!r}") from exc
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"基本尺寸必须为大于 0 的有限数值，收到 {phi!r}")
    if value > 500:
        raise ValueError(
            f"基本尺寸 {value:g} mm 超出本引擎覆盖范围 (0, 500] mm"
            "（GB/T 1800.1 表 1 本引擎仅内嵌至 500 mm 段）"
        )
    return value


def _check_grade(grade: int) -> int:
    try:
        g = int(grade)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"公差等级必须是整数，收到 {grade!r}") from exc
    if g not in IT_GRADES:
        raise ValueError(
            f"标准公差等级 IT{g} 不受支持：本引擎仅覆盖 IT5~IT11"
            "（更精密的 IT01~IT4 与更粗糙的 IT12~IT18 未内嵌）"
        )
    return g


def _it_um(phi: float, grade: int) -> float:
    key = _find_range(phi, SIZE_RANGES)
    return float(_IT_TABLE[key][grade - 5])


def _delta_um(phi: float, grade: int) -> float:
    """Δ = ITn - IT(n-1)（µm），GB/T 1800.2-2020 表 3。"""
    key = _find_range(phi, FD_RANGES)
    return float(_DELTA[key][grade - 3])


def _fundamental_shaft_um(phi: float, letter: str, grade: int) -> float:
    """轴的基本偏差（µm，带符号）。"""
    if letter in _SHAFT_ES:
        return float(_SHAFT_ES[letter][_find_range(phi, FD_RANGES)])
    if letter == "h":
        return 0.0
    if letter == "js":
        return _it_um(phi, grade) / 2.0
    if letter == "j":
        key = _find_range(phi, SIZE_RANGES)
        if grade in (5, 6):
            return float(_SHAFT_J56[key])
        if grade == 7:
            return float(_SHAFT_J7[key])
        if grade == 8:
            if phi > 3:
                raise ValueError(
                    "轴 j8 仅在基本尺寸 ≤3 mm 时为标准公差带；"
                    f"{phi:g} mm 的 j8 非标准组合，请改用 js8 或 h8"
                )
            return -6.0
        raise ValueError(
            f"轴 j{grade} 不是标准公差带：j 仅 IT5~IT7 为标准（≤3 mm 另有 j8），"
            "其他等级请改用 js"
        )
    if letter == "k":
        if grade >= 8:
            return 0.0
        return float(_SHAFT_K[_find_range(phi, SIZE_RANGES)])
    if letter == "m":
        return float(_SHAFT_M[_find_range(phi, SIZE_RANGES)])
    if letter == "n":
        return float(_SHAFT_N[_find_range(phi, SIZE_RANGES)])
    if letter == "p":
        return float(_SHAFT_P[_find_range(phi, SIZE_RANGES)])
    if letter in _SHAFT_EI:
        return float(_SHAFT_EI[letter][_find_range(phi, FD_RANGES)])
    raise ValueError(
        f"未知的轴基本偏差代号 {letter!r}；本引擎支持："
        + "、".join(SUPPORTED_SHAFT_LETTERS)
    )


def _fundamental_hole_um(phi: float, letter: str, grade: int) -> float:
    """孔的基本偏差（µm，带符号；H 为 EI=0，其余为 ES）。"""
    if letter == "H":
        return 0.0
    if letter == "JS":
        return _it_um(phi, grade) / 2.0
    if letter == "J":
        key = _find_range(phi, SIZE_RANGES)
        if grade not in (6, 7, 8):
            raise ValueError(
                f"孔 J{grade} 不是标准公差带：J 仅 IT6~IT8 为标准，"
                "其他等级请改用 JS"
            )
        return float(_HOLE_J[key][grade - 6])
    if letter in ("K", "M", "N"):
        base = {
            "K": _SHAFT_K[_find_range(phi, SIZE_RANGES)]
            if phi > 3
            else 0.0,
            "M": _SHAFT_M[_find_range(phi, SIZE_RANGES)],
            "N": _SHAFT_N[_find_range(phi, SIZE_RANGES)],
        }[letter]
        if grade <= 8:
            return -base + _delta_um(phi, grade)
        if letter == "K":
            raise ValueError(
                "孔 K9~K11 不是 500 mm 以内的标准公差带"
                "（GB/T 1800.2 仅规定 K4~K8），请改用 JS 或 M/N"
            )
        if letter == "N":
            # GB/T 1800.1 表 3：尺寸 >3~500 mm 时 N(>IT8) 的 ES 为 0
            return 0.0 if phi > 3 else -base
        return -base
    if letter in ("P", "R", "S"):
        base = {
            "P": _SHAFT_P[_find_range(phi, SIZE_RANGES)],
            "R": _SHAFT_EI["r"][_find_range(phi, FD_RANGES)],
            "S": _SHAFT_EI["s"][_find_range(phi, FD_RANGES)],
        }[letter]
        if grade <= 7:
            return -base + _delta_um(phi, grade)
        return -base
    raise ValueError(
        f"未知的孔基本偏差代号 {letter!r}；本引擎支持："
        + "、".join(SUPPORTED_HOLE_LETTERS)
    )


def _shaft_zone_um(phi: float, letter: str, grade: int) -> tuple[float, float]:
    """返回轴的 (es, ei)（µm）。"""
    it = _it_um(phi, grade)
    if letter in ("d", "e", "f", "g", "h"):
        es = _fundamental_shaft_um(phi, letter, grade)
        return es, es - it
    if letter == "js":
        return it / 2.0, -it / 2.0
    # j/k/m/n/p/r/s：基本偏差为下偏差 ei
    ei = _fundamental_shaft_um(phi, letter, grade)
    return ei + it, ei


def _hole_zone_um(phi: float, letter: str, grade: int) -> tuple[float, float]:
    """返回孔的 (ES, EI)（µm）。"""
    it = _it_um(phi, grade)
    if letter == "H":
        return it, 0.0
    if letter == "JS":
        return it / 2.0, -it / 2.0
    # J/K/M/N/P/R/S：基本偏差为上偏差 ES
    es = _fundamental_hole_um(phi, letter, grade)
    return es, es - it


def _mm(value_um: float) -> float:
    return round(value_um / 1000.0, 6)


def _split_code(code: str) -> tuple[str, int]:
    """把 'H7' / 'k6' / 'js6' 拆成 (letter, grade)。"""
    if not isinstance(code, str):
        raise ValueError(f"公差带代号必须是字符串，收到 {code!r}")
    text = code.strip().replace(" ", "")
    if not text:
        raise ValueError("公差带代号不能为空")
    i = 0
    while i < len(text) and text[i].isalpha():
        i += 1
    letter, digits = text[:i], text[i:]
    if not letter or not digits.isdigit():
        raise ValueError(f"无法解析公差带代号 {code!r}，正确格式如 H7、k6、js6")
    grade = int(digits)
    if len(digits) > 2:
        raise ValueError(f"公差等级位数异常：{code!r}")
    return letter, grade


# ---------------------------------------------------------------------------
# 公开 API
# ---------------------------------------------------------------------------


def it_tolerance(phi: float, grade: int) -> float:
    """基本尺寸 ``phi`` 的 IT{grade} 标准公差值（mm）。

    参数
    ----
    phi:   基本尺寸（mm），范围 (0, 500]
    grade: 标准公差等级，仅支持 5~11

    返回
    ----
    公差值（mm，正数）。例如 ``it_tolerance(30, 7) == 0.021``。

    依据
    ----
    GB/T 1800.1-2020 表 1；标准公差因子
    ``i = 0.45·D^(1/3) + 0.001·D``（µm），``ITn = 系数 × i``。
    """
    value = _check_phi(phi)
    g = _check_grade(grade)
    return _mm(_it_um(value, g))


def fundamental_deviation(phi: float, letter: str, is_hole: bool, grade: int) -> float:
    """基本偏差（mm，带符号）。

    参数
    ----
    phi:     基本尺寸（mm），范围 (0, 500]
    letter:  基本偏差代号。轴用小写（a~zc），孔用大写（A~ZC）；
             本引擎支持轴 d/e/f/g/h/js/j/k/m/n/p/r/s，孔 H/JS/J/K/M/N/P/R/S。
    is_hole: True 表示孔（取靠近零线的偏差：H 为 EI=0，其余为 ES）；
             False 表示轴（d~h 取 es，j~s 取 ei，js 取 es=+IT/2）。
    grade:   标准公差等级 5~11。

    返回
    ----
    基本偏差（mm）。孔 H 返回 0.0；轴 h 返回 0.0。

    说明
    ----
    基本偏差是"靠近零线"的那个极限偏差。对 js/JS 这类对称公差带，
    按行业惯例返回上偏差（+IT/2）。
    """
    value = _check_phi(phi)
    g = _check_grade(grade)
    if not isinstance(letter, str) or not letter.strip():
        raise ValueError(f"基本偏差代号必须是非空字符串，收到 {letter!r}")
    raw = letter.strip()
    if is_hole:
        # 孔：统一转大写后查表
        upper = raw.upper()
        if upper not in SUPPORTED_HOLE_LETTERS:
            raise ValueError(
                f"不支持的孔基本偏差代号 {letter!r}；本引擎支持："
                + "、".join(SUPPORTED_HOLE_LETTERS)
            )
        return _mm(_fundamental_hole_um(value, upper, g))
    lower = raw.lower()
    if lower not in SUPPORTED_SHAFT_LETTERS:
        raise ValueError(
            f"不支持的轴基本偏差代号 {letter!r}；本引擎支持："
            + "、".join(SUPPORTED_SHAFT_LETTERS)
        )
    return _mm(_fundamental_shaft_um(value, lower, g))


def parse_fit(spec: str) -> dict:
    """解析配合代号字符串。

    支持示例::

        "Φ30 H7/k6"  "Ø30H7/k6"  "30 H7 k6"  "Φ50H7"  "Φ30h6"
        "Φ20 H8/f7"  "φ45 js6"

    返回
    ----
    ``{"phi":30.0, "hole":"H7", "shaft":"k6", "hole_letter":"H",
       "hole_grade":7, "shaft_letter":"k", "shaft_grade":6}``

    只给出一个公差带时，另一侧为 ``None``。
    """
    if not isinstance(spec, str):
        raise ValueError(f"配合代号必须是字符串，收到 {spec!r}")
    text = unicodedata.normalize("NFKC", spec).strip()
    if not text:
        raise ValueError("配合代号不能为空")
    # 去掉直径符号、mm 单位与全角斜杠
    for symbol in ("Φ", "φ", "Ø", "ø", "⌀", "∅", "Mm", "MM", "mm"):
        text = text.replace(symbol, " ")
    text = text.replace("／", "/").replace("，", ",").replace(",", " ")

    code_re = re.compile(r"([A-Za-z]{1,2})\s*(\d{1,2})")
    codes = code_re.findall(text)
    if not codes:
        raise ValueError(
            f"未能从 {spec!r} 中解析出公差带代号（形如 H7、k6、js6）"
        )
    if len(codes) > 2:
        raise ValueError(f"{spec!r} 中公差带代号过多，一个配合最多包含孔、轴各一个代号")

    # 去掉公差带后代号，剩余数字即基本尺寸
    rest = code_re.sub(" ", text)
    num_re = re.compile(r"\d+(?:\.\d+)?")
    numbers = num_re.findall(rest)
    if not numbers:
        raise ValueError(f"未能从 {spec!r} 中解析出基本尺寸（如 30）")
    if len(numbers) > 1:
        raise ValueError(f"{spec!r} 中基本尺寸不唯一：{numbers}")
    phi = float(numbers[0])
    if phi <= 0 or phi > 500:
        raise ValueError(f"基本尺寸 {phi:g} mm 超出 (0, 500] mm 范围")

    hole_letter = hole_grade = None
    shaft_letter = shaft_grade = None
    for raw_letter, raw_grade in codes:
        grade = int(raw_grade)
        if raw_letter.isupper():
            if hole_letter is not None:
                raise ValueError(f"{spec!r} 中出现两个孔公差带，无法确定配合")
            hole_letter, hole_grade = raw_letter.upper(), grade
        elif raw_letter.islower():
            if shaft_letter is not None:
                raise ValueError(f"{spec!r} 中出现两个轴公差带，无法确定配合")
            shaft_letter, shaft_grade = raw_letter.lower(), grade
        else:  # pragma: no cover - isupper/islower 已覆盖全部字母
            raise ValueError(f"无法判断 {raw_letter!r} 是孔还是轴代号")

    hole = f"{hole_letter}{hole_grade}" if hole_letter is not None else None
    shaft = f"{shaft_letter}{shaft_grade}" if shaft_letter is not None else None
    return {
        "phi": phi,
        "hole": hole,
        "shaft": shaft,
        "hole_letter": hole_letter,
        "hole_grade": hole_grade,
        "shaft_letter": shaft_letter,
        "shaft_grade": shaft_grade,
    }


def solve_fit(phi: float, hole_code: str, shaft_code: str) -> dict:
    """求解一个配合：极限偏差、极限尺寸、配合性质、公差带与工艺提示。

    参数
    ----
    phi:        基本尺寸（mm）
    hole_code:  孔公差带代号（大写字母 + 等级，如 ``"H7"``）
    shaft_code: 轴公差带代号（小写字母 + 等级，如 ``"k6"``）

    返回
    ----
    字典（字段名固定，前端直接使用）::

        {"basic_size": 30.0,
         "system": "基孔制",
         "hole": {"code":"H7","IT":0.021,"ES":0.021,"EI":0.0,
                  "max":30.021,"min":30.0},
         "shaft": {"code":"k6","IT":0.013,"es":0.015,"ei":0.002,
                   "max":30.015,"min":30.002},
         "fit": {"type":"过渡配合","max_gap":0.019,"min_gap":-0.015,
                 "max_interference":0.015,"note":"..."},
         "tolerance_zone": {"hole":["EI","ES"], "shaft":["ei","es"]},
         "process_hint": "...",
         "refs": ["GB/T 1800.1-2020","GB/T 1800.2-2020"]}

    配合量约定（与教材一致）::

        最大间隙 Xmax = ES - ei
        最小间隙 Xmin = EI - es      （负值即过盈）
        最大过盈 Ymax = es - EI      （= -Xmin，无过盈可能时为 0）
    """
    value = _check_phi(phi)
    if not hole_code or not shaft_code:
        raise ValueError("solve_fit 需要同时给出孔、轴公差带代号（如 H7 / k6）")

    hole_letter, hole_grade = _split_code(hole_code)
    shaft_letter, shaft_grade = _split_code(shaft_code)
    if not hole_letter.isupper():
        raise ValueError(
            f"孔公差带代号必须使用大写字母（如 H7），收到 {hole_code!r}"
        )
    if not shaft_letter.islower():
        raise ValueError(
            f"轴公差带代号必须使用小写字母（如 k6），收到 {shaft_code!r}"
        )
    if hole_letter.upper() not in SUPPORTED_HOLE_LETTERS:
        raise ValueError(
            f"不支持的孔基本偏差代号 {hole_letter!r}；本引擎支持："
            + "、".join(SUPPORTED_HOLE_LETTERS)
        )
    if shaft_letter.lower() not in SUPPORTED_SHAFT_LETTERS:
        raise ValueError(
            f"不支持的轴基本偏差代号 {shaft_letter!r}；本引擎支持："
            + "、".join(SUPPORTED_SHAFT_LETTERS)
        )

    hg = _check_grade(hole_grade)
    sg = _check_grade(shaft_grade)

    ES_um, EI_um = _hole_zone_um(value, hole_letter.upper(), hg)
    es_um, ei_um = _shaft_zone_um(value, shaft_letter.lower(), sg)
    it_h_um = _it_um(value, hg)
    it_s_um = _it_um(value, sg)

    ES, EI = _mm(ES_um), _mm(EI_um)
    es, ei = _mm(es_um), _mm(ei_um)
    it_h, it_s = _mm(it_h_um), _mm(it_s_um)

    hole = {
        "code": f"{hole_letter.upper()}{hg}",
        "IT": it_h,
        "ES": ES,
        "EI": EI,
        "max": round(value + ES, 6),
        "min": round(value + EI, 6),
    }
    shaft = {
        "code": f"{shaft_letter.lower()}{sg}",
        "IT": it_s,
        "es": es,
        "ei": ei,
        "max": round(value + es, 6),
        "min": round(value + ei, 6),
    }

    max_gap = round((ES_um - ei_um) / 1000.0, 6)
    min_gap = round((EI_um - es_um) / 1000.0, 6)
    max_interference = round(max(0.0, -min_gap), 6)

    if max_gap > 0 and min_gap >= 0:
        fit_type = "间隙配合"
    elif max_gap <= 0:
        fit_type = "过盈配合"
    else:
        fit_type = "过渡配合"

    # 配合制判断：以孔为基准（H）→ 基孔制；以轴为基准（h）→ 基轴制
    if hole_letter.upper() == "H":
        system = "基孔制"
    elif shaft_letter.lower() == "h":
        system = "基轴制"
    else:
        system = "非基准制"

    note = _fit_note(fit_type, max_gap, min_gap, max_interference, hole["code"], shaft["code"])
    process_hint = _process_hint(fit_type, hole, shaft)

    return {
        "basic_size": value,
        "system": system,
        "hole": hole,
        "shaft": shaft,
        "fit": {
            "type": fit_type,
            "max_gap": max_gap,
            "min_gap": min_gap,
            "max_interference": max_interference,
            "note": note,
        },
        "tolerance_zone": {"hole": ["EI", "ES"], "shaft": ["ei", "es"]},
        "process_hint": process_hint,
        "refs": ["GB/T 1800.1-2020", "GB/T 1800.2-2020"],
    }


# ---------------------------------------------------------------------------
# 文案生成（确定性，不含随机/网络）
# ---------------------------------------------------------------------------


def _fmt(value: float) -> str:
    text = f"{value:+.6f}".rstrip("0").rstrip(".")
    return "0" if text in ("+0", "-0") else text


def _fit_note(
    fit_type: str,
    max_gap: float,
    min_gap: float,
    max_interference: float,
    hole_code: str,
    shaft_code: str,
) -> str:
    if fit_type == "间隙配合":
        return (
            f"{hole_code}/{shaft_code} 为间隙配合：孔的最小极限尺寸不小于轴的最大极限尺寸，"
            f"最大间隙 Xmax = ES − ei = {_fmt(max_gap)} mm，"
            f"最小间隙 Xmin = EI − es = {_fmt(min_gap)} mm。"
        )
    if fit_type == "过盈配合":
        return (
            f"{hole_code}/{shaft_code} 为过盈配合：孔的最大极限尺寸不大于轴的最小极限尺寸，"
            f"最大过盈 Ymax = es − EI = {_fmt(max_interference)} mm，"
            f"最小过盈 Ymin = ei − ES = {_fmt(-max_gap)} mm。"
        )
    return (
        f"{hole_code}/{shaft_code} 为过渡配合：孔、轴公差带相互交叠，可能得到间隙也可能得到过盈；"
        f"最大间隙 Xmax = ES − ei = {_fmt(max_gap)} mm，"
        f"最大过盈 Ymax = es − EI = {_fmt(max_interference)} mm。"
    )


def _process_hint(fit_type: str, hole: dict, shaft: dict) -> str:
    """结合加工工艺与表面粗糙度给出一句工艺建议（确定性规则）。"""
    tightest = min(hole["IT"], shaft["IT"])  # mm
    if tightest <= 0.009:
        rough = "Ra 0.4~0.8 μm"
        process = "精磨/研磨"
    elif tightest <= 0.021:
        rough = "Ra 0.8~1.6 μm"
        process = "磨削或精车"
    elif tightest <= 0.039:
        rough = "Ra 1.6~3.2 μm"
        process = "精车或铰削"
    else:
        rough = "Ra 3.2~6.3 μm"
        process = "粗车、钻扩或粗铰"

    if fit_type == "间隙配合":
        use = "用于滑动、导向或转动配合，装配时涂润滑油可自由装入"
    elif fit_type == "过盈配合":
        use = "用于传递扭矩的固定连接，需压力机压入或温差法（加热孔、冷却轴）装配"
    else:
        use = "用于定位或可拆连接，装配时用铜锤轻敲或小压力机压入"

    return (
        f"工艺建议：孔 {hole['code']}、轴 {shaft['code']} 的配合面宜{process}"
        f"（{rough}），{use}。"
    )
