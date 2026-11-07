# 模块任务书 · 三视图投影画布（`three_view`）

> ⚠️ **本文件由 `scripts/gen-module-docs.py` 从代码生成，请勿手改。**
> 改契约改代码，再跑一次生成脚本；`--check` 模式会在 CI 里拦住漂移。

## 一、模块身份

| 项 | 值 | 来源 |
|---|---|---|
| id | `three_view` | `features/three_view/index.ts` |
| 显示名 | 三视图投影画布 | 同上 |
| 左栏排序 | 50 | 同上 |
| artifactType | `three_view` | 同上 |
| 自动展开画布 | true | 同上 |
| 样例数据 | 有（`preview`） | 同上 |
| 整页模式 | 无 | 同上 |
| 画布组件 | `apps/web/src/features/three_view/Canvas.tsx` | 文件存在性 |

## 二、这个模块干什么

按后端图纸坐标直出 SVG：三视图 · 虚线不可见轮廓 · 投影辅助线

## 三、后端工具

| 工具 | 展示文案 | 入参 | 说明 |
|---|---|---|---|
| `projection_render` | 三视图投影 · {model_id} | `model_id`, `query` | 对内置 CSG 教学模型做真投影 + 隐藏线消除，输出主/俯/左三视图与长对正、高平齐、宽相等辅助线数据。学生问三视图、投影规律、补画视图时调用。 |
| `section_render` | 剖视图生成 · {model_id} | `axis`, `mode`, `model_id`, `query`, `ratio` | 对内置教学模型做真剖切（不是盖阴影），生成全剖/半剖/局部剖视图与 45° 剖面线，返回可直接绘制的线段数据。学生问剖视图画法、剖面线怎么画时调用。 |

## 四、数据形状（从 `lib/types.ts` 抽取）

### `ThreeViewArtifactData`（对应 `three_view`）

```ts
interface ThreeViewArtifactData {
  model_id?: string;
  name?: string;
  unit?: string;
  size?: { L?: number; W?: number; H?: number };
  segments: ThreeViewSegment[];
  viewBox?: [number, number, number, number];
  labels?: ThreeViewLabel[];
  aux?: ThreeViewAux[];
  view_boxes?: Record<string, ThreeViewBox>;
  stats?: Record<string, ThreeViewSideStats>;
  projection?: string;
  bbox?: number[][];
}
```

## 五、验收清单（由脚本按现有检查项生成）

```powershell
cd apps\web; npm run build                 # 前端构建（含 tsc 严格检查）
python apps\api\tests\check_reachability.py  # 工具/画布可达性
python apps\api\tests\check_tools.py         # 工具自注册三条硬校验
python verify_all.py                         # 全量 11 项
```

手工验收：左栏点「三视图投影画布」→ 空态显示「查看三视图示例」入口；提问产出 `three_view` 时画布应自动展开。

---

源：`apps/web/src/features/three_view/index.ts`（本文件由脚本生成，勿手改）
