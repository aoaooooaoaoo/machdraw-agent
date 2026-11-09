#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
kb/graph/_check.py —— 知识条目与知识图谱一致性校验脚本

用法:
    D:\\python\\python.exe kb\\graph\\_check.py            # 校验（缺文件仅告警）
    D:\\python\\python.exe kb\\graph\\_check.py --strict   # 缺文件视为错误

校验内容:
  1. JSONL 逐行 JSON 合法、无空行、可解析
  2. 字段齐全、类型正确、取值域合法（chapter 逐字匹配 SPEC、tier/rel/layer 等）
  3. ID 唯一（kp_id / node id / qid），且符合 ID 规约（KP-<CODE>-<3位> 等）
  4. kp.jsonl 的 chapter 属于 SPEC 的 10 个完整章名；_terms.tsv 与 kp.jsonl 一一对应
  5. nodes.kp_id 必须回指存在的知识点；nodes 无孤立节点（每条边两端都必须是节点）
  6. edges 端点必须存在、rel 合法、note 非空、无自环、无重复边
  7. questions.kp_ids 必须全部存在、layer/bloom 合法
  8. 输出规模统计与错误清单；有错误时退出码 1
"""
from __future__ import print_function

import io
import json
import os
import re
import sys
from collections import Counter, defaultdict

# 在 Windows 控制台（GBK 代码页）下也尽量输出 UTF-8，避免中文乱码
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
KB = os.path.dirname(HERE)                       # kb/
KP_FILE = os.path.join(KB, "knowledge", "kp.jsonl")
TERMS_FILE = os.path.join(KB, "knowledge", "_terms.tsv")
NODES = os.path.join(HERE, "nodes.jsonl")
EDGES = os.path.join(HERE, "edges.jsonl")
QUESTIONS = os.path.join(HERE, "questions.jsonl")

STRICT = "--strict" in sys.argv

# ---- SPEC 第 1 节：章节完整章名（逐字，不得改动） ----
CHAPTERS = [
    "第一章 绪论",
    "第二章 核物理基础",
    "第三章 反应堆中子学过程",
    "第四章 中子扩散理论与计算",
    "第五章 中子能谱与群常数计算",
    "第六章 燃耗与中毒",
    "第七章 反应性系数与反应性控制",
    "第八章 核反应堆中子动力学",
    "第九章 堆芯核燃料管理",
    "第十章 堆芯核设计",
]
CHAPTER_SET = set(CHAPTERS)

TIERS = {"core", "trackA", "trackB", "branch", "concept"}
RELS = {"prereq", "contrast", "cause", "compose"}
BLOOMS = {"记忆", "理解", "应用", "分析", "综合"}
LAYERS = {1, 2, 3}

KP_FIELDS = ["kp_id", "chapter", "section", "term", "aliases", "definition",
             "points", "common_mistakes", "refs", "bloom", "level"]
NODE_FIELDS = ["id", "kp_id", "label", "tier", "chapter", "state"]
EDGE_FIELDS = ["source", "target", "rel", "note"]
Q_FIELDS = ["qid", "layer", "question", "bloom", "kp_ids", "hint"]

RE_KP = re.compile(r"^KP-[A-Z]+-\d{3}$")
RE_NODE = re.compile(r"^KN-\d{3}$")
RE_Q = re.compile(r"^Q-\d{3}$")

errors = []          # (级别, 文件, 位置, 信息)
warnings = []
stats = {}


def err(f, where, msg):
    errors.append(("ERROR", f, where, msg))


def warn(f, where, msg):
    warnings.append(("WARN", f, where, msg))


def load_jsonl(path, strict_missing=False):
    """返回 list[(行号, dict)]；逐行 JSON 合法性检查。"""
    name = os.path.basename(path)
    rows = []
    if not os.path.exists(path):
        if strict_missing or STRICT:
            err(name, "-", "文件不存在: %s" % path)
        else:
            warn(name, "-", "文件不存在（跳过校验）: %s" % path)
        return rows
    with io.open(path, "r", encoding="utf-8-sig") as f:
        for i, line in enumerate(f, 1):
            s = line.strip()
            if not s:
                err(name, "第%d行" % i, "空行（JSONL 不应有空行）")
                continue
            try:
                o = json.loads(s)
            except ValueError as e:
                err(name, "第%d行" % i, "JSON 解析失败: %s" % e)
                continue
            if not isinstance(o, dict):
                err(name, "第%d行" % i, "不是 JSON 对象")
                continue
            rows.append((i, o))
    return rows


def check_fields(name, i, o, fields):
    miss = [f for f in fields if f not in o]
    if miss:
        err(name, "第%d行" % i, "缺字段: %s" % ",".join(miss))
        return False
    extra = [f for f in o if f not in fields]
    if extra:
        warn(name, "第%d行" % i, "多余字段: %s" % ",".join(extra))
    return True


def check_str_list(name, i, o, key, min_n, max_n):
    v = o.get(key)
    if not isinstance(v, list):
        err(name, "第%d行" % i, "%s 应为数组" % key)
        return
    if not all(isinstance(x, str) and x.strip() for x in v):
        err(name, "第%d行" % i, "%s 含空串或非字符串" % key)
    if min_n is not None and len(v) < min_n:
        err(name, "第%d行" % i, "%s 条数 %d < %d" % (key, len(v), min_n))
    if max_n is not None and len(v) > max_n:
        err(name, "第%d行" % i, "%s 条数 %d > %d" % (key, len(v), max_n))


# ============================ 1. kp.jsonl ============================
kp_rows = load_jsonl(KP_FILE, True)
kp_ids = []
kp_chapter = {}
for i, o in kp_rows:
    if not check_fields("kp.jsonl", i, o, KP_FIELDS):
        continue
    kid = o["kp_id"]
    if not isinstance(kid, str) or not RE_KP.match(kid):
        err("kp.jsonl", "第%d行" % i, "kp_id 不符合规约: %r" % (kid,))
    kp_ids.append(kid)
    if o["chapter"] not in CHAPTER_SET:
        err("kp.jsonl", kid, "chapter 不是 SPEC 逐字章名: %r" % (o["chapter"],))
    kp_chapter[kid] = o["chapter"]
    if not isinstance(o["section"], str) or not o["section"].strip():
        err("kp.jsonl", kid, "section 为空")
    elif not re.match(r"^\d+\.\d+", o["section"]):
        warn("kp.jsonl", kid, "section 未以“章.节”开头: %r" % (o["section"],))
    if not isinstance(o["term"], str) or not o["term"].strip():
        err("kp.jsonl", kid, "term 为空")
    if not isinstance(o["definition"], str) or len(o["definition"]) < 60:
        err("kp.jsonl", kid, "definition 过短(%d 字)" % len(o.get("definition") or ""))
    if len(o["definition"]) > 260:
        warn("kp.jsonl", kid, "definition 偏长(%d 字)" % len(o["definition"]))
    check_str_list("kp.jsonl", i, o, "aliases", 0, None)
    check_str_list("kp.jsonl", i, o, "points", 3, 5)
    check_str_list("kp.jsonl", i, o, "common_mistakes", 2, 4)
    check_str_list("kp.jsonl", i, o, "refs", 1, None)
    if o["bloom"] not in BLOOMS:
        err("kp.jsonl", kid, "bloom 非法: %r" % (o["bloom"],))
    if o["level"] not in (1, 2, 3, 4):
        err("kp.jsonl", kid, "level 非法: %r" % (o["level"],))

dup = [k for k, n in Counter(kp_ids).items() if n > 1]
for k in dup:
    err("kp.jsonl", k, "kp_id 重复 %d 次" % kp_ids.count(k))

# ============================ 2. _terms.tsv ============================
term_pairs = []
if os.path.exists(TERMS_FILE):
    with io.open(TERMS_FILE, "r", encoding="utf-8-sig") as f:
        for i, line in enumerate(f, 1):
            s = line.rstrip("\n")
            if not s.strip():
                err("_terms.tsv", "第%d行" % i, "空行")
                continue
            parts = s.split("\t")
            if len(parts) != 2 or not parts[1].strip():
                err("_terms.tsv", "第%d行" % i, "格式应为 kp_id<TAB>term: %r" % (s,))
                continue
            term_pairs.append((parts[0], parts[1]))
    for kid, _t in term_pairs:
        if kid not in kp_chapter:
            err("_terms.tsv", kid, "kp_id 在 kp.jsonl 中不存在")
    tdup = [k for k, n in Counter(k for k, _ in term_pairs).items() if n > 1]
    for k in tdup:
        err("_terms.tsv", k, "kp_id 重复")
    missing = [k for k in kp_ids if k not in {x for x, _ in term_pairs}]
    if missing:
        warn("_terms.tsv", "-", "%d 个 kp 无对应 term 行" % len(missing))
else:
    warn("_terms.tsv", "-", "文件不存在（跳过）")

# ============================ 3. nodes.jsonl ============================
node_rows = load_jsonl(NODES)
node_ids = []
node_kp = {}
for i, o in node_rows:
    if not check_fields("nodes.jsonl", i, o, NODE_FIELDS):
        continue
    nid = o["id"]
    if not isinstance(nid, str) or not RE_NODE.match(nid):
        err("nodes.jsonl", "第%d行" % i, "id 不符合 KN-<三位>: %r" % (nid,))
    node_ids.append(nid)
    node_kp[nid] = o.get("kp_id")
    if o.get("kp_id") not in kp_chapter:
        err("nodes.jsonl", nid, "kp_id 回指不存在: %r" % (o.get("kp_id"),))
    if o.get("tier") not in TIERS:
        err("nodes.jsonl", nid, "tier 非法: %r" % (o.get("tier"),))
    if o.get("state") != "未学":
        err("nodes.jsonl", nid, "state 必须固定为 '未学': %r" % (o.get("state"),))
    if o.get("chapter") not in CHAPTER_SET:
        err("nodes.jsonl", nid, "chapter 不是 SPEC 逐字章名: %r" % (o.get("chapter"),))
    if not isinstance(o.get("label"), str) or not o.get("label").strip():
        err("nodes.jsonl", nid, "label 为空")

ndup = [k for k, n in Counter(node_ids).items() if n > 1]
for k in ndup:
    err("nodes.jsonl", k, "节点 id 重复")
node_set = set(node_ids)

# 同一 kp_id 只能对应一个节点
kp_nodes = defaultdict(list)
for nid, kid in node_kp.items():
    kp_nodes[kid].append(nid)
for kid, ns in kp_nodes.items():
    if len(ns) > 1:
        err("nodes.jsonl", kid, "同一 kp_id 对应多个节点: %s" % ",".join(ns))

# ============================ 4. edges.jsonl ============================
edge_rows = load_jsonl(EDGES)
edge_keys = []
adj = defaultdict(set)
rel_counter = Counter()
for i, o in edge_rows:
    if not check_fields("edges.jsonl", i, o, EDGE_FIELDS):
        continue
    s, t, rel = o["source"], o["target"], o["rel"]
    if s not in node_set:
        err("edges.jsonl", "第%d行" % i, "source 端点不存在: %r" % (s,))
    if t not in node_set:
        err("edges.jsonl", "第%d行" % i, "target 端点不存在: %r" % (t,))
    if s == t:
        err("edges.jsonl", "第%d行" % i, "自环边: %r" % (s,))
    if rel not in RELS:
        err("edges.jsonl", "第%d行" % i, "rel 非法: %r" % (rel,))
    if not isinstance(o.get("note"), str) or not o["note"].strip():
        err("edges.jsonl", "第%d行" % i, "note 为空")
    edge_keys.append((s, t, rel))
    adj[s].add(t)
    adj[t].add(s)
    rel_counter[rel] += 1
for key in [k for k, n in Counter(edge_keys).items() if n > 1]:
    err("edges.jsonl", "-", "重复边: %s -[%s]-> %s" % key)

# 无孤立节点
for nid in node_ids:
    if not adj.get(nid):
        err("nodes.jsonl", nid, "孤立节点（没有任何边）")

# ============================ 5. questions.jsonl ============================
q_rows = load_jsonl(QUESTIONS)
qids = []
layer_counter = Counter()
for i, o in q_rows:
    if not check_fields("questions.jsonl", i, o, Q_FIELDS):
        continue
    qid = o["qid"]
    if not isinstance(qid, str) or not RE_Q.match(qid):
        err("questions.jsonl", "第%d行" % i, "qid 不符合 Q-<三位>: %r" % (qid,))
    qids.append(qid)
    if o.get("layer") not in LAYERS:
        err("questions.jsonl", qid, "layer 必须为 1/2/3: %r" % (o.get("layer"),))
    else:
        layer_counter[o["layer"]] += 1
    if o.get("bloom") not in BLOOMS:
        err("questions.jsonl", qid, "bloom 非法: %r" % (o.get("bloom"),))
    if not isinstance(o.get("question"), str) or not o["question"].strip():
        err("questions.jsonl", qid, "question 为空")
    if not isinstance(o.get("hint"), str) or not o["hint"].strip():
        err("questions.jsonl", qid, "hint 为空")
    kids = o.get("kp_ids")
    if not isinstance(kids, list) or not kids:
        err("questions.jsonl", qid, "kp_ids 必须为非空数组")
    else:
        for k in kids:
            if k not in kp_chapter:
                err("questions.jsonl", qid, "kp_ids 引用不存在: %r" % (k,))
qdup = [k for k, n in Counter(qids).items() if n > 1]
for k in qdup:
    err("questions.jsonl", k, "qid 重复")

# ============================ 6. 统计 ============================
ch_counter = Counter(kp_chapter.values())
tier_counter = Counter(o.get("tier") for _i, o in node_rows)
print("=" * 78)
print("《核反应堆物理》知识条目与知识图谱校验")
print("=" * 78)
print("知识点 kp.jsonl      : %d 条" % len(kp_rows))
for ch in CHAPTERS:
    if ch_counter.get(ch):
        print("    %-24s %3d" % (ch, ch_counter[ch]))
print("术语表 _terms.tsv    : %d 行" % len(term_pairs))
print("图谱节点 nodes.jsonl : %d 个   tier: %s" % (
    len(node_rows), ", ".join("%s=%d" % (k, tier_counter[k]) for k in sorted(tier_counter))))
print("图谱边 edges.jsonl   : %d 条   rel: %s" % (
    len(edge_rows), ", ".join("%s=%d" % (k, rel_counter[k]) for k in sorted(rel_counter))))
print("问题链 questions     : %d 条   layer: %s" % (
    len(q_rows), ", ".join("L%d=%d" % (k, layer_counter[k]) for k in sorted(layer_counter))))
print("kp 覆盖率            : %d/%d kp 有对应节点" % (len(kp_nodes), len(kp_chapter)))
if errors:
    print("-" * 78)
    print("错误 %d 条:" % len(errors))
    for lvl, f, where, msg in errors:
        print("  [%s] %s %s : %s" % (lvl, f, where, msg))
else:
    print("校验结果             : 通过（0 错误）")
if warnings:
    print("-" * 78)
    print("告警 %d 条:" % len(warnings))
    for lvl, f, where, msg in warnings[:30]:
        print("  [%s] %s %s : %s" % (lvl, f, where, msg))
    if len(warnings) > 30:
        print("  ... 其余 %d 条告警省略" % (len(warnings) - 30))
print("=" * 78)
sys.exit(1 if errors else 0)
