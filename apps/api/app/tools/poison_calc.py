"""工具 poison_calc：氙/钐中毒与停堆暂态（调用 app.domain.poison）。

只传 query 时解析 Φ=3e13 cm-2 s-1、运行/照射 200 天、停堆 60 小时、钐/氙 等。
spec 第4.3 节：name=poison_calc，画布 ``plot``。
"""
from __future__ import annotations

import importlib
import re

from .base import ToolContext, ToolOutcome
from .spec import ToolSpec

_NUM = r"([-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)"
_TIME_U = r"(s|sec|秒|min|分钟|h|hr|小时|d|day|天|周|week)"


def _grab(text: str, patterns: list[str], default=None):
    for p in patterns:
        m = re.search(p, text, re.I)
        if m:
            try:
                val = float(m.group(1))
            except (TypeError, ValueError, IndexError):
                continue
            unit = (m.group(2) if m.lastindex and m.lastindex >= 2 and m.group(2) else "")
            return val, unit
    return default, ""


def _to_hours(value: float, unit: str) -> float:
    u = (unit or "h").lower()
    if u in ("s", "sec", "秒"):
        return value / 3600.0
    if u in ("min", "分钟"):
        return value / 60.0
    if u in ("h", "hr", "小时"):
        return value
    if u in ("d", "day", "天"):
        return value * 24.0
    if u in ("周", "week"):
        return value * 24.0 * 7.0
    return value


def poison_calc(ctx: ToolContext, query: str = "", mode: str = "",
                flux: float | None = None, t_irr: float | None = None,
                t_down: float | None = None, time_unit: str = "h",
                rho_ex0_pcm: float | None = None, **_) -> ToolOutcome:
    q = query or ""
    try:
        poison = importlib.import_module("app.domain.poison")
    except ImportError:
        return ToolOutcome(ok=False, summary="中毒引擎尚未就绪",
                           detail="app/domain/poison.py 缺失")

    m = (mode or "").strip().lower()
    if not m:
        if re.search(r"钐|Sm\b|samarium", q, re.I):
            m = "samarium"
        elif re.search(r"氙|Xe\b|xenon|碘坑", q, re.I):
            m = "xenon"
        elif re.search(r"钷|Pm\b", q, re.I):
            m = "samarium"
        else:
            m = ""
    if not m:
        return ToolOutcome(
            ok=False, summary="请说明研究氙中毒还是钐中毒",
            detail="示例：氙：停堆后碘坑（Φ=3e13 cm-2 s-1，运行 200 天，停堆 60 小时）；"
                   "钐：运行 200 天停堆后 Sm-149 积累。",
        )

    # ---------------- 通量
    if flux is None:
        val, _u = _grab(q, [
            r"(?:Φ|phi|通量|中子通量密度)\s*[=:：]?\s*" + _NUM + r"\s*(?:cm-2|cm\^-2|cm⁻²|m-2|m\^-2|m⁻²)?",
            _NUM + r"\s*(?:cm-2|cm\^-2|cm⁻²)\s*s-1",
        ])
        if val is not None:
            flux = val
    if flux is None:
        flux = poison.FLUX_DEFAULT
        flux_note = f"未给通量，采用教学默认 Φ={poison.FLUX_DEFAULT:g} cm⁻²s⁻¹（习题 v4.0 题6.7 的 100%FP 假设）"
    else:
        flux_note = f"Φ={flux:g} cm⁻²s⁻¹"

    # ---------------- 时间
    if t_irr is None:
        val, u = _grab(q, [r"(?:t_irr|照射时间|运行时间|满功率运行|运行)\s*[=:：]?\s*" + _NUM + r"\s*" + _TIME_U])
        if val is not None:
            t_irr = _to_hours(val, u or "h")
    if t_down is None:
        val, u = _grab(q, [r"(?:t_down|停堆时间|停堆后|停堆)\s*[=:：]?\s*" + _NUM + r"\s*" + _TIME_U])
        if val is not None:
            t_down = _to_hours(val, u or "h")
    t_irr = 200.0 * 24.0 if t_irr is None else float(t_irr)
    t_down = 60.0 if t_down is None else float(t_down)
    if t_irr <= 0 or t_down <= 0:
        return ToolOutcome(ok=False, summary="时间参数必须为正",
                           detail=f"收到 t_irr={t_irr} h、t_down={t_down} h")
    if rho_ex0_pcm is None:
        val, _u = _grab(q, [r"(?:剩余反应性|ρ_ex0|rho_ex0)\s*[=:：]?\s*" + _NUM + r"\s*(?:pcm)?"])
        if val is not None:
            rho_ex0_pcm = val
    rho_ex0_pcm = 0.0 if rho_ex0_pcm is None else float(rho_ex0_pcm)

    try:
        if m == "samarium":
            res = poison.samarium_transient(float(flux), t_irr, t_down, time_unit="h")
            eq = poison.samarium_equilibrium(float(flux))
            series_names = ("N_Pm-149", "N_Sm-149")
            rho_key = "rho_sm_pcm"
            title = "钷-钐（Pm-149→Sm-149）中毒暂态（运行+停堆）"
            eq_note = (f"平衡钐反应性当量 ρ_Sm={eq['results']['rho_sm_pcm']:.1f} pcm"
                       "（与通量无关，教材 p.108）")
            extra = [
                {"name": "平衡 N_Pm", "value": eq["results"]["N_Pm_eq"], "unit": "cm⁻³", "note": "γ_PmΣfΦ/λ_Pm"},
                {"name": "平衡 N_Sm", "value": eq["results"]["N_Sm_eq"], "unit": "cm⁻³", "note": "与 Φ 无关"},
                {"name": "ρ_Sm(平衡)", "value": round(eq["results"]["rho_sm_pcm"], 2), "unit": "pcm", "note": "教材 p.108 约 0.007"},
            ]
        else:
            res = poison.xenon_transient(float(flux), t_irr, t_down, time_unit="h",
                                         rho_ex0_pcm=rho_ex0_pcm)
            eq = poison.xenon_equilibrium(float(flux))
            series_names = ("N_I-135", "N_Xe-135")
            rho_key = "rho_xe_pcm"
            title = "碘-氙（I-135→Xe-135）中毒暂态（运行+停堆）"
            eq_note = (f"平衡氙反应性当量 ρ_Xe={eq['results']['rho_xe_pcm']:.1f} pcm"
                       "（教材 p.105 对 GW 级堆约 0.04~0.05）")
            extra = [
                {"name": "平衡 N_I", "value": eq["results"]["N_I_eq"], "unit": "cm⁻³", "note": "γ_IΣfΦ/λ_I"},
                {"name": "平衡 N_Xe", "value": eq["results"]["N_Xe_eq"], "unit": "cm⁻³", "note": "(γ_I+γ_Xe)ΣfΦ/(λ_Xe+σ_XeΦ)"},
                {"name": "ρ_Xe(平衡)", "value": round(eq["results"]["rho_xe_pcm"], 2), "unit": "pcm", "note": "教材 p.105 约 0.04~0.05"},
                {"name": "碘坑深度", "value": round(res["results"]["iodine_pit_depth_pcm"], 2), "unit": "pcm",
                 "note": "ρ_Xe(t_max)−ρ_Xe(停堆)"},
                {"name": "最大碘坑时刻", "value": round(res["results"]["max_pit_time_h"], 3), "unit": "h", "note": "停堆后"},
            ]
    except ValueError as exc:
        return ToolOutcome(ok=False, summary="中毒计算失败", detail=str(exc))

    # 曲线：为看清停堆瞬变，照射段只保留停堆前 48 h
    shut = res["results"]["shutdown_time_h"]
    t0 = max(0.0, shut - 48.0)
    kept = []
    for name, pts in ((series_names[0], res["series"][0]["points"]),
                      (series_names[1], res["series"][1]["points"])):
        kept.append({"name": name, "points": [[t, v] for t, v in pts if t >= t0]})
    svg = _svg(kept, "t / h", "核素浓度 / cm⁻³", title)
    series_out = kept
    x_label = "t / h（含停堆前最后 48 h）"

    artifact = {
        "kind": "curve",
        "title": title,
        "x_label": x_label,
        "y_label": "核素浓度 / cm⁻³",
        "series": series_out,
        "markers": [{"x": shut, "y": res["results"]["N_Xe_at_shutdown"] if m != "samarium"
                     else res["results"]["N_Sm_at_shutdown"], "label": "停堆"}],
        "results": extra,
        "note": (f"{flux_note}；t_irr={t_irr / 24:.4g} d，t_down={t_down:.4g} h。" + eq_note),
        "refs": res["refs"],
        "svg": svg,
    }
    if m == "samarium":
        summary = (f"钐中毒：平衡 ρ_Sm={eq['results']['rho_sm_pcm']:.1f} pcm；"
                   f"运行 {t_irr / 24:.4g} d + 停堆 {t_down:.4g} h")
        detail_lines = [
            f"【模型】Pm-149→Sm-149 链，恒定通量解析解（教材 6.2.2 p.107-109）",
            f"【输入】Φ={float(flux):g} cm⁻²s⁻¹；t_irr={t_irr:.6g} h；t_down={t_down:.6g} h",
            f"【平衡】N_Pm={eq['results']['N_Pm_eq']:.4g} cm⁻³，N_Sm={eq['results']['N_Sm_eq']:.4g} cm⁻³",
            f"【反应性】ρ_Sm={eq['results']['rho_sm_pcm']:.2f} pcm（约 0.007，教材 p.108）",
            "【要点】Sm 为稳定核素：停堆后 Pm 全部衰变为 Sm，Sm 浓度只增不减。",
            "【依据】教材 第6章 6.2.2 p.107-109（式6-19~6-25）",
        ]
        payload = {"result": {"mode": "samarium", "flux": float(flux),
                              "t_irr_h": t_irr, "t_down_h": t_down,
                              "rho_sm_eq_pcm": eq["results"]["rho_sm_pcm"],
                              "N_Pm_eq": eq["results"]["N_Pm_eq"],
                              "N_Sm_eq": eq["results"]["N_Sm_eq"]}}
    else:
        summary = (f"氙中毒：平衡 ρ_Xe={eq['results']['rho_xe_pcm']:.0f} pcm；停堆后最大碘坑 "
                   f"{res['results']['max_pit_time_h']:.3g} h，坑深 "
                   f"{res['results']['iodine_pit_depth_pcm']:.0f} pcm")
        detail_lines = [
            f"【模型】I-135→Xe-135 链，恒定通量启动解 + 停堆解析解（教材 6.2.1 p.101-107）",
            f"【输入】Φ={float(flux):g} cm⁻²s⁻¹；t_irr={t_irr:.6g} h；t_down={t_down:.6g} h；"
            f"停堆前剩余反应性 ρ_ex0={rho_ex0_pcm:g} pcm",
            f"【平衡】N_I={eq['results']['N_I_eq']:.4g} cm⁻³，N_Xe={eq['results']['N_Xe_eq']:.4g} cm⁻³",
            f"【反应性】ρ_Xe(平衡)={eq['results']['rho_xe_pcm']:.2f} pcm（教材 p.105 约 0.04~0.05）",
            f"【碘坑】t_max={res['results']['max_pit_time_h']:.3g} h，"
            f"坑深 Δρ={res['results']['iodine_pit_depth_pcm']:.1f} pcm",
            f"【过零点】ρ_ex=0 时刻（停堆后 h）：{[round(z, 2) for z in res['results']['rho_ex_zeros_h']]}",
            "【依据】教材 第6章 6.2.1 p.101-107（式6-6~6-18）",
        ]
        payload = {"result": {"mode": "xenon", "flux": float(flux),
                              "t_irr_h": t_irr, "t_down_h": t_down,
                              "rho_xe_eq_pcm": eq["results"]["rho_xe_pcm"],
                              "N_I_eq": eq["results"]["N_I_eq"],
                              "N_Xe_eq": eq["results"]["N_Xe_eq"],
                              "iodine_pit_depth_pcm": res["results"]["iodine_pit_depth_pcm"],
                              "max_pit_time_h": res["results"]["max_pit_time_h"]}}

    return ToolOutcome(ok=True, summary=summary, detail="\n".join(detail_lines),
                       artifact_type="plot", artifact_data=artifact, payload=payload)


def _svg(series, x_label, y_label, title) -> str:
    try:
        from app.plots import svg as svgmod
        return svgmod.line_chart(series, x_label=x_label, y_label=y_label, title=title,
                                 width=820, height=440,
                                 note="依据教材 6.2 节：恒定通量解析解")
    except Exception:
        return ""


TOOL = ToolSpec(
    name="poison_calc",
    label="氙钐中毒 · {query}",
    description=(
        "裂变产物中毒计算：I-135→Xe-135 与 Pm-149→Sm-149 链的平衡浓度、"
        "反应性当量、停堆后碘坑（t_max、坑深、强迫停堆/允许停堆时间）与 Sm 积累。"
        "学生问“碘坑/氙毒/钐中毒/停堆后何时可再启动”时调用；可只传 query，"
        "自动解析通量、运行天数、停堆小时数。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "学生原问题文本；缺省结构化参数时从中解析"},
            "mode": {"type": "string", "enum": ["xenon", "samarium"], "description": "氙或钐"},
            "flux": {"type": "number", "description": "中子通量密度 Φ（cm⁻²s⁻¹）"},
            "t_irr": {"type": "number", "description": "照射/运行时间（配合 time_unit）"},
            "t_down": {"type": "number", "description": "停堆时间（配合 time_unit）"},
            "time_unit": {"type": "string", "description": "时间单位，默认 h"},
            "rho_ex0_pcm": {"type": "number", "description": "停堆前剩余反应性（pcm），用于算允许停堆时间"},
        },
        "required": [],
    },
    run=poison_calc,
)


__all__ = ["poison_calc", "TOOL"]
