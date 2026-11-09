"""工具 burnup_calc：燃耗深度、²³⁵U 消耗、铀装载量与循环长度。

支持只传 ``query``：自动解析 P=3000MW、t=30天、m=72tU、BU=15000 MWd/tU、
Pe=1200MW、ηe=0.30、负荷因子=0.8、ρ0=0.05、α=...、n=3 等。
spec 第4.3 节：name=burnup_calc，画布 ``calc``。
"""
from __future__ import annotations

import importlib
import math
import re

from .base import ToolContext, ToolOutcome
from .spec import ToolSpec

_NUM = r"([-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)"
_TIME_U = r"(s|秒|d|day|天|年|yr|a|周)"


def _grab(text: str, patterns: list[str], default=None):
    for p in patterns:
        m = re.search(p, text, re.I)
        if m:
            try:
                return float(m.group(1)), (m.group(2) if m.lastindex and m.lastindex >= 2 and m.group(2) else "")
            except (TypeError, ValueError, IndexError):
                continue
    return default, ""


def _to_days(value: float, unit: str) -> float:
    u = (unit or "d").lower()
    if u in ("s", "秒"):
        return value / 86400.0
    if u in ("d", "day", "天"):
        return value
    if u in ("年", "yr", "a"):
        return value * 365.0
    if u in ("周",):
        return value * 7.0
    return value


def _detect_mode(q: str, explicit: str) -> str:
    m = (explicit or "").strip().lower()
    if m:
        return m
    if re.search(r"循环长度|寿期|线性反应性|LRM|循环燃耗", q, re.I):
        return "cycle"
    if re.search(r"装载量|装料量|铀装载|堆芯装料", q, re.I):
        return "loading"
    if re.search(r"kWh|kW·h|千瓦时|度电", q, re.I):
        return "energy"
    if re.search(r"燃耗深度|卸料燃耗|比燃耗", q, re.I):
        return "burnup"
    if re.search(r"消耗|耗铀|烧掉|需要多少.*铀", q, re.I):
        return "consumption"
    return ""


def _fmt(v, nd=6) -> str:
    if v is None:
        return "—"
    if isinstance(v, float) and (abs(v) >= 1e5 or (v != 0 and abs(v) < 1e-3)):
        return f"{v:.4e}"
    return f"{v:.{nd}g}"


def burnup_calc(ctx: ToolContext, query: str = "", mode: str = "",
                power_mw: float | None = None, days: float | None = None,
                mass_tu: float | None = None, alpha: float | None = None,
                energy_kwh: float | None = None,
                power_e_mw: float | None = None, eta_e: float | None = None,
                load_factor: float | None = None, burnup_mwd_tu: float | None = None,
                refuel_fraction: float | None = None, rho0: float | None = None,
                alpha_per_mwd_tu: float | None = None, n_batches: float | None = None,
                **_) -> ToolOutcome:
    q = query or ""
    try:
        bu = importlib.import_module("app.domain.burnup")
    except ImportError:
        return ToolOutcome(ok=False, summary="燃耗引擎尚未就绪",
                           detail="app/domain/burnup.py 缺失")

    mode = _detect_mode(q, mode)

    # ---------------- 解析
    if power_mw is None:
        val, u = _grab(q, [r"(?:P|功率|热功率)\s*[=:：]?\s*" + _NUM + r"\s*(MWt|MWe|MW|kW)?"])
        if val is not None:
            power_mw = val * (1e-3 if (u or "").lower() == "kw" else 1.0)
    if power_e_mw is None:
        val, _u = _grab(q, [r"(?:Pe|电功率|额定电功率)\s*[=:：]?\s*" + _NUM + r"\s*(MW|kW)?"])
        if val is not None:
            power_e_mw = val
    if days is None:
        val, u = _grab(q, [
            r"(?:t|运行时间|满功率运行时间|时间)\s*[=:：]\s*" + _NUM + r"\s*" + _TIME_U,
            r"(?:满功率运行|运行|照射|燃耗)\s*[=:：]?\s*" + _NUM + r"\s*" + _TIME_U,
            r"(?<![A-Za-z0-9])" + _NUM + r"\s*" + _TIME_U,
        ])
        if val is not None:
            days = _to_days(val, u or "d")
    if mass_tu is None:
        val, _u = _grab(q, [
            r"(?:m|M|质量|装量|装料量|装料|铀装载量|铀装量|燃料质量|铀质量)\s*[=:：]?\s*"
            + _NUM + r"\s*(tU|t|kg)?",
        ])
        if val is not None:
            mass_tu = val * (1e-3 if "kg" in (_u or "") else 1.0)
    if alpha is None:
        val, _u = _grab(q, [r"(?:α|alpha|俘获[-—]?裂变比)\s*[=:：]?\s*" + _NUM])
        if val is not None:
            alpha = val
    if energy_kwh is None:
        val, _u = _grab(q, [
            r"(?:E|能量|电能)\s*[=:：]?\s*" + _NUM + r"\s*(?:kWh|kW·h|度)",
            _NUM + r"\s*(?:kWh|kW·h)",
        ])
        if val is not None:
            energy_kwh = val
    if eta_e is None:
        val, _u = _grab(q, [r"(?:ηe|eta_?e|热效率|效率)\s*[=:：]?\s*" + _NUM])
        if val is not None:
            eta_e = val / 100.0 if val > 1 else val
    if load_factor is None:
        val, _u = _grab(q, [r"(?:负荷因子|load_?factor)\s*[=:：]?\s*" + _NUM])
        if val is not None:
            load_factor = val / 100.0 if val > 1 else val
    if burnup_mwd_tu is None:
        val, _u = _grab(q, [r"(?:BU|燃耗深度|平均卸料燃耗|卸料燃耗)\s*[=:：]?\s*" + _NUM])
        if val is not None:
            burnup_mwd_tu = val
    if refuel_fraction is None:
        m = re.search(r"(?:每年|年)\s*(?:平均)?\s*更换?\s*(1/3|1/4|1/2|0\.\d+)", q)
        if m:
            tok = m.group(1)
            if "/" in tok:
                a_, b_ = tok.split("/")
                refuel_fraction = float(a_) / float(b_)
            else:
                refuel_fraction = float(tok)
        else:
            m = re.search(r"(?:换料份额|换料比例)\s*[=:：]?\s*" + _NUM, q)
            if m:
                v = float(m.group(1))
                refuel_fraction = v / 100.0 if v > 1 else v
    if rho0 is None:
        val, _u = _grab(q, [r"(?:ρ0|rho0|初始剩余反应性|剩余反应性)\s*[=:：]?\s*" + _NUM
                            + r"\s*(pcm|%)?"])
        if val is not None:
            unit = (_u or "").lower()
            rho0 = val * (1e-5 if unit == "pcm" else (1e-2 if unit == "%" else 1.0))
    if alpha_per_mwd_tu is None:
        val, _u = _grab(q, [r"(?:α|斜率)\s*[=:：]?\s*" + _NUM + r"\s*(?:/|\s*per\s*)?(?:MWd/tU)?"])
        if val is not None and alpha is None:
            alpha_per_mwd_tu = val
    if n_batches is None:
        val, _u = _grab(q, [r"(?:n|批料数|批数)\s*[=:：]?\s*" + _NUM + r"\s*(?:批)?",
                            r"(\d+)\s*批"])
        if val is not None:
            n_batches = val

    # 自动判定模式
    if not mode:
        if power_e_mw is not None and eta_e is not None and burnup_mwd_tu is not None:
            mode = "loading"
        elif rho0 is not None and alpha_per_mwd_tu is not None and n_batches is not None:
            mode = "cycle"
        elif energy_kwh is not None:
            mode = "energy"
        elif power_mw is not None and days is not None and mass_tu is not None:
            mode = "burnup"
        elif power_mw is not None and mass_tu is not None:
            mode = "burnup"
        elif power_mw is not None and days is not None:
            mode = "consumption"
        else:
            return ToolOutcome(
                ok=False, summary="缺少燃耗计算所需参数",
                detail="示例：① 燃耗深度：P=3000MW，t=365天，m=72tU；"
                       "② 铀消耗：P=3000MW，t=30天（α=0.169）；"
                       "③ 装载量：Pe=1200MW，ηe=0.30，负荷因子=0.8，BU=15000MWd/tU，每年换1/3；"
                       "④ 循环长度：ρ0=0.05，α=0.0007/(MWd/tU)，n=3，m=72tU，P=3000MW。",
            )

    try:
        if mode == "energy":
            if energy_kwh is None:
                raise ValueError("缺少能量 E（kWh）")
            r = bu.mass_for_energy(energy_kwh, 0.0 if alpha is None else alpha)
            title = "裂变能—²³⁵U 质量换算"
            inputs = [{"name": "能量 E", "value": energy_kwh, "unit": "kW·h"}]
            rows = [
                {"name": "²³⁵U 裂变质量", "value": r["results"]["fissioned_mass_kg"], "unit": "kg", "note": ""},
                {"name": "²³⁵U 消耗质量（含 α）", "value": r["results"]["consumed_mass_kg"], "unit": "kg", "note": f"α={0.0 if alpha is None else alpha:g}"},
            ]
            verdict = {"level": "能量—质量换算", "note": "按每次裂变 200 MeV（教材 2.5.2 p.26）"}
            steps = r["steps"]
            refs = r["refs"]
            summary = (f"{energy_kwh:g} kW·h 对应 ²³⁵U 裂变质量 {r['results']['fissioned_mass_kg']:.4g} kg")
            payload = {"result": r["results"]}
        elif mode == "consumption":
            if power_mw is None or days is None:
                raise ValueError("铀消耗计算需要功率 P（MW）与时间 t（d）")
            a = 0.169 if alpha is None else float(alpha)
            r = bu.u235_consumption(float(power_mw), float(days), a)
            title = "²³⁵U 消耗量估算"
            inputs = [
                {"name": "热功率 P", "value": power_mw, "unit": "MW"},
                {"name": "时间 t", "value": days, "unit": "d"},
                {"name": "俘获-裂变比 α", "value": a, "unit": ""},
            ]
            rows = [
                {"name": "裂变质量", "value": r["results"]["fissioned_mass_kg"], "unit": "kg", "note": "仅裂变"},
                {"name": "消耗质量（含 α）", "value": r["results"]["consumed_mass_kg"], "unit": "kg",
                 "note": "(1+α) 修正"},
                {"name": "产生能量", "value": r["results"]["energy_j"] / 3.6e6, "unit": "kW·h", "note": ""},
            ]
            verdict = {"level": "铀消耗量", "note": "教材 3.1.3 式(3-15) p.33"}
            steps = r["steps"]
            refs = r["refs"]
            summary = (f"P={power_mw:g} MW 运行 {days:g} d 消耗 ²³⁵U "
                       f"{r['results']['consumed_mass_kg']:.4g} kg（α={a:g}）")
            payload = {"result": r["results"]}
        elif mode == "loading":
            if power_e_mw is None or eta_e is None or burnup_mwd_tu is None:
                raise ValueError("装载量计算需要 Pe（MW）、ηe、BU（MWd/tU）")
            lf = 1.0 if load_factor is None else float(load_factor)
            rf = 1.0 / 3.0 if refuel_fraction is None else float(refuel_fraction)
            r = bu.uranium_loading(float(power_e_mw), float(eta_e), lf,
                                   float(burnup_mwd_tu), rf)
            title = "由年发电量与平衡换料估算铀装载量"
            inputs = [
                {"name": "电功率 Pe", "value": power_e_mw, "unit": "MW"},
                {"name": "热效率 ηe", "value": eta_e, "unit": ""},
                {"name": "负荷因子", "value": lf, "unit": ""},
                {"name": "平均卸料燃耗 BU", "value": burnup_mwd_tu, "unit": "MWd/tU"},
                {"name": "每年换料份额", "value": rf, "unit": ""},
            ]
            rows = [
                {"name": "平均热功率", "value": r["results"]["P_th_avg_mw"], "unit": "MW", "note": ""},
                {"name": "年发热量", "value": r["results"]["annual_energy_mwd"], "unit": "MWd", "note": ""},
                {"name": "每批换料量", "value": r["results"]["batch_mass_tu"], "unit": "tU", "note": ""},
                {"name": "铀装载量", "value": r["results"]["total_loading_tu"], "unit": "tU", "note": "题6.4 答案 233.6 tU"},
            ]
            verdict = {"level": "铀装载量", "note": "平衡换料简化估算（习题 v4.0 题6.4）"}
            steps = r["steps"]
            refs = r["refs"]
            summary = f"铀装载量约 {r['results']['total_loading_tu']:.4g} tU（Pe={power_e_mw:g} MW，换料 {rf:.3g}/年）"
            payload = {"result": r["results"]}
        elif mode == "cycle":
            if rho0 is None or alpha_per_mwd_tu is None or n_batches is None or mass_tu is None or power_mw is None:
                raise ValueError("循环长度需要 ρ0、α(/MWd/tU)、n、m(tU)、P(MW)")
            r = bu.cycle_length_linear(float(rho0), float(alpha_per_mwd_tu), int(n_batches),
                                       float(mass_tu), float(power_mw))
            title = "线性反应性模型（LRM）循环长度"
            inputs = [
                {"name": "循环初剩余反应性 ρ0", "value": rho0, "unit": ""},
                {"name": "反应性斜率 α", "value": alpha_per_mwd_tu, "unit": "/(MWd/tU)"},
                {"name": "批料数 n", "value": n_batches, "unit": ""},
                {"name": "铀装量 m", "value": mass_tu, "unit": "tU"},
                {"name": "热功率 P", "value": power_mw, "unit": "MW"},
            ]
            rows = [
                {"name": "循环燃耗 B_c", "value": r["results"]["cycle_burnup_mwd_tu"], "unit": "MWd/tU", "note": "2ρ0/((n+1)α)"},
                {"name": "卸料燃耗 B_d", "value": r["results"]["discharge_burnup_mwd_tu"], "unit": "MWd/tU", "note": "n·B_c"},
                {"name": "循环长度 T", "value": r["results"]["cycle_length_efpd"], "unit": "EFPD", "note": "B_c·m/P"},
            ]
            verdict = {"level": "线性反应性模型", "note": "假设各批 α 相同、循环末堆芯 ρ=0（题9.2）"}
            steps = r["steps"]
            refs = r["refs"]
            summary = (f"循环燃耗 {r['results']['cycle_burnup_mwd_tu']:.4g} MWd/tU，"
                       f"循环长度 {r['results']['cycle_length_efpd']:.4g} EFPD，"
                       f"卸料燃耗 {r['results']['discharge_burnup_mwd_tu']:.4g} MWd/tU")
            payload = {"result": r["results"]}
        else:  # burnup
            if power_mw is None or mass_tu is None:
                raise ValueError("燃耗深度需要 P（MW）与 m（tU）；补 t（d）可得燃耗深度")
            if days is None:
                # 只给了功率与装量：先给单位时间燃耗速率（不臆造运行时间）
                rate = float(power_mw) / float(mass_tu)  # MWd/tU per day
                title = "燃耗速率（未给运行时间）"
                inputs = [
                    {"name": "热功率 P", "value": power_mw, "unit": "MW"},
                    {"name": "铀装量 m", "value": mass_tu, "unit": "tU"},
                ]
                rows = [
                    {"name": "燃耗速率", "value": rate, "unit": "MWd/tU/d",
                     "note": "BU/t = P/m"},
                ]
                verdict = {"level": "燃耗速率（缺运行时间）",
                           "note": "给出运行天数 t 后：BU = (P·t)/m"}
                steps = [f"燃耗速率 = P/m = {power_mw:g}/{mass_tu:g} = {rate:.6g} MWd/tU/d",
                         "补充运行天数 t 后，燃耗深度 BU = rate × t"]
                refs = ["教材 第6章 6.1 节 p.98-99（燃耗深度定义）",
                        "教材 第3章 3.1.3 节 p.33（裂变功率与消耗量）"]
                summary = (f"燃耗速率 {rate:.4g} MWd/(tU·d)（P={power_mw:g} MW，m={mass_tu:g} tU；"
                           "补 t 可算燃耗深度）")
                payload = {"result": {"burnup_rate_mwd_tu_d": rate,
                                      "power_mw": float(power_mw),
                                      "mass_tu": float(mass_tu)}}
            else:
                r = bu.burnup_depth(float(power_mw), float(days), float(mass_tu))
                BU = r["results"]["burnup_mwd_tu"]
                title = "燃耗深度计算"
                inputs = [
                    {"name": "热功率 P", "value": power_mw, "unit": "MW"},
                    {"name": "时间 t", "value": days, "unit": "d"},
                    {"name": "铀装量 m", "value": mass_tu, "unit": "tU"},
                ]
                rows = [
                    {"name": "燃耗深度", "value": BU, "unit": "MWd/tU", "note": "P·t/m"},
                    {"name": "总能量", "value": r["results"]["energy_mwd"], "unit": "MWd", "note": ""},
                ]
                if BU > 50000:
                    level = "超过典型卸料限值"
                else:
                    level = "在典型卸料限值内"
                vnote = "教材 9.2.1 p.145-147：Zr 包壳 UO₂ 卸料燃耗限制约 40000~50000 MWd/tU"
                verdict = {"level": level, "note": vnote}
                steps = r["steps"]
                refs = r["refs"]
                summary = (f"燃耗深度 {BU:.4g} MWd/tU（P={power_mw:g} MW，t={days:g} d，"
                           f"m={mass_tu:g} tU）")
                payload = {"result": r["results"]}
    except ValueError as exc:
        return ToolOutcome(ok=False, summary="燃耗计算参数不完整或越界", detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        return ToolOutcome(ok=False, summary=f"燃耗计算失败：{type(exc).__name__}", detail=str(exc))

    artifact = {
        "title": title,
        "inputs": [{"name": x["name"], "value": x["value"], "unit": x.get("unit", "")} for x in inputs],
        "formulas": [{"step": s_, "note": n_} for s_, n_ in _formulas(mode)],
        "results": rows,
        "verdict": verdict,
        "refs": refs,
        "note": verdict["note"],
        "svg": "",
    }
    detail_lines = [f"【模式】{mode}"] + [f"【步骤】{s_}" for s_ in steps] + [f"【依据】{'；'.join(refs[:2])}"]
    return ToolOutcome(ok=True, summary=summary, detail="\n".join(detail_lines[:15]),
                       artifact_type="calc", artifact_data=artifact, payload=payload)


def _formulas(mode: str) -> list[tuple[str, str]]:
    table = {
        "burnup": [("BU = P·t/m_U", "教材 6.1 p.98-99")],
        "consumption": [("m_消耗 = (1+α)·P·t·M/(E_f·N_A)", "教材 3.1.3 p.33 式(3-15)")],
        "loading": [("m_U = (Pe·f/ηe·T)/BU ÷ 换料份额", "习题 v4.0 题6.4")],
        "cycle": [("B_c = 2ρ0/((n+1)α)；T=B_c·m/P", "教材 9.2.1 p.145-147；题9.2")],
        "energy": [("m = E·M/(E_f·N_A)", "教材 3.1.3 p.33")],
    }
    return table.get(mode, [])


TOOL = ToolSpec(
    name="burnup_calc",
    label="燃耗计算 · {query}",
    description=(
        "燃耗计算：燃耗深度 BU=P·t/m（MWd/tU）、²³⁵U 消耗量（含俘获-裂变比 α 的 "
        "(1+α) 修正）、由年发电量与平衡换料估算铀装载量、线性反应性模型（LRM）的"
        "循环燃耗/循环长度/卸料燃耗。学生问“燃耗多深/一年烧多少铀/循环多长”时调用。"
        "可只传 query，自动解析 P=3000MW、t=30天、BU=15000MWd/tU、Pe=1200MW、ηe=0.30 等。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "学生原问题文本；缺省结构化参数时从中解析"},
            "mode": {"type": "string", "enum": ["burnup", "consumption", "loading", "cycle", "energy"],
                     "description": "计算模式"},
            "power_mw": {"type": "number", "description": "热功率（MW）"},
            "days": {"type": "number", "description": "运行时间（d）"},
            "mass_tu": {"type": "number", "description": "铀质量（tU）"},
            "alpha": {"type": "number", "description": "俘获-裂变比 α，²³⁵U 常取 0.169"},
            "energy_kwh": {"type": "number", "description": "能量（kW·h）"},
            "power_e_mw": {"type": "number", "description": "电功率（MW）"},
            "eta_e": {"type": "number", "description": "热效率"},
            "load_factor": {"type": "number", "description": "年负荷因子"},
            "burnup_mwd_tu": {"type": "number", "description": "平均卸料燃耗（MWd/tU）"},
            "refuel_fraction": {"type": "number", "description": "每年换料份额，如 1/3"},
            "rho0": {"type": "number", "description": "循环初剩余反应性（无量纲）"},
            "alpha_per_mwd_tu": {"type": "number", "description": "反应性随燃耗斜率 α（/(MWd/tU)）"},
            "n_batches": {"type": "number", "description": "批料数 n"},
        },
        "required": [],
    },
    run=burnup_calc,
)


__all__ = ["burnup_calc", "TOOL"]
