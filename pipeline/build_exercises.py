"""把题库索引 CSV 转成可检索的习题条目（kb/exercises/exercises.jsonl）。

数据来源：docs/题库索引_习题集第6版_252题.csv（由解答册 PDF 书签解析 + OCR 得到）。
**版权受限，全部标 internal_only=true，仅限内部教研使用**（详见 docs/03 §6.5）。

OCR 题面有噪声，这里做质量过滤：
  · 去掉纯符号/过短/中文占比过低的；
  · 保留书名、章号、书页、题号，便于"错题溯源回原书"。
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "docs" / "题库索引_习题集第6版_252题.csv"
OUT = ROOT / "kb" / "exercises" / "exercises.jsonl"

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

_CJK = re.compile(r"[\u4e00-\u9fff]")
_SPACE = re.compile(r"\s+")


def clean(text: str) -> str:
    text = (text or "").replace("|", " ")
    text = _SPACE.sub(" ", text).strip()
    return text


def quality(text: str) -> float:
    """中文占比；OCR 乱码的条目中文占比很低。"""
    if not text:
        return 0.0
    return len(_CJK.findall(text)) / max(len(text), 1)


def main() -> int:
    if not SRC.exists():
        print(f"[!] 找不到 {SRC}")
        return 1
    rows = list(csv.DictReader(SRC.open(encoding="utf-8-sig")))
    print(f"读入 {len(rows)} 条")

    kept, dropped = [], 0
    for r in rows:
        stem = clean(r.get("题面_已校字") or "") or clean(r.get("题面_OCR") or "")
        stem = re.sub(r"^p?\d+\s*[.．]\s*\d*\s*", "", stem).strip()
        if len(stem) < 8 or quality(stem) < 0.30:
            dropped += 1
            continue
        kept.append({
            "exercise_id": r.get("exercise_id") or "",
            "chapter": clean(r.get("章节") or ""),
            "stem": stem[:300],
            "book_page": r.get("书页") or "",
            "qno": r.get("题号") or "",
            "answer_page": r.get("解答pdf页") or "",
            "model_page": r.get("模型pdf页") or "",
            "source": "《机械制图习题集》第6版（高教社，内部教研用）",
            "internal_only": True,
        })

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        for rec in kept:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"保留 {len(kept)} 条，丢弃 {dropped} 条（OCR 质量过低）")
    print(f"写出 {OUT}")
    by_ch = {}
    for rec in kept:
        by_ch[rec["chapter"][:12]] = by_ch.get(rec["chapter"][:12], 0) + 1
    for k, v in sorted(by_ch.items(), key=lambda x: -x[1]):
        print(f"  {v:3d}  {k}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
