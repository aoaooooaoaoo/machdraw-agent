"""FastAPI 服务入口。

接口面刻意保持极小（对齐参考作品实测的 3 个端点）：
    POST /api/chat             唯一对话入口（SSE）
    POST /api/auth/login       学号/姓名即账号，首次自动建号
    GET/PUT /api/auth/records  个人记录（错题/历史）同步
    GET  /api/health           健康检查 + 工具清单
另有前端只读接口：/api/modules、/api/graph、/api/wrongbook、/api/stats
"""
from __future__ import annotations

import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Body, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from . import events as E
from .config import (
    GATE_TAU,
    GATE_TAU_CHUNK,
    LLM_API_KEY,
    LLM_MODEL,
    LLM_PROVIDER,
    ROOT,
    SPARSE_WEIGHT,
)
from .contracts.models import AuthRequest, ChatRequest
from .orchestrator import run_chat
from .state import MODULES, get_state, load_state, reset_state
from .tools import TOOLS

WEB_DIST = ROOT / "apps" / "web" / "dist"
ADMIN_HTML = ROOT / "apps" / "api" / "static" / "admin.html"


@asynccontextmanager
async def lifespan(app: FastAPI):
    st = load_state()
    print(f"[startup] chunks={len(st.chunks)} nodes={len(st.nodes)} edges={len(st.edges)}")
    for w in st.warnings:
        print(f"[warn] {w}")
    yield


app = FastAPI(title="机械制图 AI 助教 Agent", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _account(x_account: str | None) -> str:
    return (x_account or "anonymous").strip() or "anonymous"


# ---------------------------------------------------------------- 健康检查


@app.get("/api/health")
def health() -> dict:
    st = get_state()
    return {
        "ok": True,
        "model": LLM_MODEL if LLM_PROVIDER != "mock" else "mock(extractive-local)",
        "provider": LLM_PROVIDER,
        # 之前写成 bool(LLM_PROVIDER != "mock")，只看 provider 不看 key ——
        # 会出现"显示有 key、实际回落 mock 且不打降级提示"的假象。这里改成真的看 key。
        "has_key": bool(LLM_API_KEY),
        "llm_ready": bool(LLM_PROVIDER != "mock" and LLM_API_KEY),
        "tools": list(TOOLS.keys()),
        "chunks": len(st.chunks),
        "docs": len({c.doc_id for c in st.chunks}),
        "nodes": len(st.nodes),
        "edges": len(st.edges),
        "sparse_weight": SPARSE_WEIGHT,
        "gate_tau": GATE_TAU,
        "warnings": st.warnings,
    }


@app.post("/api/admin/reload")
def reload_kb() -> dict:
    """重载知识库与索引（改完 kb/ 后不用重启服务）。"""
    reset_state()
    st = load_state()
    return {"ok": True, "chunks": len(st.chunks), "warnings": st.warnings}


# ---------------------------------------------------------------- 教师端


@app.get("/api/admin/overview")
def admin_overview() -> dict:
    """教师端总览：语料/图谱/图库规模 + 学情聚合。"""
    st = get_state()
    docs: dict[str, dict] = {}
    for c in st.chunks:
        d = docs.setdefault(c.doc_id, {
            "doc_id": c.doc_id, "title": c.document_title, "category": c.category,
            "role": c.role.value, "internal_only": c.internal_only, "chunks": 0,
            "sections": set(),
        })
        d["chunks"] += 1
        if c.section:
            d["sections"].add(c.section.split(" › ")[0])
    doc_list = []
    for d in docs.values():
        d["sections"] = sorted(d["sections"])[:12]
        doc_list.append(d)
    doc_list.sort(key=lambda x: -x["chunks"])

    return {
        "ok": True,
        "corpus": {
            "chunks": len(st.chunks),
            "docs": len(doc_list),
            "internal_only": sum(1 for c in st.chunks if c.internal_only),
            "figures": len(st.figures),
            "pairs": len(st.pairs),
            "nodes": len(st.nodes),
            "edges": len(st.edges),
            "questions": len(st.questions),
            "kb_dir": str(st.kb_dir),
            "documents": doc_list,
        },
        "stats": st.store.admin_overview(),
        "config": {
            "sparse_weight": SPARSE_WEIGHT,
            "gate_tau": GATE_TAU,
            "gate_tau_chunk": GATE_TAU_CHUNK,
            "llm_provider": LLM_PROVIDER,
            "tools": list(TOOLS.keys()),
        },
        "warnings": st.warnings,
    }


@app.get("/api/admin/users")
def admin_users() -> dict:
    st = get_state()
    return {"ok": True, "users": st.store.admin_users()}


@app.get("/api/admin/review")
def admin_review() -> dict:
    """待教师复核的条目：从知识库文本里抽"需要人工确认"的痕迹。"""
    st = get_state()
    marks = ("以标准表为准", "以手册为准", "以教材为准", "为准", "待核", "需核对",
             "存疑", "待确认", "按标准原文", "另有规定", "略有差异", "以标准规定为准")
    out = []
    for c in st.chunks:
        hit = next((m for m in marks if m in c.text), None)
        if hit:
            out.append({
                "chunk_id": c.chunk_id,
                "doc_title": c.document_title,
                "section": c.section,
                "mark": hit,
                "snippet": c.text[:160],
            })
        if len(out) >= 60:
            break
    return {"ok": True, "total": len(out), "items": out}


# ---------------------------------------------------------------- 账号


@app.post("/api/auth/login")
def login(req: AuthRequest) -> dict:
    st = get_state()
    if not req.account.strip():
        raise HTTPException(400, "账号不能为空")
    try:
        info = st.store.login_or_register(req.account, req.password)
    except PermissionError as exc:
        raise HTTPException(401, str(exc)) from exc
    return {"ok": True, **info}


@app.get("/api/auth/records")
def get_records(x_account: str | None = Header(default=None)) -> dict:
    st = get_state()
    acc = _account(x_account)
    return {
        "ok": True,
        "records": st.store.get_records(acc),
        "wrongbook": st.store.list_wrong(acc),
        "stats": st.store.event_stats(acc),
    }


@app.put("/api/auth/records")
def put_records(payload: dict = Body(...), x_account: str | None = Header(default=None)) -> dict:
    st = get_state()
    acc = _account(x_account)
    data = payload.get("data") or {}
    st.store.put_records(acc, data)
    return {"ok": True, "revision": int(payload.get("revision") or 0) + 1}


# ---------------------------------------------------------------- 模块与图谱


@app.get("/api/modules")
def modules() -> dict:
    return {"modules": [m.model_dump() for m in MODULES]}


GRAPH_LAYERS = [
    {"layer": 1, "name": "基础理解", "desc": "概念、规则、符号怎么定义"},
    {"layer": 2, "name": "识图分析", "desc": "给图能不能读出结构与表达方法"},
    {"layer": 3, "name": "综合绘图", "desc": "给定条件能不能画对、能不能讲清工艺"},
]




# ---------------------------------------------------------------- 图谱展示投影

# tier → 视觉层级（1 最大）。trackA / trackB 是两条并行主线，层级相同、轨道不同。
TIER_TO_LEVEL = {"core": 1, "trackA": 2, "trackB": 2, "branch": 3, "concept": 4}
TIER_TO_TRACK = {"trackA": "A", "trackB": "B"}

_CN_NUM = {c: i for i, c in enumerate("零一二三四五六七八九", 0)}
_CN_NUM.update({"十": 10})


def _chapter_order(name: str) -> int:
    """从「第三章 ...」里取出 3。取不到就排到最后。"""
    import re as _re

    m = _re.match(r"^第([零一二三四五六七八九十]+)章", (name or "").strip())
    if not m:
        return 99
    s = m.group(1)
    if s == "十":
        return 10
    if s.startswith("十"):
        return 10 + _CN_NUM.get(s[1:], 0)
    if s.endswith("十"):
        return _CN_NUM.get(s[0], 0) * 10
    if "十" in s:
        a, b = s.split("十", 1)
        return _CN_NUM.get(a, 0) * 10 + _CN_NUM.get(b, 0)
    return _CN_NUM.get(s, 99)


_KP_CACHE: dict[str, dict] = {}


def _kp_index(kb_dir) -> dict[str, dict]:
    """读 kb/knowledge/kp.jsonl，给节点补详情素材（按 kb_dir 缓存一次）。"""
    key = str(kb_dir)
    if key in _KP_CACHE:
        return _KP_CACHE[key]
    out: dict[str, dict] = {}
    p = kb_dir / "knowledge" / "kp.jsonl"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            kp = rec.get("kp_id")
            if kp:
                out[kp] = rec
    _KP_CACHE[key] = out
    return out


def _load_question_edges(kb_dir) -> list[dict]:
    """问题链：kb/graph/question_edges.jsonl（可选文件，没有就空）。"""
    p = kb_dir / "graph" / "question_edges.jsonl"
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if rec.get("source") and rec.get("target"):
            out.append({
                "source": rec["source"],
                "target": rec["target"],
                "relation": rec.get("relation", "prereq"),
                "why": rec.get("why", ""),
            })
    return out


@app.get("/api/graph")
def graph() -> dict:
    """知识图谱 + 问题图谱共用的数据源。

    · nodes / edges：知识图谱（169 节点 / 279 边）
    · chapters：按章分组的节点 id，供"全课程星图"分星系
    · questions：问题图谱，已把 kp_ids 解析成 kp_labels + node_ids，便于点知识点跳回星图
    · question_layers：三层递进的层名与认知标签分布
    """
    st = get_state()

    kp_to_node = {}
    for n in st.nodes:
        kp = n.get("kp_id")
        if kp:
            kp_to_node[kp] = n

    # 按章分组（星图的"星系"）
    chapter_map: dict[str, list[str]] = {}
    for n in st.nodes:
        ch = (n.get("chapter") or "未分章").strip()
        chapter_map.setdefault(ch, []).append(n.get("id"))

    questions = []
    bloom_by_layer: dict[int, dict[str, int]] = {1: {}, 2: {}, 3: {}}
    for q in st.questions:
        kps = [k for k in (q.get("kp_ids") or []) if k]
        labels = [kp_to_node[k].get("label", k) for k in kps if k in kp_to_node]
        node_ids = [kp_to_node[k].get("id") for k in kps if k in kp_to_node]
        layer = int(q.get("layer") or 1)
        bloom = q.get("bloom") or ""
        if bloom:
            bloom_by_layer.setdefault(layer, {})
            bloom_by_layer[layer][bloom] = bloom_by_layer[layer].get(bloom, 0) + 1
        questions.append({
            "qid": q.get("qid"),
            "layer": layer,
            "question": q.get("question"),
            "bloom": bloom,
            "kp_ids": kps,
            "kp_labels": labels,
            "node_ids": node_ids,
            "hint": q.get("hint", ""),
        })

    layers = []
    for meta in GRAPH_LAYERS:
        ids = [q["qid"] for q in questions if q["layer"] == meta["layer"]]
        layers.append({
            **meta,
            "count": len(ids),
            "qids": ids,
            "blooms": bloom_by_layer.get(meta["layer"], {}),
        })

    chapters = [
        {"chapter": ch, "node_ids": ids, "count": len(ids)}
        for ch, ids in sorted(chapter_map.items(), key=lambda kv: -len(kv[1]))
    ]

    # ---- 展示投影：章节统一成按课程顺序编号的 sector，方便星图按章分星系
    order = sorted(chapter_map.keys(), key=_chapter_order)
    sector_of = {ch: i for i, ch in enumerate(order)}
    kps = _kp_index(st.kb_dir)

    # 由 compose 边推出父节点（compose 的 source 是整体、target 是部分）
    parent_of: dict[str, str] = {}
    for e in st.edges:
        if e.get("rel") == "compose" and e.get("target"):
            parent_of.setdefault(e["target"], e.get("source"))

    enriched_nodes = []
    for n in st.nodes:
        ch = (n.get("chapter") or "未分章").strip()
        tier = n.get("tier") or "concept"
        kp = kps.get(n.get("kp_id") or "", {})
        enriched_nodes.append({
            **n,
            "sector": sector_of.get(ch, 99),
            "level": TIER_TO_LEVEL.get(tier, 4),
            "track": TIER_TO_TRACK.get(tier, ""),
            "parent": parent_of.get(n.get("id")),
            # 详情面板素材（kp.jsonl 里没有就留空，前端做兜底）
            "desc": kp.get("definition") or "",
            "points": kp.get("points") or [],
            "refs": kp.get("refs") or [],
            "commonMistakes": kp.get("common_mistakes") or [],
            "bloom": kp.get("bloom") or "",
            "section": kp.get("section") or "",
        })

    import math as _math

    sectors = []
    total = max(1, len(order))
    for ch in order:
        i = sector_of[ch]
        sectors.append({
            "sector": i,
            "chapter": ch,
            "count": len(chapter_map.get(ch, [])),
            # 极角（弧度，0 在正上方，顺时针），星图按章均匀铺一圈
            "angle": -_math.pi / 2 + i * (2 * _math.pi / total),
        })

    return {
        "nodes": enriched_nodes,
        "edges": st.edges,
        "questions": questions,
        "question_layers": layers,
        "chapters": chapters,
        "sectors": sectors,
        "question_edges": _load_question_edges(st.kb_dir),
        "stats": {
            "nodes": len(st.nodes),
            "edges": len(st.edges),
            "questions": len(questions),
            "chains": sum(1 for e in st.edges if e.get("rel") == "prereq"),
            "chapters": len(chapters),
            "relations": {
                r: sum(1 for e in st.edges if e.get("rel") == r)
                for r in ("prereq", "contrast", "compose", "cause")
            },
        },
    }


@app.get("/api/figures")
def figures() -> dict:
    """自绘教学图库。每项带 file，前端用 /figures/<file> 取 SVG。"""
    st = get_state()
    return {"figures": st.figures, "total": len(st.figures)}


@app.get("/api/pairs")
def pairs() -> dict:
    """剖视/投影辨析成对图（含差异点与随堂题）。"""
    st = get_state()
    return {"pairs": st.pairs, "total": len(st.pairs)}


_VIEW_CACHE: dict[str, dict] = {}


@app.get("/api/models")
def models() -> dict:
    """可用教学模型清单（三视图真投影）。"""
    from .geometry.models import MODELS

    out = []
    for mid, meta in MODELS.items():
        out.append({"model_id": mid, "name": meta["name"]})
    return {"models": out, "total": len(out)}


@app.get("/api/models/{model_id}")
def model_view(model_id: str, mode: str = "three_view") -> dict:
    """取某个模型的三视图数据（已排版，前端直接画）。结果进程内缓存。"""
    cache_key = f"{model_id}:{mode}"
    if cache_key in _VIEW_CACHE:
        return _VIEW_CACHE[cache_key]
    try:
        from .geometry.models import MODELS, build_model, model_name
        from .geometry.projection import build_three_view
        from .geometry.section import (
            build_half_section_view,
            build_local_section_view,
            build_section_view,
        )
    except ImportError as exc:
        raise HTTPException(500, f"投影引擎不可用：{exc}") from exc
    if model_id not in MODELS:
        raise HTTPException(404, f"未知模型 {model_id}")
    if mode in ("section", "full", "half_section", "local_section"):
        solid = build_model(model_id)
        nm = model_name(model_id)
        if mode == "half_section":
            data = build_half_section_view(solid, nm, model_id, "y")
        elif mode == "local_section":
            data = build_local_section_view(solid, nm, model_id, "y")
        else:
            data = build_section_view(solid, nm, model_id, "y")
    else:
        data = build_three_view(build_model(model_id), model_name(model_id), model_id)
    _VIEW_CACHE[cache_key] = data
    return data


@app.get("/api/graph/node/{node_id}")
def graph_node(node_id: str) -> dict:
    st = get_state()
    node = st.node(node_id)
    if not node:
        raise HTTPException(404, "节点不存在")
    return {
        "node": node,
        "neighbors": st.neighbors(node_id),
        "prereq": st.prereq_chain(node_id),
    }


# ---------------------------------------------------------------- 错题本


@app.get("/api/wrongbook")
def wrongbook_list(x_account: str | None = Header(default=None)) -> dict:
    st = get_state()
    return {"items": st.store.list_wrong(_account(x_account))}


@app.post("/api/wrongbook")
def wrongbook_add(payload: dict = Body(...), x_account: str | None = Header(default=None)) -> dict:
    st = get_state()
    acc = _account(x_account)
    wid = st.store.add_wrong(acc, payload)
    st.store.log_event(acc, "wrongbook_manual", {"id": wid})
    return {"ok": True, "id": wid}


@app.post("/api/quiz/explain")
def quiz_explain(payload: dict = Body(...)) -> dict:
    """题目解析：答案隔离——只有学生点了"看解析"才下发。"""
    st = get_state()
    chunk_id = str(payload.get("chunk_id") or "")
    if not chunk_id:
        raise HTTPException(400, "缺少 chunk_id")
    chunk = next((c for c in st.chunks if c.chunk_id == chunk_id), None)
    if chunk is None:
        raise HTTPException(404, "题目不存在")

    # 解析优先取"答案卷"同题号的段落，其次退化为该题所在章节的讲授原文
    answer_doc = ""
    try:
        key = chunk.text[:18]
        for c in st.chunks:
            if c.role.value == "answer" and key and key in c.text:
                answer_doc = c.text
                break
    except Exception:
        answer_doc = ""

    refs = st.retriever.search(chunk.text[:120], top_k=3)
    hits = [h.model_dump() for h in refs["hits"]]

    return {
        "ok": True,
        "chunk_id": chunk_id,
        "question": chunk.text,
        "section": chunk.section,
        "source": chunk.document_title,
        "explain": answer_doc or (hits[0]["content"] if hits else "本题解析暂未收录。"),
        "refs": [
            {"documentTitle": h["documentTitle"], "section": h["section"],
             "chunkId": h["chunkId"], "score": h["score"]}
            for h in hits
        ],
    }


@app.get("/api/quiz")
def quiz_pick(topic: str = "", n: int = 3, x_account: str | None = Header(default=None)) -> dict:
    """从题库抽题（不下发答案）。"""
    from .tools import ToolContext, quiz_from_kb

    st = get_state()
    out = quiz_from_kb(ToolContext(state=st, account=_account(x_account)), topic=topic, n=n)
    return {"ok": out.ok, "summary": out.summary, **out.artifact_data}


# ---------------------------------------------------------------- 手绘找茬


@app.get("/api/sketch/exercise")
def sketch_exercise(model_id: str = "M-L-BLOCK", view: str = "front",
                    inject: str = "missing,linetype") -> dict:
    """生成一道找茬练习：返回被改坏的图，答案不下发。"""
    from .tools import TOOLS

    st = get_state()
    from .tools import ToolContext

    out = TOOLS["sketch_grade"](ToolContext(state=st), model_id=model_id,
                                view=view, inject=inject)
    if not out.ok:
        raise HTTPException(400, out.summary)
    return {"ok": True, **out.artifact_data}


@app.post("/api/sketch/grade")
def sketch_grade_api(payload: dict = Body(...)) -> dict:
    """批改：提交学生画的线段集合，返回结构化错误列表。"""
    from .tools import TOOLS, ToolContext

    st = get_state()
    model_id = str(payload.get("model_id") or "M-L-BLOCK")
    view = str(payload.get("view") or "all")
    segs = payload.get("segments") or []
    tol = float(payload.get("tol") or 3.0)
    out = TOOLS["sketch_grade"](ToolContext(state=st), model_id=model_id,
                                view=view, segments=segs)
    if not out.ok:
        raise HTTPException(400, out.summary)
    res = dict(out.artifact_data)
    res["tol"] = tol
    return {"ok": True, **res}


@app.get("/api/sketch/truth")
def sketch_truth(model_id: str = "M-L-BLOCK", view: str = "all") -> dict:
    """给出标准答案的线段（供练习界面显示"对照答案"）。"""
    from .geometry.models import MODELS, build_model, model_name
    from .geometry.projection import build_three_view

    if model_id not in MODELS:
        raise HTTPException(404, "未知模型")
    d = build_three_view(build_model(model_id), model_name(model_id), model_id)
    segs = d["segments"] if view == "all" else [s for s in d["segments"] if s["view"] == view]
    return {"model_id": model_id, "view": view, "segments": segs,
            "viewBox": d["viewBox"], "name": d["name"]}


@app.get("/api/stats")
def stats(x_account: str | None = Header(default=None)) -> dict:
    st = get_state()
    acc = _account(x_account)
    return {"account": acc, "events": st.store.event_stats(acc), "wrongbook": len(st.store.list_wrong(acc))}


# ---------------------------------------------------------------- 对话（核心）


@app.post("/api/chat")
async def chat(req: ChatRequest, x_account: str | None = Header(default=None)):
    acc = _account(x_account)

    async def gen():
        try:
            async for ev in run_chat(req, acc):
                yield E.to_sse(ev)
            yield "data: [DONE]\n\n"
        except Exception as exc:  # 任何异常都要变成一帧 error，不能让流断死
            yield E.to_sse(E.error("INTERNAL", f"{type(exc).__name__}: {exc}"))
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.post("/api/chat/sync")
async def chat_sync(req: ChatRequest, x_account: str | None = Header(default=None)) -> dict:
    """非流式版本，便于脚本与测试。"""
    acc = _account(x_account)
    evs, answer = [], []
    async for ev in run_chat(req, acc):
        d = ev.model_dump(exclude_none=True)
        if ev.type.value == "token":
            answer.append(ev.text)
        evs.append(d)
    return {"events": evs, "answer": "".join(answer)}


# ---------------------------------------------------------------- 静态前端


@app.get("/")
def index():
    idx = WEB_DIST / "index.html"
    if idx.exists():
        return FileResponse(idx)
    return JSONResponse(
        {
            "service": "机械制图 AI 助教 Agent",
            "hint": "前端未构建。开发模式请运行 pnpm dev（apps/web）；API 见 /docs",
            "api": ["/api/health", "/api/chat", "/api/modules", "/api/graph"],
        }
    )


@app.get("/admin")
def admin_page():
    """教师端页面（独立静态页，不动前端构建产物）。"""
    if ADMIN_HTML.exists():
        return FileResponse(ADMIN_HTML)
    return JSONResponse({"error": "apps/api/static/admin.html 缺失"}, status_code=404)


if WEB_DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(WEB_DIST / "assets")), name="assets")

# 自绘 SVG 教学图库：前端直接用 <img src="/figures/FIG-xxx.svg"> 或内联 <object>
FIG_DIR = ROOT / "kb" / "figures"
if FIG_DIR.exists():
    app.mount("/figures", StaticFiles(directory=str(FIG_DIR)), name="figures")
