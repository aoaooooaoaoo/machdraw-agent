# 模块任务书 · 临界与扩散计算（`critical`）

> ⚠️ **本文件由 `scripts/gen-module-docs.py` 从代码生成，请勿手改。**
> 改契约改代码（`app/state.py` 的 `MODULES` / `app/tools/<name>.py` / `features/<id>/index.ts` / `lib/types.ts`），再跑一次生成脚本；`--check` 模式会在 CI 里拦住漂移。

## 一、模块身份

| 项 | 值 | 来源 |
|---|---|---|
| id | `critical` | `apps/api/app/state.py` · `MODULES` |
| 显示名 | 临界与扩散计算 | 同上 |
| 图标 | `target` | 同上（须存在于 `shell/Icons.tsx`） |
| 画布类型 | `calc` | 同上 · `canvas_kinds` |
| 工具 | `critical_calc`、`spectrum_plot`、`kb_search` | 同上 · `tools` |
| 前端画布 | 确定性计算画布（`calc`，order 20） | `features/*/index.ts` |
| 入口示例 | 2 条 | `state.py` · `entry_examples` |

**一句话职责**：k∞、M²=L²+τ、B²、k_eff、临界尺寸、反射层节省

## 二、系统提示词（`system_prompt`，拼进 LLM system 消息）

```text
临界计算助教：先把题目给成材料曲率/几何曲率/单群临界方程的标准形式，数值一律由 critical_calc 工具确定性计算，再解释每一步的物理含义。数值不得自行推算或编造；检索教材原文作为公式依据。
```

> mock 模式（无 key）不使用系统提示词；只在真实模型路径由 `llm.generate(..., persona=...)` 拼进去。

## 三、画布（artifactType → feature → 组件）

| artifactType | feature id | 画布标题 | order | 自动展开 | 整页 | 组件 | 数据接口 |
|---|---|---|---|---|---|---|---|
| `calc` | `calc` | 确定性计算画布 | 20 | true | 无 | `apps/web/src/modules/calc/Canvas.tsx` | `CalcData` |

**空态示例**：

- `calc`：「查看临界计算示例」按钮（`preview.label`）

## 四、工具（本模块 `tools` 清单逐个核对）

| 工具 | 展示文案 | 产出画布 | 入参 | 实现 | 说明 |
|---|---|---|---|---|---|
| `critical_calc` | 临界计算 · {query} | `calc` | `H`、`L2`、`M2`、`R`、`a`、`b`、`c`、`d`、`geometry`、`k_inf`、`lambda_tr`、`query`、`reflector_saving`、`tau`、`unit` | ✅ 已注册 | 单群/修正单群临界计算：由 k∞、L²、τ、外推距离、反射层节省与几何尺寸，计算材料曲率 B_m²、几何曲率 B_g²、k_eff/反应性，或用二分反解平板/球/圆柱/长方体的临界… |
| `spectrum_plot` | 能谱曲线 · {query} | `plot` | `T_k`、`e_max_ev`、`e_min_ev`、`group_bounds`、`model`、`n_points`、`query` | ✅ 已注册 | 中子能谱/分布曲线：Watt 裂变谱、Maxwell 热谱（含温度）、1/E 费米慢化谱、压水堆合成谱；并可按能群边界数值积分求群平均截面（1/v 截面+1/E 谱有解析对照）。学… |
| `kb_search` | 检索课程原文 · {query} | `evidence` | `query`、`scope`、`top_k` | ✅ 已注册 | 在课程知识库中检索与问题最相关的原文段落，返回证据卡（chunk_id、章节、覆盖率门控、配图）。它是所有回答的兜底依据；需要严谨出处时优先调用。 |

## 五、数据形状（`apps/web/src/lib/types.ts` 抽取）

### `CalcData`（对应 `calc`）

```ts
export interface CalcData {
  title?: string;
  inputs?: CalcInput[];
  formulas?: CalcFormula[];
  results?: CalcResult[];
  verdict?: CalcVerdict;
  refs?: string[];
  note?: string;
  svg?: string;
}
```

## 六、入口示例（`entry_examples`，空态 chips 直接发送）

- 裸堆单群临界尺寸怎么算
- k∞=1.06、M²=180 cm² 的临界曲率是多少

## 七、验收清单

```powershell
cd apps\web; npm run build                       # 前端构建（tsc 严格检查）
apps\api\.venv\Scripts\python.exe apps\api\tests\check_tools.py         # 工具自注册（11 个）
apps\api\.venv\Scripts\python.exe apps\api\tests\check_reachability.py  # 模块/工具/画布可达性
apps\api\.venv\Scripts\python.exe apps\api\tests\smoke.py              # 端到端冒烟
apps\api\.venv\Scripts\python.exe scripts\gen-module-docs.py --check     # 本文档与代码一致
```

手工验收：左栏点「临界与扩散计算」；空态应显示 1 个画布的示例入口；提问产出 `calc` 时画布按 `autoOpenCanvas` 行为自动展开。

---

源：`apps/api/app/state.py` · `MODULES[critical]`；画布：`apps/web/src/features/*/index.ts`；工具：`apps/api/app/tools/*.py` 的 `ToolSpec`（本文件由脚本生成，勿手改）
