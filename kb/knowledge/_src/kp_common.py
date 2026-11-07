# -*- coding: utf-8 -*-
"""机械制图知识条目（kp.jsonl）公共定义。

设计要点：
1. 各 kp_partN.py 只负责用 kp(...) 追加条目，不关心编号。
2. build_kp.py 按“章内出现顺序”自动编号，并生成 kp_index.json（key -> kp_id），
   供知识图谱/问题图谱按 key 引用，避免手写编号错位。
3. 新增条目请追加到对应章末尾，否则会改动既有编号（图谱引用会失效）。
"""

CHAPTERS = {
    "BASIC": "第一章 制图的基本知识和基本技能",
    "CAD": "第二章 AutoCAD 基础",
    "PROJ": "第三章 点、直线和平面的投影",
    "SOLID": "第四章 立体的投影",
    "COMP": "第五章 组合体的视图与形体构型",
    "AXO": "第六章 轴测图",
    "EXPR": "第七章 机件的常用表达方法",
    "STD": "第八章 螺纹、齿轮、常用标准件及其连接",
    "PART": "第九章 零件图",
    "ASSY": "第十章 装配图",
}

PREFIX = {
    "BASIC": "KP-BASIC",
    "CAD": "KP-CAD",
    "PROJ": "KP-PROJ",
    "SOLID": "KP-SOLID",
    "COMP": "KP-COMP",
    "AXO": "KP-AXO",
    "EXPR": "KP-EXPR",
    "STD": "KP-STD",
    "PART": "KP-PART",
    "ASSY": "KP-ASSY",
}

BLOOM = ["记忆", "理解", "应用", "分析", "综合"]

ALL = []
_KEYS = {}


def kp(ch, key, section, term, aliases, definition, points, mistakes, refs, bloom, level):
    """登记一条知识点。key 为全局唯一的英文短键，供图谱引用。"""
    assert ch in CHAPTERS, "unknown chapter key: %s" % ch
    assert key not in _KEYS, "duplicate key: %s" % key
    assert bloom in BLOOM, "bad bloom: %s (%s)" % (bloom, key)
    assert level in (1, 2, 3), "bad level: %s (%s)" % (level, key)
    _KEYS[key] = True
    ALL.append(
        dict(
            ch=ch,
            key=key,
            section=section,
            term=term,
            aliases=aliases,
            definition=definition,
            points=points,
            common_mistakes=mistakes,
            refs=refs,
            bloom=bloom,
            level=level,
        )
    )
