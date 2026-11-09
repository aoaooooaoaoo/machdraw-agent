# 模块任务书 · 学习计划（`study`）

> ⚠️ **本文件由 `scripts/gen-module-docs.py` 从代码生成，请勿手改。**
> 改契约改代码（`app/state.py` 的 `MODULES` / `app/tools/<name>.py` / `features/<id>/index.ts` / `lib/types.ts`），再跑一次生成脚本；`--check` 模式会在 CI 里拦住漂移。

## 一、模块身份

| 项 | 值 | 来源 |
|---|---|---|
| id | `study` | `apps/api/app/state.py` · `MODULES` |
| 显示名 | 学习计划 | 同上 |
| 图标 | `target` | 同上（须存在于 `shell/Icons.tsx`） |
| 画布类型 | （无） | 同上 · `canvas_kinds` |
| 工具 | `quiz_from_kb`、`kb_search` | 同上 · `tools` |
| 前端画布 | ⚠️ 无对应 feature | `features/*/index.ts` |
| 入口示例 | 0 条 | `state.py` · `entry_examples` |

**一句话职责**：今日任务、到期复习、下一步学什么

## 二、系统提示词（`system_prompt`，拼进 LLM system 消息）

```text
学习计划助教：根据学生的掌握度、到期复习和前置依赖，安排今天先学/先复习什么。
```

> mock 模式（无 key）不使用系统提示词；只在真实模型路径由 `llm.generate(..., persona=...)` 拼进去。

## 三、画布（artifactType → feature → 组件）

_本模块不声明画布。_
## 四、工具（本模块 `tools` 清单逐个核对）

| 工具 | 展示文案 | 产出画布 | 入参 | 实现 | 说明 |
|---|---|---|---|---|---|
| `quiz_from_kb` | 从题库出题 · {topic} | `quiz` | `n`、`topic` | ✅ 已注册 | 从习题库按主题抽题，题面下发、答案隔离（学生点"看解析"才给答案）。学生说"考考我/来一道题/练一练"时调用。 |
| `kb_search` | 检索课程原文 · {query} | `evidence` | `query`、`scope`、`top_k` | ✅ 已注册 | 在课程知识库中检索与问题最相关的原文段落，返回证据卡（chunk_id、章节、覆盖率门控、配图）。它是所有回答的兜底依据；需要严谨出处时优先调用。 |

## 五、数据形状（`apps/web/src/lib/types.ts` 抽取）

_`types.ts` 里没有按命名约定找到对应接口。_

## 六、入口示例（`entry_examples`，空态 chips 直接发送）

_（未配置入口示例。）_

## 七、验收清单

```powershell
cd apps\web; npm run build                       # 前端构建（tsc 严格检查）
apps\api\.venv\Scripts\python.exe apps\api\tests\check_tools.py         # 工具自注册（11 个）
apps\api\.venv\Scripts\python.exe apps\api\tests\check_reachability.py  # 模块/工具/画布可达性
apps\api\.venv\Scripts\python.exe apps\api\tests\smoke.py              # 端到端冒烟
apps\api\.venv\Scripts\python.exe scripts\gen-module-docs.py --check     # 本文档与代码一致
```

手工验收：左栏点「学习计划」；提问产出 `?` 时画布按 `autoOpenCanvas` 行为不抢屏。

---

源：`apps/api/app/state.py` · `MODULES[study]`；画布：`apps/web/src/features/*/index.ts`；工具：`apps/api/app/tools/*.py` 的 `ToolSpec`（本文件由脚本生成，勿手改）
