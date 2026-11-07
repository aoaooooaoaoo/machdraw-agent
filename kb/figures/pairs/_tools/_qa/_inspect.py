"""pairs.jsonl 快速体检：逐行打印 A/B 正确性、差异数、答案。"""
import io
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")
rows = [json.loads(l) for l in io.open("kb/figures/pairs.jsonl", encoding="utf-8")]
print("行数", len(rows), "| pair_id 唯一", len({r["pair_id"] for r in rows}) == len(rows))
for r in rows:
    q = r["question"]
    ans = q["options"][q["answer_index"]]
    print(f"{r['pair_id']:<26} A={r['a']['正确性']:<2} B={r['b']['正确性']:<2} "
          f"diff={len(r['differences'])} ans#{q['answer_index']} {ans[:24]}")
print("module", {r["module"] for r in rows}, "| license", {r["license"] for r in rows})
print("差异总数", sum(len(r["differences"]) for r in rows))
