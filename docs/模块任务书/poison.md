# 模块任务书 · 燃耗与中毒（`poison`）

> ⚠️ **本文件由 `scripts/gen-module-docs.py` 从代码生成，请勿手改。**
> 改契约改代码（`app/state.py` 的 `MODULES` / `app/tools/<name>.py` / `features/<id>/index.ts` / `lib/types.ts`），再跑一次生成脚本；`--check` 模式会在 CI 里拦住漂移。

## 一、模块身份

| 项 | 值 | 来源 |
|---|---|---|
| id | `poison` | `apps/api/app/state.py` · `MODULES` |
| 显示名 | 燃耗与中毒 | 同上 |
| 图标 | `alert` | 同上（须存在于 `shell/Icons.tsx`） |
| 画布类型 | `plot` | 同上 · `canvas_kinds` |
| 工具 | `poison_calc`、`burnup_calc`、`kb_search` | 同上 · `tools` |
| 前端画布 | 曲线与分布画布（`plot`，order 30） | `features/*/index.ts` |
| 入口示例 | 2 条 | `state.py` · `entry_examples` |

**一句话职责**：氙/钐中毒、碘坑、燃耗深度、循环长度

## 二、系统提示词（`system_prompt`，拼进 LLM system 消息）

```text
燃耗与中毒助教：碘氙链、钐积累、停堆碘坑、燃耗深度与循环长度。浓度与反应性当量由 poison_calc/burnup_calc 工具计算，再解释工程含义。
```

> mock 模式（无 key）不使用系统提示词；只在真实模型路径由 `llm.generate(..., persona=...)` 拼进去。

## 三、画布（artifactType → feature → 组件）

| artifactType | feature id | 画布标题 | order | 自动展开 | 整页 | 组件 | 数据接口 |
|---|---|---|---|---|---|---|---|
| `plot` | `plot` | 曲线与分布画布 | 30 | true | 无 | `apps/web/src/modules/plot/Canvas.tsx` | `PlotData` |

**空态示例**：

- `plot`：「查看点堆阶跃响应示例」按钮（`preview.label`）

## 四、工具（本模块 `tools` 清单逐个核对）

| 工具 | 展示文案 | 产出画布 | 入参 | 实现 | 说明 |
|---|---|---|---|---|---|
| `poison_calc` | 氙钐中毒 · {query} | `plot` | `flux`、`mode`、`query`、`rho_ex0_pcm`、`t_down`、`t_irr`、`time_unit` | ✅ 已注册 | 裂变产物中毒计算：I-135→Xe-135 与 Pm-149→Sm-149 链的平衡浓度、反应性当量、停堆后碘坑（t_max、坑深、强迫停堆/允许停堆时间）与 Sm 积累。学生问“… |
| `burnup_calc` | 燃耗计算 · {query} | `calc` | `alpha`、`alpha_per_mwd_tu`、`burnup_mwd_tu`、`days`、`energy_kwh`、`eta_e`、`load_factor`、`mass_tu`、`mode`、`n_batches`、`power_e_mw`、`power_mw`、`query`、`refuel_fraction`、`rho0` | ✅ 已注册 | 燃耗计算：燃耗深度 BU=P·t/m（MWd/tU）、²³⁵U 消耗量（含俘获-裂变比 α 的 (1+α) 修正）、由年发电量与平衡换料估算铀装载量、线性反应性模型（LRM）的循环… |
| `kb_search` | 检索课程原文 · {query} | `evidence` | `query`、`scope`、`top_k` | ✅ 已注册 | 在课程知识库中检索与问题最相关的原文段落，返回证据卡（chunk_id、章节、覆盖率门控、配图）。它是所有回答的兜底依据；需要严谨出处时优先调用。 |

## 五、数据形状（`apps/web/src/lib/types.ts` 抽取）

### `PlotData`（对应 `plot`）

```ts
export interface PlotData {
  kind?: 'curve' | 'spectrum' | 'distribution' | string;
  title?: string;
  x_label?: string;
  y_label?: string;
  series?: PlotSeries[];
  markers?: PlotMarker[];
  results?: CalcResult[];
  note?: string;
  refs?: string[];
  svg?: string;
}
```

## 六、入口示例（`entry_examples`，空态 chips 直接发送）

- 停堆后氙浓度怎么变，碘坑有多深
- 燃耗深度 30000 MWd/tU 是什么概念

## 七、验收清单

```powershell
cd apps\web; npm run build                       # 前端构建（tsc 严格检查）
apps\api\.venv\Scripts\python.exe apps\api\tests\check_tools.py         # 工具自注册（11 个）
apps\api\.venv\Scripts\python.exe apps\api\tests\check_reachability.py  # 模块/工具/画布可达性
apps\api\.venv\Scripts\python.exe apps\api\tests\smoke.py              # 端到端冒烟
apps\api\.venv\Scripts\python.exe scripts\gen-module-docs.py --check     # 本文档与代码一致
```

手工验收：左栏点「燃耗与中毒」；空态应显示 1 个画布的示例入口；提问产出 `plot` 时画布按 `autoOpenCanvas` 行为自动展开。

---

源：`apps/api/app/state.py` · `MODULES[poison]`；画布：`apps/web/src/features/*/index.ts`；工具：`apps/api/app/tools/*.py` 的 `ToolSpec`（本文件由脚本生成，勿手改）
