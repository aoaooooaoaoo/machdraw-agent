"""工具 kg_lookup：知识图谱查询（前置/易混淆/包含/因果邻居 + 复习路径）。"""
from __future__ import annotations

from .base import ToolContext, ToolOutcome
from .spec import ToolSpec


def kg_lookup(ctx: ToolContext, term: str = "", node_id: str = "", **_) -> ToolOutcome:
    st = ctx.state
    node = st.node(node_id) if node_id else st.node_by_label(term)
    if not node:
        return ToolOutcome(ok=False, summary="图谱中未找到该知识点",
                           detail=f"「{term or node_id}」不在知识图谱中")
    neigh = st.neighbors(node["id"])
    prereq = st.prereq_chain(node["id"])
    lines = [f"{node.get('label')}（{node.get('tier')} · {node.get('chapter','')}）"]
    for n in neigh:
        other = n.get("node") or {}
        rel_cn = {"prereq": "前置", "contrast": "易混淆", "compose": "包含",
                  "cause": "导致"}.get(n["rel"], n["rel"])
        lines.append(f"  - [{rel_cn}] {other.get('label','?')} {n.get('note','')}")
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
            "term": {"type": "string", "description": "知识点名称，如\"尺寸标注\"、\"剖视图\""},
            "node_id": {"type": "string", "description": "已知图谱节点 id（与 term 二选一）"},
        },
        "required": [],
    },
    run=kg_lookup,
)
