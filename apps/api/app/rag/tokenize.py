"""中文分词（BM25 / 覆盖率共用）。

用 jieba 搜索模式分词；未安装 jieba 时自动降级为「单字 + 相邻二元组」。
降级模式可用，但二元组会跨越词边界（"图的""的投"），产生噪声匹配——
所以生产环境应安装 jieba（纯 Python，无编译依赖）。
"""
from __future__ import annotations

import re

from .symbols import normalize

_CJK = r"\u4e00-\u9fff"
_RE_ASCII = re.compile(r"[a-z]+[0-9]*|[0-9]+[a-z]*|[0-9]+(?:\.[0-9]+)?")
_RE_CJK = re.compile(f"[{_CJK}]+")

try:  # pragma: no cover
    import jieba

    jieba.setLogLevel(60)
    _HAS_JIEBA = True
except ImportError:  # pragma: no cover
    _HAS_JIEBA = False


_CURATED_TERMS = (
    "反应堆", "堆芯", "链式裂变反应", "自持链式反应", "有效增殖系数", "无限介质增殖系数",
    "不泄漏概率", "临界条件", "临界尺寸", "临界质量", "反应性", "缓发中子", "瞬发中子",
    "缓发中子先驱核", "裂变碎片", "易裂变核素", "可裂变核素", "可转换核燃料", "富集度",
    "微观截面", "宏观截面", "平均自由程", "核反应率", "中子注量率", "中子密度", "中子流密度",
    "共振峰", "共振能", "多普勒展宽", "多普勒效应", "能量自屏", "空间自屏", "逃脱共振吸收",
    "热中子利用系数", "快中子倍增系数", "慢化不泄漏概率", "扩散不泄漏概率",
    "四因子公式", "六因子公式", "慢化剂", "慢化能力", "慢化比", "平均对数能降",
    "平均散射角余弦", "扩散系数", "斐克定律", "扩散方程", "边界条件", "外推距离",
    "外推边界", "扩散长度", "慢化长度", "徙动长度", "中子年龄", "移出截面",
    "反射层", "反射层节省", "材料曲率", "几何曲率", "单群扩散", "多群扩散", "双群扩散",
    "亥姆霍兹方程", "功率分布", "功率不均匀系数", "中子能谱", "裂变中子能谱", "慢化能谱",
    "费米谱", "共振能谱", "热中子能谱", "谱硬化", "最可几速度", "丹可夫效应",
    "首次飞行逃脱概率", "水铀比", "过慢化", "欠慢化", "群常数", "能群", "压水堆", "沸水堆",
    "燃耗", "燃耗链", "燃耗深度", "卸料燃耗", "堆芯寿期", "转化比", "裂变产物",
    "氙中毒", "碘坑", "氙振荡", "钐中毒", "饱和裂变产物", "非饱和裂变产物",
    "剩余反应性", "反应性系数", "温度系数", "燃料温度系数", "慢化剂温度系数",
    "空泡系数", "功率系数", "功率亏损", "控制棒", "控制棒价值", "微分价值", "积分价值",
    "硼微分价值", "临界硼浓度", "可燃毒物", "可溶硼", "停堆裕量", "黑棒", "灰棒",
    "点堆动力学", "倒时方程", "反应堆周期", "瞬发临界", "中子寿命", "瞬发中子寿命",
    "阶跃反应性", "功率响应", "燃料管理", "循环长度", "换料周期", "初始循环",
    "平衡循环", "过渡循环", "扰动循环", "低泄漏换料", "堆芯核设计", "组件布置",
    "径向功率分布", "轴向功率分布",
)


def _load_domain_dict() -> list[str]:
    """从知识库自身抽取领域术语，喂给 jieba 当用户词典。

    不加载的话「封闭环」会被切成「封闭 / 环」、「共有点」切成「共有 / 点」、
    「尺寸界线」切成「尺寸 / 界线」——术语被切碎后，检索与门控都会明显变差。
    术语来源（不需要手工维护第二份词表）：
      ① kb/knowledge/kp.jsonl 的 term / aliases；
      ② kb/figures/figures.jsonl 的 structure_tags；
      ③ kb/**/*.md 的章节标题（去掉编号后的那个短语往往就是术语）；
      ④ 一小份跨文档的通用术语补充（标题里未必出现，但提问会用到）。
    """
    import json
    from pathlib import Path

    try:
        from ..config import KB_DIR
    except Exception:  # pragma: no cover
        return []

    words: dict[str, None] = {}

    def add(w: str) -> None:
        w = (w or "").strip().strip("：:、，,（）()")
        if 2 <= len(w) <= 12 and re.fullmatch(f"[{_CJK}A-Za-z0-9]+", w):
            words.setdefault(w, None)

    kp = Path(KB_DIR) / "knowledge" / "kp.jsonl"
    if kp.exists():
        for line in kp.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            add(rec.get("term"))
            for w in rec.get("aliases") or []:
                add(w)

    fig = Path(KB_DIR) / "figures" / "figures.jsonl"
    if fig.exists():
        for line in fig.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            for w in rec.get("structure_tags") or []:
                add(w)

    # 章节标题：`## 2.3 尺寸链的组成` → 去掉编号后剩下的短语
    _heading = re.compile(r"^#{2,4}\s*(?:[0-9]+(?:[.．][0-9]+)*\s*)?(.+)$")
    for md in Path(KB_DIR).rglob("*.md"):
        try:
            for line in md.read_text(encoding="utf-8").splitlines():
                m = _heading.match(line.strip())
                if m:
                    title = m.group(1).strip()
                    # 标题里常见 "A与B的C" 这类长串，取整体 + 括号前的部分
                    add(title.split("（")[0])
                    for part in re.split(r"[、，,与和及/]", title):
                        add(part)
        except (OSError, UnicodeDecodeError):
            continue

    for w in _CURATED_TERMS:
        add(w)
    return list(words)


_DOMAIN_TERMS: list[str] = []
if _HAS_JIEBA:
    _DOMAIN_TERMS = _load_domain_dict()
    for _w in _DOMAIN_TERMS:
        # add_word(word, freq, tag)：给一个偏高词频，让 jieba 优先整体切出
        jieba.add_word(_w, freq=20000)


def tokenize(text: str) -> list[str]:
    """返回词元列表（含重复，BM25 需要 tf）。"""
    if not text:
        return []
    s = normalize(text)

    toks: list[str] = [m.group() for m in _RE_ASCII.finditer(s)]

    runs = _RE_CJK.findall(s)
    if not runs:
        return toks
    joined = " ".join(runs)

    if _HAS_JIEBA:
        for w in jieba.lcut_for_search(joined):
            w = w.strip()
            if not w or not _RE_CJK.match(w[0]):
                continue
            toks.append(w)
        return toks

    # 降级：单字 + 二元组
    for run in runs:
        toks.extend(run)
        if len(run) > 1:
            toks.extend(run[i: i + 2] for i in range(len(run) - 1))
    return toks


def unique_tokens(text: str) -> list[str]:
    seen: dict[str, None] = {}
    for t in tokenize(text):
        seen.setdefault(t, None)
    return list(seen)


# 虚词/疑问词字符集。整词全部由这些字组成时，视为"无实义词"。
_FUNC_CHARS = set(
    "的了是在和有与及或那么呢吗吧啊嘛哦嗯就都也还又而且之其这那哪个些么什怎样如何"
    "为以于对从到把被给让使需可要能会应请我你他她它们一下中里外时便再很最更吗"
)

# 通用提问词：任何学科都会问，不承载领域信息。参与覆盖率只会稀释指标。
_GENERIC_WORDS = {
    "意思", "含义", "解释", "说明", "介绍", "举例", "例子", "区别", "差别", "关系",
    "作用", "原因", "特点", "优点", "缺点", "方法", "步骤", "如何", "怎么", "怎样",
    "什么", "哪些", "哪个", "为什么", "多少", "是否", "可以", "需要", "应该",
    "一下", "请问", "告诉", "讲讲", "说说", "通俗", "简单", "详细",
}


def is_content_token(tok: str) -> bool:
    """是否实义词：至少含一个非虚词字符，且不是纯标点/通用提问词。"""
    if not tok:
        return False
    if tok in _GENERIC_WORDS:
        return False
    return any(ch not in _FUNC_CHARS for ch in tok)


def content_tokens(text: str, min_len: int = 2) -> list[str]:
    """抽取参与门控的实义词。

    min_len=2 是刻意的：单字（如「打」「印」「油」）几乎在任何语料里都能撞上，
    用它参与覆盖率会把"3D打印""润滑油"这类超纲问题的覆盖率抬到门限以上。
    ASCII 词元（h7、ra、c2、m10）本身就是一个完整语义单位，长度 2 也保留。
    """
    seen: dict[str, None] = {}
    for t in unique_tokens(text):
        if not is_content_token(t):
            continue
        if len(t) < min_len:
            continue
        seen.setdefault(t, None)
    return list(seen)
