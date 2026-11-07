# 模块任务书 · 题卡画布（`quiz`）

> ⚠️ **本文件由 `scripts/gen-module-docs.py` 从代码生成，请勿手改。**
> 改契约改代码，再跑一次生成脚本；`--check` 模式会在 CI 里拦住漂移。

## 一、模块身份

| 项 | 值 | 来源 |
|---|---|---|
| id | `quiz` | `features/quiz/index.ts` |
| 显示名 | 题卡画布 | 同上 |
| 左栏排序 | 60 | 同上 |
| artifactType | `quiz` | 同上 |
| 自动展开画布 | false | 同上 |
| 样例数据 | 有（`preview`） | 同上 |
| 整页模式 | 无 | 同上 |
| 画布组件 | `apps/web/src/modules/quiz/Canvas.tsx` | 文件存在性 |

## 二、这个模块干什么

题库抽取的题目（答案隔离）+ 展开看解析

## 三、后端工具

| 工具 | 展示文案 | 入参 | 说明 |
|---|---|---|---|
| `quiz_from_kb` | 从题库出题 · {topic} | `n`, `topic` | 从习题库按主题抽题，题面下发、答案隔离（学生点"看解析"才给答案）。学生说"考考我/来一道题/练一练"时调用。 |

## 四、数据形状（从 `lib/types.ts` 抽取）

### `QuizArtifactData`（对应 `quiz`）

```ts
interface QuizArtifactData {
  questions: QuizQuestion[];
  answer_withheld?: boolean;
  quality_note?: string;
}
```

## 五、验收清单（由脚本按现有检查项生成）

```powershell
cd apps\web; npm run build                 # 前端构建（含 tsc 严格检查）
python apps\api\tests\check_reachability.py  # 工具/画布可达性
python apps\api\tests\check_tools.py         # 工具自注册三条硬校验
python verify_all.py                         # 全量 11 项
```

手工验收：左栏点「题卡画布」→ 空态显示「查看题卡示例」入口；提问产出 `quiz` 时画布应不抢屏（手动点开）。

---

源：`apps/web/src/features/quiz/index.ts`（本文件由脚本生成，勿手改）
