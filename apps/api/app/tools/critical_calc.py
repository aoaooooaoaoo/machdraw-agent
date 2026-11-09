"""工具 critical_calc：单群/修正单群临界计算（调用 app.domain.critical）。

支持两种用法：
1. 结构化参数（模型/前端显式传参）；
2. 只传 ``query``（学生原问题），从文本里解析 k∞、L²、τ、λtr、几何尺寸等。

spec 第4.3 节：name=critical_calc，画布 calculator = ``calc``。
"""
from __future__ import annotations

import importlib
import math
import re

from .base import ToolContext, ToolOutcome
from .spec import ToolSpec

_NUM = r"([-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)"
_AREA_U = r"(cm2|cm²|cm\^2|m2|m²|m\^2|mm2|mm²|mm\^2)"
_LEN_U = r"(cm|mm|m)?"

_GEOM_WORDS = {
    "slab": ("平板", "无限平板", "slab", "plate"),
    "sphere": ("球形", "球壳", "球", "sphere"),
    "cylinder": ("圆柱", "cylinder"),
    "cuboid": ("长方体", "立方体", "矩形", "cuboid", "box"),
}


def _grab(text: str, patterns: list[str], default=None):
    for p in patterns:
        m = re.search(p, text, re.I)
        if m:
            try:
                val = float(m.group(1))
            except (TypeError, ValueError, IndexError):
                continue
            unit = ""
            if m.lastindex and m.lastindex >= 2 and m.group(2):
                unit = m.group(2)
            return val, unit
    return default, ""


def _len_to_m(val: float, unit: str) -> float:
    u = (unit or "m").lower().replace("²", "2").replace("^", "")
    if u == "cm":
        return val * 1e-2
    if u == "mm":
        return val * 1e-3
    return val


def _area_to_m2(val: float, unit: str) -> float:
    u = (unit or "m2").lower().replace("²", "2").replace("^", "")
    if u == "cm2":
        return val * 1e-4
    if u == "mm2":
        return val * 1e-6
    return val


def _detect_geometry(query: str, explicit: str) -> str:
    g = (explicit or "").strip().lower()
    if g in _GEOM_WORDS:
        return g
    for key, words in _GEOM_WORDS.items():
        if any(w in query for w in words):
            return key
    return "slab"


def _fmt(v) -> str:
    if v is None:
        return "—"
    av = abs(float(v))
    if av != 0 and (av >= 1e5 or av < 1e-3):
        return f"{float(v):.4e}"
    return f"{float(v):.6g}"


def critical_calc(ctx: ToolContext, query: str = "", k_inf: float | None = None,
                  L2: float | None = None, tau: float | None = None,
                  M2: float | None = None, geometry: str = "",
                  H: float | None = None, R: float | None = None,
                  a: float | None = None, b: float | None = None,
                  c: float | None = None, d: float | None = None,
                  lambda_tr: float | None = None,
                  reflector_saving: float | None = None,
                  unit: str = "m", **_) -> ToolOutcome:
    q = query or ""
    try:
        crit = importlib.import_module("app.domain.critical")
    except ImportError:
        return ToolOutcome(ok=False, summary="临界引擎尚未就绪",
                           detail="app/domain/critical.py 缺失")

    # ---------------- 从 query 解析
    if k_inf is None:
        val, _u = _grab(q, [
            r"k\s*_?\s*(?:inf|infinity|∞)\s*[=:：]?\s*" + _NUM,
            r"k∞\s*[=:：]?\s*" + _NUM,
            r"k\s*_?\s*eff\s*[=:：]\s*" + _NUM,
            r"无限介质增殖系数\s*[=:：]?\s*" + _NUM,
        ])
        k_inf = val
    if L2 is None:
        val, u = _grab(q, [
            r"L\s*_?\s*(?:2|²|\^2)\s*[=:：]?\s*" + _NUM + r"\s*" + _AREA_U,
            r"L\s*(?:2|²|\^2)" + _NUM + r"\s*" + _AREA_U,
            r"扩散面积\s*[=:：]?\s*" + _NUM + r"\s*" + _AREA_U,
            r"L\s*(?:2|²)\s*[=:：]\s*" + _NUM,
        ])
        if val is not None:
            L2 = _area_to_m2(val, u)
        else:
            # 兼容“L=0.0434m”写法：L² = L²
            val, u = _grab(q, [r"L\s*[=:：]\s*" + _NUM + r"\s*(cm|mm|m)"])
            if val is not None:
                L_m = _len_to_m(val, u)
                L2 = L_m * L_m
    if tau is None:
        val, u = _grab(q, [
            r"(?:τ|tau|τth|θ)\s*(?:th)?\s*[=:：]?\s*" + _NUM + r"\s*" + _AREA_U,
            r"τ\s*(?:th)?\s*[=:：]\s*" + _NUM,
            r"慢化面积\s*[=:：]?\s*" + _NUM + r"\s*" + _AREA_U,
        ])
        if val is not None:
            tau = _area_to_m2(val, u)
    if M2 is None:
        val, u = _grab(q, [
            r"M\s*_?\s*(?:2|²|\^2)\s*[=:：]?\s*" + _NUM + r"\s*" + _AREA_U,
            r"徙动面积\s*[=:：]?\s*" + _NUM + r"\s*" + _AREA_U,
        ])
        if val is not None:
            M2 = _area_to_m2(val, u)
    if lambda_tr is None:
        val, u = _grab(q, [
            r"λ\s*_?\s*(?:tr|transport)\s*[=:：]?\s*" + _NUM + r"\s*" + _LEN_U,
            r"输运平均自由程\s*[=:：]?\s*" + _NUM + r"\s*" + _LEN_U,
        ])
        if val is not None:
            lambda_tr = _len_to_m(val, u)
    if d is None:
        val, u = _grab(q, [r"外推距离\s*[=:：]?\s*" + _NUM + r"\s*" + _LEN_U,
                           r"\bd\s*[=:：]\s*" + _NUM + r"\s*" + _LEN_U])
        if val is not None:
            d = _len_to_m(val, u)
    if reflector_saving is None:
        val, u = _grab(q, [r"反射层节省\s*[=:：]?\s*" + _NUM + r"\s*" + _LEN_U,
                           r"(?:δ|delta)\s*[=:：]\s*" + _NUM + r"\s*" + _LEN_U])
        if val is not None:
            reflector_saving = _len_to_m(val, u)

    geom = _detect_geometry(q, geometry)
    if H is None:
        val, u = _grab(q, [
            r"(?<![A-Za-z])H\s*[=:：]?\s*" + _NUM + r"\s*" + _LEN_U,
            r"(?:高度|高|厚度)\s*[=:：]?\s*" + _NUM + r"\s*" + _LEN_U,
        ])
        if val is not None:
            H = _len_to_m(val, u)
    if R is None:
        val, u = _grab(q, [
            r"(?<![A-Za-z])R\s*[=:：]?\s*" + _NUM + r"\s*" + _LEN_U,
            r"半径\s*[=:：]?\s*" + _NUM + r"\s*" + _LEN_U,
        ])
        if val is not None:
            R = _len_to_m(val, u)
    if a is None:
        val, u = _grab(q, [r"(?<![A-Za-z])a\s*[=:：]\s*" + _NUM + r"\s*" + _LEN_U])
        if val is not None:
            a = _len_to_m(val, u)
    if b is None:
        val, u = _grab(q, [r"(?<![A-Za-z])b\s*[=:：]\s*" + _NUM + r"\s*" + _LEN_U])
        if val is not None:
            b = _len_to_m(val, u)
    if c is None:
        val, u = _grab(q, [r"(?<![A-Za-z])c\s*[=:：]\s*" + _NUM + r"\s*" + _LEN_U])
        if val is not None:
            c = _len_to_m(val, u)

    if k_inf is None:
        return ToolOutcome(
            ok=False, summary="缺少无限介质增殖系数 k∞",
            detail="请给出 k∞（或 k_inf），例如：k∞=1.06, L²=0.03 m², τ=0 m²",
        )
    if L2 is None and tau is None and M2 is None:
        return ToolOutcome(
            ok=False, summary="缺少 L²/τ（或 M²）",
            detail="请给出 L² 与 τ（或直接给 M²），例如：k∞=1.06, L²=0.03 m², τ=0",
        )
    if M2 is None:
        L2 = 0.0 if L2 is None else float(L2)
        tau = 0.0 if tau is None else float(tau)
        M2 = L2 + tau
    else:
        M2 = float(M2)
        L2 = 0.0 if L2 is None else float(L2)
        tau = 0.0 if tau is None else float(tau)
        if abs((L2 + tau) - M2) > 1e-12 and (L2 or tau):
            # 用户同时给了三者，以 M² 为准
            pass

    try:
        bm = crit.buckling_material(k_inf, M2, 0.0)  # 直接用 M²
    except ValueError as exc:
        return ToolOutcome(ok=False, summary="材料参数无法临界", detail=str(exc))

    Bm2 = bm["results"]["Bm2"]
    if d is None and lambda_tr is not None:
        d = crit.extrapolation_distance(lambda_tr)["results"]["d"]
    d = 0.0 if d is None else float(d)
    delta = 0.0 if reflector_saving is None else float(reflector_saving)

    def _dims_for(g: str):
        if g == "slab":
            return {"H": H}
        if g == "sphere":
            return {"R": R}
        if g == "cylinder":
            return {"R": R, "H": H}
        return {"a": a, "b": b, "c": c}

    dims = _dims_for(geom)
    complete = all(v is not None for v in dims.values())
    partial = any(v is not None for v in dims.values())

    ask_curvature = bool(re.search(r"临界曲率|材料曲率|几何曲率|曲率", q))
    ask_size = bool(re.search(r"临界(?:厚度|尺寸|半径|高度|大小|体积)|多厚|多大|临界尺寸", q))
    ask_keff = bool(re.search(
        r"k\s*_?\s*eff|有效增殖|反应性|是否临界|能否临界|临界吗|k_?eff", q, re.I))

    used = {"engine": "critical", "k_inf": float(k_inf), "M2": float(M2),
            "L2": L2, "tau": tau, "Bm2": Bm2, "d": d,
            "reflector_saving": delta, "geometry": geom}

    try:
        # ---------- 分支 0：只问“材料曲率/临界曲率”，且没给完整尺寸、没问尺寸/keff
        if ask_curvature and not complete and not ask_size and not ask_keff:
            bm_full = crit.buckling_material(k_inf, L2, tau) if (L2 or tau) else bm
            Bm = bm_full["results"]["Bm"]
            verdict = {"level": "材料曲率",
                       "note": f"B_m²=(k∞−1)/M²={Bm2:.6g} m⁻²；临界条件 B_g²=B_m²"}
            artifact = {
                "title": "材料曲率（单群临界条件）",
                "inputs": [
                    {"name": "k∞", "value": round(float(k_inf), 8), "unit": ""},
                    {"name": "M²", "value": round(float(M2), 10), "unit": "m²"},
                    {"name": "L²", "value": round(float(L2), 10), "unit": "m²"},
                    {"name": "τ", "value": round(float(tau), 10), "unit": "m²"},
                ],
                "formulas": [
                    {"step": "M² = L² + τ", "note": "徙动面积"},
                    {"step": "B_m² = (k∞ − 1) / M²", "note": "教材 4.2.1 p.57 式(4-49)"},
                    {"step": "临界条件 B_g² = B_m²", "note": "教材 4.2.1 p.58 式(4-50)"},
                ],
                "results": [
                    {"name": "M²", "value": round(float(M2), 10), "unit": "m²", "note": "L²+τ"},
                    {"name": "B_m²", "value": round(Bm2, 10), "unit": "m⁻²", "note": "(k∞−1)/M²"},
                    {"name": "B_m", "value": round(Bm, 10), "unit": "m⁻¹", "note": "√B_m²"},
                    {"name": "k∞", "value": round(float(k_inf), 8), "unit": "", "note": "给定"},
                ],
                "verdict": verdict,
                "refs": [
                    "教材 第4章 4.2.1 节 p.56-58（式4-49、4-50）",
                    "教材 第4章 4.2.2 节 p.60-61（修正单群）",
                ],
                "note": "求“临界曲率/材料曲率”不需要几何尺寸：只要 B_m² 与 B_g² 相等即临界。",
                "svg": "",
            }
            return ToolOutcome(
                ok=True,
                summary=f"k∞={k_inf:g}，M²={M2:g} m² → B_m²={Bm2:.6g} m⁻²",
                detail="\n".join([
                    f"【输入】k∞={k_inf:g}，M²={M2:g} m²（L²={L2:g}，τ={tau:g}）",
                    f"【材料曲率】B_m²=(k∞−1)/M²={Bm2:.6g} m⁻²，B_m={Bm:.6g} m⁻¹",
                    "【临界条件】几何曲率 B_g² 必须等于该 B_m²（教材 4.2.1 p.58）",
                    "【提示】若要临界尺寸，请给出几何形状与已知尺寸（如“平板，H=2.5m，求临界厚度”）。",
                ]),
                artifact_type="calc",
                artifact_data=artifact,
                payload={"result": {"k_inf": float(k_inf), "M2": float(M2),
                                    "Bm2": Bm2, "Bm": Bm, "geometry": geom}},
            )

        if complete:
            bg = crit.buckling_geometric(geom, dims, d=d, reflector_saving=delta)
            Bg2 = bg["results"]["Bg2"]
            ke = crit.k_eff_single_group(k_inf, M2, 0.0, Bg2)
            results = dict(ke["results"])
            results["Bg2"] = Bg2
            rho = results["rho"]
            verdict_level = "超临界" if rho > 1e-12 else ("临界" if abs(rho) <= 1e-12 else "次临界")
            verdict_note = f"B_g²={_fmt(Bg2)} m⁻²，k_eff={results['k_eff']:.6g}"
            res_rows = [
                {"name": "k∞", "value": round(float(k_inf), 8), "unit": "", "note": "四因子/给定"},
                {"name": "M²", "value": round(float(M2), 10), "unit": "m²", "note": "L²+τ"},
                {"name": "B_m²", "value": round(Bm2, 10), "unit": "m⁻²", "note": "(k∞−1)/M²"},
                {"name": "B_g²", "value": round(Bg2, 10), "unit": "m⁻²", "note": "几何曲率"},
                {"name": "k_eff", "value": round(results["k_eff"], 8), "unit": "", "note": "单群临界公式"},
                {"name": "ρ", "value": round(rho * 1e5, 4), "unit": "pcm", "note": "(k−1)/k"},
                {"name": "P_L", "value": round(results["P_L"], 6), "unit": "", "note": "不泄漏概率"},
            ]
            summary = (f"k∞={k_inf:g}，B_m²={Bm2:.6g} m⁻²，B_g²={Bg2:.6g} m⁻² → "
                       f"k_eff={results['k_eff']:.6g}（ρ={rho * 1e5:+.1f} pcm，{verdict_level}）")
            svg = ""
            formulas = bg["formulas"] + ke["formulas"]
            refs = ke["refs"]
            steps = bg["steps"] + ke["steps"]
        else:
            if geom == "cylinder" and not partial:
                return ToolOutcome(
                    ok=False, summary="圆柱临界计算缺少已知尺寸",
                    detail="请给出 H 或 R 之一（另一个将反解），例如：圆柱 k∞=1.072, L²=0.047 m², "
                           "τ=0.0048 m², λtr=0.097 m, H=3.55 m",
                )
            if geom == "cuboid" and not partial:
                return ToolOutcome(
                    ok=False, summary="长方体临界计算缺少已知边",
                    detail="请给出 a、b、c 中至少两个（另一个反解），例如：长方体 k∞=1.264, "
                           "L²=0.00188 m², τ=0.0006 m², a=0.5, b=0.5",
                )
            if geom == "slab":
                dims = {"H": H}
            cs = crit.critical_size(geom, k_inf, M2, 0.0, dims, d=d,
                                    reflector_saving=delta)
            L = cs["results"]["critical_size"]
            name = cs["results"]["size_name"]
            results = cs["results"]
            verdict_level = "临界尺寸"
            verdict_note = f"{name}={L:.6g} m 时 B_g²=B_m²（d={d:g} m，δ={delta:g} m）"
            res_rows = [
                {"name": "k∞", "value": round(float(k_inf), 8), "unit": "", "note": "给定"},
                {"name": "M²", "value": round(float(M2), 10), "unit": "m²", "note": "L²+τ"},
                {"name": "B_m²", "value": round(Bm2, 10), "unit": "m⁻²", "note": "(k∞−1)/M²"},
                {"name": f"临界 {name}", "value": round(L, 8), "unit": "m", "note": "二分反解（实际尺寸）"},
                {"name": "B_g² 校核", "value": round(results["Bg2_check"], 10), "unit": "m⁻²",
                 "note": f"二分 {results['iterations']} 次"},
            ]
            summary = (f"k∞={k_inf:g}，B_m²={Bm2:.6g} m⁻² → {_geom_cn(geom)}临界 {name}="
                       f"{L:.6g} m（d={d:g}, δ={delta:g}）")
            svg = _buckling_svg(crit, geom, dims, d, delta, Bm2, L, name)
            formulas = cs["formulas"]
            refs = cs["refs"]
            steps = cs["steps"]

        # 从 query 判断单位：本工具内部统一换算为 m
        note = ("长度单位已统一为 m；d 为外推距离，δ 为反射层节省。"
                if (d or delta) else "长度单位已统一为 m；未给外推距离时 d=0（等价于尺寸已含外推距离）。")
        detail_lines = [
            f"【输入】k∞={k_inf:g}，M²={M2:g} m²，几何={_geom_cn(geom)}",
            f"【材料曲率】B_m²=(k∞−1)/M² = {Bm2:.6g} m⁻²",
        ]
        if complete:
            detail_lines.append(f"【几何曲率】B_g² = {Bg2:.6g} m⁻²")
            detail_lines.append(f"【结果】k_eff={results['k_eff']:.6g}，ρ={rho * 1e5:+.2f} pcm，{verdict_level}")
        else:
            detail_lines.append(f"【临界尺寸】{name}={L:.6g} m（含二分校核 B_g²={results['Bg2_check']:.6g}）")
        detail_lines += [
            "【依据】教材 4.2.1 p.56-58（式4-43/4-49、表4-2）；4.2.2 p.60-61；3.3.3 p.42-43",
            f"【校核】{verdict_note}",
        ]
        artifact = {
            "title": f"{_geom_cn(geom)}单群临界计算",
            "inputs": [
                {"name": "k∞", "value": round(float(k_inf), 8), "unit": ""},
                {"name": "M²", "value": round(float(M2), 10), "unit": "m²"},
                {"name": "外推距离 d", "value": round(d, 8), "unit": "m"},
                {"name": "反射层节省 δ", "value": round(delta, 8), "unit": "m"},
            ],
            "formulas": [dict(f) for f in formulas],
            "results": res_rows,
            "verdict": {"level": verdict_level, "note": verdict_note},
            "refs": refs,
            "note": note,
            "svg": svg,
        }
        return ToolOutcome(
            ok=True,
            summary=summary,
            detail="\n".join(detail_lines),
            artifact_type="calc",
            artifact_data=artifact,
            payload={"result": {"k_inf": float(k_inf), "M2": float(M2), "Bm2": Bm2,
                                "B": results, "geometry": geom,
                                "d": d, "reflector_saving": delta}},
        )
    except ValueError as exc:
        return ToolOutcome(ok=False, summary="临界计算失败", detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        return ToolOutcome(ok=False, summary=f"临界计算失败：{type(exc).__name__}",
                           detail=str(exc))


def _geom_cn(g: str) -> str:
    return {"slab": "平板", "sphere": "球", "cylinder": "圆柱",
            "cuboid": "长方体"}.get(g, g)


def _buckling_svg(crit, geom, dims, d, delta, Bm2, L, name) -> str:
    """B_g²(尺寸) 与 B_m² 水平线的示意曲线（calc 卡片可选 svg）。"""
    try:
        importlib.import_module("app.plots.svg")
        from app.plots import svg as svgmod
    except Exception:
        return ""
    try:
        xs = [L * 0.4 + L * 1.6 * k / 79 for k in range(80)]
        pts = []
        for x in xs:
            merged = dict(dims)
            merged[name] = x
            try:
                bg = crit.buckling_geometric(geom, merged, d=d, reflector_saving=delta)
                pts.append([x, bg["results"]["Bg2"]])
            except Exception:
                continue
        if not pts:
            return ""
        return svgmod.line_chart(
            [
                {"name": "B_g²(尺寸)", "points": pts},
                {"name": "B_m²", "points": [[pts[0][0], Bm2], [pts[-1][0], Bm2]], "dash": True},
            ],
            x_label=f"{name} / m", y_label="曲率 / m⁻²",
            title="几何曲率与材料曲率交点（临界）",
            markers=[{"x": L, "y": Bm2, "label": "临界点"}],
            width=760, height=420,
            note="依据教材 4.2.1：临界条件 B_g²=B_m²",
        )
    except Exception:
        return ""


TOOL = ToolSpec(
    name="critical_calc",
    label="临界计算 · {query}",
    description=(
        "单群/修正单群临界计算：由 k∞、L²、τ、外推距离、反射层节省与几何尺寸，"
        "计算材料曲率 B_m²、几何曲率 B_g²、k_eff/反应性，或用二分反解平板/球/圆柱/"
        "长方体的临界尺寸。学生问“临界厚度/临界半径/k_eff/材料曲率”时调用。"
        "可只传 query（学生原问题），自动解析 k∞=1.06、L²=0.03m²、τ=0、H=2.5m 等。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "学生原问题文本；缺省结构化参数时从中解析"},
            "k_inf": {"type": "number", "description": "无限介质增殖系数 k∞"},
            "L2": {"type": "number", "description": "热中子扩散面积 L²（m²）"},
            "tau": {"type": "number", "description": "慢化面积 τ（m²）"},
            "M2": {"type": "number", "description": "徙动面积 M²=L²+τ（m²）；与 L2/tau 二选一"},
            "geometry": {"type": "string", "enum": ["slab", "sphere", "cylinder", "cuboid"],
                         "description": "几何：平板/球/圆柱/长方体"},
            "H": {"type": "number", "description": "平板厚度或圆柱高度（m）"},
            "R": {"type": "number", "description": "球/圆柱半径（m）"},
            "a": {"type": "number", "description": "长方体边长 a（m）"},
            "b": {"type": "number", "description": "长方体边长 b（m）"},
            "c": {"type": "number", "description": "长方体边长 c（m）"},
            "d": {"type": "number", "description": "外推距离（m）"},
            "lambda_tr": {"type": "number", "description": "输运平均自由程 λtr（m）；给定时 d=0.7104λtr"},
            "reflector_saving": {"type": "number", "description": "反射层节省 δ（m）"},
            "unit": {"type": "string", "description": "长度单位（m/cm/mm），默认 m"},
        },
        "required": [],
    },
    run=critical_calc,
)


__all__ = ["critical_calc", "TOOL"]
