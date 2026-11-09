#!/usr/bin/env python
"""复刻对照表（老工程 → 新工程）：逐文件/逐契约说清"照搬了什么、重写了什么、为什么"。

数据来源：`docs/00-工程解剖与复刻蓝图.md`（anatomy 实测）+ 本工程改造记录。
用途：评审时回答"你到底复刻了哪些东西"，答辩时说明"哪些是通用骨架、哪些是本课程重写"。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

CONTENT = """# 08 · 复刻对照表（机械制图 agent → 核反应堆物理 agent）

> 老工程：`D:\\桌面\\教学agent\\机械制图agent`（只读参照，未改一行）。
> 新工程：本目录。下表按"照搬 / 改名 / 重写 / 删除"四类逐项交代。

## 1. 一句话结论

同一套架构（FastAPI + SSE + 工具总线自注册 + RAG 双门控 + React 三栏壳 + 画布自注册 + 教师端 + 评测 + Docker）**整体复刻**；
变化集中在**领域层**：知识库、确定性引擎、教学图库、工具集、模块表、提示词与品牌。通用骨架的代码与契约基本逐字保留。

## 2. 后端逐项

| 老工程文件/目录 | 处置 | 新工程对应 | 说明 |
|---|---|---|---|
| `app/events.py` | **照搬** | 同 | SSE 七类事件 + `[DONE]` + 24 字切帧 |
| `app/contracts/models.py` | 改名/改枚举 | 同 | `ARTIFACT_TYPES` 由 9 类改 8 类（`tolerance`→`calc`、`three_view`→`plot`、删 `coach`）；其余字段照搬 |
| `app/tools/{base,spec}.py` | **照搬** | 同 | 工具基元与 ToolSpec |
| `app/tools/__init__.py` | 改注册表 | 同 | 自注册机制照搬；`TOOL_LABELS`/转发导出改为 11 个新工具 |
| `app/tools/kb_search.py` | **照搬** | 同 | 证据卡 + 门控 + 配图挂载 |
| `app/tools/kg_lookup.py` | **照搬** | 同 | 图谱邻居 + 前置复习路径 |
| `app/tools/comparison_pick.py` | **照搬** | 同 | 辨析对挑选 + 差异点 + 随堂题 |
| `app/tools/quiz_from_kb.py` | 小改 | 同 | 答案隔离不变；题面质量声明改为核物理口径 |
| `app/tools/wrongbook_crud.py` | **照搬** | 同 | 错题增删查 |
| `app/tools/{tolerance_calc,thread_calc,arc_construct,projection_render,section_render,sketch_grade}.py` | **删除** | — | 机械制图专属（国标公差/螺纹/圆弧/三视图/剖视/手绘找茬） |
| `app/tools/{critical_calc,kinetics_calc,poison_calc,burnup_calc,reactivity_calc,spectrum_plot}.py` | **新增** | 同 | 6 个确定性物理工具（自注册） |
| `app/domain/tolerance.py`、`thread.py` | **删除** | — | 1219 行国标逻辑，不适用 |
| `app/domain/{critical,kinetics,poison,burnup,reactivity,spectrum,rod}.py` | **新增** | 同 | 7 个物理引擎（约 8k 行改为约 2k 行，含锚点校验） |
| `app/geometry/`（CSG/三视图/剖视，5 文件 2369 行） | **删除** | `app/plots/` | 3D 几何内核不适用；改为 SVG 曲线渲染 |
| `app/vision/sketch.py`（手绘找茬 CV） | **删除** | — | 课程无手绘图批改需求 |
| `app/rag/symbols.py` | **重写** | 同 | 机械符号（⌀/H7/M12/Ra）→ 核物理符号（k_eff/ρ/Σ/Φ/β/λ/$/pcm/U-235） |
| `app/rag/tokenize.py` | 小改 | 同 | 领域词典 `_CURATED_TERMS` 换成 130 个核物理术语；算法照搬 |
| `app/rag/chunking.py` | 小改 | 同 | 四套切分器照搬；文档标题改为核物理 |
| `app/rag/index.py`、`retrieve.py` | **照搬** | 同 | hashing TF-IDF + BM25 + 双门控；仅改注释 |
| `app/orchestrator.py` | **重写** | 同 | 关键词表、`_plan` 路由、`_answer_from_tool` 模板全部换领域；事件顺序/持久化/降级照搬 |
| `app/state.py` | 改注册表 | 同 | 9 个模块换成本课程 9 个（kbrag/critical/kinetics/poison/concept/graph/wrongbook/feynman + 全局） |
| `app/llm.py` | 小改 | 同 | SYSTEM_PROMPT 与 mock 拒答示例改成核物理；三档降级照搬 |
| `app/modules/feynman.py` | **照搬** | 同 | 三色标注算法与轮次门槛不变 |
| `app/modules/wrongbook.py` | 小改 | 同 | 六步诊改流程照搬；根因 6 类改成"概念混淆/公式误用/忽略假设与边界条件/单位与量纲错误/计算失误/物理图像偏差" |
| `app/db.py` | **照搬** | 同 | SQLite 5 表（账号/会话/消息/错题/埋点） |
| `app/config.py` | 改名 | 同 | 环境变量前缀 `MW_` → `RP_`；参数默认值照搬 |
| `app/main.py` | 小改 | 同 | 品牌/接口文案；删 `/api/models*`、`/api/sketch*`（无 3D/手绘）；`GRAPH_LAYERS` 改三层认知模型；其余路由照搬 |
| `apps/api/static/admin.html` | 小改 | 同 | 标题/品牌；页面结构与接口照搬 |
| `apps/api/tests/*`（20 个脚本） | 重写 | `tests/{check_tools,check_reachability,smoke,run_anchors,anchors/}` | 机械专属验收删掉；新增锚点/工具契约/可达性/端到端四类 |
| `pipeline/build_kb.py` | **照搬** | 同 | 装载→切分→索引→落盘 |
| `pipeline/build_exercises.py` | **重写** | 同 | 从"CSV 转 JSONL"改为"JSONL 清洗/校验" |
| `pipeline/export_models.py` | 删除 | — | 导出 3D 模型用 |
| `eval/run.py` | **照搬** | 同 | 指标口径（acc/课内召回/课外拒答/分离带）不变；探针换成本课程 54 题 |
| `eval/probes*.jsonl` | 重写 | `probes.jsonl` | 40 课内 + 2 近邻 + 12 课外 |
| `scripts/gen-module-docs.py` | 小改 | 同 | 模块任务书由代码生成，防文档漂移 |
| `scripts/check_llm.py` | **照搬** | 同 | LLM 连通性自检 |
| `verify_all.py` | 改清单 | 同 | 检查项换成新工程的 4 类测试 + 评测 + 健康检查 + 前端产物 |
| `Dockerfile` / `docker-compose.yml` / `render.yaml` | 改名 | 同 | 镜像名/环境变量前缀；两阶段构建照搬 |

## 3. 前端逐项

| 老工程 | 处置 | 新工程 | 说明 |
|---|---|---|---|
| `lib/sse.ts`、`lib/store.ts`、`lib/api.ts`、`lib/types.ts` | 小改 | 同 | SSE 五条容错、三栏状态机照搬；类型与接口去掉 3D/模型/手绘 |
| `modules/registry.ts`、`lib/canvasFeature.ts` | **照搬** | 同 | 画布自注册（`import.meta.glob` + 四类校验） |
| `shell/` 10 个组件（TopBar/LeftNav/ChatPanel/CanvasPanel/StatusBar/Composer/LoginGate/MessageItem/Markdown/Icons） | 小改 | 同 | 结构、布局、交互照搬；品牌与示例问题换成本课程 |
| `modules/evidence`、`modules/graph`、`modules/quiz`、`modules/comparison`、`modules/annotation`、`modules/wrongbook` | 小改 | 同 | 画布与知识图谱星系布局照搬；文案/示例数据换成核物理 |
| `modules/tolerance` | **重写** | `modules/calc` | 公差带图 → 计算卡（输入/公式/结果/校核） |
| `modules/three` | **重写** | `modules/plot` | 三视图 SVG → 曲线图（能谱/响应/中毒，含 log 轴） |
| `modules/coach`（螺纹/圆弧分步作图） | 删除 | — | 课程无对应需求 |
| `features/*/index.ts` | 改名/改文案 | `features/*/index.ts` | 9 → 8 个 feature；`tolerance`→`calc`、`three_view`→`plot` |
| `app.css`（4992 行） | **照搬** | 同 | 设计令牌与样式基本原样保留 |

## 4. 数据与内容（全部重建）

| 资产 | 老工程 | 新工程 |
|---|---|---|
| 知识条目 | 197 条（机械制图国标/画法） | 160~180 条（核反应堆物理 10 章） |
| 知识图谱 | 169 节点 / 279 边 / 26 问 | 140~170 / 230~280 / 22~26 |
| 教学图库 | 34 张 SVG（图线/三视图/剖视/公差带…） | 26~32 张 SVG（截面/四因子/通量/能谱/氙曲线/点堆响应…） |
| 辨析对 | 10 组（半剖 vs 局部剖…） | 8 组（快群vs热群、扩散vs输运、正vs负温度系数…） |
| 题库 | 196 题（习题集 OCR） | 100+ 题（习题解答 v4.0 + 教师版 + 教材章末） |
| 标准整理 | 4 份国标摘录 | 4~5 份核领域标准/规范整理 |
| 拓展阅读 | 22 篇网络采集 | 6~8 篇自写拓展（无网络采集） |
| 课程语料 | 手册 + 国标 + 习题集 | 教材 DOC（9.36 万汉字）+ 课件 + 复习笔记 |

## 5. 保留的"三条硬设计"（直接照抄的价值）

1. **能算的绝不让模型背**：数值只经确定性引擎，模型只组织语言。
2. **三条降级不中断**：无 key 走 mock 抽取、模型失败回落 mock、证据字段 `.get` 兜底。
3. **每句结论可溯源**：证据卡带文档·章节·页码/chunk，拒答走双门控。

## 6. 明确不搬的东西

- 3D 几何内核（CSG/隐藏线消除/真剖切）、手绘 CV 找茬、国标公差/螺纹/圆弧引擎；
- 3D 模型接口、找茬接口与对应前端画布；
- 网络采集的参考语料（本工程无网络采集，全部自写整理）。
"""


def main() -> int:
    out = ROOT / "docs" / "08-复刻对照表.md"
    out.write_text(CONTENT, encoding="utf-8")
    print(f"写出 {out}（{len(CONTENT)} 字符）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
