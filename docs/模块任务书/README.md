# 模块任务书索引

> 全部由 `scripts/gen-module-docs.py` 从代码生成，**勿手改**。
> 校验：`apps\api\.venv\Scripts\python.exe scripts\gen-module-docs.py --check`（漂移时退出码 1，已接入 `verify_all.py`）。

## 一、九个模块

| # | 模块 | 文件 | 画布类型 | 工具 | 前端 feature |
|---|---|---|---|---|---|
| 1 | 全局对话 | [__global__.md](__global__.md) | `evidence` | `kb_search`、`kg_lookup`、`critical_calc`、`kinetics_calc`、`poison_calc` | `evidence` |
| 2 | 教材与概念溯源 | [kbrag.md](kbrag.md) | `evidence` | `kb_search`、`kg_lookup` | `evidence` |
| 3 | 临界与扩散计算 | [critical.md](critical.md) | `calc` | `critical_calc`、`spectrum_plot`、`kb_search` | `calc` |
| 4 | 动力学与反应性 | [kinetics.md](kinetics.md) | `plot` | `kinetics_calc`、`reactivity_calc`、`spectrum_plot`、`kb_search` | `plot` |
| 5 | 燃耗与中毒 | [poison.md](poison.md) | `plot` | `poison_calc`、`burnup_calc`、`kb_search` | `plot` |
| 6 | 概念辨析 | [concept.md](concept.md) | `comparison`、`quiz` | `comparison_pick`、`quiz_from_kb`、`kb_search` | `comparison`、`quiz` |
| 7 | 知识图谱 | [graph.md](graph.md) | `graph` | `kg_lookup`、`kb_search` | `graph` |
| 8 | 学习计划 | [study.md](study.md) | — | `quiz_from_kb`、`kb_search` | ⚠️ 无 |
| 9 | 错题与计算批改 | [wrongbook.md](wrongbook.md) | `annotation`、`wrongbook` | `wrongbook_crud`、`kb_search`、`quiz_from_kb` | `annotation`、`wrongbook` |
| 10 | 费曼追问 | [feynman.md](feynman.md) | `annotation` | `kb_search` | `annotation` |

共 10 个模块（真源：`apps/api/app/state.py` 的 `MODULES`）。

## 二、八类画布 → 前端 feature

| artifactType | feature | 画布标题 | order | 自动展开 | 整页 | 组件 |
|---|---|---|---|---|---|---|
| `evidence` | `evidence` | 证据溯源画布 | 10 | true | 无 | `apps/web/src/modules/evidence/Canvas.tsx` |
| `calc` | `calc` | 确定性计算画布 | 20 | true | 无 | `apps/web/src/modules/calc/Canvas.tsx` |
| `plot` | `plot` | 曲线与分布画布 | 30 | true | 无 | `apps/web/src/modules/plot/Canvas.tsx` |
| `comparison` | `comparison` | 成对图辨析画布 | 40 | true | 无 | `apps/web/src/modules/comparison/Canvas.tsx` |
| `annotation` | `annotation` | 费曼/步骤标注画布 | 50 | true | 无 | `apps/web/src/modules/annotation/Canvas.tsx` |
| `quiz` | `quiz` | 题库题卡 | 60 | false | 无 | `apps/web/src/modules/quiz/Canvas.tsx` |
| `wrongbook` | `wrongbook` | 错题诊改画布 | 70 | false | 无 | `apps/web/src/modules/wrongbook/Canvas.tsx` |
| `graph` | `graph` | 知识图谱画布 | 80 | true | 有 | `apps/web/src/modules/graph/Canvas.tsx` |

共 8 类画布被模块引用；前端已注册 9 个 feature。

## 三、十一个工具

| 工具 | 展示文案 | 产出画布 | 入参个数 | 实现 | 源文件 |
|---|---|---|---|---|---|
| `burnup_calc` | 燃耗计算 · {query} | `calc` | 15 | ✅ 已注册 | `apps/api/app/tools/burnup_calc.py` |
| `comparison_pick` | 辨析图对照 · {term} | `comparison` | 3 | ✅ 已注册 | `apps/api/app/tools/comparison_pick.py` |
| `critical_calc` | 临界计算 · {query} | `calc` | 15 | ✅ 已注册 | `apps/api/app/tools/critical_calc.py` |
| `kb_search` | 检索课程原文 · {query} | `evidence` | 3 | ✅ 已注册 | `apps/api/app/tools/kb_search.py` |
| `kg_lookup` | 知识图谱查询 · {term} | `graph` | 2 | ✅ 已注册 | `apps/api/app/tools/kg_lookup.py` |
| `kinetics_calc` | 点堆动力学 · {query} | `plot` | 9 | ✅ 已注册 | `apps/api/app/tools/kinetics_calc.py` |
| `poison_calc` | 氙钐中毒 · {query} | `plot` | 7 | ✅ 已注册 | `apps/api/app/tools/poison_calc.py` |
| `quiz_from_kb` | 从题库出题 · {topic} | `quiz` | 2 | ✅ 已注册 | `apps/api/app/tools/quiz_from_kb.py` |
| `reactivity_calc` | 反应性换算 · {query} | `calc` | 14 | ✅ 已注册 | `apps/api/app/tools/reactivity_calc.py` |
| `spectrum_plot` | 能谱曲线 · {query} | `plot` | 7 | ✅ 已注册 | `apps/api/app/tools/spectrum_plot.py` |
| `wrongbook_crud` | 错题本 · {action} | `wrongbook` | 2 | ✅ 已注册 | `apps/api/app/tools/wrongbook_crud.py` |

共 11 个工具：已注册 11，计划项 0（真源：`app/tools/<name>.py` 的 `ToolSpec`；计划项来自 SPEC §4.3）。

## 四、一键验收

```powershell
apps\api\.venv\Scripts\python.exe scripts\gen-module-docs.py            # 重新生成全部任务书
apps\api\.venv\Scripts\python.exe scripts\gen-module-docs.py --check    # 只校验（CI 用）
apps\api\.venv\Scripts\python.exe verify_all.py                          # 全量验收
```

## 五、生成信息与告警

- ℹ️ 工具表来自 `import app.tools`（11 个，pydantic 校验过的真值）

---

源：`apps/api/app/state.py`、`apps/api/app/tools/*.py`、`apps/web/src/features/*/index.ts`、`apps/web/src/lib/types.ts`。
