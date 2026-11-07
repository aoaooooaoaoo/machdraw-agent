"""工具 comparison_pick：成对图辨析（易混结构对照 + 差异点 + 随堂题）。"""
from __future__ import annotations

from .base import ToolContext, ToolOutcome
from .spec import ToolSpec


def comparison_pick(ctx: ToolContext, pair_id: str = "", term: str = "", query: str = "", **_) -> ToolOutcome:
    """给一组辨析对（默认按提问关键词挑，挑不到就用第一组）。"""
    st = ctx.state
    pairs = getattr(st, "pairs", []) or []
    if not pairs:
        return ToolOutcome(ok=False, summary="辨析图库尚未装载",
                           detail="kb/figures/pairs.jsonl 为空")

    pick = None
    if pair_id:
        pick = next((p for p in pairs if p.get("pair_id") == pair_id), None)
    if pick is None:
        q = f"{term} {query}"
        best_score, best = 0, None
        for p in pairs:
            score = 0
            if p.get("title"):
                for frag in p["title"].replace(" vs ", " ").replace(" 与 ", " ").split():
                    if frag and frag in q:
                        score += 2
            for tag in p.get("structure_tags") or []:
                if tag and tag in q:
                    score += 2
            for d in p.get("differences") or []:
                if d.get("name") and d["name"] in q:
                    score += 3
            if score > best_score:
                best_score, best = score, p
        pick = best if best else pairs[0]

    diffs = pick.get("differences") or []
    detail = "\n".join(
        f"{d.get('no')}. {d.get('name')}：A {d.get('a_desc','')} / B {d.get('b_desc','')}"
        f"（{d.get('why','')}）"
        for d in diffs
    )
    return ToolOutcome(
        summary=f"{pick.get('title')} · {len(diffs)} 个差异点",
        detail=detail,
        artifact_type="comparison",
        artifact_data=pick,
        payload={"pair": pick},
    )


TOOL = ToolSpec(
    name="comparison_pick",
    label="辨析图对照 · {term}",
    description=(
        "从成对图库挑一组易混结构做辨析：并排两张图、逐条差异点、随堂一问（答案不下发）。"
        "学生问\"A 和 B 有什么区别/怎么区分\"时调用。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "pair_id": {"type": "string", "description": "指定辨析对 id（可选）"},
            "term": {"type": "string", "description": "要辨析的术语，如\"半剖\"、\"局部剖\""},
            "query": {"type": "string", "description": "学生原问题（用于关键词打分挑对）"},
        },
        "required": [],
    },
    run=comparison_pick,
)
