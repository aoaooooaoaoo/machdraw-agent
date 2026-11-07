"""验收：剖视图 + 剖切（chat 链路 + /api/models?mode=section）。"""
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
                                          "X-Account": "sec"}, method="POST")
    arts, ans = [], []
    with urllib.request.urlopen(req, timeout=180) as r:
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
    print("=== 1. /api/models?mode=section ===")
    d = get("/api/models/M-TUBE?mode=section")
    print(f"  {d['name']} mode={d.get('mode')} 剖切位置={d['cut_at']} "
          f"线段={len(d['segments'])} 剖面线={len(d['hatch'])}")
    print(f"  note: {d['note']}")

    print("\n=== 2. 对话：剖视图怎么画（3D 沙盒模块） ===")
    arts, ans = ask("圆筒的剖视图怎么画？", "sandbox3d")
    for t, data in arts:
        if t == "three_view":
            print(f"  artifact=three_view mode={data.get('mode')} "
                  f"剖面线={len(data.get('hatch') or [])}")
        else:
            print(f"  artifact={t}")
    print("  回答：")
    for line in ans.splitlines()[:10]:
        print("   ", line)

    print("\n=== 3. 对话：全局问剖切 ===")
    arts, ans = ask("带孔零件的剖视图剖开后剖面线怎么画？")
    print("  画布：", [(t, d.get("mode") if t == "three_view" else "") for t, d in arts])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
