"""习题库构建/校验：把 kb/exercises/exercises.jsonl 规范化并做质量过滤。

习题数据由人工整理 / 习题解答抽取而来（见 docs/01 语料盘点），本脚本负责：
  1. 逐行 JSON 解析，坏行报错但不炸流水线；
  2. 清洗题面：折叠空白、去掉题号前缀、去掉明显 OCR 噪声；
  3. 质量过滤：题面过短 / 中文占比过低（OCR 乱码）的丢弃并统计；
  4. 字段规范化（exercise_id / chapter / stem / book_page / qno / answer_page /
     model_page / source / internal_only）；
  5. 输出统计：按章分布、来源分布、丢弃原因。

用法：
    python pipeline/build_exercises.py [--in kb/exercises/exercises.jsonl] [--out ...]

**版权受限：全部 internal_only=true，仅限内部教研。**
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "kb" / "exercises" / "exercises.jsonl"

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

_CJK = re.compile(r"[\u4e00-\u9fff]")
_SPACE = re.compile(r"\s+")
# 题号前缀：「3.」「(2)」「p12.3」之类
_LEAD = re.compile(r"^(?:p?\d+\s*[.．]\s*\d*|\(\d+\)|第\s*\d+\s*题)\s*")


def clean(text: str) -> str:
    text = (text or "").replace("|", " ")
    text = _SPACE.sub(" ", text).strip()
    text = _LEAD.sub("", text).strip()
    return text


def quality(text: str) -> float:
    """中文占比；OCR 乱码的条目中文占比很低。"""
    if not text:
        return 0.0
    return len(_CJK.findall(text)) / max(len(text), 1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", default=str(SRC))
    ap.add_argument("--out", dest="out", default=str(SRC))
    args = ap.parse_args()

    src = Path(args.src)
    if not src.exists():
        print(f"[!] 找不到 {src}")
        return 1

    kept, dropped, bad = [], [], []
    for i, line in enumerate(src.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError as exc:
            bad.append((i, str(exc)))
            continue
        stem = clean(rec.get("stem") or "")
        if len(stem) < 8 or quality(stem) < 0.25:
            dropped.append((rec.get("exercise_id") or f"line{i}", len(stem), quality(stem)))
            continue
        out = {
            "exercise_id": str(rec.get("exercise_id") or f"EX-UNK-{i:03d}"),
            "chapter": str(rec.get("chapter") or "").strip(),
            "stem": stem[:400],
            "book_page": str(rec.get("book_page") or ""),
            "qno": str(rec.get("qno") or ""),
            "answer_page": str(rec.get("answer_page") or ""),
            "model_page": str(rec.get("model_page") or ""),
            "source": str(rec.get("source") or ""),
            "internal_only": True,
        }
        kept.append(out)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for rec in kept:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print("=" * 60)
    print(f"读入 {len(kept) + len(dropped) + len(bad)} 行 / 保留 {len(kept)} / 丢弃 {len(dropped)} / 坏行 {len(bad)}")
    if bad:
        print("坏行：", bad[:5])
    if dropped:
        print("丢弃样例：", dropped[:5])
    by_ch = Counter(r["chapter"] for r in kept)
    print("-" * 60)
    for ch, n in sorted(by_ch.items(), key=lambda kv: -kv[1]):
        print(f"  {n:3d}  {ch or '（未标章）'}")
    srcs = Counter(r["source"][:24] for r in kept)
    print("-" * 60)
    for s, n in srcs.most_common(8):
        print(f"  {n:3d}  {s}")
    print(f"写出 {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
