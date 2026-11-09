# 模块任务书 · 概念辨析（`concept`）

> ⚠️ **本文件由 `scripts/gen-module-docs.py` 从代码生成，请勿手改。**
> 改契约改代码（`app/state.py` 的 `MODULES` / `app/tools/<name>.py` / `features/<id>/index.ts` / `lib/types.ts`），再跑一次生成脚本；`--check` 模式会在 CI 里拦住漂移。

## 一、模块身份

| 项 | 值 | 来源 |
|---|---|---|
| id | `concept` | `apps/api/app/state.py` · `MODULES` |
| 显示名 | 概念辨析 | 同上 |
| 图标 | `layers` | 同上（须存在于 `shell/Icons.tsx`） |
| 画布类型 | `comparison`、`quiz` | 同上 · `canvas_kinds` |
| 工具 | `comparison_pick`、`quiz_from_kb`、`kb_search` | 同上 · `tools` |
| 前端画布 | 成对图辨析画布（`comparison`，order 40）、题库题卡（`quiz`，order 60） | `features/*/index.ts` |
| 入口示例 | 2 条 | `state.py` · `entry_examples` |

**一句话职责**：快群/热群、扩散/输运、单群/双群、正/负温度系数等对照

## 二、系统提示词（`system_prompt`，拼进 LLM system 消息）

```text
概念辨析助教：给出成对图并让学生找出差异，不直接给答案。
```

> mock 模式（无 key）不使用系统提示词；只在真实模型路径由 `llm.generate(..., persona=...)` 拼进去。

## 三、画布（artifactType → feature → 组件）

| artifactType | feature id | 画布标题 | order | 自动展开 | 整页 | 组件 | 数据接口 |
|---|---|---|---|---|---|---|---|
| `comparison` | `comparison` | 成对图辨析画布 | 40 | true | 无 | `apps/web/src/modules/comparison/Canvas.tsx` | `ComparisonArtifactData` |
| `quiz` | `quiz` | 题库题卡 | 60 | false | 无 | `apps/web/src/modules/quiz/Canvas.tsx` | `QuizArtifactData` |

**空态示例**：

- `comparison`：「查看辨析示例」按钮（`preview.label`）
- `quiz`：「查看题卡示例」按钮（`preview.label`）

## 四、工具（本模块 `tools` 清单逐个核对）

| 工具 | 展示文案 | 产出画布 | 入参 | 实现 | 说明 |
|---|---|---|---|---|---|
| `comparison_pick` | 辨析图对照 · {term} | `comparison` | `pair_id`、`query`、`term` | ✅ 已注册 | 从成对图库挑一组易混结构做辨析：并排两张图、逐条差异点、随堂一问（答案不下发）。学生问"A 和 B 有什么区别/怎么区分"时调用。 |
| `quiz_from_kb` | 从题库出题 · {topic} | `quiz` | `n`、`topic` | ✅ 已注册 | 从习题库按主题抽题，题面下发、答案隔离（学生点"看解析"才给答案）。学生说"考考我/来一道题/练一练"时调用。 |
| `kb_search` | 检索课程原文 · {query} | `evidence` | `query`、`scope`、`top_k` | ✅ 已注册 | 在课程知识库中检索与问题最相关的原文段落，返回证据卡（chunk_id、章节、覆盖率门控、配图）。它是所有回答的兜底依据；需要严谨出处时优先调用。 |

## 五、数据形状（`apps/web/src/lib/types.ts` 抽取）

### `ComparisonArtifactData`（对应 `comparison`）

```ts
export interface ComparisonArtifactData {
  pair_id?: string;
  file: string;
  title?: string;
  a?: ComparisonSideInfo;
  b?: ComparisonSideInfo;
  differences?: ComparisonDifference[];
  question?: ComparisonQuestion;
  kp_ids?: string[];
}
```

### `QuizArtifactData`（对应 `quiz`）

```ts
export interface QuizArtifactData {
  questions: QuizQuestion[];
  answer_withheld?: boolean;
  quality_note?: string;
}
```

## 六、入口示例（`entry_examples`，空态 chips 直接发送）

- 快群和热群有什么区别
- 扩散理论和输运理论怎么区分

## 七、验收清单

```powershell
cd apps\web; npm run build                       # 前端构建（tsc 严格检查）
apps\api\.venv\Scripts\python.exe apps\api\tests\check_tools.py         # 工具自注册（11 个）
apps\api\.venv\Scripts\python.exe apps\api\tests\check_reachability.py  # 模块/工具/画布可达性
apps\api\.venv\Scripts\python.exe apps\api\tests\smoke.py              # 端到端冒烟
apps\api\.venv\Scripts\python.exe scripts\gen-module-docs.py --check     # 本文档与代码一致
```

手工验收：左栏点「概念辨析」；空态应显示 2 个画布的示例入口；提问产出 `comparison` 时画布按 `autoOpenCanvas` 行为自动展开。

---

源：`apps/api/app/state.py` · `MODULES[concept]`；画布：`apps/web/src/features/*/index.ts`；工具：`apps/api/app/tools/*.py` 的 `ToolSpec`（本文件由脚本生成，勿手改）
