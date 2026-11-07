"""验收：三视图真投影（/api/models + 投影工具 + three_view artifact）。"""
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
                                          "X-Account": "tv"}, method="POST")
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
    print("=== 1. /api/models ===")
    d = get("/api/models")
    print(f"  模型 {d['total']} 个：", "、".join(m["name"] for m in d["models"]))

    print("\n=== 2. /api/models/{id} 数据形状 ===")
    m = get("/api/models/M-L-BLOCK")
    print(f"  {m['name']}  {m['size']}  segments={len(m['segments'])}  "
          f"viewBox={m['viewBox']}  projection={m['projection']}")
    print(f"  aux 条数={len(m['aux'])}  stats={m['stats']}")
    seg = m["segments"][0]
    print(f"  样例线：{seg}")

    print("\n=== 3. 对话链路（3D 沙盒模块） ===")
    arts, ans = ask("这个零件的三视图怎么画？", "sandbox3d")
    for t, data in arts:
        if t == "three_view":
            print(f"  artifact=three_view  {data['name']}  {data['size']}  "
                  f"线 {len(data['segments'])} 条")
        else:
            print(f"  artifact={t}")
    print("  回答：")
    for line in ans.splitlines()[:12]:
        print("   ", line)

    print("\n=== 4. 全局对话里问投影规律（应同时给三视图 + 证据） ===")
    arts, ans = ask("三视图的长对正高平齐宽相等是怎么来的？")
    print("  画布：", [t for t, _ in arts])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
