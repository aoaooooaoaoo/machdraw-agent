# 模块任务书 · 知识图谱画布（`graph`）

> ⚠️ **本文件由 `scripts/gen-module-docs.py` 从代码生成，请勿手改。**
> 改契约改代码，再跑一次生成脚本；`--check` 模式会在 CI 里拦住漂移。

## 一、模块身份

| 项 | 值 | 来源 |
|---|---|---|
| id | `graph` | `features/graph/index.ts` |
| 显示名 | 知识图谱画布 | 同上 |
| 左栏排序 | 30 | 同上 |
| artifactType | `graph` | 同上 |
| 自动展开画布 | true | 同上 |
| 样例数据 | 无 | 同上 |
| 整页模式 | 有（`page`） | 同上 |
| 画布组件 | `apps/web/src/modules/graph/Canvas.tsx` | 文件存在性 |

## 二、这个模块干什么

焦点星图 · 前置依赖 · 易混淆对比，点节点换焦点

## 三、后端工具

| 工具 | 展示文案 | 入参 | 说明 |
|---|---|---|---|
| `kg_lookup` | 知识图谱查询 · {term} | `node_id`, `term` | 在课程知识图谱中查询一个知识点的前置知识、易混淆对比、包含关系与因果邻居，并给出前置复习路径。学生问"XX 要先学什么/和 YY 什么关系"时调用。 |

## 四、数据形状（从 `lib/types.ts` 抽取）

### `GraphArtifactData`（对应 `graph`）

```ts
interface GraphArtifactData {
  focus: GraphNodeInfo;
  neighbors: GraphNeighbor[];
  prereq: GraphPrereqStep[];
  nodes: GraphNodeInfo[];
  edges: GraphEdgeInfo[];
  mode?: 'knowledge' | 'question';
}
```

## 五、验收清单（由脚本按现有检查项生成）

```powershell
cd apps\web; npm run build                 # 前端构建（含 tsc 严格检查）
python apps\api\tests\check_reachability.py  # 工具/画布可达性
python apps\api\tests\check_tools.py         # 工具自注册三条硬校验
python verify_all.py                         # 全量 11 项
```

手工验收：左栏点「知识图谱画布」→ 空态无示例按钮；提问产出 `graph` 时画布应自动展开。

---

源：`apps/web/src/features/graph/index.ts`（本文件由脚本生成，勿手改）
