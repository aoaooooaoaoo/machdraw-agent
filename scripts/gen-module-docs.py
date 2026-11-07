#!/usr/bin/env python
"""从代码生成 9 个模块的任务书，带 --check 模式防文档漂移。

为什么要有这个脚本：
    参考作品的任务书会漂移 —— `module1/AGENTS.md` 写知识点字段叫 `type`，
    代码里其实是 `kind`；`module4` 的 AGENTS 至今还是「【待填】」空模板；
    注释写「语料 116 块」实际 163 块。**手写文档必然腐烂。**

    所以我们的任务书由代码生成：字段从 `features/*/index.ts` 与 `types.ts` 抽，
    工具信息从 `app/tools/*.py` 的 ToolSpec 抽。
    `--check` 模式下如果磁盘上的任务书与代码不一致就退出码 1，
    这样可以进 CI，文档就不会再漂。

用法：
    python scripts/gen-module-docs.py           # 生成/更新
    python scripts/gen-module-docs.py --check   # 只校验，不一致退出 1
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "web" / "src"
API = ROOT / "apps" / "api"
OUT = ROOT / "docs" / "模块任务书"

sys.path.insert(0, str(API))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


# ---------------------------------------------------------------- 抽取

def parse_ts_object(src: str) -> dict[str, str]:
    """从 `export default { ... } satisfies X` 里抽出顶层 key: 字面量。"""
    out: dict[str, str] = {}
    for key in ("id", "title", "hint", "order", "autoOpenCanvas", "page"):
        m = re.search(rf"^\s*{key}:\s*(.+?),?\s*$", src, re.M)
        if m:
            out[key] = m.group(1).rstrip(",").strip()
    m = re.search(r"artifactTypes:\s*\[([^\]]*)\]", src)
    if m:
        out["artifactTypes"] = " ".join(x.strip() for x in m.group(1).split(",") if x.strip())
    m = re.search(r"preview:\s*\{([\s\S]*?)\}", src)
    if m:
        # preview 是对象（label + data）；文档里展示 label，而不是变量名
        lm = re.search(r"label:\s*['\"]([^'\"]+)['\"]", m.group(1))
        out["preview"] = lm.group(1) if lm else "有"
    else:
        m = re.search(r"preview:\s*(\w+)", src)
        if m:
            out["preview"] = m.group(1)
    return out


def parse_interfaces(types_src: str) -> dict[str, list[str]]:
    """抽出 types.ts 里所有 interface 的字段行。"""
    out: dict[str, list[str]] = {}
    for m in re.finditer(r"export interface (\w+)\s*\{", types_src):
        name = m.group(1)
        start = m.end()
        depth = 1
        i = start
        while i < len(types_src) and depth:
            if types_src[i] == "{":
                depth += 1
            elif types_src[i] == "}":
                depth -= 1
            i += 1
        body = types_src[start:i - 1]
        fields = []
        for line in body.splitlines():
            s = line.strip()
            if not s or s.startswith("//") or s.startswith("*") or s.startswith("/*"):
                continue
            fields.append(s)
        out[name] = fields
    return out


def load_tools() -> dict[str, dict]:
    """从后端导入 SPECS，拿到真实的 name/label/description/parameters。"""
    try:
        from app.tools import SPECS  # type: ignore
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] 无法导入后端工具（{exc}），工具一节将留空")
        return {}
    out = {}
    # SPECS 是 {name: ToolSpec} 的字典
    specs = SPECS.values() if isinstance(SPECS, dict) else SPECS
    for spec in specs:
        # 该工具实际产出哪个 artifact_type：读它的源文件
        f = API / "app" / "tools" / f"{spec.name}.py"
        arts = []
        if f.exists():
            src = f.read_text(encoding="utf-8")
            arts = re.findall(r'artifact_type="([a-z_0-9]+)"', src)
        out[spec.name] = {
            "label": spec.label,
            "description": (spec.description or "").strip().replace("\n", " "),
            "parameters": sorted((spec.parameters or {}).get("properties", {}).keys()),
            "artifactTypes": sorted(set(arts)),
        }
    return out


# ---------------------------------------------------------------- 渲染

def render(feature_dir: Path, meta: dict, tools: dict, ifaces: dict) -> str:
    fid = meta.get("id", "").strip("'\"")
    title = meta.get("title", "").strip("'\"")
    hint = meta.get("hint", "").strip("'\"")
    arts = [x.strip().strip("'\"") for x in (meta.get("artifactTypes", "") or "").split()]
    order = meta.get("order", "?")
    auto = meta.get("autoOpenCanvas", "false")
    preview = meta.get("preview")
    page = meta.get("page")

    comp = feature_dir / "Canvas.tsx"
    # 组件可能在 modules/<id>/Canvas.tsx
    if not comp.exists():
        alt = WEB / "modules" / fid / "Canvas.tsx"
        if alt.exists():
            comp = alt

    lines: list[str] = []
    lines.append(f"# 模块任务书 · {title}（`{fid}`）")
    lines.append("")
    lines.append("> ⚠️ **本文件由 `scripts/gen-module-docs.py` 从代码生成，请勿手改。**")
    lines.append("> 改契约改代码，再跑一次生成脚本；`--check` 模式会在 CI 里拦住漂移。")
    lines.append("")
    lines.append("## 一、模块身份")
    lines.append("")
    lines.append("| 项 | 值 | 来源 |")
    lines.append("|---|---|---|")
    lines.append(f"| id | `{fid}` | `features/{fid}/index.ts` |")
    lines.append(f"| 显示名 | {title} | 同上 |")
    lines.append(f"| 左栏排序 | {order} | 同上 |")
    lines.append(f"| artifactType | {', '.join(f'`{a}`' for a in arts) or '（无）'} | 同上 |")
    lines.append(f"| 自动展开画布 | {auto} | 同上 |")
    lines.append(f"| 样例数据 | {'有（`preview`）' if preview else '无'} | 同上 |")
    lines.append(f"| 整页模式 | {'有（`page`）' if page else '无'} | 同上 |")
    lines.append(f"| 画布组件 | `{comp.relative_to(ROOT).as_posix()}` | 文件存在性 |")
    lines.append("")
    lines.append("## 二、这个模块干什么")
    lines.append("")
    lines.append(f"{hint}")
    lines.append("")
    lines.append("## 三、后端工具")
    lines.append("")
    mine = {n: t for n, t in tools.items() if set(t["artifactTypes"]) & set(arts)}
    if mine:
        lines.append("| 工具 | 展示文案 | 入参 | 说明 |")
        lines.append("|---|---|---|---|")
        for name, t in sorted(mine.items()):
            params = ", ".join(f"`{p}`" for p in t["parameters"]) or "—"
            lines.append(f"| `{name}` | {t['label']} | {params} | {t['description'][:80]} |")
    else:
        lines.append("_本模块的 artifactType 目前没有专属工具产出（可能由编排器直接构造或尚未接入）。_")
    lines.append("")
    lines.append("## 四、数据形状（从 `lib/types.ts` 抽取）")
    lines.append("")
    shown = False
    for a in arts:
        # 命名约定实测是 `<PascalCase(artifactType)>ArtifactData`
        base = "".join(w.capitalize() for w in a.split("_"))
        cand = [base + "ArtifactData", base + "Data", base]
        for c in cand:
            if c in ifaces:
                shown = True
                lines.append(f"### `{c}`（对应 `{a}`）")
                lines.append("")
                lines.append("```ts")
                lines.append(f"interface {c} {{")
                for f in ifaces[c][:30]:
                    lines.append(f"  {f}")
                lines.append("}")
                lines.append("```")
                lines.append("")
                break
    if not shown:
        lines.append("_`types.ts` 里没有按命名约定找到对应接口，请人工补：")
        lines.append("先用 `grep -n 'export interface' apps/web/src/lib/types.ts` 看清单。_")
        lines.append("")
    lines.append("## 五、验收清单（由脚本按现有检查项生成）")
    lines.append("")
    lines.append("```powershell")
    lines.append("cd apps\\web; npm run build                 # 前端构建（含 tsc 严格检查）")
    lines.append("python apps\\api\\tests\\check_reachability.py  # 工具/画布可达性")
    lines.append("python apps\\api\\tests\\check_tools.py         # 工具自注册三条硬校验")
    lines.append("python verify_all.py                         # 全量 11 项")
    lines.append("```")
    lines.append("")
    lines.append(f"手工验收：左栏点「{title}」→ 空态{'显示「' + preview + '」入口' if preview else '无示例按钮'}；"
                 f"提问产出 `{arts[0] if arts else '?'}` 时画布应{'自动展开' if auto == 'true' else '不抢屏（手动点开）'}。")
    lines.append("")
    lines.append("---")
    lines.append("")
    # 注意：这里不能写生成时间戳，否则 --check 每次都判定不一致。
    # 生成物必须是对同一份代码**确定**的。
    lines.append(f"源：`apps/web/src/features/{fid}/index.ts`（本文件由脚本生成，勿手改）")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    check_only = "--check" in sys.argv
    OUT.mkdir(parents=True, exist_ok=True)

    tools = load_tools()
    types_src = (WEB / "lib" / "types.ts").read_text(encoding="utf-8")
    ifaces = parse_interfaces(types_src)

    feat_root = WEB / "features"
    dirs = sorted([d for d in feat_root.iterdir() if d.is_dir()]) if feat_root.exists() else []
    if not dirs:
        print(f"[error] 没找到任何 feature 目录：{feat_root}")
        return 1

    generated: list[tuple[str, str]] = []
    for d in dirs:
        idx = d / "index.ts"
        if not idx.exists():
            continue
        meta = parse_ts_object(idx.read_text(encoding="utf-8"))
        if not meta.get("id"):
            print(f"[warn] {idx} 没有解析出 id，跳过")
            continue
        body = render(d, meta, tools, ifaces)
        generated.append((f"{meta['id'].strip(chr(39) + chr(34))}.md", body))

    # 索引
    idx_lines = ["# 模块任务书索引", "",
                 "> 全部由 `scripts/gen-module-docs.py` 从代码生成，勿手改。", "",
                 "| 模块 | 文件 | artifactType | 自动展开 | 整页 |", "|---|---|---|---|---|"]
    for name, body in generated:
        m_art = re.search(r"\| artifactType \| (.+?) \|", body)
        m_auto = re.search(r"\| 自动展开画布 \| (\S+) \|", body)
        m_page = re.search(r"\| 整页模式 \| (.+?) \|", body)
        m_title = re.search(r"^# 模块任务书 · (.+?)（", body, re.M)
        idx_lines.append(f"| {m_title.group(1) if m_title else name} | [{name}]({name}) | "
                         f"{m_art.group(1) if m_art else '?'} | {m_auto.group(1) if m_auto else '?'} | "
                         f"{m_page.group(1) if m_page else '?'} |")
    idx_lines.append("")
    idx_lines.append(f"共 {len(generated)} 个模块")
    generated.append(("README.md", "\n".join(idx_lines) + "\n"))

    drift: list[str] = []
    written = 0
    for name, body in generated:
        p = OUT / name
        if check_only:
            if not p.exists():
                drift.append(f"{name}：缺失")
            elif p.read_text(encoding="utf-8") != body:
                drift.append(f"{name}：内容与代码不一致")
        else:
            p.write_text(body, encoding="utf-8")
            written += 1

    if check_only:
        if drift:
            print("[FAIL] 任务书与代码不一致：")
            for d in drift:
                print("  ✗ " + d)
            print("\n修法：python scripts/gen-module-docs.py")
            return 1
        print(f"[OK] {len(generated)} 份任务书与代码一致")
        return 0

    print(f"[OK] 已生成 {written} 份任务书 → {OUT.relative_to(ROOT).as_posix()}")
    for name, _ in generated:
        print("  - " + name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
