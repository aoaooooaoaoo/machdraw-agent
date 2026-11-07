"""工具 tolerance_calc：极限与配合计算（调用 app.domain.tolerance 确定性引擎）。"""
from __future__ import annotations

import importlib

from .base import ToolContext, ToolOutcome
from .spec import ToolSpec


def tolerance_calc(ctx: ToolContext, spec: str = "", **_) -> ToolOutcome:
    try:
        tol = importlib.import_module("app.domain.tolerance")
    except ImportError:
        return ToolOutcome(ok=False, summary="公差引擎尚未就绪", detail="app/domain/tolerance.py 缺失")
    if not spec:
        return ToolOutcome(ok=False, summary="缺少配合代号", detail="请给出如 Φ30 H7/k6 的代号")
    try:
        parsed = tol.parse_fit(spec)
        if not parsed or not parsed.get("hole"):
            return ToolOutcome(ok=False, summary="无法解析配合代号",
                               detail=f"「{spec}」不符合 Φ30 H7/k6 形式")
        shaft = parsed.get("shaft") or "h6"
        res = tol.solve_fit(parsed["phi"], parsed["hole"], shaft)
    except ValueError as exc:
        return ToolOutcome(ok=False, summary="超出标准范围", detail=str(exc))
    except Exception as exc:  # 引擎内部异常不拖垮对话
        return ToolOutcome(ok=False, summary=f"公差计算失败：{type(exc).__name__}", detail=str(exc))

    h, s, f = res["hole"], res["shaft"], res["fit"]
    detail = (
        f"基本尺寸 {res['basic_size']} mm，{res['system']}\n"
        f"孔 {h['code']}：IT={h['IT']}  ES={h['ES']:+.3f}  EI={h['EI']:+.3f}  "
        f"极限尺寸 {h['min']:.3f}~{h['max']:.3f}\n"
        f"轴 {s['code']}：IT={s['IT']}  es={s['es']:+.3f}  ei={s['ei']:+.3f}  "
        f"极限尺寸 {s['min']:.3f}~{s['max']:.3f}\n"
        f"配合：{f['type']}  最大间隙 {f['max_gap']:+.3f}  最小间隙 {f['min_gap']:+.3f}\n"
        f"工艺提示：{res.get('process_hint','')}\n"
        f"依据：{'、'.join(res.get('refs', []))}"
    )
    return ToolOutcome(
        summary=f"Φ{res['basic_size']:g}{h['code']}/{s['code']} → {f['type']}",
        detail=detail,
        artifact_type="tolerance",
        artifact_data=res,
        payload={"result": res},
    )


TOOL = ToolSpec(
    name="tolerance_calc",
    label="公差与配合计算 · {spec}",
    description=(
        "按 GB/T 1800.1-2020/1800.2-2020 计算极限与配合：解析 Φ30 H7/k6 这类代号，"
        "给出孔/轴极限偏差、极限尺寸、配合性质（间隙/过渡/过盈）与工艺提示。"
        "确定性引擎计算，数值零误差，涉及配合标注时必须用它。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "spec": {
                "type": "string",
                "description": "配合代号，如 \"Φ30 H7/k6\"、\"Φ50 H7\"、\"Φ30h6\"、\"Φ20 H8/f7\"",
            },
        },
        "required": ["spec"],
    },
    run=tolerance_calc,
)
