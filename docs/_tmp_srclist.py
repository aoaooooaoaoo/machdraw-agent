import json, os
p=r"D:\桌面\机械制图agent\docs\_tmp_src_tree.json"
d=json.load(open(p,encoding="utf-8-sig"))
root=r"D:\桌面\机械制图agent\_recon\材料智能体_src\材料智能体\teaching-agent"
lines=[]
for f in d:
    rel=os.path.relpath(f["FullName"],root)
    if any(part in (".venv","venv","node_modules","__pycache__",".git","dist","build") for part in rel.split(os.sep)):
        continue
    lines.append("%8d  %s"%(f["Length"],rel))
lines.sort()
open(r"D:\桌面\机械制图agent\docs\_tmp_src_list.txt","w",encoding="utf-8").write("\n".join(lines))
print(len(lines))
