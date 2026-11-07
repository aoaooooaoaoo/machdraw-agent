"""工具 sketch_grade：手绘找茬（真判分 / 生成找茬练习）。"""
from __future__ import annotations

from .base import ToolContext, ToolOutcome
from .spec import ToolSpec


def sketch_grade(ctx: ToolContext, model_id: str = "", view: str = "all",
                 segments: list | None = None, inject: str = "", **_) -> ToolOutcome:
    """手绘找茬：把学生画的线与标准答案比对，给出可命名的错误。

    · segments 给了 → 真判分；
    · 没给 + inject="missing,linetype" → 生成一道"找茬练习"（改坏图 + 藏起来的答案）。
    """
    try:
        from ..geometry.models import MODELS, build_model, model_name
        from ..geometry.projection import build_three_view
        from ..vision.sketch import grade, inject_errors
    except ImportError as exc:
        return ToolOutcome(ok=False, summary="找茬引擎尚未就绪", detail=str(exc))

    model_id = model_id or "M-L-BLOCK"
    if model_id not in MODELS:
        return ToolOutcome(ok=False, summary="未知模型", detail=model_id)

    data = build_three_view(build_model(model_id), model_name(model_id), model_id)
    truth_all = [{"x1": s["x1"], "y1": s["y1"], "x2": s["x2"], "y2": s["y2"],
                  "hidden": s["hidden"], "view": s["view"]} for s in data["segments"]]
    truth = truth_all if view == "all" else [t for t in truth_all if t["view"] == view]
    if not truth:
        return ToolOutcome(ok=False, summary="该视图没有可供比对的线条", detail=view)

    kinds = [k.strip() for k in (inject or "").split(",") if k.strip()]

    if kinds:
        bad, done = inject_errors(truth, kinds, seed=0)
        return ToolOutcome(
            summary=f"找茬练习已生成：{len(done)} 处错误（{view}）",
            detail="题目已下发，答案暂不公开。逐条找出来后提交，系统会告诉你对不对。",
            artifact_type="annotation",
            artifact_data={
                "mode": "exercise",
                "model_id": model_id,
                "model_name": model_name(model_id),
                "view": view,
                "drawing": bad,
                "expect_count": len(done),
                "inject_hint": "、".join(done),
                "answer_withheld": True,
            },
            payload={"drawing": bad, "truth": truth},
        )

    if not segments:
        return ToolOutcome(
            ok=False,
            summary="还没有收到你画的线",
            detail="把线提交上来才能批改；也可以先要一道找茬练习。",
        )

    res = grade(segments, truth)
    detail_lines = [f"得分 {res['score']:.0%}（{res['matched']}/{res['truth_total']} 条）· {res['level']}"]
    for e in res["errors"][:8]:
        detail_lines.append(f"[{e['type_name']}] {e['desc']}")
    if res["errors"]:
        detail_lines.append(f"共 {len(res['errors'])} 处，统计 {res['error_counts']}")
    detail_lines.append(res["note"])

    return ToolOutcome(
        summary=f"找茬结果：{res['level']} · 得分 {res['score']:.0%} · {len(res['errors'])} 处问题",
        detail="\n".join(detail_lines),
        artifact_type="annotation",
        artifact_data={"mode": "grade", "model_id": model_id, "view": view, **res},
        payload={"result": res},
    )


TOOL = ToolSpec(
    name="sketch_grade",
    label="手绘找茬 · {view}",
    description=(
        "把学生提交的线段与标准三视图比对，给出可命名的错误（漏画/多画/虚实线混淆/位置偏差）；"
        "不传 segments 而传 inject 时，生成一道找茬练习（改坏图、答案暂不下发）。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "model_id": {"type": "string", "description": "教学模型 id，默认 M-L-BLOCK"},
            "view": {"type": "string", "enum": ["all", "front", "top", "left"], "default": "all",
                     "description": "只检查某个视图，默认全部"},
            "segments": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "x1": {"type": "number"}, "y1": {"type": "number"},
                        "x2": {"type": "number"}, "y2": {"type": "number"},
                        "view": {"type": "string"},
                        "hidden": {"type": "boolean"},
                    },
                    "required": ["x1", "y1", "x2", "y2"],
                },
                "description": "学生画的线段集合；给了才判分",
            },
            "inject": {
                "type": "string",
                "description": "要注入的错误类型，逗号分隔：missing,linetype,offset 等；给了就生成找茬练习",
            },
        },
        "required": [],
    },
    run=sketch_grade,
)
