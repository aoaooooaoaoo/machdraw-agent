"""工具 section_render：剖视图真剖切（全剖/半剖/局部剖 + 45° 剖面线）。"""
from __future__ import annotations

from .base import ToolContext, ToolOutcome
from .spec import ToolSpec


def section_render(ctx: ToolContext, model_id: str = "", axis: str = "y",
                   ratio: float = 0.5, query: str = "", mode: str = "", **_) -> ToolOutcome:
    """剖视图：平面剖切 + 剖面线（真剖切，不是盖阴影）。mode: full/half/local"""
    try:
        from ..geometry.models import MODELS, build_model, model_name
        from ..geometry.section import (
            build_half_section_view,
            build_local_section_view,
            build_section_view,
        )
    except ImportError as exc:
        return ToolOutcome(ok=False, summary="剖切引擎尚未就绪", detail=str(exc))

    if not model_id:
        keys = {"圆筒": "M-TUBE", "管": "M-TUBE", "端盖": "M-CAP", "支架": "M-BRACKET",
                "通孔": "M-HOLE-BLOCK", "孔": "M-HOLE-BLOCK", "L形": "M-L-BLOCK",
                "L 形": "M-L-BLOCK", "轴": "M-SHAFT"}
        for kw, mid in keys.items():
            if kw in (query or ""):
                model_id = mid
                break
        model_id = model_id or "M-HOLE-BLOCK"
    if model_id not in MODELS:
        return ToolOutcome(ok=False, summary="未知模型", detail=f"{model_id}")
    if axis not in ("x", "y", "z"):
        axis = "y"

    # 从提问里判断剖视类型
    if not mode:
        q = query or ""
        if "半剖" in q:
            mode = "half"
        elif "局部剖" in q:
            mode = "local"
        else:
            mode = "full"
    try:
        solid = build_model(model_id)
        nm = model_name(model_id)
        if mode == "half":
            data = build_half_section_view(solid, nm, model_id, axis)
        elif mode == "local":
            data = build_local_section_view(solid, nm, model_id, axis)
        else:
            data = build_section_view(solid, nm, model_id, axis, float(ratio))
    except Exception as exc:
        return ToolOutcome(ok=False, summary=f"剖切计算失败：{type(exc).__name__}", detail=str(exc))

    detail = (
        f"{data['name']} · 沿 {'XYZ'[('x','y','z').index(axis)]} 方向在 {data['cut_at']} mm 处剖切\n"
        f"线段 {len(data['segments'])} 条，剖面线 {len(data['hatch'])} 条（45°，间距 {data['hatch_spacing']} mm）\n"
        f"{data['note']}"
    )
    mode_cn = {"half": "半剖视图", "local": "局部剖视图", "full": "全剖视图"}.get(mode, "剖视图")
    return ToolOutcome(
        summary=f"{data['name']} {mode_cn}已生成 · 剖面线 {len(data['hatch'])} 条",
        detail=detail,
        artifact_type="three_view",
        artifact_data=data,
        payload={"section": data},
    )


TOOL = ToolSpec(
    name="section_render",
    label="剖视图生成 · {model_id}",
    description=(
        "对内置教学模型做真剖切（不是盖阴影），生成全剖/半剖/局部剖视图与 45° 剖面线，"
        "返回可直接绘制的线段数据。学生问剖视图画法、剖面线怎么画时调用。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "model_id": {
                "type": "string",
                "description": "教学模型 id，如 M-HOLE-BLOCK、M-TUBE、M-CAP、M-BRACKET、M-L-BLOCK、M-SHAFT；省略时按 query 关键词猜",
            },
            "axis": {"type": "string", "enum": ["x", "y", "z"], "default": "y",
                     "description": "剖切方向"},
            "ratio": {"type": "number", "minimum": 0.05, "maximum": 0.95, "default": 0.5,
                      "description": "剖切位置占该方向尺寸的比例"},
            "query": {"type": "string", "description": "学生原问题（用于判断模型与剖视类型）"},
            "mode": {"type": "string", "enum": ["full", "half", "local"],
                     "description": "剖视类型；省略时从 query 判断，默认全剖"},
        },
        "required": [],
    },
    run=section_render,
)
