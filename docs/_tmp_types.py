import json,os
root=r"D:\桌面\机械制图agent\_recon\材料智能体_src\材料智能体\teaching-agent"
out={}
out["ids.py"]=open(os.path.join(root,"rag-system","core","ids.py"),encoding="utf-8").read()
terms=json.load(open(os.path.join(root,"backend","knowledge","terms.json"),encoding="utf-8"))
out["terms_count"]=len(terms)
out["terms_sample"]=terms[:3]
out["terms_keys"]=sorted({k for t in terms for k in t})
# ChildChunk / ParentChunk dataclass
t=open(os.path.join(root,"rag-system","rag","types.py"),encoding="utf-8").read()
import re
m=re.search(r"class ParentChunk.*?(?=\n@dataclass|\Z)",t,re.S); out["ParentChunk"]=m.group(0)[:1200] if m else ""
m=re.search(r"class ChildChunk.*?(?=\n@dataclass|\Z)",t,re.S); out["ChildChunk"]=m.group(0)[:1600] if m else ""
open(r"D:\桌面\机械制图agent\docs\_tmp_types.json","w",encoding="utf-8").write(json.dumps(out,ensure_ascii=False,indent=2))
print("terms",len(terms))
