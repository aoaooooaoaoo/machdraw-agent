"""探针评测：标定门控阈值 τ、检索权重 λ，并输出可写进方案的实测数字。

用法（服务端先起或直接跑本地索引）：
    python eval/run.py                     # 用本地 kb 直接评测
    python eval/run.py --sweep             # 扫 λ 与 τ
    python eval/run.py --write              # 把结果写入 eval/results/
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from app.config import KB_DIR  # noqa: E402
from app.rag.chunking import load_kb  # noqa: E402
from app.rag.index import build_index  # noqa: E402
from app.rag.retrieve import Retriever, keyword_coverage  # noqa: E402


def load_probes(name: str = "probes.jsonl") -> list[dict]:
    p = ROOT / "eval" / name
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.append(json.loads(line))
    return out


def evaluate(tau: float, lam: float, probes: list[dict], index, tau_chunk: float = 0.45) -> dict:
    r = Retriever(index, sparse_weight=lam, gate_tau=tau, coverage_mode="docs")
    r.gate_tau_chunk = tau_chunk
    rows = []
    for p in probes:
        res = r.search(p["q"], top_k=5)
        cov = res["coverage"]
        gated = res["gated"]
        titles = " ".join(h.documentTitle for h in res["hits"])
        doc_hit = True
        if p.get("expect_docs"):
            doc_hit = any(t in titles for t in p["expect_docs"])
        # 判对标准：课内(含 near)不拒答、课外必拒答。
        # 检索精度（期望文档是否进 top5）单独作为 doc_hit 报告，不混进 acc。
        if p["domain"] == "out":
            ok = gated
        else:
            ok = not gated
        rows.append({"id": p["id"], "domain": p["domain"], "q": p["q"],
                     "coverage": cov, "gated": gated, "ok": ok,
                     "doc_hit": doc_hit,
                     "top": res["hits"][0].documentTitle if res["hits"] else ""})
    n_in = sum(1 for r0 in rows if r0["domain"] == "in")
    n_out = sum(1 for r0 in rows if r0["domain"] == "out")
    n_near = sum(1 for r0 in rows if r0["domain"] == "near")
    in_cov = [r0["coverage"] for r0 in rows if r0["domain"] == "in"]
    out_cov = [r0["coverage"] for r0 in rows if r0["domain"] != "in"]
    acc = sum(1 for r0 in rows if r0["ok"]) / len(rows) if rows else 0.0
    hit = sum(1 for r0 in rows if r0["domain"] == "in" and r0["doc_hit"])
    return {
        "tau": tau, "lam": lam,
        "acc": round(acc, 4),
        "in_min": round(min(in_cov), 4) if in_cov else None,
        "out_max": round(max(out_cov), 4) if out_cov else None,
        "separation": round(min(in_cov) - max(out_cov), 4) if in_cov and out_cov else None,
        "in_recall": f"{sum(1 for r0 in rows if r0['domain']=='in' and not r0['gated'])}/{n_in}",
        "out_reject": f"{sum(1 for r0 in rows if r0['domain']=='out' and r0['gated'])}/{n_out}",
        "near_note": f"{sum(1 for r0 in rows if r0['domain']=='near' and not r0['gated'])}/{n_near}",
        "doc_hit": f"{hit}/{n_in}",
        "rows": rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sweep", action="store_true")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--tau", type=float, default=0.40)
    ap.add_argument("--lam", type=float, default=0.45)
    ap.add_argument("--probes", default="probes.jsonl", help="探针文件名（eval/ 下）")
    ap.add_argument("--tau-chunk", type=float, default=0.25)
    args = ap.parse_args()

    probes = load_probes(args.probes)
    if not probes:
        print("[!] eval/probes.jsonl 为空或不存在")
        return 1
    chunks = load_kb(KB_DIR)
    if not chunks:
        print("[!] kb/ 没有内容")
        return 1
    index = build_index(chunks)
    print(f"语料：{len(chunks)} 块 / {len({c.doc_id for c in chunks})} 文档 / 词表 {len(index.idf)}")
    print(f"探针：{len(probes)} 题\n")

    if args.sweep:
        best = None
        print(f"{'τ':>5} {'λ':>5} {'acc':>6} {'课内min':>8} {'课外max':>8} {'分离带':>8}  召回/拒答")
        for lam in (0.30, 0.35, 0.45, 0.55):
            for tau in (0.30, 0.35, 0.40, 0.45, 0.50, 0.55):
                res = evaluate(tau, lam, probes, index)
                sep = res["separation"]
                print(f"{tau:5.2f} {lam:5.2f} {res['acc']:6.3f} "
                      f"{str(res['in_min']):>8} {str(res['out_max']):>8} {str(sep):>8}  "
                      f"{res['in_recall']} {res['out_reject']}")
                key = (res["acc"], sep if sep is not None else -9)
                if best is None or key > best[0]:
                    best = (key, res)
        _, b = best
        print(f"\n最佳：τ={b['tau']} λ={b['lam']} acc={b['acc']} 分离带={b['separation']}")
        result = b
    else:
        result = evaluate(args.tau, args.lam, probes, index, args.tau_chunk)
        print(f"τ={result['tau']} λ={result['lam']} acc={result['acc']} "
              f"课内min={result['in_min']} 课外max={result['out_max']} 分离带={result['separation']}")
        print(f"课内召回 {result['in_recall']} · 课外拒答 {result['out_reject']}\n")
        print(f"{'id':6} {'域':5} {'cov':>6} {'gate':>5} {'ok':>4}  提问")
        for r in result["rows"]:
            flag = "✓" if r["ok"] else "✗"
            print(f"{r['id']:6} {r['domain']:5} {r['coverage']:6.3f} {str(r['gated']):>5} {flag:>4}  {r['q'][:36]}")

    if args.write:
        out = ROOT / "eval" / "results"
        out.mkdir(parents=True, exist_ok=True)
        import datetime
        name = out / f"run-{datetime.datetime.now():%Y%m%d-%H%M%S}.json"
        name.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n已写入 {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
