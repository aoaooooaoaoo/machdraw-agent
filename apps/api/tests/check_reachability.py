"""可达性检查：每个工具/画布是否真的在对话链路里被用到。

动机来自参考源码的教训：它把「热处理数值模型」写进项目书当创新点，
但代码里被 `_RETIRED` 滤掉了，只活在测试里 —— 核心卖点在产品中根本没被调用。

本脚本检查三件事：
1. 注册的工具里，哪些在 `_plan()` / 特殊分支里从来不会被选中（= 死工具）
2. 工具产出的 artifact_type，前端有没有画布认领（= 悬空类型）
3. 前端注册的画布，后端有没有工具能产出（= 空画布）

用法：python apps/api/tests/check_reachability.py
退出码 0 = 全通；1 = 有死工具/悬空类型
"""
from __future__ import annotations

import inspect
import json
import re
import sys
from pathlib import Path

API = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API))

from app import orchestrator as orch  # noqa: E402
from app.tools import TOOLS  # noqa: E402

WEB_SRC = API.parent / "web" / "src"
failures: list[str] = []


def source_of(mod) -> str:
    return inspect.getsource(mod)


print("=" * 74)
print("可达性检查：工具 / 画布是否真的被用上")
print("=" * 74)

orch_src = source_of(orch)

# ---------- 1. 工具是否可达 ----------
print(f"\n[1] 工具可达性（共 {len(TOOLS)} 个）")
dead: list[str] = []
for name in TOOLS:
    # 在编排器源码里出现该工具名即视为可达（_plan 返回的 steps 会带 name）
    if f'"{name}"' in orch_src or f"'{name}'" in orch_src:
        print(f"  OK   {name}")
    else:
        print(f"  DEAD {name}   ← 编排器里从不选它")
        dead.append(name)
if dead:
    failures.append(f"{len(dead)} 个工具在编排器里不可达：{', '.join(dead)}")

# ---------- 2. 工具产出的 artifact_type 是否有画布认领 ----------
print("\n[2] artifact_type 认领检查")
# 工具自注册后，artifact_type 分散在各 tools/*.py 里（不再集中在 __init__.py），
# 所以这里扫描整个 tools 目录，否则会误报"后端可产出 0 种"。
tools_dir = API / "app" / "tools"
tools_src = "\n".join(
    path.read_text(encoding="utf-8") for path in sorted(tools_dir.glob("*.py"))
)

# 从工具源码里抓 artifact_type="xxx"
produced = set(re.findall(r'artifact_type="([a-z_0-9]+)"', tools_src))
# 编排器里也有直接构造 artifact 的
produced |= set(re.findall(r'E\.artifact\(\s*"([a-z_0-9]+)"', orch_src))
produced = sorted(produced)
print(f"  后端可产出 {len(produced)} 种：{', '.join(produced)}")

# ★ 画布现在是自注册的：扫 features/*/index.ts 的 artifactTypes，
#   不再扫 modules/registry.ts 的硬编码 map（strangler 改造后它已经没有 map 了）。
features_dir = WEB_SRC / "features"
registered: set[str] = set()
owners: dict[str, str] = {}
feature_count = 0
for feature_index in sorted(features_dir.glob("*/index.ts")):
    feature_id = feature_index.parent.name
    feature_count += 1
    text = feature_index.read_text(encoding="utf-8")

    id_match = re.search(r"\bid:\s*['\"]([^'\"]+)['\"]", text)
    if not id_match:
        failures.append(f"{feature_id}/index.ts 没有声明 id")
    elif id_match.group(1) != feature_id:
        failures.append(
            f"{feature_id}/index.ts 的 id='{id_match.group(1)}' 与目录名不一致（registry 会跳过它）"
        )

    types_match = re.search(r"artifactTypes\s*:\s*\[([^\]]*)\]", text, re.S)
    if not types_match:
        failures.append(f"{feature_id}/index.ts 没有声明 artifactTypes")
        continue
    types = re.findall(r"['\"]([a-z_0-9]+)['\"]", types_match.group(1))
    if not types:
        failures.append(f"{feature_id}/index.ts 的 artifactTypes 为空")
    for artifact_type in types:
        if artifact_type in owners:
            failures.append(
                f"artifactType '{artifact_type}' 被 {owners[artifact_type]} 与 {feature_id} 重复注册"
            )
        owners[artifact_type] = feature_id
        registered.add(artifact_type)

print(f"  前端 features 注册 {feature_count} 个 feature / {len(registered)} 个 artifactType")
unclaimed = [t for t in produced if t not in registered]
for t in produced:
    print(f"  {'OK  ' if t not in unclaimed else '悬空'} {t}")
if unclaimed:
    failures.append(f"{len(unclaimed)} 个 artifact_type 没有画布认领：{', '.join(unclaimed)}")

# ---------- 3. 画布是否有后端能产出 ----------
print("\n[3] 空画布检查（前端注册了但后端永不产出）")
reg_keys = sorted(registered)
empty = [k for k in reg_keys if k not in produced]
for k in reg_keys:
    print(f"  {'OK  ' if k not in empty else '空  '} {k}")
if empty:
    failures.append(f"{len(empty)} 个画布后端永不产出：{', '.join(empty)}")



# ---------- 4. 字符串引用检查（补上队友指出的盲区） ----------
# `_plan()` 返回的 steps 是字典，但 main.py / modules/ 里还有 TOOLS["xxx"] 这种直接按名取用。
# 名字改了而这里没改，运行到那行才炸 —— 静态扫出来提前报。
print("\n[4] TOOLS[...] 字符串引用检查")
APP = API / "app"
refs: dict[str, list[str]] = {}
for py_file in sorted(APP.rglob("*.py")):
    if "__pycache__" in str(py_file):
        continue
    try:
        src = py_file.read_text(encoding="utf-8")
    except OSError:
        continue
    for m in re.finditer(r"""TOOLS\[\s*["']([a-z_0-9]+)["']\s*\]""", src):
        refs.setdefault(m.group(1), []).append(py_file.relative_to(API).as_posix())

bad_refs = {k: v for k, v in refs.items() if k not in TOOLS}
for name in sorted(refs):
    where = ", ".join(sorted(set(refs[name])))
    print(f"  {'OK  ' if name in TOOLS else 'BAD '} {name:20} 引用于 {where}")
if bad_refs:
    failures.append(f"引用了不存在的工具：{', '.join(bad_refs)}")
else:
    print(f"  共 {len(refs)} 个工具被按名引用，全部存在")


# ---------- 汇总 ----------
print("\n" + "=" * 74)
if failures:
    print("发现问题：")
    for f in failures:
        print("  ✗ " + f)
    sys.exit(1)
print(f"全部通过：{len(TOOLS)} 工具可达 · {len(produced)} artifact_type 均有认领 · "
      f"{len(reg_keys)} 画布均有产出")
sys.exit(0)
