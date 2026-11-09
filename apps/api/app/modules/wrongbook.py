"""错题六步诊改：原题 → 错误作答 → 根因 → 溯源 → 正解 → 避坑。

参考作品的核心教学机制（docs/02 §2.5）。这里不依赖大模型：
  · 溯源 / 正解 都由知识库检索给出，带四级出处；
  · 根因按"措辞线索 + 命中内容"归类到 6 类；
  · 避坑取命中段里的「易错」「注意」「不应」「不得」等句。
"""
from __future__ import annotations

import re

ROOT_CAUSES = {
    "概念混淆": ("混淆", "分不清", "以为", "当成", "搞混", "一样", "相同", "记成"),
    "公式误用": ("公式", "代入", "套", "系数", "记错", "用错"),
    "忽略假设与边界条件": ("忘了", "漏了", "忽略", "没注意", "边界条件", "假设", "适用条件"),
    "单位与量纲错误": ("单位", "量纲", "数量级", "pcm", "换算", "量级"),
    "计算失误": ("算错", "数错", "加错", "小数点", "算反"),
    "物理图像偏差": ("想象", "趋势", "方向", "符号", "想不出", "画不出"),
    "其他": (),
}

PITFALL_PAT = re.compile(r"[^。；\n]*(?:易错|注意|不应|不得|不能|避免|常见错误)[^。；\n]*[。；]?")


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[。；\n])", text) if len(s.strip()) >= 8]


def classify_root_cause(question: str, wrong_answer: str = "") -> str:
    blob = f"{question} {wrong_answer}"
    for name, words in ROOT_CAUSES.items():
        if any(w in blob for w in words):
            return name
    return "概念混淆"


def _pits(hits: list[dict], used: str = "") -> list[str]:
    """取命中段里的易错提醒句；跳过已经被"正解"用过的句子，避免两栏重复。"""
    out: list[str] = []
    for h in hits:
        for m in PITFALL_PAT.findall(h["content"]):
            m = m.strip()
            if not (8 <= len(m) <= 120):
                continue
            if used and (m[:16] in used or used[:16] in m):
                continue
            if m not in out:
                out.append(m)
        if len(out) >= 3:
            break
    return out[:3]


def six_step(retriever, question: str, wrong_answer: str = "", kp_ids: list[str] | None = None) -> dict:
    """返回 wrongbook artifact 的 data。"""
    res = retriever.search(question, top_k=4)
    hits = [h.model_dump() for h in res["hits"]]
    gated = bool(res.get("gated"))
    coverage = float(res.get("coverage") or 0.0)

    root = classify_root_cause(question, wrong_answer)
    trace = [
        {
            "ref": f"《{h['documentTitle']}》 · {h['section']}",
            "chunk_id": h["chunkId"],
            "score": h["score"],
            "text": h["content"][:400],
        }
        for h in hits[:3]
    ]

    correct = ""
    if hits:
        sents = _sentences(hits[0]["content"])
        correct = " ".join(sents[:2]) if sents else hits[0]["content"][:200]

    pits = _pits(hits, used=correct)

    steps = [
        {"n": 1, "key": "原题", "value": question or "（未提供）"},
        {"n": 2, "key": "错误作答", "value": wrong_answer or "（未提供，按典型错误推断）"},
        {"n": 3, "key": "根因", "value": root},
        {"n": 4, "key": "溯源", "value": "见下方出处卡片"},
        {"n": 5, "key": "正解", "value": correct or "知识库未收录，未代为补充"},
        {"n": 6, "key": "避坑", "value": "；".join(pits) if pits else "（本段没有显式的易错提醒）"},
    ]

    return {
        "question": question,
        "wrong_answer": wrong_answer,
        "root_cause": root,
        "root_causes_all": list(ROOT_CAUSES.keys()),
        "steps": steps,
        "trace": trace,
        "pitfalls": pits,
        "kp_ids": kp_ids or [],
        "coverage": coverage,
        "gated": gated,
        "note": (
            "本诊断只依据课程原文；知识库未收录时不会代为补充。"
            if not gated
            else "检索覆盖率偏低，正解可能不完整——建议教师复核。"
        ),
    }


def render_markdown(data: dict) -> str:
    lines = [f"**错题六步诊改：{data['question'][:40]}**", ""]
    for s in data["steps"]:
        lines.append(f"**{s['n']}. {s['key']}**：{s['value']}")
        lines.append("")
    if data["trace"]:
        lines.append("**出处**：")
        for t in data["trace"]:
            lines.append(f"- {t['ref']}（chunk `{t['chunk_id']}`，相关度 {t['score']:.3f}）")
    if data["note"]:
        lines += ["", f"> {data['note']}"]
    return "\n".join(lines)
