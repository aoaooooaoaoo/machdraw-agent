# 核反应堆物理 AI 助教 Agent

> 面向《核反应堆物理》课程的智能助学智能体：**懂方程、通能谱、能算准、可溯源**。
> 知识库封闭在课程语料内，每句结论都能翻出教材原文出处，越界问题明确拒答。

本项目是机械制图 AI 助教（`D:\桌面\教学agent\机械制图agent`）的**同架构复刻**：
FastAPI 后端 + SSE 事件流 + 工具总线自注册 + RAG 双门控 + React 三栏工作台 + 画布自注册 + 教师端 + 评测 + Docker。
换掉的只有**领域层**——知识库、确定性引擎、教学图库、工具集、模块表、提示词与品牌全部按本课程重建。

> **学生/教师使用手册：[docs/21-使用说明.md](docs/21-使用说明.md)**（在线地址、10 个模块、快捷键、数据备份、常见问题）。

---

## 现在能跑什么

| 能力 | 状态 | 说明 |
|---|---|---|
| 知识库装载与切分 | ✅ | 四套切分器；`kb/**/*.md` 按节切、`kp.jsonl` 按知识点切、习题一题一块 |
| 混合检索（BM25 + hashing TF-IDF + jieba） | ✅ | 无需向量数据库，394 块全量点积 < 20ms |
| 双门控（IDF 覆盖率 + 单块覆盖率） | ✅ | τ=0.40 / τ_chunk=0.25。**标定集 54 题 54/54**（拟合值）、**留出集 26 题 25/26（acc 0.962）** |
| SSE 七类事件流 | ✅ | `thinking / token / tool_call / tool_result / artifact / error / done` + `[DONE]` |
| 工具总线 | ✅ | **11 个工具**，确定性工具走引擎不算模型 |
| **临界与扩散计算** | ✅ | 单群/双群 k_eff、材料/几何曲率、外推距离、反射层节省、临界尺寸（二分）、不泄漏概率 |
| **点堆动力学** | ✅ | 六组缓发中子、倒时方程 7 根、反应堆周期、瞬发跳跃/瞬发临界、RK4 阶跃响应曲线 |
| **燃耗与中毒** | ✅ | 碘氙/钐平衡与停堆碘坑、反应性当量、燃耗深度、U-235 消耗、循环长度（LRM） |
| **反应性换算与控制** | ✅ | k↔ρ、pcm/mk/$、温度系数、功率亏损、控制棒微分/积分价值、硼价值、临界硼浓度 |
| **中子能谱** | ✅ | Watt 裂变谱、Maxwell 热谱、Fermi 1/E 谱、压水堆合成谱、群平均截面 |
| 锚点校验 | ✅ | **68/68 通过**：教材例题/习题原答案 + 物理不变量，逐条标明出处与容差 |
| 知识图谱 | ✅ | **175 节点 / 280 边 / 24 课程问题**（跨章前置 57 条） |
| 自绘教学图库 | ✅ | **32 张 SVG**（截面曲线/四因子/通量分布/能谱/碘氙/点堆响应/控制棒价值…），按 kp_ids 自动挂到证据卡 |
| 概念辨析 | ✅ | **8 组成对图** + 差异点 + 随堂题（快群vs热群、扩散vs输运、正vs负温度系数…） |
| 前端三栏工作台 | ✅ | **8 类画布真实渲染**：evidence / calc / plot / comparison / annotation / quiz / wrongbook / graph |
| 费曼追问 | ✅ | 逐句三色标注 + 追问 + 满三轮总评 + 故意埋错 |
| 出题 | ✅ | **112 道习题**（内部版权限制，`internal_only`） |
| 错题六步诊改 | ✅ | 原题→错误作答→根因→溯源→正解→避坑，溯源带出处 |
| 教师端 | ✅ | `GET /admin` 独立页面：语料清单/学情看板/错题根因/待复核清单/重建索引 |
| 会话持久化 | ✅ | 对话写入 SQLite（消息/会话），刷新不掉线 |
| 部署 | ✅ | 本地 venv 已实机验证；Docker 多阶段构建 / Render 蓝图已就绪（**本机 Docker Desktop 未启动，未做镜像实机复测**）；无 API Key 也能完整演示 |

> 详细验收证据见 [docs/06-评测与门控.md](docs/06-评测与门控.md)、[docs/09-一致性审计.md](docs/09-一致性审计.md)；
> **交付清单、启动方式、实测数据与已知限制见 [docs/10-交付说明.md](docs/10-交付说明.md)**。

---

## 快速开始

### 1. 起后端

```powershell
cd D:\桌面\教学agent\核反应堆物理agent\apps\api
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8077 --reload
```

打开 <http://127.0.0.1:8077/docs> 看接口；<http://127.0.0.1:8077/api/health> 看装载状态。

### 2. 建/重建知识库索引

改了 `kb/` 之后二选一：

```powershell
# 方式 A：重跑流水线（推荐，能看到统计）
apps\api\.venv\Scripts\python.exe pipeline\build_kb.py

# 方式 B：服务在跑时热重载
curl -X POST http://127.0.0.1:8077/api/admin/reload
```

### 3. 跑测试与评测

```powershell
cd D:\桌面\教学agent\核反应堆物理agent

# 确定性引擎锚点（68 条，全绿才算改对）
apps\api\.venv\Scripts\python.exe apps\api\tests\run_anchors.py

# 工具契约（11 个工具 + calc/plot 画布字段）
apps\api\.venv\Scripts\python.exe apps\api\tests\check_tools.py

# 模块/工具/画布可达性
apps\api\.venv\Scripts\python.exe apps\api\tests\check_reachability.py

# 端到端冒烟（对话 + 8 类画布）
apps\api\.venv\Scripts\python.exe apps\api\tests\smoke.py

# 真实 HTTP 端到端（自己起 8093、跑完只关自己）
apps\api\.venv\Scripts\python.exe scripts\e2e_check.py

# 探针评测（门控与检索质量）
apps\api\.venv\Scripts\python.exe eval\run.py
apps\api\.venv\Scripts\python.exe eval\run.py --probes probes_holdout.jsonl
apps\api\.venv\Scripts\python.exe eval\run.py --sweep     # 扫 λ 与 τ
```

### 4. 教师端

<http://127.0.0.1:8077/admin> —— 语料清单、学情看板、错题根因分布、待复核条目、一键重建索引。
（独立静态页，不动前端构建产物）

### 5. Docker 部署

```powershell
$env:HOST_PORT="8078"            # 8077 给本机开发服务，容器用 8078 避免冲突
docker compose up -d --build
# 学生端 http://127.0.0.1:8078/    教师端 http://127.0.0.1:8078/admin
```

### 6. 开发模式起前端

```powershell
cd apps\web
npm install
npm run dev        # 开发：默认 http://127.0.0.1:5173，代理到 8077
npm run build      # 产物进 apps/web/dist，后端会自动托管
```

> 一键全量验收：`apps\api\.venv\Scripts\python.exe verify_all.py`（服务先起）。


### 7. 实装：让别人电脑用浏览器打开

**永久在线地址（已部署，任何电脑/手机直接打开）：**

- 学生端：<https://reactor-physics-agent.onrender.com/>
- 教师端：<https://reactor-physics-agent.onrender.com/admin>
- 健康检查：<https://reactor-physics-agent.onrender.com/api/health>

部署方式：代码在 GitHub 仓库 `aoaooooaoaoo/machdraw-agent` 的 **`reactor-physics` 分支**，Render 上对应服务 `reactor-physics-agent`（Docker 运行时、Free 计划、Oregon）。
更新方法：本地改完 → `git push` 到该分支 → Render 自动重新构建部署。

> Render 免费档：**15 分钟无访问会休眠**，下一次打开约需 40~60 秒唤醒；实例无持久磁盘，账号/错题等 `data/app.db` 数据在重启/重部署后重置（知识库、索引随镜像重建）。
> 如需本机同时发布（校园局域网 + 临时公网隧道）：双击根目录 `启动核反应堆物理助教.bat`，见 [DEPLOY.md](DEPLOY.md) §11。

---

## 目录

```
apps/api/            FastAPI 后端
  app/contracts/     契约（单一事实源，前端类型由它派生）
  app/rag/           符号归一 / 分词 / 切分 / 索引 / 混合检索 + 双门控
  app/tools/         工具总线（11 个工具，自注册）
  app/domain/        确定性物理引擎（临界/点堆/中毒/燃耗/反应性/能谱/控制棒）
  app/plots/         纯 stdlib SVG 曲线渲染
  app/orchestrator.py ReAct 编排 → 事件流
  app/state.py       启动装载 + 模块注册表
apps/web/            React 三栏工作台（8 类画布自注册）
kb/                  知识库
  knowledge/         自建知识条目 kp.jsonl（175 条）
  graph/             知识图谱 nodes/edges/questions
  figures/           自绘教学图 32 张 + 辨析对 8 组
  exercises/         习题（内部，版权受限，112 道）
  standards/         核领域标准/规范整理（5 份）
  web/               自写拓展阅读（8 篇）
pipeline/            离线构建
eval/                探针集 + 评测脚本
scripts/             统计/回填/端到端/模块任务书生成
docs/                规划、设计与验收文档（先看 docs/README.md）
data/                索引与数据库（可重建，不入版本库）
working/             课程材料抽取中间产物（机读，可删）
```

---

## 关键设计取舍

1. **没有 API Key 也能完整跑**。`RP_LLM_PROVIDER=mock` 时走"本地证据抽取 + 模板作答"，
   配上 Key 即自动切真实模型（失败会自动降级）。
2. **能算的绝不让模型背**。临界、点堆、中毒、燃耗、反应性、能谱全部是确定性引擎，模型只组织语言，
   数值不经过自然语言生成——这是零幻觉的唯一来源（68 条教材锚点兜底）。
3. **不引入向量数据库**。语料 1e3 量级，hashing TF-IDF + numpy 全量点积足够；接口预留 `Embedder`。
4. **章节路径参与索引**。只索引正文会让"碘坑是怎么回事"这类提问命中率明显偏低。

## 配置

全部在 `apps/api/app/config.py`，可用环境变量覆盖（前缀 `RP_`）：

| 变量 | 默认 | 含义 |
|---|---|---|
| `RP_SPARSE_WEIGHT` | 0.45 | 混合检索 λ（BM25 通道权重） |
| `RP_GATE_TAU` | 0.40 | 覆盖率门控阈值 |
| `RP_GATE_TAU_CHUNK` | 0.25 | 单块覆盖率门限 |
| `RP_OOV_WEIGHT` | 1.2 | 语料外实义词权重倍数 |
| `RP_LLM_PROVIDER` | mock | `mock` / `deepseek` / `openai-compatible` |
| `RP_LLM_MODEL` | deepseek-chat | 模型名；讯飞星辰用 `spark-x2.6-4b`（免费） |
| `RP_LLM_BASE_URL` | https://api.deepseek.com/v1 | OpenAI 兼容端点；星火填 `https://maas-api.cn-huabei-1.xf-yun.com/v2` |
| `RP_LLM_API_KEY` | — | 没有就走 mock |
| `RP_LLM_EXTRA_BODY` | — | 额外请求体（如关思维链） |

## 版权说明

- `kb/standards/`、`kb/knowledge/`、`kb/graph/`、`kb/figures/`、`kb/web/` 是**自建整理内容**（事实性知识 + 自写表述 + 自绘 SVG），可自由使用，引用标准时标注标准号。
- `kb/exercises/` 来自教材配套习题集与习题解答，**版权受限，仅限内部教研**（`internal_only=true`），对外发布必须换源。
- 根目录课程原件（教材/课件/复习笔记/习题解答 PDF、DOC、PPTX）为用户所有，只读、未修改、未再分发。

## 文档导航

| 文档 | 内容 |
|---|---|
| [docs/SPEC-课程对象与数据契约.md](docs/SPEC-课程对象与数据契约.md) | 课程对象、ID 规约、数据契约、画布/模块/工具/引擎清单（单一事实源） |
| [docs/01-课程材料盘点与语料决策.md](docs/01-课程材料盘点与语料决策.md) | 18 个课程原件的抽取质量与语料决策 |
| [docs/02-知识库与图谱.md](docs/02-知识库与图谱.md) | 175 条知识点、175 节点/280 边/24 问的设计与校验 |
| [docs/03-确定性引擎与工具.md](docs/03-确定性引擎与工具.md) | 7 引擎 + 6 工具的公式来源、68 条锚点表、自然语言解析、边界 |
| [docs/04-教学图库与辨析对.md](docs/04-教学图库与辨析对.md) | 32 张自绘图 + 8 组辨析对的规范与挂接 |
| [docs/05-前端与画布.md](docs/05-前端与画布.md) | 三栏壳、8 类画布、自注册机制、构建与联调 |
| [docs/06-评测与门控.md](docs/06-评测与门控.md) | 探针设计、τ 标定、标定集/留出集结果、复算方法 |
| [docs/08-复刻对照表.md](docs/08-复刻对照表.md) | 机械制图 → 核反应堆物理的逐文件对照 |
| [docs/09-一致性审计.md](docs/09-一致性审计.md) | 代码与契约的逐条审计结果 |
| [docs/10-交付说明.md](docs/10-交付说明.md) | 交付清单、验收数据、已知限制、后续路线 |
| [docs/11-待人工复核清单.md](docs/11-待人工复核清单.md) | 标准/条目/习题/图谱的待复核条目 |
| [docs/12-知识图谱视觉改版.md](docs/12-知识图谱视觉改版.md) | 知识图谱重绘：GitHub 参考项目、章节分簇布局、深色/浅色双主题 |
| [docs/13-整体美化与交互升级.md](docs/13-整体美化与交互升级.md) | 工作台整体美化与命令面板/消息操作/骨架屏/Toast 等交互升级 |
| [docs/14-同类开源项目对比调研.md](docs/14-同类开源项目对比调研.md) | 与 12 个同类开源项目的对比矩阵、差距分析与改进路线 |
| [docs/15-P0实现记录-星火与会话掌握度.md](docs/15-P0实现记录-星火与会话掌握度.md) | 星火接入、硬门控、刷新不丢会话、题卡自评与掌握度回写 |
| [docs/16-第二轮增强-缓存图谱判分历史复习.md](docs/16-第二轮增强-缓存图谱判分历史复习.md) | 语义缓存、GraphRAG-lite、自动判分、历史会话、今日复习、画布导出、教师端掌握度 |
| [docs/17-第三轮-语音深色移动端OCR持久化.md](docs/17-第三轮-语音深色移动端OCR持久化.md) | 语音/朗读、深色模式、移动端 PWA、拍题 OCR、掌握度镜像、历史恢复画布 |
| [docs/18-继续尝试-OCR增强与数据备份.md](docs/18-继续尝试-OCR增强与数据备份.md) | OCR 增强、RapidOCR 实测/OOM 回滚、学习数据备份恢复、mastery 路由修复 |
| [docs/19-公式渲染与学习计划模块.md](docs/19-公式渲染与学习计划模块.md) | KaTeX 公式渲染、学习计划模块、图谱路由误伤修复 |
| [docs/20-可拖拽便签.md](docs/20-可拖拽便签.md) | 可拖拽便签：多张、颜色、折叠、Markdown/公式预览、自动保存 |
| [docs/模块任务书/](docs/模块任务书/) | 由代码生成的 10 个模块任务书（`--check` 防漂移） |
| [DEPLOY.md](DEPLOY.md) | 部署与运维手册 |
