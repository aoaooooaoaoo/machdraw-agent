"""验收：费曼追问 + 错题六步诊改（走真实 HTTP）。"""
from __future__ import annotations

import json
import sys
import urllib.request

BASE = "http://127.0.0.1:8077"
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def ask(q: str, feature: str | None = None, account: str = "acc2", history=None):
    msgs = (history or []) + [{"role": "user", "content": q}]
    body = json.dumps({"session_id": "local", "messages": msgs, "feature": feature}).encode()
    req = urllib.request.Request(
        BASE + "/api/chat", data=body,
        headers={"Content-Type": "application/json", "X-Account": account}, method="POST")
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
            if ev["type"] == "artifact":
                arts.append((ev["artifactType"], ev["data"]))
            elif ev["type"] == "tool_result":
                tools.append((ev.get("name"), ev.get("summary")))
            elif ev["type"] == "token":
                ans.append(ev.get("text", ""))
    return arts, tools, "".join(ans)


def main() -> int:
    print("=" * 70)
    print("【费曼追问】第 1 轮")
    statement = "剖视图就是把零件切开来看，比较直观，大概能看出里面的孔。"
    arts, tools, ans = ask(statement, "feynman")
    for n, s in tools:
        print(f"  工具 {n}: {s}")
    for t, d in arts:
        print(f"  画布 {t}: 标注 {len(d.get('annotations', []))} 条 / 追问 {len(d.get('probes', []))} 个")
        for a in d.get("annotations", []):
            print(f"    [{a['color']:5}] {a['label']:6} {a['text'][:30]}  ← {a['comment'][:30]}")
        print(f"    评分: {d.get('score')}")
    print("  回答:")
    for line in ans.splitlines()[:10]:
        print("   ", line)

    print("\n" + "=" * 70)
    print("【费曼追问】第 3 轮（应给总评）")
    hist = [
        {"role": "user", "content": "我来讲讲剖视图"},
        {"role": "assistant", "content": "…"},
        {"role": "user", "content": "剖视图是把内部结构画出来"},
        {"role": "assistant", "content": "…"},
    ]
    arts, tools, ans = ask(
        "剖视图是假想用剖切面剖开机件，移去观察者与剖切面之间的部分，其余向投影面投射得到的图形。",
        "feynman", history=hist)
    for t, d in arts:
        print(f"  画布 {t}: round={d.get('round')} final={d.get('final')} 评分={d.get('score')}")
        print(f"    summary: {d.get('summary')}")

    print("\n" + "=" * 70)
    print("【错题六步诊改】")
    arts, tools, ans = ask("为什么尺寸链不能标注成封闭的？", "wrongbook")
    for n, s in tools:
        print(f"  工具 {n}: {s}")
    for t, d in arts:
        print(f"  画布 {t}: 根因={d.get('root_cause')} 溯源 {len(d.get('trace', []))} 段")
        for s in d.get("steps", []):
            print(f"    {s['n']}. {s['key']}：{str(s['value'])[:56]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
