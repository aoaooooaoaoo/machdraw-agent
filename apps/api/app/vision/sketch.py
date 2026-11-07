"""图形找茬：把学生画的线与标准答案比对，分成可命名的错误类型。

这是"智能找茬"的几何内核部分（可判定的那一半）。设计原则与全项目一致：
**能算的绝不让模型猜** —— 漏画、多画、虚实线混淆、位置偏差，全是可判定的。

支持两种输入：
  1. 学生提交的线段集合（来自画板/批改前端）；
  2. 图片识别结果（未来接 CV/VLM 后归一成同样的线段集合再走本模块）。

坐标单位 mm，容差可调（默认 3 mm，约等于 A3 图上 1 mm 的作图误差）。
"""
from __future__ import annotations

import math

Seg = dict          # {x1,y1,x2,y2,hidden}


def _len(s: Seg) -> float:
    return math.hypot(s["x2"] - s["x1"], s["y2"] - s["y1"])


def _angle(s: Seg) -> float:
    """方向角（0..180），用于判平行。"""
    a = math.degrees(math.atan2(s["y2"] - s["y1"], s["x2"] - s["x1"])) % 180.0
    return a


def _pt_line_dist(p, s: Seg) -> float:
    x1, y1, x2, y2 = s["x1"], s["y1"], s["x2"], s["y2"]
    dx, dy = x2 - x1, y2 - y1
    L2 = dx * dx + dy * dy
    if L2 < 1e-12:
        return math.hypot(p[0] - x1, p[1] - y1)
    t = ((p[0] - x1) * dx + (p[1] - y1) * dy) / L2
    t = max(0.0, min(1.0, t))
    return math.hypot(p[0] - (x1 + t * dx), p[1] - (y1 + t * dy))


def _proj_interval(s: Seg, ux: float, uy: float) -> tuple[float, float]:
    t1 = s["x1"] * ux + s["y1"] * uy
    t2 = s["x2"] * ux + s["y2"] * uy
    return (min(t1, t2), max(t1, t2))


def _bbox(segs: list[Seg]) -> list[float]:
    xs, ys = [], []
    for s in segs:
        xs += [s["x1"], s["x2"]]
        ys += [s["y1"], s["y2"]]
    return [round(min(xs), 2), round(min(ys), 2), round(max(xs), 2), round(max(ys), 2)]


ERROR_TYPES = {
    "missing":       ("漏画", "答案里有这条线，你的图上没有"),
    "extra":         ("多画", "你的图上多了这条线，答案里没有"),
    "linetype":      ("虚实线混淆", "位置对了，但该画虚线却画成实线（或相反）"),
    "offset":        ("位置偏差", "线画歪了或长度不对，超出作图容差"),
    "wrong_angle":   ("方向错误", "斜率与答案不一致（可能画错了视图或投影）"),
}


def _angle_diff(a: float, b: float) -> float:
    d = abs(a - b) % 180.0
    return min(d, 180.0 - d)


def grade(
    student: list[Seg],
    truth: list[Seg],
    tol: float = 3.0,
    angle_tol: float = 3.0,
) -> dict:
    """比对并给出结构化错误列表。"""
    used_truth: set[int] = set()
    errors: list[dict] = []
    matched = 0

    for s in student:
        best: tuple[float, float, int] | None = None
        ls = max(_len(s), 1e-6)
        for ti, t in enumerate(truth):
            if ti in used_truth:
                continue
            # 双向端点距离（都截到对方线段上），这样"短一点/长一点"不算错
            d = max(
                _pt_line_dist((s["x1"], s["y1"]), t),
                _pt_line_dist((s["x2"], s["y2"]), t),
                _pt_line_dist((t["x1"], t["y1"]), s),
                _pt_line_dist((t["x2"], t["y2"]), s),
            )
            da = _angle_diff(_angle(s), _angle(t))
            if best is None or d < best[0]:
                best = (d, da, ti)
        if best is None:
            errors.append(_err("extra", s, "你的图上多画了一条线"))
            continue
        d, da, ti = best
        t = truth[ti]
        # 短线被同样的绝对误差扰动时角度会显得差很多，容差随线长自适应
        da_allowed = angle_tol + math.degrees(math.atan(min(2.0, 2.0 * tol / ls)))

        if d <= tol and da <= da_allowed:
            used_truth.add(ti)
            if bool(s.get("hidden")) != bool(t.get("hidden")):
                want = "虚线" if t.get("hidden") else "粗实线"
                got = "虚线" if s.get("hidden") else "粗实线"
                errors.append(_err(
                    "linetype", s,
                    f"这条线应该是**{want}**，你画成了**{got}**",
                    truth_bbox=_bbox([t]),
                ))
            else:
                matched += 1
        elif d <= tol * 4 and da <= da_allowed:
            # 位置接近但偏差超容差：位置偏差
            used_truth.add(ti)
            errors.append(_err(
                "offset", s,
                f"这条线偏离答案约 {d:.1f} mm（容差 {tol:g} mm）",
                truth_bbox=_bbox([t]),
            ))
        elif da <= da_allowed:
            used_truth.add(ti)
            errors.append(_err("extra", s, "这条线的位置不对，答案中同一方向没有对应的线"))
        else:
            errors.append(_err("wrong_angle", s, f"这条线的方向与答案不一致（差 {da:.0f}°）"))

    # 答案里没被匹配到的 → 漏画
    for ti, t in enumerate(truth):
        if ti in used_truth:
            continue
        errors.append(_err("missing", t, "这条线漏画了"))

    total = len(truth)
    score = matched / total if total else 0.0
    counts: dict[str, int] = {}
    for e in errors:
        counts[e["type"]] = counts.get(e["type"], 0) + 1

    return {
        "score": round(score, 4),
        "matched": matched,
        "truth_total": total,
        "student_total": len(student),
        "level": "通过" if (score >= 0.95 and not errors) else ("存疑" if score >= 0.72 else "未通过"),
        "errors": errors,
        "error_counts": counts,
        "types": {k: {"name": v[0], "desc": v[1]} for k, v in ERROR_TYPES.items()},
        "note": "只做几何级判定：漏画/多画/虚实线/位置/方向。尺寸数值、剖面线间距、粗糙度符号等需教师复核。",
    }


def angle_normalize(a: float) -> float:
    return a % 180.0


def _err(kind: str, seg: Seg, desc: str, truth_bbox=None) -> dict:
    return {
        "type": kind,
        "type_name": ERROR_TYPES[kind][0],
        "segment": {
            "x1": round(seg["x1"], 2), "y1": round(seg["y1"], 2),
            "x2": round(seg["x2"], 2), "y2": round(seg["y2"], 2),
            "hidden": bool(seg.get("hidden")),
        },
        "bbox": _bbox([seg]),
        "truth_bbox": truth_bbox,
        "desc": desc,
    }


# ---------------------------------------------------------------- 造错（用于自测与演示）


INJECT_KINDS = ("missing", "extra", "linetype", "offset", "wrong_angle")


def inject_errors(truth: list[Seg], kinds: list[str] | None = None, seed: int = 0) -> tuple[list[Seg], list[str]]:
    """故意在一份标准答案里注入错误，返回 (被改坏的图, 注入的错误类型)。

    用来做两件事：① 自测"判错能不能判出来"；② 生成"找茬练习"的题目。
    """
    import random

    rnd = random.Random(seed)
    kinds = kinds or ["missing", "linetype", "offset"]
    segs = [dict(s) for s in truth]
    done: list[str] = []
    pool = list(range(len(segs)))
    rnd.shuffle(pool)

    for kind in kinds:
        if not pool:
            break
        i = pool.pop()
        s = segs[i]
        if kind == "missing":
            segs[i] = None       # type: ignore[assignment]
            done.append("missing")
        elif kind == "linetype":
            s["hidden"] = not s.get("hidden", False)
            done.append("linetype")
        elif kind == "offset":
            s["x1"] += 6.0
            s["x2"] += 6.0
            done.append("offset")
        elif kind == "wrong_angle":
            s["x2"] += 5.0
            s["y2"] += 9.0
            done.append("wrong_angle")
        elif kind == "extra":
            segs.append({
                "x1": s["x1"], "y1": s["y1"] + 9.0,
                "x2": s["x2"], "y2": s["y2"] + 9.0,
                "hidden": False,
            })
            done.append("extra")
    return [s for s in segs if s is not None], done
