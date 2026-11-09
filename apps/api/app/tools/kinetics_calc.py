"""工具 kinetics_calc：点堆动力学（倒时方程、周期、瞬发跳跃、阶跃响应）。

支持只传 ``query``：自动解析 ρ=200pcm、+0.2$、β=0.0065、l=1e-4s、t=100s 等。
spec 第4.3 节：name=kinetics_calc，画布 ``plot``。
"""
from __future__ import annotations

import importlib
import math
import re

from .base import ToolContext, ToolOutcome
from .spec import ToolSpec

_NUM = r"([-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)"


def _grab(text: str, patterns: list[str], default=None):
    for p in patterns:
        m = re.search(p, text, re.I)
        if m:
            try:
                return float(m.group(1)), (m.group(2) if m.lastindex and m.lastindex >= 2 and m.group(2) else "")
            except (TypeError, ValueError, IndexError):
                continue
    return default, ""


def _rho_from_query(q: str):
    for p, unit in (
        (r"(?:ρ|rho|反应性)\s*[=:：]?\s*" + _NUM + r"\s*(pcm|mk|%|dk/k|delta_k/k|\$|元)", None),
        (r"(?:ρ|rho|反应性)\s*[=:：]\s*" + _NUM, None),
        (r"([-+]?\d+(?:\.\d+)?)\s*(pcm)\b", None),
        (r"([-+]?\d+(?:\.\d+)?)\s*(mk)\b", None),
        (r"([-+]?\d+(?:\.\d+)?)\s*(\$|元|dollar|美元)", None),
    ):
        m = re.search(p, q, re.I)
        if m:
            try:
                val = float(m.group(1))
            except (TypeError, ValueError):
                continue
            u = (m.group(2) if m.lastindex and m.lastindex >= 2 else "") or unit or "dk/k"
            return val, u
    return None, ""


def _fmt(v, nd=6) -> str:
    if v is None:
        return "—"
    if isinstance(v, float) and (abs(v) >= 1e5 or (v != 0 and abs(v) < 1e-3)):
        return f"{v:.4e}"
    return f"{v:.{nd}g}" if isinstance(v, float) else str(v)


def _finite(v):
    """把 inf/nan 换成 None，保证 payload 可 JSON 序列化。"""
    if isinstance(v, float) and not math.isfinite(v):
        return None
    return v


def kinetics_calc(ctx: ToolContext, query: str = "", rho: float | None = None,
                  rho_unit: str = "dk/k", beta: float | None = None,
                  l: float | None = None, k_eff: float | None = None,
                  ratio: float | None = None, dt: float | None = None,
                  t_end: float | None = None, **_) -> ToolOutcome:
    q = query or ""
    try:
        kin = importlib.import_module("app.domain.kinetics")
    except ImportError:
        return ToolOutcome(ok=False, summary="动力学引擎尚未就绪",
                           detail="app/domain/kinetics.py 缺失")

    # ---------------- 解析
    if rho is None:
        val, u = _rho_from_query(q)
        if val is not None:
            rho, rho_unit = val, (u or rho_unit)
    if rho is None:
        val, _u = _grab(q, [r"k\s*_?\s*eff\s*[=:：]\s*" + _NUM,
                            r"\bk\s*[=:：]\s*" + _NUM])
        if val is not None:
            k_eff = val
    if k_eff is not None and rho is None:
        if k_eff <= 0:
            return ToolOutcome(ok=False, summary="k_eff 必须为正", detail=f"收到 k_eff={k_eff}")
        rho = (k_eff - 1.0) / k_eff
        rho_unit = "dk/k"
    if beta is None:
        val, _u = _grab(q, [r"(?:β|beta)\s*[=:：]?\s*" + _NUM])
        beta = val
    beta = kin.BETA_U235 if beta is None else float(beta)
    if l is None:
        val, u = _grab(q, [r"(?:l|Λ|lambda|中子寿命|代时间)\s*[=:：]?\s*" + _NUM + r"\s*(ms|s)?"])
        if val is not None:
            l = val * (1e-3 if (u or "") == "ms" else 1.0)
    if l is None:
        val, u = _grab(q, [r"\bT\s*[=:：]\s*" + _NUM + r"\s*(ms|s)"])
        if val is not None and val <= 0.05:
            l = val * (1e-3 if (u or "") == "ms" else 1.0)
    if l is None:
        l = kin.PWR_NEUTRON_LIFETIME
    if ratio is None:
        m = re.search(r"(?:n2\s*/\s*n1|n₂\s*/\s*n₁|功率比)\s*[=:：]?\s*" + _NUM, q, re.I)
        if m:
            ratio = float(m.group(1))
    if dt is None:
        val, u = _grab(q, [r"(?:Δt|dt|间隔|时间间隔)\s*[=:：]?\s*" + _NUM + r"\s*(ms|s|min|分钟)"])
        if val is not None:
            dt = val * {"ms": 1e-3, "min": 60.0, "分钟": 60.0}.get(u or "s", 1.0)
    if t_end is None:
        val, u = _grab(q, [r"(?:t_end|t|观察时间|运行时间)\s*[=:：]\s*" + _NUM + r"\s*(ms|s|min|分钟)"])
        if val is not None:
            t_end = val * {"ms": 1e-3, "min": 60.0, "分钟": 60.0}.get(u or "s", 1.0)

    # 模式 A：由功率比求周期（题8.5）
    if ratio is not None and rho is None:
        dt = 120.0 if dt is None else float(dt)
        try:
            res = kin.period_from_ratio(ratio, dt)
        except ValueError as exc:
            return ToolOutcome(ok=False, summary="周期计算失败", detail=str(exc))
        T = res["results"]["T_s"]
        artifact = {
            "kind": "curve",
            "title": "功率指数增长与反应堆周期",
            "x_label": "t / s",
            "y_label": "n / n0",
            "series": [{"name": "指数增长", "points": [[0.0, 1.0], [dt, float(ratio)]]}],
            "markers": [{"x": 0.0, "y": 1.0, "label": "起点"},
                        {"x": dt, "y": float(ratio), "label": f"n₂/n₁={ratio:g}"}],
            "results": [
                {"name": "反应堆周期 T", "value": round(T, 4), "unit": "s", "note": "T=Δt/ln(n₂/n₁)"},
                {"name": "时间间隔 Δt", "value": round(dt, 4), "unit": "s", "note": ""},
            ],
            "note": "低功率启动阶段中子密度按 n(t)=n₀e^{t/T} 增长。",
            "refs": res["refs"],
            "svg": "",
        }
        return ToolOutcome(ok=True, summary=f"由 n₂/n₁={ratio:g}、Δt={dt:g} s 得反应堆周期 T={T:.4g} s",
                           detail="\n".join(res["steps"]), artifact_type="plot",
                           artifact_data=artifact, payload={"result": res["results"]})

    if rho is None:
        return ToolOutcome(
            ok=False, summary="缺少反应性 ρ",
            detail="请给出反应性，例如：ρ=200pcm、+0.2$、ρ=0.001；或给 k_eff=1.001。"
                   "也可给 n2/n1=1.5、Δt=120s 求周期。",
        )
    try:
        rho_value = kin.rho_in(float(rho), rho_unit, beta)
    except ValueError as exc:
        return ToolOutcome(ok=False, summary="反应性单位无法识别", detail=str(exc))

    try:
        roots = kin.inhour_roots(rho_value, float(l))
        period = kin.period(rho_value, float(l))
        jump = kin.prompt_jump_ratio(rho_value, beta)
        crit = kin.prompt_critical_check(rho_value, beta)
    except ValueError as exc:
        return ToolOutcome(ok=False, summary="点堆计算失败", detail=str(exc))

    s = roots["results"]["dominant"]
    T = period["results"]["T_s"]
    if t_end is None:
        if T > 0 and math.isfinite(T):
            t_end = max(1.0, min(600.0, 10.0 * T))
        else:
            t_end = 100.0
    t_end = float(t_end)
    dt = float(dt) if dt else max(t_end / 2000.0, 1e-6)
    if dt <= 0:
        dt = max(t_end / 2000.0, 1e-6)
    try:
        resp = kin.response_curve(rho_value, t_end, dt, float(l), n0=1.0, max_points=260)
    except ValueError as exc:
        return ToolOutcome(ok=False, summary="响应曲线积分失败", detail=str(exc))

    series = [{"name": f"n/n₀（ρ={rho_value * 1e5:.4g} pcm）",
               "points": resp["series"][0]["points"]}]
    jump_ratio = jump["results"]["jump_ratio"]
    artifact = {
        "kind": "curve",
        "title": "阶跃反应性下的中子密度响应（点堆，六组缓发中子）",
        "x_label": "t / s",
        "y_label": "n / n₀",
        "series": series,
        "markers": [{"x": 0.0, "y": 1.0, "label": "阶跃引入"}],
        "results": [
            {"name": "反应性 ρ", "value": round(rho_value * 1e5, 4), "unit": "pcm",
             "note": f"{rho_value / beta:.4g} $"},
            {"name": "主导根 s₁", "value": round(s, 8), "unit": "s⁻¹", "note": "倒时方程"},
            {"name": "反应堆周期 T", "value": (round(T, 4) if math.isfinite(T) else None),
             "unit": "s", "note": "T=1/s₁"},
            {"name": "瞬发跳跃比 n₁/n₀",
             "value": (round(jump_ratio, 6) if math.isfinite(jump_ratio) else None),
             "unit": "", "note": "β/(β−ρ)"},
            {"name": "判定", "value": crit["results"]["level"], "unit": "",
             "note": f"β={beta:g}"},
        ],
        "note": (f"Λ=l={float(l):g} s；RK4 积分 0→{t_end:g} s，{len(series[0]['points'])} 点。"
                 "不含温度反馈。"),
        "refs": roots["refs"],
        "svg": _svg_curve(series, "t / s", "n / n₀",
                          "阶跃反应性下的中子密度响应", t_end),
    }
    detail_lines = [
        f"【输入】ρ={rho_value:.6g} Δk/k = {rho_value * 1e5:.4g} pcm = {rho_value / beta:.4g} $；"
        f"l={float(l):g} s；β={beta:g}",
        f"【倒时方程】主导根 s₁={s:.6g} s⁻¹，其余 {len(roots['results']['roots']) - 1} 个根为负",
        f"【周期】T=1/s₁={_fmt(T)} s",
        f"【瞬发跳跃】n₁/n₀={_fmt(jump_ratio)}",
        f"【判定】{crit['results']['level']}（ρ/β={rho_value / beta:.4g}）",
        f"【响应曲线】t_end={t_end:g} s，n/n₀ 终值={resp['results']['final_n_over_n0']:.6g}",
        "【依据】教材 8.1 p.128、8.2 p.129-132（式8-13~8-17）；表2-3 p.27",
    ]
    return ToolOutcome(
        ok=True,
        summary=(f"ρ={rho_value * 1e5:.4g} pcm（{rho_value / beta:.3g}$）→ 周期 T={_fmt(T)} s，"
                 f"瞬发跳跃 {_fmt(jump_ratio)}，{crit['results']['level']}"),
        detail="\n".join(detail_lines),
        artifact_type="plot",
        artifact_data=artifact,
        payload={"result": {
            "rho": rho_value, "rho_pcm": rho_value * 1e5, "rho_dollar": rho_value / beta,
            "s": _finite(s), "period_s": _finite(T), "prompt_jump": _finite(jump_ratio),
            "prompt_critical": crit["results"]["prompt_critical"],
            "level": crit["results"]["level"],
            "final_n_over_n0": resp["results"]["final_n_over_n0"],
        }},
    )


def _svg_curve(series, x_label, y_label, title, t_end) -> str:
    try:
        from app.plots import svg as svgmod
        return svgmod.line_chart(series, x_label=x_label, y_label=y_label, title=title,
                                 width=820, height=440,
                                 note="六组缓发中子点堆方程 RK4 数值积分")
    except Exception:
        return ""


TOOL = ToolSpec(
    name="kinetics_calc",
    label="点堆动力学 · {query}",
    description=(
        "点堆中子动力学计算：六组缓发中子倒时方程求主导根 s 与反应堆周期 T、"
        "瞬发跳跃比、瞬发临界判定（ρ≥β），并用 RK4 数值积分给出阶跃反应性后的"
        "n/n₀–t 响应曲线。反应性支持 pcm/mk/%/Δk·k⁻¹/$；可只传 query，"
        "自动解析 ρ=200pcm、+0.2$、β=0.0065、l=1e-4s、t=100s。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "学生原问题文本；缺省结构化参数时从中解析"},
            "rho": {"type": "number", "description": "阶跃反应性（配合 rho_unit）"},
            "rho_unit": {"type": "string", "enum": ["dk/k", "pcm", "mk", "%", "$"],
                         "description": "反应性单位，默认 dk/k"},
            "beta": {"type": "number", "description": "有效缓发中子份额 β，默认 0.0065"},
            "l": {"type": "number", "description": "热中子寿期/代时间 Λ（s），默认 1e-4"},
            "k_eff": {"type": "number", "description": "由 k_eff 换算反应性（与 rho 二选一）"},
            "ratio": {"type": "number", "description": "功率比 n₂/n₁（求平均周期模式）"},
            "dt": {"type": "number", "description": "时间间隔（s），配合 ratio"},
            "t_end": {"type": "number", "description": "响应曲线积分总时间（s）"},
        },
        "required": [],
    },
    run=kinetics_calc,
)


__all__ = ["kinetics_calc", "TOOL"]
