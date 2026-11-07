"""端到端冒烟测试：不依赖 pytest，直接跑。

    D:\\桌面\\机械制图agent\\apps\\api\\.venv\\Scripts\\python.exe apps/api/tests/smoke.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

API = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API))

try:  # Windows 控制台默认 GBK，会把 ⌀/Ø 打崩
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from app.config import KB_DIR  # noqa: E402
from app.contracts.models import ChatMessage, ChatRequest  # noqa: E402
from app.rag.chunking import load_kb  # noqa: E402
from app.rag.index import build_index  # noqa: E402
from app.rag.retrieve import Retriever  # noqa: E402
from app.rag.symbols import extract_fit_spec, extract_thread_spec, normalize  # noqa: E402


def hr(t=""):
    print("\n" + "=" * 66)
    if t:
        print(t)
        print("=" * 66)


def test_symbols():
    hr("1) 符号规范化与代号抽取")
    cases = ["Φ30 H7/k6", "Ø30H7/k6", "内螺纹 M10×1.5 怎么画", "表面 Ra 3.2", "⌀20 H8/f7"]
    for c in cases:
        print(f"  {c!r:28} → norm={normalize(c)!r}")
        print(f"  {'':28}   fit={extract_fit_spec(c)} thread={extract_thread_spec(c)}")


def test_rag():
    hr("2) 切分 / 索引 / 检索 / 门控")
    chunks = load_kb(KB_DIR)
    print(f"  kb 目录 : {KB_DIR}")
    print(f"  分块数  : {len(chunks)}")
    if not chunks:
        print("  [!] kb/ 还没有内容，跳过检索测试（队友正在写语料）")
        return None
    idx = build_index(chunks)
    print(f"  词表    : {len(idx.idf)}   向量 {idx.vecs.shape}")
    r = Retriever(idx)
    for q in ["内螺纹剖视图怎么画", "三视图的投影规律", "铝合金焊接工艺参数怎么定"]:
        res = r.search(q, top_k=3)
        print(f"\n  Q: {q}")
        print(f"     coverage={res['coverage']:.3f}  gated={res['gated']}  hits={len(res['hits'])}")
        for h in res["hits"][:2]:
            print(f"     - {h.score:.3f} 《{h.documentTitle}》{h.section} | {h.snippet[:48]}")
    return idx


def test_tools():
    hr("3) 确定性工具")
    try:
        from app.domain.tolerance import parse_fit, solve_fit
    except ImportError:
        print("  [!] app/domain/tolerance.py 尚未就绪（domain-engines 正在写），跳过")
        return

    for spec in ["Φ30 H7/k6", "Φ30 f7", "Φ50 H7/h6"]:
        try:
            p = parse_fit(spec)
            r = solve_fit(p["phi"], p["hole"], p.get("shaft") or "h6")
            print(f"  {spec:14} → {r['fit']['type']:6} 孔 {r['hole']['ES']:+.3f}/{r['hole']['EI']:+.3f}"
                  f"  轴 {r['shaft']['es']:+.3f}/{r['shaft']['ei']:+.3f}")
        except Exception as exc:
            print(f"  {spec:14} → 出错：{type(exc).__name__}: {exc}")


async def test_chat():
    hr("4) 端到端对话（事件流）")
    from app.orchestrator import run_chat

    for q in ["内螺纹剖视图怎么画？", "Φ30 H7/k6 是什么配合？"]:
        print(f"\n  --- Q: {q} ---")
        counts: dict[str, int] = {}
        answer = []
        async for ev in run_chat(ChatRequest(messages=[ChatMessage(role="user", content=q)]), "smoke"):
            t = ev.type.value
            counts[t] = counts.get(t, 0) + 1
            if t == "thinking":
                print(f"    [think] {ev.text[:90]}")
            elif t == "tool_call":
                print(f"    [tool ] {ev.name}  {ev.label}")
            elif t == "tool_result":
                print(f"    [res  ] {ev.summary}")
            elif t == "artifact":
                print(f"    [card ] {ev.artifactType}  keys={list(ev.data)[:6]}")
            elif t == "token":
                answer.append(ev.text)
        print(f"    事件统计: {counts}")
        print("    回答:")
        for line in "".join(answer).splitlines()[:14]:
            print("      " + line)


def main() -> int:
    test_symbols()
    test_rag()
    test_tools()
    asyncio.run(test_chat())
    hr("完成")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
