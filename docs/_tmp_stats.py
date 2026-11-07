import json, os, collections
root=r"D:\桌面\机械制图agent\_recon\材料智能体_src\材料智能体\teaching-agent"
ch=os.path.join(root,"data","chunks.jsonl")
rows=[json.loads(l) for l in open(ch,encoding="utf-8") if l.strip()]
out={"chunk_total":len(rows)}
out["by_source"]=dict(collections.Counter(r["metadata"].get("source") for r in rows))
out["by_doc"]=dict(collections.Counter(r["metadata"].get("doc") for r in rows))
out["by_section"]=dict(collections.Counter(r["metadata"].get("section") for r in rows))
out["by_experiment"]=dict(collections.Counter(r["metadata"].get("experiment") for r in rows))
lens=[len(r["text"]) for r in rows]
out["len_stats"]={"min":min(lens),"max":max(lens),"avg":round(sum(lens)/len(lens),1)}
out["sample"]=[{"text":r["text"][:160],"metadata":r["metadata"]} for r in rows[:3]]
# graph
g=json.load(open(os.path.join(root,"data","graph.json"),encoding="utf-8"))
out["graph"]={"keys":list(g.keys()),"nodes":len(g.get("nodes",[])),"edges":len(g.get("edges",[])),
 "questionNodes":len(g.get("questionNodes",[])),"questionEdges":len(g.get("questionEdges",[])),
 "node_levels":dict(collections.Counter(n.get("level") for n in g.get("nodes",[]))),
 "node_sector":dict(collections.Counter(n.get("sector") for n in g.get("nodes",[]))),
 "node_type":dict(collections.Counter(n.get("type") for n in g.get("nodes",[]))),
 "relations":dict(collections.Counter(e.get("relation") for e in g.get("edges",[]))),
 "sample_node":g.get("nodes",[])[:2],"sample_q":g.get("questionNodes",[])[:2]}
open(r"D:\桌面\机械制图agent\docs\_tmp_chunk_stats.json","w",encoding="utf-8").write(json.dumps(out,ensure_ascii=False,indent=2))
print("chunks",len(rows),"avg",out["len_stats"]["avg"],"nodes",out["graph"]["nodes"],"edges",out["graph"]["edges"],"q",out["graph"]["questionNodes"])
