"""给习题自动标注知识点（kp_ids）。

背景：题库来自扫描件，112 道题的 kp_ids 全是空，导致"题卡自评"只能写章级掌握度。
做法：同一章内，用习题题干 vs 知识点（term + aliases + definition + points）的
BM25 式词元重叠打分，取 top1（必要时 top2），写回 `kb/exercises/exercises.jsonl`。
这是离线、确定性的，不调用大模型，可重复运行。

用法：
    python scripts/annotate_exercise_kp.py            # 写回 + 备份
    python scripts/annotate_exercise_kp.py --dry-run  # 只看统计
"""
from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from app.rag.tokenize import tokenize  # noqa: E402


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def kp_text(kp: dict) -> str:
    parts = [kp.get("term", ""), " ".join(kp.get("aliases") or []),
             kp.get("definition", ""), " ".join(kp.get("points") or []),
             kp.get("section", "")]
    return "\n".join(p for p in parts if p)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    kp_path = ROOT / "kb" / "knowledge" / "kp.jsonl"
    ex_path = ROOT / "kb" / "exercises" / "exercises.jsonl"
    kps = load_jsonl(kp_path)
    exercises = load_jsonl(ex_path)

    by_chapter: dict[str, list[dict]] = {}
    for kp in kps:
        by_chapter.setdefault((kp.get("chapter") or "").strip(), []).append(kp)

    # 全局 IDF：让"反应性""温度系数"这类术语比"反应堆"更有区分度
    df: dict[str, int] = {}
    docs = [set(tokenize(kp_text(kp))) for kp in kps]
    for toks in docs:
        for t in toks:
            df[t] = df.get(t, 0) + 1
    N = max(1, len(docs))
    idf = {t: math.log(1 + N / (1 + c)) for t, c in df.items()}

    stats = {"total": len(exercises), "annotated": 0, "no_candidate": 0, "multi": 0}
    out: list[dict] = []
    for ex in exercises:
        chapter = (ex.get("chapter") or "").strip()
        candidates = by_chapter.get(chapter) or []
        if not candidates:
            stats["no_candidate"] += 1
            out.append({**ex, "kp_ids": []})
            continue
        stem_tokens = set(tokenize(ex.get("stem") or ""))
        stem_tokens = {t for t in stem_tokens if len(t) >= 2}
        scored: list[tuple[float, str]] = []
        for kp in candidates:
            kp_tokens = set(tokenize(kp_text(kp)))
            if not kp_tokens:
                continue
            hit = stem_tokens & kp_tokens
            if not hit:
                continue
            score = sum(idf.get(t, 1.0) for t in hit) / math.sqrt(len(stem_tokens) + 1)
            scored.append((score, kp["kp_id"]))
        scored.sort(reverse=True)
        picked: list[str] = []
        if scored and scored[0][0] > 0.8:
            picked = [scored[0][1]]
            if len(scored) > 1 and scored[1][0] >= scored[0][0] * 0.82:
                picked.append(scored[1][1])
        if picked:
            stats["annotated"] += 1
            if len(picked) > 1:
                stats["multi"] += 1
        out.append({**ex, "kp_ids": picked})

    print(json.dumps(stats, ensure_ascii=False))
    print("示例：")
    for ex in out[:5]:
        print(" ", ex.get("exercise_id"), "→", ex.get("kp_ids"))

    if args.dry_run:
        return
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = ROOT / "working" / f"_exercises_before_kp_{stamp}.jsonl"
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ex_path, backup)
    ex_path.write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in out) + "\n",
        encoding="utf-8",
    )
    print(f"已写回 {ex_path}（备份 {backup}）")


if __name__ == "__main__":
    main()
