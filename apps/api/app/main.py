"""FastAPI 服务入口。

接口面刻意保持极小（对齐参考作品实测的 3 个端点）：
    POST /api/chat             唯一对话入口（SSE）
    POST /api/auth/login       学号/姓名即账号，首次自动建号
    GET/PUT /api/auth/records  个人记录（错题/历史）同步
    GET  /api/health           健康检查 + 工具清单
另有前端只读接口：/api/modules、/api/graph、/api/wrongbook、/api/stats
"""
from __future__ import annotations

import base64
import io
import json
import time
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
    print(f"[startup] chunks={len(st.chunks)} nodes={len(st.nodes)} edges={len(st.edges)} "
          f"figures={len(st.figures)} pairs={len(st.pairs)}")
    for w in st.warnings:
        print(f"[warn] {w}")
    yield


app = FastAPI(title="核反应堆物理 AI 助教 Agent", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _account(x_account: str | None) -> str:
    return (x_account or "anonymous").strip() or "anonymous"


def _mastery_records(account: str) -> dict:
    """读取账号的掌握度记录（独立 mastery 表，按账号 + 知识点）。"""
    try:
        return get_state().store.list_mastery(account)
    except Exception:
        return {}


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
             "需人工复核", "复核", "存疑", "待确认", "按标准原文", "另有规定",
             "略有差异", "以标准规定为准", "ENDF", "版本号")
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


# ---------------------------------------------------------------- 学习者模型（掌握度）

@app.get("/api/mastery")
def get_mastery(x_account: str | None = Header(default=None)) -> dict:
    acc = _account(x_account)
    mastery = _mastery_records(acc)
    summary: dict[str, int] = {}
    for item in mastery.values():
        state = (item or {}).get("state") or "未学"
        summary[state] = summary.get(state, 0) + 1
    return {"ok": True, "account": acc, "mastery": mastery, "summary": summary}


@app.post("/api/mastery/report")
def _apply_mastery(st, account: str, keys: set[str], signal: str, quality: float | None = None) -> tuple[dict, dict]:
    """统一的掌握度更新：signal=got/again；quality 0–1（判分时用）优先。"""
    mastery = dict(st.store.list_mastery(account))
    now = time.time()
    updated: dict[str, dict] = {}
    for key in keys:
        prev = mastery.get(key) or {}
        prev_score = float(prev.get("score") or 0.0)
        if quality is not None:
            score = max(0.0, min(1.0, prev_score * 0.4 + float(quality) * 0.6))
        elif signal == "again":
            score = max(0.0, prev_score * 0.45)
        else:
            score = min(1.0, prev_score + (0.35 if prev_score < 0.75 else 0.18))
        if score >= 0.75:
            state = "已掌握"
        elif signal == "again" and score < 0.25:
            state = "需复习"
        elif score > 0:
            state = "在学"
        else:
            state = "未学"
        item = {
            "score": round(score, 3),
            "attempts": int(prev.get("attempts") or 0) + 1,
            "correct": int(prev.get("correct") or 0) + (0 if signal == "again" else 1),
            "state": state,
            "last_at": now,
            "last_signal": signal,
        }
        mastery[key] = item
        updated[key] = item
    st.store.upsert_mastery(account, updated)
    records = st.store.get_records(account)
    records["mastery_updated_at"] = now
    st.store.put_records(account, records)
    return updated, mastery


@app.post("/api/mastery/report")
def report_mastery(payload: dict = Body(...), x_account: str | None = Header(default=None)) -> dict:
    """学生自评 / 判分回写掌握度。

    signal='got'   我会了     → 加分（≥0.75 记已掌握）
    signal='again' 还不会     → 减分并记需复习，同时可自动写入错题本
    """
    st = get_state()
    acc = _account(x_account)
    signal = str(payload.get("signal") or "got")
    if signal not in ("got", "again"):
        raise HTTPException(400, "signal 只能是 got / again")
    kp_ids = [k for k in (payload.get("kp_ids") or []) if k]
    node_ids = [k for k in (payload.get("node_ids") or []) if k]
    node_kp = {n.get("id"): (n.get("kp_id") or n.get("id")) for n in st.nodes}
    keys = set(kp_ids) | {node_kp.get(nid, nid) for nid in node_ids}
    if not keys:
        # 没有 kp 标注时退化为"章级掌握度"：chapter:<章名>
        chapter = str(payload.get("chapter") or "").strip()
        if not chapter and payload.get("chunk_id"):
            hit = next((c for c in st.chunks if c.chunk_id == payload.get("chunk_id")), None)
            if hit is not None:
                chapter = (hit.section or "").split("›")[0].strip()
        if chapter:
            keys = {f"chapter:{chapter}"}
    if not keys:
        raise HTTPException(400, "缺少 kp_ids / node_ids / chapter")

    updated, mastery = _apply_mastery(st, acc, keys, signal)

    if signal == "again" and payload.get("question"):
        st.store.add_wrong(acc, {
            "question": str(payload.get("question") or "")[:2000],
            "wrong_answer": "（自评：还不会）",
            "root_cause": "自评未掌握",
            "trace_ref": str(payload.get("chunk_id") or ""),
            "correct": str(payload.get("explanation") or "")[:4000],
            "pitfall": "",
            "kp_ids": sorted(keys),
            "source": str(payload.get("document_title") or "题卡自评"),
        })

    return {"ok": True, "account": acc, "updated": updated, "mastery": mastery}


# ---------------------------------------------------------------- 历史会话

@app.get("/api/history")
def history(x_account: str | None = Header(default=None)) -> dict:
    st = get_state()
    acc = _account(x_account)
    convs = st.store.list_conversations(acc)
    for c in convs:
        c["title"] = (c.get("title") or "").strip() or "未命名会话"
    return {"ok": True, "conversations": convs}


@app.get("/api/history/{conv_id}")
def history_detail(conv_id: str, x_account: str | None = Header(default=None)) -> dict:
    st = get_state()
    acc = _account(x_account)
    owner = st.store.conversation_owner(conv_id)
    if owner is None:
        raise HTTPException(404, "会话不存在")
    if owner != acc:
        raise HTTPException(403, "无权访问该会话")
    messages = st.store.messages(conv_id)
    artifacts: list[dict] = []
    for m in messages:
        payload = m.get("payload") or {}
        for a in payload.get("artifacts") or []:
            if isinstance(a, dict) and a.get("type"):
                artifacts.append({"artifactType": a["type"], "data": a.get("data") or {}})
    return {"ok": True, "conversation_id": conv_id, "messages": messages, "artifacts": artifacts}


# ---------------------------------------------------------------- 拍题 OCR

@app.post("/api/vision/ocr")
def vision_ocr(payload: dict = Body(...)) -> dict:
    """离线 OCR：接收 dataURL/纯 base64 图片，返回识别文字（拍题/公式）。"""
    raw = str(payload.get("image") or "")
    if not raw:
        raise HTTPException(400, "缺少图片数据")
    try:
        data = base64.b64decode(raw.split(",", 1)[-1])
    except Exception as exc:
        raise HTTPException(400, f"图片解码失败：{exc}") from exc
    try:
        from PIL import Image
        import pytesseract
    except ImportError as exc:
        raise HTTPException(501, "OCR 组件未安装（pip install pytesseract Pillow）") from exc
    try:
        img = Image.open(io.BytesIO(data)).convert("RGB")
    except Exception as exc:
        raise HTTPException(400, f"不支持的图片格式：{exc}") from exc
    # 大图缩到 1800px 内，OCR 更快
    if max(img.size) > 1800:
        ratio = 1800 / max(img.size)
        img = img.resize((int(img.width * ratio), int(img.height * ratio)))
    try:
        text = pytesseract.image_to_string(img, lang="chi_sim+eng")
    except Exception as exc:  # tesseract 未装/语言包缺失
        raise HTTPException(501, f"OCR 不可用：{exc}") from exc
    return {"ok": True, "text": (text or "").strip()[:6000]}


# ---------------------------------------------------------------- 掌握度导入

@app.post("/api/mastery/import")
def mastery_import(payload: dict = Body(...), x_account: str | None = Header(default=None)) -> dict:
    """浏览器本地镜像 → 服务端（Render 重启后恢复掌握度）。"""
    st = get_state()
    acc = _account(x_account)
    items = payload.get("mastery") or {}
    server = dict(st.store.list_mastery(acc))
    merged: dict[str, dict] = {}
    for key, item in items.items():
        if not isinstance(item, dict):
            continue
        srv = server.get(key) or {}
        if float(item.get("last_at") or 0) >= float(srv.get("last_at") or 0):
            merged[key] = item
    if merged:
        st.store.upsert_mastery(acc, merged)
    return {"ok": True, "imported": len(merged), "mastery": dict(st.store.list_mastery(acc))}


# ---------------------------------------------------------------- 复习计划

@app.get("/api/review")
def review(x_account: str | None = Header(default=None)) -> dict:
    """FSRS-lite：按掌握度 + 最近练习时间给出"今天该复习什么"。"""
    st = get_state()
    acc = _account(x_account)
    mastery = st.store.list_mastery(acc)
    kp_to_node = {n.get("kp_id"): n for n in st.nodes if n.get("kp_id")}
    now = time.time()
    due: list[dict] = []
    for key, item in mastery.items():
        if key.startswith("chapter:"):
            label = key.split(":", 1)[1]
        else:
            node = kp_to_node.get(key) or {}
            label = node.get("label") or key
        score = float(item.get("score") or 0)
        state = item.get("state") or "未学"
        last = float(item.get("last_at") or 0)
        interval_days = 1 if state == "需复习" else (3 if score < 0.75 else 7)
        due_at = last + interval_days * 86400
        if due_at <= now:
            due.append({
                "key": key,
                "label": label,
                "state": state,
                "score": round(score, 3),
                "interval_days": interval_days,
                "overdue_days": round((now - due_at) / 86400, 1),
            })
    due.sort(key=lambda x: -x["overdue_days"])
    return {"ok": True, "due": due, "total_tracked": len(mastery)}


# ---------------------------------------------------------------- 模块与图谱


@app.get("/api/modules")
def modules() -> dict:
    return {"modules": [m.model_dump() for m in MODULES]}


GRAPH_LAYERS = [
    {"layer": 1, "name": "基础概念", "desc": "术语、截面、核反应与守恒关系"},
    {"layer": 2, "name": "机理与方程", "desc": "慢化、扩散、点堆、燃耗方程的物理图像"},
    {"layer": 3, "name": "综合计算", "desc": "给定条件能否算对、能否解释工程含义"},
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
def graph(x_account: str | None = Header(default=None)) -> dict:
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

    # 学习者模型：把该账号的掌握度叠加到节点 state 上（图谱颜色随之变化）
    mastery = _mastery_records(_account(x_account))
    if mastery:
        for node in enriched_nodes:
            chapter = (node.get("chapter") or "").strip()
            item = (
                mastery.get(node.get("kp_id") or "")
                or mastery.get(node.get("id") or "")
                or mastery.get(f"chapter:{chapter}")
            )
            if item and item.get("state"):
                node["state"] = item["state"]

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
    """概念辨析成对图（含差异点与随堂题）。"""
    st = get_state()
    return {"pairs": st.pairs, "total": len(st.pairs)}


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

    # 解析 = 用题面去检索教材/知识点原文（习题本身不参与，避免题面噪声）
    refs = st.retriever.search(chunk.text[:160], top_k=3,
                               exclude_roles=["exercise", "answer"])
    hits = [h.model_dump() for h in refs["hits"]]

    return {
        "ok": True,
        "chunk_id": chunk_id,
        "question": chunk.text,
        "section": chunk.section,
        "source": chunk.document_title,
        "explain": (hits[0]["content"] if hits else "本题解析暂未收录。"),
        "refs": [
            {"documentTitle": h["documentTitle"], "section": h["section"],
             "chunkId": h["chunkId"], "score": h["score"]}
            for h in hits
        ],
    }


@app.post("/api/quiz/grade")
def quiz_grade(payload: dict = Body(...), x_account: str | None = Header(default=None)) -> dict:
    """自动判分：学生答案 vs 检索到的参考答案，星火给分 + 回写掌握度/错题本。"""
    from . import llm as llm_mod

    st = get_state()
    acc = _account(x_account)
    chunk_id = str(payload.get("chunk_id") or "")
    student_answer = str(payload.get("student_answer") or "").strip()
    if not chunk_id:
        raise HTTPException(400, "缺少 chunk_id")
    if not student_answer:
        raise HTTPException(400, "请先写下你的答案")
    chunk = next((c for c in st.chunks if c.chunk_id == chunk_id), None)
    if chunk is None:
        raise HTTPException(404, "题目不存在")

    refs = st.retriever.search(chunk.text[:160], top_k=3, exclude_roles=["exercise", "answer"])
    reference = refs["hits"][0].content if refs["hits"] else ""
    result = llm_mod.grade_answer(chunk.text, reference, student_answer)
    score = int(result.get("score") or 0)
    signal = "got" if score >= 60 else "again"
    keys = {k for k in (chunk.kp_ids or []) if k}
    if not keys:
        chapter = (chunk.section or "").split("›")[0].strip()
        keys = {f"chapter:{chapter}"} if chapter else set()
    updated: dict = {}
    if keys:
        updated, _ = _apply_mastery(st, acc, keys, signal, quality=(score / 100.0) if score >= 60 else None)
    if score < 60:
        st.store.add_wrong(acc, {
            "question": chunk.text[:2000],
            "wrong_answer": student_answer[:2000],
            "root_cause": "自动判分未通过",
            "trace_ref": chunk_id,
            "correct": reference[:4000],
            "pitfall": "；".join(result.get("missing") or [])[:1000],
            "kp_ids": sorted(keys),
            "source": chunk.document_title,
        })
    first = next(iter(updated.values()), {})
    return {
        "ok": True,
        "score": score,
        "verdict": result.get("verdict"),
        "feedback": result.get("feedback"),
        "missing": result.get("missing") or [],
        "reference": reference,
        "state": first.get("state"),
        "kp_ids": sorted(keys),
        "mastery": dict(st.store.list_mastery(acc)),
    }


@app.get("/api/quiz")
def quiz_pick(topic: str = "", n: int = 3, x_account: str | None = Header(default=None)) -> dict:
    """从题库抽题（不下发答案）。"""
    from .tools import ToolContext, quiz_from_kb

    st = get_state()
    out = quiz_from_kb(ToolContext(state=st, account=_account(x_account)), topic=topic, n=n)
    return {"ok": out.ok, "summary": out.summary, **out.artifact_data}


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


@app.get("/manifest.webmanifest")
def manifest():
    f = WEB_DIST / "manifest.webmanifest"
    if f.exists():
        return FileResponse(f, media_type="application/manifest+json")
    return JSONResponse({"error": "manifest 缺失"}, status_code=404)


@app.get("/icon.svg")
def app_icon():
    f = WEB_DIST / "icon.svg"
    if f.exists():
        return FileResponse(f, media_type="image/svg+xml")
    return JSONResponse({"error": "icon 缺失"}, status_code=404)


@app.get("/")
def index():
    idx = WEB_DIST / "index.html"
    if idx.exists():
        return FileResponse(idx)
    return JSONResponse(
        {
            "service": "核反应堆物理 AI 助教 Agent",
            "hint": "前端未构建。开发模式请运行 npm run dev（apps/web）；API 见 /docs",
            "api": ["/api/health", "/api/chat", "/api/modules", "/api/graph", "/api/figures"],
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
