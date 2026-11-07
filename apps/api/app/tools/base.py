"""工具基元：上下文、结果与证据约束句。

历史调用方一直使用 ``from app.tools import ToolContext, ToolOutcome``；
本模块只是把这两个 dataclass 从包入口 `__init__.py` 拆出来，**对外导出位置与行为不变**，
但工具模块可以 ``from .base import ToolContext, ToolOutcome`` 直接引用，
避免在包初始化期间发生循环 import。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# 工具结果末尾固定的约束句（与参考作品线上实测一致，docs/05 §2.2）
EVIDENCE_CONSTRAINT = "引用时标注 chunk_id，只依据以上证据作答。"


@dataclass
class ToolContext:
    state: Any
    account: str = "anonymous"


@dataclass
class ToolOutcome:
    ok: bool = True
    summary: str = ""
    detail: str = ""
    artifact_type: str = ""
    artifact_data: dict = field(default_factory=dict)
    payload: dict = field(default_factory=dict)   # 给后续生成用的结构化信息


__all__ = ["ToolContext", "ToolOutcome", "EVIDENCE_CONSTRAINT"]
