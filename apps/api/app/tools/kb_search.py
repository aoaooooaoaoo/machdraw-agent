"""工具 kb_search：知识库检索（返回原文证据卡，带门控与配图）。"""
from __future__ import annotations

from .base import EVIDENCE_CONSTRAINT, ToolContext, ToolOutcome
from .spec import ToolSpec

from ..rag.tokenize import tokenize


def _graph_expand(st, hits: list[dict], query: str, limit: int = 2) -> list[dict]:
    """GraphRAG-lite：命中块 → 知识点 → 沿图谱 1 跳邻居 → 补相关块。

    只做“补充上下文”，不改变原检索的 coverage/门控判定；
    补进来的块带 related=True / via 标签，前端可区分。
    """
    kp_to_node = {}
    for n in st.nodes:
        if n.get("kp_id"):
            kp_to_node[n["kp_id"]] = n
    if not kp_to_node:
        return []
    adj: dict[str, set[str]] = {}
    for e in st.edges:
        s, t = e.get("source"), e.get("target")
        if not s or not t:
            continue
        adj.setdefault(s, set()).add(t)
        adj.setdefault(t, set()).add(s)
    node_to_kp = {n["id"]: n.get("kp_id") for n in st.nodes if n.get("id")}
    seed_kps = {k for h in hits for k in (h.get("kp_ids") or []) if k in kp_to_node}
    if not seed_kps:
        return []
    neighbor_kps: set[str] = set()
    for kp in seed_kps:
        node = kp_to_node[kp]
        for nid in adj.get(node["id"], set()):
            nkp = node_to_kp.get(nid)
            if nkp and nkp not in seed_kps:
                neighbor_kps.add(nkp)
    if not neighbor_kps:
        return []
    seen = {h.get("chunkId") for h in hits}
    q_tokens = set(tokenize(query))
    candidates: list[tuple[float, dict]] = []
    for c in st.chunks:
        if c.role.value in ("exercise", "answer") or c.chunk_id in seen:
            continue
        if not (set(c.kp_ids) & neighbor_kps):
            continue
        overlap = len(q_tokens & set(tokenize(c.text[:400]))) if q_tokens else 0
        candidates.append((overlap + 0.1, c))
    candidates.sort(key=lambda x: -x[0])
    out: list[dict] = []
    for _, c in candidates[:limit]:
        labels = [kp_to_node[k]["label"] for k in (set(c.kp_ids) & neighbor_kps) if k in kp_to_node]
        out.append({
            "chunkId": c.chunk_id,
            "documentId": c.doc_id,
            "documentTitle": c.document_title,
            "category": c.category,
            "section": c.section,
            "content": c.text,
            "score": 0.0,
            "role": c.role.value,
            "page": c.page,
            "kp_ids": c.kp_ids,
            "related": True,
            "via": labels[:2],
        })
    return out


def kb_search(ctx: ToolContext, query: str = "", top_k: int = 6,
              scope: list[str] | None = None, **_) -> ToolOutcome:
    st = ctx.state
    # 习题默认不参与知识问答（OCR 题面噪声会污染证据），只在"出题"工具里用
    res = st.retriever.search(query, top_k=int(top_k or 6), roles=scope or None,
                              exclude_roles=["exercise", "answer"])
    hits = [h.model_dump() for h in res["hits"]]
    related = _graph_expand(st, hits, query) if hits else []
    if related:
        hits = hits + related

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
    if related:
        lines.append(f"\n【图谱扩展】另有 {len(related)} 段来自前置/关联知识点（不改变原检索门控）：")
        for r in related:
            via = "、".join(r.get("via") or [])
            lines.append(f"- {r['documentTitle']} · {r['section']}（{r['chunkId']}，经：{via}）")
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
        summary=f"命中 {len(hits) - len(related)} 段原文证据 · 「{query}」"
        + (f" · 图谱扩展 {len(related)} 段" if related else "")
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
                 "figures": figures, "graph_expanded": len(related)},
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
