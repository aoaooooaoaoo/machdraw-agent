# 模块任务书 · 动力学与反应性（`kinetics`）

> ⚠️ **本文件由 `scripts/gen-module-docs.py` 从代码生成，请勿手改。**
> 改契约改代码（`app/state.py` 的 `MODULES` / `app/tools/<name>.py` / `features/<id>/index.ts` / `lib/types.ts`），再跑一次生成脚本；`--check` 模式会在 CI 里拦住漂移。

## 一、模块身份

| 项 | 值 | 来源 |
|---|---|---|
| id | `kinetics` | `apps/api/app/state.py` · `MODULES` |
| 显示名 | 动力学与反应性 | 同上 |
| 图标 | `pencil` | 同上（须存在于 `shell/Icons.tsx`） |
| 画布类型 | `plot` | 同上 · `canvas_kinds` |
| 工具 | `kinetics_calc`、`reactivity_calc`、`spectrum_plot`、`kb_search` | 同上 · `tools` |
| 前端画布 | 曲线与分布画布（`plot`，order 30） | `features/*/index.ts` |
| 入口示例 | 2 条 | `state.py` · `entry_examples` |

**一句话职责**：缓发中子、点堆动力学、周期、瞬发临界、反应性换算

## 二、系统提示词（`system_prompt`，拼进 LLM system 消息）

```text
反应堆动力学助教：点堆方程、倒时方程、反应堆周期、瞬发临界。计算与曲线一律由 kinetics_calc/reactivity_calc 工具给出，解释缓发中子如何把反应堆周期从毫秒级拉长到秒级。
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
| `kinetics_calc` | 点堆动力学 · {query} | `plot` | `beta`、`dt`、`k_eff`、`l`、`query`、`ratio`、`rho`、`rho_unit`、`t_end` | ✅ 已注册 | 点堆中子动力学计算：六组缓发中子倒时方程求主导根 s 与反应堆周期 T、瞬发跳跃比、瞬发临界判定（ρ≥β），并用 RK4 数值积分给出阶跃反应性后的n/n₀–t 响应曲线。反应性支… |
| `reactivity_calc` | 反应性换算 · {query} | `calc` | `P1`、`P2`、`T1`、`T2`、`beta`、`k`、`power_coefficient`、`query`、`rho1`、`rho2`、`terms`、`to_unit`、`unit`、`value` | ✅ 已注册 | 反应性换算与系数：k_eff↔ρ、pcm/mk/%/Δk·k⁻¹/$ 互转、温度系数（燃料/慢化剂）、功率系数与功率亏损、多项反应性贡献代数叠加（停堆深度）。学生问“k=0.998… |
| `spectrum_plot` | 能谱曲线 · {query} | `plot` | `T_k`、`e_max_ev`、`e_min_ev`、`group_bounds`、`model`、`n_points`、`query` | ✅ 已注册 | 中子能谱/分布曲线：Watt 裂变谱、Maxwell 热谱（含温度）、1/E 费米慢化谱、压水堆合成谱；并可按能群边界数值积分求群平均截面（1/v 截面+1/E 谱有解析对照）。学… |
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

- 阶跃引入 0.2$ 反应性，稳定周期是多少
- 反应堆周期怎么定义

## 七、验收清单

```powershell
cd apps\web; npm run build                       # 前端构建（tsc 严格检查）
apps\api\.venv\Scripts\python.exe apps\api\tests\check_tools.py         # 工具自注册（11 个）
apps\api\.venv\Scripts\python.exe apps\api\tests\check_reachability.py  # 模块/工具/画布可达性
apps\api\.venv\Scripts\python.exe apps\api\tests\smoke.py              # 端到端冒烟
apps\api\.venv\Scripts\python.exe scripts\gen-module-docs.py --check     # 本文档与代码一致
```

手工验收：左栏点「动力学与反应性」；空态应显示 1 个画布的示例入口；提问产出 `plot` 时画布按 `autoOpenCanvas` 行为自动展开。

---

源：`apps/api/app/state.py` · `MODULES[kinetics]`；画布：`apps/web/src/features/*/index.ts`；工具：`apps/api/app/tools/*.py` 的 `ToolSpec`（本文件由脚本生成，勿手改）
