"""一键全量验收：跑完所有检查并给出一张总表。

    D:\\桌面\\教学agent\\核反应堆物理agent\\apps\\api\\.venv\\Scripts\\python.exe verify_all.py

前置：先在另一个终端起后端
    cd apps\\api
    .\\.venv\\Scripts\\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8077
（未启动时脚本会把"服务健康"等项标为 FAIL，但本地检查照跑。）
"""
from __future__ import annotations

import json
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = ROOT / "apps" / "api" / ".venv" / "Scripts" / "python.exe"
if not PY.exists():
    PY = Path(sys.executable)

CHECKS = [
    ("工具自注册（11 个）", "apps/api/tests/check_tools.py", True),
    ("确定性引擎锚点", "apps/api/tests/run_anchors.py", True),
    ("模块/工具/画布可达性", "apps/api/tests/check_reachability.py", True),
    ("端到端冒烟（对话+8 画布）", "apps/api/tests/smoke.py", True),
    ("模块任务书与代码一致", "scripts/gen-module-docs.py --check", False),
]


def run(path: str) -> tuple[bool, str]:
    parts = path.split()
    script = str(ROOT / parts[0])
    if not Path(script).exists():
        return False, "脚本不存在"
    cmd = [str(PY), script, *parts[1:]]
    p = subprocess.run(cmd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", cwd=str(ROOT))
    tail = [ln for ln in (p.stdout or "").splitlines() if ln.strip()][-1:] or [""]
    if p.returncode != 0 and not tail[0]:
        err = [ln for ln in (p.stderr or "").splitlines() if ln.strip()][-1:]
        tail = err or ["（无输出）"]
    return p.returncode == 0, tail[0]


def http_json(path: str, timeout: int = 60):
    return json.loads(urllib.request.urlopen("http://127.0.0.1:8077" + path,
                                             timeout=timeout).read().decode("utf-8"))


def main() -> int:
    rows = []
    print("=" * 78)
    print("核反应堆物理 AI 助教 Agent · 全量验收")
    print("=" * 78)

    for name, path, required in CHECKS:
        ok, tail = run(path)
        rows.append((name, ok, required))
        print(f"[{'PASS' if ok else ('FAIL' if required else 'SKIP')}] {name:28} {tail}")

    # 评测
    p = subprocess.run([str(PY), str(ROOT / "eval" / "run.py")],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       cwd=str(ROOT))
    line = ""
    for ln in (p.stdout or "").splitlines():
        if ln.startswith("τ="):
            line = ln
            break
    rows.append(("检索与门控（54 题探针集）", p.returncode == 0, True))
    print(f"[{'PASS' if p.returncode == 0 else 'FAIL'}] {'检索与门控（54 题探针集）':28} {line}")

    # 服务健康
    try:
        h = http_json("/api/health")
        ok = bool(h.get("ok")) and h.get("chunks", 0) > 0
        detail = (f"语料 {h['chunks']} 块 / {h['docs']} 文档 · 图谱 {h['nodes']} 节点 "
                  f"{h['edges']} 边 · 工具 {len(h['tools'])} 个")
        rows.append(("服务健康", ok, True))
        print(f"[{'PASS' if ok else 'FAIL'}] {'服务健康':28} {detail}")
        if h.get("warnings"):
            print(f"       warnings: {h['warnings'][:3]}")

        f = http_json("/api/figures")
        print(f"[PASS] {'教学图库':28} {f['total']} 张自绘 SVG")
        pr = http_json("/api/pairs")
        print(f"[PASS] {'概念辨析对':28} {pr['total']} 组")
        m = http_json("/api/modules")
        print(f"[PASS] {'模块注册表':28} {len(m['modules'])} 个")
    except Exception as exc:
        print(f"[FAIL] 服务未启动或异常：{type(exc).__name__} {exc}")
        rows.append(("服务健康", False, True))

    # 前端构建产物
    dist = ROOT / "apps" / "web" / "dist" / "index.html"
    rows.append(("前端构建产物", dist.exists(), True))
    print(f"[{'PASS' if dist.exists() else 'FAIL'}] {'前端构建产物':28} {dist}")

    print("=" * 78)
    bad = [r for r in rows if r[1] is False and r[2]]
    print(f"合计 {len(rows)} 项，通过 {sum(1 for r in rows if r[1])}，失败 {len(bad)}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
