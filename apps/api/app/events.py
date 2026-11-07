"""SSE 事件构造与序列化。

协议对照参考作品实测命名（docs/05 §2.2）：
    thinking / token / tool_call / tool_result / artifact / error / done + [DONE]
"""
from __future__ import annotations

import json
from typing import Any, Iterable

from .contracts.models import EventType, SSEEvent


def thinking(text: str, seq: int = 0) -> SSEEvent:
    return SSEEvent(type=EventType.thinking, seq=seq, text=text)


def token(text: str, seq: int = 0) -> SSEEvent:
    return SSEEvent(type=EventType.token, seq=seq, text=text)


def tool_call(call_id: str, name: str, label: str, args: dict, seq: int = 0) -> SSEEvent:
    return SSEEvent(
        type=EventType.tool_call, seq=seq, id=call_id, name=name, label=label, args=args
    )


def tool_result(call_id: str, summary: str, detail: str = "", seq: int = 0, name: str = "") -> SSEEvent:
    return SSEEvent(
        type=EventType.tool_result,
        seq=seq,
        id=call_id,
        name=name,
        summary=summary,
        detail=detail,
    )


def artifact(artifact_type: str, data: dict, seq: int = 0) -> SSEEvent:
    return SSEEvent(type=EventType.artifact, seq=seq, artifactType=artifact_type, data=data)


def error(code: str, message: str, seq: int = 0) -> SSEEvent:
    return SSEEvent(type=EventType.error, seq=seq, code=code, text=message)


def done(seq: int = 0, **extra: Any) -> SSEEvent:
    e = SSEEvent(type=EventType.done, seq=seq)
    if extra:
        e.data.update(extra)
    return e


def to_sse(ev: SSEEvent) -> str:
    """单帧 → SSE 文本。用 exclude_none 保持体积小。"""
    payload = ev.model_dump(exclude_none=True)
    # 去掉无关的空字段，前端只认有值的
    for k in ("text", "id", "name", "label", "args", "summary", "detail",
              "artifactType", "data", "code"):
        if k in payload and payload[k] in ("", {}, [], 0) and k not in ("type", "seq"):
            payload.pop(k, None)
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def encode_stream(events: Iterable[SSEEvent]) -> Iterable[str]:
    for ev in events:
        yield to_sse(ev)
    yield "data: [DONE]\n\n"


CHUNK_TOKEN_SIZE = 24


def split_for_stream(text: str, size: int = CHUNK_TOKEN_SIZE) -> list[str]:
    """把答案切成小段逐帧下发。参考作品是 1–2 字一帧（一次问答 1418 帧），这里取 24 字。"""
    return [text[i: i + size] for i in range(0, len(text), size)]
