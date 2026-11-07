# 模块任务书 · 三色标注画布（`annotation`）

> ⚠️ **本文件由 `scripts/gen-module-docs.py` 从代码生成，请勿手改。**
> 改契约改代码，再跑一次生成脚本；`--check` 模式会在 CI 里拦住漂移。

## 一、模块身份

| 项 | 值 | 来源 |
|---|---|---|
| id | `annotation` | `features/annotation/index.ts` |
| 显示名 | 三色标注画布 | 同上 |
| 左栏排序 | 70 | 同上 |
| artifactType | `annotation` | 同上 |
| 自动展开画布 | true | 同上 |
| 样例数据 | 无 | 同上 |
| 整页模式 | 无 | 同上 |
| 画布组件 | `apps/web/src/modules/annotation/Canvas.tsx` | 文件存在性 |

## 二、这个模块干什么

费曼追问：逐句三色标注 + 追问 + 轮次总评

## 三、后端工具

| 工具 | 展示文案 | 入参 | 说明 |
|---|---|---|---|
| `sketch_grade` | 手绘找茬 · {view} | `inject`, `model_id`, `segments`, `view` | 把学生提交的线段与标准三视图比对，给出可命名的错误（漏画/多画/虚实线混淆/位置偏差）；不传 segments 而传 inject 时，生成一道找茬练习（改坏图 |

## 四、数据形状（从 `lib/types.ts` 抽取）

### `AnnotationArtifactData`（对应 `annotation`）

```ts
interface AnnotationArtifactData {
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

## 五、验收清单（由脚本按现有检查项生成）

```powershell
cd apps\web; npm run build                 # 前端构建（含 tsc 严格检查）
python apps\api\tests\check_reachability.py  # 工具/画布可达性
python apps\api\tests\check_tools.py         # 工具自注册三条硬校验
python verify_all.py                         # 全量 11 项
```

手工验收：左栏点「三色标注画布」→ 空态无示例按钮；提问产出 `annotation` 时画布应自动展开。

---

源：`apps/web/src/features/annotation/index.ts`（本文件由脚本生成，勿手改）
