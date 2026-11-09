"""工具总线（自注册）。

约定：每个工具 = 本目录下**一个模块** ``<name>.py``，模块内导出 ``TOOL = ToolSpec(...)``，
``TOOL.run`` 是纯函数 ``(ctx: ToolContext, **args) -> ToolOutcome``。
工具不直接发事件，由 orchestrator 统一发 tool_call / tool_result / artifact。

**新增工具只需新增 <name>.py 并定义 TOOL，不需要改本文件。**
启动时用 ``pkgutil.iter_modules`` 扫描本目录自动发现，并按三条硬校验注册（违反即 raise）：

1. ``TOOL.name`` 必须等于模块文件名（去掉 ``.py``）；
2. 工具名不能重复；
3. ``description`` 与 ``parameters`` 必须非空（前者给模型判断何时调用，后者是 JSON Schema）。

跳过 ``__init__`` / ``base`` / ``spec`` 以及以下划线开头的私有辅助模块。

"凡是能算的绝不让模型背"——确定性工具（临界/点堆/燃耗/反应性/能谱）一律调用
app.domain 下的引擎，模型只负责组织语言。
"""
from __future__ import annotations

import importlib
import pkgutil
from typing import Callable

from .base import EVIDENCE_CONSTRAINT, ToolContext, ToolOutcome
from .spec import ToolSpec

__all__ = [
    # 注册表
    "SPECS",
    "TOOLS",
    "TOOL_LABELS",
    "discover",
    # 基元
    "ToolContext",
    "ToolOutcome",
    "ToolSpec",
    "EVIDENCE_CONSTRAINT",
    # 调用
    "call",
    # 工具函数名（向后兼容的转发导出）
    "kb_search",
    "critical_calc",
    "kinetics_calc",
    "poison_calc",
    "burnup_calc",
    "reactivity_calc",
    "spectrum_plot",
    "comparison_pick",
    "kg_lookup",
    "quiz_from_kb",
    "wrongbook_crud",
]

#: 本目录下"不是工具"的模块：包入口、基类、规格。
#: 新增私有辅助模块时请以 ``_`` 开头，或显式加入这个集合。
_SKIP_MODULES = frozenset({"__init__", "base", "spec"})


def discover() -> list[ToolSpec]:
    """扫描本目录，导入所有工具模块并返回规格列表。

    三条硬校验（任一违反直接抛 ``ValueError``，并在消息里带文件名，绝不静默跳过）：

    a) ``TOOL.name`` 必须等于模块名（文件名去掉 ``.py``）；
    b) 工具名不能重复；
    c) ``description`` 与 ``parameters`` 必须非空。

    返回按模块名排序的列表，保证每次启动顺序稳定。
    """
    specs: list[ToolSpec] = []
    seen: dict[str, str] = {}
    modules = sorted(
        (info.name for info in pkgutil.iter_modules(__path__)),
        key=str,
    )
    for name in modules:
        if name in _SKIP_MODULES or name.startswith("_"):
            continue
        try:
            module = importlib.import_module(f"{__name__}.{name}")
        except Exception as exc:  # noqa: BLE001 - 注册期要给可定位的报错
            raise ValueError(
                f"工具注册失败：导入 {name}.py 时出错：{type(exc).__name__}: {exc}"
            ) from exc
        origin = getattr(module, "__file__", f"{__name__}.{name}")

        tool = getattr(module, "TOOL", None)
        if tool is None:
            raise ValueError(
                f"工具注册失败：{origin} 没有导出 TOOL（ToolSpec）。"
                "请补上 `TOOL = ToolSpec(...)`；如果它是辅助模块，请以 `_` 开头命名。"
            )
        if not isinstance(tool, ToolSpec):
            raise ValueError(
                f"工具注册失败：{origin} 导出的 TOOL 必须是 ToolSpec 实例，"
                f"实际是 {type(tool).__name__}"
            )

        # 硬校验 a：name 必须等于文件名（模块名）
        if tool.name != name:
            raise ValueError(
                f"工具注册失败：{origin} 的 TOOL.name={tool.name!r} 与文件名 {name!r} 不一致。"
                f"name 必须等于模块名（去掉 .py），否则无法按名字定位工具。"
            )

        # 硬校验 b：工具名不能重复
        if tool.name in seen:
            raise ValueError(
                f"工具注册失败：{origin} 与 {seen[tool.name]} 重复注册工具名 {tool.name!r}。"
                "请改名（同时改文件名）。"
            )

        # 硬校验 c：description 与 parameters 必须非空
        if not isinstance(tool.description, str) or not tool.description.strip():
            raise ValueError(
                f"工具注册失败：{origin} 的 description 为空。"
                "description 是模型判断「何时调用该工具」的唯一依据，不能缺。"
            )
        if not isinstance(tool.parameters, dict) or not tool.parameters:
            raise ValueError(
                f"工具注册失败：{origin} 的 parameters 为空。"
                "必须给出 JSON Schema（至少 `{\"type\": \"object\", \"properties\": {...}}`）。"
            )
        if not callable(tool.run):
            raise ValueError(
                f"工具注册失败：{origin} 的 TOOL.run 不可调用（应为 (ctx, **args) -> ToolOutcome）"
            )

        seen[tool.name] = origin
        specs.append(tool)

    if not specs:
        raise ValueError(
            f"工具注册失败：{__name__} 目录下没有发现任何工具模块"
            f"（已跳过 {sorted(_SKIP_MODULES)} 与下划线开头的模块）"
        )
    return specs


_SPEC_LIST = discover()

#: 工具规格表：name -> ToolSpec（新增工具自动进入）
SPECS: dict[str, ToolSpec] = {spec.name: spec for spec in _SPEC_LIST}

#: 工具函数表：name -> 可调用对象（历史调用方 `TOOLS[name](ctx, **args)` 不变）
TOOLS: dict[str, Callable[..., ToolOutcome]] = {spec.name: spec.run for spec in _SPEC_LIST}

#: 展示文案（orchestrator._tool_label 依赖它）。
TOOL_LABELS = {
    "kb_search": "检索课程原文",
    "critical_calc": "临界计算",
    "kinetics_calc": "点堆动力学",
    "poison_calc": "氙钐中毒",
    "burnup_calc": "燃耗计算",
    "reactivity_calc": "反应性换算",
    "spectrum_plot": "能谱曲线",
    "comparison_pick": "概念辨析",
    "kg_lookup": "知识图谱查询",
    "quiz_from_kb": "从题库出题",
    "wrongbook_crud": "错题本",
}


def call(name: str, ctx: ToolContext, **args) -> ToolOutcome:
    fn = TOOLS.get(name)
    if fn is None:
        return ToolOutcome(ok=False, summary=f"未知工具 {name}", detail="")
    try:
        return fn(ctx, **args)
    except Exception as exc:
        return ToolOutcome(ok=False, summary=f"{name} 执行失败：{type(exc).__name__}", detail=str(exc))


# ---------------------------------------------------------------------------
# 转发导出：`from app.tools import kb_search` 等函数名照旧可用
# ---------------------------------------------------------------------------
from .burnup_calc import burnup_calc  # noqa: E402
from .comparison_pick import comparison_pick  # noqa: E402
from .critical_calc import critical_calc  # noqa: E402
from .kb_search import kb_search  # noqa: E402
from .kg_lookup import kg_lookup  # noqa: E402
from .kinetics_calc import kinetics_calc  # noqa: E402
from .poison_calc import poison_calc  # noqa: E402
from .quiz_from_kb import quiz_from_kb  # noqa: E402
from .reactivity_calc import reactivity_calc  # noqa: E402
from .spectrum_plot import spectrum_plot  # noqa: E402
from .wrongbook_crud import wrongbook_crud  # noqa: E402
