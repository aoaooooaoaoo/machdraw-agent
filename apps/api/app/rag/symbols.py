"""符号规范化层（核反应堆物理）。

核反应堆物理的提问里同时混着中文术语、希腊字母符号、上下标、单位与数值
（k_eff、ρ=200 pcm、Φ=3×10¹³ cm⁻²s⁻¹、Σ_a、M²=L²+τ、1/v、10 MWd/tU），
纯语义分词对符号几乎无效，因此检索前必须先做符号与全半角归一。

归一规则的目标只有一个：**让"同一个概念的十种写法"落到同一个词元上**。
展示给用户时仍用原文。

注意：这里只做"检索匹配"用的归一，不改变语义；也不做单位换算。
"""
from __future__ import annotations

import re
import unicodedata

# ------------------------------------------------------------------ 希腊字母
# 映射成英文单词（而不是删掉），这样 "Σ_a" 与 "宏观截面" 至少能在 ASCII 通道命中。
_GREEK = {
    "α": " alpha ", "β": " beta ", "γ": " gamma ", "Γ": " gamma ",
    "δ": " delta ", "Δ": " delta ", "ε": " epsilon ", "ζ": " zeta ",
    "η": " eta ", "θ": " theta ", "Θ": " theta ", "κ": " kappa ",
    "λ": " lambda ", "Λ": " lambda ", "μ": " mu ", "ν": " nu ",
    "ξ": " xi ", "π": " pi ", "ρ": " rho ", "σ": " sigma ", "Σ": " sigma ",
    "τ": " tau ", "φ": " phi ", "Φ": " phi ", "χ": " chi ", "ψ": " psi ",
    "ω": " omega ", "Ω": " omega ", "ℓ": " l ",
}

# 常用数学/物理记号
_SYMBOL_ALIASES = {
    "×": " x ", "✕": " x ", "＊": " * ", "·": " ", "⋅": " ",
    "≤": " le ", "≥": " ge ", "≠": " ne ", "≈": " approx ", "∼": " approx ", "∝": " prop ",
    "→": " to ", "←": " from ", "⇒": " to ", "⇔": " eq ",
    "∞": " inf ", "±": " pm ", "℃": " c ", "°C": " c ", "°": " deg ",
    "²": " 2 ", "³": " 3 ", "⁻": " - ", "₁": " 1 ", "₂": " 2 ", "₃": " 3 ",
}

# 单位 / 量的写法归一（在 normalize 里逐个正则替换）
_UNIT_ALIASES = [
    (re.compile(r"\b(mev|kev|ev|gev)\b", re.I), r" \1 "),
    (re.compile(r"\bcm\s*[-^]?\s*2\b", re.I), " cm2 "),
    (re.compile(r"\bcm\s*[-^]?\s*3\b", re.I), " cm3 "),
    (re.compile(r"\bs\s*[-^]?\s*1\b", re.I), " s-1 "),
    (re.compile(r"\b(mwd|gwd)\s*/\s*t\s*u\b", re.I), " mwd/tu "),
    (re.compile(r"\bpcm\b", re.I), " pcm "),
    (re.compile(r"\bmk\b", re.I), " mk "),
    (re.compile(r"\bbarn(s)?\b", re.I), " b "),
    (re.compile(r"\b(w|kw|mw)\s*/\s*(cm2|cm3)\b", re.I), lambda m: f" {m.group(1)}/{m.group(2)} "),
]

# 概念别名的归一：同一概念的常见写法合并成同一个 ASCII 词元。
# 例如 "k_eff / k-eff / keff / K有效 / 有效增殖系数" 统一成 " keff "。
_CONCEPT_ALIASES = [
    # ---- 增殖系数与反应性
    (re.compile(r"\bk[\s_\-]*(?:eff|有效)", re.I), " keff "),
    (re.compile(r"\bk[\s_\-]*(?:inf|∞|无限)", re.I), " kinf "),
    (re.compile(r"有效增殖(?:系数|因子)"), " keff "),
    (re.compile(r"无限(?:介质)?增殖(?:系数|因子)"), " kinf "),
    (re.compile(r"\breactivity\b", re.I), " rho "),
    (re.compile(r"反应性"), " rho "),
    (re.compile(r"(裂变| fission)\s*(微观|宏观)?\s*(截面|cross\s*section)", re.I), " sigmaf "),
    (re.compile(r"(吸收|absorption)\s*(微观|宏观)?\s*(截面|cross\s*section)", re.I), " sigmaa "),
    (re.compile(r"(散射|scattering)\s*(微观|宏观)?\s*(截面|cross\s*section)", re.I), " sigmas "),
    # ---- 核素写法：U-235 / U235 / 235U / u235 统一成 u235
    (re.compile(r"\bu[\s_\-]*235\b", re.I), " u235 "),
    (re.compile(r"\b235\s*u\b", re.I), " u235 "),
    (re.compile(r"\bu[\s_\-]*238\b", re.I), " u238 "),
    (re.compile(r"\b238\s*u\b", re.I), " u238 "),
    (re.compile(r"\bpu[\s_\-]*239\b", re.I), " pu239 "),
    (re.compile(r"\b239\s*pu\b", re.I), " pu239 "),
    (re.compile(r"\bth[\s_\-]*232\b", re.I), " th232 "),
    (re.compile(r"\bxe[\s_\-]*135\b", re.I), " xe135 "),
    (re.compile(r"\bi[\s_\-]*135\b", re.I), " i135 "),
    (re.compile(r"\bsm[\s_\-]*149\b", re.I), " sm149 "),
    (re.compile(r"\bpm[\s_\-]*149\b", re.I), " pm149 "),
    # ---- 常见符号写法
    (re.compile(r"\bm\s*2\b", re.I), " m2 "),
    (re.compile(r"\bl\s*2\b", re.I), " l2 "),
    (re.compile(r"\b1\s*/\s*v\b", re.I), " 1v "),
    (re.compile(r"\bn\s*/\s*n0\b", re.I), " n n0 "),
    (re.compile(r"\bβ[\s_\-]*eff\b", re.I), " betaeff "),
    (re.compile(r"\bβ[\s_\-]*i\b", re.I), " betai "),
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


def _apply(text: str, keepcase: bool = False) -> str:
    s = unicodedata.normalize("NFKC", text)   # 全角、上标数字、兼容字符
    s = to_halfwidth(s)
    s = s.translate(_DASHES)
    for k, v in _GREEK.items():
        if k in s:
            s = s.replace(k, v)
    for k, v in _SYMBOL_ALIASES.items():
        if k in s:
            s = s.replace(k, v)
    for pat, rep in _UNIT_ALIASES:
        s = pat.sub(rep, s)
    for pat, rep in _CONCEPT_ALIASES:
        if callable(rep):
            s = pat.sub(rep, s)
        else:
            s = pat.sub(rep, s)
    s = re.sub(r"[ \t\u00a0]+", " ", s)
    if not keepcase:
        s = s.lower()
    return s.strip()


def normalize(text: str) -> str:
    """检索用归一化：全角→半角、希腊字母→英文词、概念别名→统一词元、空白折叠、小写。"""
    if not text:
        return ""
    return _apply(text, keepcase=False)


def normalize_keepcase(text: str) -> str:
    """只归符号与全角，不做小写转换（核素/单位大小写有时有意义）。"""
    if not text:
        return ""
    return _apply(text, keepcase=True)
