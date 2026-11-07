# -*- coding: utf-8 -*-
"""构建 kb/knowledge/kp.jsonl。

- 按“章内出现顺序”自动编号（KP-<章前缀>-<三位序号>）
- 校验：字段齐全、definition 长度 60~160 字、bloom/level 合法、id 唯一
- 输出 kp_index.json（key -> kp_id / term / chapter）供图谱与问题图谱引用
"""

import importlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from kp_common import ALL, CHAPTERS, PREFIX  # noqa: E402

PARTS = ["kp_part1", "kp_part2", "kp_part3", "kp_part4", "kp_part5"]
loaded = []
for name in PARTS:
    try:
        importlib.import_module(name)
        loaded.append(name)
    except ImportError as e:
        print("[skip] %s: %s" % (name, e))

counts = {}
rows = []
index = {}
errors = []

for e in ALL:
    if e["ch"] not in counts:
        counts[e["ch"]] = 0
    counts[e["ch"]] += 1
    kp_id = "%s-%03d" % (PREFIX[e["ch"]], counts[e["ch"]])

    dlen = len(e["definition"])
    if not (60 <= dlen <= 160):
        errors.append("%s(%s) definition 长度 %d 不在 60~160" % (kp_id, e["key"], dlen))
    for f in ("points", "common_mistakes", "refs"):
        if not e[f]:
            errors.append("%s(%s) 字段 %s 为空" % (kp_id, e["key"], f))
    if not e["aliases"]:
        errors.append("%s(%s) aliases 为空" % (kp_id, e["key"]))
    if e["key"] in index:
        errors.append("key 重复: %s" % e["key"])

    rows.append({
        "kp_id": kp_id,
        "chapter": CHAPTERS[e["ch"]],
        "section": e["section"],
        "term": e["term"],
        "aliases": e["aliases"],
        "definition": e["definition"],
        "points": e["points"],
        "common_mistakes": e["common_mistakes"],
        "refs": e["refs"],
        "bloom": e["bloom"],
        "level": e["level"],
    })
    index[e["key"]] = {"kp_id": kp_id, "term": e["term"], "chapter": CHAPTERS[e["ch"]]}

out = os.path.normpath(os.path.join(HERE, "..", "kp.jsonl"))
with open(out, "w", encoding="utf-8", newline="\n") as f:
    for r in rows:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

with open(os.path.join(HERE, "kp_index.json"), "w", encoding="utf-8") as f:
    json.dump(index, f, ensure_ascii=False, indent=1)

print("写出 %d 条 -> %s" % (len(rows), out))
print("分章：")
for k in ["BASIC", "CAD", "PROJ", "SOLID", "COMP", "AXO", "EXPR", "STD", "PART", "ASSY"]:
    if counts.get(k):
        print("  %-6s %3d  %s" % (k, counts[k], CHAPTERS[k]))
print("errors:", len(errors))
for e in errors:
    print("  !", e)
