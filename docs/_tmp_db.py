import sqlite3, json, os
root=r"D:\桌面\机械制图agent\_recon\材料智能体_src\材料智能体\teaching-agent"
db=os.path.join(root,"rag-system","data","msrag.db")
con=sqlite3.connect(f"file:{db}?mode=ro",uri=True)
cur=con.cursor()
out={}
for q,label in [("select count(*) from documents","documents"),("select count(*) from sections","sections"),("select count(*) from chunks","chunks"),("select count(*) from citations","citations")]:
    try: out[label]=cur.execute(q).fetchone()[0]
    except Exception as e: out[label]=str(e)
try:
    out["docs"]=cur.execute("select id,title from documents").fetchall()[:20]
except Exception as e: out["docs"]=str(e)
try:
    out["chunk_len"]=cur.execute("select min(length(content)),max(length(content)),avg(length(content)) from chunks").fetchone()
except Exception as e: out["chunk_len"]=str(e)
try:
    out["per_doc_chunks"]=cur.execute("select d.title,count(c.id) from chunks c join documents d on d.id=c.document_id group by d.title").fetchall()
except Exception as e: out["per_doc_chunks"]=str(e)
con.close()
v=json.load(open(os.path.join(root,"rag-system","data","vectors.json"),encoding="utf-8"))
out["vectors_json"]={"count":v.get("count"),"version":v.get("version"),"items":len(v.get("items",{}))}
open(r"D:\桌面\机械制图agent\docs\_tmp_db_stats.json","w",encoding="utf-8").write(json.dumps(out,ensure_ascii=False,indent=2,default=str))
print("ok")
