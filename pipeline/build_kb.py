"""离线构建：装载 kb/ → 切分 → 建索引 → 落盘 data/index/。

用法：
    python pipeline/build_kb.py [--kb DIR] [--out DIR] [--stats]
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from app.config import INDEX_DIR, KB_DIR  # noqa: E402
from app.rag.chunking import load_kb  # noqa: E402
from app.rag.index import build_index  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kb", default=str(KB_DIR))
    ap.add_argument("--out", default=str(INDEX_DIR))
    args = ap.parse_args()

    kb_dir = Path(args.kb)
    chunks = load_kb(kb_dir)
    if not chunks:
        print(f"[!] {kb_dir} 下没有可检索内容（需要 kb/**/*.md 或 kb/knowledge/kp.jsonl）")
        return 1

    idx = build_index(chunks)
    out = idx.save(Path(args.out))

    by_doc = Counter(c.doc_id for c in chunks)
    by_role = Counter(c.role.value for c in chunks)
    by_cat = Counter(c.category for c in chunks)
    lens = [len(c.text) for c in chunks]

    print("=" * 60)
    print(f"分块总数 : {len(chunks)}")
    print(f"文档数   : {len(by_doc)}")
    print(f"词表大小 : {len(idx.idf)}")
    print(f"平均长度 : {sum(lens)/len(lens):.0f} 字  (min {min(lens)} / max {max(lens)})")
    print(f"向量矩阵 : {idx.vecs.shape}  {idx.vecs.nbytes/1e6:.1f} MB")
    print("-" * 60)
    print("按分类 :", dict(by_cat))
    print("按角色 :", dict(by_role))
    print("按文档 :", dict(by_doc.most_common(20)))
    print("-" * 60)
    print(f"索引已写入 {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
