"""工具 wrongbook_crud：错题本读写（按账号隔离）。"""
from __future__ import annotations

from .base import ToolContext, ToolOutcome
from .spec import ToolSpec


def wrongbook_crud(ctx: ToolContext, action: str = "list",
                   record: dict | None = None, **_) -> ToolOutcome:
    st = ctx.state
    if action == "add" and record:
        wid = st.store.add_wrong(ctx.account, record)
        st.store.log_event(ctx.account, "wrongbook_add", {"id": wid})
        return ToolOutcome(
            summary="已存入错题本",
            detail=f"错题 {wid} 已记录",
            artifact_type="wrongbook",
            artifact_data={"added": wid, "items": st.store.list_wrong(ctx.account)},
            payload={"id": wid},
        )
    items = st.store.list_wrong(ctx.account)
    return ToolOutcome(
        summary=f"错题本共 {len(items)} 条",
        detail="\n".join(f"- {i['question'][:40]}" for i in items[:10]) or "错题本为空",
        artifact_type="wrongbook",
        artifact_data={"items": items},
        payload={"items": items},
    )


TOOL = ToolSpec(
    name="wrongbook_crud",
    label="错题本 · {action}",
    description=(
        "错题本读写：action=list 列出当前账号的错题；action=add 需要同时给 record 记录一条错题。"
        "学生问\"我的错题/易错题\"时调用。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["list", "add"], "default": "list",
                       "description": "list=列出错题，add=新增一条"},
            "record": {
                "type": "object",
                "description": "要记录的错题（action=add 时必填，如 question/answer/kp_ids 等字段）",
            },
        },
        "required": [],
    },
    run=wrongbook_crud,
)
