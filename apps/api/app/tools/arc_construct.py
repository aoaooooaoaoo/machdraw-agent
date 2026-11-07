"""工具 arc_construct：圆弧连接分步作图（调用 app.geometry.arc 几何引擎）。"""
from __future__ import annotations

import importlib

from .base import ToolContext, ToolOutcome
from .spec import ToolSpec

# 圆弧连接的标准示例（学生问"外切圆弧连接怎么画"时没有给数值，就用这组典型参数演示）
_ARC_EXAMPLES: dict[str, dict] = {
    "line_line": dict(r=10.0, line1=[(0.0, 0.0), (100.0, 0.0)], line2=[(0.0, 0.0), (0.0, 100.0)]),
    # 直线 y=0 与圆 O(60,45) R20 用 R20 连接：圆心须距直线 20，且距圆外切距离 40 → 有解
    "line_arc": dict(
        r=20.0, line_p1=(0.0, 0.0), line_p2=(120.0, 0.0),
        circle_center=(60.0, 45.0), circle_r=20.0,
    ),
    "arc_arc_outer": dict(r=20.0, c1=(0.0, 0.0), r1=30.0, c2=(100.0, 0.0), r2=30.0),
    # 内切：|C−O1| = r−r1 = 60，两心距 100，半径 60 的两圆相交 → 有解
    "arc_arc_inner": dict(r=80.0, c1=(0.0, 0.0), r1=20.0, c2=(100.0, 0.0), r2=20.0),
}

_ARC_KIND_CN = {
    "line_line": "直线-直线圆角",
    "line_arc": "直线-圆弧",
    "arc_arc_outer": "圆弧-圆弧外切",
    "arc_arc_inner": "圆弧-圆弧内切",
}


def _infer_arc_kind(kind: str, query: str) -> str:
    """把「外切圆弧连接怎么画」这种自然语言意图映射到具体类型。"""
    if kind in _ARC_EXAMPLES:
        return kind
    q = f"{kind} {query}"
    if "外切" in q:
        return "arc_arc_outer"
    if "内切" in q:
        return "arc_arc_inner"
    if "圆角" in q:
        return "line_line"
    if "圆弧" in q and "直线" in q:
        return "line_arc"
    if "圆弧" in q and ("两" in q or "相切" in q):
        return "arc_arc_outer"
    return "line_line"


def _extract_radius(kind: str, query: str, default: float) -> float:
    """从提问里抓 "R20" / "半径 20"；抓不到就用示例默认值。"""
    import re as _re

    m = _re.search(r"[Rr]\s*(\d+(?:\.\d+)?)", query or "")
    if not m:
        m = _re.search(r"半径\s*(\d+(?:\.\d+)?)", query or "")
    if m:
        try:
            v = float(m.group(1))
            if 0.5 <= v <= 500:
                return v
        except ValueError:
            pass
    return default


def arc_construct(ctx: ToolContext, kind: str = "", query: str = "", **params) -> ToolOutcome:
    try:
        arc = importlib.import_module("app.geometry.arc")
    except ImportError:
        return ToolOutcome(ok=False, summary="几何引擎尚未就绪", detail="app/geometry/arc.py 缺失")

    resolved = _infer_arc_kind(kind, query)
    defaults = dict(_ARC_EXAMPLES.get(resolved) or {})
    call_params = dict(defaults)
    call_params.update({k: v for k, v in params.items() if v is not None})
    note = ""
    if "r" in call_params and query:
        asked = _extract_radius(resolved, query, float(defaults.get("r", 10.0)))
        if abs(asked - float(defaults.get("r", 10.0))) > 1e-9:
            call_params["r"] = asked
            note = f"（按你给的 R{asked:g} 计算）"

    try:
        res = arc.build_steps(resolved, **call_params)
    except Exception:
        # 学生给的半径在示例几何下无解时，退回标准示例半径再演示一次，
        # 并把"为什么无解"讲清楚——这本身就是教学内容。
        if note and "r" in defaults:
            try:
                res = arc.build_steps(resolved, **defaults)
                note = (f"（R{call_params['r']:g} 在这组示例几何下无解——"
                        f"连接弧半径必须与两已知要素的间距匹配；下面按标准示例 R{defaults['r']:g} 演示）")
                call_params = dict(defaults)
            except Exception as exc:
                return ToolOutcome(ok=False, summary=f"作图计算失败：{type(exc).__name__}", detail=str(exc))
        else:
            return ToolOutcome(ok=False, summary="作图计算失败：ValueError",
                               detail="该组几何条件下无解，请检查半径与已知要素的间距是否匹配。")

    steps = res.get("steps") or []
    detail = "\n".join(f"{s['n']}. {s['title']}：{s['detail']}" for s in steps)
    return ToolOutcome(
        summary=(res.get("summary") or f"{_ARC_KIND_CN.get(resolved, resolved)} 作图步骤已生成") + note,
        detail=detail,
        artifact_type="coach",
        artifact_data={
            "kind": resolved,
            "kind_cn": _ARC_KIND_CN.get(resolved, resolved),
            "params": call_params,
            "note": note,
            "data": res,
        },
        payload={"result": res},
    )


TOOL = ToolSpec(
    name="arc_construct",
    label="圆弧连接作图 · {kind}",
    description=(
        "生成圆弧连接的分步作图脚本（圆心、切点、圆弧指令）：直线-直线圆角、"
        "直线-圆弧、圆弧-圆弧外切、圆弧-圆弧内切。学生问\"圆弧连接怎么画\"且没给数值时，"
        "用内置标准示例演示；给了 R 值会按值重算。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "kind": {
                "type": "string",
                "enum": ["auto", "line_line", "line_arc", "arc_arc_outer", "arc_arc_inner"],
                "default": "auto",
                "description": "连接类型；auto 时按 query 里的关键词自动判断",
            },
            "query": {"type": "string", "description": "学生原问题（用于判断类型与抓取 R 值）"},
            "r": {"type": "number", "exclusiveMinimum": 0, "description": "连接圆弧半径"},
            "line1": {
                "type": "array", "items": {"type": "array", "items": {"type": "number"},
                                           "minItems": 2, "maxItems": 2},
                "minItems": 2, "maxItems": 2,
                "description": "第一条直线两点 [[x1,y1],[x2,y2]]",
            },
            "line2": {
                "type": "array", "items": {"type": "array", "items": {"type": "number"},
                                           "minItems": 2, "maxItems": 2},
                "minItems": 2, "maxItems": 2,
                "description": "第二条直线两点 [[x1,y1],[x2,y2]]",
            },
            "line_p1": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 2,
                        "description": "直线—圆弧连接：直线上一点"},
            "line_p2": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 2,
                        "description": "直线—圆弧连接：直线上另一点"},
            "circle_center": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 2,
                              "description": "直线—圆弧连接：已知圆圆心"},
            "circle_r": {"type": "number", "exclusiveMinimum": 0,
                         "description": "直线—圆弧连接：已知圆半径"},
            "c1": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 2,
                   "description": "圆弧—圆弧连接：第一个已知圆圆心"},
            "r1": {"type": "number", "exclusiveMinimum": 0, "description": "第一个已知圆半径"},
            "c2": {"type": "array", "items": {"type": "number"}, "minItems": 2, "maxItems": 2,
                   "description": "圆弧—圆弧连接：第二个已知圆圆心"},
            "r2": {"type": "number", "exclusiveMinimum": 0, "description": "第二个已知圆半径"},
        },
        "required": [],
    },
    run=arc_construct,
)
