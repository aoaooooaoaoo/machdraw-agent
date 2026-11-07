# 模块任务书 · 作图教练画布（`coach`）

> ⚠️ **本文件由 `scripts/gen-module-docs.py` 从代码生成，请勿手改。**
> 改契约改代码，再跑一次生成脚本；`--check` 模式会在 CI 里拦住漂移。

## 一、模块身份

| 项 | 值 | 来源 |
|---|---|---|
| id | `coach` | `features/coach/index.ts` |
| 显示名 | 作图教练画布 | 同上 |
| 左栏排序 | 40 | 同上 |
| artifactType | `coach` | 同上 |
| 自动展开画布 | true | 同上 |
| 样例数据 | 无 | 同上 |
| 整页模式 | 无 | 同上 |
| 画布组件 | `apps/web/src/modules/coach/Canvas.tsx` | 文件存在性 |

## 二、这个模块干什么

圆弧连接分步作图 / 螺纹比例画法

## 三、后端工具

| 工具 | 展示文案 | 入参 | 说明 |
|---|---|---|---|
| `arc_construct` | 圆弧连接作图 · {kind} | `c1`, `c2`, `circle_center`, `circle_r`, `kind`, `line1`, `line2`, `line_p1`, `line_p2`, `query`, `r`, `r1`, `r2` | 生成圆弧连接的分步作图脚本（圆心、切点、圆弧指令）：直线-直线圆角、直线-圆弧、圆弧-圆弧外切、圆弧-圆弧内切。学生问"圆弧连接怎么画"且没给数值时，用内置标准 |
| `thread_calc` | 螺纹比例画法 · {spec} | `spec` | 按 GB/T 4459.1-1995 比例画法给出螺纹大径/小径/中径与画法要点，支持 M10、M10×1.5、M20×2-6H、Tr24×5、G1/2。问螺纹 |

## 四、数据形状（从 `lib/types.ts` 抽取）

### `CoachArtifactData`（对应 `coach`）

```ts
interface CoachArtifactData {
  kind: string;
  data: Record<string, any>;
}
```

## 五、验收清单（由脚本按现有检查项生成）

```powershell
cd apps\web; npm run build                 # 前端构建（含 tsc 严格检查）
python apps\api\tests\check_reachability.py  # 工具/画布可达性
python apps\api\tests\check_tools.py         # 工具自注册三条硬校验
python verify_all.py                         # 全量 11 项
```

手工验收：左栏点「作图教练画布」→ 空态无示例按钮；提问产出 `coach` 时画布应自动展开。

---

源：`apps/web/src/features/coach/index.ts`（本文件由脚本生成，勿手改）
