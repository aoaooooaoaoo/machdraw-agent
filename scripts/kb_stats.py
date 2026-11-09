"""知识库/工程规模统计：给 README 与验收文档提供可复算的数字。

    python scripts/kb_stats.py            # 人类可读
    python scripts/kb_stats.py --json     # 机读 JSON
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KB = ROOT / "kb"

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def jl(p: Path) -> list[dict]:
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    kps = jl(KB / "knowledge" / "kp.jsonl")
    nodes = jl(KB / "graph" / "nodes.jsonl")
    edges = jl(KB / "graph" / "edges.jsonl")
    questions = jl(KB / "graph" / "questions.jsonl")
    figures = jl(KB / "figures" / "figures.jsonl")
    pairs = jl(KB / "figures" / "pairs.jsonl")
    exercises = jl(KB / "exercises" / "exercises.jsonl")

    stats = {
        "kp": len(kps),
        "kp_by_chapter": dict(Counter(k.get("chapter", "") for k in kps)),
        "nodes": len(nodes),
        "edges": len(edges),
        "edges_by_rel": dict(Counter(e.get("rel", "") for e in edges)),
        "questions": len(questions),
        "questions_by_layer": dict(Counter(str(q.get("layer", "")) for q in questions)),
        "figures": len(figures),
        "pairs": len(pairs),
        "exercises": len(exercises),
        "exercises_by_chapter": dict(Counter(e.get("chapter", "") for e in exercises)),
        "standards": len(list((KB / "standards").glob("*.md"))),
        "web": len(list((KB / "web").glob("*.md"))),
        "svg": len(list((KB / "figures").rglob("*.svg"))),
    }

    if args.json:
        print(json.dumps(stats, ensure_ascii=False, indent=2))
        return 0

    print("=" * 62)
    print("核反应堆物理 AI 助教 · 知识库规模")
    print("=" * 62)
    print(f"知识点      {stats['kp']:>4} 条")
    for ch, n in sorted(stats["kp_by_chapter"].items()):
        print(f"    {ch:<28} {n:>4}")
    print(f"图谱节点    {stats['nodes']:>4} 个")
    print(f"图谱边      {stats['edges']:>4} 条  {stats['edges_by_rel']}")
    print(f"问题链      {stats['questions']:>4} 条  layer={stats['questions_by_layer']}")
    print(f"教学图      {stats['figures']:>4} 张（SVG 文件 {stats['svg']} 个）")
    print(f"辨析对      {stats['pairs']:>4} 组")
    print(f"习题        {stats['exercises']:>4} 道")
    for ch, n in sorted(stats["exercises_by_chapter"].items()):
        print(f"    {ch:<28} {n:>4}")
    print(f"标准整理    {stats['standards']:>4} 份")
    print(f"拓展阅读    {stats['web']:>4} 份")
    print("=" * 62)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
