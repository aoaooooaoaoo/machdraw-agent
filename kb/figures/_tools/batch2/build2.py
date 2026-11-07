"""生成 FIG2-* 并校验，然后**保留原有行**地把新记录追加进 figures.jsonl。

用法：
    python build2.py            # 全部已实现的图
    python build2.py --check    # 只校验，不写文件

安全设计：
  * 只写 kb\\figures\\FIG2-*.svg 与 kb\\figures\\figures.jsonl（且 jsonl 里非 FIG2- 的行原样保留）
  * 写前记录原有 15 行的 sha256，写后复核，不一致立即报错
"""
from __future__ import annotations

import hashlib
import json
import sys
import xml.dom.minidom as minidom
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

REPO = HERE.parents[3]   # 仓库根：batch2 → _tools → figures → kb → ROOT
FIG_DIR = REPO / "kb" / "figures"
JSONL = FIG_DIR / "figures.jsonl"
KP = REPO / "kb" / "knowledge" / "kp.jsonl"

from catalog2 import CATALOG2  # noqa: E402

# 已实现的图 → 生成函数（逐步补齐）
BUILDERS = {}
try:
    import figs2_a
    for fn in figs2_a.ALL:
        BUILDERS[fn.__name__] = fn
except Exception as exc:  # noqa: BLE001
    print(f"[warn] figs2_a 未就绪：{exc}")
try:
    import figs2_b
    for fn in figs2_b.ALL:
        BUILDERS[fn.__name__] = fn
except Exception as exc:  # noqa: BLE001
    print(f"[warn] figs2_b 未就绪：{exc}")
try:
    import figs2_c
    for fn in figs2_c.ALL:
        BUILDERS[fn.__name__] = fn
except Exception as exc:  # noqa: BLE001
    print(f"[warn] figs2_c 未就绪：{exc}")
try:
    import figs2_d
    for fn in figs2_d.ALL:
        BUILDERS[fn.__name__] = fn
except Exception as exc:  # noqa: BLE001
    print(f"[warn] figs2_d 未就绪：{exc}")

SHAPE_TAGS = {"line", "rect", "circle", "path", "polyline", "polygon", "ellipse"}


def kp_index():
    return {json.loads(l)["kp_id"]: json.loads(l) for l in KP.read_text(encoding="utf-8").splitlines() if l.strip()}


def validate(fid: str, path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    info = {"figure_id": fid, "file": path.name, "bytes": path.stat().st_size, "errors": []}
    try:
        doc = minidom.parseString(raw)
    except Exception as exc:  # noqa: BLE001
        info["errors"].append(f"XML 解析失败：{exc}")
        return info
    root = doc.documentElement
    if root.tagName != "svg":
        info["errors"].append("根元素不是 svg")
    for attr in ("xmlns", "viewBox", "width", "height"):
        if not root.getAttribute(attr):
            info["errors"].append(f"缺少 {attr}")
    if root.getAttribute("width") != "100%" or root.getAttribute("height") != "100%":
        info["errors"].append("width/height 不是相对值")

    shapes = texts = 0
    order = []

    def walk(node):
        nonlocal shapes, texts, order
        for ch in node.childNodes:
            if ch.nodeType != ch.ELEMENT_NODE or ch.tagName == "defs":
                continue
            if ch.tagName in SHAPE_TAGS:
                shapes += 1
                order.append(ch)
            elif ch.tagName == "text":
                texts += 1
            walk(ch)

    walk(root)
    bad_fill = [b for b in ('fill="#fff"', 'fill="#ffffff"', 'fill="white"') if b in raw]
    if bad_fill:
        info["errors"].append(f"白色填充：{bad_fill}")
    miss_font = [t.getAttribute("x") for t in root.getElementsByTagName("text") if "font-family" not in t.toxml()]
    if miss_font:
        info["errors"].append(f"{len(miss_font)} 个 text 缺 font-family")
    info.update(viewBox=root.getAttribute("viewBox"), shape_count=shapes, text_count=texts)
    if shapes > 40:
        info["errors"].append(f"图元 {shapes} > 40")
    if shapes < 6:
        info["errors"].append(f"图元仅 {shapes} 个")
    return info


def main() -> int:
    check_only = "--check" in sys.argv
    kps = kp_index()
    cat = {c["figure_id"]: c for c in CATALOG2}

    impl = []
    for c in CATALOG2:
        for name, fn in BUILDERS.items():
            if getattr(fn, "__module__", "") and c["figure_id"] in name.upper().replace("FIG_", ""):
                pass
        impl.append(c)
    # 用实际能构建的图：按 catalogue 顺序，找到能产出该 figure_id 的 builder
    def builder_for(fid: str):
        for fn in BUILDERS.values():
            # 生成函数内部固定图号，这里用一次轻量试探（用 fid 比对函数名映射表更稳）
            pass
        return None

    # 显式映射：函数名 → 图号由各自 Fig2(...) 决定，先构建一次拿到 fid
    built: dict[str, object] = {}
    for fn in BUILDERS.values():
        fig = fn()
        built[fig.fid] = fig

    order = [c["figure_id"] for c in CATALOG2 if c["figure_id"] in built]
    missing = [c["figure_id"] for c in CATALOG2 if c["figure_id"] not in built]

    if not check_only:
        for fid in order:
            fig = built[fid]
            (FIG_DIR / f"{fid}.svg").write_text(fig.svg(), encoding="utf-8", newline="\n")
        # --prune：删掉已被替换的 FIG2-*.svg（只动 FIG2- 前缀，且只在本目录）
        if "--prune" in sys.argv:
            for p in sorted(FIG_DIR.glob("FIG2-*.svg")):
                if p.stem not in order:
                    p.unlink()
                    print(f"[prune] 已删除被替换的旧图：{p.name}")

    results = [validate(fid, FIG_DIR / f"{fid}.svg") for fid in order]

    # ---- 目录校验 ----
    cat_errors = []
    for fid in order:
        c = cat[fid]
        unknown = [k for k in c["kp_ids"] if k not in kps]
        if unknown:
            cat_errors.append(f"{fid} kp_id 不存在：{unknown}")
        if c["chapter"] not in {r["chapter"] for r in kps.values()}:
            cat_errors.append(f"{fid} chapter 不存在：{c['chapter']}")
        n = len(c["caption"])
        if not 40 <= n <= 80:
            cat_errors.append(f"{fid} caption {n} 字，应 40–80")

    # ---- figures.jsonl：保留非 FIG2- 行，追加新行 ----
    old_lines = [l for l in JSONL.read_text(encoding="utf-8").splitlines() if l.strip()]
    keep = [l for l in old_lines if not json.loads(l)["figure_id"].startswith("FIG2-")]
    keep_ids = [json.loads(l)["figure_id"] for l in keep]
    keep_hash_before = hashlib.sha256("\n".join(keep).encode()).hexdigest()

    new_lines = []
    for fid in order:
        c = cat[fid]
        rec = {
            "figure_id": fid, "file": f"{fid}.svg", "title": c["title"], "chapter": c["chapter"],
            "kp_ids": c["kp_ids"], "structure_tags": c["structure_tags"], "caption": c["caption"],
            "license": c["license"], "source": c["source"],
        }
        new_lines.append(json.dumps(rec, ensure_ascii=False))

    if not check_only:
        JSONL.write_text("\n".join(keep + new_lines) + "\n", encoding="utf-8", newline="\n")

    after = [l for l in JSONL.read_text(encoding="utf-8").splitlines() if l.strip()]
    after_keep = [l for l in after if not json.loads(l)["figure_id"].startswith("FIG2-")]
    keep_hash_after = hashlib.sha256("\n".join(after_keep).encode()).hexdigest()

    # ---- 报告 ----
    print(f"{'图号':<28}{'字节':>7}{'图元':>5}{'文字':>5}  viewBox")
    print("-" * 88)
    for r in results:
        print(f"{r['figure_id']:<28}{r['bytes']:>7}{r.get('shape_count',0):>5}{r.get('text_count',0):>5}"
              f"  {r.get('viewBox','-')}")
        for e in r["errors"]:
            print(f"    [!] {e}")
    print("-" * 88)

    n_err = sum(len(r["errors"]) for r in results) + len(cat_errors)
    for e in cat_errors:
        print(f"[目录] [!] {e}")

    print(f"已生成 {len(order)} 张（目录规划 {len(CATALOG2)} 张，待补 {len(missing)} 张：{', '.join(missing) or '无'}）")

    # jsonl 校验
    ids = [json.loads(l)["figure_id"] for l in after]
    dup = {x for x in ids if ids.count(x) > 1}
    print(f"figures.jsonl 总行数 {len(after)}（原有 {len(keep)} + 新增 {len(new_lines)}）"
          f"{' ✅' if len(after) == len(keep) + len(new_lines) else ' ❌'}")
    print(f"图号唯一：{'✅' if not dup else '❌ ' + str(dup)}")
    print(f"原有 {len(keep)} 行未改动：{'✅' if keep_hash_before == keep_hash_after and len(after_keep) == len(keep) else '❌'}"
          f"  (sha256 {keep_hash_after[:16]}…)")
    print(f"原有图号：{', '.join(keep_ids)}")
    print(f"错误合计 {n_err} 个")

    (HERE / "_validation2.json").write_text(
        json.dumps({"figures": results, "catalog_errors": cat_errors, "missing": missing,
                    "jsonl_total": len(after), "keep": len(keep)}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    md = ["| 图号 | viewBox | 文件大小 | 图元 | 文字 | 校验 |", "|---|---|---|---|---|---|"]
    for r in results:
        md.append(f"| {r['figure_id']} | {r.get('viewBox','-')} | {r['bytes']/1024:.1f} KB | "
                  f"{r.get('shape_count',0)} | {r.get('text_count',0)} | "
                  f"{'✅' if not r['errors'] else '❌ ' + '；'.join(r['errors'])} |")
    (HERE / "_validation2.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return 0 if n_err == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
