# 模块任务书 · 教材与概念溯源（`kbrag`）

> ⚠️ **本文件由 `scripts/gen-module-docs.py` 从代码生成，请勿手改。**
> 改契约改代码（`app/state.py` 的 `MODULES` / `app/tools/<name>.py` / `features/<id>/index.ts` / `lib/types.ts`），再跑一次生成脚本；`--check` 模式会在 CI 里拦住漂移。

## 一、模块身份

| 项 | 值 | 来源 |
|---|---|---|
| id | `kbrag` | `apps/api/app/state.py` · `MODULES` |
| 显示名 | 教材与概念溯源 | 同上 |
| 图标 | `book` | 同上（须存在于 `shell/Icons.tsx`） |
| 画布类型 | `evidence` | 同上 · `canvas_kinds` |
| 工具 | `kb_search`、`kg_lookup` | 同上 · `tools` |
| 前端画布 | 证据溯源画布（`evidence`，order 10） | `features/*/index.ts` |
| 入口示例 | 2 条 | `state.py` · `entry_examples` |

**一句话职责**：每句结论都能翻到教材原文出处

## 二、系统提示词（`system_prompt`，拼进 LLM system 消息）

```text
课程知识库溯源助教：回答任何专业问题时必须先调用 kb_search 检索教材/课件原文，把证据卡推上画布并逐条标注出处（文档·章节·页码）。检索不到就如实说明“知识库未收录”，绝不用课程以外的知识补充。
```

> mock 模式（无 key）不使用系统提示词；只在真实模型路径由 `llm.generate(..., persona=...)` 拼进去。

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

- 缓发中子的作用是什么？
- 为什么燃料温度系数一定为负？

## 七、验收清单

```powershell
cd apps\web; npm run build                       # 前端构建（tsc 严格检查）
apps\api\.venv\Scripts\python.exe apps\api\tests\check_tools.py         # 工具自注册（11 个）
apps\api\.venv\Scripts\python.exe apps\api\tests\check_reachability.py  # 模块/工具/画布可达性
apps\api\.venv\Scripts\python.exe apps\api\tests\smoke.py              # 端到端冒烟
apps\api\.venv\Scripts\python.exe scripts\gen-module-docs.py --check     # 本文档与代码一致
```

手工验收：左栏点「教材与概念溯源」；空态列出声明画布；提问产出 `evidence` 时画布按 `autoOpenCanvas` 行为自动展开。

---

源：`apps/api/app/state.py` · `MODULES[kbrag]`；画布：`apps/web/src/features/*/index.ts`；工具：`apps/api/app/tools/*.py` 的 `ToolSpec`（本文件由脚本生成，勿手改）
