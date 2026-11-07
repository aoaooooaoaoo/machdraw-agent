# 机械制图 AI 助教 Agent

> 面向《机械制图》课程的智能助学智能体：**懂国标、通空间、能判图**。
> 知识库封闭在课程语料内，每句结论都能翻出原文出处，越界问题明确拒答。

本项目是 `docs/` 里那份规划的**可运行实现**。设计对标西安交通大学《材料物理实验教学Agent》（参赛作品），
但把课程域从材料实验换成机械制图，并补上它没有的三块硬能力：**确定性公差计算、圆弧作图、三视图投影**。

---

## 现在能跑什么

| 能力 | 状态 | 说明 |
|---|---|---|
| 知识库装载与切分 | ✅ | 四套切分器；`kb/**/*.md` 按章节切，`kp.jsonl` 按知识点切 |
| 混合检索（BM25 + hashing TF-IDF + jieba） | ✅ | 无需向量数据库，566 块全量点积 < 15ms |
| 双门控（关键词覆盖率 + 单块覆盖率） | ✅ | τ=0.55 / 0.45。**held-out 38 题：课内 29/30、课外 8/8、acc 0.974**（标定集 54 题为 1.000，属拟合，不作泛化性能） |
| SSE 六类事件流 | ✅ | `thinking / token / tool_call / tool_result / artifact / done` + `[DONE]` |
| 工具总线 | ✅ | **11 个工具**，确定性工具走引擎不算模型 |
| 公差与配合计算 | ✅ | GB/T 1800 引擎，31 项锚点全通过（H7/k6、f7、js6、p6…） |
| 圆弧连接几何 | ✅ | 直线-直线/直线-圆弧/圆弧-圆弧外切内切，分步脚本 |
| 螺纹比例画法 | ✅ | M/Tr/G 解析，d₁=0.85d |
| 知识图谱 | ✅ | 169 节点 / 279 边 / 26 问题图谱，接口已通 |
| 自绘教学图库 | ✅ | 15 张 SVG（线型/三视图/三类剖视/公差带/圆弧连接/螺纹/表面结构…），已按知识点自动挂到证据卡 |
| **三视图真投影** | ✅ | 自研 CSG + 隐藏线消除（HLR），8 个模型，14/14 验收通过；长对正/高平齐/宽相等严格成立 |
| **剖视真剖切** | ✅ | 全剖 / **半剖** / **局部剖** 三种：半空间裁剪 + 45° 剖面线（孔洞处自动断开），半剖按中心线拼接、局部剖用波浪线分界 |
| 前端三栏工作台 | ✅ | **9 类画布真实渲染**：evidence / tolerance / graph / annotation / wrongbook / coach / three_view / comparison / quiz |
| 费曼追问 | ✅ | 逐句三色标注 + 追问 + 满三轮总评 + 故意埋错 |
| 剖视辨析 | ✅ | 10 组成对图 + 差异点 + 随堂题 |
| 手绘找茬 | ✅ | 5 类可判定错误（漏画/多画/虚实线/位置/方向），12/12 验收 |
| 出题 | ✅ | 196 道习题（内部版权限制，OCR 待校） |
| 错题六步诊改 | ✅ | 原题→错误作答→根因→溯源→正解→避坑，溯源带出处 |
| **教师端** | ✅ | `GET /admin` 独立页面：语料清单/学情看板/错题根因/待复核清单/重建索引 |
| 会话持久化 | ✅ | 对话写入 SQLite（消息/会话），刷新不掉线 |

> 详细验收证据见 [docs/09-系统实现与验收.md](docs/09-系统实现与验收.md)；
> **交付清单、启动方式、实测数据与已知限制见 [docs/14-交付说明.md](docs/14-交付说明.md)**。

---

## 快速开始

### 1. 起后端

```powershell
cd apps\api
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
# 端到端冒烟（符号抽取 / 切分 / 检索 / 工具 / 对话事件流）
apps\api\.venv\Scripts\python.exe apps\api\tests\smoke.py

# 探针评测（门控与检索质量）
apps\api\.venv\Scripts\python.exe eval\run.py
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

**✅ 已实机验证**：镜像 434 MB，容器 `Up (healthy)`，`/api/health`、`/`、`/admin`、`/api/chat` 全部通过。
多阶段构建（Node 建前端 → Python 运行时 + 构建期预建索引），数据落在 `./data-docker` 卷。
起不来的排查记录见 [docs/16](docs/16-Docker问题排查与修复.md)（daemon.json 带 BOM、死镜像源等）。

### 6. 开发模式起前端

```powershell
cd apps\web
npm install
npm run dev        # 开发：默认 http://127.0.0.1:5173，代理到 8077
npm run build      # 产物进 apps/web/dist，后端会自动托管
```

---

## 目录

```
apps/api/            FastAPI 后端
  app/contracts/     契约（单一事实源，前端类型由它派生）
  app/rag/           符号归一 / 分词 / 切分 / 索引 / 混合检索 + 门控
  app/tools/         工具总线
  app/domain/        确定性领域引擎（公差、螺纹）
  app/geometry/      几何引擎（圆弧连接、投影）
  app/orchestrator.py ReAct 编排 → 事件流
  app/state.py       启动装载 + 模块注册表
apps/web/            React 三栏工作台
kb/                  知识库
  standards/         国标摘录整理（自建，标注标准号）
  knowledge/         自建知识条目 kp.jsonl
  graph/             知识图谱 nodes/edges/questions
  web/               网上采集的开放许可资料
  exercises/         习题（内部，版权受限）
pipeline/            离线构建
eval/                探针集 + 评测脚本
docs/                规划与设计文档（先看 docs/README.md）
data/                索引与数据库（可重建，不入版本库）
```

---

## 关键设计取舍

1. **没有 API Key 也能完整跑**。`MW_LLM_PROVIDER=mock` 时走"本地证据抽取 + 模板作答"，
   等价于参考作品的"本地资料检索，未调用大模型"模式；配上 Key 即自动切真实模型（失败会自动降级）。
2. **能算的绝不让模型背**。公差、螺纹、圆弧、投影全部是确定性引擎，模型只组织语言，
   数值不经过自然语言生成——这是零幻觉的唯一来源。
3. **不引入向量数据库**。语料 1e3 量级，hashing TF-IDF + numpy 全量点积足够；
   接口预留 `Embedder`，将来换真 embedding 只改一个类。
4. **章节路径参与索引**。只索引正文会让"剖视图的概念是什么"这类提问命中率明显偏低。

## 配置

全部在 `apps/api/app/config.py`，可用环境变量覆盖：

| 变量 | 默认 | 含义 |
|---|---|---|
| `MW_SPARSE_WEIGHT` | 0.45 | 混合检索 λ（BM25 通道权重） |
| `MW_GATE_TAU` | 0.50 | 覆盖率门控阈值 |
| `MW_OOV_WEIGHT` | 1.2 | 语料外实义词权重倍数 |
| `MW_LLM_PROVIDER` | mock | `mock` / `deepseek` / `openai-compatible` |
| `MW_LLM_API_KEY` | — | 没有就走 mock |

## 版权说明

- `kb/standards/`、`kb/knowledge/`、`kb/graph/` 是**自建整理内容**（事实性知识 + 自写表述），可自由使用，引用标准时标注标准号。
- `kb/web/` 只收 CC BY-SA / 公有领域 / 政府公开信息，逐份记录来源与许可，见 `kb/_manifest_web.json`。
- `kb/exercises/` 来自教材配套习题集，**版权受限，仅限内部教研**，对外发布必须换源。
