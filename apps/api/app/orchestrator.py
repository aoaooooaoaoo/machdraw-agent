"""ReAct 编排：把一次提问变成一条事件流。

无 API Key 时走"本地规则编排 + 抽取式作答"（provider=mock）：
   1. 先跑确定性工具（临界/点堆/中毒/燃耗/反应性/能谱），因为这些能算准；
   2. 再检索知识库拿证据（带门控）；
   3. 最后由 llm.generate 组织语言（mock 模式下是抽取式，不编造）。

有 API Key 时同一套骨架换成模型决策，工具调用与事件协议不变。
"""
from __future__ import annotations

import re
import time
import uuid
from typing import AsyncIterator

from . import events as E
from . import llm
from .contracts.models import ChatRequest, EventType, SSEEvent
from .state import MODULE_BY_ID, get_state
from .tools import TOOLS, ToolContext, call

# ---- 路由关键词（核反应堆物理）
CRITICAL_WORDS = ("临界", "k_eff", "keff", "k∞", "kinf", "增殖系数", "曲率", "扩散方程",
                  "临界尺寸", "不泄漏", "反射层", "外推", "单群", "双群", "四因子", "六因子")
KIN_WORDS = ("周期", "缓发", "瞬发", "点堆", "倒时", "阶跃", "功率响应", "反应堆周期")
REAC_WORDS = ("反应性", "温度系数", "空泡系数", "功率系数", "功率亏损", "pcm", "mk", "$",
              "反应性系数", "控制棒价值", "硼")
POISON_WORDS = ("氙", "碘", "钐", "中毒", "碘坑", "振荡", "裂变产物")
BURN_WORDS = ("燃耗", "寿期", "卸料", "循环长度", "mwd", "tu", "转化比", "换料")
SPECTRUM_WORDS = ("能谱", "群常数", "群截面", "1/e", "费米谱", "麦克斯韦", "热谱",
                  "裂变谱", "谱硬化", "自屏")
CONCEPT_WORDS = ("区别", "辨析", "对比", "区分", "异同", "怎么分辨")
GRAPH_WORDS = ("关系", "前置", "先学", "知识点", "依赖", "学习路径", "图谱", "易混淆")
QUIZ_WORDS = ("出题", "考考我", "来一道", "练一练", "做道题", "来几道",
              "出两道", "出几道", "出个题", "给我出", "做题", "练习一下")
WRONG_WORDS = ("错题", "错题本", "易错")
# 「出两道题」「给我来几道题」这类口语说法
QUIZ_PAT = re.compile(r"(出|来|给|做|练)[^。？！?]{0,6}(道|个)?[^。？！?]{0,2}题")


def _has(text: str, words: tuple[str, ...]) -> bool:
    low = text.lower()
    return any(w in low for w in words)


def _looks_numeric(q: str) -> bool:
    """题面里是否给了可计算的条件（数值+单位/等式）——用于区分"辨析"与"计算"。"""
    return bool(re.search(
        r"[=＝]\s*[-+]?\d|\d+(?:\.\d+)?\s*(?:cm|pcm|mk|mwd|mev|kev|ev|k\b|℃|%|\$)",
        q, re.I))


def _plan(query: str, feature: str | None) -> list[dict]:
    """决定要调哪些工具。返回 [{name, args, label}]。"""
    steps: list[dict] = []
    q = query.strip()

    # 这两类由 run_chat 里的专用教学流程接管，不在这里排工具
    if feature == "feynman":
        return []
    if (feature == "wrongbook"
            and not _has(q, QUIZ_WORDS)
            and not _has(q, ("我的错题", "错题本", "列表", "有哪些"))):
        return []

    # ---- 图谱查询优先于计算路由（"点堆动力学依赖哪些前置知识"不是计算题）
    if feature == "graph" or (_has(q, GRAPH_WORDS) and not _looks_numeric(q)
                              and feature != "concept"):
        m = re.search(r"([\u4e00-\u9fff]{2,10})\s*(?:和|与|跟|vs)\s*([\u4e00-\u9fff]{2,10})", q)
        term = m.group(1) if m else q[:12]
        steps.append({"name": "kg_lookup", "args": {"term": term}})
        steps.append({"name": "kb_search", "args": {"query": q, "top_k": 6}})
        return steps

    # ---- 概念辨析（有数值条件时不算辨析题）
    if (feature == "concept" or _has(q, CONCEPT_WORDS)) and not _looks_numeric(q):
        steps.append({"name": "comparison_pick", "args": {"query": q}})

    # ---- 确定性计算：按"问的是什么"路由
    if not steps or all(s["name"] == "comparison_pick" for s in steps):
        if _has(q, KIN_WORDS) or (feature == "kinetics" and not _has(q, REAC_WORDS)):
            steps.append({"name": "kinetics_calc", "args": {"query": q}})
        elif _has(q, REAC_WORDS) or feature == "kinetics":
            steps.append({"name": "reactivity_calc", "args": {"query": q}})
        elif _has(q, POISON_WORDS):
            steps.append({"name": "poison_calc", "args": {"query": q}})
        elif _has(q, BURN_WORDS) or feature == "poison":
            steps.append({"name": "burnup_calc", "args": {"query": q}})
        elif _has(q, SPECTRUM_WORDS) or feature == "critical":
            if _has(q, CRITICAL_WORDS) or feature == "critical":
                steps.append({"name": "critical_calc", "args": {"query": q}})
            else:
                steps.append({"name": "spectrum_plot", "args": {"query": q}})
        elif _has(q, CRITICAL_WORDS):
            steps.append({"name": "critical_calc", "args": {"query": q}})
        elif _has(q, SPECTRUM_WORDS):
            steps.append({"name": "spectrum_plot", "args": {"query": q}})

    # ---- 出题 / 错题
    if _has(q, QUIZ_WORDS) or QUIZ_PAT.search(q):
        steps.append({"name": "quiz_from_kb", "args": {"topic": q, "n": 2}})
    if _has(q, WRONG_WORDS):
        steps.append({"name": "wrongbook_crud", "args": {"action": "list"}})

    # 检索永远兜底
    steps.append({"name": "kb_search", "args": {"query": q, "top_k": 6}})
    return steps


def _tool_label(name: str, args: dict) -> str:
    from .tools import TOOL_LABELS

    base = TOOL_LABELS.get(name, name)
    if name == "kb_search":
        return f"{base} ·「{args.get('query','')}」"
    if name in ("critical_calc", "kinetics_calc", "poison_calc",
                "burnup_calc", "reactivity_calc", "spectrum_plot"):
        return f"{base} ·「{(args.get('query') or '')[:36]}」"
    if name == "kg_lookup":
        return f"{base} ·「{args.get('term','')}」"
    return base


# ------------------------------------------------------------------ 模板作答
# 确定性工具命中时，用结构化模板作答（不经过模型，保证数值零误差）。

def _fmt(v) -> str:
    if isinstance(v, float):
        if v == 0:
            return "0"
        if abs(v) >= 1e5 or abs(v) < 1e-3:
            return f"{v:.4e}"
        return f"{v:.6g}"
    return str(v)


def _render_calc(d: dict) -> str:
    """渲染 calc 画布数据（输入 → 公式 → 结果 → 校核）。"""
    lines = [f"**{d.get('title') or '确定性计算'}**", ""]
    inputs = d.get("inputs") or []
    if inputs:
        lines.append("**输入**")
        lines.append("")
        lines.append("| 量 | 取值 | 单位 |")
        lines.append("|---|---|---|")
        for it in inputs:
            lines.append(f"| {it.get('name','')} | {_fmt(it.get('value',''))} | {it.get('unit','')} |")
        lines.append("")
    formulas = d.get("formulas") or d.get("steps") or []
    if formulas:
        lines.append("**计算步骤**")
        lines.append("")
        for i, f in enumerate(formulas, 1):
            if isinstance(f, dict):
                expr = f.get("step") or f.get("expr") or f.get("formula") or ""
                note = f.get("note") or f.get("desc") or ""
                lines.append(f"{i}. `{expr}`" + (f"　—　{note}" if note else ""))
            else:
                lines.append(f"{i}. {f}")
        lines.append("")
    results = d.get("results") or []
    if results:
        lines.append("**结果**")
        lines.append("")
        lines.append("| 量 | 数值 | 单位 | 说明 |")
        lines.append("|---|---|---|---|")
        for it in results:
            lines.append(
                f"| {it.get('name','')} | {_fmt(it.get('value',''))} | {it.get('unit','')} | {it.get('note','')} |"
            )
        lines.append("")
    verdict = d.get("verdict") or {}
    if verdict:
        lines.append(f"**结论**：{verdict.get('level','')}　{verdict.get('note','')}")
        lines.append("")
    if d.get("note"):
        lines.append(f"> {d['note']}")
        lines.append("")
    refs = d.get("refs") or []
    if refs:
        lines.append("**依据**：" + "；".join(refs))
    return "\n".join(lines).strip()


def _render_plot(d: dict) -> str:
    lines = [f"**{d.get('title') or '曲线'}**", ""]
    series = d.get("series") or []
    for s in series:
        pts = s.get("points") or []
        if pts:
            lines.append(f"- **{s.get('name','曲线')}**：{len(pts)} 个采样点，"
                         f"首点 ({_fmt(pts[0][0])}, {_fmt(pts[0][1])})，"
                         f"末点 ({_fmt(pts[-1][0])}, {_fmt(pts[-1][1])})")
    if series:
        lines.append("")
    results = d.get("results") or []
    if results:
        lines.append("**关键结果**")
        lines.append("")
        lines.append("| 量 | 数值 | 单位 | 说明 |")
        lines.append("|---|---|---|---|")
        for it in results:
            lines.append(
                f"| {it.get('name','')} | {_fmt(it.get('value',''))} | {it.get('unit','')} | {it.get('note','')} |"
            )
        lines.append("")
    if d.get("note"):
        lines.append(f"> {d['note']}")
        lines.append("")
    refs = d.get("refs") or []
    if refs:
        lines.append("**依据**：" + "；".join(refs))
    return "\n".join(lines).strip()


def _answer_from_tool(query: str, name: str, outcome, hits: list[dict], coverage: float) -> str:
    """确定性工具命中时，用结构化模板作答（不经过模型，保证数值零误差）。"""
    at = outcome.artifact_type or ""
    d = outcome.artifact_data or {}

    if at == "calc" and d:
        return _render_calc(d)
    if at == "plot" and d:
        return _render_plot(d)

    if name == "comparison_pick" and outcome.ok:
        p = outcome.payload.get("pair") or {}
        lines = [f"**{p.get('title')}**", ""]
        a, b = p.get("a") or {}, p.get("b") or {}
        lines.append(f"- **A**：{a.get('caption','')}（{a.get('正确性','')}）")
        lines.append(f"- **B**：{b.get('caption','')}（{b.get('正确性','')}）")
        lines.append("")
        lines.append("**关键差异**：")
        for diff in p.get("differences") or []:
            lines.append(f"{diff.get('no')}. **{diff.get('name')}**——A {diff.get('a_desc','')}；"
                         f"B {diff.get('b_desc','')}。{diff.get('why','')}")
        qn = p.get("question") or {}
        if qn.get("stem"):
            lines += ["", f"**随堂一问**：{qn['stem']}", ""]
            for i, opt in enumerate(qn.get("options") or []):
                lines.append(f"  {'ABCD'[i]}. {opt}")
            lines.append("")
            lines.append("> 先自己选，再在画布上点确认——答案不在这里给。")
        return "\n".join(lines)

    if name == "quiz_from_kb" and outcome.ok:
        qs = outcome.payload.get("questions") or []
        lines = [f"**给你 {len(qs)} 道题**（答案先不下发）", ""]
        for i, qd in enumerate(qs, 1):
            stem = (qd.get("content") or "").replace("\n", " ")
            lines.append(f"{i}. {stem[:160]}")
            lines.append(f"   —— 出处：《{qd.get('documentTitle','')}》· {qd.get('section','')}")
        lines += ["", "> 想好了再说，或者点题卡上的「我先想想」看解析。"]
        return "\n".join(lines)

    if name == "kg_lookup" and outcome.ok:
        p = outcome.payload
        node = p["node"]
        lines = [f"**{node.get('label')}**（{node.get('chapter','')}）", ""]
        contra = [n for n in p["neighbors"] if n.get("rel") == "contrast"]
        pre = [n for n in p["neighbors"] if n.get("rel") == "prereq"]
        if pre:
            lines.append("**前置知识**：")
            lines += [f"- {n['node'].get('label','?')}：{n.get('note','')}" for n in pre if n.get("node")]
            lines.append("")
        if contra:
            lines.append("**易混淆对比**：")
            lines += [f"- {n['node'].get('label','?')}：{n.get('note','')}" for n in contra if n.get("node")]
            lines.append("")
        if p.get("prereq"):
            lines.append("**建议先复习**：" + " → ".join(
                x["node"].get("label", "?") for x in p["prereq"][:5] if x.get("node")))
        return "\n".join(lines)

    # 兜底：证据抽取
    return llm.mock_answer(query, hits, gated=coverage < 0.40, coverage=coverage)


async def run_chat(req: ChatRequest, account: str = "anonymous") -> AsyncIterator[SSEEvent]:
    st = get_state()
    ctx = ToolContext(state=st, account=account)
    t0 = time.time()
    seq = 0

    msgs = [m for m in req.messages if m.role == "user"]
    query = (msgs[-1].content if msgs else "").strip()
    if not query:
        yield E.error("EMPTY_QUERY", "没有收到问题")
        yield E.done(seq=seq)
        return

    # 模块身份：前端随请求发 {id,title,persona}，后端拼进系统提示词。
    fref = req.feature
    persona_block = ""
    if isinstance(fref, str):
        feature = fref
    elif fref is not None:
        feature = fref.id or None
        if fref.title or fref.persona:
            persona_block = f"【当前模块】{fref.title or feature}"
            if fref.persona:
                persona_block += f"\n【模块职责】{fref.persona}"
    else:
        feature = None
    mod = MODULE_BY_ID.get(feature or "__global__")
    if not persona_block and mod is not None:
        persona_block = f"【当前模块】{mod.name}"
        if getattr(mod, "system_prompt", ""):
            persona_block += f"\n【模块职责】{mod.system_prompt}"
    seq += 1
    yield E.thinking(
        f"学生提问：{query}。"
        f"{'当前模块：' + mod.name + '。' if mod else ''}"
        f"先判断需要哪些工具，再检索课程原文作为依据。",
        seq,
    )

    steps = _plan(query, feature)
    if not steps and feature not in ("feynman", "wrongbook"):
        steps = [{"name": "kb_search", "args": {"query": query, "top_k": 6}}]

    # ---- 费曼追问：走模块内专用链路（不是检索工具，而是教学流程）
    if feature == "feynman":
        from .modules import feynman as fey

        round_no = len([m for m in req.messages if m.role == "user"])
        call_id = f"call_{uuid.uuid4().hex[:10]}"
        seq += 1
        yield E.tool_call(call_id, "feynman_probe", f"费曼追问 · 第 {round_no} 轮",
                          {"statement": query[:60], "round": round_no}, seq)
        result = fey.analyze(query, st.retriever, round_no=round_no)
        seq += 1
        yield E.tool_result(call_id, result["summary"], "", seq, name="feynman_probe")
        seq += 1
        yield E.artifact("annotation", result, seq)

        answer = fey.followup_text(result)
        for piece in E.split_for_stream(answer):
            yield E.token(piece)
        st.store.log_event(account, "feynman", {"round": round_no, "level": result["score"]["level"]})
        seq += 1
        yield E.done(seq, provider="deterministic", model="feynman_probe",
                     evidence=0, coverage=result["coverage"],
                     ms=round((time.time() - t0) * 1000))
        return

    # ---- 错题六步诊改（"出题/列表"这类走别的流程，不走六步）
    if (feature == "wrongbook"
            and not _has(query, QUIZ_WORDS)
            and not _has(query, ("我的错题", "错题本", "列表", "有哪些"))):
        from .modules import wrongbook as wb

        call_id = f"call_{uuid.uuid4().hex[:10]}"
        seq += 1
        yield E.tool_call(call_id, "wrongbook_diagnose", f"错题六步诊改 ·「{query[:24]}」",
                          {"question": query}, seq)
        data = wb.six_step(st.retriever, query)
        seq += 1
        yield E.tool_result(call_id, f"根因判定：{data['root_cause']} · 溯源 {len(data['trace'])} 段",
                            "", seq, name="wrongbook_diagnose")
        seq += 1
        yield E.artifact("wrongbook", data, seq)

        answer = wb.render_markdown(data)
        for piece in E.split_for_stream(answer):
            yield E.token(piece)
        st.store.log_event(account, "wrongbook_diagnose", {"root": data["root_cause"]})
        seq += 1
        yield E.done(seq, provider="deterministic", model="wrongbook_diagnose",
                     evidence=len(data["trace"]), coverage=data["coverage"],
                     ms=round((time.time() - t0) * 1000))
        return

    seq += 1
    yield E.thinking("计划调用：" + "、".join(s["name"] for s in steps), seq)

    hits: list[dict] = []
    coverage = 0.0
    tool_answers: list[tuple[str, object]] = []

    for step in steps:
        name = step["name"]
        args = step["args"]
        call_id = f"call_{uuid.uuid4().hex[:10]}"
        seq += 1
        yield E.tool_call(call_id, name, _tool_label(name, args), args, seq)

        outcome = call(name, ctx, **args)

        seq += 1
        yield E.tool_result(call_id, outcome.summary, outcome.detail, seq, name=name)

        if outcome.artifact_type and outcome.artifact_data:
            seq += 1
            yield E.artifact(outcome.artifact_type, outcome.artifact_data, seq)

        if name == "kb_search":
            hits = outcome.payload.get("hits") or []
            coverage = float(outcome.payload.get("coverage") or 0.0)
            gated = bool(outcome.payload.get("gated"))
            st.store.log_event(account, "kb_search", {
                "q": query, "n": len(hits), "coverage": coverage, "gated": gated,
            })
        elif outcome.ok:
            tool_answers.append((name, outcome))

    # ---- 生成
    seq += 1
    if tool_answers:
        name, outcome = tool_answers[0]
        yield E.thinking(f"已有确定性结果（{name}），按结构化模板作答，避免模型改动数值。", seq)
        answer = _answer_from_tool(query, name, outcome, hits, coverage)
        provider, model = "deterministic", name
    else:
        gated = coverage < 0.40
        yield E.thinking(
            f"证据检索完成（覆盖率 {coverage:.0%}），"
            + ("低于门限，应当拒答并说明知识库未收录。" if gated else "据证据组织回答。"),
            seq,
        )
        result = llm.generate(query, hits, gated, coverage, persona=persona_block)
        answer = result.text
        provider, model = result.provider, result.model

    for piece in E.split_for_stream(answer):
        yield E.token(piece)

    # 学情埋点 + 会话持久化
    st.store.log_event(account, "answer", {
        "q": query, "provider": provider, "model": model,
        "n_evidence": len(hits), "coverage": coverage,
        "ms": round((time.time() - t0) * 1000),
    })
    try:
        conv_id = st.store.get_or_create_conversation(account, feature or "__global__", query[:80])
        st.store.append_message(conv_id, "user", query)
        st.store.append_message(conv_id, "assistant", answer, {
            "provider": provider, "model": model,
            "n_evidence": len(hits), "coverage": coverage,
        })
    except Exception:
        pass   # 持久化失败不能影响回答

    seq += 1
    yield E.done(seq, provider=provider, model=model,
                 evidence=len(hits), coverage=coverage,
                 ms=round((time.time() - t0) * 1000))
