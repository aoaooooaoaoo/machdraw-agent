"""工具 spectrum_plot：能谱/分布曲线与群平均截面（调用 app.domain.spectrum）。

支持只传 query：自动识别 Watt/裂变谱、Maxwell/热谱、1/E/费米谱、压水堆合成谱，
解析温度 T=535.5K、能量范围与群边界。spec 第4.3 节：name=spectrum_plot，画布 ``plot``。
"""
from __future__ import annotations

import importlib
import math
import re

from .base import ToolContext, ToolOutcome
from .spec import ToolSpec

_NUM = r"([-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)"
_EV_U = r"(eV|keV|MeV)"


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


def _to_ev(value: float, unit: str) -> float:
    u = (unit or "eV").lower()
    if u == "kev":
        return value * 1e3
    if u == "mev":
        return value * 1e6
    return value


def _detect_model(q: str, explicit: str) -> str:
    m = (explicit or "").strip().lower()
    if m:
        return m
    if re.search(r"压水堆|合成|PWR|完整谱", q, re.I):
        return "pwr"
    if re.search(r"麦克斯韦|Maxwell|热谱|热中子谱", q, re.I):
        return "maxwell"
    if re.search(r"1/E|1／E|费米|Fermi", q, re.I):
        return "fermi"
    if re.search(r"瓦特|Watt|裂变谱|裂变中子谱", q, re.I):
        return "watt"
    return ""


def _fmt(v, nd=4) -> str:
    if v is None:
        return "—"
    if isinstance(v, float) and (abs(v) >= 1e4 or (v != 0 and abs(v) < 1e-3)):
        return f"{v:.{nd}e}"
    return f"{v:.{nd}g}"


def spectrum_plot(ctx: ToolContext, query: str = "", model: str = "",
                  e_min_ev: float | None = None, e_max_ev: float | None = None,
                  T_k: float | None = None, n_points: int = 320,
                  group_bounds: list | None = None, **_) -> ToolOutcome:
    q = query or ""
    try:
        sp = importlib.import_module("app.domain.spectrum")
    except ImportError:
        return ToolOutcome(ok=False, summary="能谱引擎尚未就绪",
                           detail="app/domain/spectrum.py 缺失")

    model = _detect_model(q, model)
    if not model:
        return ToolOutcome(
            ok=False, summary="请说明要画哪种能谱",
            detail="可选：压水堆合成谱 / Watt 裂变谱 / Maxwell 热谱 / 1/E 费米谱。"
                   "示例：画出压水堆中子能谱（T=535.5K，从 1e-4 eV 到 2e7 eV）；"
                   "热谱最可几能量是多少（T=293.6K）。",
        )

    if T_k is None:
        val, u = _grab(q, [r"(?:T|温度)\s*[=:：]?\s*" + _NUM + r"\s*(K|℃|C)?"])
        if val is not None:
            T_k = val + 273.15 if (u or "").upper() in ("℃", "C") else val
    if T_k is None:
        T_k = sp.T_0253
    if T_k <= 0:
        return ToolOutcome(ok=False, summary="温度必须为正", detail=f"收到 T={T_k} K")

    # 群平均截面模式（补充2.1：1/v 截面 + 1/E 谱）
    if group_bounds or re.search(r"群平均|群常数", q, re.I):
        if group_bounds is None:
            vals = re.findall(_NUM + r"\s*" + _EV_U, q)
            if len(vals) >= 2:
                group_bounds = [_to_ev(float(v), u) for v, u in vals[:2]]
        if not group_bounds or len(group_bounds) < 2:
            return ToolOutcome(
                ok=False, summary="群平均截面需要能群边界",
                detail="示例：求 0.0253 eV~1 eV 群的 1/v 吸收截面群平均值（σ=C/√E，1/E 谱）。",
            )
        bounds = [float(x) for x in group_bounds]
        C = 1.0
        m = re.search(r"(?:C|σ0?)\s*[=:：]?\s*" + _NUM, q)
        if m:
            C = float(m.group(1))

        def sigma_1v(E: float) -> float:
            return C / math.sqrt(E)

        try:
            r = sp.group_average(sigma_1v, bounds, weight="fermi")
        except ValueError as exc:
            return ToolOutcome(ok=False, summary="群平均计算失败", detail=str(exc))
        sig = r["results"]["sigma_g"]
        analytic = 2.0 * C * (1.0 / math.sqrt(bounds[0]) - 1.0 / math.sqrt(bounds[1])) / math.log(bounds[1] / bounds[0])
        artifact = {
            "kind": "distribution",
            "title": "群平均截面（1/v 截面 + 1/E 谱）",
            "x_label": "E / eV（对数）",
            "y_label": "φ(E)·σ(E)（相对）",
            "series": [{"name": "σ(E)φ(E)",
                        "points": [[10 ** (math.log10(bounds[0]) + (math.log10(bounds[1]) - math.log10(bounds[0])) * k / 119),
                                    C / math.sqrt(10 ** (math.log10(bounds[0]) + (math.log10(bounds[1]) - math.log10(bounds[0])) * k / 119)) /
                                    (10 ** (math.log10(bounds[0]) + (math.log10(bounds[1]) - math.log10(bounds[0])) * k / 119))]
                                   for k in range(120)]}],
            "markers": [],
            "results": [
                {"name": "群平均截面 σ_g", "value": sig, "unit": "（与 C 同单位）", "note": "数值积分"},
                {"name": "解析值", "value": analytic, "unit": "（与 C 同单位）", "note": "补充2.1 解析式"},
            ],
            "note": "σ_g=∫σφdE/∫φdE；σ∝1/√E、φ∝1/E，解析式为 2C(1/√E₁−1/√E₂)/ln(E₂/E₁)。",
            "refs": r["refs"],
            "svg": "",
        }
        return ToolOutcome(
            ok=True,
            summary=f"[{bounds[0]:g}, {bounds[1]:g}] eV 群平均截面 σ_g={sig:.6g}（解析 {analytic:.6g}）",
            detail="\n".join(r["steps"]), artifact_type="plot",
            artifact_data=artifact,
            payload={"result": {"sigma_g": sig, "analytic": analytic, "bounds_ev": bounds}},
        )

    # 能谱曲线模式：按模型设默认范围
    defaults = {
        "watt": (1e5, 2e7),
        "maxwell": (1e-3, 1.0),
        "fermi": (0.1, 1e7),
        "pwr": (1e-4, 2e7),
    }
    lo_d, hi_d = defaults.get(model, (1e-3, 2e7))
    if e_min_ev is None:
        val, u = _grab(q, [r"(?:E_?min|从)\s*[=:：]?\s*" + _NUM + r"\s*" + _EV_U])
        e_min_ev = _to_ev(val, u) if val is not None else lo_d
    if e_max_ev is None:
        val, u = _grab(q, [r"(?:E_?max|到)\s*[=:：]?\s*" + _NUM + r"\s*" + _EV_U])
        e_max_ev = _to_ev(val, u) if val is not None else hi_d
    if e_max_ev <= e_min_ev:
        e_max_ev = hi_d
    n_points = max(40, min(int(n_points or 320), 1200))

    try:
        r = sp.spectrum_curve(model=model, e_min_ev=float(e_min_ev),
                              e_max_ev=float(e_max_ev), n_points=n_points, T_k=float(T_k))
    except ValueError as exc:
        return ToolOutcome(ok=False, summary="能谱计算失败", detail=str(exc))

    peak = r["results"]["peak_energy_ev"]
    mean_mev = r["results"]["mean_energy_mev"]
    chi_or_phi = "χ(E)" if model == "watt" else "φ(E)"
    refs = r["refs"]
    if model == "watt":
        note = "Watt 裂变谱：平均值≈2 MeV（教材 p.79）；纵轴为每 eV 的归一化谱值。"
    elif model == "maxwell":
        note = f"Maxwell 热谱：峰值在 E=kT={sp.K_B_EV * T_k:.4g} eV；T={T_k:g} K。"
    elif model == "fermi":
        note = "Fermi 1/E 慢化谱：φ(E)∝1/E（教材 5.2 p.80-82）。"
    else:
        note = "压水堆合成谱：热 Maxwell + 1/E + Watt 分段拼接后归一化（教材 5.4 p.88-90）。"
    artifact = {
        "kind": "spectrum",
        "title": {"watt": "Watt 裂变中子能谱", "maxwell": "Maxwell 热中子能谱",
                  "fermi": "Fermi 1/E 慢化谱", "pwr": "压水堆合成中子能谱"}[model],
        "x_label": "E / eV（对数轴）",
        "y_label": f"{chi_or_phi} / eV⁻¹",
        "series": r["series"],
        "markers": [{"x": peak, "y": r["results"]["peak_value"], "label": "峰值"}],
        "results": [
            {"name": "峰值能量", "value": peak, "unit": "eV", "note": ""},
            {"name": "平均能量（数值）", "value": round(mean_mev, 4), "unit": "MeV", "note": ""},
            {"name": "kT", "value": round(sp.K_B_EV * T_k, 6), "unit": "eV", "note": f"T={T_k:g} K"},
        ],
        "note": note,
        "refs": refs,
        "svg": _svg(r["series"], "E / eV", f"{chi_or_phi} / eV⁻¹",
                    artifact_title(model), model),
    }
    detail_lines = [
        f"【模型】{model}；T={T_k:g} K（kT={sp.K_B_EV * T_k:.4g} eV）",
        f"【能量范围】{e_min_ev:g} ~ {e_max_ev:g} eV，对数网格 {n_points} 点",
        f"【峰值】E_peak={peak:.4g} eV",
        f"【平均能量】{mean_mev:.4g} MeV",
        f"【依据】{refs[0]}",
    ]
    return ToolOutcome(
        ok=True,
        summary=f"{artifact['title']}：峰值 E={_fmt(peak)} eV，平均能量 {mean_mev:.4g} MeV",
        detail="\n".join(detail_lines), artifact_type="plot",
        artifact_data=artifact,
        payload={"result": {"model": model, "peak_energy_ev": peak,
                            "mean_energy_mev": mean_mev, "T_k": float(T_k),
                            "e_min_ev": float(e_min_ev), "e_max_ev": float(e_max_ev)}},
    )


def artifact_title(model: str) -> str:
    return {"watt": "Watt 裂变中子能谱", "maxwell": "Maxwell 热中子能谱",
            "fermi": "Fermi 1/E 慢化谱", "pwr": "压水堆合成中子能谱"}.get(model, "中子能谱")


def _svg(series, x_label, y_label, title, model) -> str:
    try:
        from app.plots import svg as svgmod
        return svgmod.line_chart(series, x_label=x_label, y_label=y_label, title=title,
                                 x_log=True, y_log=(model in ("pwr", "fermi", "maxwell")),
                                 width=860, height=460,
                                 note="依据教材 第5章：裂变谱/慢化谱/热谱")
    except Exception:
        return ""


TOOL = ToolSpec(
    name="spectrum_plot",
    label="能谱曲线 · {query}",
    description=(
        "中子能谱/分布曲线：Watt 裂变谱、Maxwell 热谱（含温度）、1/E 费米慢化谱、"
        "压水堆合成谱；并可按能群边界数值积分求群平均截面（1/v 截面+1/E 谱有解析对照）。"
        "学生问“画出中子能谱/裂变谱/热谱/群平均截面”时调用；可只传 query，"
        "自动识别谱型、温度、能量范围与群边界。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "学生原问题文本；缺省结构化参数时从中解析"},
            "model": {"type": "string", "enum": ["watt", "maxwell", "fermi", "pwr"],
                      "description": "谱型：裂变/热/1E/压水堆合成"},
            "e_min_ev": {"type": "number", "description": "能量下限（eV）"},
            "e_max_ev": {"type": "number", "description": "能量上限（eV）"},
            "T_k": {"type": "number", "description": "温度（K），默认 293.6 K"},
            "n_points": {"type": "integer", "description": "曲线点数，默认 320"},
            "group_bounds": {"type": "array", "description": "群边界（eV），如 [0.0253, 1.0]"},
        },
        "required": [],
    },
    run=spectrum_plot,
)


__all__ = ["spectrum_plot", "TOOL"]
