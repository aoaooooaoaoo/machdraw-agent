"""LLM 适配层。

三种模式：
  · mock      —— 无 API Key 时的本地抽取式作答：从证据句子里抽最相关的，按模板组织。
                 不编造、不改写事实，等价于参考作品的"本地资料检索，未调用大模型"模式。
  · deepseek / openai-compatible —— 有 Key 时走真实模型（OpenAI 兼容协议）。

设计意图：**没有 Key 系统也能完整跑通并演示**，这是可复现性的前提。
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass

from .config import (
    GATE_TAU,
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_EXTRA_BODY,
    LLM_MODEL,
    LLM_PROVIDER,
    LLM_TIMEOUT,
)
from .rag.tokenize import tokenize
from .rag.symbols import normalize


@dataclass
class LLMResult:
    text: str
    provider: str
    model: str


# ------------------------------------------------------------------ mock


_SENT_SPLIT = re.compile(r"(?<=[。；！？\n])")


def _sentences(text: str) -> list[str]:
    """切句并过滤掉 Markdown 表格行/分隔线——表格行单独拿出来当结论很难读。"""
    out = []
    for s in _SENT_SPLIT.split(text):
        s = s.strip().lstrip("·-*# ").strip()
        if len(s) < 10:
            continue
        if s.startswith("|") or set(s) <= set("|-: "):
            continue
        if s.count("|") >= 2:      # 表格行
            continue
        out.append(s)
    return out


def _pick_sentences(
    query: str, evidence_texts: list[str], limit: int = 4, scores: list[float] | None = None
) -> list[tuple[str, int]]:
    """按「与提问的词元重叠」×「所在证据的相关度」挑句子，返回 [(句子, 证据序号)]。"""
    q = set(tokenize(query))
    scored: list[tuple[float, str, int, int]] = []
    for ei, text in enumerate(evidence_texts):
        ew = 1.0 if not scores else 0.5 + float(scores[ei])
        for pos, s in enumerate(_sentences(text)):
            st = set(tokenize(s))
            if not st:
                continue
            overlap = len(q & st) / (len(q) ** 0.5 + 1e-6)
            if overlap <= 0:
                continue
            scored.append((overlap * ew, s, ei, pos))
    scored.sort(key=lambda x: -x[0])
    picked = scored[:limit]
    picked.sort(key=lambda x: (x[2], x[3]))       # 还原证据顺序
    return [(s, ei) for _, s, ei, _ in picked]


def mock_answer(query: str, hits: list[dict], gated: bool, coverage: float) -> str:
    q = query.strip().rstrip("？?。！!，,、 ")
    if not hits:
        return (
            "**知识库未收录**\n\n"
            f"本课程知识库里没有检索到与「{q}」相关的内容。\n\n"
            "我不代为补充课程以外的说法。可以换个说法再问，或换一个课程内的关键词"
            "（例如：有效增殖系数、缓发中子、多普勒展宽、点堆动力学、氙中毒、"
            "燃耗深度、控制棒价值、中子能谱）。"
        )

    if gated:
        return (
            "**知识库未收录**\n\n"
            f"就「{q}」而言，课程资料里只检索到边缘相关的内容（关键词覆盖率 "
            f"{coverage:.0%}，低于 {GATE_TAU} 的门限），不足以支撑一个可靠回答。\n\n"
            "按本课程的范围约束，我不使用课程以外的知识作答，也不代为补充。"
            "如果你确认这个问题属于本课程，可以换用课程里的术语再问一次。"
        )

    texts = [h["content"] for h in hits]
    scores = [float(h.get("score") or 0.0) for h in hits]
    picked = _pick_sentences(query, texts, limit=4, scores=scores)
    if not picked:
        picked = [(_sentences(texts[0])[0], 0)] if _sentences(texts[0]) else [(texts[0][:160], 0)]

    head = picked[0][0]
    rest = picked[1:]

    lines = [f"**结论**：{head}", ""]
    if rest:
        lines.append("**依据**：")
        for s, ei in rest:
            h = hits[ei]
            ref = f"《{h['documentTitle']}》"
            if h.get("section"):
                ref += f" · {h['section']}"
            lines.append(f"- {s}（出处：{ref}）")
        lines.append("")

    lines.append("**出处**：")
    seen = set()
    for h in hits[:3]:
        # ⚠ 这里原本是 h['documentTitle'] / h['chunkId'] / h['score'] 硬索引。
        # 这是**降级路径**（模型调用失败时才走到），一旦某个字段缺失就 KeyError 把请求打成 500 ——
        # 降级本身失败比不降级更糟。全部改成 .get 兜底。
        ref = f"《{h.get('documentTitle') or h.get('docId') or '未知文档'}》"
        if h.get("section"):
            ref += f" · {h['section']}"
        if h.get("kbNo"):
            ref += f" · {h['kbNo']}"
        if ref in seen:
            continue
        seen.add(ref)
        chunk = h.get("chunkId") or h.get("chunk_id") or "?"
        try:
            score = float(h.get("score") or 0.0)
        except (TypeError, ValueError):
            score = 0.0
        lines.append(f"- {ref}（chunk `{chunk}`，相关度 {score:.3f}）")

    if coverage < 0.75:
        lines += [
            "",
            "**需要说明的一点**：这个话题在课程资料里覆盖得不算充分（关键词覆盖率 "
            f"{coverage:.0%}），上面的回答只基于检索到的原文，没有做课程以外的补充。",
        ]
    return "\n".join(lines)


# ------------------------------------------------------------------ 真实模型


def _extra_body() -> dict:
    """把 RP_LLM_EXTRA_BODY 解析成 dict（解析失败就当没有，不影响主流程）。"""
    raw = (LLM_EXTRA_BODY or "").strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def _http_chat(messages: list[dict], temperature: float = 0.2, timeout: float | None = None) -> str:
    body = {
        "model": LLM_MODEL,
        "messages": messages,
        "temperature": temperature,
        "stream": False,
    }
    body.update(_extra_body())      # 例如关闭推理模型的思维链
    payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        f"{LLM_BASE_URL.rstrip('/')}/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {LLM_API_KEY}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout or LLM_TIMEOUT) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


SYSTEM_PROMPT = (
    "你是《核反应堆物理》课程的助教。只能依据下面提供的【课程证据】作答，"
    "不得使用课程以外的知识，不得编造公式、常数、核数据或页码。"
    "涉及数值计算时，数值必须来自检索证据或确定性工具的结果，不得自行推算。"
    "回答后用“出处：”列出所用证据的文档名与章节。"
    "如果证据不足以回答，直接说明“知识库未收录”，不要猜。"
)


def generate(query: str, hits: list[dict], gated: bool, coverage: float,
             persona: str = "") -> LLMResult:
    provider = LLM_PROVIDER
    if provider == "mock" or not LLM_API_KEY:
        return LLMResult(
            text=mock_answer(query, hits, gated, coverage),
            provider="mock",
            model="extractive-local",
        )

    # 同上：证据字段用 .get 兜底，避免上游数据结构变动直接把整条链路打崩
    ctx = "\n\n".join(
        f"【证据{i+1}】《{h.get('documentTitle') or h.get('docId') or '未知文档'}》"
        f"· {h.get('section', '')}\n{h.get('content', '')}"
        for i, h in enumerate(hits)
    )
    cache_key = _cache_key(query, ctx, persona)
    cached = _cache_get(cache_key)
    if cached:
        return LLMResult(text=cached, provider="cache", model=LLM_MODEL)

    system = SYSTEM_PROMPT + ("\n\n" + persona if persona else "")
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"【课程证据】\n{ctx}\n\n【学生提问】\n{query}"},
    ]
    last_exc: Exception | None = None
    for attempt in range(2):          # 超时/网络错误重试一次，再降级
        try:
            text = _http_chat(messages)
            _cache_put(cache_key, text)
            return LLMResult(text=text, provider=provider, model=LLM_MODEL)
        except (urllib.error.URLError, KeyError, TimeoutError, OSError) as exc:
            last_exc = exc
            if attempt == 0:
                continue
    # 失败时优雅降级到本地抽取，不让对话中断
    return LLMResult(
        text=mock_answer(query, hits, gated, coverage)
        + f"\n\n> ⚠ 模型调用失败（{type(last_exc).__name__ if last_exc else 'unknown'}），已自动降级为本地证据抽取模式。",
        provider="mock-fallback",
        model="extractive-local",
    )


# ------------------------------------------------------------------ 语义缓存
# 相同问题 + 相同证据 + 相同 persona → 直接复用上一次模型回答，省 10–18s 和 token。
import hashlib
from collections import OrderedDict

_ANSWER_CACHE: "OrderedDict[str, str]" = OrderedDict()
_ANSWER_CACHE_MAX = 128


def _cache_key(query: str, ctx: str, persona: str) -> str:
    h = hashlib.sha1()
    h.update((query.strip() + "\x00" + ctx + "\x00" + persona).encode("utf-8"))
    return h.hexdigest()


def _cache_get(key: str) -> str | None:
    val = _ANSWER_CACHE.get(key)
    if val is None:
        return None
    _ANSWER_CACHE.move_to_end(key)
    return val


def _cache_put(key: str, text: str) -> None:
    if not text.strip():
        return
    _ANSWER_CACHE[key] = text
    _ANSWER_CACHE.move_to_end(key)
    while len(_ANSWER_CACHE) > _ANSWER_CACHE_MAX:
        _ANSWER_CACHE.popitem(last=False)


def cache_stats() -> dict:
    return {"size": len(_ANSWER_CACHE), "max": _ANSWER_CACHE_MAX}


# ------------------------------------------------------------------ 自动判分


def grade_answer(question: str, reference: str, student_answer: str) -> dict:
    """用模型按"参考答案/评分点"判分；失败时用关键词重叠做保守兜底。

    返回：{score: 0-100, verdict: pass|partial|fail, feedback, missing[]}
    """
    q = (question or "").strip()
    ref = (reference or "").strip()
    ans = (student_answer or "").strip()
    if not ans:
        return {"score": 0, "verdict": "fail", "feedback": "没有填写答案。", "missing": []}
    if LLM_PROVIDER != "mock" and LLM_API_KEY:
        prompt = (
            "你是核反应堆物理课程的阅卷助教。请对照【参考答案】给学生答案打分。\n"
            "只输出 JSON，不要 markdown：\n"
            '{"score": 0-100 的整数, "verdict": "pass|partial|fail", '
            '"feedback": "两三句话，指出对在哪、错在哪", "missing": ["漏掉的评分点"]}\n'
            "评分标准：核心概念/公式正确 60 分起；数值与单位正确再加；关键步骤缺失给 partial。\n\n"
            f"【题目】\n{q[:1200]}\n\n【参考答案】\n{ref[:3000]}\n\n【学生答案】\n{ans[:2000]}"
        )
        try:
            raw = _http_chat(
                [{"role": "system", "content": "你只输出 JSON，不要任何解释或代码块。"},
                 {"role": "user", "content": prompt}],
                temperature=0.1,
                timeout=min(45.0, LLM_TIMEOUT),
            )
            data = _parse_json_object(raw)
            if data:
                score = int(max(0, min(100, float(data.get("score", 0)))))
                verdict = str(data.get("verdict") or ("pass" if score >= 60 else "fail"))
                if verdict not in ("pass", "partial", "fail"):
                    verdict = "pass" if score >= 60 else "fail"
                missing = data.get("missing") or []
                if not isinstance(missing, list):
                    missing = []
                return {
                    "score": score,
                    "verdict": verdict,
                    "feedback": str(data.get("feedback") or ""),
                    "missing": [str(x) for x in missing[:6]],
                }
        except Exception:
            pass
    # 兜底：关键词覆盖率
    q_tokens = set(tokenize(q))
    ref_tokens = set(tokenize(ref))
    ans_tokens = set(tokenize(ans))
    key_tokens = {t for t in ref_tokens - q_tokens if len(t) >= 2}
    if not key_tokens:
        score = 60 if ans else 0
    else:
        hit = len(key_tokens & ans_tokens) / len(key_tokens)
        score = int(round(min(100, hit * 100)))
    verdict = "pass" if score >= 60 else ("partial" if score >= 30 else "fail")
    missing = [t for t in sorted(key_tokens - ans_tokens)][:6]
    return {
        "score": score,
        "verdict": verdict,
        "feedback": "模型判分不可用，已按关键词覆盖做保守估计；建议对照解析自查。" if LLM_PROVIDER != "mock" else "本地关键词判分（未接模型）。",
        "missing": missing,
    }


def _parse_json_object(raw: str) -> dict | None:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", text)
        if not m:
            return None
        try:
            data = json.loads(m.group(0))
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            return None
