# -*- coding: utf-8 -*-
"""知识库自检脚本（只读，不改数据）。

用法：D:\\python\\python.exe selfcheck.py
校验对象：kb/knowledge/kp.jsonl、kb/graph/nodes.jsonl、kb/graph/edges.jsonl、kb/graph/questions.jsonl
输出：逐项 PASS/FAIL + 统计数据，可直接粘进 docs/07 报告。
"""

import json
import os
import sys
from collections import defaultdict, deque

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
KP_FILE = os.path.join(ROOT, "kb", "knowledge", "kp.jsonl")
NODE_FILE = os.path.join(ROOT, "kb", "graph", "nodes.jsonl")
EDGE_FILE = os.path.join(ROOT, "kb", "graph", "edges.jsonl")
Q_FILE = os.path.join(ROOT, "kb", "graph", "questions.jsonl")

CH_PREFIX = {
    "第一章": "KP-BASIC", "第二章": "KP-CAD", "第三章": "KP-PROJ", "第四章": "KP-SOLID",
    "第五章": "KP-COMP", "第六章": "KP-AXO", "第七章": "KP-EXPR", "第八章": "KP-STD",
    "第九章": "KP-PART", "第十章": "KP-ASSY",
}
BLOOM = {"记忆", "理解", "应用", "分析", "综合"}
TIERS = {"core", "trackA", "trackB", "branch", "concept"}
RELS = {"prereq", "contrast", "compose", "cause"}
STATES = {"未学", "正在学", "已掌握", "需复习"}

fails = []
warns = []


def load_jsonl(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            s = line.strip()
            if not s:
                fails.append("%s 第 %d 行为空行" % (os.path.basename(path), i))
                continue
            try:
                rows.append(json.loads(s))
            except Exception as e:
                fails.append("%s 第 %d 行 json 解析失败: %s" % (os.path.basename(path), i, e))
    return rows


def check(cond, msg):
    if not cond:
        fails.append(msg)
    return cond


# ===================== 1. kp.jsonl =====================
KPS = load_jsonl(KP_FILE)
kp_ids = set()
ch_count = defaultdict(int)
for r in KPS:
    for f in ("kp_id", "chapter", "section", "term", "aliases", "definition",
              "points", "common_mistakes", "refs", "bloom", "level"):
        check(f in r, "KP 缺字段 %s: %s" % (f, r.get("kp_id", "?")))
    kid = r.get("kp_id", "")
    check(kid not in kp_ids, "kp_id 重复: %s" % kid)
    kp_ids.add(kid)
    ch = r.get("chapter", "")
    pref = CH_PREFIX.get(ch[:3])
    check(pref is not None and kid.startswith(pref), "kp_id 前缀与章不符: %s / %s" % (kid, ch))
    check(r.get("bloom") in BLOOM, "bloom 非法: %s (%s)" % (r.get("bloom"), kid))
    check(r.get("level") in (1, 2, 3), "level 非法: %s (%s)" % (r.get("level"), kid))
    d = r.get("definition", "")
    if not (60 <= len(d) <= 160):
        fails.append("definition 长度越界(%d): %s" % (len(d), kid))
    for f in ("aliases", "points", "common_mistakes", "refs"):
        check(bool(r.get(f)), "%s 的 %s 为空" % (kid, f))
    check(bool(r.get("section")), "%s 的 section 为空" % kid)
    # 引用国标时应写“GB/T xxxx-yyyy”
    for ref in r.get("refs", []):
        if "GB/T" in ref and not any(ch.isdigit() for ch in ref):
            fails.append("%s 的国标引用缺编号: %s" % (kid, ref))
    ch_count[ch] += 1

check(len(KPS) >= 160, "知识点总数不足 160：%d" % len(KPS))

# ===================== 2. nodes.jsonl =====================
NODES = load_jsonl(NODE_FILE)
node_ids = set()
tier_count = defaultdict(int)
node_kp = {}
for r in NODES:
    for f in ("id", "kp_id", "label", "tier", "chapter", "state"):
        check(f in r, "节点缺字段 %s: %s" % (f, r.get("id", "?")))
    nid = r.get("id", "")
    check(nid not in node_ids, "节点 id 重复: %s" % nid)
    node_ids.add(nid)
    check(r.get("kp_id") in kp_ids, "节点 %s 的 kp_id 不存在: %s" % (nid, r.get("kp_id")))
    check(r.get("tier") in TIERS, "节点 %s tier 非法: %s" % (nid, r.get("tier")))
    check(r.get("state") in STATES, "节点 %s state 非法: %s" % (nid, r.get("state")))
    check(bool(r.get("label")), "节点 %s label 为空" % nid)
    tier_count[r.get("tier")] += 1
    node_kp[nid] = r.get("kp_id")

check(len(NODES) >= 90, "节点数不足 90：%d" % len(NODES))
covered = set(node_kp.values())
check(covered == set(node_kp.values()), "节点 kp_id 无重复（本行仅占位）")

# ===================== 3. edges.jsonl =====================
EDGES = load_jsonl(EDGE_FILE)
rel_count = defaultdict(int)
seen = set()
adj = defaultdict(list)
undirected = defaultdict(set)
for r in EDGES:
    for f in ("source", "target", "rel", "note"):
        check(f in r, "边缺字段 %s: %s" % (f, r))
    s, t, rel = r.get("source"), r.get("target"), r.get("rel")
    if not (s in node_ids and t in node_ids):
        fails.append("边端点不存在: %s -> %s" % (s, t))
        continue
    check(s != t, "自环边: %s" % s)
    check(rel in RELS, "rel 非法: %s" % rel)
    key = (s, t, rel)
    check(key not in seen, "重复边: %s" % (key,))
    seen.add(key)
    check(bool(r.get("note")), "边缺 note: %s->%s" % (s, t))
    rel_count[rel] += 1
    if rel == "prereq":
        adj[s].append(t)
    undirected[s].add(t)
    undirected[t].add(s)

check(len(EDGES) >= 120, "边数不足 120：%d" % len(EDGES))
check(rel_count["prereq"] >= 25, "prereq 边不足 25：%d" % rel_count["prereq"])
check(rel_count["contrast"] >= 25, "contrast 边不足 25：%d" % rel_count["contrast"])

# 必备对比边（按节点 label 定位）
label_index = defaultdict(list)
label_of = {}
for r in NODES:
    label_index[r["label"]].append(r["id"])
    label_of[r["id"]] = r["label"]

REQUIRED_PAIRS = [
    ("截交线", "相贯线"),
    ("半剖视图", "局部剖视图"),
    ("六个基本视图", "剖视图"),
    ("尺寸基准（零件图）", "工艺基准"),
    ("基孔制", "基轴制"),
    ("间隙配合", "过盈配合"),
]
required_result = []
for a, b in REQUIRED_PAIRS:
    na = label_index.get(a, [])
    nb = label_index.get(b, [])
    ok = False
    for x in na:
        for y in nb:
            if ((x, y, "contrast") in seen) or ((y, x, "contrast") in seen):
                ok = True
    required_result.append((a, b, ok))
    check(ok, "缺少必备对比边: %s ↔ %s" % (a, b))

# prereq 可达性：投影基础 -> 装配图（按节点 label 定位）
start = (label_index.get("投影基础") or [None])[0]
goal = (label_index.get("装配图") or [None])[0]
path = []
if start and goal:
    prev = {start: None}
    q = deque([start])
    while q:
        u = q.popleft()
        if u == goal:
            break
        for v in adj[u]:
            if v not in prev:
                prev[v] = u
                q.append(v)
    if goal in prev:
        cur = goal
        while cur is not None:
            path.append(cur)
            cur = prev[cur]
        path.reverse()
check(bool(path), "prereq 子图上“投影基础 → 装配图”不可达")
path_labels = [label_of.get(p, p) for p in path]

# 弱连通分量
visited = set()
comps = []
for n in NODES:
    nid = n["id"]
    if nid in visited:
        continue
    q = deque([nid])
    visited.add(nid)
    size = 0
    while q:
        u = q.popleft()
        size += 1
        for v in undirected[u]:
            if v not in visited:
                visited.add(v)
                q.append(v)
    comps.append(size)
comps.sort(reverse=True)
check(len(comps) == 1, "图不连通，弱连通分量 %d 个：%s" % (len(comps), comps))

# ===================== 4. questions.jsonl =====================
QS = load_jsonl(Q_FILE)
qids = set()
layer_count = defaultdict(int)
q_hit_kp = set()
for r in QS:
    for f in ("qid", "layer", "question", "bloom", "kp_ids", "hint"):
        check(f in r, "问题缺字段 %s: %s" % (f, r.get("qid", "?")))
    qid = r.get("qid", "")
    check(qid not in qids, "qid 重复: %s" % qid)
    qids.add(qid)
    check(r.get("layer") in (1, 2, 3), "layer 非法: %s" % qid)
    check(r.get("bloom") in BLOOM, "问题 bloom 非法: %s" % qid)
    layer_count[r.get("layer")] += 1
    check(bool(r.get("kp_ids")), "%s 未关联 kp" % qid)
    for k in r.get("kp_ids", []):
        check(k in kp_ids, "%s 引用了不存在的 kp_id: %s" % (qid, k))
        q_hit_kp.add(k)

check(layer_count[1] >= 8, "layer1 不足 8：%d" % layer_count[1])
check(layer_count[2] >= 6, "layer2 不足 6：%d" % layer_count[2])
check(layer_count[3] >= 4, "layer3 不足 4：%d" % layer_count[3])

# ===================== 5. 覆盖统计 =====================
kp_hit_node = set(node_kp.values())
cover_node = len(kp_hit_node) / len(kp_ids) * 100
cover_q = len(q_hit_kp) / len(kp_ids) * 100

# ===================== 输出 =====================
print("=" * 66)
print("知识库自检报告（kb/knowledge + kb/graph）")
print("=" * 66)
print("[1] kp.jsonl        行数 %d，kp_id 唯一 %s，最小 requirement 160 -> %s"
      % (len(KPS), len(kp_ids) == len(KPS), "PASS" if len(KPS) >= 160 else "FAIL"))
print("    分章分布：")
for ch in sorted(ch_count):
    print("      %-28s %3d" % (ch, ch_count[ch]))
print("[2] nodes.jsonl     节点 %d（要求 ≥90 -> %s），tier 分布 %s"
      % (len(NODES), "PASS" if len(NODES) >= 90 else "FAIL", dict(tier_count)))
print("[3] edges.jsonl     边 %d（要求 ≥120 -> %s）"
      % (len(EDGES), "PASS" if len(EDGES) >= 120 else "FAIL"))
print("    rel 分布：prereq %d（≥25 -> %s）/ contrast %d（≥25 -> %s）/ compose %d / cause %d"
      % (rel_count["prereq"], "PASS" if rel_count["prereq"] >= 25 else "FAIL",
         rel_count["contrast"], "PASS" if rel_count["contrast"] >= 25 else "FAIL",
         rel_count["compose"], rel_count["cause"]))
print("    必备对比边：")
for a, b, ok in required_result:
    print("      %-22s ↔ %-14s %s" % (a, b, "PASS" if ok else "FAIL"))
print("    prereq 路径：%s" % (" → ".join(path_labels) if path else "不可达 FAIL"))
print("    弱连通分量：%d 个（%s）" % (len(comps), "PASS" if len(comps) == 1 else "FAIL"))
print("[4] questions.jsonl 问题 %d，分层 %s（layer1≥8 / layer2≥6 / layer3≥4 -> %s）"
      % (len(QS), dict(sorted(layer_count.items())),
         "PASS" if layer_count[1] >= 8 and layer_count[2] >= 6 and layer_count[3] >= 4 else "FAIL"))
print("[5] 覆盖：节点覆盖知识点 %d/%d = %.1f%%；问题覆盖 %d/%d = %.1f%%"
      % (len(kp_hit_node), len(kp_ids), cover_node, len(q_hit_kp), len(kp_ids), cover_q))
print("-" * 66)
if fails:
    print("结果：FAIL，%d 项问题" % len(fails))
    for f in fails:
        print("  !", f)
    sys.exit(1)
else:
    print("结果：ALL PASS（JSONL 全部可解析、kp_id 唯一、边端点全部存在、统计与连通性达标）")
    sys.exit(0)
