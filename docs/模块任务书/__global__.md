# 模块任务书 · 全局对话（`__global__`）

> ⚠️ **本文件由 `scripts/gen-module-docs.py` 从代码生成，请勿手改。**
> 改契约改代码（`app/state.py` 的 `MODULES` / `app/tools/<name>.py` / `features/<id>/index.ts` / `lib/types.ts`），再跑一次生成脚本；`--check` 模式会在 CI 里拦住漂移。

## 一、模块身份

| 项 | 值 | 来源 |
|---|---|---|
| id | `__global__` | `apps/api/app/state.py` · `MODULES` |
| 显示名 | 全局对话 | 同上 |
| 图标 | `chat` | 同上（须存在于 `shell/Icons.tsx`） |
| 画布类型 | `evidence` | 同上 · `canvas_kinds` |
| 工具 | `kb_search`、`kg_lookup`、`critical_calc`、`kinetics_calc`、`poison_calc` | 同上 · `tools` |
| 前端画布 | 证据溯源画布（`evidence`，order 10） | `features/*/index.ts` |
| 入口示例 | 2 条 | `state.py` · `entry_examples` |

**一句话职责**：统一提问入口，自动路由到合适的工具与模块

## 二、系统提示词（`system_prompt`，拼进 LLM system 消息）

_（本模块未设置 `system_prompt`，走全局默认提示词。）_

## 三、画布（artifactType → feature → 组件）

| artifactType | feature id | 画布标题 | order | 自动展开 | 整页 | 组件 | 数据接口 |
|---|---|---|---|---|---|---|---|
| `evidence` | `evidence` | 证据溯源画布 | 10 | true | 无 | `apps/web/src/modules/evidence/Canvas.tsx` | `EvidenceArtifactData` |

**空态示例**：

- `evidence`：无示例按钮（未声明 `preview`）

## 四、工具（本模块 `tools` 清单逐个核对）

| 工具 | 展示文案 | 产出画布 | 入参 | 实现 | 说明 |
|---|---|---|---|---|---|
| `kb_search` | 检索课程原文 · {query} | `evidence` | `query`、`scope`、`top_k` | ✅ 已注册 | 在课程知识库中检索与问题最相关的原文段落，返回证据卡（chunk_id、章节、覆盖率门控、配图）。它是所有回答的兜底依据；需要严谨出处时优先调用。 |
| `kg_lookup` | 知识图谱查询 · {term} | `graph` | `node_id`、`term` | ✅ 已注册 | 在课程知识图谱中查询一个知识点的前置知识、易混淆对比、包含关系与因果邻居，并给出前置复习路径。学生问"XX 要先学什么/和 YY 什么关系"时调用。 |
| `critical_calc` | 临界计算 · {query} | `calc` | `H`、`L2`、`M2`、`R`、`a`、`b`、`c`、`d`、`geometry`、`k_inf`、`lambda_tr`、`query`、`reflector_saving`、`tau`、`unit` | ✅ 已注册 | 单群/修正单群临界计算：由 k∞、L²、τ、外推距离、反射层节省与几何尺寸，计算材料曲率 B_m²、几何曲率 B_g²、k_eff/反应性，或用二分反解平板/球/圆柱/长方体的临界… |
| `kinetics_calc` | 点堆动力学 · {query} | `plot` | `beta`、`dt`、`k_eff`、`l`、`query`、`ratio`、`rho`、`rho_unit`、`t_end` | ✅ 已注册 | 点堆中子动力学计算：六组缓发中子倒时方程求主导根 s 与反应堆周期 T、瞬发跳跃比、瞬发临界判定（ρ≥β），并用 RK4 数值积分给出阶跃反应性后的n/n₀–t 响应曲线。反应性支… |
| `poison_calc` | 氙钐中毒 · {query} | `plot` | `flux`、`mode`、`query`、`rho_ex0_pcm`、`t_down`、`t_irr`、`time_unit` | ✅ 已注册 | 裂变产物中毒计算：I-135→Xe-135 与 Pm-149→Sm-149 链的平衡浓度、反应性当量、停堆后碘坑（t_max、坑深、强迫停堆/允许停堆时间）与 Sm 积累。学生问“… |

## 五、数据形状（`apps/web/src/lib/types.ts` 抽取）

### `EvidenceArtifactData`（对应 `evidence`）

```ts
export interface EvidenceArtifactData {
  query: string;
  evidences: EvidenceItem[];
  documents?: { id: string; title: string; category: string; status?: string }[];
  totalDocs?: number;
  coverage?: number;
  chunkCoverage?: number;
  gated?: boolean;
  figures?: FigureItem[];
}
```

## 六、入口示例（`entry_examples`，空态 chips 直接发送）

- 热中子利用系数是什么？
- k_eff=1.05 时反应性是多少 pcm？

## 七、验收清单

```powershell
cd apps\web; npm run build                       # 前端构建（tsc 严格检查）
apps\api\.venv\Scripts\python.exe apps\api\tests\check_tools.py         # 工具自注册（11 个）
apps\api\.venv\Scripts\python.exe apps\api\tests\check_reachability.py  # 模块/工具/画布可达性
apps\api\.venv\Scripts\python.exe apps\api\tests\smoke.py              # 端到端冒烟
apps\api\.venv\Scripts\python.exe scripts\gen-module-docs.py --check     # 本文档与代码一致
```

手工验收：左栏点「全局对话」；空态列出声明画布；提问产出 `evidence` 时画布按 `autoOpenCanvas` 行为自动展开。

---

源：`apps/api/app/state.py` · `MODULES[__global__]`；画布：`apps/web/src/features/*/index.ts`；工具：`apps/api/app/tools/*.py` 的 `ToolSpec`（本文件由脚本生成，勿手改）
