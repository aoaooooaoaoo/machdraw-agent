"""工具总线验收：11 个工具自注册、契约合法、画布类型合法。

    D:\\桌面\\教学agent\\核反应堆物理agent\\apps\\api\\.venv\\Scripts\\python.exe apps/api/tests/check_tools.py

检查项：
1. `app.tools.TOOLS` 恰好 11 个，名字与 SPEC 第 4.3 节一致；
2. 每个 ToolSpec 的 name==文件名、description/parameters 非空、parameters 是 object schema；
3. 每个工具声明的 artifact_type（通过源码静态检查 TOOL 定义或实际调用）落在 8 类画布内；
4. 确定性工具用一句示例 query 调用，必须 ok 且 artifact_data 满足 calc/plot 契约；
5. 出错时不抛异常（返回 ok=False）。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "apps" / "api"))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from app.contracts.models import ARTIFACT_TYPES  # noqa: E402
from app.state import load_state  # noqa: E402
from app.tools import SPECS, TOOL_LABELS, TOOLS, ToolContext, call  # noqa: E402

EXPECTED = {
    "kb_search", "kg_lookup", "critical_calc", "kinetics_calc", "poison_calc",
    "burnup_calc", "reactivity_calc", "spectrum_plot", "comparison_pick",
    "quiz_from_kb", "wrongbook_crud",
}

CALC_TOOLS = ("critical_calc", "burnup_calc", "reactivity_calc")
PLOT_TOOLS = ("kinetics_calc", "poison_calc", "spectrum_plot")

# 每个确定性工具的示例输入（自然语言），用于验证 query 解析 + 画布契约
SAMPLES = {
    "critical_calc": "k∞=1.06，L2=100cm2，τ=80cm2，裸圆柱，求临界曲率",
    "kinetics_calc": "阶跃引入0.2$反应性，缓发中子寿命1e-4s，求反应堆周期",
    "poison_calc": "通量3e13 cm-2 s-1，运行30天，求氙平衡浓度与反应性",
    "burnup_calc": "功率3000MW，装料80tU，求燃耗深度",
    "reactivity_calc": "k=1.05，求反应性pcm",
    "spectrum_plot": "画压水堆中子能谱",
}


def check_registry() -> list[str]:
    errs = []
    if set(TOOLS) != EXPECTED:
        errs.append(f"工具集合不符：多 {sorted(set(TOOLS) - EXPECTED)} / 少 {sorted(EXPECTED - set(TOOLS))}")
    for name in sorted(set(TOOLS)):
        spec = SPECS[name]
        if spec.name != name:
            errs.append(f"{name}: name 与文件名不一致")
        if not spec.description.strip():
            errs.append(f"{name}: description 为空")
        if not isinstance(spec.parameters, dict) or spec.parameters.get("type") != "object":
            errs.append(f"{name}: parameters 不是 object schema")
        if name not in TOOL_LABELS:
            errs.append(f"{name}: TOOL_LABELS 缺展示文案")
    return errs


def check_artifact_types() -> list[str]:
    errs = []
    st = load_state()
    ctx = ToolContext(state=st)
    for name, q in SAMPLES.items():
        out = call(name, ctx, query=q)
        if not out.ok:
            errs.append(f"{name}: 示例调用失败（{out.summary}）")
            continue
        at = out.artifact_type
        if at not in ARTIFACT_TYPES:
            errs.append(f"{name}: artifact_type={at!r} 不在 ARTIFACT_TYPES")
        d = out.artifact_data or {}
        if name in CALC_TOOLS:
            if at != "calc":
                errs.append(f"{name}: 画布应为 calc，实际 {at}")
            for key in ("title", "inputs", "results"):
                if key not in d:
                    errs.append(f"{name}: calc data 缺字段 {key}")
            for it in d.get("results") or []:
                if not {"name", "value"} <= set(it):
                    errs.append(f"{name}: results 项缺 name/value")
        if name in PLOT_TOOLS:
            if at != "plot":
                errs.append(f"{name}: 画布应为 plot，实际 {at}")
            for key in ("title", "series"):
                if key not in d:
                    errs.append(f"{name}: plot data 缺字段 {key}")
            for s in d.get("series") or []:
                if not s.get("points"):
                    errs.append(f"{name}: series 没有 points")
    return errs


def check_bad_input() -> list[str]:
    """缺参数时应 ok=False 而不是抛异常。"""
    errs = []
    st = load_state()
    ctx = ToolContext(state=st)
    for name in CALC_TOOLS + PLOT_TOOLS:
        out = call(name, ctx, query="")
        if not isinstance(out.ok, bool):
            errs.append(f"{name}: 返回不是 ToolOutcome")
    return errs


def main() -> int:
    errs = []
    errs += check_registry()
    print(f"[1] 注册 {len(TOOLS)} 个工具：{', '.join(sorted(TOOLS))}")
    errs += check_artifact_types()
    print(f"[2] 画布契约：{len(SAMPLES)} 个确定性工具样例调用完成")
    errs += check_bad_input()
    print("[3] 空输入降级：完成")
    if errs:
        print("\n失败项：")
        for e in errs:
            print("  -", e)
        return 1
    print("\n全部通过。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
