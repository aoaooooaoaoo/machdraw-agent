"""符号规范化层。

机械制图提问大量是符号/数值型（⌀20H7、Ra 3.2、⊥ 0.05、M12×1.5），
纯语义向量对符号几乎无效，因此检索前必须先做符号与全半角归一。

注意：只用于"检索匹配"，展示给用户时仍用原文。
"""
from __future__ import annotations

import re
import unicodedata

# 一个符号可能对应多个码位，全部归到同一个 ASCII 词
_SYMBOL_ALIASES = {
    "⌀": " phi ", "Ø": " phi ", "ø": " phi ", "Φ": " phi ", "φ": " phi ", "Ф": " phi ",
    "±": " pm ", "×": " x ", "✕": " x ", "＊": " * ",
    "°": " deg ", "′": " min ", "´": " min ", "″": " sec ", "〃": " sec ",
    "≤": " le ", "≥": " ge ", "≠": " ne ", "≈": " approx ",
    "⊥": " perp ", "∥": " parallel ", "∠": " angle ", "⌒": " arc ",
    "○": " circle ", "□": " square ", "△": " triangle ",
    "→": " to ", "←": " from ",
    "㎡": " m2 ", "㈠": " 1 ", "㈡": " 2 ",
}

# 单位与常见记号的归一
_UNIT_ALIASES = [
    (re.compile(r"μm|µm|um"), " um "),
    (re.compile(r"mm\b"), " mm "),
    (re.compile(r"Ra\s*([0-9.]+)", re.I), r" ra \1 "),
    (re.compile(r"Rz\s*([0-9.]+)", re.I), r" rz \1 "),
    (re.compile(r"\bRa\b", re.I), " ra "),
    (re.compile(r"\bRz\b", re.I), " rz "),
    (re.compile(r"\bIT(\d{1,2})\b", re.I), r" it \1 "),
]

_DASHES = dict.fromkeys(map(ord, "—–−‐‑‒"), "-")


def to_halfwidth(text: str) -> str:
    """全角 → 半角（NFKC 会把大部分全角字符归一）。"""
    out = []
    for ch in text:
        code = ord(ch)
        if code == 0x3000:          # 全角空格
            out.append(" ")
        elif 0xFF01 <= code <= 0xFF5E:   # 全角 ASCII
            out.append(chr(code - 0xFEE0))
        else:
            out.append(ch)
    return "".join(out)


def normalize(text: str) -> str:
    """检索用归一化：全角→半角、符号→英文词、空白折叠、小写。"""
    if not text:
        return ""
    s = unicodedata.normalize("NFKC", text)
    s = to_halfwidth(s)
    s = s.translate(_DASHES)
    for k, v in _SYMBOL_ALIASES.items():
        if k in s:
            s = s.replace(k, v)
    for pat, rep in _UNIT_ALIASES:
        s = pat.sub(rep, s)
    s = s.lower()
    s = re.sub(r"[ \t\u00a0]+", " ", s)
    return s.strip()


def normalize_keepcase(text: str) -> str:
    """只归符号与全角，不做小写转换（配合代号需要靠大小写区分孔/轴）。"""
    if not text:
        return ""
    s = unicodedata.normalize("NFKC", text)
    s = to_halfwidth(s)
    s = s.translate(_DASHES)
    for k, v in _SYMBOL_ALIASES.items():
        if k in s:
            s = s.replace(k, v)
    return s


_RE_FIT = re.compile(
    r"(\d+(?:\.\d+)?)\s*([A-Za-z]{1,2}\d{1,2})(?:\s*/\s*([A-Za-z]{1,2}\d{1,2}))?"
)


def extract_fit_spec(text: str) -> dict | None:
    """从自然语言里抓配合代号，如 "Φ30 H7/k6"、"30H7-k6"、"Φ50h6"。

    返回 {"phi": float, "hole": str|None, "shaft": str|None} 或 None。
    孔径代号大写、轴径代号小写——原文的大小写本身就是判据，所以这里不能先 lower()。
    """
    if not text:
        return None
    raw = unicodedata.normalize("NFKC", text)
    has_phi = any(ch in raw for ch in "⌀ØøΦφФ")
    s = normalize_keepcase(raw)

    best = None
    for m in _RE_FIT.finditer(s):
        phi_s, g2, g3 = m.group(1), m.group(2), m.group(3)
        if g3:
            hole, shaft = g2.upper(), g3.lower()
            best = (float(phi_s), hole, shaft)
            break
        # 单个代号：靠大小写判断是孔还是轴
        if g2[0].isupper() and (has_phi or re.search(r"[/\-]\s*[a-z]{1,2}\d", s)):
            best = (float(phi_s), g2.upper(), None)
            break
        if g2[0].islower():
            best = (float(phi_s), None, g2.lower())
            break
    if best is None:
        return None
    phi, hole, shaft = best
    if not has_phi and hole is None and shaft is None:
        return None
    return {"phi": phi, "hole": hole, "shaft": shaft}


def extract_thread_spec(text: str) -> str | None:
    """从文本抓螺纹标记，如 M10、M10×1.5、M20-6H、Tr24×5、G1/2。"""
    if not text:
        return None
    s = unicodedata.normalize("NFKC", text)
    m = re.search(r"\b(M|Tr|G)\s?(\d+(?:\.\d+)?)(?:\s*[x×*]\s*(\d+(?:\.\d+)?))?", s, re.I)
    if not m:
        return None
    kind = m.group(1)
    kind = "M" if kind.lower() == "m" else kind
    out = f"{kind}{m.group(2)}"
    if m.group(3):
        out += f"×{m.group(3)}"
    return out
