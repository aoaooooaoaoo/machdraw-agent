"""生成 10 组辨析对比图 SVGs + pairs.jsonl，并做 XML / JSON / 规范校验。

用法（在项目根目录）：
    D:\\python\\python.exe kb\\figures\\pairs\\_tools\\build_pairs.py            # 生成 + 校验
    D:\\python\\python.exe kb\\figures\\pairs\\_tools\\build_pairs.py --check    # 只校验已有文件
    D:\\python\\python.exe kb\\figures\\pairs\\_tools\\build_pairs.py --png      # 另外渲染 QA 预览图

校验项：
  1. 每个 SVG 用 xml.dom.minidom 解析（非法 XML / 重复属性在这里炸）
  2. 根元素 svg + xmlns / viewBox=0 0 760 420 + width/height=100%
  3. 不允许白色填充（背景必须透明）、不允许 currentColor（本题要求写死 #1f2937）
  4. 每个 <text> 必须带 font-family；图元数、文字数、字节数逐个打印
  5. 每个图形区（data-panel=a/b）内的差异标号数量必须等于 differences 条数，
     且编号 1..n 齐全 —— 保证“同一差异点在两图中同号”
  6. 图例行 ≤4 条，编号行与 differences 一一对应
  7. pairs.jsonl 每行 json.loads、pair_id 唯一、字段齐全、answers 合法
  8. kp_ids 必须能在 kb/knowledge/kp.jsonl 查到，chapter 至少与其中一个 kp 的章一致
"""
from __future__ import annotations

import json
import re
import sys
import xml.dom.minidom as minidom
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAIR_DIR = HERE.parent                 # kb/figures/pairs
FIG_DIR = PAIR_DIR.parent              # kb/figures
KB_DIR = FIG_DIR.parent                # kb
ROOT = KB_DIR.parent
sys.path.insert(0, str(HERE))

import pairs_defs  # noqa: E402

JSONL = FIG_DIR / "pairs.jsonl"
SHAPE_TAGS = {"line", "rect", "circle", "path", "polyline", "polygon", "ellipse"}
BAD_FILLS = ('fill="#fff"', 'fill="#ffffff"', 'fill="white"', 'fill="#FFF"')
REQUIRED_A = {"label", "caption", "正确性"}


def kp_index() -> dict:
    rows = [
        json.loads(line)
        for line in (KB_DIR / "knowledge" / "kp.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return {r["kp_id"]: r for r in rows}


def panel_diffs(raw: str, key: str) -> list[int]:
    """取出某个图形区内的差异标号（circle 元素上的 data-diff）。"""
    m = re.search(rf'<g data-panel="{key}".*?</g>', raw, re.S)
    if not m:
        return []
    return [int(x) for x in re.findall(r'class="diff-marker" data-diff="(\d+)"', m.group(0))]


def validate_svg(pid: str, path: Path, n_diff: int) -> dict:
    raw = path.read_text(encoding="utf-8")
    info = {"pair_id": pid, "file": path.name, "bytes": path.stat().st_size, "errors": []}
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
    if root.getAttribute("viewBox") != "0 0 760 420":
        info["errors"].append(f"viewBox 不是 0 0 760 420：{root.getAttribute('viewBox')}")
    if root.getAttribute("width") != "100%" or root.getAttribute("height") != "100%":
        info["errors"].append("width/height 不是相对值 100%")

    shapes = texts = 0

    def walk(node):
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
    if any("font-family" not in el.toxml() for el in root.getElementsByTagName("text")):
        info["errors"].append("有 <text> 缺 font-family")
    hit = [b for b in BAD_FILLS if b in raw]
    if hit:
        info["errors"].append(f"出现白色填充：{hit}")
    if "currentColor" in raw:
        info["errors"].append("出现 currentColor（本题要求线条写死 #1f2937）")
    # 线型必须是国标那三种之一，别自创 dasharray
    ok_dash = {"6 4", "18 4 3 4", "20 4 3 4 3 4"}
    bad_dash = {d for d in re.findall(r'stroke-dasharray="([^"]+)"', raw)} - ok_dash
    if bad_dash:
        info["errors"].append(f"非国标 dasharray：{sorted(bad_dash)}")
    # 线宽只用 0.8 / 1.2 / 2
    bad_w = {w for w in re.findall(r'stroke-width="([^"]+)"', raw)} - {"0.8", "1", "1.2", "2"}
    if bad_w:
        info["errors"].append(f"非约定线宽：{sorted(bad_w)}")

    # 差异标号：两个图形区各 n 个，编号齐全
    for key in ("a", "b"):
        got = sorted(panel_diffs(raw, key))
        want = list(range(1, n_diff + 1))
        if got != want:
            info["errors"].append(f"图形区 {key} 的标号是 {got}，应为 {want}")
    # 图例行（只看 data-legend 分组里的编号行）
    m = re.search(r'<g data-legend="1">(.*?)</g>', raw, re.S)
    leg_block = m.group(1) if m else ""
    n_leg_num = len(re.findall(r'<text[^>]*data-diff="[1-9]"', leg_block))
    if n_leg_num != n_diff:
        info["errors"].append(f"图例编号行 {n_leg_num} 条，differences 有 {n_diff} 条")
    if shapes > 90:
        info["errors"].append(f"图形元素 {shapes} 个，超过 90（成对图上限定 90）")

    info.update(viewBox=root.getAttribute("viewBox"), shape_count=shapes,
                text_count=texts, n_diff=n_diff)
    return info


def validate_record(rec: dict, kps: dict) -> list[str]:
    err: list[str] = []
    need = {"pair_id", "file", "title", "module", "chapter", "kp_ids", "a", "b",
            "differences", "question", "license", "source"}
    missing = need - set(rec)
    if missing:
        err.append(f"{rec.get('pair_id')} 缺字段 {sorted(missing)}")
        return err
    if not rec["pair_id"].startswith("PAIR-"):
        err.append(f"{rec['pair_id']} 编号不以 PAIR- 开头")
    if not rec["file"].startswith("pairs/") or not rec["file"].endswith(".svg"):
        err.append(f"{rec['pair_id']} file 应为 pairs/XXX.svg")
    if rec["file"] != f"pairs/{rec['pair_id']}.svg":
        err.append(f"{rec['pair_id']} file 与 pair_id 不对应")
    for key in ("a", "b"):
        blk = rec[key]
        if not REQUIRED_A.issubset(blk):
            err.append(f"{rec['pair_id']} {key} 缺 {sorted(REQUIRED_A - set(blk))}")
        if blk.get("label") != key.upper():
            err.append(f"{rec['pair_id']} {key}.label 应为 {key.upper()}")
        if blk.get("正确性") not in ("正确", "错误"):
            err.append(f"{rec['pair_id']} {key}.正确性 只能是 正确/错误")
    diffs = rec["differences"]
    if len(diffs) < 2:
        err.append(f"{rec['pair_id']} differences 少于 2 条")
    if [d.get("no") for d in diffs] != list(range(1, len(diffs) + 1)):
        err.append(f"{rec['pair_id']} differences 的 no 必须是 1..n 连续")
    for d in diffs:
        for k in ("no", "name", "a_desc", "b_desc", "why"):
            if not d.get(k):
                err.append(f"{rec['pair_id']} differences[{d.get('no')}] 缺 {k}")
    q = rec["question"]
    for k in ("stem", "options", "answer_index", "explain"):
        if k not in q:
            err.append(f"{rec['pair_id']} question 缺 {k}")
    if not isinstance(q.get("options"), list) or len(q["options"]) < 2:
        err.append(f"{rec['pair_id']} question.options 至少 2 项")
    elif not (0 <= q.get("answer_index", -1) < len(q["options"])):
        err.append(f"{rec['pair_id']} question.answer_index 越界")
    unknown = [k for k in rec["kp_ids"] if k not in kps]
    if unknown:
        err.append(f"{rec['pair_id']} 引用了不存在的 kp_id：{unknown}")
    else:
        chapters = {kps[k]["chapter"] for k in rec["kp_ids"]}
        if rec["chapter"] not in chapters:
            err.append(f"{rec['pair_id']} chapter 与任一 kp 的章都不一致：{sorted(chapters)}")
    return err


def render_png(svg_path: Path, out: Path) -> str | None:
    """QA 预览渲染。注意 cairosvg 遇到根元素上的 style="display:block" 会整张画不出来，
    只在校验渲染时剥掉它 —— 产物 SVG 本身保留该属性（与图库其余图一致）。"""
    try:
        import cairosvg  # noqa: PLC0415
    except Exception as exc:  # noqa: BLE001
        return f"cairosvg 不可用：{exc}"
    raw = svg_path.read_text(encoding="utf-8")
    raw = raw.replace(' style="height:auto;display:block"', "")
    raw = raw.replace('width="100%" height="100%"', 'width="760" height="420"')
    # cairo 不认 system-ui，换成机器上有的中文字体，QA 图才能看出文字压不压线
    raw = raw.replace("system-ui, sans-serif", "Microsoft YaHei")
    out.parent.mkdir(parents=True, exist_ok=True)
    cairosvg.svg2png(bytestring=raw.encode("utf-8"), write_to=str(out), scale=1.6,
                     background_color="white")
    return None


def main() -> int:
    check_only = "--check" in sys.argv
    want_png = "--png" in sys.argv
    kps = kp_index()

    built = []
    for pid, builder in pairs_defs.ALL:
        fig, meta = builder()
        assert fig.pair_id == pid, f"{pid} 的 builder 返回了 {fig.pair_id}"
        built.append((pid, fig, meta))
        if not check_only:
            (PAIR_DIR / f"{pid}.svg").write_text(fig.svg(), encoding="utf-8", newline="\n")

    ids = [b[0] for b in built]
    if len(ids) != len(set(ids)):
        print("[!] pair_id 重复")

    results = []
    rec_errors: list[str] = []
    records: list[dict] = []
    for pid, fig, meta in built:
        n_diff = len(meta["differences"])
        r = validate_svg(pid, PAIR_DIR / f"{pid}.svg", n_diff)
        results.append(r)
        rec = {
            "pair_id": pid,
            "file": f"pairs/{pid}.svg",
            "title": meta["title"],
            "module": pairs_defs.MODULE,
            "chapter": meta["chapter"],
            "kp_ids": meta["kp_ids"],
            "a": meta["a"],
            "b": meta["b"],
            "differences": meta["differences"],
            "question": meta["question"],
            "license": pairs_defs.LIC,
            "source": meta["source"],
        }
        records.append(rec)
        rec_errors += validate_record(rec, kps)

    # ---- 写 pairs.jsonl（无注释、单行一条、UTF-8）----
    if not check_only:
        text = "\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n"
        JSONL.write_text(text, encoding="utf-8", newline="\n")

    # ---- 回读校验：每行 json.loads + pair_id 唯一 ----
    json_errors: list[str] = []
    seen: list[str] = []
    if JSONL.exists():
        for i, line in enumerate(JSONL.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                json_errors.append(f"第 {i} 行是空行")
                continue
            try:
                obj = json.loads(line)
            except Exception as exc:  # noqa: BLE001
                json_errors.append(f"第 {i} 行 json.loads 失败：{exc}")
                continue
            seen.append(obj.get("pair_id"))
    else:
        json_errors.append("pairs.jsonl 不存在")
    dup = {p for p in seen if seen.count(p) > 1}
    if dup:
        json_errors.append(f"pair_id 重复：{sorted(dup)}")
    if len(seen) != len(built):
        json_errors.append(f"pairs.jsonl 有 {len(seen)} 行，生成 {len(built)} 组")

    # ---- 打印 ----
    print(f"{'pair_id':<26}{'字节':>7}{'KB':>7}{'图元':>5}{'文字':>5}{'差异':>5}  viewBox")
    print("-" * 96)
    for r in results:
        print(f"{r['pair_id']:<26}{r['bytes']:>7}{r['bytes']/1024:>7.1f}"
              f"{r.get('shape_count', 0):>5}{r.get('text_count', 0):>5}"
              f"{r.get('n_diff', 0):>5}  {r.get('viewBox', '-')}")
        for e in r["errors"]:
            print(f"    [!] {e}")
    print("-" * 96)
    for e in rec_errors + json_errors:
        print(f"[!] {e}")

    n_err = (sum(len(r["errors"]) for r in results) + len(rec_errors) + len(json_errors))
    print(f"合计 {len(results)} 组，图元 {sum(r.get('shape_count', 0) for r in results)} 个，"
          f"总大小 {sum(r['bytes'] for r in results)/1024:.1f} KB，"
          f"XML/JSON/规范错误 {n_err} 个")

    if want_png:
        qa = HERE / "_qa"
        bad = [render_png(PAIR_DIR / f"{pid}.svg", qa / f"{pid}.png") for pid, _, _ in built]
        bad = [b for b in bad if b]
        print(f"QA 预览图：{len(built) - len(bad)} 张写入 {qa}" if not bad else f"[!] {bad}")
    return 0 if n_err == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
