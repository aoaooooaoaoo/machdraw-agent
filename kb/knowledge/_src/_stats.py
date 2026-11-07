import json, re, collections
kps=[json.loads(l) for l in open("../kp.jsonl",encoding="utf-8")]
print("bloom:", dict(collections.Counter(k["bloom"] for k in kps)))
print("level:", dict(sorted(collections.Counter(k["level"] for k in kps).items())))
stds=collections.Counter()
for k in kps:
    for r in k["refs"]:
        m=re.search(r"(GB/T\s?\d+[\.\d]*(?:-\d{4})?)", r)
        if m: stds[m.group(1).replace(" ","")]+=1
print("标准引用数:", len(stds))
for s,c in sorted(stds.items()):
    print("  %-22s %d" % (s,c))
# 可疑占位/未完成标记
bad=[k["kp_id"] for k in kps if re.search(r"xxx|TODO|待补|待定|……|\?\?\?", k["definition"]+json.dumps(k["points"],ensure_ascii=False))]
print("可疑占位:", bad)
# 长句/短定义
print("最短定义:", min((len(k["definition"]),k["kp_id"]) for k in kps))
print("最长定义:", max((len(k["definition"]),k["kp_id"]) for k in kps))
