"""螺纹与标准件比例画法计算引擎。

依据
----
* GB/T 192-2003《普通螺纹 基本牙型》、GB/T 193-2003《普通螺纹 直径与螺距系列》、
  GB/T 196-2003《普通螺纹 基本尺寸》；
* GB/T 197-2018《普通螺纹 公差》、GB/T 5796.1~5796.4《梯形螺纹》；
* GB/T 7307-2001《55°非密封管螺纹》；
* GB/T 4459.1-1995《机械制图 螺纹及螺纹紧固件表示法》；
* GB/T 5782-2016《六角头螺栓》及其比例画法（教材"螺纹紧固件比例画法"）。

本模块提供 3 个纯函数：

    parse_thread(spec)    解析螺纹标记，如 M10、M10×1.5、M20×2-6H、Tr24×5、G1/2
    thread_drawing(spec)  按比例画法给出大径/小径/中径与表示法要点
    bolt_drawing(spec)    六角头螺栓（GB/T 5782）的比例画法尺寸

设计原则
--------
* 只用 Python 标准库（math / re / unicodedata / typing），不依赖网络与大模型；
* 全部数值来自标准表或标准规定的比例关系，函数是确定性的纯函数；
* 比例画法（如小径 d1 ≈ 0.85d）是**制图简化约定**，不是螺纹真实牙型尺寸，
  返回值中同时给出了使用的依据，便于教学时讲清"为什么这么画"；
* 无法识别或超出常用范围的标记一律抛 ``ValueError``（中文原因），不猜。
"""
from __future__ import annotations

import math
import re
import unicodedata
from typing import Final

__all__ = ["parse_thread", "thread_drawing", "bolt_drawing", "COARSE_PITCH", "PIPE_THREADS"]

# ---------------------------------------------------------------------------
# 标准数据
# ---------------------------------------------------------------------------

#: 普通螺纹粗牙螺距（GB/T 193-2003），单位 mm，键为公称直径
COARSE_PITCH: Final[dict[float, float]] = {
    1.0: 0.25,
    1.2: 0.25,
    1.4: 0.3,
    1.6: 0.35,
    1.8: 0.35,
    2.0: 0.4,
    2.2: 0.45,
    2.5: 0.45,
    3.0: 0.5,
    3.5: 0.6,
    4.0: 0.7,
    4.5: 0.75,
    5.0: 0.8,
    5.5: 0.9,
    6.0: 1.0,
    7.0: 1.0,
    8.0: 1.25,
    9.0: 1.25,
    10.0: 1.5,
    11.0: 1.5,
    12.0: 1.75,
    14.0: 2.0,
    16.0: 2.0,
    18.0: 2.5,
    20.0: 2.5,
    22.0: 2.5,
    24.0: 3.0,
    27.0: 3.0,
    30.0: 3.5,
    33.0: 3.5,
    36.0: 4.0,
    39.0: 4.0,
    42.0: 4.5,
    45.0: 4.5,
    48.0: 5.0,
    52.0: 5.0,
    56.0: 5.5,
    60.0: 5.5,
    64.0: 6.0,
}

#: 55°非密封管螺纹（GB/T 7307-2001）常用尺寸：
#: 键为英寸尺寸代号，值为 (大径 d, 螺距 P)，单位 mm
PIPE_THREADS: Final[dict[str, tuple[float, float]]] = {
    "1/8": (9.728, 0.907),
    "1/4": (13.157, 1.337),
    "3/8": (16.662, 1.337),
    "1/2": (20.955, 1.814),
    "5/8": (22.911, 1.814),
    "3/4": (26.441, 1.814),
    "7/8": (30.201, 1.814),
    "1": (33.249, 2.309),
    "1-1/4": (41.910, 2.309),
    "1-1/2": (47.803, 2.309),
    "2": (59.614, 2.309),
    "2-1/2": (75.184, 2.309),
    "3": (87.884, 2.309),
    "3-1/2": (100.330, 2.309),
    "4": (113.030, 2.309),
}

#: 管螺纹牙型高度系数（55° 牙型）：d2 = d - 0.640327P，d1 = d - 1.280654P
_PIPE_HALF_HEIGHT: Final[float] = 0.640327

_CN_DIGITS = str.maketrans("０１２３４５６７８９", "0123456789")


# ---------------------------------------------------------------------------
# 工具
# ---------------------------------------------------------------------------


def _normalize(spec: str) -> str:
    if not isinstance(spec, str):
        raise ValueError(f"螺纹标记必须是字符串，收到 {spec!r}")
    text = unicodedata.normalize("NFKC", spec).strip()
    text = text.translate(_CN_DIGITS)
    # 统一乘号与空白
    text = text.replace("×", "x").replace("X", "x").replace("*", "x")
    text = text.replace("＊", "x").replace("—", "-").replace("－", "-")
    text = re.sub(r"\s+", "", text)
    if not text:
        raise ValueError("螺纹标记不能为空")
    return text


def _fmt(value: float) -> float:
    result = round(float(value), 6)
    return 0.0 if result == 0 else result


def _check_positive(value: float, name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} 必须是数值，收到 {value!r}") from exc
    if not math.isfinite(number) or number <= 0:
        raise ValueError(f"{name} 必须大于 0，收到 {value!r}")
    return number


def _coarse_pitch(diameter: float) -> float:
    for nominal, pitch in COARSE_PITCH.items():
        if abs(nominal - diameter) < 1e-9:
            return pitch
    supported = "、".join(f"M{d:g}" for d in sorted(COARSE_PITCH))
    raise ValueError(
        f"公称直径 {diameter:g} mm 不在常用粗牙普通螺纹序列内，无法确定粗牙螺距；"
        f"可用的粗牙公称直径：{supported}"
    )


def _parse_pipe(text: str) -> dict:
    """解析 G 系列 55°非密封管螺纹标记。"""
    match = re.fullmatch(r"G(\d+(?:-\d+/\d+|/\d+)?)([ABC]?)", text, re.IGNORECASE)
    if not match:
        raise ValueError(
            f"无法解析管螺纹标记 {text!r}；正确格式如 G1/2、G3/4、G1、G1-1/4（可选 A/B 精度等级）"
        )
    size = match.group(1)
    grade = match.group(2).upper() or None
    if size.startswith("0"):
        size = size.lstrip("0") or "0"
    key = size
    if key not in PIPE_THREADS:
        supported = "、".join(f"G{s}" for s in PIPE_THREADS)
        raise ValueError(
            f"不支持的管螺纹尺寸代号 G{size}；本引擎已内嵌：{supported}"
        )
    major, pitch = PIPE_THREADS[key]
    inch = _inch_value(key)
    return {
        "spec": f"G{key}" + (grade or ""),
        "raw": f"G{key}" + (grade or ""),
        "type": "pipe",
        "type_name": "55°非密封管螺纹",
        "profile": "55°",
        "standard": "GB/T 7307-2001",
        "size_inch": key,
        "nominal": float(inch),
        "d": float(major),
        "pitch": float(pitch),
        "series": "",
        "starts": 1,
        "direction": "右旋",
        "tolerance": grade,
        "length_class": None,
    }


def _inch_value(size: str) -> float:
    """把 '1/2'、'1-1/4' 形式的尺寸代号换算成英寸数值。"""
    total = 0.0
    for part in size.split("-"):
        if "/" in part:
            num, den = part.split("/")
            total += float(num) / float(den)
        else:
            total += float(part)
    return total


def _parse_metric(text: str) -> dict:
    """解析米制普通螺纹标记（M）。"""
    match = re.fullmatch(
        r"M(\d+(?:\.\d+)?)(?:x(\d+(?:\.\d+)?))?(.*)", text, re.IGNORECASE
    )
    if not match:
        raise ValueError(
            f"无法解析普通螺纹标记 {text!r}；正确格式如 M10、M10x1.5、M20x2-6H"
        )
    diameter = float(match.group(1))
    if diameter <= 0:
        raise ValueError(f"螺纹公称直径必须大于 0，收到 {text!r}")
    given_pitch = match.group(2)
    rest = match.group(3) or ""

    direction = "右旋"
    tolerance: str | None = None
    length_class: str | None = None
    starts = 1

    # 处理剩余部分：-6H、-7H、-6g、-LH、-S 等（顺序可变，允许连写）
    tokens = [token for token in rest.split("-") if token != ""]
    for token in tokens:
        upper = token.upper()
        if "LH" in upper or token in ("左", "左旋"):
            direction = "左旋"
            token = re.sub(r"(?i)LH|左旋|左", "", token) or ""
        elif "RH" in upper or token in ("右", "右旋"):
            direction = "右旋"
            token = re.sub(r"(?i)RH|右旋|右", "", token) or ""
        if not token:
            continue
        if re.fullmatch(r"[0-9]+[gGhH][0-9]*(?:[gGhH][0-9]*)?", token):
            tolerance = token
            continue
        if token.upper() in ("S", "N", "L"):
            length_class = token.upper()
            continue
        raise ValueError(
            f"无法识别螺纹标记中的附加代号 {token!r}（{text!r}）；"
            "支持公差带（如 6H、6g）、旋向（LH）与旋合长度（S/N/L）"
        )

    if given_pitch is not None:
        pitch = float(given_pitch)
        _check_positive(pitch, "螺距")
        series = "细牙"
        if abs(pitch - _coarse_pitch(diameter)) < 1e-9:
            series = "粗牙"
    else:
        pitch = _coarse_pitch(diameter)
        series = "粗牙"

    display = f"M{diameter:g}"
    if given_pitch is not None:
        display += f"x{pitch:g}"
    if tolerance:
        display += f"-{tolerance}"
    if direction == "左旋":
        display += "-LH"

    return {
        "spec": display,
        "raw": text,
        "type": "metric",
        "type_name": "普通米制螺纹（60°）",
        "profile": "60°",
        "standard": "GB/T 192-2003 / GB/T 193-2003 / GB/T 196-2003",
        "size_inch": None,
        "nominal": diameter,
        "d": diameter,
        "pitch": pitch,
        "series": series,
        "starts": starts,
        "direction": direction,
        "tolerance": tolerance,
        "length_class": length_class,
    }


def _parse_trapezoidal(text: str) -> dict:
    """解析梯形螺纹标记（Tr）。"""
    match = re.fullmatch(
        r"TR(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)(.*)", text, re.IGNORECASE
    )
    if not match:
        raise ValueError(
            f"无法解析梯形螺纹标记 {text!r}；正确格式如 Tr24x5、Tr30x6-7e-LH"
        )
    diameter = float(match.group(1))
    pitch = float(match.group(2))
    _check_positive(diameter, "公称直径")
    _check_positive(pitch, "螺距")
    rest = match.group(3) or ""

    direction = "右旋"
    tolerance: str | None = None
    length_class: str | None = None
    tokens = [token for token in rest.split("-") if token != ""]
    for token in tokens:
        upper = token.upper()
        if "LH" in upper or token in ("左", "左旋"):
            direction = "左旋"
            token = re.sub(r"(?i)LH|左旋|左", "", token) or ""
        elif "RH" in upper:
            direction = "右旋"
            token = re.sub(r"(?i)RH", "", token) or ""
        if not token:
            continue
        if re.fullmatch(r"[0-9]+[A-Za-z][0-9]*(?:[A-Za-z][0-9]*)?", token):
            tolerance = token
            continue
        if token.upper() in ("S", "N", "L"):
            length_class = token.upper()
            continue
        raise ValueError(
            f"无法识别梯形螺纹标记中的附加代号 {token!r}（{text!r}）"
        )

    display = f"Tr{diameter:g}x{pitch:g}"
    if tolerance:
        display += f"-{tolerance}"
    if direction == "左旋":
        display += "-LH"
    return {
        "spec": display,
        "raw": text,
        "type": "trapezoidal",
        "type_name": "梯形螺纹（30°）",
        "profile": "30°",
        "standard": "GB/T 5796.1~5796.4-2005",
        "size_inch": None,
        "nominal": diameter,
        "d": diameter,
        "pitch": pitch,
        "series": "",
        "starts": 1,
        "direction": direction,
        "tolerance": tolerance,
        "length_class": length_class,
    }


# ---------------------------------------------------------------------------
# 公开 API
# ---------------------------------------------------------------------------


def parse_thread(spec: str) -> dict:
    """解析螺纹标记。

    支持示例::

        "M10"          普通螺纹，粗牙（P=1.5）
        "M10x1.5"      普通螺纹，细牙
        "M20x2-6H"     普通螺纹，细牙，内螺纹公差带 6H
        "Tr24x5"       梯形螺纹
        "G1/2"         55°非密封管螺纹

    返回
    ----
    ``{"spec", "raw", "type", "type_name", "profile", "standard", "size_inch",
       "nominal", "d", "pitch", "series", "starts", "direction",
       "tolerance", "length_class"}``

    其中 ``type`` 为 ``"metric"`` / ``"trapezoidal"`` / ``"pipe"``，
    ``d`` 为大径（mm），``pitch`` 为螺距（mm）。
    """
    text = _normalize(spec)
    if text.upper().startswith("TR"):
        return _parse_trapezoidal(text)
    if text.upper().startswith("G"):
        return _parse_pipe(text)
    if text.upper().startswith("M"):
        return _parse_metric(text)
    raise ValueError(
        f"无法识别的螺纹标记 {spec!r}；支持 M（普通螺纹）、Tr（梯形螺纹）、G（55°管螺纹）"
    )


def _thread_points(parsed: dict) -> list[str]:
    """按类型返回螺纹规定画法要点（教材口径）。"""
    kind = parsed["type"]
    if kind == "metric":
        return [
            "牙顶（大径 d）用粗实线绘制，牙底（小径 d1）用细实线绘制，且 d1 ≈ 0.85d。",
            "小径细实线应画入倒角内（外螺纹）；内螺纹的小径用粗实线、大径用细实线，细实线也画入倒角内。",
            "在垂直于轴线的端视图中，小径细实线圆只画约 3/4 圈，不画倒角圆。",
            "螺纹终止线用粗实线绘制；外螺纹终止线画到牙底处，内螺纹终止线画到牙顶处。",
            "剖面线画到粗实线（外螺纹画到大径、内螺纹画到小径）为止。",
            "需要表示螺纹收尾时，用与轴线成 30° 的细实线表示。",
        ]
    if kind == "trapezoidal":
        return [
            "梯形螺纹牙型为 30°，大径 d 用粗实线绘制，小径用细实线绘制。",
            "比例画法按基本尺寸：中径 d2 = d − 0.5P，小径 d1 = d − P（近似）。",
            "螺纹标记 Tr 写在尺寸线处，梯形螺纹需注出螺距（如 Tr24x5）。",
            "左旋螺纹需注 LH；多线螺纹注导程与螺距（如 Tr24x10(P5)）。",
            "端视图中牙底细实线圆同样只画约 3/4 圈，不画倒角圆。",
        ]
    return [
        "55°非密封管螺纹的尺寸代号是英寸制，必须查表确定大径 d，不能按代号直接乘 25.4。",
        "外螺纹大径用粗实线、小径用细实线；内螺纹小径用粗实线、大径用细实线。",
        "管螺纹的配合以大径为基准，标记 G1/2 中的 1/2 表示尺寸代号而不是公称直径。",
        "端视图中牙底细实线圆画约 3/4 圈，不画倒角圆。",
        "螺纹终止线用粗实线绘制，剖面线画到粗实线为止。",
    ]


def thread_drawing(spec: str) -> dict:
    """按比例画法给出螺纹的绘图尺寸与表示法要点。

    参数
    ----
    spec: 螺纹标记，如 ``"M10"``、``"M10x1.5"``、``"Tr24x5"``、``"G1/2"``

    返回
    ----
    ``{"spec", "type", "type_name", "d", "d1", "d2", "pitch",
       "points": [...], "table": {...}}``

    说明
    ----
    * 普通螺纹按 GB/T 4459.1 比例画法：``d1 = d2 = 0.85d``（制图简化值，
      不是螺纹真实小径/中径）；``pitch`` 由 GB/T 193 查得。
    * 梯形螺纹按 GB/T 5796 基本尺寸近似：``d2 = d − 0.5P``、``d1 = d − P``。
    * 55°管螺纹按牙型关系：``d2 = d − 0.640327P``、``d1 = d − 1.280654P``。
    """
    parsed = parse_thread(spec)
    d = parsed["d"]
    pitch = parsed["pitch"]
    kind = parsed["type"]

    if kind == "metric":
        d1 = _fmt(0.85 * d)
        d2 = _fmt(0.85 * d)
        ratio_note = "比例画法：d1 = d2 = 0.85d（GB/T 4459.1 简化画法）"
    elif kind == "trapezoidal":
        d2 = _fmt(d - 0.5 * pitch)
        d1 = _fmt(d - pitch)
        ratio_note = "梯形螺纹基本尺寸近似：d2 = d − 0.5P，d1 = d − P（GB/T 5796.3）"
    else:  # pipe
        d2 = _fmt(d - _PIPE_HALF_HEIGHT * pitch)
        d1 = _fmt(d - 2.0 * _PIPE_HALF_HEIGHT * pitch)
        ratio_note = "55°管螺纹牙型关系：d2 = d − 0.640327P，d1 = d − 1.280654P"

    table = {
        "d": d,
        "d1": d1,
        "d2": d2,
        "pitch": pitch,
        "series": parsed["series"],
        "standard": parsed["standard"],
        "profile": parsed["profile"],
        "draw_ratio": ratio_note,
    }
    if parsed["tolerance"]:
        table["tolerance"] = parsed["tolerance"]
    if parsed["type"] == "pipe":
        table["size_inch"] = parsed["size_inch"]

    return {
        "spec": parsed["spec"],
        "type": kind,
        "type_name": parsed["type_name"],
        "d": d,
        "d1": d1,
        "d2": d2,
        "pitch": pitch,
        "points": _thread_points(parsed),
        "table": table,
    }


def _parse_bolt_spec(spec: str) -> tuple[float, float, float | None, str | None]:
    """解析螺栓标记，返回 (d, pitch, length, tolerance)。

    ``M10`` / ``M10x60`` / ``M10x1.5x60`` / ``M10x60-6g`` 均可；
    ``x`` 后的数值小于 d/2 时按细牙螺距处理，否则按公称长度处理。
    """
    text = _normalize(spec)
    match = re.fullmatch(r"M(\d+(?:\.\d+)?)(?:x(\d+(?:\.\d+)?))?(?:x(\d+(?:\.\d+)?))?(?:-(.*))?", text, re.IGNORECASE)
    if not match:
        raise ValueError(
            f"无法解析螺栓标记 {spec!r}；正确格式如 M10、M10x60、M10x1.5x60"
        )
    diameter = float(match.group(1))
    _check_positive(diameter, "螺栓公称直径")
    second = match.group(2)
    third = match.group(3)
    tail = match.group(4) or ""

    pitch: float | None = None
    length: float | None = None
    if second is not None:
        value = float(second)
        if value < diameter / 2.0:
            pitch = value
            if third is not None:
                length = float(third)
        else:
            length = value
    if third is not None and length is None:
        length = float(third)
    if pitch is not None:
        _check_positive(pitch, "螺距")
    if length is not None:
        _check_positive(length, "螺栓公称长度")

    tolerance: str | None = None
    if tail:
        if not re.fullmatch(r"[0-9]*[gGhH][0-9]*(?:[gGhH][0-9]*)?", tail):
            raise ValueError(f"无法识别螺栓标记中的公差带代号 {tail!r}")
        tolerance = tail
    if pitch is None:
        pitch = _coarse_pitch(diameter)
    return diameter, pitch, length, tolerance


def bolt_drawing(spec: str) -> dict:
    """六角头螺栓（GB/T 5782）比例画法尺寸。

    参数
    ----
    spec: 螺栓标记，如 ``"M10"``、``"M10x60"``、``"M10x1.5x60"``

    返回
    ----
    ``{"spec", "d", "pitch", "k", "e", "s", "r", "l", "b",
       "head": {...}, "points": [...], "table": {...}}``

    比例关系（教材 / GB/T 5782 比例画法）
    ------------------------------------
    * 头部高度 ``k ≈ 0.7d``；
    * 头部对角宽度 ``e ≈ 2d``；
    * 六角头对边宽度 ``s = e·cos30° ≈ 1.732d``；
    * 头部端面圆弧半径 ``r ≈ 1.5d``（六角头简化画法：用圆弧代替双曲线）；
    * 螺纹长度 ``b = 2d + 6``（l ≤ 125）、``2d + 12``（125 < l ≤ 200）、
      ``2d + 25``（l > 200），GB/T 5782 规定；
    * 垫圈 ``d_w ≈ 2.2d``、厚 ``h ≈ 0.15d``；螺母高 ``≈0.8d``、对角 ``≈2d``。
    未给出公称长度时，取 ``l = 4d`` 作为示例长度并在 table 中注明。
    """
    diameter, pitch, length, tolerance = _parse_bolt_spec(spec)
    d = diameter
    l = length if length is not None else _fmt(4.0 * d)
    explicit_length = length is not None

    if l <= 125.0:
        b = 2.0 * d + 6.0
    elif l <= 200.0:
        b = 2.0 * d + 12.0
    else:
        b = 2.0 * d + 25.0
    b = _fmt(min(b, l))  # 短螺栓时螺纹长不应超过公称长度

    k = _fmt(0.7 * d)
    e = _fmt(2.0 * d)
    s = _fmt(e * math.cos(math.radians(30.0)))
    r = _fmt(1.5 * d)
    washer_d = _fmt(2.2 * d)
    washer_h = _fmt(0.15 * d)
    nut_h = _fmt(0.8 * d)

    table = {
        "d": d,
        "pitch": pitch,
        "k": k,
        "e": e,
        "s": s,
        "r": r,
        "l": l,
        "b": b,
        "washer_d": washer_d,
        "washer_h": washer_h,
        "nut_height": nut_h,
        "standard": "GB/T 5782-2016",
        "proportion": "k=0.7d, e=2d, s=e·cos30°, r=1.5d",
        "length_explicit": explicit_length,
    }
    if tolerance:
        table["tolerance"] = tolerance

    points = [
        "六角头螺栓头部高度 k≈0.7d，对角宽度 e≈2d，对边宽度 s=e·cos30°≈1.732d。",
        "头部端面按简化画法用半径 r≈1.5d 的圆弧代替双曲线（六角头简化画法）。",
        "螺栓杆部大径 d 用粗实线，螺纹小径 d1≈0.85d 用细实线，小径线画入倒角内。",
        "螺纹长度 b 按 GB/T 5782：l≤125 时 b=2d+6；125<l≤200 时 b=2d+12；l>200 时 b=2d+25。",
        "头部与杆部过渡处应有小圆角 r≈0.1d，不画成尖角。",
        "螺栓连接装配图中，两零件接触面画一条线，不接触面画两条线；螺纹连接部分按外螺纹画法。",
    ]

    return {
        "spec": spec.strip() if isinstance(spec, str) else spec,
        "d": d,
        "pitch": pitch,
        "k": k,
        "e": e,
        "s": s,
        "r": r,
        "l": l,
        "b": b,
        "head": {
            "k": k,
            "e": e,
            "s": s,
            "r": r,
            "form": "hex",
            "simplified": True,
        },
        "points": points,
        "table": table,
    }
