"""混合检索 + 知识边界门控。

两通道各自 min-max 归一后按 λ 融合（参考作品实测 λ=0.35；制图术语与符号密集，起步取 0.45）。
门控：对提问做 IDF 加权覆盖率检查，低于 τ 直接拒答——宁可说"知识库未收录"，也不编。

额外做了一步「短语加权」：检索本质是术语匹配，query 的核心词若在块里原样出现，
说明这块很可能就是讲这个的，给一个确定的加分，压掉「碰巧高频命中」的块。
"""
from __future__ import annotations

import numpy as np

from ..config import (
    COVERAGE_MODE,
    GATE_TAU,
    GATE_RARE_K,
    GATE_TAU_CHUNK,
    OOV_WEIGHT,
    RECALL_K,
    SPARSE_WEIGHT,
)
from ..contracts.models import Chunk, Evidence
from .index import Index, index_text
from .tokenize import content_tokens


def _minmax(x: np.ndarray) -> np.ndarray:
    if x.size == 0:
        return x
    lo, hi = float(x.min()), float(x.max())
    if hi - lo < 1e-9:
        return np.zeros_like(x)
    return (x - lo) / (hi - lo)


def keyword_coverage(
    query: str,
    docs_tokens: list[set[str]],
    idf: dict,
    max_idf: float,
    corpus_vocab: set[str] | None = None,
) -> float:
    """IDF 加权关键词覆盖率。

    · 生僻词权重高、常见词权重低；
    · 语料中完全不存在的**实义词**按 OOV_WEIGHT×max_idf 计权（它最能说明「这个问题超纲」）；
    · 纯虚词/疑问词（是什么、怎么、的、了）与单字不计入，否则课内问题会被误拒。

    两种判定口径：
      · docs  （默认）看「召回的这批块里有没有这个词」——精度高，但召回集只占语料一小部分；
      · corpus 看「全库是否收录这个词」——稳定，但语料越大越容易命中，门控会变松。
    """
    toks = content_tokens(query)
    if not toks:
        return 1.0     # 只有虚词的提问不做门控（让它走正常检索）

    if corpus_vocab is not None:
        present: set[str] = corpus_vocab
    else:
        present = set()
        for s in docs_tokens:
            present |= s

    total = 0.0
    covered = 0.0
    oov_w = max_idf * OOV_WEIGHT
    for t in toks:
        w = idf.get(t, oov_w)
        total += w
        if t in present:
            covered += w
    return covered / total if total else 0.0


class Retriever:
    def __init__(
        self,
        index: Index,
        sparse_weight: float = SPARSE_WEIGHT,
        gate_tau: float = GATE_TAU,
        allow_internal: bool = True,
        coverage_mode: str | None = None,
    ):
        self.index = index
        self.sparse_weight = sparse_weight
        self.gate_tau = gate_tau
        self.allow_internal = allow_internal
        self.coverage_mode = coverage_mode or COVERAGE_MODE
        self.gate_tau_chunk = GATE_TAU_CHUNK
        self._vocab: set[str] = set(index.idf.keys())
        self._texts: list[str] = [index_text(c) for c in index.chunks]

    def _phrase_boost(self, query: str) -> np.ndarray:
        """query 的核心词在块中原样出现 → 加分。权重按词长与 idf 递增。"""
        idx = self.index
        boost = np.zeros(idx.n, dtype=np.float32)
        terms = [t for t in content_tokens(query) if len(t) >= 2]
        if not terms:
            return boost
        for t in terms:
            w = 0.06 * min(len(t), 4) * (0.5 + idx.idf.get(t, idx.max_idf) / (idx.max_idf * 2))
            for i, txt in enumerate(self._texts):
                if t in txt:
                    boost[i] += w
        return boost

    def search(
        self,
        query: str,
        top_k: int = 6,
        roles: list[str] | None = None,
        recall_k: int = RECALL_K,
        apply_gate: bool = True,
        exclude_roles: list[str] | None = None,
    ) -> dict:
        idx = self.index
        if idx.n == 0:
            return {"hits": [], "coverage": 0.0, "gated": True, "reason": "索引为空"}

        bm25 = idx.bm25_scores(query)
        dense = idx.dense_scores(query)
        lam = self.sparse_weight
        fused = lam * _minmax(bm25) + (1.0 - lam) * _minmax(dense)
        fused = fused + self._phrase_boost(query)

        order = np.argsort(-fused)

        allow: list[int] = []
        # 习题/答案默认不进知识问答（OCR 题面噪声会污染证据）；显式给了 roles 时以 roles 为准
        excluded = set(exclude_roles or (() if roles else ("exercise", "answer")))
        for i in order:
            c = idx.chunks[i]
            if not self.allow_internal and c.internal_only:
                continue
            if roles and c.role.value not in roles:
                continue
            if excluded and c.role.value in excluded:
                continue
            allow.append(int(i))
            if len(allow) >= max(recall_k, top_k):
                break

        recall = allow[:recall_k]
        docs_tokens = [set(idx.tfs[i].keys()) for i in recall]
        vocab = self._vocab if self.coverage_mode == "corpus" else None
        coverage = keyword_coverage(
            query, docs_tokens, idx.idf, idx.max_idf, corpus_vocab=vocab
        )

        # 第二道信号：有没有**单独一块**真的吃下了这个问题。
        # 关键词覆盖率只回答「语料里有没有这些词」，语料一大就容易全命中；
        # 单块覆盖率回答「是不是有一段就是在讲这个」，能挡掉「词都在但没人讲」的提问。
        # （试过只取最稀有的 K 个词，反而更差：同义改写会让稀有词变成 OOV 而误判成超纲。）
        q_toks = content_tokens(query)
        best_chunk_cov = 0.0
        if q_toks:
            oov_w = idx.max_idf * OOV_WEIGHT
            total_w = sum(idx.idf.get(t, oov_w) for t in q_toks) or 1.0
            for i in allow[: min(len(allow), 10)]:
                toks_i = idx.tfs[i]
                got = sum(idx.idf.get(t, oov_w) for t in q_toks if t in toks_i)
                best_chunk_cov = max(best_chunk_cov, got / total_w)

        gated = apply_gate and (
            coverage < self.gate_tau or best_chunk_cov < self.gate_tau_chunk
        )

        hits: list[Evidence] = []
        for i in allow[:top_k]:
            c: Chunk = idx.chunks[i]
            hits.append(
                Evidence(
                    chunkId=c.chunk_id,
                    documentId=c.doc_id,
                    documentTitle=c.document_title,
                    category=c.category,
                    section=c.section,
                    score=round(min(float(fused[i]), 1.0), 4),
                    content=c.text,
                    snippet=c.text[:220],
                    kbNo=c.kb_no,
                    clause=c.clause,
                    page=c.page,
                    figureRefs=c.figure_refs,
                    kp_ids=list(c.kp_ids),
                )
            )
        return {
            "hits": hits,
            "coverage": round(coverage, 4),
            "chunk_coverage": round(best_chunk_cov, 4),
            "gated": bool(gated),
            "tau": self.gate_tau,
            "tau_chunk": self.gate_tau_chunk,
            "recall": len(recall),
        }

    # 供评测脚本直接调用
    def coverage_of(self, query: str) -> float:
        return self.search(query, top_k=3, apply_gate=False)["coverage"]


def build_retriever(chunks: list[Chunk], allow_internal: bool = True) -> Retriever:
    return Retriever(Index.build(chunks), allow_internal=allow_internal)
