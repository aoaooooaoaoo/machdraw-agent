#!/usr/bin/env python
"""从代码生成 9 个模块的任务书，带 --check 模式防文档漂移。

为什么要有这个脚本：
    参考作品的任务书会漂移 —— `module1/AGENTS.md` 写知识点字段叫 `type`，
    代码里其实是 `kind`；`module4` 的 AGENTS 至今还是「【待填】」空模板；
    注释写「语料 116 块」实际 163 块。**手写文档必然腐烂。**

    所以我们的任务书由代码生成，三处真源：
      1. `apps/api/app/state.py` 的 `MODULES`（模块身份、画布类型、工具清单、系统提示词）
      2. `apps/api/app/tools/<name>.py` 的 `TOOL = ToolSpec(...)`（工具名/文案/入参/产出画布）
      3. `apps/web/src/features/<id>/index.ts` + `apps/web/src/lib/types.ts`（画布元数据与数据形状）

    `--check` 模式下如果磁盘上的任务书与代码不一致（缺文件/内容不同/多出孤儿文件）
    就退出码 1，这样可以进 CI（`verify_all.py` 的"模块任务书与代码一致"项），文档就不会再漂。

读法说明（为什么用 AST 而不是直接 import）：
    · 直接 `from app.state import MODULES` 需要 numpy/rag 一整条依赖链，且 `app.tools`
      在某个工具文件尚未落盘时会因底部转发 import 直接 ModuleNotFoundError；
    · 用 `ast` 静态解析 `state.py` 与各 `ToolSpec(...)`，零依赖、不会因为队友正在写
      某个工具而让文档生成失败；`app.tools` 能 import 时优先用它（拿到 pydantic 校验过的值）。

用法：
    apps\\api\\.venv\\Scripts\\python.exe scripts\\gen-module-docs.py           # 生成/更新
    apps\\api\\.venv\\Scripts\\python.exe scripts\\gen-module-docs.py --check   # 只校验，不一致退出 1
（任意 Python 3.8+ 也能跑：脚本只用标准库）
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "web" / "src"
API = ROOT / "apps" / "api"
OUT = ROOT / "docs" / "模块任务书"
SPEC_MD = ROOT / "docs" / "SPEC-课程对象与数据契约.md"

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # pragma: no cover - 老终端
    pass


# ============================================================ 常量与工具函数

#: 画布类型 → types.ts 里数据接口的命名候选（按顺序匹配）。
#: 旧工程是 `<Pascal>ArtifactData`；新工程 calc/plot 用 `CalcData`/`PlotData`。
def iface_candidates(artifact_type: str) -> list[str]:
    base = "".join(w.capitalize() for w in artifact_type.split("_"))
    return [base + "ArtifactData", base + "Data", base]


def _const(node: ast.AST):
    """把 AST 字面量转成 Python 值（只支持文档需要的类型）。"""
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, (ast.List, ast.Tuple)):
        return [_const(x) for x in node.elts]
    if isinstance(node, ast.Dict):
        out = {}
        for k, v in zip(node.keys, node.values):
            kk = _const(k) if k is not None else None
            out[kk] = _const(v)
        return out
    if isinstance(node, ast.JoinedStr):  # f-string：静态解析不出，退化成原文
        return "<f-string>"
    try:
        return ast.unparse(node)
    except Exception:  # pragma: no cover
        return ""


# ============================================================ 真源 1：MODULES

def load_modules() -> tuple[list[dict], list[str]]:
    """从 `apps/api/app/state.py` 静态解出 MODULES（9 条）。"""
    warnings: list[str] = []
    p = API / "app" / "state.py"
    if not p.exists():
        return [], [f"找不到 {p}"]
    tree = ast.parse(p.read_text(encoding="utf-8"))
    modules: list[dict] = []
    for node in ast.walk(tree):
        # 兼容 `MODULES = [...]` 与带类型标注的 `MODULES: list[ModuleManifest] = [...]`
        if isinstance(node, ast.AnnAssign):
            target, value = node.target, node.value
        elif isinstance(node, ast.Assign):
            targets = [t for t in node.targets if isinstance(t, ast.Name) and t.id == "MODULES"]
            if not targets:
                continue
            target, value = targets[0], node.value
        else:
            continue
        if not (isinstance(target, ast.Name) and target.id == "MODULES"):
            continue
        if not isinstance(value, ast.List):
            continue
        for elt in value.elts:
            if not (isinstance(elt, ast.Call) and getattr(elt.func, "id", "") == "ModuleManifest"):
                continue
            kw = {k.arg: _const(k.value) for k in elt.keywords if k.arg}
            modules.append({
                "id": str(kw.get("id") or ""),
                "name": str(kw.get("name") or ""),
                "icon": str(kw.get("icon") or ""),
                "canvas_kinds": [str(x) for x in (kw.get("canvas_kinds") or [])],
                "tools": [str(x) for x in (kw.get("tools") or [])],
                "system_prompt": str(kw.get("system_prompt") or ""),
                "entry_examples": [str(x) for x in (kw.get("entry_examples") or [])],
                "desc": str(kw.get("desc") or ""),
            })
    if not modules:
        warnings.append("`state.py` 里没有解析到任何 ModuleManifest")
    return modules, warnings


# ============================================================ 真源 2：ToolSpec

def _rel(p: Path) -> str:
    """尽量给相对 ROOT 的路径；不在 ROOT 下（例如自测用的临时目录）就返回绝对路径。"""
    try:
        return p.relative_to(ROOT).as_posix()
    except ValueError:
        return p.as_posix()


def _artifact_types_from_src(src: str) -> list[str]:
    return sorted(set(re.findall(r'artifact_type\s*=\s*"([a-z_0-9]+)"', src)))


def load_tools_spec_md() -> dict[str, dict]:
    """从 SPEC §4.3 表格兜底：name → {canvas, desc}（工具文件还没落盘时用）。"""
    out: dict[str, dict] = {}
    if not SPEC_MD.exists():
        return out
    text = SPEC_MD.read_text(encoding="utf-8")
    # 只取 §4.3 那一节（到下一个 "---" 结束），避免误吞 §3.x 的数据字段表
    start = text.find("### 4.3")
    if start < 0:
        return out
    block = text[start:]
    end = block.find("\n---")
    if end >= 0:
        block = block[:end]
    valid_canvas = {"evidence", "calc", "plot", "comparison", "annotation",
                    "quiz", "wrongbook", "graph"}
    for line in block.splitlines():
        # SPEC §4.3 的行格式：| `name` | canvas | 说明 |（canvas 列不一定带反引号）
        m = re.match(r"^\|\s*`([a-z][a-z_0-9]*)`\s*\|\s*`?([a-z_]+)`?\s*\|\s*(.+?)\s*\|\s*$", line)
        if m and m.group(2) in valid_canvas:
            out[m.group(1)] = {"canvas": m.group(2), "desc": m.group(3)}
    return out


def _tools_from_ast() -> dict[str, dict]:
    """静态解析 `app/tools/*.py` 的 `TOOL = ToolSpec(...)`。"""
    out: dict[str, dict] = {}
    tdir = API / "app" / "tools"
    if not tdir.exists():
        return out
    for f in sorted(tdir.glob("*.py")):
        if f.name in ("__init__.py", "base.py", "spec.py") or f.name.startswith("_"):
            continue
        try:
            src = f.read_text(encoding="utf-8")
            tree = ast.parse(src)
        except Exception:  # noqa: BLE001
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            if not any(isinstance(t, ast.Name) and t.id == "TOOL" for t in node.targets):
                continue
            if not (isinstance(node.value, ast.Call) and getattr(node.value.func, "id", "") == "ToolSpec"):
                continue
            kw = {k.arg: _const(k.value) for k in node.value.keywords if k.arg}
            name = str(kw.get("name") or "")
            params = kw.get("parameters") or {}
            props = sorted((params.get("properties") or {}).keys()) if isinstance(params, dict) else []
            out[name] = {
                "name": name,
                "label": str(kw.get("label") or ""),
                "description": str(kw.get("description") or "").strip().replace("\n", " "),
                "parameters": props,
                "artifactTypes": _artifact_types_from_src(src),
                "file": _rel(f),
                "source": "ast",
            }
    return out


def load_tools() -> tuple[dict[str, dict], list[str], list[str]]:
    """工具表：优先 import app.tools（pydantic 校验过的真值），失败则 AST，最后 SPEC 兜底。

    返回 (tools, warnings, infos)：infos 是"生成来源"这类正常信息，不算告警。
    """
    warnings: list[str] = []
    infos: list[str] = []
    tools = _tools_from_ast()

    try:
        sys.path.insert(0, str(API))
        from app.tools import SPECS  # type: ignore

        live = {}
        for name, spec in SPECS.items():
            f = API / "app" / "tools" / f"{name}.py"
            src = f.read_text(encoding="utf-8") if f.exists() else ""
            live[name] = {
                "name": name,
                "label": spec.label,
                "description": (spec.description or "").strip().replace("\n", " "),
                "parameters": sorted((spec.parameters or {}).get("properties", {}).keys()),
                "artifactTypes": _artifact_types_from_src(src),
                "file": _rel(f) if f.exists() else "",
                "source": "import",
            }
        if live:
            tools = live
            infos.append(f"工具表来自 `import app.tools`（{len(live)} 个，pydantic 校验过的真值）")
        else:
            warnings.append("`app.tools` 导入成功但 `SPECS` 为空，已退回 AST 静态解析")
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"`import app.tools` 失败（{type(exc).__name__}: {exc}），已退回 AST 静态解析")
    finally:
        if str(API) in sys.path:
            sys.path.remove(str(API))

    # SPEC 兜底 / 交叉核对：补齐代码里还没落盘的"计划工具"
    planned = load_tools_spec_md()
    for name, meta in planned.items():
        if name in tools:
            continue
        warnings.append(f"工具 `{name}` 尚未落盘（按 SPEC §4.3 记为计划项）")
        tools[name] = {
            "name": name,
            "label": name,
            "description": meta["desc"],
            "parameters": [],
            "artifactTypes": [meta["canvas"]],
            "file": "",
            "source": "spec",
        }
        tools[name]["planned"] = True
    return tools, warnings, infos


# ============================================================ 真源 3：前端

def parse_ts_object(src: str) -> dict[str, str]:
    """从 `export default { ... } satisfies CanvasFeature` 里抽顶层 key: 字面量。"""
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
        lm = re.search(r"label:\s*['\"]([^'\"]+)['\"]", m.group(1))
        out["preview"] = lm.group(1) if lm else "有"
    else:
        m = re.search(r"preview:\s*(\w+)", src)
        if m:
            out["preview"] = m.group(1)
    return out


def load_features() -> list[dict]:
    """扫描 `features/<id>/index.ts`（画布自注册元数据）。"""
    out: list[dict] = []
    feat_root = WEB / "features"
    if not feat_root.exists():
        return out
    for d in sorted(p for p in feat_root.iterdir() if p.is_dir()):
        idx = d / "index.ts"
        if not idx.exists():
            continue
        meta = parse_ts_object(idx.read_text(encoding="utf-8"))
        fid = (meta.get("id") or "").strip("'\"")
        if not fid:
            continue
        arts = [x.strip().strip("'\"") for x in (meta.get("artifactTypes") or "").split()]
        comp = WEB / "modules" / fid / "Canvas.tsx"
        if not comp.exists():
            comp = d / "Canvas.tsx"
        out.append({
            "id": fid,
            "dir": d.name,
            "title": (meta.get("title") or "").strip("'\""),
            "hint": (meta.get("hint") or "").strip("'\""),
            "order": (meta.get("order") or "?").strip().rstrip(","),
            "autoOpen": (meta.get("autoOpenCanvas") or "false").strip().rstrip(","),
            "preview": meta.get("preview"),
            "page": meta.get("page"),
            "artifactTypes": arts,
            "component": comp.relative_to(ROOT).as_posix() if comp.exists() else "",
            "index": idx.relative_to(ROOT).as_posix(),
            "id_matches_dir": fid == d.name,
        })
    out.sort(key=lambda f: int(re.sub(r"\D", "", f["order"]) or 999))
    return out


def parse_interfaces(types_src: str) -> dict[str, list[str]]:
    """抽出 types.ts 里所有 interface 的字段行（含嵌套）。"""
    out: dict[str, list[str]] = {}
    for m in re.finditer(r"export interface (\w+)\s*\{", types_src):
        name = m.group(1)
        start = m.end()
        depth, i = 1, start
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


# ============================================================ 渲染

def _code(s: str) -> str:
    return "`" + s + "`"


def render_module(m: dict, tools: dict, features: list[dict], ifaces: dict) -> str:
    fid = m["id"]
    name = m["name"]
    kinds = m["canvas_kinds"]
    feat_by_type: dict[str, dict] = {}
    for f in features:
        for a in f["artifactTypes"]:
            feat_by_type[a] = f
    my_feats = [feat_by_type[k] for k in kinds if k in feat_by_type]
    missing_kinds = [k for k in kinds if k not in feat_by_type]

    L: list[str] = []
    L.append(f"# 模块任务书 · {name}（`{fid}`）")
    L.append("")
    L.append("> ⚠️ **本文件由 `scripts/gen-module-docs.py` 从代码生成，请勿手改。**")
    L.append("> 改契约改代码（`app/state.py` 的 `MODULES` / `app/tools/<name>.py` / "
             "`features/<id>/index.ts` / `lib/types.ts`），再跑一次生成脚本；"
             "`--check` 模式会在 CI 里拦住漂移。")
    L.append("")

    # ---- 一、身份
    L.append("## 一、模块身份")
    L.append("")
    L.append("| 项 | 值 | 来源 |")
    L.append("|---|---|---|")
    L.append(f"| id | `{fid}` | `apps/api/app/state.py` · `MODULES` |")
    L.append(f"| 显示名 | {name} | 同上 |")
    L.append(f"| 图标 | `{m['icon'] or '（未设置）'}` | 同上（须存在于 `shell/Icons.tsx`） |")
    L.append(f"| 画布类型 | {'、'.join(_code(k) for k in kinds) or '（无）'} | 同上 · `canvas_kinds` |")
    L.append(f"| 工具 | {'、'.join(_code(t) for t in m['tools']) or '（无）'} | 同上 · `tools` |")
    if my_feats:
        L.append("| 前端画布 | " + "、".join(
            f"{f['title']}（`{f['id']}`，order {f['order']}）" for f in my_feats) + " | `features/*/index.ts` |")
    else:
        L.append("| 前端画布 | ⚠️ 无对应 feature | `features/*/index.ts` |")
    L.append(f"| 入口示例 | {len(m['entry_examples'])} 条 | `state.py` · `entry_examples` |")
    L.append("")
    L.append(f"**一句话职责**：{m['desc'] or '（`desc` 未填写）'}")
    L.append("")

    # ---- 二、系统提示词
    L.append("## 二、系统提示词（`system_prompt`，拼进 LLM system 消息）")
    L.append("")
    if m["system_prompt"]:
        L.append("```text")
        L.append(m["system_prompt"])
        L.append("```")
        L.append("")
        L.append("> mock 模式（无 key）不使用系统提示词；只在真实模型路径由 "
                 "`llm.generate(..., persona=...)` 拼进去。")
    else:
        L.append("_（本模块未设置 `system_prompt`，走全局默认提示词。）_")
    L.append("")

    # ---- 三、画布
    L.append("## 三、画布（artifactType → feature → 组件）")
    L.append("")
    if not kinds:
        L.append("_本模块不声明画布。_")
    else:
        L.append("| artifactType | feature id | 画布标题 | order | 自动展开 | 整页 | 组件 | 数据接口 |")
        L.append("|---|---|---|---|---|---|---|---|")
        for k in kinds:
            f = feat_by_type.get(k)
            iface = ""
            for c in iface_candidates(k):
                if c in ifaces:
                    iface = _code(c)
                    break
            if f:
                L.append(f"| `{k}` | `{f['id']}` | {f['title']} | {f['order']} | "
                         f"{f['autoOpen']} | {'有' if f['page'] else '无'} | "
                         f"{_code(f['component']) if f['component'] else '⚠️ 缺'} | {iface or '⚠️ 缺'} |")
            else:
                L.append(f"| `{k}` | ⚠️ 未注册 | — | — | — | — | — | {iface or '⚠️ 缺'} |")
        L.append("")
        if missing_kinds:
            L.append(f"> ⚠️ 以下 artifactType 没有对应 feature（前端会回落占位画布）："
                     + "、".join(_code(x) for x in missing_kinds))
            L.append("")
        if my_feats:
            L.append("**空态示例**：")
            L.append("")
            for f in my_feats:
                L.append(f"- `{f['id']}`：" + (f"「{f['preview']}」按钮（`preview.label`）"
                                               if f["preview"] else "无示例按钮（未声明 `preview`）"))
            L.append("")

    # ---- 四、工具
    L.append("## 四、工具（本模块 `tools` 清单逐个核对）")
    L.append("")
    if not m["tools"]:
        L.append("_本模块不直接调用工具（可能由编排器特殊链路构造 artifact）。_")
    else:
        L.append("| 工具 | 展示文案 | 产出画布 | 入参 | 实现 | 说明 |")
        L.append("|---|---|---|---|---|---|")
        for t in m["tools"]:
            info = tools.get(t)
            if not info:
                L.append(f"| `{t}` | — | — | — | ❌ 未找到（既不在代码也不在 SPEC） | — | |".rstrip(" |"))
                continue
            arts = "、".join(_code(a) for a in info["artifactTypes"]) or "—"
            params = "、".join(_code(p) for p in info["parameters"]) or "—"
            if info.get("planned"):
                status = "⏳ 计划项（SPEC）"
            elif info["source"] == "spec":
                status = "⏳ SPEC 计划项"
            else:
                status = "✅ 已注册"
            desc = info["description"][:90] + ("…" if len(info["description"]) > 90 else "")
            L.append(f"| `{t}` | {info['label']} | {arts} | {params} | {status} | {desc} |")
        L.append("")
        planned = [t for t in m["tools"] if tools.get(t, {}).get("planned")]
        if planned:
            L.append("> ⏳ 标记的工具文件尚未落盘，任务书按 SPEC §4.3 记录；落地后重跑本脚本即可自动转 ✅。")
            L.append("")

    # ---- 五、数据形状
    L.append("## 五、数据形状（`apps/web/src/lib/types.ts` 抽取）")
    L.append("")
    shown = 0
    for k in kinds:
        for c in iface_candidates(k):
            if c in ifaces:
                shown += 1
                L.append(f"### `{c}`（对应 `{k}`）")
                L.append("")
                L.append("```ts")
                L.append(f"export interface {c} {{")
                for line in ifaces[c][:40]:
                    L.append("  " + line)
                L.append("}")
                L.append("```")
                L.append("")
                break
    if not shown:
        L.append("_`types.ts` 里没有按命名约定找到对应接口。_")
        L.append("")

    # ---- 六、入口示例
    L.append("## 六、入口示例（`entry_examples`，空态 chips 直接发送）")
    L.append("")
    if m["entry_examples"]:
        for ex in m["entry_examples"]:
            L.append(f"- {ex}")
    else:
        L.append("_（未配置入口示例。）_")
    L.append("")

    # ---- 七、验收
    L.append("## 七、验收清单")
    L.append("")
    L.append("```powershell")
    L.append("cd apps\\web; npm run build                       # 前端构建（tsc 严格检查）")
    L.append("apps\\api\\.venv\\Scripts\\python.exe apps\\api\\tests\\check_tools.py         # 工具自注册（11 个）")
    L.append("apps\\api\\.venv\\Scripts\\python.exe apps\\api\\tests\\check_reachability.py  # 模块/工具/画布可达性")
    L.append("apps\\api\\.venv\\Scripts\\python.exe apps\\api\\tests\\smoke.py              # 端到端冒烟")
    L.append("apps\\api\\.venv\\Scripts\\python.exe scripts\\gen-module-docs.py --check     # 本文档与代码一致")
    L.append("```")
    L.append("")
    first_art = kinds[0] if kinds else "?"
    hint_parts = [f"左栏点「{name}」"]
    if my_feats:
        hint_parts.append(f"空态应显示 {len(my_feats)} 个画布的示例入口"
                          if any(f["preview"] for f in my_feats) else "空态列出声明画布")
    hint_parts.append(f"提问产出 `{first_art}` 时画布按 `autoOpenCanvas` 行为"
                      + ("自动展开" if any(f["autoOpen"] == "true" for f in my_feats) else "不抢屏"))
    L.append("手工验收：" + "；".join(hint_parts) + "。")
    L.append("")
    L.append("---")
    L.append("")
    # 注意：不能写生成时间戳，否则 --check 每次都判定不一致。生成物必须确定性。
    L.append(f"源：`apps/api/app/state.py` · `MODULES[{fid}]`；"
             f"画布：`apps/web/src/features/*/index.ts`；"
             f"工具：`apps/api/app/tools/*.py` 的 `ToolSpec`（本文件由脚本生成，勿手改）")
    L.append("")
    return "\n".join(L)


def render_readme(modules: list[dict], tools: dict, features: list[dict],
                  warnings: list[str], infos: list[str]) -> str:
    # 画布总表
    feat_by_type: dict[str, dict] = {}
    for f in features:
        for a in f["artifactTypes"]:
            feat_by_type[a] = f
    all_kinds: list[str] = []
    for m in modules:
        for k in m["canvas_kinds"]:
            if k not in all_kinds:
                all_kinds.append(k)

    def _kind_order(k: str) -> int:
        f = feat_by_type.get(k)
        if not f:
            return 9999
        try:
            return int(re.sub(r"\D", "", f["order"]) or 9998)
        except Exception:  # noqa: BLE001
            return 9998

    all_kinds.sort(key=_kind_order)

    L: list[str] = []
    L.append("# 模块任务书索引")
    L.append("")
    L.append("> 全部由 `scripts/gen-module-docs.py` 从代码生成，**勿手改**。")
    L.append("> 校验：`apps\\api\\.venv\\Scripts\\python.exe scripts\\gen-module-docs.py --check`"
             "（漂移时退出码 1，已接入 `verify_all.py`）。")
    L.append("")
    L.append("## 一、九个模块")
    L.append("")
    L.append("| # | 模块 | 文件 | 画布类型 | 工具 | 前端 feature |")
    L.append("|---|---|---|---|---|---|")
    for i, m in enumerate(modules, 1):
        feats = [feat_by_type[k]["id"] for k in m["canvas_kinds"] if k in feat_by_type]
        L.append(f"| {i} | {m['name']} | [{m['id']}.md]({m['id']}.md) | "
                 f"{'、'.join(_code(k) for k in m['canvas_kinds']) or '—'} | "
                 f"{'、'.join(_code(t) for t in m['tools']) or '—'} | "
                 f"{'、'.join(_code(x) for x in feats) or '⚠️ 无'} |")
    L.append("")
    L.append(f"共 {len(modules)} 个模块（真源：`apps/api/app/state.py` 的 `MODULES`）。")
    L.append("")

    L.append("## 二、八类画布 → 前端 feature")
    L.append("")
    L.append("| artifactType | feature | 画布标题 | order | 自动展开 | 整页 | 组件 |")
    L.append("|---|---|---|---|---|---|---|")
    for k in all_kinds:
        f = feat_by_type.get(k)
        if f:
            L.append(f"| `{k}` | `{f['id']}` | {f['title']} | {f['order']} | {f['autoOpen']} | "
                     f"{'有' if f['page'] else '无'} | {_code(f['component']) if f['component'] else '⚠️ 缺'} |")
        else:
            L.append(f"| `{k}` | ⚠️ 未注册 | — | — | — | — | — |")
    L.append("")
    L.append(f"共 {len(all_kinds)} 类画布被模块引用；前端已注册 {len(features)} 个 feature。")
    L.append("")

    L.append("## 三、十一个工具")
    L.append("")
    L.append("| 工具 | 展示文案 | 产出画布 | 入参个数 | 实现 | 源文件 |")
    L.append("|---|---|---|---|---|---|")
    for name in sorted(tools):
        info = tools[name]
        arts = "、".join(_code(a) for a in info["artifactTypes"]) or "—"
        status = "⏳ 计划项" if info.get("planned") else "✅ 已注册"
        L.append(f"| `{name}` | {info['label']} | {arts} | {len(info['parameters'])} | {status} | "
                 f"{_code(info['file']) if info['file'] else '—'} |")
    L.append("")
    live = sum(1 for t in tools.values() if not t.get("planned"))
    L.append(f"共 {len(tools)} 个工具：已注册 {live}，计划项 {len(tools) - live}"
             "（真源：`app/tools/<name>.py` 的 `ToolSpec`；计划项来自 SPEC §4.3）。")
    L.append("")

    L.append("## 四、一键验收")
    L.append("")
    L.append("```powershell")
    L.append("apps\\api\\.venv\\Scripts\\python.exe scripts\\gen-module-docs.py            # 重新生成全部任务书")
    L.append("apps\\api\\.venv\\Scripts\\python.exe scripts\\gen-module-docs.py --check    # 只校验（CI 用）")
    L.append("apps\\api\\.venv\\Scripts\\python.exe verify_all.py                          # 全量验收")
    L.append("```")
    L.append("")
    if infos or warnings:
        L.append("## 五、生成信息与告警")
        L.append("")
        for i in infos:
            L.append(f"- ℹ️ {i}")
        for w in warnings:
            L.append(f"- ⚠️ {w}")
        L.append("")
    L.append("---")
    L.append("")
    L.append("源：`apps/api/app/state.py`、`apps/api/app/tools/*.py`、`apps/web/src/features/*/index.ts`、"
             "`apps/web/src/lib/types.ts`。")
    L.append("")
    return "\n".join(L)


# ============================================================ 主流程

def main() -> int:
    check_only = "--check" in sys.argv
    quiet = "--quiet" in sys.argv

    modules, warnings = load_modules()
    tools, tool_warnings, infos = load_tools()
    warnings.extend(tool_warnings)
    features = load_features()
    if not features:
        warnings.append(f"没找到任何 feature 目录：{WEB / 'features'}")
    types_src = (WEB / "lib" / "types.ts").read_text(encoding="utf-8") if (WEB / "lib" / "types.ts").exists() else ""
    if not types_src:
        warnings.append("`apps/web/src/lib/types.ts` 缺失，数据形状一节将为空")
    ifaces = parse_interfaces(types_src)

    if not modules:
        print("[error] 没有解析到任何模块（检查 apps/api/app/state.py 的 MODULES）")
        return 1

    # 一致性自检（只告警，不阻断生成）
    for f in features:
        if not f["id_matches_dir"]:
            warnings.append(f"feature `{f['id']}` 与目录名 `{f['dir']}` 不一致（registry 会跳过该模块）")
        if not f["component"]:
            warnings.append(f"feature `{f['id']}` 找不到 Canvas 组件")
    registered = {t for t in tools}
    for m in modules:
        for t in m["tools"]:
            if t not in registered:
                warnings.append(f"模块 `{m['id']}` 引用了不存在的工具 `{t}`")

    generated: list[tuple[str, str]] = []
    for m in modules:
        generated.append((f"{m['id']}.md", render_module(m, tools, features, ifaces)))
    generated.append(("README.md", render_readme(modules, tools, features, warnings, infos)))

    OUT.mkdir(parents=True, exist_ok=True)
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

    # 孤儿文件（模块被删/改名后残留的旧任务书）
    expected = {n for n, _ in generated}
    extra = sorted(p.name for p in OUT.glob("*.md") if p.name not in expected)
    if extra:
        msg = "多出未生成的旧任务书：" + "、".join(extra)
        if check_only:
            drift.append(msg)
        else:
            warnings.append(msg + "（请确认后删除）")

    if check_only:
        if drift:
            print("[FAIL] 任务书与代码不一致：")
            for d in drift:
                print("  ✗ " + d)
            print("\n修法：apps\\api\\.venv\\Scripts\\python.exe scripts\\gen-module-docs.py")
            return 1
        print(f"[OK] {len(generated)} 份任务书与代码一致"
              f"（{len(modules)} 模块 / {len([f for f in features])} feature / {len(tools)} 工具）")
        for w in warnings:
            print("  · " + w)
        return 0

    print(f"[OK] 已生成 {written} 份 → {OUT.relative_to(ROOT).as_posix()}")
    for name, _ in generated:
        print("  - " + name)
    if warnings and not quiet:
        print("\n[告警]")
        for w in warnings:
            print("  · " + w)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
