# 核反应堆物理 AI 助教 · 文档索引

> 全部文档都基于**实际代码与实测数据**写作；数字可用 `scripts/kb_stats.py`、`eval/run.py`、`tests/run_anchors.py` 复算。
> 阅读顺序：先 `SPEC`（契约），再 `01`（语料），然后按角色选读。

## 一、总览与契约

| 文档 | 内容 | 读它解决什么问题 |
|---|---|---|
| [SPEC-课程对象与数据契约.md](SPEC-课程对象与数据契约.md) | 课程 10 章、ID 规约、kb 逐字段契约、8 类画布、9 个模块、11 个工具、7 个引擎、RP_ 配置、验收口径 | "要做成什么样、字段叫什么" |
| [08-复刻对照表.md](08-复刻对照表.md) | 机械制图 → 核反应堆物理：逐文件/逐契约的"照搬/改名/重写/删除" | "复刻了哪些、为什么这么改" |
| [01-课程材料盘点与语料决策.md](01-课程材料盘点与语料决策.md) | 18 个原件（1.1 GB）的抽取质量、可用性、语料去向、版权边界 | "语料从哪来、哪些不能用" |

## 二、内容资产

| 文档 | 内容 |
|---|---|
| [02-知识库与图谱.md](02-知识库与图谱.md) | 175 条知识点（10 章）、175 节点 / 280 边 / 24 问题、112 道习题、5 份标准、8 篇拓展；`_check.py` 正反向校验 |
| [04-教学图库与辨析对.md](04-教学图库与辨析对.md) | 32 张自绘 SVG 逐张说明、绘图规范、与证据卡的挂接、新增一张图的步骤 |
| [11-待人工复核清单.md](11-待人工复核清单.md) | 标准/条目/习题/图谱的存疑条目（严重度 × 对象），对外引用前的核对清单 |

## 三、工程实现

| 文档 | 内容 |
|---|---|
| [03-确定性引擎与工具.md](03-确定性引擎与工具.md) | 7 个物理引擎 + 6 个计算工具的公式/常数来源（教材页码）、68 条锚点表、自然语言解析、能算什么/不能算什么 |
| [05-前端与画布.md](05-前端与画布.md) | 三栏壳数据流、8 类画布组件与 data 契约、calc/plot 实现、自注册机制、构建与浏览器联调 |
| [00-工程解剖与复刻蓝图.md](00-工程解剖与复刻蓝图.md) | 参考工程的五层架构、SSE 契约、工具总线、注册表机制 |
| [00a-后端解剖-RAG知识库与配置.md](00a-后端解剖-RAG知识库与配置.md) | RAG 全链路与双门控精确算法、kb 逐字段 schema、SQLite/env/LLM |
| [00b-前端与运维解剖.md](00b-前端与运维解剖.md) | 三栏壳、画布分发、SSE 解析、教师端、评测、部署 |
| [00c-文件处置清单与耦合点.md](00c-文件处置清单与耦合点.md) | 140 个参考文件的逐文件处置 + 耦合点 grep 全表 + 分阶段改造步骤 |
| [09-一致性审计.md](09-一致性审计.md) | 新工程与契约的逐条审计：P0/P1/P2 问题与对齐亮点 |
| [模块任务书/](模块任务书/) | 由代码生成的 9 个模块任务书（`scripts/gen-module-docs.py --check` 防漂移） |

## 四、验收与交付

| 文档 | 内容 |
|---|---|
| [06-评测与门控.md](06-评测与门控.md) | 探针设计、τ 标定表、标定集 54/54 与留出集 25/26、复算与重标定流程 |
| [10-交付说明.md](10-交付说明.md) | 交付清单、验收结果汇总、已知限制、版权边界、后续路线 |
| [../DEPLOY.md](../DEPLOY.md) | 三种启动方式、环境变量全表、Docker/Render、常见故障 |

## 五、可复算命令速查

```powershell
cd D:\桌面\教学agent\核反应堆物理agent

# 规模统计
apps\api\.venv\Scripts\python.exe  scripts\kb_stats.py
# 知识图谱/知识点校验
apps\api\.venv\Scripts\python.exe  kb\graph\_check.py
# 确定性引擎锚点（68 条）
apps\api\.venv\Scripts\python.exe  apps\api\tests\run_anchors.py
# 工具契约 / 可达性 / 冒烟
apps\api\.venv\Scripts\python.exe  apps\api\tests\check_tools.py
apps\api\.venv\Scripts\python.exe  apps\api\tests\check_reachability.py
apps\api\.venv\Scripts\python.exe  apps\api\tests\smoke.py
# 检索评测
apps\api\.venv\Scripts\python.exe  eval\run.py
apps\api\.venv\Scripts\python.exe  eval\run.py --probes probes_holdout.jsonl
# 一键全量（服务先起）
apps\api\.venv\Scripts\python.exe  verify_all.py
```
