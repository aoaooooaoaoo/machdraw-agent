import json,os
root=r"D:\桌面\机械制图agent\_recon\材料智能体_src\材料智能体\teaching-agent"
v=json.load(open(os.path.join(root,"rag-system","data","vectors.json"),encoding="utf-8"))
items=v["items"]; k=list(items)[0]
vec=items[k]["vec"]
out={"count":len(items),"dim":len(vec),"sample_key":k,"sample_keys":list(items)[:3],
     "has_tf":bool(items[k].get("tf")),"tf_size":len(items[k].get("tf") or {}),
     "vec_norm":round(sum(x*x for x in vec)**0.5,4),
     "doc_field":items[k].get("doc")}
# 检索演示：用哈希向量做一次混合检索（复刻 vectorstore 算法），确认可离线跑
open(r"D:\桌面\机械制图agent\docs\_tmp_vec.json","w",encoding="utf-8").write(json.dumps(out,ensure_ascii=False,indent=2))
print(out)
