"""索引：BM25 稀疏通道 + hashing TF-IDF 稠密通道。

设计取舍（见 docs/04 D5）：语料规模在 1e3 量级，**不需要向量数据库**。
   · BM25：内存倒排（启动时从 chunk 文本重建，约 0.3s）
   · 稠密：hashing TF-IDF 投到 HASH_DIM 维，numpy 全量点积 < 10ms
   · 预留 Embedder 接口，接入真实 embedding 模型时只需替换 dense 通道
"""
from __future__ import annotations

import json
import math
import zlib
from collections import Counter
from pathlib import Path

import numpy as np

from ..config import HASH_DIM, INDEX_DIR
from ..contracts.models import Chunk
from .tokenize import tokenize


def _hash_bucket(tok: str, dim: int) -> tuple[int, float]:
    h = zlib.crc32(tok.encode("utf-8"))
    bucket = h % dim
    sign = 1.0 if (h >> 20) & 1 else -1.0
    return bucket, sign


def index_text(c: Chunk) -> str:
    """检索用文本 = 章节路径 + 正文。

    章节标题里往往就是最关键的术语（如「剖视图的基本概念」），
    只索引正文会让"剖视图的概念是什么"这类提问命中率明显偏低。
    """
    return (c.section + "\n" + c.text) if c.section else c.text


class Index:
    """可检索索引。"""

    def __init__(self, chunks: list[Chunk], vecs: np.ndarray, dim: int = HASH_DIM):
        self.chunks = chunks
        self.vecs = vecs
        self.dim = dim
        self.n = len(chunks)

        self.tfs: list[Counter] = []
        self.lens: list[int] = []
        self.df: Counter = Counter()
        for c in chunks:
            toks = tokenize(index_text(c))
            tf = Counter(toks)
            self.tfs.append(tf)
            self.lens.append(max(len(toks), 1))
            for t in tf:
                self.df[t] += 1
        self.avgdl = (sum(self.lens) / self.n) if self.n else 1.0
        self.idf = {
            t: math.log(1 + (self.n - f + 0.5) / (f + 0.5)) for t, f in self.df.items()
        }
        self.max_idf = max(self.idf.values()) if self.idf else 1.0

        # 桶级 idf（稠密通道用）
        bucket_df = np.zeros(dim, dtype=np.float32)
        for tf in self.tfs:
            seen = set()
            for t in tf:
                b, _ = _hash_bucket(t, dim)
                if b not in seen:
                    seen.add(b)
            for b in seen:
                bucket_df[b] += 1
        self.bucket_idf = np.log((self.n + 1) / (bucket_df + 1)).astype(np.float32) + 1.0

    # ------------------------------------------------------------ 构建

    @classmethod
    def build(cls, chunks: list[Chunk]) -> "Index":
        vecs = cls._encode_chunks(chunks, HASH_DIM)
        return cls(chunks, vecs, HASH_DIM)

    @staticmethod
    def _encode_chunks(chunks: list[Chunk], dim: int) -> np.ndarray:
        # 先统计 df 得到桶级 idf
        bucket_df = np.zeros(dim, dtype=np.float32)
        tfs: list[Counter] = []
        for c in chunks:
            tf = Counter(tokenize(index_text(c)))
            tfs.append(tf)
            for t in tf:
                b, _ = _hash_bucket(t, dim)
                bucket_df[b] += 1
        n = max(len(chunks), 1)
        idf = np.log((n + 1) / (bucket_df + 1)).astype(np.float32) + 1.0

        mat = np.zeros((len(chunks), dim), dtype=np.float32)
        for i, tf in enumerate(tfs):
            for t, f in tf.items():
                b, sign = _hash_bucket(t, dim)
                mat[i, b] += sign * (1.0 + math.log(f)) * idf[b]
        norms = np.linalg.norm(mat, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return mat / norms

    # ------------------------------------------------------------ 检索打分

    def bm25_scores(self, query: str, k1: float = 1.5, b: float = 0.75) -> np.ndarray:
        q = [t for t in tokenize(query) if t in self.idf]
        scores = np.zeros(self.n, dtype=np.float32)
        if not q:
            return scores
        for t in set(q):
            idf = self.idf[t]
            for i, tf in enumerate(self.tfs):
                f = tf.get(t, 0)
                if not f:
                    continue
                dl = self.lens[i]
                scores[i] += idf * (f * (k1 + 1)) / (
                    f + k1 * (1 - b + b * dl / self.avgdl)
                )
        return scores

    def encode_query(self, query: str) -> np.ndarray:
        vec = np.zeros(self.dim, dtype=np.float32)
        tf = Counter(tokenize(query))
        for t, f in tf.items():
            bkt, sign = _hash_bucket(t, self.dim)
            vec[bkt] += sign * (1.0 + math.log(f)) * self.bucket_idf[bkt]
        norm = float(np.linalg.norm(vec))
        return vec / norm if norm else vec

    def dense_scores(self, query: str) -> np.ndarray:
        if self.n == 0:
            return np.zeros(0, dtype=np.float32)
        return self.vecs @ self.encode_query(query)

    # ------------------------------------------------------------ 持久化

    def save(self, out_dir: Path | None = None) -> Path:
        out_dir = out_dir or INDEX_DIR
        out_dir.mkdir(parents=True, exist_ok=True)
        with (out_dir / "chunks.jsonl").open("w", encoding="utf-8") as f:
            for c in self.chunks:
                f.write(c.model_dump_json() + "\n")
        np.save(out_dir / "vecs.npy", self.vecs)
        (out_dir / "meta.json").write_text(
            json.dumps(
                {
                    "n": self.n,
                    "dim": self.dim,
                    "avgdl": self.avgdl,
                    "vocab": len(self.idf),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return out_dir

    @classmethod
    def load(cls, in_dir: Path | None = None) -> "Index":
        in_dir = in_dir or INDEX_DIR
        chunks: list[Chunk] = []
        with (in_dir / "chunks.jsonl").open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    chunks.append(Chunk.model_validate_json(line))
        vecs = np.load(in_dir / "vecs.npy")
        meta = json.loads((in_dir / "meta.json").read_text(encoding="utf-8"))
        return cls(chunks, vecs, int(meta.get("dim", HASH_DIM)))


def build_index(kb_chunks: list[Chunk]) -> Index:
    return Index.build(kb_chunks)
