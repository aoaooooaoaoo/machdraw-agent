"""费曼追问：把"讲给别人听"做成结构化练习。

不依赖大模型也能工作：
  1. 逐句拆解学生的复述；
  2. 每句按「讲对了 / 表述模糊 / 逻辑跳跃」三色标注；
     - 讲对了：句子里有能在知识库命中的实义术语
     - 表述模糊：含"比较/大概/可能/一些/差不多"这类不可检验的措辞
     - 逻辑跳跃：含"所以/因此/就"但缺少前提，或句子过短无信息量
  3. 针对模糊句生成追问（不给答案）；
  4. 满 3 轮才给总评——防止一轮敷衍过关。

有 API Key 时可以把 `analyze` 换成模型调用，产物结构不变。
"""
from __future__ import annotations

import re

VAGUE_WORDS = (
    "比较", "大概", "可能", "一些", "有点", "差不多", "差不多", "大约", "左右",
    "等等", "之类", "什么的", "基本上", "好像", "应该吧", "一般", "挺", "很",
)
JUMP_WORDS = ("所以", "因此", "于是", "由此可见", "从而")   # 不含"就/然后"：太常见，会把正常句子误判成跳步

_SENT = re.compile(r"(?<=[。；！？，,\n])")


def split_sentences(text: str) -> list[str]:
    """按句号与逗号一起切——学生口头复述常是一整句长串，只按句号切会只剩一句。"""
    out = []
    for s in _SENT.split(text or ""):
        s = s.strip().strip("，,。；;")
        if len(s) >= 4:
            out.append(s)
    return out


def analyze(statement: str, retriever, round_no: int = 1) -> dict:
    """返回 annotation artifact 的 data。

    data = {round, sentence_count, annotations:[{text, label, color, comment, probe}], probes:[...], summary}
    """
    sents = split_sentences(statement)
    annotations = []
    probes = []

    for s in sents:
        res = retriever.search(s, top_k=2, apply_gate=False)
        cov = float(res.get("coverage") or 0.0)
        has_vague = any(w in s for w in VAGUE_WORDS)
        has_jump = any(w in s for w in JUMP_WORDS) and len(s) < 24

        # 判断优先级：先把"说得不清"挑出来——费曼法的目的就是逼出模糊表述，
        # 术语对了但措辞不可检验，仍然不算讲清楚。
        if has_vague:
            label, color = "表述模糊", "amber"
            hit = next(w for w in VAGUE_WORDS if w in s)
            comment = f"「{hit}」这类词不可检验：到底是多少、在什么范围内？"
            probes.append(f"你说的「{s[:14]}…」里的「{hit}」，具体是多少？有没有上限？超过会发生什么？")
        elif has_jump:
            label, color = "逻辑跳跃", "red"
            comment = "这里缺少前提：为什么会得到这个结论？"
            probes.append("你这一步是从哪个前提出发的？如果没有那个前提，结论还成立吗？")
        elif cov >= 0.5:
            label, color, comment = "讲对了", "green", "这段表述能在课程原文里找到对应依据。"
        else:
            label, color, comment = "表述模糊", "amber"
            comment = "没有命中课程术语，也没说清对象与条件。"
            probes.append(f"「{s[:14]}…」——你能换成课程里的术语再说一遍吗？")

        annotations.append({"text": s, "label": label, "color": color, "comment": comment})

    # 故意埋一个错误复述，让学生纠正（参考作品的做法）
    if round_no <= 2 and sents:
        annotations.append({
            "text": "（提示：下面这句是我故意说错的，请你来纠正）" + "复述只要把话说顺就行，不必用课程术语。",
            "label": "待纠正",
            "color": "red",
            "comment": "这句是错的。请用课程概念指出错在哪。",
        })

    score = sum(1 for a in annotations if a["color"] == "green")
    total = max(len(annotations), 1)
    final = round_no >= 3
    summary = (
        f"第 {round_no} 轮：共 {len(sents)} 句，讲对 {score} 句。"
        + ("已满 3 轮，给出总评。" if final else "继续把模糊处讲清楚，至少 3 轮后才给总评。")
    )
    return {
        "round": round_no,
        "final": final,
        "sentence_count": len(sents),
        "coverage": round(score / total, 3),
        "annotations": annotations,
        "probes": probes[:3],
        "summary": summary,
        "score": {"correct": score, "total": total, "level": _level(score, total)},
    }


def _level(score: int, total: int) -> str:
    r = score / max(total, 1)
    if r >= 0.8:
        return "掌握较好"
    if r >= 0.5:
        return "基本会说，但有模糊处"
    return "还没讲清楚，需要回到教材"


def followup_text(result: dict) -> str:
    """把分析结果写成给学生看的追问话术（不直接给答案）。"""
    lines = [f"**{result['summary']}**", ""]
    if result["probes"]:
        lines.append("我按你刚才说的逐句看了一遍，有几处想追问：")
        for i, p in enumerate(result["probes"], 1):
            lines.append(f"{i}. {p}")
        lines.append("")
    wrong = [a for a in result["annotations"] if a["label"] == "待纠正"]
    if wrong:
        # 错句在画布里（红色「待纠正」），不在对话流里。
        # 之前写「我上面故意写了一句」会让学生在中栏找不到 —— 明确指向右栏画布。
        lines.append("另外，我在**右栏画布**里故意写了一句**错的**（红色那句），你先指出它错在哪。")
        lines.append("")
    lines.append("> 本模块只给批改与追问，不给答案——讲清楚比看答案有用。")
    return "\n".join(lines)
