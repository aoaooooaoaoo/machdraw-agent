"""验收：教学图库接入（/api/figures + 静态 SVG + 证据卡配图）。"""
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
    return urllib.request.urlopen(BASE + path, timeout=15)


def ask(q: str):
    body = json.dumps({"session_id": "local", "messages": [{"role": "user", "content": q}]}).encode()
    req = urllib.request.Request(BASE + "/api/chat", data=body,
                                headers={"Content-Type": "application/json", "X-Account": "fig"},
                                method="POST")
    figs, ev = [], 0
    with urllib.request.urlopen(req, timeout=90) as r:
        for raw in r:
            line = raw.decode("utf-8").rstrip()
            if not line.startswith("data: "):
                continue
            p = line[6:]
            if p == "[DONE]":
                break
            e = json.loads(p)
            if e["type"] == "artifact" and e.get("artifactType") == "evidence":
                d = e["data"]
                ev = len(d.get("evidences") or [])
                figs = d.get("figures") or []
    return ev, figs


def main() -> int:
    print("=== 1. /api/figures ===")
    d = json.loads(get("/api/figures").read().decode("utf-8"))
    print(f"  图形总数 {d['total']}")
    for f in d["figures"][:3]:
        print(f"   - {f['figure_id']:24} {f['title'][:26]}  章:{f['chapter'][:10]}")
    print("   ...")

    print("\n=== 2. 静态 SVG 可取 ===")
    for fid in ("FIG-LINETYPE.svg", "FIG-SANSHITU-BASE.svg", "FIG-POU-SHI-QUAN.svg"):
        try:
            r = get("/figures/" + fid)
            raw = r.read()
            print(f"   OK  /figures/{fid:24} {r.status} {len(raw)} bytes  <svg={b'<svg' in raw}")
        except Exception as e:
            print(f"   --  /figures/{fid:24} {type(e).__name__}")

    print("\n=== 3. 证据卡自动配图 ===")
    for q in ["三视图的投影规律是什么？", "剖视图和断面图有什么区别？", "表面粗糙度 Ra 怎么标注？"]:
        ev, figs = ask(q)
        print(f"   Q: {q}")
        print(f"      证据 {ev} 段 · 配图 {len(figs)} 张")
        for f in figs:
            print(f"       - {f['figure_id']:26} {f['title'][:24]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
