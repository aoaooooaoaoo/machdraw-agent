"""一键全量验收：跑完所有检查并给出一张总表。

    D:\\桌面\\机械制图agent\\apps\\api\\.venv\\Scripts\\python.exe verify_all.py
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
    ("后端工具自注册", "apps/api/tests/check_tools.py"),
    ("确定性引擎（公差/螺纹/圆弧）", "apps/api/tests/check_engines.py"),
    ("三视图真投影", "apps/api/tests/check_projection.py"),
    ("工具/画布可达性", "apps/api/tests/check_reachability.py"),
    ("模块任务书与代码一致", "scripts/gen-module-docs.py --check"),
    ("剖视图真剖切（全剖）", "apps/api/tests/check_section.py"),
    ("半剖 / 局部剖", "apps/api/tests/check_section_variants.py"),
    ("手绘找茬", "apps/api/tests/check_sketch.py"),
    ("端到端冒烟", "apps/api/tests/smoke.py"),
]


def run(path: str) -> tuple[bool, str]:
    """path 可带参数，例如 "scripts/gen-module-docs.py --check"。

    早期版本直接把整串当路径拼上去，带参数的项会变成找不到文件 —— 这里按空格拆开。
    """
    parts = path.split()
    script = str(ROOT / parts[0])
    cmd = [str(PY), script, *parts[1:]]
    p = subprocess.run(cmd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", cwd=str(ROOT))
    tail = [ln for ln in (p.stdout or "").splitlines() if ln.strip()][-1:] or [""]
    if p.returncode != 0 and not tail[0]:
        err = [ln for ln in (p.stderr or "").splitlines() if ln.strip()][-1:]
        tail = err or ["（无输出）"]
    return p.returncode == 0, tail[0]


def http_json(path: str, timeout: int = 30):
    return json.loads(urllib.request.urlopen("http://127.0.0.1:8077" + path,
                                             timeout=timeout).read().decode("utf-8"))


def main() -> int:
    rows = []
    print("=" * 74)
    print("机械制图 AI 助教 Agent · 全量验收")
    print("=" * 74)

    for name, path in CHECKS:
        ok, tail = run(path)
        rows.append((name, "PASS" if ok else "FAIL", tail))
        print(f"[{'PASS' if ok else 'FAIL'}] {name:26} {tail}")

    # 评测
    p = subprocess.run([str(PY), str(ROOT / "eval" / "run.py")],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       cwd=str(ROOT))
    line = ""
    for ln in (p.stdout or "").splitlines():
        if ln.startswith("τ="):
            line = ln
            break
    rows.append(("检索与门控（54 题标定集）", "PASS" if p.returncode == 0 else "FAIL", line))
    print(f"[{'PASS' if p.returncode == 0 else 'FAIL'}] {'检索与门控（54 题标定集）':26} {line}")

    # 服务健康
    try:
        h = http_json("/api/health")
        ok = h.get("ok") and h.get("chunks", 0) > 0
        detail = (f"语料 {h['chunks']} 块 / {h['docs']} 文档 · 图谱 {h['nodes']} 节点 "
                  f"{h['edges']} 边 · 工具 {len(h['tools'])} 个")
        rows.append(("服务健康", "PASS" if ok else "FAIL", detail))
        print(f"[{'PASS' if ok else 'FAIL'}] {'服务健康':26} {detail}")

        f = http_json("/api/figures")
        print(f"[PASS] {'教学图库':26} {f['total']} 张自绘 SVG")
        m = http_json("/api/models")
        print(f"[PASS] {'三视图模型库':26} {m['total']} 个模型")
    except Exception as exc:
        print(f"[FAIL] 服务未启动或异常：{type(exc).__name__} {exc}")
        rows.append(("服务健康", "FAIL", str(exc)))

    print("=" * 74)
    bad = [r for r in rows if r[1] == "FAIL"]
    print(f"合计 {len(rows)} 项，通过 {len(rows)-len(bad)}，失败 {len(bad)}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
