"""回填教学图/辨析对的 kp_ids（图库作者只写术语，这里按 kp.jsonl 精确对齐）。

输入：
  kb/knowledge/kp.jsonl
  kb/figures/figures.jsonl + kb/figures/_link_terms.json      {figure_id: [术语...]}
  kb/figures/pairs.jsonl  + kb/figures/_pairs_link_terms.json {pair_id: [术语...]}
输出：原地重写 figures.jsonl / pairs.jsonl（kp_ids 填进去），并打印命中统计。

匹配规则（从严到宽）：
  1. KP 的 term 与目标术语完全相等；
  2. KP 的 aliases 里含该术语；
  3. KP 的 term/aliases 与术语互相包含（长度 ≥3 的才允许包含，避免"能谱"这种短词乱配）；
  4. 术语本身是 KP term 的子串且术语长度 ≥4。
每个图最多挂 4 个 kp_id，按匹配优先级去重。
"""
from __future__ import annotations

import json
import sys
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
    return [json.loads(ln) for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]


def dump(p: Path, rows: list[dict]) -> None:
    p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
                 encoding="utf-8")


def build_index(kps: list[dict]) -> list[tuple[str, str, str]]:
    """[(匹配键, kp_id, 来源)]，来源=term/alias。"""
    out = []
    for kp in kps:
        kid = kp.get("kp_id", "")
        term = (kp.get("term") or "").strip()
        if term:
            out.append((term, kid, "term"))
        for a in kp.get("aliases") or []:
            a = (a or "").strip()
            if a:
                out.append((a, kid, "alias"))
    return out


def match(terms: list[str], index: list[tuple[str, str, str]]) -> list[str]:
    """给一组术语找最匹配的 kp_id（最多 3 个，按匹配质量排序）。

    规则（从严到宽）：
      · 完全相等（term 优先于 alias）；
      · 互相包含，但**两边长度都 ≥3** 才算，避免"硼"配到一切含硼的词；
      · 短术语（1~2 字）只允许完全相等。
    """
    scored: dict[str, float] = {}
    for key, kid, src in index:
        for t in terms:
            t = (t or "").strip()
            if not t:
                continue
            if key == t:
                score = 3.0 if src == "term" else 2.6
            elif len(t) >= 3 and len(key) >= 3 and (t in key or key in t):
                score = 2.0 + min(len(t), len(key)) / 100.0
            else:
                continue
            if score > scored.get(kid, 0):
                scored[kid] = score
    ranked = sorted(scored.items(), key=lambda kv: -kv[1])
    return [kid for kid, _s in ranked[:3]]


def main() -> int:
    kps = jl(KB / "knowledge" / "kp.jsonl")
    index = build_index(kps)
    print(f"KP {len(kps)} 条 / 匹配键 {len(index)} 个")

    fig_terms = {}
    p = KB / "figures" / "_link_terms.json"
    if p.exists():
        fig_terms = json.loads(p.read_text(encoding="utf-8"))
    figs = jl(KB / "figures" / "figures.jsonl")
    fhit = 0
    for f in figs:
        terms = fig_terms.get(f.get("figure_id")) or []
        if not terms:
            terms = [f.get("title") or ""] + [t for t in (f.get("structure_tags") or [])]
        kp_ids = match([t for t in terms if t], index)
        if kp_ids:
            f["kp_ids"] = kp_ids
            fhit += 1
    dump(KB / "figures" / "figures.jsonl", figs)
    print(f"图 {len(figs)} 张，回填 {fhit} 张（0 张表示术语没对上，需人工看）")

    pair_terms_path = KB / "figures" / "_pairs_link_terms.json"
    pair_terms = json.loads(pair_terms_path.read_text(encoding="utf-8")) if pair_terms_path.exists() else {}
    pairs = jl(KB / "figures" / "pairs.jsonl")
    phit = 0
    for pr in pairs:
        terms = pair_terms.get(pr.get("pair_id")) or []
        if not terms:
            terms = [pr.get("title") or ""]
        kp_ids = match([t for t in terms if t], index)
        if kp_ids:
            pr["kp_ids"] = kp_ids
            phit += 1
    if pairs:
        dump(KB / "figures" / "pairs.jsonl", pairs)
    print(f"辨析对 {len(pairs)} 组，回填 {phit} 组")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
