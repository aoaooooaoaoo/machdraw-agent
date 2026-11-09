"""工具 kb_search：知识库检索（返回原文证据卡，带门控与配图）。"""
from __future__ import annotations

from .base import EVIDENCE_CONSTRAINT, ToolContext, ToolOutcome
from .spec import ToolSpec


def kb_search(ctx: ToolContext, query: str = "", top_k: int = 6,
              scope: list[str] | None = None, **_) -> ToolOutcome:
    st = ctx.state
    # 习题默认不参与知识问答（OCR 题面噪声会污染证据），只在"出题"工具里用
    res = st.retriever.search(query, top_k=int(top_k or 6), roles=scope or None,
                              exclude_roles=["exercise", "answer"])
    hits = [h.model_dump() for h in res["hits"]]

    if not hits:
        return ToolOutcome(
            ok=False,
            summary="未检索到相关内容",
            detail="知识库中没有匹配段落。",
            artifact_type="evidence",
            artifact_data={"query": query, "evidences": [], "gated": True,
                           "coverage": res["coverage"], "totalDocs": 0},
            payload={"hits": [], "gated": True, "coverage": res["coverage"]},
        )

    lines = [f"检索到 {len(hits)} 段（top_k={top_k}）：", ""]
    for i, h in enumerate(hits, 1):
        lines.append(f"【{i}】{h['documentTitle']} · {h['section']} （{h['chunkId']}，相关度 {h['score']:.3f}）")
        lines.append(h["content"][:900])
        lines.append("")
    lines.append(EVIDENCE_CONSTRAINT)
    detail = "\n".join(lines)

    docs: dict[str, dict] = {}
    for h in hits:
        docs.setdefault(h["documentId"], {
            "id": h["documentId"], "title": h["documentTitle"],
            "category": h["category"], "status": "ready",
        })

    # 给命中的章节挂上自绘教学图（证据卡右侧直接显示 SVG）
    figures: list[dict] = []
    for h in hits[:3]:
        for f in st.figures_for(h.get("kp_ids") or [], chapter=h.get("section", "")):
            if f.get("figure_id") not in {x.get("figure_id") for x in figures}:
                figures.append(f)
        if len(figures) >= 3:
            break

    return ToolOutcome(
        summary=f"命中 {len(hits)} 段原文证据 · 「{query}」"
        + (f" · 配图 {len(figures)} 张" if figures else ""),
        detail=detail,
        artifact_type="evidence",
        artifact_data={
            "query": query,
            "evidences": hits,
            "documents": list(docs.values()),
            "totalDocs": len({c.doc_id for c in st.chunks}),
            "coverage": res["coverage"],
            "chunkCoverage": res.get("chunk_coverage"),
            "gated": res["gated"],
            "figures": figures,
        },
        payload={"hits": hits, "gated": res["gated"], "coverage": res["coverage"],
                 "figures": figures},
    )


TOOL = ToolSpec(
    name="kb_search",
    label="检索课程原文 · {query}",
    description=(
        "在课程知识库中检索与问题最相关的原文段落，返回证据卡（chunk_id、章节、"
        "覆盖率门控、配图）。它是所有回答的兜底依据；需要严谨出处时优先调用。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "检索关键词或学生原问题"},
            "top_k": {
                "type": "integer", "minimum": 1, "maximum": 20, "default": 6,
                "description": "返回的证据段数",
            },
            "scope": {
                "type": "array", "items": {"type": "string"},
                "description": "限定文档角色（如 standard、lecture），默认不限",
            },
        },
        "required": ["query"],
    },
    run=kb_search,
)
