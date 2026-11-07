"""工具 quiz_from_kb：从习题库出题（答案隔离）。"""
from __future__ import annotations

from .base import ToolContext, ToolOutcome
from .spec import ToolSpec


def quiz_from_kb(ctx: ToolContext, topic: str = "", n: int = 1, **_) -> ToolOutcome:
    """从习题库出题。正确答案不下发（答案隔离）。"""
    st = ctx.state
    pool = [c for c in st.chunks if c.role.value == "exercise"]
    if not pool:
        return ToolOutcome(ok=False, summary="题库尚未装载", detail="kb/exercises/*.jsonl 为空")
    res = st.retriever.search(topic, top_k=max(int(n), 3), roles=["exercise"])
    hits = res["hits"][: int(n)]
    if not hits:
        return ToolOutcome(ok=False, summary="未命中合适题目", detail=f"没有与「{topic}」相关的习题")
    return ToolOutcome(
        summary=f"从题库抽了 {len(hits)} 道题（答案暂不下发）",
        detail="\n".join(f"- {h.content[:140]}" for h in hits),
        artifact_type="quiz",
        artifact_data={
            "questions": [h.model_dump() for h in hits],
            "answer_withheld": True,
            "quality_note": "题面来自扫描件 OCR，存在错字；内部教研用，对外须换源或人工校对。",
        },
        payload={"questions": [h.model_dump() for h in hits]},
    )


TOOL = ToolSpec(
    name="quiz_from_kb",
    label="从题库出题 · {topic}",
    description=(
        "从习题库按主题抽题，题面下发、答案隔离（学生点\"看解析\"才给答案）。"
        "学生说\"考考我/来一道题/练一练\"时调用。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "topic": {"type": "string", "description": "出题主题或学生原问题"},
            "n": {"type": "integer", "minimum": 1, "maximum": 10, "default": 1,
                  "description": "出几道题"},
        },
        "required": [],
    },
    run=quiz_from_kb,
)
