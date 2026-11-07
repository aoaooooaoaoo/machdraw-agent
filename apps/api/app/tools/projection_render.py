"""工具 projection_render：三视图真投影（CSG → 隐藏线消除 → 三视图排版）。"""
from __future__ import annotations

from .base import ToolContext, ToolOutcome
from .spec import ToolSpec


def projection_render(ctx: ToolContext, model_id: str = "", query: str = "", **_):
    """三视图真投影：CSG 实体 → 隐藏线消除 → 三视图排版 + 投影辅助线。"""
    try:
        from ..geometry.models import MODELS, build_model, model_name
        from ..geometry.projection import build_three_view
    except ImportError as exc:
        return ToolOutcome(ok=False, summary="投影引擎尚未就绪", detail=str(exc))

    # 没指定模型就从提问里猜（按模型中文名或关键词）
    if not model_id:
        keys = {"圆柱": "M-TUBE", "圆筒": "M-TUBE", "轴": "M-SHAFT", "阶梯": "M-SHAFT",
                "支架": "M-BRACKET", "端盖": "M-CAP", "通孔": "M-HOLE-BLOCK",
                "孔": "M-HOLE-BLOCK", "台阶": "M-STEP", "L形": "M-L-BLOCK", "L 形": "M-L-BLOCK"}
        for kw, mid in keys.items():
            if kw in (query or ""):
                model_id = mid
                break
        model_id = model_id or "M-L-BLOCK"

    if model_id not in MODELS:
        return ToolOutcome(ok=False, summary="未知模型",
                           detail=f"{model_id}；可用：{'、'.join(MODELS)}")
    try:
        solid = build_model(model_id)
        data = build_three_view(solid, model_name(model_id), model_id)
    except Exception as exc:
        return ToolOutcome(ok=False, summary=f"投影计算失败：{type(exc).__name__}", detail=str(exc))

    st = data["stats"]
    detail = (
        f"{data['name']} · {data['size']['L']:g}×{data['size']['W']:g}×{data['size']['H']:g} mm"
        f" · {data['projection']}\n"
        f"主视图 {st['front']['visible']} 实线 / {st['front']['hidden']} 虚线\n"
        f"俯视图 {st['top']['visible']} 实线 / {st['top']['hidden']} 虚线\n"
        f"左视图 {st['left']['visible']} 实线 / {st['left']['hidden']} 虚线\n"
        "投影规律：长对正、高平齐、宽相等（图中已用彩色虚线标出）"
    )
    return ToolOutcome(
        summary=f"{data['name']} 三视图已生成 · 长对正/高平齐/宽相等",
        detail=detail,
        artifact_type="three_view",
        artifact_data=data,
        payload={"model": data},
    )


TOOL = ToolSpec(
    name="projection_render",
    label="三视图投影 · {model_id}",
    description=(
        "对内置 CSG 教学模型做真投影 + 隐藏线消除，输出主/俯/左三视图与"
        "长对正、高平齐、宽相等辅助线数据。学生问三视图、投影规律、补画视图时调用。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "model_id": {
                "type": "string",
                "description": "教学模型 id，如 M-L-BLOCK、M-TUBE、M-SHAFT、M-STEP、M-BRACKET、M-CAP；省略时按 query 关键词猜",
            },
            "query": {"type": "string", "description": "学生原问题（用于猜模型）"},
        },
        "required": [],
    },
    run=projection_render,
)
