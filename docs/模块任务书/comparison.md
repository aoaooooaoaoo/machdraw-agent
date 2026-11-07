# 模块任务书 · 成对图辨析画布（`comparison`）

> ⚠️ **本文件由 `scripts/gen-module-docs.py` 从代码生成，请勿手改。**
> 改契约改代码，再跑一次生成脚本；`--check` 模式会在 CI 里拦住漂移。

## 一、模块身份

| 项 | 值 | 来源 |
|---|---|---|
| id | `comparison` | `features/comparison/index.ts` |
| 显示名 | 成对图辨析画布 | 同上 |
| 左栏排序 | 90 | 同上 |
| artifactType | `comparison` | 同上 |
| 自动展开画布 | true | 同上 |
| 样例数据 | 有（`preview`） | 同上 |
| 整页模式 | 无 | 同上 |
| 画布组件 | `apps/web/src/modules/comparison/Canvas.tsx` | 文件存在性 |

## 二、这个模块干什么

成对图 + 差异点 + 随堂做题

## 三、后端工具

| 工具 | 展示文案 | 入参 | 说明 |
|---|---|---|---|
| `comparison_pick` | 辨析图对照 · {term} | `pair_id`, `query`, `term` | 从成对图库挑一组易混结构做辨析：并排两张图、逐条差异点、随堂一问（答案不下发）。学生问"A 和 B 有什么区别/怎么区分"时调用。 |

## 四、数据形状（从 `lib/types.ts` 抽取）

### `ComparisonArtifactData`（对应 `comparison`）

```ts
interface ComparisonArtifactData {
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

## 五、验收清单（由脚本按现有检查项生成）

```powershell
cd apps\web; npm run build                 # 前端构建（含 tsc 严格检查）
python apps\api\tests\check_reachability.py  # 工具/画布可达性
python apps\api\tests\check_tools.py         # 工具自注册三条硬校验
python verify_all.py                         # 全量 11 项
```

手工验收：左栏点「成对图辨析画布」→ 空态显示「查看辨析示例」入口；提问产出 `comparison` 时画布应自动展开。

---

源：`apps/web/src/features/comparison/index.ts`（本文件由脚本生成，勿手改）
