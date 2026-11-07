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

from .config import GATE_TAU, LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, LLM_PROVIDER
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
            "（例如：三视图、剖视图、尺寸标注、表面结构、极限与配合、螺纹画法）。"
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
        ref = f"《{h['documentTitle']}》"
        if h.get("section"):
            ref += f" · {h['section']}"
        if h.get("kbNo"):
            ref += f" · {h['kbNo']}"
        if ref in seen:
            continue
        seen.add(ref)
        lines.append(f"- {ref}（chunk `{h['chunkId']}`，相关度 {h['score']:.3f}）")

    if coverage < 0.75:
        lines += [
            "",
            "**需要说明的一点**：这个话题在课程资料里覆盖得不算充分（关键词覆盖率 "
            f"{coverage:.0%}），上面的回答只基于检索到的原文，没有做课程以外的补充。",
        ]
    return "\n".join(lines)


# ------------------------------------------------------------------ 真实模型


def _http_chat(messages: list[dict], temperature: float = 0.2) -> str:
    payload = json.dumps(
        {
            "model": LLM_MODEL,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
        },
        ensure_ascii=False,
    ).encode("utf-8")
    req = urllib.request.Request(
        f"{LLM_BASE_URL.rstrip('/')}/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {LLM_API_KEY}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


SYSTEM_PROMPT = (
    "你是机械制图课程的助教。只能依据下面提供的【课程证据】作答，"
    "不得使用课程以外的知识，不得编造国标号、数值或页码。"
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

    ctx = "\n\n".join(
        f"【证据{i+1}】《{h['documentTitle']}》· {h.get('section','')}\n{h['content']}"
        for i, h in enumerate(hits)
    )
    try:
        system = SYSTEM_PROMPT + ("\n\n" + persona if persona else "")
        text = _http_chat(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": f"【课程证据】\n{ctx}\n\n【学生提问】\n{query}"},
            ]
        )
        return LLMResult(text=text, provider=provider, model=LLM_MODEL)
    except (urllib.error.URLError, KeyError, TimeoutError, OSError) as exc:
        # 失败时优雅降级到本地抽取，不让对话中断
        return LLMResult(
            text=mock_answer(query, hits, gated, coverage)
            + f"\n\n> ⚠ 模型调用失败（{type(exc).__name__}），已自动降级为本地证据抽取模式。",
            provider="mock-fallback",
            model="extractive-local",
        )
