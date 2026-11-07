"""生成全部教学 SVG + figures.jsonl，并做 XML / 规范校验。

用法：
    D:\\python\\python.exe kb\\figures\\_tools\\build.py           # 生成 + 校验
    D:\\python\\python.exe kb\\figures\\_tools\\build.py --check   # 只校验已有文件

校验项：
  1. xml.dom.minidom 解析（非法 XML、重复属性都会在这里炸）
  2. 根元素必须是 svg 且带 xmlns / viewBox / width=100% / height=100%
  3. 不允许出现白底填充（fill="#fff" / white / #ffffff）—— 深色背景下会糊成一块
  4. 统计：文件大小、图形元素数、文字数、viewBox
  5. figures.jsonl 的 chapter / kp_id 必须能在 kb/knowledge/kp.jsonl 里查到
输出：kb/figures/*.svg、kb/figures/figures.jsonl、_tools/_validation.{json,md}
"""
from __future__ import annotations

import json
import sys
import xml.dom.minidom as minidom
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIG_DIR = HERE.parent
KB_DIR = FIG_DIR.parent
ROOT = KB_DIR.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "apps" / "api"))

import figs_a  # noqa: E402
import figs_b  # noqa: E402
import figs_c  # noqa: E402
from catalog import CATALOG  # noqa: E402

BUILDERS = {fn.__name__: fn for fn in (figs_a.ALL + figs_b.ALL + figs_c.ALL)}
# 图号 → 生成函数（顺序即展示顺序）
ORDER = [
    "FIG-LINETYPE",
    "FIG-SANSHITU-BASE",
    "FIG-SANSHITU-EXAMPLE",
    "FIG-LIUGESHITU",
    "FIG-POUSHI-QUAN",
    "FIG-POUSHI-BAN",
    "FIG-POUSHI-JUBU",
    "FIG-DUANMIAN",
    "FIG-POUMAINXIAN",
    "FIG-GONGCHA-DAI",
    "FIG-YUANHU-LIANJIE",
    "FIG-LUOWEN",
    "FIG-BIAOMIAN",
    "FIG-CHICUN-SIYAOSU",
    "FIG-GONGCHA-PEIJIAN",
]
FUNC_BY_ID = {
    "FIG-LINETYPE": figs_a.fig_linetype,
    "FIG-SANSHITU-BASE": figs_a.fig_sanshitu_base,
    "FIG-SANSHITU-EXAMPLE": figs_a.fig_sanshitu_example,
    "FIG-LIUGESHITU": figs_a.fig_liugeshitu,
    "FIG-POUSHI-QUAN": figs_b.fig_poushi_quan,
    "FIG-POUSHI-BAN": figs_b.fig_poushi_ban,
    "FIG-POUSHI-JUBU": figs_b.fig_poushi_jubu,
    "FIG-DUANMIAN": figs_b.fig_duanmian,
    "FIG-POUMAINXIAN": figs_b.fig_poumainxian,
    "FIG-GONGCHA-DAI": figs_c.fig_gongcha_dai,
    "FIG-YUANHU-LIANJIE": figs_c.fig_yuanhu_lianjie,
    "FIG-LUOWEN": figs_c.fig_luowen,
    "FIG-BIAOMIAN": figs_c.fig_biaomian,
    "FIG-CHICUN-SIYAOSU": figs_c.fig_chicun_siyaosu,
    "FIG-GONGCHA-PEIJIAN": figs_c.fig_gongcha_peijian,
}

SHAPE_TAGS = {"line", "rect", "circle", "path", "polyline", "polygon", "ellipse"}
BAD_FILLS = ('fill="#fff"', 'fill="#ffffff"', 'fill="white"', 'fill="#FFF"', 'fill="#FFFFFF"')


def kp_index() -> dict:
    """kp_id / chapter → 用于校验引用现存。"""
    rows = [
        json.loads(line)
        for line in (KB_DIR / "knowledge" / "kp.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return {r["kp_id"]: r for r in rows}


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
        info["errors"].append(f"根元素不是 svg：{root.tagName}")
    for attr in ("xmlns", "viewBox", "width", "height"):
        if not root.getAttribute(attr):
            info["errors"].append(f"缺少 {attr}")
    if root.getAttribute("width") != "100%" or root.getAttribute("height") != "100%":
        info["errors"].append("width/height 不是相对值 100%")
    vb = root.getAttribute("viewBox").split()
    if len(vb) != 4:
        info["errors"].append(f"viewBox 非法：{root.getAttribute('viewBox')}")

    shapes = texts = 0

    def walk(node):
        """只数正文里的图元：<defs>（剖面线 pattern、箭头 marker）不算图元。"""
        nonlocal shapes, texts
        for child in node.childNodes:
            if child.nodeType != child.ELEMENT_NODE or child.tagName == "defs":
                continue
            if child.tagName in SHAPE_TAGS:
                shapes += 1
            elif child.tagName == "text":
                texts += 1
            walk(child)

    walk(root)
    # 每个 text 必须带 font-family（中文能正常显示的前提）
    missing_font = [
        el.getAttribute("x") for el in root.getElementsByTagName("text") if "font-family" not in el.toxml()
    ]
    if missing_font:
        info["errors"].append(f"{len(missing_font)} 个 <text> 缺 font-family")

    hit = [b for b in BAD_FILLS if b in raw]
    if hit:
        info["errors"].append(f"出现白色填充：{hit}")

    info.update(
        viewBox=root.getAttribute("viewBox"),
        shape_count=shapes,
        text_count=texts,
        has_title=bool(root.getElementsByTagName("title")),
        has_desc=bool(root.getElementsByTagName("desc")),
    )
    if shapes > 40:
        info["errors"].append(f"图形元素 {shapes} 个，超过 40（会显得拥挤）")
    if shapes < 6:
        info["errors"].append(f"图形元素只有 {shapes} 个，恐怕不足以讲清一件事")
    return info


def main() -> int:
    check_only = "--check" in sys.argv
    kps = kp_index()
    cat = {c["figure_id"]: c for c in CATALOG}

    if not check_only:
        for fid in ORDER:
            fig = FUNC_BY_ID[fid]()
            assert fig.fid == fid, f"{fid} 生成器返回了 {fig.fid}"
            (FIG_DIR / f"{fid}.svg").write_text(fig.svg(), encoding="utf-8", newline="\n")

    results = [validate(fid, FIG_DIR / f"{fid}.svg") for fid in ORDER]

    # ---- 目录一致性 ----
    cat_errors = []
    for fid in ORDER:
        c = cat.get(fid)
        if not c:
            cat_errors.append(f"{fid} 缺 catalog 条目")
            continue
        unknown = [k for k in c["kp_ids"] if k not in kps]
        if unknown:
            cat_errors.append(f"{fid} 引用了不存在的 kp_id：{unknown}")
        bad_ch = [fid] if c["chapter"] not in {r["chapter"] for r in kps.values()} else []
        if bad_ch:
            cat_errors.append(f"{fid} chapter 与 kp.jsonl 不一致：{c['chapter']}")
        n = len(c["caption"])
        if not 40 <= n <= 80:
            cat_errors.append(f"{fid} caption 长度 {n} 字，应在 40–80")
    if len(cat) != len(ORDER):
        cat_errors.append(f"catalog 有 {len(cat)} 条，图清单是 {len(ORDER)} 张")

    # ---- 写 figures.jsonl ----
    if not check_only:
        lines = []
        for fid in ORDER:
            c = cat[fid]
            rec = {
                "figure_id": fid,
                "file": f"{fid}.svg",
                "title": c["title"],
                "chapter": c["chapter"],
                "kp_ids": c["kp_ids"],
                "structure_tags": c["structure_tags"],
                "caption": c["caption"],
                "license": c["license"],
                "source": c["source"],
            }
            lines.append(json.dumps(rec, ensure_ascii=False))
        (FIG_DIR / "figures.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    # ---- 报告 ----
    print(f"{'图号':<24}{'字节':>7}{'KB':>7}{'图元':>5}{'文字':>5}  viewBox")
    print("-" * 92)
    ok = True
    for r in results:
        kb = r["bytes"] / 1024
        print(
            f"{r['figure_id']:<24}{r['bytes']:>7}{kb:>7.1f}{r.get('shape_count', 0):>5}"
            f"{r.get('text_count', 0):>5}  {r.get('viewBox', '-')}"
        )
        for e in r["errors"]:
            ok = False
            print(f"    [!] {e}")
    print("-" * 92)
    for e in cat_errors:
        ok = False
        print(f"[目录] [!] {e}")

    n_err = sum(len(r["errors"]) for r in results) + len(cat_errors)
    total_shapes = sum(r.get("shape_count", 0) for r in results)
    print(
        f"合计 {len(results)} 张，图形元素 {total_shapes} 个，"
        f"总大小 {sum(r['bytes'] for r in results)/1024:.1f} KB，错误 {n_err} 个"
    )

    (HERE / "_validation.json").write_text(
        json.dumps({"figures": results, "catalog_errors": cat_errors}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    md = ["| 图号 | 文件 | viewBox | 尺寸 (px) | 文件大小 | 图元 | 文字 | 校验 |",
          "|---|---|---|---|---|---|---|---|"]
    for r in results:
        vb = r.get("viewBox", "-").split()
        size = f"{vb[2]}×{vb[3]}" if len(vb) == 4 else "-"
        md.append(
            f"| {r['figure_id']} | `{r['file']}` | {r.get('viewBox', '-')} | {size} | "
            f"{r['bytes']/1024:.1f} KB | {r.get('shape_count', 0)} | {r.get('text_count', 0)} | "
            f"{'✅' if not r['errors'] else '❌ ' + '；'.join(r['errors'])} |"
        )
    (HERE / "_validation.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
