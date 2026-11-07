# 模块任务书 · 公差与配合画布（`tolerance`）

> ⚠️ **本文件由 `scripts/gen-module-docs.py` 从代码生成，请勿手改。**
> 改契约改代码，再跑一次生成脚本；`--check` 模式会在 CI 里拦住漂移。

## 一、模块身份

| 项 | 值 | 来源 |
|---|---|---|
| id | `tolerance` | `features/tolerance/index.ts` |
| 显示名 | 公差与配合画布 | 同上 |
| 左栏排序 | 20 | 同上 |
| artifactType | `tolerance` | 同上 |
| 自动展开画布 | true | 同上 |
| 样例数据 | 有（`preview`） | 同上 |
| 整页模式 | 无 | 同上 |
| 画布组件 | `apps/web/src/modules/tolerance/Canvas.tsx` | 文件存在性 |

## 二、这个模块干什么

孔/轴的上下偏差、极限尺寸与公差带图

## 三、后端工具

| 工具 | 展示文案 | 入参 | 说明 |
|---|---|---|---|
| `tolerance_calc` | 公差与配合计算 · {spec} | `spec` | 按 GB/T 1800.1-2020/1800.2-2020 计算极限与配合：解析 Φ30 H7/k6 这类代号，给出孔/轴极限偏差、极限尺寸、配合性质（间隙/ |

## 四、数据形状（从 `lib/types.ts` 抽取）

### `ToleranceArtifactData`（对应 `tolerance`）

```ts
interface ToleranceArtifactData {
  basic_size: number;
  system: string;
  hole: ToleranceSide;
  shaft: ToleranceSide;
  fit: ToleranceFit;
  tolerance_zone?: { hole?: string[]; shaft?: string[] };
  process_hint?: string;
  refs?: string[];
}
```

## 五、验收清单（由脚本按现有检查项生成）

```powershell
cd apps\web; npm run build                 # 前端构建（含 tsc 严格检查）
python apps\api\tests\check_reachability.py  # 工具/画布可达性
python apps\api\tests\check_tools.py         # 工具自注册三条硬校验
python verify_all.py                         # 全量 11 项
```

手工验收：左栏点「公差与配合画布」→ 空态显示「查看公差带示例」入口；提问产出 `tolerance` 时画布应自动展开。

---

源：`apps/web/src/features/tolerance/index.ts`（本文件由脚本生成，勿手改）
