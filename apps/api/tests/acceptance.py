"""端到端验收：走真实 HTTP，覆盖三条主链路（知识问答 / 公差 / 图谱）。"""
from __future__ import annotations

import json
import sys
import urllib.request

BASE = "http://127.0.0.1:8077"
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def ask(q: str, feature: str | None = None, account: str = "acceptance"):
    body = json.dumps({
        "session_id": "local",
        "messages": [{"role": "user", "content": q}],
        "feature": feature,
    }).encode()
    req = urllib.request.Request(
        BASE + "/api/chat", data=body,
        headers={"Content-Type": "application/json", "X-Account": account}, method="POST",
    )
    stats: dict[str, int] = {}
    arts, tools, ans = [], [], []
    with urllib.request.urlopen(req, timeout=120) as r:
        for raw in r:
            line = raw.decode("utf-8").rstrip()
            if not line.startswith("data: "):
                continue
            p = line[6:]
            if p == "[DONE]":
                break
            ev = json.loads(p)
            t = ev["type"]
            stats[t] = stats.get(t, 0) + 1
            if t == "artifact":
                arts.append(ev.get("artifactType"))
            elif t == "tool_result":
                tools.append((ev.get("name"), ev.get("summary")))
            elif t == "token":
                ans.append(ev.get("text", ""))
    return stats, arts, tools, "".join(ans)


def main() -> int:
    cases = [
        ("三视图的投影规律是什么？", None),
        ("Φ30 H7/k6 是什么配合？", None),
        ("M10 螺纹怎么画？", "coach"),
        ("剖视图依赖哪些前置知识？", "graph"),
        ("铝合金焊接工艺参数怎么确定？", None),
    ]
    for q, feat in cases:
        stats, arts, tools, ans = ask(q, feat)
        print("=" * 70)
        print(f"Q: {q}    feature={feat}")
        print(f"  事件: {stats}")
        print(f"  画布: {arts}")
        for n, s in tools:
            print(f"  工具: {n} → {s}")
        print("  回答:")
        for line in ans.splitlines()[:14]:
            print("   ", line)
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
