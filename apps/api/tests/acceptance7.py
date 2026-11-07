"""验收：辨析对比图 + 出题（对话链路 + 接口）。"""
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


def ask(q: str, feature: str | None = None):
    body = json.dumps({"session_id": "local", "messages": [{"role": "user", "content": q}],
                       "feature": feature}).encode()
    req = urllib.request.Request(BASE + "/api/chat", data=body,
                                 headers={"Content-Type": "application/json",
                                          "X-Account": "pq"}, method="POST")
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
    print("=== 1. /api/pairs ===")
    d = get("/api/pairs")
    print(f"  成对图 {d['total']} 组")
    for p in d["pairs"][:4]:
        print(f"   - {p['pair_id']:26} {p['title']}  差异 {len(p.get('differences') or [])} 个")

    print("\n=== 2. 对话：辨析模块 ===")
    arts, ans = ask("半剖视图和局部剖视图有什么区别？", "projection")
    print("  画布：", [t for t, _ in arts])
    for t, data in arts:
        if t == "comparison":
            print(f"  comparison: {data.get('title')}  差异 {len(data.get('differences') or [])} 个  "
                  f"题 {len((data.get('question') or {}).get('options') or [])} 选项")
    print("  回答：")
    for line in ans.splitlines()[:14]:
        print("   ", line)

    print("\n=== 3. 对话：出题 ===")
    arts, ans = ask("考考我，给我出两道题", "wrongbook")
    print("  画布：", [t for t, _ in arts])
    print("  回答：")
    for line in ans.splitlines()[:10]:
        print("   ", line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
