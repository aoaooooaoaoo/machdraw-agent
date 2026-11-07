import os, json, re
root=r"D:\桌面\机械制图agent\_recon\材料智能体_src\材料智能体\teaching-agent"
out={}
for rel in [r"backend\.env", r"rag-system\.env"]:
    p=os.path.join(root,rel)
    out[rel]={"exists":os.path.exists(p)}
    if os.path.exists(p):
        lines=[]
        for raw in open(p,encoding="utf-8",errors="replace").read().splitlines():
            s=raw.strip()
            if not s or s.startswith("#"):
                continue
            k,_,v=s.partition("=")
            k=k.strip(); v=v.strip()
            if re.search(r"KEY|TOKEN|SECRET",k.upper()):
                lines.append(f"{k}=<SET len={len(v)} looks_placeholder={v in ('sk-xxxxxxxxxxxxxxxx','replace_me','')}>")
            else:
                lines.append(f"{k}={v}")
        out[rel]["lines"]=lines
# types.py RetrievedChunk.to_dict shape
t=open(os.path.join(root,"rag-system","rag","types.py"),encoding="utf-8").read()
m=re.search(r"class RetrievedChunk.*?def to_dict.*?(?=\nclass |\Z)", t, re.S)
out["RetrievedChunk.to_dict"]=m.group(0)[:2200] if m else "NOT FOUND"
open(r"D:\桌面\机械制图agent\docs\_tmp_env.json","w",encoding="utf-8").write(json.dumps(out,ensure_ascii=False,indent=2))
print("ok")
