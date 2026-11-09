"""工具 reactivity_calc：反应性换算、温度系数、功率亏损（调用 app.domain.reactivity）。

支持只传 query：自动解析 k=0.998、ρ=200pcm、+0.2$、T1=280/T2=300、
α_P=-0.020%/1%FP 等。spec 第4.3 节：name=reactivity_calc，画布 ``calc``。
"""
from __future__ import annotations

import importlib
import re

from .base import ToolContext, ToolOutcome
from .spec import ToolSpec

_NUM = r"([-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)"
_UNIT = r"(pcm|mk|%|dk/k|delta_k/k|\$|元)"


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


def _fmt(v, nd=6) -> str:
    if v is None:
        return "—"
    if isinstance(v, float) and (abs(v) >= 1e5 or (v != 0 and abs(v) < 1e-3)):
        return f"{v:.4e}"
    return f"{v:.{nd}g}"


def reactivity_calc(ctx: ToolContext, query: str = "", k: float | None = None,
                    value: float | None = None, unit: str = "pcm",
                    to_unit: str = "", T1: float | None = None,
                    T2: float | None = None, rho1: float | None = None,
                    rho2: float | None = None, P1: float | None = None,
                    P2: float | None = None,
                    power_coefficient: float | None = None,
                    terms: list | None = None, beta: float | None = None,
                    **_) -> ToolOutcome:
    q = query or ""
    try:
        rx = importlib.import_module("app.domain.reactivity")
    except ImportError:
        return ToolOutcome(ok=False, summary="反应性引擎尚未就绪",
                           detail="app/domain/reactivity.py 缺失")
    beta = rx.BETA_U235 if beta is None else float(beta)

    # ---------------- 解析
    if k is None:
        val, _u = _grab(q, [r"\bk\s*_?\s*(?:eff)?\s*[=:：]\s*" + _NUM,
                            r"有效增殖因子?\s*[=:：]?\s*" + _NUM,
                            r"有效增殖系数?\s*[=:：]?\s*" + _NUM])
        k = val
    if value is None:
        val, u = _grab(q, [r"(?:ρ|rho|反应性)\s*[=:：]?\s*" + _NUM + r"\s*" + _UNIT,
                           r"([-+]?\d+(?:\.\d+)?)\s*" + _UNIT])
        if val is not None:
            value, unit = val, (u or unit)
    if T1 is None:
        val, _u = _grab(q, [r"T1\s*[=:：]?\s*" + _NUM, r"初温(?:度)?\s*[=:：]?\s*" + _NUM])
        T1 = val
    if T2 is None:
        val, _u = _grab(q, [r"T2\s*[=:：]?\s*" + _NUM, r"末温(?:度)?\s*[=:：]?\s*" + _NUM])
        T2 = val
    if rho1 is None:
        val, _u = _grab(q, [r"ρ1\s*[=:：]?\s*" + _NUM, r"反应性1\s*[=:：]?\s*" + _NUM])
        rho1 = val
    if rho2 is None:
        val, _u = _grab(q, [r"ρ2\s*[=:：]?\s*" + _NUM, r"反应性2\s*[=:：]?\s*" + _NUM])
        rho2 = val
    if P1 is None:
        val, _u = _grab(q, [r"P1\s*[=:：]?\s*" + _NUM, r"初功率\s*[=:：]?\s*" + _NUM])
        P1 = val
    if P2 is None:
        val, _u = _grab(q, [r"P2\s*[=:：]?\s*" + _NUM, r"末功率\s*[=:：]?\s*" + _NUM])
        P2 = val
    if power_coefficient is None:
        val, _u = _grab(q, [r"(?:功率系数|α_P|功率亏损系数)\s*[=:：]?\s*" + _NUM])
        if val is not None:
            power_coefficient = val
    if terms is None:
        # 解析“控制棒=-6.918%、氙=+2.675%”这类叠加项
        found = re.findall(r"([\u4e00-\u9fa5A-Za-z]+)\s*[=:：]\s*" + _NUM + r"\s*(" + _UNIT[1:-1] + ")",
                           q)
        if found:
            terms = [{"name": n, "value": float(v), "unit": u} for n, v, u in found]

    # ---------------- 分支
    try:
        if terms:
            r = rx.combine_terms(terms)
            title = "反应性贡献代数叠加 / 停堆深度"
            inputs = [{"name": t.get("name", "项"), "value": t.get("value"),
                       "unit": str(t.get("unit", ""))} for t in terms]
            rows = [
                {"name": "总反应性", "value": r["results"]["rho_pcm"], "unit": "pcm",
                 "note": f"{r['results']['rho_percent']:+.4g}% Δk/k"},
                {"name": "判定", "value": r["results"]["verdict"], "unit": "", "note": ""},
            ]
            verdict = {"level": r["results"]["verdict"],
                       "note": f"ΣΔρ={r['results']['rho_percent']:+.4g}% Δk/k"}
            steps = r["steps"]
            refs = r["refs"]
            summary = (f"反应性叠加 ΣΔρ={r['results']['rho_percent']:+.4g}% Δk/k"
                       f"（{r['results']['rho_pcm']:+.0f} pcm）→ {r['results']['verdict']}")
            payload = {"result": r["results"]}
        elif T1 is not None and T2 is not None and (rho1 is not None or rho2 is not None or value is not None):
            if rho1 is None or rho2 is None:
                raise ValueError("温度系数需要 ρ1 与 ρ2 两个反应性值")
            r = rx.temperature_coefficient(rho1, rho2, T1, T2)
            title = "反应性温度系数"
            inputs = [
                {"name": "T1", "value": T1, "unit": "K"}, {"name": "T2", "value": T2, "unit": "K"},
                {"name": "ρ1", "value": rho1, "unit": ""}, {"name": "ρ2", "value": rho2, "unit": ""},
            ]
            rows = [
                {"name": "α_T", "value": r["results"]["alpha_pcm_per_K"], "unit": "pcm/K",
                 "note": ""},
                {"name": "α_T", "value": r["results"]["alpha_dk_per_K"], "unit": "Δk·k⁻¹/K",
                 "note": r["results"]["sign"]},
            ]
            verdict = {"level": "温度系数符号判定",
                       "note": r["results"]["sign"]}
            steps = r["steps"]
            refs = r["refs"]
            summary = (f"温度系数 α_T={r['results']['alpha_pcm_per_K']:+.4g} pcm/K"
                       f"（{r['results']['sign']}）")
            payload = {"result": r["results"]}
        elif P1 is not None and P2 is not None and rho1 is not None and rho2 is not None:
            r = rx.power_coefficient(rho1, rho2, P1, P2)
            title = "反应性功率系数"
            inputs = [{"name": n, "value": v, "unit": ""} for n, v in
                      (("P1/%FP", P1), ("P2/%FP", P2), ("ρ1", rho1), ("ρ2", rho2))]
            rows = [
                {"name": "α_P", "value": r["results"]["alpha_percent_per_percentFP"], "unit": "%/%FP", "note": ""},
                {"name": "α_P", "value": r["results"]["alpha_pcm_per_percentFP"], "unit": "pcm/%FP", "note": ""},
            ]
            verdict = {"level": "功率系数", "note": "教材 7.2 p.119"}
            steps = r["steps"]
            refs = r["refs"]
            summary = f"功率系数 α_P={r['results']['alpha_percent_per_percentFP']:+.4g}%/1%FP"
            payload = {"result": r["results"]}
        elif power_coefficient is not None and P1 is not None and P2 is not None:
            r = rx.power_defect(power_coefficient, P1, P2)
            title = "功率亏损计算"
            inputs = [{"name": "总功率系数", "value": power_coefficient, "unit": "%/%FP"},
                      {"name": "P1", "value": P1, "unit": "%FP"},
                      {"name": "P2", "value": P2, "unit": "%FP"}]
            rows = [
                {"name": "功率亏损", "value": r["results"]["delta_rho_percent"], "unit": "% Δk/k", "note": ""},
                {"name": "功率亏损", "value": r["results"]["delta_rho_pcm"], "unit": "pcm", "note": ""},
            ]
            verdict = {"level": "功率亏损", "note": "习题 v4.0 题7.8：-0.020%/1%FP×(30-100)=+1.4%"}
            steps = r["steps"]
            refs = r["refs"]
            summary = (f"功率亏损 Δρ={r['results']['delta_rho_percent']:+.4g}% Δk/k"
                       f"（{r['results']['delta_rho_pcm']:+.0f} pcm）")
            payload = {"result": r["results"]}
        elif k is not None:
            r = rx.rho_from_k(k)
            title = "由 k_eff 求反应性"
            inputs = [{"name": "k_eff", "value": k, "unit": ""}]
            rows = [
                {"name": "ρ", "value": r["results"]["rho_pcm"], "unit": "pcm", "note": "Δk/k×10⁵"},
                {"name": "ρ", "value": r["results"]["rho_percent"], "unit": "% Δk/k", "note": ""},
                {"name": "ρ", "value": r["results"]["rho_mk"], "unit": "mk", "note": ""},
                {"name": "ρ", "value": r["results"]["rho_dollar"], "unit": "$", "note": f"β={beta:g}"},
            ]
            verdict = {"level": "超临界" if r["results"]["rho"] > 0 else ("临界" if r["results"]["rho"] == 0 else "次临界"),
                       "note": f"ρ=(k−1)/k={r['results']['rho']:.6g}"}
            steps = r["steps"]
            refs = r["refs"]
            summary = (f"k_eff={k:g} → ρ={r['results']['rho_pcm']:+.2f} pcm"
                       f"（{r['results']['rho_dollar']:+.4g} $）")
            payload = {"result": r["results"]}
        elif value is not None:
            r = rx.unit_convert(value, unit, to_unit or "dk/k", beta)
            title = "反应性单位换算"
            inputs = [{"name": "输入值", "value": value, "unit": unit}]
            rows = [
                {"name": "ρ", "value": r["results"]["rho_pcm"], "unit": "pcm", "note": ""},
                {"name": "ρ", "value": r["results"]["rho"], "unit": "Δk/k", "note": ""},
                {"name": "ρ", "value": r["results"]["rho_dollar"], "unit": "$", "note": f"β={beta:g}"},
                {"name": "换算结果", "value": r["results"]["converted"], "unit": to_unit or "Δk/k",
                 "note": ""},
            ]
            verdict = {"level": "单位换算", "note": "1 pcm=10⁻⁵；1 mk=10⁻³；1$=β"}
            steps = r["steps"]
            refs = r["refs"]
            summary = (f"{value:g}{unit} = {r['results']['rho_pcm']:+.4g} pcm = "
                       f"{r['results']['rho_dollar']:+.4g} $")
            payload = {"result": r["results"]}
        else:
            return ToolOutcome(
                ok=False, summary="缺少反应性换算所需的输入",
                detail="示例：k_eff=0.998；ρ=200pcm；+0.2$；"
                       "温度系数：T1=280, T2=300, ρ1=0, ρ2=-0.001；"
                       "功率亏损：功率系数=-0.020, P1=100, P2=30。",
            )
    except ValueError as exc:
        return ToolOutcome(ok=False, summary="反应性计算失败", detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        return ToolOutcome(ok=False, summary=f"反应性计算失败：{type(exc).__name__}", detail=str(exc))

    artifact = {
        "title": title,
        "inputs": [{"name": x["name"], "value": x["value"], "unit": x.get("unit", "")} for x in inputs],
        "formulas": [{"step": s_, "note": n_} for s_, n_ in _formulas(title)],
        "results": rows,
        "verdict": verdict,
        "refs": refs,
        "note": verdict["note"],
        "svg": "",
    }
    detail_lines = [f"【输入】{x['name']}={x['value']:g}{x.get('unit', '')}" for x in inputs]
    detail_lines += [f"【步骤】{s_}" for s_ in steps[:5]]
    detail_lines.append(f"【依据】{'；'.join(refs[:2])}")
    return ToolOutcome(ok=True, summary=summary, detail="\n".join(detail_lines[:15]),
                       artifact_type="calc", artifact_data=artifact, payload=payload)


def _formulas(title: str) -> list[tuple[str, str]]:
    if "温度" in title:
        return [("α_T = Δρ/ΔT", "教材 7.1 p.116")]
    if "功率" in title:
        return [("α_P = Δρ/ΔP；Δρ=∫α_P dP", "教材 7.2 p.119")]
    if "k_eff" in title:
        return [("ρ=(k_eff−1)/k_eff；k_eff=1/(1−ρ)", "教材 3.1.1 p.33")]
    if "叠加" in title:
        return [("ρ_total=Σρ_i", "反应性代数叠加（小扰动）")]
    return [("1 pcm=10⁻⁵；1 mk=10⁻³；1$=β", "教材 8.2 p.130；题3.4")]


TOOL = ToolSpec(
    name="reactivity_calc",
    label="反应性换算 · {query}",
    description=(
        "反应性换算与系数：k_eff↔ρ、pcm/mk/%/Δk·k⁻¹/$ 互转、温度系数"
        "（燃料/慢化剂）、功率系数与功率亏损、多项反应性贡献代数叠加（停堆深度）。"
        "学生问“k=0.998 的反应性是多少/多少 pcm/温度系数/功率亏损”时调用。"
        "可只传 query，自动解析 k=0.998、ρ=200pcm、+0.2$、T1/T2、P1/P2 等。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "学生原问题文本；缺省结构化参数时从中解析"},
            "k": {"type": "number", "description": "有效增殖系数 k_eff"},
            "value": {"type": "number", "description": "反应性数值（配合 unit）"},
            "unit": {"type": "string", "enum": ["pcm", "mk", "%", "dk/k", "$"], "description": "输入单位"},
            "to_unit": {"type": "string", "description": "目标单位（可选）"},
            "T1": {"type": "number", "description": "初温度（K）"},
            "T2": {"type": "number", "description": "末温度（K）"},
            "rho1": {"type": "number", "description": "初反应性（Δk/k）"},
            "rho2": {"type": "number", "description": "末反应性（Δk/k）"},
            "P1": {"type": "number", "description": "初功率（%FP）"},
            "P2": {"type": "number", "description": "末功率（%FP）"},
            "power_coefficient": {"type": "number", "description": "总功率系数（%/1%FP）"},
            "terms": {"type": "array", "description": "反应性叠加项：[{name,value,unit}]",
                      "items": {"type": "object"}},
            "beta": {"type": "number", "description": "β，默认 0.0065"},
        },
        "required": [],
    },
    run=reactivity_calc,
)


__all__ = ["reactivity_calc", "TOOL"]
