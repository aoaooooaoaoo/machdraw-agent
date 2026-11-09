# 模块任务书 · 错题与计算批改（`wrongbook`）

> ⚠️ **本文件由 `scripts/gen-module-docs.py` 从代码生成，请勿手改。**
> 改契约改代码（`app/state.py` 的 `MODULES` / `app/tools/<name>.py` / `features/<id>/index.ts` / `lib/types.ts`），再跑一次生成脚本；`--check` 模式会在 CI 里拦住漂移。

## 一、模块身份

| 项 | 值 | 来源 |
|---|---|---|
| id | `wrongbook` | `apps/api/app/state.py` · `MODULES` |
| 显示名 | 错题与计算批改 | 同上 |
| 图标 | `alert` | 同上（须存在于 `shell/Icons.tsx`） |
| 画布类型 | `annotation`、`wrongbook` | 同上 · `canvas_kinds` |
| 工具 | `wrongbook_crud`、`kb_search`、`quiz_from_kb` | 同上 · `tools` |
| 前端画布 | 费曼/步骤标注画布（`annotation`，order 50）、错题诊改画布（`wrongbook`，order 70） | `features/*/index.ts` |
| 入口示例 | 2 条 | `state.py` · `entry_examples` |

**一句话职责**：六步诊改，溯源回教材原文

## 二、系统提示词（`system_prompt`，拼进 LLM system 消息）

```text
错题诊断助教：按“原题→错误作答→根因→溯源→正解→避坑”六步拆解，根因归入概念混淆/公式误用/忽略假设与边界条件/单位与量纲错误/计算失误/物理图像偏差。
```

> mock 模式（无 key）不使用系统提示词；只在真实模型路径由 `llm.generate(..., persona=...)` 拼进去。

## 三、画布（artifactType → feature → 组件）

| artifactType | feature id | 画布标题 | order | 自动展开 | 整页 | 组件 | 数据接口 |
|---|---|---|---|---|---|---|---|
| `annotation` | `annotation` | 费曼/步骤标注画布 | 50 | true | 无 | `apps/web/src/modules/annotation/Canvas.tsx` | `AnnotationArtifactData` |
| `wrongbook` | `wrongbook` | 错题诊改画布 | 70 | false | 无 | `apps/web/src/modules/wrongbook/Canvas.tsx` | `WrongbookArtifactData` |

**空态示例**：

- `annotation`：无示例按钮（未声明 `preview`）
- `wrongbook`：无示例按钮（未声明 `preview`）

## 四、工具（本模块 `tools` 清单逐个核对）

| 工具 | 展示文案 | 产出画布 | 入参 | 实现 | 说明 |
|---|---|---|---|---|---|
| `wrongbook_crud` | 错题本 · {action} | `wrongbook` | `action`、`record` | ✅ 已注册 | 错题本读写：action=list 列出当前账号的错题；action=add 需要同时给 record 记录一条错题。学生问"我的错题/易错题"时调用。 |
| `kb_search` | 检索课程原文 · {query} | `evidence` | `query`、`scope`、`top_k` | ✅ 已注册 | 在课程知识库中检索与问题最相关的原文段落，返回证据卡（chunk_id、章节、覆盖率门控、配图）。它是所有回答的兜底依据；需要严谨出处时优先调用。 |
| `quiz_from_kb` | 从题库出题 · {topic} | `quiz` | `n`、`topic` | ✅ 已注册 | 从习题库按主题抽题，题面下发、答案隔离（学生点"看解析"才给答案）。学生说"考考我/来一道题/练一练"时调用。 |

## 五、数据形状（`apps/web/src/lib/types.ts` 抽取）

### `AnnotationArtifactData`（对应 `annotation`）

```ts
export interface AnnotationArtifactData {
  round: number;
  final: boolean;
  sentence_count: number;
  coverage?: number;
  annotations: AnnotationItem[];
  probes: string[];
  summary?: string;
  score?: { correct: number; total: number; level?: string };
}
```

### `WrongbookArtifactData`（对应 `wrongbook`）

```ts
export interface WrongbookArtifactData {
  question: string;
  wrong_answer?: string;
  root_cause?: string;
  root_causes_all?: string[];
  steps: WrongbookStep[];
  trace?: WrongbookTrace[];
  pitfalls?: string[];
  kp_ids?: string[];
  coverage?: number;
  gated?: boolean;
  note?: string;
  source?: string;
}
```

## 六、入口示例（`entry_examples`，空态 chips 直接发送）

- 抽一道错题
- 我的错题本

## 七、验收清单

```powershell
cd apps\web; npm run build                       # 前端构建（tsc 严格检查）
apps\api\.venv\Scripts\python.exe apps\api\tests\check_tools.py         # 工具自注册（11 个）
apps\api\.venv\Scripts\python.exe apps\api\tests\check_reachability.py  # 模块/工具/画布可达性
apps\api\.venv\Scripts\python.exe apps\api\tests\smoke.py              # 端到端冒烟
apps\api\.venv\Scripts\python.exe scripts\gen-module-docs.py --check     # 本文档与代码一致
```

手工验收：左栏点「错题与计算批改」；空态列出声明画布；提问产出 `annotation` 时画布按 `autoOpenCanvas` 行为自动展开。

---

源：`apps/api/app/state.py` · `MODULES[wrongbook]`；画布：`apps/web/src/features/*/index.ts`；工具：`apps/api/app/tools/*.py` 的 `ToolSpec`（本文件由脚本生成，勿手改）
