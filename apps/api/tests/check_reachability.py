"""可达性验收：模块 × 工具 × 画布 三角关系没有悬空项。

    D:\\桌面\\教学agent\\核反应堆物理agent\\apps\\api\\.venv\\Scripts\\python.exe apps/api/tests/check_reachability.py

检查：
1. 9 个模块声明的 tools 都在工具总线里；
2. 9 个模块声明的 canvas_kinds 都在 8 类画布里；
3. 每个工具至少被一个模块声明（否则学生永远触发不到）；
4. 每个画布至少被一个模块声明；
5. 前端 features/ 目录（若存在）与画布集合一致。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "apps" / "api"))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from app.contracts.models import ARTIFACT_TYPES  # noqa: E402
from app.state import MODULES  # noqa: E402
from app.tools import TOOLS  # noqa: E402

FAILS: list[str] = []


def check(cond: bool, label: str, detail: str = "") -> None:
    print(f"[{'PASS' if cond else 'FAIL'}] {label}" + (f"  {detail}" if detail else ""))
    if not cond:
        FAILS.append(label)


def main() -> int:
    print("=" * 66)
    print("核反应堆物理 AI 助教 · 模块/工具/画布可达性")
    print("=" * 66)

    used_tools = set()
    used_canvas = set()
    for m in MODULES:
        bad_tools = [t for t in m.tools if t not in TOOLS]
        bad_canvas = [c for c in m.canvas_kinds if c not in ARTIFACT_TYPES]
        check(not bad_tools, f"模块 {m.id} 工具存在", f"缺 {bad_tools}")
        check(not bad_canvas, f"模块 {m.id} 画布合法", f"未知 {bad_canvas}")
        used_tools.update(m.tools)
        used_canvas.update(m.canvas_kinds)

    unreachable = sorted(set(TOOLS) - used_tools)
    check(not unreachable, "每个工具都被模块声明", f"悬空：{unreachable}")
    dead_canvas = sorted(set(ARTIFACT_TYPES) - used_canvas)
    check(not dead_canvas, "每类画布都被模块声明", f"悬空：{dead_canvas}")

    # 前端 features 目录（目录名 = feature.id = artifactType）
    feats = ROOT / "apps" / "web" / "src" / "features"
    if feats.exists():
        dirs = {p.name for p in feats.iterdir() if p.is_dir()}
        mapping = {"three_view": "plot", "tolerance": "calc"}
        dirs = {mapping.get(d, d) for d in dirs}
        check(dirs == set(ARTIFACT_TYPES),
              "前端 features 与画布集合一致",
              f"多 {sorted(dirs - set(ARTIFACT_TYPES))} / 少 {sorted(set(ARTIFACT_TYPES) - dirs)}")

    print("-" * 66)
    if FAILS:
        print(f"失败 {len(FAILS)} 项")
        return 1
    print("全部通过。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
