"""验收：手绘找茬（接口 + 对话链路）。"""
from __future__ import annotations

import json
import sys
import urllib.request

BASE = "http://127.0.0.1:8077"
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def get(path: str):
    return json.loads(urllib.request.urlopen(BASE + path, timeout=30).read().decode("utf-8"))


def post(path: str, body: dict):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    return json.loads(urllib.request.urlopen(req, timeout=60).read().decode("utf-8"))


def ask(q: str, feature: str | None = None):
    body = json.dumps({"session_id": "local", "messages": [{"role": "user", "content": q}],
                       "feature": feature}).encode()
    req = urllib.request.Request(BASE + "/api/chat", data=body,
                                 headers={"Content-Type": "application/json",
                                          "X-Account": "sk"}, method="POST")
    arts, ans = [], []
    with urllib.request.urlopen(req, timeout=120) as r:
        for raw in r:
            line = raw.decode("utf-8").rstrip()
            if not line.startswith("data: "):
                continue
            p = line[6:]
            if p == "[DONE]":
                break
            e = json.loads(p)
            if e["type"] == "artifact":
                arts.append((e["artifactType"], e["data"]))
            elif e["type"] == "token":
                ans.append(e.get("text", ""))
    return arts, "".join(ans)


def main() -> int:
    print("=== 1. 标准答案接口 ===")
    t = get("/api/sketch/truth?model_id=M-L-BLOCK&view=front")
    print(f"  {t['name']} 主视图 标准答案 {len(t['segments'])} 条")

    print("\n=== 2. 生成找茬练习 ===")
    ex = get("/api/sketch/exercise?model_id=M-L-BLOCK&view=front&inject=missing,linetype,offset")
    print(f"  图上线条 {len(ex['drawing'])} 条，含错误 {ex['expect_count']} 处，答案下发={ex['answer_withheld']}")

    print("\n=== 3. 提交完全正确的图（应满分） ===")
    truth = t["segments"]
    r = post("/api/sketch/grade", {"model_id": "M-L-BLOCK", "view": "front", "segments": truth})
    print(f"  得分 {r['score']:.0%}  等级 {r['level']}  错误 {r['error_counts']}")

    print("\n=== 4. 提交练习图（应判出错误） ===")
    r2 = post("/api/sketch/grade", {"model_id": "M-L-BLOCK", "view": "front",
                                   "segments": ex["drawing"]})
    print(f"  得分 {r2['score']:.0%}  等级 {r2['level']}  错误 {r2['error_counts']}")
    for e in r2["errors"][:5]:
        print(f"    [{e['type_name']}] {e['desc']}")

    print("\n=== 5. 对话链路：我说想找茬 ===")
    arts, ans = ask("帮我找茬，看看我画的图有什么问题", "wrongbook")
    print("  画布：", [(t_, d_.get("mode") if t_ == "annotation" else "") for t_, d_ in arts])
    print("  回答：")
    for line in ans.splitlines()[:12]:
        print("   ", line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
