# 模块任务书 · 证据溯源画布（`evidence`）

> ⚠️ **本文件由 `scripts/gen-module-docs.py` 从代码生成，请勿手改。**
> 改契约改代码，再跑一次生成脚本；`--check` 模式会在 CI 里拦住漂移。

## 一、模块身份

| 项 | 值 | 来源 |
|---|---|---|
| id | `evidence` | `features/evidence/index.ts` |
| 显示名 | 证据溯源画布 | 同上 |
| 左栏排序 | 10 | 同上 |
| artifactType | `evidence` | 同上 |
| 自动展开画布 | true | 同上 |
| 样例数据 | 无 | 同上 |
| 整页模式 | 无 | 同上 |
| 画布组件 | `apps/web/src/modules/evidence/Canvas.tsx` | 文件存在性 |

## 二、这个模块干什么

每条结论可回翻到原文：文档 · 章节 · chunk_id · 相关度

## 三、后端工具

| 工具 | 展示文案 | 入参 | 说明 |
|---|---|---|---|
| `kb_search` | 检索课程原文 · {query} | `query`, `scope`, `top_k` | 在课程知识库中检索与问题最相关的原文段落，返回证据卡（chunk_id、章节、覆盖率门控、配图）。它是所有回答的兜底依据；需要严谨出处时优先调用。 |

## 四、数据形状（从 `lib/types.ts` 抽取）

### `EvidenceArtifactData`（对应 `evidence`）

```ts
interface EvidenceArtifactData {
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

## 五、验收清单（由脚本按现有检查项生成）

```powershell
cd apps\web; npm run build                 # 前端构建（含 tsc 严格检查）
python apps\api\tests\check_reachability.py  # 工具/画布可达性
python apps\api\tests\check_tools.py         # 工具自注册三条硬校验
python verify_all.py                         # 全量 11 项
```

手工验收：左栏点「证据溯源画布」→ 空态无示例按钮；提问产出 `evidence` 时画布应自动展开。

---

源：`apps/web/src/features/evidence/index.ts`（本文件由脚本生成，勿手改）
