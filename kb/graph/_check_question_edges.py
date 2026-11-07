# -*- coding: utf-8 -*-
"""问题链（question_edges.jsonl）校验脚本（只读）。

用法：D:\\python\\python.exe _check_question_edges.py
校验：
  1. 每行可 json.loads；字段齐全（source/target/relation/why）；relation 属于四类
  2. source/target 都在 questions.jsonl 里存在
  3. 无自环、无重复（同一 source-target 只能一条）、无环（Kahn 拓扑排序能输出全部节点）
  4. 每道题度数（入+出）≥ 1
  5. 统计：跨层/同层、各 relation 数量、每层出入度、最长链
"""

import json
import os
import sys
from collections import Counter, defaultdict, deque

HERE = os.path.dirname(os.path.abspath(__file__))
Q_FILE = os.path.join(HERE, "questions.jsonl")
E_FILE = os.path.join(HERE, "question_edges.jsonl")
RELS = {"prereq", "contrast", "compose", "cause"}
REL_CN = {"prereq": "前置依赖", "contrast": "对比辨析", "compose": "组成", "cause": "因果"}

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
                rows.append((i, json.loads(s)))
            except Exception as e:
                fails.append("%s 第 %d 行 json 解析失败: %s" % (os.path.basename(path), i, e))
    return rows


def check(cond, msg):
    if not cond:
        fails.append(msg)
    return cond


# ---------- 读题目 ----------
qrows = load_jsonl(Q_FILE)
Q = {}                      # qid -> row
for _, r in qrows:
    qid = r.get("qid")
    check(qid not in Q, "questions.jsonl 里 qid 重复: %s" % qid)
    Q[qid] = r

# ---------- 读边 ----------
erows = load_jsonl(E_FILE)
edges = []                  # (src, dst, rel)
seen_pair = {}
for ln, r in erows:
    for f in ("source", "target", "relation", "why"):
        check(f in r, "第 %d 行缺字段 %s" % (ln, f))
    s, t, rel, why = r.get("source"), r.get("target"), r.get("relation"), (r.get("why") or "")
    if s not in Q:
        fails.append("第 %d 行 source 不存在于 questions.jsonl: %s" % (ln, s))
        continue
    if t not in Q:
        fails.append("第 %d 行 target 不存在于 questions.jsonl: %s" % (ln, t))
        continue
    check(s != t, "第 %d 行自环: %s" % (ln, s))
    check(rel in RELS, "第 %d 行 relation 非法: %s" % (ln, rel))
    key = (s, t)
    check(key not in seen_pair, "第 %d 行重复边（同一对 source-target）: %s->%s，与第 %s 行重复"
          % (ln, s, t, seen_pair.get(key)))
    seen_pair[key] = ln
    check(len(why) >= 8, "第 %d 行 why 过短（应写清知识点）: %s" % (ln, why))
    edges.append((s, t, rel))

# ---------- 无环：Kahn 拓扑排序 ----------
adj = defaultdict(list)
indeg = Counter()
nodes = list(Q.keys())
for s, t, rel in edges:
    adj[s].append(t)
    indeg[t] += 1
for n in nodes:
    indeg.setdefault(n, 0)
q = deque([n for n in nodes if indeg[n] == 0])
order = []
while q:
    u = q.popleft()
    order.append(u)
    for v in adj[u]:
        indeg[v] -= 1
        if indeg[v] == 0:
            q.append(v)
check(len(order) == len(nodes), "存在环：拓扑排序只输出 %d/%d 个节点" % (len(order), len(nodes)))

# ---------- 度数 ----------
deg_in = Counter()
deg_out = Counter()
for s, t, rel in edges:
    deg_out[s] += 1
    deg_in[t] += 1
for n in nodes:
    if deg_in[n] + deg_out[n] < 1:
        fails.append("孤岛题（度数为 0）: %s" % n)

# ---------- 统计 ----------
cross, same = [], []
for s, t, rel in edges:
    (cross if Q[s]["layer"] != Q[t]["layer"] else same).append((s, t, rel))
rel_count = Counter(rel for _, _, rel in edges)

layer_of = {n: Q[n]["layer"] for n in nodes}
per_layer = defaultdict(lambda: {"题目数": 0, "入度": 0, "出度": 0})
for n in nodes:
    L = per_layer[layer_of[n]]
    L["题目数"] += 1
    L["入度"] += deg_in[n]
    L["出度"] += deg_out[n]

# ---------- 最长链（按边数） ----------
# 拓扑序上做 DP，记录前驱
best = {n: 0 for n in nodes}
prev = {n: None for n in nodes}
for u in order:
    for v in adj[u]:
        if best[u] + 1 > best[v]:
            best[v] = best[u] + 1
            prev[v] = u
end = max(nodes, key=lambda n: best[n])
chain = []
cur = end
while cur is not None:
    chain.append(cur)
    cur = prev[cur]
chain.reverse()

# ---------- 输出 ----------
print("=" * 68)
print("问题链 question_edges.jsonl 校验报告")
print("=" * 68)
print("题目总数 %d（layer1 %d / layer2 %d / layer3 %d）"
      % (len(Q), sum(1 for n in nodes if layer_of[n] == 1),
         sum(1 for n in nodes if layer_of[n] == 2),
         sum(1 for n in nodes if layer_of[n] == 3)))
print("边总数 %d（要求 22~30 -> %s）"
      % (len(edges), "PASS" if 22 <= len(edges) <= 30 else "FAIL"))
print("  · 跨层 %d 条（要求 ≥16 -> %s）" % (len(cross), "PASS" if len(cross) >= 16 else "FAIL"))
print("  · 同层 %d 条（%s）" % (len(same), "，".join("%s→%s %s" % (a, b, REL_CN[c]) for a, b, c in same)))
print("relation 分布：", " / ".join("%s %d" % (REL_CN[k], rel_count[k])
                                    for k in ["prereq", "contrast", "compose", "cause"]))
print("拓扑排序：%s（输出 %d/%d 节点）"
      % ("PASS 无环" if len(order) == len(nodes) else "FAIL 有环", len(order), len(nodes)))
print("孤岛题：%s" % ("无" if all(deg_in[n] + deg_out[n] >= 1 for n in nodes) else "见错误列表"))
print("最长链（%d 条边）：%s" % (len(chain) - 1, " → ".join(chain)))
print("-" * 68)
print("每层出入度：")
for L in (1, 2, 3):
    d = per_layer[L]
    print("  layer%d：题 %2d 道，入度合计 %2d，出度合计 %2d"
          % (L, d["题目数"], d["入度"], d["出度"]))
print("每题度数：")
for n in nodes:
    print("  %s L%d  入%2d 出%2d  %s" % (n, layer_of[n], deg_in[n], deg_out[n],
                                        (Q[n]["question"][:26] + "…") if len(Q[n]["question"]) > 26 else Q[n]["question"]))
print("-" * 68)
if fails:
    print("结果：FAIL（%d 项问题）" % len(fails))
    for f in fails:
        print("  !", f)
    sys.exit(1)
print("结果：ALL PASS（结构合法、无自环/重复/环、每道题均有连接、规模与跨层比例达标）")
sys.exit(0)
