"""锚点测试运行器（纯 assert，不依赖 pytest）。

用法（在 ``apps/api`` 目录下）::

    python tests/run_anchors.py

行为
----
* 自动发现 ``tests/anchors/test_*.py`` 中所有 ``test_*`` 函数；
* 逐个运行，打印 ``[PASS]/[FAIL] 模块.函数``；
* 汇总每项与总数；有失败则退出码非 0。

注意：请用带 numpy 的 ``D:\\python\\python.exe``（项目 venv 里的旧工具链尚未清理），
本运行器本身只用标准库。
"""
from __future__ import annotations

import importlib
import sys
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent          # apps/api/tests
API_ROOT = HERE.parent                          # apps/api
ANCHOR_DIR = HERE / "anchors"
MODULE_PREFIX = "anchors"


def _bootstrap() -> None:
    # 让 `import app.*` 可用
    if str(API_ROOT) not in sys.path:
        sys.path.insert(0, str(API_ROOT))
    # 让 `import anchors.*` 可用
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))
    # Windows 控制台默认 GBK，锚点输出含 ⁻¹、ρ 等字符
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # pragma: no cover
        pass


def discover_modules() -> list:
    if not ANCHOR_DIR.is_dir():
        raise SystemExit(f"找不到锚点目录：{ANCHOR_DIR}")
    files = sorted(ANCHOR_DIR.glob("test_*.py"))
    if not files:
        raise SystemExit(f"锚点目录下没有 test_*.py：{ANCHOR_DIR}")
    modules = []
    for path in files:
        name = f"{MODULE_PREFIX}.{path.stem}"
        modules.append(importlib.import_module(name))
    return modules


def main() -> int:
    _bootstrap()
    modules = discover_modules()
    total = 0
    passed = 0
    failures: list[tuple[str, str]] = []
    for module in modules:
        tests = [(name, fn) for name, fn in vars(module).items()
                 if name.startswith("test_") and callable(fn)]
        tests.sort(key=lambda item: item[0])
        for name, fn in tests:
            total += 1
            label = f"{module.__name__}.{name}"
            try:
                fn()
            except Exception as exc:  # noqa: BLE001 - 汇总所有失败后统一退出
                failures.append((label, f"{type(exc).__name__}: {exc}"))
                print(f"[FAIL] {label}")
                traceback.print_exc(limit=3)
            else:
                passed += 1
                print(f"[PASS] {label}")

    print("-" * 72)
    print(f"锚点测试：{passed}/{total} 通过" + ("" if not failures else f"，{len(failures)} 失败"))
    if failures:
        print("失败清单：")
        for label, msg in failures:
            print(f"  - {label}: {msg}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
