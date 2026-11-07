import sys, os, json, collections, re
root=r"D:\桌面\机械制图agent\_recon\材料智能体_src\材料智能体\teaching-agent"
sys.path.insert(0, os.path.join(root,"backend"))
os.chdir(os.path.join(root,"backend"))
import importlib.util
spec=importlib.util.spec_from_file_location("bank", os.path.join(root,"backend","app","tools","mistake_book","bank.py"))
bank=importlib.util.module_from_spec(spec); spec.loader.exec_module(bank)
out={"entries":len(bank.ENTRIES),
     "categories":bank.categories() if callable(getattr(bank,"categories",None)) else None,
     "root_causes":getattr(bank,"ROOT_CAUSE_KINDS",None),
     "syllabus_topics":getattr(bank,"SYLLABUS_TOPICS",None),
     "sample":bank.ENTRIES[0] if bank.ENTRIES else None}
open(r"D:\桌面\机械制图agent\docs\_tmp_bank.json","w",encoding="utf-8").write(json.dumps(out,ensure_ascii=False,indent=2,default=str))
print("ok",len(bank.ENTRIES))
