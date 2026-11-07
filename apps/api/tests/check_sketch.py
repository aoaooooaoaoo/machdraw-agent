"""找茬引擎验收：注入已知错误，看能不能都判出来。"""
from __future__ import annotations

import sys
from pathlib import Path

API = Path(__file__).resolve().parents[1]
ROOT = API.parents[1]
sys.path.insert(0, str(API))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from app.geometry.models import build_model, model_name  # noqa: E402
from app.geometry.projection import build_three_view  # noqa: E402
from app.vision.sketch import grade, inject_errors  # noqa: E402

PASS = FAIL = 0


def check(label: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    print(f"  {'OK ' if cond else 'BAD'} {label} {detail}")
    if cond:
        PASS += 1
    else:
        FAIL += 1


def main() -> int:
    d = build_three_view(build_model("M-L-BLOCK"), "L 形块", "M-L-BLOCK")
    truth = [{"x1": s["x1"], "y1": s["y1"], "x2": s["x2"], "y2": s["y2"],
              "hidden": s["hidden"]} for s in d["segments"]]
    print(f"标准答案：{len(truth)} 条线（三个视图合计）")

    print("\n=== 1. 完全正确的图（应满分、零错误） ===")
    r = grade(truth, truth)
    check("score=1.0", r["score"] == 1.0, f"（实得 {r['score']}）")
    check("无错误", len(r["errors"]) == 0, f"（{r['error_counts']}）")
    check("等级=通过", r["level"] == "通过", r["level"])

    print("\n=== 2. 逐个注入单类错误（每类都应被识别） ===")
    for kind, expect_name in [("missing", "漏画"), ("linetype", "虚实线混淆"),
                              ("offset", "位置偏差"), ("extra", "多画")]:
        bad, done = inject_errors(truth, [kind], seed=7)
        r = grade(bad, truth)
        types = {e["type_name"] for e in r["errors"]}
        check(f"注入「{kind}」→ 检出「{expect_name}」", expect_name in types,
              f"（实际检出 {sorted(types)}）")

    print("\n=== 3. 一次注入 3 类错误 ===")
    bad, done = inject_errors(truth, ["missing", "linetype", "offset"], seed=3)
    r = grade(bad, truth)
    print(f"  注入：{done}")
    print(f"  得分 {r['score']}  等级 {r['level']}  错误统计 {r['error_counts']}")
    for e in r["errors"]:
        print(f"    [{e['type_name']}] {e['desc']}")
    check("检出 3 类", len(r["error_counts"]) >= 2, f"（{r['error_counts']}）")

    print("\n=== 4. 空图（全部漏画） ===")
    r = grade([], truth)
    check("全部判为漏画", r["error_counts"].get("missing", 0) == len(truth),
          f"（漏画 {r['error_counts'].get('missing', 0)}/{len(truth)}）")
    check("等级=未通过", r["level"] == "未通过", r["level"])

    print("\n=== 5. 只画了主视图（漏 2/3） ===")
    front = [s for s in d["segments"] if s["view"] == "front"]
    r = grade(front, truth)
    print(f"  得分 {r['score']}（{len(front)}/{len(truth)} 条）  {r['error_counts']}")
    check("判为未通过或存疑", r["level"] in ("未通过", "存疑"), r["level"])

    print("\n=== 6. 带容差的近似手绘（每条线偏 1.5mm，应判通过） ===")
    import random
    rnd = random.Random(1)
    approx = []
    for s in truth:
        approx.append({
            "x1": s["x1"] + rnd.uniform(-1.5, 1.5), "y1": s["y1"] + rnd.uniform(-1.5, 1.5),
            "x2": s["x2"] + rnd.uniform(-1.5, 1.5), "y2": s["y2"] + rnd.uniform(-1.5, 1.5),
            "hidden": s["hidden"],
        })
    r = grade(approx, truth, tol=3.0)
    print(f"  得分 {r['score']}  等级 {r['level']}  {r['error_counts']}")
    check("小误差被判通过", r["level"] == "通过", r["level"])

    print(f"\n{'='*52}\n通过 {PASS} / 失败 {FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
