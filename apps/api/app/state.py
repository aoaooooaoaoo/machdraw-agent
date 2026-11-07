"""应用状态：一次性装载知识库、索引、知识图谱、数据库、模块注册表。"""
from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .config import GATE_TAU, INDEX_DIR, KB_DIR, SPARSE_WEIGHT
from .contracts.models import Chunk, ModuleManifest
from .db import Store
from .rag.chunking import load_kb
from .rag.index import Index, build_index
from .rag.retrieve import Retriever


# ------------------------------------------------------------------ 模块注册表
# 铁律：模块之间不互相 import；新增模块 = 加一个条目 + 前后端各一个目录。

MODULES: list[ModuleManifest] = [
    ModuleManifest(
        id="__global__", name="全局对话", icon="chat",
        canvas_kinds=["evidence"],
        tools=["kb_search", "kg_lookup", "tolerance_calc", "thread_calc", "arc_construct"],
        desc="统一提问入口，自动路由到合适的工具与模块",
        entry_examples=["内螺纹剖视图怎么画？", "Φ30 H7/k6 是什么配合？"],
    ),
    ModuleManifest(
        id="kbrag", name="国标与概念溯源", icon="book",
        canvas_kinds=["evidence"],
        tools=["kb_search", "kg_lookup"],
        system_prompt=(
            "课程知识库溯源助教：回答任何专业问题时必须先调用 kb_search 检索课程原文，"
            "把证据卡推上画布并逐条标注出处（文档·章节·条款/页码）。"
            "检索不到就如实说明“知识库未收录”，绝不用课程以外的知识补充。"
        ),
        desc="每句结论都能翻出原文出处",
        entry_examples=["剖视图和断面图的区别？", "表面结构 Ra 的含义"],
    ),
    ModuleManifest(
        id="tolerance", name="公差与配合侦探", icon="target",
        canvas_kinds=["tolerance"],
        tools=["tolerance_calc", "kb_search"],
        system_prompt=(
            "公差与配合侦探：先把配合代号解析成数值（由 tolerance_calc 工具确定性计算），"
            "再结合加工工艺与表面粗糙度解释。数值一律来自工具，不得自行推算或编造。"
        ),
        desc="输入 Φ30 H7/k6，解析配合类型、极限偏差与工艺",
        entry_examples=["Φ30 H7/k6", "Φ50 H8/f7 是什么配合"],
    ),
    ModuleManifest(
        id="coach", name="虚拟画图教练", icon="pencil",
        canvas_kinds=["coach"],
        tools=["arc_construct", "thread_calc"],
        system_prompt="画图教练：分步演示作图过程，每一步说明几何依据（找圆心→找切点→画弧）。",
        desc="圆弧连接、螺纹比例画法的分步演示",
        entry_examples=["外切圆弧连接怎么画", "M10 螺纹怎么画"],
    ),
    ModuleManifest(
        id="graph", name="知识图谱", icon="graph",
        canvas_kinds=["graph"],
        tools=["kg_lookup", "kb_search"],
        system_prompt="知识图谱助教：说明知识点之间的关系（前置依赖、易混淆对比）并给出课程出处。",
        desc="一核心两主线双分支的知识星图",
        entry_examples=["剖视图依赖哪些前置知识？", "截交线和相贯线怎么区分"],
    ),
    ModuleManifest(
        id="wrongbook", name="智能找茬与错题本", icon="alert",
        canvas_kinds=["annotation", "wrongbook"],
        tools=["wrongbook_crud", "kb_search", "quiz_from_kb"],
        system_prompt=(
            "错题诊断助教：按“原题→错误作答→根因→溯源→正解→避坑”六步拆解，"
            "根因归入概念混淆/公式误用/模型理解偏差/忽略边界条件/计算失误/其他。"
        ),
        desc="六步诊改，溯源回原文",
        entry_examples=["抽一道错题", "我的错题本"],
    ),
    ModuleManifest(
        id="projection", name="剖视与投影辨析", icon="layers",
        canvas_kinds=["comparison", "quiz"],
        tools=["kb_search", "quiz_from_kb"],
        system_prompt="投影辨析助教：给出成对图并让学生找出差异，不直接给答案。",
        desc="全剖/半剖/局部剖、截交线/相贯线对照辨析",
        entry_examples=["半剖和局部剖的区别", "相贯线常见错误"],
    ),
    ModuleManifest(
        id="feynman", name="形体重构与费曼追问", icon="mic",
        canvas_kinds=["annotation"],
        tools=["kb_search"],
        system_prompt=(
            "费曼追问：学生用自己的话复述时，你扮演只会追问的初学者——"
            "先找表述模糊点、再找逻辑跳跃，至少追问 3 轮，最后给对照评价与改进建议。"
        ),
        desc="讲给 Agent 听，讲不清楚就追问到底",
        entry_examples=["我来讲讲什么是剖视图"],
    ),
    ModuleManifest(
        id="sandbox3d", name="3D 可视化沙盒", icon="cube",
        canvas_kinds=["three_view"],
        tools=["projection_render", "section_render"],
        system_prompt="3D 沙盒助教：解释三视图投影关系（长对正、高平齐、宽相等）与剖切效果。",
        desc="3D 实体与 2D 三视图联动",
        entry_examples=["三视图的投影规律"],
    ),
]

MODULE_BY_ID = {m.id: m for m in MODULES}


@dataclass
class AppState:
    kb_dir: Path
    index: Index
    retriever: Retriever
    store: Store
    chunks: list[Chunk] = field(default_factory=list)
    nodes: list[dict] = field(default_factory=list)
    edges: list[dict] = field(default_factory=list)
    questions: list[dict] = field(default_factory=list)
    figures: list[dict] = field(default_factory=list)
    pairs: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    # ---------------- 图形
    def figures_for(self, kp_ids: list[str], chapter: str = "", limit: int = 2) -> list[dict]:
        """按知识点 id 或章名找相关教学图（figures.jsonl 里的 kp_ids / chapter）。"""
        out: list[dict] = []
        kpset = {k for k in (kp_ids or []) if k}
        for f in self.figures:
            hit = bool(kpset & set(f.get("kp_ids") or []))
            if not hit and chapter:
                hit = bool(f.get("chapter")) and str(f["chapter"])[:6] == chapter[:6]
            if hit:
                out.append(f)
            if len(out) >= limit:
                break
        return out

    # ---------------- 图谱查询
    def node(self, nid: str) -> dict | None:
        return next((n for n in self.nodes if n.get("id") == nid), None)

    def node_by_label(self, text: str) -> dict | None:
        text = text.strip()
        if not text:
            return None
        for n in self.nodes:
            if n.get("label") and (n["label"] == text or n["label"] in text):
                return n
        return None

    def neighbors(self, nid: str, rel: str | None = None) -> list[dict]:
        out = []
        for e in self.edges:
            if e.get("source") == nid or e.get("target") == nid:
                if rel and e.get("rel") != rel:
                    continue
                other = e["target"] if e.get("source") == nid else e.get("source")
                out.append({"id": other, "rel": e.get("rel"), "note": e.get("note", ""),
                            "node": self.node(other)})
        return out

    def prereq_chain(self, nid: str, depth: int = 4) -> list[dict]:
        seen, queue, out = {nid}, [(nid, 0)], []
        while queue:
            cur, d = queue.pop(0)
            if d >= depth:
                continue
            for e in self.edges:
                if e.get("rel") != "prereq":
                    continue
                if e.get("target") == cur and e.get("source") not in seen:
                    src = e["source"]
                    seen.add(src)
                    out.append({"id": src, "level": d + 1, "node": self.node(src), "note": e.get("note", "")})
                    queue.append((src, d + 1))
        return out


_lock = threading.Lock()
_state: AppState | None = None


def _jl(p: Path) -> list[dict]:
    """读 JSONL；坏行跳过而不炸整个启动。"""
    if not p.exists():
        return []
    out: list[dict] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def _load_graph(kb_dir: Path) -> tuple[list[dict], list[dict], list[dict], list[str]]:
    warns: list[str] = []

    gdir = kb_dir / "graph"
    nodes = _jl(gdir / "nodes.jsonl")
    edges = _jl(gdir / "edges.jsonl")
    questions = _jl(gdir / "questions.jsonl")
    if not nodes:
        warns.append("知识图谱未装载（kb/graph/nodes.jsonl 缺失或为空）")
    return nodes, edges, questions, warns


def load_state(kb_dir: Path | None = None, use_saved_index: bool = True) -> AppState:
    global _state
    with _lock:
        kb_dir = Path(kb_dir or KB_DIR)
        warnings: list[str] = []

        chunks: list[Chunk] = []
        index: Index | None = None
        if use_saved_index and (INDEX_DIR / "chunks.jsonl").exists():
            try:
                index = Index.load(INDEX_DIR)
                chunks = index.chunks
            except Exception as exc:  # 索引损坏就重建
                warnings.append(f"索引载入失败({type(exc).__name__})，已重建")

        if index is None:
            chunks = load_kb(kb_dir)
            index = build_index(chunks) if chunks else Index([], np.zeros((0, 4096), dtype=np.float32))

        if not chunks:
            warnings.append("知识库为空：kb/ 下没有可检索内容，请先运行 pipeline/build_kb.py")

        nodes, edges, questions, gw = _load_graph(kb_dir)
        warnings.extend(gw)

        figures = _jl(kb_dir / "figures" / "figures.jsonl")
        if not figures:
            warnings.append("教学图形库未装载（kb/figures/figures.jsonl 缺失或为空）")

        pairs = _jl(kb_dir / "figures" / "pairs.jsonl")

        store = Store()
        retriever = Retriever(index, sparse_weight=SPARSE_WEIGHT, gate_tau=GATE_TAU)

        _state = AppState(
            kb_dir=kb_dir, index=index, retriever=retriever, store=store,
            chunks=chunks, nodes=nodes, edges=edges, questions=questions,
            figures=figures, pairs=pairs, warnings=warnings,
        )
        return _state


def get_state() -> AppState:
    if _state is None:
        return load_state()
    return _state


def reset_state() -> None:
    global _state
    _state = None
