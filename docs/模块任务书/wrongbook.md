# 模块任务书 · 错题诊改画布（`wrongbook`）

> ⚠️ **本文件由 `scripts/gen-module-docs.py` 从代码生成，请勿手改。**
> 改契约改代码，再跑一次生成脚本；`--check` 模式会在 CI 里拦住漂移。

## 一、模块身份

| 项 | 值 | 来源 |
|---|---|---|
| id | `wrongbook` | `features/wrongbook/index.ts` |
| 显示名 | 错题诊改画布 | 同上 |
| 左栏排序 | 80 | 同上 |
| artifactType | `wrongbook` | 同上 |
| 自动展开画布 | false | 同上 |
| 样例数据 | 无 | 同上 |
| 整页模式 | 无 | 同上 |
| 画布组件 | `apps/web/src/modules/wrongbook/Canvas.tsx` | 文件存在性 |

## 二、这个模块干什么

六步拆解：原题 → 错误作答 → 根因 → 溯源 → 正解 → 避坑

## 三、后端工具

| 工具 | 展示文案 | 入参 | 说明 |
|---|---|---|---|
| `wrongbook_crud` | 错题本 · {action} | `action`, `record` | 错题本读写：action=list 列出当前账号的错题；action=add 需要同时给 record 记录一条错题。学生问"我的错题/易错题"时调用。 |

## 四、数据形状（从 `lib/types.ts` 抽取）

### `WrongbookArtifactData`（对应 `wrongbook`）

```ts
interface WrongbookArtifactData {
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

## 五、验收清单（由脚本按现有检查项生成）

```powershell
cd apps\web; npm run build                 # 前端构建（含 tsc 严格检查）
python apps\api\tests\check_reachability.py  # 工具/画布可达性
python apps\api\tests\check_tools.py         # 工具自注册三条硬校验
python verify_all.py                         # 全量 11 项
```

手工验收：左栏点「错题诊改画布」→ 空态无示例按钮；提问产出 `wrongbook` 时画布应不抢屏（手动点开）。

---

源：`apps/web/src/features/wrongbook/index.ts`（本文件由脚本生成，勿手改）
