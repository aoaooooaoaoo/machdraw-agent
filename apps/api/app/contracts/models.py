"""核心契约（单一事实源）。

所有模块、工具、前端类型都由本文件派生。改契约 = 改全项目。
参考作品实测协议见 docs/05-线上站点逆向观察.md，本文件按其实测命名对齐。
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------- 文档与分块


class DocRole(str, Enum):
    authority = "authority"   # 教材/自建知识条目（权威证据）
    standard = "standard"     # 国家标准
    curriculum = "curriculum" # 大纲/计划
    lecture = "lecture"       # 课件/讲义
    procedure = "procedure"   # 上机/实验指导
    exercise = "exercise"     # 习题/真题
    answer = "answer"         # 答案/解析（不进主索引）
    figure = "figure"         # 图块


class DocMeta(BaseModel):
    doc_id: str
    title: str
    category: str
    role: DocRole = DocRole.authority
    source: str = ""              # 来源说明（URL / 出版信息 / 自建）
    license: str = ""             # 许可与使用范围
    version: str = ""             # 国标版本，如 2003
    effective: bool = True


class Chunk(BaseModel):
    """一个可检索单元。chunk_id = chk_<doc_id>_<父块4位>_<子块4位>。"""

    chunk_id: str
    doc_id: str
    document_title: str
    category: str
    role: DocRole = DocRole.authority
    section: str = ""             # 章节路径，如 "第四章 中子扩散理论与计算 › 4.2.1 均匀裸堆的单群中子扩散方程计算"
    parent_id: str = ""
    text: str
    page: int | None = None
    slide: int | None = None
    kb_no: str = ""               # 标准号，如 GB/T 4960.1
    clause: str = ""              # 条款号
    version: str = ""
    figure_refs: list[str] = Field(default_factory=list)
    kp_ids: list[str] = Field(default_factory=list)
    bloom: str = ""
    internal_only: bool = False   # 版权受限，只内部使用


class Evidence(BaseModel):
    """检索命中的证据卡（前端证据溯源画布用）。"""

    chunkId: str
    documentId: str
    documentTitle: str
    category: str
    section: str
    score: float
    content: str
    snippet: str
    kbNo: str = ""
    clause: str = ""
    page: int | None = None
    figureRefs: list[str] = Field(default_factory=list)
    kp_ids: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------- 事件流

class EventType(str, Enum):
    thinking = "thinking"
    token = "token"
    tool_call = "tool_call"
    tool_result = "tool_result"
    artifact = "artifact"
    error = "error"
    done = "done"


class SSEEvent(BaseModel):
    type: EventType
    seq: int = 0
    # thinking / token
    text: str = ""
    # tool_call / tool_result
    id: str = ""
    name: str = ""
    label: str = ""
    args: dict[str, Any] = Field(default_factory=dict)
    summary: str = ""
    detail: str = ""
    # artifact
    artifactType: str = ""
    data: dict[str, Any] = Field(default_factory=dict)
    # error
    code: str = ""


# ---------------------------------------------------------------- 画布 artifact

ARTIFACT_TYPES = (
    "evidence",    # 证据溯源
    "comparison",  # 成对图辨析
    "annotation",  # 费曼三色标注 / 计算步骤标注
    "calc",        # 确定性计算卡（输入→公式→结果→校核）
    "plot",        # 曲线/分布图卡（能谱、响应、中毒曲线）
    "graph",       # 知识图谱
    "quiz",        # 题目
    "wrongbook",   # 错题
)


class Artifact(BaseModel):
    artifactType: str
    data: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------- 模块

class ModuleManifest(BaseModel):
    id: str
    name: str
    icon: str = ""
    canvas_kinds: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    system_prompt: str = ""
    entry_examples: list[str] = Field(default_factory=list)
    desc: str = ""


# ---------------------------------------------------------------- 请求/响应

class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class FeatureRef(BaseModel):
    """前端功能模块的身份：随每次请求带上，后端拼进系统提示词。

    参考作品（材料智能体）的做法：壳从 features/<名>/index.ts 读出来一起发，
    后端不需要维护模块表就能知道"现在在哪个模块、这个模块负责什么"。
    """
    id: str = ""
    title: str = ""
    persona: str = ""


class ChatRequest(BaseModel):
    session_id: str = "local"
    messages: list[ChatMessage] = Field(default_factory=list)
    # 既可传模块 key（兼容旧前端），也可传 {id,title,persona} 对象（参考作品契约）
    feature: str | FeatureRef | None = None
    model: str | None = None


class AuthRequest(BaseModel):
    account: str
    password: str = ""


class SourceRef(BaseModel):
    """四级出处：文档 · 章节 · 条款/页码 · chunk。"""

    label: str
    doc_title: str
    section: str = ""
    clause: str = ""
    page: int | None = None
    chunk_id: str = ""

    def render(self) -> str:
        parts = [f"《{self.doc_title}》"]
        if self.section:
            parts.append(self.section)
        if self.clause:
            parts.append(f"第{self.clause}条")
        elif self.page:
            parts.append(f"p{self.page}")
        return " · ".join(parts)
