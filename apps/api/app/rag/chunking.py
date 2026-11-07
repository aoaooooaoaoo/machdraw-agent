"""知识库装载与切分。

四套切分器（对照 docs/04 §6）：
  · MarkdownSplitter   —— 教材/讲义/资料：`##` = 父块（节），段内合并到子块
  · KnowledgeSplitter  —— kp.jsonl 知识条目：一章 = 父块，一条 = 子块
  · ExerciseSplitter   —— 习题：一题一块；答案单独索引
  · (StandardSplitter  —— 国标：按条款切，前端 Markdown 里用 `### 5.1` 表达)

chunk_id 规范：chk_<doc_id>_<父块4位>_<子块4位>
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from ..config import KB_DIR, MAX_CHUNK_CHARS, MIN_CHUNK_CHARS
from ..contracts.models import Chunk, DocRole

_FM_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.S)


def parse_front_matter(text: str) -> tuple[dict, str]:
    m = _FM_RE.match(text)
    if not m:
        return {}, text
    meta: dict = {}
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if v.lower() in ("true", "false"):
            meta[k] = v.lower() == "true"
        else:
            meta[k] = v
    return meta, text[m.end():]


def _mk_id(doc_id: str, parent: int, child: int) -> str:
    return f"chk_{doc_id}_{parent:04d}_{child:04d}"


def _merge_paragraphs(paras: list[str]) -> list[str]:
    """把短段合并成 MIN–MAX 字的子块，避免大量"半句话块"。"""
    out: list[str] = []
    buf = ""
    for p in paras:
        p = p.strip()
        if not p:
            continue
        if not buf:
            buf = p
        elif len(buf) + len(p) + 1 <= MAX_CHUNK_CHARS:
            buf += "\n" + p
        else:
            out.append(buf)
            buf = p
        # 单段就超长：按句号切
        while len(buf) > MAX_CHUNK_CHARS:
            cut = max(buf.rfind("。", 0, MAX_CHUNK_CHARS), buf.rfind("；", 0, MAX_CHUNK_CHARS))
            if cut < MIN_CHUNK_CHARS:
                cut = MAX_CHUNK_CHARS
            out.append(buf[: cut + 1])
            buf = buf[cut + 1:].strip()
    if buf:
        out.append(buf)
    return [c for c in out if len(c) >= MIN_CHUNK_CHARS // 2]


def chunk_markdown(meta: dict, body: str) -> list[Chunk]:
    doc_id = meta.get("doc_id") or "DOC"
    title = meta.get("title") or doc_id
    category = meta.get("category") or "参考资料"
    try:
        role = DocRole(meta.get("role") or "authority")
    except ValueError:
        role = DocRole.authority
    internal = bool(meta.get("internal_only", False))
    version = str(meta.get("version") or "")

    chunks: list[Chunk] = []
    parent_idx = -1
    cur_parent_title = ""
    cur_paras: list[str] = []
    h1 = ""

    def flush() -> None:
        nonlocal cur_paras
        if parent_idx < 0:
            cur_paras = []
            return
        pid = _mk_id(doc_id, parent_idx, 0).rsplit("_", 1)[0]
        for ci, text in enumerate(_merge_paragraphs(cur_paras)):
            chunks.append(
                Chunk(
                    chunk_id=_mk_id(doc_id, parent_idx, ci),
                    doc_id=doc_id,
                    document_title=title,
                    category=category,
                    role=role,
                    section=" › ".join(x for x in (h1, cur_parent_title) if x),
                    parent_id=pid,
                    text=text,
                    version=version,
                    internal_only=internal,
                )
            )
        cur_paras = []

    for raw in body.splitlines():
        line = raw.rstrip()
        if line.startswith("### "):
            cur_paras.append("\n**" + line[4:].strip() + "**")
        elif line.startswith("## "):
            flush()
            parent_idx += 1
            cur_parent_title = line[3:].strip()
        elif line.startswith("# "):
            flush()
            parent_idx += 1
            h1 = line[2:].strip()
            cur_parent_title = h1
        else:
            cur_paras.append(line)
    flush()
    return chunks


def chunk_knowledge(path: Path) -> list[Chunk]:
    """kp.jsonl → 一章一个父块，一条知识点一个子块。"""
    by_chapter: dict[str, list[dict]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        by_chapter.setdefault(rec.get("chapter") or "未分章", []).append(rec)

    chunks: list[Chunk] = []
    for pi, (chapter, recs) in enumerate(sorted(by_chapter.items())):
        for ci, rec in enumerate(recs):
            parts = [f"**{rec.get('term','')}**：{rec.get('definition','')}"]
            for p in rec.get("points") or []:
                parts.append(f"· {p}")
            for p in rec.get("common_mistakes") or []:
                parts.append(f"⚠ 易错：{p}")
            text = "\n".join(x for x in parts if x.strip())
            if not text.strip():
                continue
            chunks.append(
                Chunk(
                    chunk_id=_mk_id("KP", pi, ci),
                    doc_id="KP",
                    document_title="机械制图知识点手册（自建）",
                    category="教材",
                    role=DocRole.authority,
                    section=" › ".join(x for x in (chapter, rec.get("section", "")) if x),
                    parent_id=_mk_id("KP", pi, 0).rsplit("_", 1)[0],
                    text=text,
                    kp_ids=[rec.get("kp_id", "")],
                    bloom=rec.get("bloom", ""),
                )
            )
    return chunks


def chunk_exercises(path: Path) -> list[Chunk]:
    """习题 jsonl → 一题一块（答案不进主索引）。"""
    chunks: list[Chunk] = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        q = (rec.get("stem") or rec.get("题面") or "").strip()
        if not q:
            continue
        chunks.append(
            Chunk(
                chunk_id=_mk_id("EX", i, 0),
                doc_id="EX",
                document_title="机械制图习题（内部）",
                category="习题",
                role=DocRole.exercise,
                section=rec.get("chapter", ""),
                parent_id=_mk_id("EX", i, 0).rsplit("_", 1)[0],
                text=q,
                kp_ids=rec.get("kp_ids") or [],
                internal_only=True,
            )
        )
    return chunks


def load_kb(kb_dir: Path | None = None) -> list[Chunk]:
    """扫描 kb/ 装载全部可检索分块。"""
    kb_dir = kb_dir or KB_DIR
    chunks: list[Chunk] = []
    if not kb_dir.exists():
        return chunks

    for p in sorted(kb_dir.rglob("*.md")):
        if p.name.lower() in ("readme.md",):
            continue
        try:
            meta, body = parse_front_matter(p.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError):
            continue
        if not meta.get("doc_id"):
            meta["doc_id"] = p.stem.upper().replace("-", "_")[:24]
        chunks.extend(chunk_markdown(meta, body))

    kp = kb_dir / "knowledge" / "kp.jsonl"
    if kp.exists():
        chunks.extend(chunk_knowledge(kp))

    ex_dir = kb_dir / "exercises"
    if ex_dir.exists():
        for p in sorted(ex_dir.glob("*.jsonl")):
            if "answer" in p.stem:
                continue
            chunks.extend(chunk_exercises(p))

    return chunks
