"""后端工具自注册自检：三条硬校验 + 编排器引用一致性 + 公共 API 兼容性。

    D:\\桌面\\机械制图agent\\apps\\api\\.venv\\Scripts\\python.exe apps/api/tests/check_tools.py

检查内容
--------
1. 扫描 ``app/tools/*.py`` 并独立验证注册规则（不依赖注册表自己"说"通过）：
   a) ``TOOL.name`` 必须等于文件名（去掉 .py）；
   b) 工具名不能重复；
   c) ``description`` 与 ``parameters`` 必须非空。
2. 注册表 ``SPECS`` / ``TOOLS`` 与扫描结果一致，每个 ``TOOL.run`` 可调用。
3. ``orchestrator._plan()`` 里出现的工具名必须都在 ``SPECS`` 里
   （防止编排器引用了被改名/删除的工具）。
4. 公共 API 兼容：``TOOLS`` / ``ToolContext`` / ``ToolOutcome`` / 11 个函数名仍可从
   ``app.tools`` 导入，且函数对象就是 ``TOOLS[name]``。

退出码：0 = 全绿；1 = 有问题（逐条打印）。
"""
from __future__ import annotations

import importlib
import inspect
import re
import sys
from pathlib import Path

API = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API))

try:  # Windows 控制台默认 GBK，中文/符号会打崩
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from app import orchestrator as orch  # noqa: E402
from app.tools import SPECS, TOOLS, ToolContext, ToolOutcome  # noqa: E402
from app.tools.spec import ToolSpec  # noqa: E402

TOOLS_DIR = API / "app" / "tools"
SKIP = {"__init__", "base", "spec"}
failures: list[str] = []


def fail(message: str) -> None:
    failures.append(message)
    print(f"  FAIL {message}")


print("=" * 74)
print("后端工具自注册自检")
print("=" * 74)

# ---------- 1. 独立扫描目录，逐条验证三条硬校验 ----------
print(f"\n[1] 扫描 {TOOLS_DIR}（规则：name=文件名 / 不重名 / description+parameters 非空）")
modules = sorted(
    path.stem
    for path in TOOLS_DIR.glob("*.py")
    if path.stem not in SKIP and not path.stem.startswith("_")
)
print(f"  发现 {len(modules)} 个候选工具模块：{', '.join(modules)}")

scanned: dict[str, ToolSpec] = {}
scanned_roots: dict[str, str] = {}
for name in modules:
    try:
        module = importlib.import_module(f"app.tools.{name}")
    except Exception as exc:  # noqa: BLE001 - 自检需要报清楚
        fail(f"{name}.py 导入失败：{type(exc).__name__}: {exc}")
        continue
    tool = getattr(module, "TOOL", None)
    file_hint = f"{name}.py"
    if tool is None:
        fail(f"{file_hint} 没有导出 TOOL（ToolSpec）")
        continue
    if not isinstance(tool, ToolSpec):
        fail(f"{file_hint} 的 TOOL 不是 ToolSpec（实际 {type(tool).__name__}）")
        continue
    # a) name == 文件名
    if tool.name != name:
        fail(f"{file_hint} 的 TOOL.name={tool.name!r} 与文件名不一致")
        continue
    # b) 不重名
    if tool.name in scanned:
        fail(f"{file_hint} 与 {scanned_roots[tool.name]} 重复注册 {tool.name!r}")
        continue
    # c) description / parameters 非空
    if not tool.description.strip():
        fail(f"{file_hint} 的 description 为空")
    if not tool.parameters:
        fail(f"{file_hint} 的 parameters 为空（必须给 JSON Schema）")
    if not callable(tool.run):
        fail(f"{file_hint} 的 TOOL.run 不可调用")
    scanned[tool.name] = tool
    scanned_roots[tool.name] = file_hint

print(f"  通过 {len(scanned)}/{len(modules)} 个模块的三条硬校验")

# ---------- 2. 注册表与扫描结果一致 ----------
print("\n[2] 注册表一致性")
if set(scanned) != set(SPECS):
    fail(f"扫描结果与 SPECS 不一致：扫描 {sorted(scanned)} vs 注册 {sorted(SPECS)}")
else:
    print(f"  SPECS 与扫描结果一致（{len(SPECS)} 个）")
if set(SPECS) != set(TOOLS):
    fail(f"SPECS 与 TOOLS 的键不一致：{sorted(SPECS)} vs {sorted(TOOLS)}")
for name, spec in SPECS.items():
    if TOOLS.get(name) is not spec.run:
        fail(f"{name}: TOOLS[name] 不是 TOOL.run")
    if not callable(spec.run):
        fail(f"{name}: TOOL.run 不可调用")

# ---------- 3. 编排器 _plan() 引用检查 ----------
print("\n[3] 编排器 _plan() 引用的工具名")
plan_src = inspect.getsource(orch._plan)
referenced = sorted(set(re.findall(r'"name"\s*:\s*"([a-z_0-9]+)"', plan_src)))
missing = [name for name in referenced if name not in SPECS]
print(f"  _plan() 引用 {len(referenced)} 个工具：{', '.join(referenced)}")
if missing:
    fail(f"编排器引用了不存在的工具：{', '.join(missing)}（改名/删除工具时必须同步）")
else:
    print("  全部引用都在 SPECS 中")

# ---------- 4. 公共 API 兼容性 ----------
print("\n[4] 公共 API 兼容性")
LEGACY_NAMES = [
    "kb_search", "tolerance_calc", "thread_calc", "arc_construct",
    "projection_render", "section_render", "sketch_grade",
    "comparison_pick", "kg_lookup", "quiz_from_kb", "wrongbook_crud",
]
app_tools = importlib.import_module("app.tools")
for legacy in LEGACY_NAMES:
    func = getattr(app_tools, legacy, None)
    if func is None:
        fail(f"app.tools 缺少历史函数名 {legacy}")
    elif TOOLS.get(legacy) is not func:
        fail(f"app.tools.{legacy} 与 TOOLS['{legacy}'] 不是同一个函数")
for legacy in ("ToolContext", "ToolOutcome"):
    if getattr(app_tools, legacy, None) is None:
        fail(f"app.tools 缺少 {legacy}")
if not isinstance(app_tools.TOOLS, dict):
    fail("TOOLS 不是 dict")
if not failures:
    print("  11 个历史函数名 + ToolContext/ToolOutcome/TOOLS 全部可用")

# ---------- 5. 参数表与函数签名一致性（提示，不计失败） ----------
print("\n[5] 参数表与函数签名一致性（提示项，不计失败）")
warn_count = 0
for name, spec in SPECS.items():
    try:
        sig = inspect.signature(spec.run)
    except (TypeError, ValueError):
        continue
    accepts_kwargs = any(
        p.kind is inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
    )
    if accepts_kwargs:
        continue  # 函数以 **kwargs 兜底，参数表可以自由扩展
    accepted = {
        p.name for p in sig.parameters.values()
        if p.kind in (p.POSITIONAL_OR_KEYWORD, p.KEYWORD_ONLY)
    }
    declared = set((spec.parameters.get("properties") or {}).keys())
    extra = sorted(declared - accepted)
    if extra:
        warn_count += 1
        print(f"  WARN {name}: 参数表声明了函数签名不接收的参数 {extra}")
if warn_count == 0:
    print("  无漂移：所有工具的参数表都在函数签名可接受范围内")

# ---------- 工具清单 ----------
print("\n[6] 工具清单")
for index, spec in enumerate(SPECS.values(), 1):
    param_names = list((spec.parameters.get("properties") or {}).keys())
    print(
        f"  {index:2d}. {spec.name:18s} label={spec.label!r:34s} "
        f"params={len(param_names)} {param_names}"
    )

# ---------- 汇总 ----------
print("\n" + "=" * 74)
if failures:
    print(f"发现问题 {len(failures)} 条：")
    for item in failures:
        print(f"  ✗ {item}")
    raise SystemExit(1)
print(f"全部通过：{len(SPECS)} 个工具自注册成功 · 三条硬校验全绿 · "
      f"编排器引用 {len(referenced)} 个工具全部存在 · 公共 API 兼容")
raise SystemExit(0)
