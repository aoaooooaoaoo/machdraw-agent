"""端到端冒烟：装载 → 检索 → 编排 → SSE 事件流 → 画布 artifact。

    D:\\桌面\\教学agent\\核反应堆物理agent\\apps\\api\\.venv\\Scripts\\python.exe apps/api/tests/smoke.py

覆盖：
1. 启动装载：chunks / nodes / edges / figures / pairs / questions 非空，无 warning；
2. 检索：课内问题能命中且不被门控；课外问题被门控；
3. 对话：run_chat 的事件序列合法（thinking → ... → done），token 非空；
4. 画布：确定性工具能产出 calc / plot artifact；
5. 模块：9 个模块都能找到；feynman / wrongbook 专用链路可跑。
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "apps" / "api"))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from app.contracts.models import ChatMessage, ChatRequest  # noqa: E402
from app.orchestrator import run_chat  # noqa: E402
from app.state import MODULES, load_state  # noqa: E402

FAILS: list[str] = []


def check(cond: bool, label: str, detail: str = "") -> None:
    print(f"[{'PASS' if cond else 'FAIL'}] {label}" + (f"  {detail}" if detail else ""))
    if not cond:
        FAILS.append(label)


async def ask(q: str, feature: str | None = None) -> dict:
    req = ChatRequest(
        session_id="smoke",
        messages=[ChatMessage(role="user", content=q)],
        feature=feature,
    )
    events = []
    text = []
    async for ev in run_chat(req, "smoke"):
        events.append(ev.model_dump())
        if ev.type.value == "token":
            text.append(ev.text)
    return {"events": events, "answer": "".join(text),
            "types": [e["type"] for e in events],
            "artifacts": [e.get("artifactType") for e in events if e["type"] == "artifact"]}


def main() -> int:
    st = load_state()
    print("=" * 66)
    print("核反应堆物理 AI 助教 · 端到端冒烟")
    print("=" * 66)

    check(len(st.chunks) > 300, f"语料装载 {len(st.chunks)} 块")
    check(len(st.nodes) >= 120, f"知识图谱 {len(st.nodes)} 节点 / {len(st.edges)} 边")
    check(len(st.figures) >= 20, f"教学图库 {len(st.figures)} 张")
    check(len(st.pairs) >= 6, f"辨析对 {len(st.pairs)} 组")
    check(len(st.questions) >= 20, f"问题链 {len(st.questions)} 条")
    check(len(MODULES) == 10, f"模块注册表 {len(MODULES)} 个")
    for w in st.warnings:
        print(f"  [warn] {w}")

    # ---- 检索门控
    r = st.retriever.search("燃料温度系数为什么一定为负？", top_k=5)
    check(not r["gated"] and r["coverage"] > 0.4,
          "课内检索不被门控", f"coverage={r['coverage']:.2f}")
    r2 = st.retriever.search("股票市盈率怎么计算？", top_k=5)
    check(r2["gated"], "课外问题被门控", f"coverage={r2['coverage']:.2f}")

    # ---- 对话 + 画布
    cases = [
        ("什么是缓发中子？为什么它对反应堆控制很重要？", None, "evidence"),
        ("k∞=1.06、M2=180cm2 的单群裸堆临界曲率是多少？", "critical", "calc"),
        ("阶跃引入0.2$反应性，反应堆周期是多少？", "kinetics", "plot"),
        ("停堆后氙135浓度怎么变化？", "poison", "plot"),
        ("快群和热群有什么区别？", "concept", "comparison"),
        ("出两道核反应堆物理的题", "concept", "quiz"),
        ("点堆动力学依赖哪些前置知识？", "graph", "graph"),
        ("我来讲讲什么是六因子公式", "feynman", "annotation"),
        ("帮我看看这道错题：k_eff算成了无穷大", "wrongbook", "wrongbook"),
    ]
    seen = set()
    for q, feat, want in cases:
        res = asyncio.run(ask(q, feat))
        types = res["types"]
        ats = [a for a in res["artifacts"] if a]
        seen.update(ats)
        ok = (
            types[0] == "thinking"
            and types[-1] == "done"
            and "token" in types
            and bool(res["answer"].strip())
        )
        check(ok, f"对话链路「{q[:18]}…」", f"events={len(types)} artifacts={ats}")
        if want:
            check(want in ats, f"  产出 {want} 画布", f"实际 {ats}")

    need = {"evidence", "calc", "plot", "comparison", "quiz", "graph", "annotation", "wrongbook"}
    check(need <= seen, "8 类画布全部可达", f"缺 {sorted(need - seen)}")

    print("-" * 66)
    if FAILS:
        print(f"失败 {len(FAILS)} 项：{FAILS}")
        return 1
    print("全部通过。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
