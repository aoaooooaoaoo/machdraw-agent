"""端到端 HTTP 验收：起一个**本脚本自己启动的** uvicorn（端口 8093），跑全部只读接口与对话接口，最后只关自己这个进程。

    D:\\桌面\\教学agent\\核反应堆物理agent\\apps\\api\\.venv\\Scripts\\python.exe scripts\\e2e_check.py

覆盖：
- GET /api/health、/api/modules、/api/graph、/api/figures、/api/pairs、/api/stats、/、/admin
- POST /api/chat/sync（mock 模式；3 个问题：课内概念 / 临界计算 / 课外拒答）
- 校验 SSE 事件序列与 artifact 类型

安全：只终止本脚本启动的子进程 PID；不按名称杀进程，不碰任何用户程序。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PORT = 8093
BASE = f"http://127.0.0.1:{PORT}"
PY = ROOT / "apps" / "api" / ".venv" / "Scripts" / "python.exe"
if not PY.exists():
    PY = Path(sys.executable)

FAILS: list[str] = []


def check(cond: bool, label: str, detail: str = "") -> None:
    print(f"[{'PASS' if cond else 'FAIL'}] {label}" + (f"  {detail}" if detail else ""))
    if not cond:
        FAILS.append(label)


def http(path: str, method: str = "GET", payload: dict | None = None, timeout: int = 90):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        BASE + path, data=data, method=method,
        headers={"Content-Type": "application/json"} if data else {},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
        ctype = resp.headers.get("Content-Type", "")
        return json.loads(raw) if "json" in ctype else raw


def wait_up(timeout: float = 60.0) -> bool:
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            h = http("/api/health", timeout=5)
            return bool(h.get("ok"))
        except Exception:
            time.sleep(1.0)
    return False


def main() -> int:
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["RP_LLM_PROVIDER"] = "mock"
    print("=" * 70)
    print("核反应堆物理 AI 助教 · 端到端 HTTP 验收")
    print("=" * 70)
    cmd = [str(PY), "-m", "uvicorn", "app.main:app",
           "--host", "127.0.0.1", "--port", str(PORT), "--app-dir", str(ROOT / "apps" / "api")]
    proc = subprocess.Popen(cmd, cwd=str(ROOT), env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        if not wait_up():
            print("[FAIL] 服务 60s 内未就绪")
            return 1
        print(f"[ok] 服务已起（pid={proc.pid}）\n")

        h = http("/api/health")
        check(bool(h.get("ok")) and h.get("chunks", 0) > 0, "GET /api/health",
              f"chunks={h.get('chunks')} docs={h.get('docs')} tools={len(h.get('tools') or [])} "
              f"nodes={h.get('nodes')} edges={h.get('edges')}")
        check(not h.get("warnings"), "健康检查无 warning", str(h.get("warnings")[:2]))
        mods = http("/api/modules")["modules"]
        check(len(mods) == 10, "GET /api/modules 10 个模块", f"{[m['id'] for m in mods]}")
        g = http("/api/graph")
        check(len(g["nodes"]) >= 140 and len(g["edges"]) >= 220, "GET /api/graph",
              f"{len(g['nodes'])} 节点 / {len(g['edges'])} 边 / {len(g['questions'])} 问")
        check(bool(g.get("sectors")), "图谱星图 sectors 投影", f"{len(g.get('sectors') or [])} 个星系")
        fg = http("/api/figures")
        check(fg["total"] >= 26, "GET /api/figures", f"{fg['total']} 张")
        pr = http("/api/pairs")
        check(pr["total"] >= 6, "GET /api/pairs", f"{pr['total']} 组")
        idx = http("/")
        check(isinstance(idx, str) and "<div id=\"root\">" in idx, "GET / 前端壳已托管")
        adm = http("/admin")
        check(isinstance(adm, str) and "教师端" in adm, "GET /admin 教师端页面")
        st = http("/api/stats")
        check("events" in st, "GET /api/stats")

        # ---- 对话（mock 抽取模式）
        cases = [
            ("什么是缓发中子？为什么重要？", "evidence"),
            ("k∞=1.06、M2=180cm2 的裸堆临界曲率是多少？", "calc"),
            ("帮我出一道题", "quiz"),
            ("齿轮的模数怎么确定？", "evidence"),   # 课外 → 应拒答
        ]
        for q, want in cases:
            r = http("/api/chat/sync", "POST", {
                "session_id": "e2e",
                "messages": [{"role": "user", "content": q}],
            })
            evs = r.get("events") or []
            types = [e.get("type") for e in evs]
            arts = [e.get("artifactType") for e in evs if e.get("type") == "artifact"]
            ok = types and types[0] == "thinking" and types[-1] == "done" and bool((r.get("answer") or "").strip())
            check(ok, f"POST /api/chat/sync「{q[:16]}…」",
                  f"events={len(evs)} artifacts={arts}")
            if want == "calc":
                check("calc" in arts, "  临界计算产出 calc 画布", str(arts))
            if "齿轮" in q:
                check("知识库未收录" in (r.get("answer") or ""), "  课外问题被拒答",
                      (r.get("answer") or "")[:30])
    except urllib.error.HTTPError as exc:
        print(f"[FAIL] HTTP {exc.code}: {exc.read()[:300]!r}")
        FAILS.append(f"HTTP {exc.code}")
    except Exception as exc:
        print(f"[FAIL] {type(exc).__name__}: {exc}")
        FAILS.append(type(exc).__name__)
    finally:
        # 只关本脚本启动的进程
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
            print(f"\n[ok] 已关闭本脚本启动的 uvicorn（pid={proc.pid}）")

    print("=" * 70)
    if FAILS:
        print(f"失败 {len(FAILS)} 项：{FAILS}")
        return 1
    print("全部通过。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
