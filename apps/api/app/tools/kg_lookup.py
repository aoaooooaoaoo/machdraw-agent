"""工具 kg_lookup：知识图谱查询（前置/易混淆/包含/因果邻居 + 复习路径）。

节点定位三级兜底：
  1. node_id 直接命中；
  2. 标签精确/包含匹配（"点堆动力学" 命中 "点堆动力学方程" 这类）；
  3. 检索兜底——用问题去检索知识库，取命中块的 kp_ids 反查节点。
"""
from __future__ import annotations

from .base import ToolContext, ToolOutcome
from .spec import ToolSpec

REL_CN = {"prereq": "前置", "contrast": "易混淆", "compose": "包含", "cause": "导致"}


def _locate(st, term: str, node_id: str):
    """按 3 级兜底找节点。"""
    if node_id:
        n = st.node(node_id)
        if n:
            return n
    if not term:
        return None
    term = term.strip()
    n = st.node_by_label(term)
    if n:
        return n

    # 2b) 字符重叠：term 的字被节点标签覆盖得越全越可能是它
    best, best_score = None, 0.0
    tset = set(term)
    for node in st.nodes:
        label = node.get("label") or ""
        if not label:
            continue
        lset = set(label)
        score = len(tset & lset) / max(len(tset), 1)
        if score > best_score:
            best, best_score = node, score
    if best is not None and best_score >= 0.8:
        return best

    # 3) 检索兜底：命中块 → kp_ids → 节点
    try:
        res = st.retriever.search(term, top_k=3, apply_gate=False,
                                  exclude_roles=["exercise", "answer"])
        for hit in res.get("hits") or []:
            for kp in (getattr(hit, "kp_ids", None) or []):
                cand = next((n for n in st.nodes if n.get("kp_id") == kp), None)
                if cand:
                    return cand
    except Exception:
        pass
    return None


def kg_lookup(ctx: ToolContext, term: str = "", node_id: str = "", **_) -> ToolOutcome:
    st = ctx.state
    node = _locate(st, term, node_id)
    if not node:
        return ToolOutcome(ok=False, summary="图谱中未找到该知识点",
                           detail=f"「{term or node_id}」不在知识图谱中；可换用更短的术语，或先问概念本身。")
    neigh = st.neighbors(node["id"])
    prereq = st.prereq_chain(node["id"])
    lines = [f"{node.get('label')}（{node.get('tier')} · {node.get('chapter','')}）"]
    for n in neigh:
        other = n.get("node") or {}
        lines.append(f"  - [{REL_CN.get(n['rel'], n['rel'])}] {other.get('label','?')} {n.get('note','')}")
    if prereq:
        lines.append("前置复习路径：" + " → ".join(
            x["node"].get("label", "?") for x in prereq if x.get("node")))
    return ToolOutcome(
        summary=f"{node.get('label')} · {len(neigh)} 条关系 · 前置 {len(prereq)} 层",
        detail="\n".join(lines),
        artifact_type="graph",
        artifact_data={
            "focus": node, "neighbors": neigh, "prereq": prereq,
            "nodes": st.nodes[:400], "edges": st.edges[:600],
        },
        payload={"node": node, "neighbors": neigh, "prereq": prereq},
    )


TOOL = ToolSpec(
    name="kg_lookup",
    label="知识图谱查询 · {term}",
    description=(
        "在课程知识图谱中查询一个知识点的前置知识、易混淆对比、包含关系与因果邻居，"
        "并给出前置复习路径。学生问\"XX 要先学什么/和 YY 什么关系\"时调用。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "term": {"type": "string", "description": "知识点名称，如\"点堆动力学\"、\"缓发中子\""},            "node_id": {"type": "string", "description": "已知图谱节点 id（与 term 二选一）"},
        },
        "required": [],
    },
    run=kg_lookup,
)
