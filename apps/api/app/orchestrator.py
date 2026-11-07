"""ReAct 编排：把一次提问变成一条事件流。

无 API Key 时走"本地规则编排 + 抽取式作答"（provider=mock）：
   1. 先跑确定性工具（公差/螺纹/圆弧/图谱/错题），因为这些能算准；
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
from .tools import TOOLS, ToolContext, call, find_fit_spec, find_thread_spec

FIT_WORDS = ("配合", "公差", "基孔制", "基轴制", "间隙", "过盈", "h7", "h8", "k6", "f7", "js6")
GRAPH_WORDS = ("关系", "前置", "区别", "区别是", "对比", "图谱", "知识点", "学什么", "易混淆")
WRONG_WORDS = ("错题", "错题本", "易错")
ARC_WORDS = ("圆弧连接", "相切", "外切", "内切", "圆角", "连接弧")
THREAD_WORDS = ("螺纹", "m10", "m12", "m20", "螺栓", "螺柱")
VIEW_WORDS = ("三视图", "投影规律", "长对正", "高平齐", "宽相等", "三面投影", "视图投影",
              "第一角", "主视图", "俯视图", "左视图")
SECTION_WORDS = ("剖视图", "剖切", "全剖", "半剖", "局部剖", "剖面线", "剖开")
SKETCH_WORDS = ("找茬", "批改", "我画的", "帮我看看图", "对对答案", "检查我的图")
QUIZ_WORDS = ("出题", "考考我", "来一道", "练一练", "做道题")


def _has(text: str, words: tuple[str, ...]) -> bool:
    low = text.lower()
    return any(w in low for w in words)


def _plan(query: str, feature: str | None) -> list[dict]:
    """决定要调哪些工具。返回 [{name, args, label}]。"""
    steps: list[dict] = []
    q = query.strip()
    low = q.lower()

    fit = find_fit_spec(q)
    thread = find_thread_spec(q)

    # 模块优先
    if feature == "tolerance" and fit:
        return [{"name": "tolerance_calc", "args": {"spec": fit}}]
    if feature == "coach":
        if thread:
            return [{"name": "thread_calc", "args": {"spec": thread}}]
        if _has(q, ARC_WORDS):
            steps.append({"name": "arc_construct", "args": {"kind": "auto", "query": q}})
            return steps

    if fit and _has(q, FIT_WORDS + ("φ", "Φ", "⌀", "ø")):
        steps.append({"name": "tolerance_calc", "args": {"spec": fit}})
    elif thread and _has(q, THREAD_WORDS):
        steps.append({"name": "thread_calc", "args": {"spec": thread}})
    elif _has(q, ARC_WORDS) and feature == "coach":
        steps.append({"name": "arc_construct", "args": {"kind": "auto", "query": q}})

    # 辨析模块：直接给成对图 + 差异点 + 随堂题
    if feature == "projection" or _has(q, ("区别", "辨析", "对比", "怎么区分")):
        if feature == "projection" or _has(q, ("辨析", "区别", "区分", "对比")):
            steps.append({"name": "comparison_pick", "args": {"query": q}})

    # 出题/练习
    if _has(q, QUIZ_WORDS):
        steps.append({"name": "quiz_from_kb", "args": {"topic": q, "n": 2}})

    # 手绘找茬：错题本模块里说"找茬/批改/我画的"
    if _has(q, SKETCH_WORDS):
        steps.append({"name": "sketch_grade",
                      "args": {"inject": "missing,linetype,offset", "view": "front"}})
    # 剖视：3D 沙盒里问剖切，或全局问"剖视图/剖面线/剖开"
    if _has(q, SECTION_WORDS) and (feature == "sandbox3d" or _has(q, ("怎么画", "画法", "剖开", "剖切", "剖面线", "长什么样"))):
        steps.append({"name": "section_render", "args": {"axis": "y", "query": q}})
    # 三视图真投影：3D 沙盒模块，或提问里出现投影规律/视图名称
    elif feature == "sandbox3d" or _has(q, VIEW_WORDS):
        steps.append({"name": "projection_render", "args": {"query": q}})

    if _has(q, WRONG_WORDS):
        steps.append({"name": "wrongbook_crud", "args": {"action": "list"}})

    # 图谱查询：抓「XX和YY的区别」这类
    m = re.search(r"([\u4e00-\u9fff]{2,8})\s*(?:和|与|跟|vs)\s*([\u4e00-\u9fff]{2,8})\s*(?:的)?(?:区别|差别|差异|对比)", q)
    if _has(q, GRAPH_WORDS) and not steps:
        term = m.group(1) if m else q[:12]
        steps.append({"name": "kg_lookup", "args": {"term": term}})

    # 检索永远兜底
    steps.append({"name": "kb_search", "args": {"query": q, "top_k": 6}})
    return steps


def _tool_label(name: str, args: dict) -> str:
    from .tools import TOOL_LABELS

    base = TOOL_LABELS.get(name, name)
    if name == "kb_search":
        return f"{base} ·「{args.get('query','')}」"
    if name in ("tolerance_calc", "thread_calc"):
        return f"{base} ·「{args.get('spec','')}」"
    if name == "kg_lookup":
        return f"{base} ·「{args.get('term','')}」"
    return base


def _answer_from_tool(query: str, name: str, outcome, hits: list[dict], coverage: float) -> str:
    """确定性工具命中时，用结构化模板作答（不经过模型，保证数值零误差）。"""
    if name == "tolerance_calc" and outcome.ok:
        r = outcome.payload["result"]
        h, s, f = r["hole"], r["shaft"], r["fit"]
        gap = max(f["max_gap"], abs(f["min_gap"]))
        lines = [
            f"**Φ{r['basic_size']:g} {r['system']} {h['code']}/{s['code']} → {f['type']}**",
            "",
            "| 项 | 孔 " + h["code"] + " | 轴 " + s["code"] + " |",
            "|---|---|---|",
            f"| 标准公差 IT | {h['IT']:.3f} | {s['IT']:.3f} |",
            f"| 上偏差 | {h['ES']:+.3f} | {s['es']:+.3f} |",
            f"| 下偏差 | {h['EI']:+.3f} | {s['ei']:+.3f} |",
            f"| 极限尺寸 | {h['min']:.3f} ~ {h['max']:.3f} | {s['min']:.3f} ~ {s['max']:.3f} |",
            "",
            f"**配合性质**：{f['type']}。最大间隙 {f['max_gap']:+.3f} mm，"
            f"最小间隙 {f['min_gap']:+.3f} mm，"
            f"{'最大过盈 ' + format(abs(f['max_interference']), '+.3f') + ' mm' if f.get('max_interference') else ''}"
            f"（量级约 {gap*1000:.0f} μm）。",
            "",
            f"**工艺提示**：{r.get('process_hint','')}",
            "",
            f"**依据**：{'、'.join(r.get('refs', []))}",
        ]
        return "\n".join(x for x in lines if x is not None)

    if name == "thread_calc" and outcome.ok:
        d = outcome.payload["result"]
        lines = [
            f"**{d.get('spec')} 比例画法**",
            "",
            f"- 大径 d = {d.get('d')} mm（画**粗实线**）",
            f"- 小径 d₁ = {d.get('d1')} mm（画**细实线**，约 0.85d）",
            f"- 牙型高度按 0.85d 近似，不画真实牙型",
            "",
            "**画法要点**：",
        ]
        lines += [f"- {p}" for p in (d.get("points") or [])]
        return "\n".join(lines)

    if name == "arc_construct" and outcome.ok:
        res = outcome.payload["result"]
        lines = [f"**{res.get('summary','圆弧连接')}**", ""]
        for s in res.get("steps") or []:
            lines.append(f"{s['n']}. **{s['title']}**：{s['detail']}")
        if res.get("principle"):
            lines += ["", f"**几何依据**：{res['principle']}"]
        note = (outcome.artifact_data or {}).get("note")
        if note:
            lines += ["", f"> {note}"]
        return "\n".join(lines)

    if name == "comparison_pick" and outcome.ok:
        p = outcome.payload["pair"]
        lines = [f"**{p.get('title')}**", ""]
        a, b = p.get("a") or {}, p.get("b") or {}
        lines.append(f"- **A**：{a.get('caption','')}（{a.get('正确性','')}）")
        lines.append(f"- **B**：{b.get('caption','')}（{b.get('正确性','')}）")
        lines.append("")
        lines.append("**关键差异**：")
        for d in p.get("differences") or []:
            lines.append(f"{d.get('no')}. **{d.get('name')}**——A {d.get('a_desc','')}；"
                         f"B {d.get('b_desc','')}。{d.get('why','')}")
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

    if name == "sketch_grade" and outcome.ok:
        d = outcome.artifact_data
        if d.get("mode") == "exercise":
            return "\n".join([
                f"**找茬练习**（{d.get('model_name')} · {d.get('view')} 视图）",
                "",
                f"右边给了一张有 **{d.get('expect_count')} 处错误**的图，请你逐条找出来：",
                "",
                "- 漏画（答案有、图上没有）",
                "- 多画（图上有、答案没有）",
                "- 虚实线混淆（该虚线画成实线，或相反）",
                "- 位置/长度偏差、方向错误",
                "",
                "> 答案先不给你。找到后告诉我哪几条，或者把改正后的线提交上来，我再判分。",
            ])
        res = outcome.payload.get("result") or {}
        lines = [f"**找茬结果：{res.get('level')} · 得分 {res.get('score', 0):.0%}**",
                 f"（{res.get('matched')}/{res.get('truth_total')} 条正确）", ""]
        errs = res.get("errors") or []
        if not errs:
            lines += ["图上没有发现错误，三个视图的线条都对上了。"]
        else:
            lines.append(f"**发现 {len(errs)} 处问题**：")
            lines.append("")
            lines.append("| 类型 | 说明 |")
            lines.append("|---|---|")
            for e in errs[:10]:
                lines.append(f"| {e['type_name']} | {e['desc']} |")
        lines += ["", f"> {res.get('note','')}"]
        return "\n".join(lines)

    if name == "section_render" and outcome.ok:
        d = outcome.payload["section"]
        sz = d["size"]
        lines = [
            f"**{d['name']}的全剖视图**（{sz['L']:g}×{sz['W']:g}×{sz['H']:g} mm）",
            "",
            f"在 {d['cut_at']:g} mm 处剖开，右侧画布左边是**外形视图**、右边是**剖视图**：",
            "",
            "- 剖视图里**剖面线（45° 细实线）只画在被剖切平面切到的实体部分**，"
            "孔、槽等空腔处必须断开——这就是判断剖面线画没画对的依据；",
            "- 剖切面**后面**的可见轮廓照常画出；不可见轮廓若已被剖视表达清楚，虚线可省略；",
            "- 肋板、轮辐等薄壁结构若沿纵向剖切，按国标**不画剖面线**（本模型不含此类结构）。",
            "",
            f"> {d['note']}",
        ]
        return "\n".join(lines)

    if name == "projection_render" and outcome.ok:
        d = outcome.payload["model"]
        sz = d["size"]
        lines = [
            f"**{d['name']}的三视图**（{sz['L']:g}×{sz['W']:g}×{sz['H']:g} mm，{d['projection']}投影）",
            "",
            "右侧画布已画出三个视图，并用彩色虚线标出三条投影规律：",
            "",
            "- **长对正**（蓝）：主视图与俯视图在长度方向上左右对齐，同一条竖线上下贯通；",
            "- **高平齐**（绿）：主视图与左视图在高度方向上上下平齐，同一条横线左右贯通；",
            "- **宽相等**（橙）：俯视图的宽度与左视图的宽度相等，靠 45° 斜线传递。",
            "",
            "**画图顺序**：先定三个视图的位置 → 画作图基准线（底面线、对称中心线）→ "
            "按主视图逐块投影 → 用三等规律校核 → 检查多线与漏线。",
        ]
        st = d.get("stats") or {}
        if st:
            h = sum(v.get("hidden", 0) for v in st.values())
            lines += ["", f"> 虚线共 {h} 条，表示该视图中看不到的轮廓（如内孔、后壁）。"]
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
    return llm.mock_answer(query, hits, gated=coverage < 0.45, coverage=coverage)


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

    # 模块身份：参考作品的做法是前端随请求发 {id,title,persona}，
    # 后端拼进系统提示词 —— 这样「加模块不用改后端」。
    # 这里同时兼容旧前端的字符串 id 和新的对象写法。
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
    mod = MODULE_BY_ID.get(feature or "__global__")
    seq += 1
    yield E.thinking(
        f"学生提问：{query}。"
        f"{'当前模块：' + mod.name + '。' if mod else ''}"
        f"先判断需要哪些工具，再检索课程原文作为依据。",
        seq,
    )

    steps = _plan(query, feature)
    if not steps:
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

    # ---- 错题六步诊改（"找茬/批改/出题"这类走别的流程，不走六步）
    if (feature == "wrongbook"
            and not _has(query, SKETCH_WORDS)
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
        gated = coverage < 0.45
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
