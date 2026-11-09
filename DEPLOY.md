# DEPLOY · 部署与运维手册

> 适用对象：`D:\桌面\教学agent\核反应堆物理agent`（核反应堆物理 AI 助教 Agent）
> 三种启动方式（本地后端 / 前端 dev / Docker）、环境变量全表、Render 部署、健康检查、常见故障、备份与重建。
> 契约与验收口径见 `docs/SPEC-课程对象与数据契约.md`；交付清单与已知限制见 `docs/10-交付说明.md`。

---

## 0. 环境要求

| 项 | 版本/路径 | 说明 |
|---|---|---|
| Python | **3.12**（本项目 venv 实测 `Python 3.12.7`） | 后端 + 流水线 + 评测 |
| Node.js | **22.x**（实测 `v22.19.0`，npm `10.9.3`） | 前端构建（Docker 里用 `node:22-alpine`） |
| 项目 venv | `apps\api\.venv\Scripts\python.exe` | 已存在，直接用；下文 `PY` 均指它 |
| 依赖 | `apps/api/requirements.txt`：fastapi / uvicorn[standard] / pydantic / numpy / jieba | 无 scipy、无向量数据库、无 ORM |
| Docker | 可选（compose v2） | 方式三使用 |

端口约定（**改端口会连带改代理/脚本，见 §7.2**）：

| 端口 | 用途 | 谁在用 |
|---|---|---|
| **8077** | 后端 FastAPI | 本地 uvicorn、`verify_all.py`、`vite` 代理目标 |
| **5173** | 前端 dev server | `npm run dev`，`/api`、`/figures` 代理到 8077 |
| 4173 | 前端 preview | `npm run preview`（同样代理到 8077） |
| 8093 | 端到端自检临时服务 | `scripts/e2e_check.py` 自己起、自己停 |

---

## 1. 方式一：本地后端（venv + uvicorn）

```powershell
cd D:\桌面\教学agent\核反应堆物理agent

# 1) （首次）建索引：kb/ 变化后都必须重跑；约 2–5 秒
apps\api\.venv\Scripts\python.exe pipeline\build_kb.py

# 2) 起服务（开发热重载）
apps\api\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8077 --reload --app-dir apps/api
```

> **`--app-dir apps/api` 不能省**：`main.py` 用的是包内相对导入（`from .config import …`），import 根必须是 `apps/api`，模块名才是 `app.main:app`。

（重建 venv 时才需要）

```powershell
py -3.12 -m venv apps\api\.venv
apps\api\.venv\Scripts\python.exe -m pip install -r apps\api\requirements.txt
```

访问：

| URL | 内容 |
|---|---|
| <http://127.0.0.1:8077/> | 前端（读 `apps/web/dist/index.html`；未构建时返回 JSON 提示） |
| <http://127.0.0.1:8077/docs> | FastAPI 自动生成的接口文档 |
| <http://127.0.0.1:8077/api/health> | 装载状态（chunks/docs/nodes/edges/tools/warnings） |
| <http://127.0.0.1:8077/admin> | 教师端（语料清单/学情看板/错题根因/待复核/重建索引） |

停止：在启动它的那个终端按 `Ctrl+C`。**如需按 PID 结束，只结束你自己启动的那个 PID**：

```powershell
Get-NetTCPConnection -LocalPort 8077 -State Listen | Select-Object OwningProcess
Stop-Process -Id <上面查到的PID>        # 只在你确认它是本项目的 uvicorn 时才执行
```

---

## 2. 方式二：前端（dev 代理 / 生产同源）

### 2.1 开发模式（5173 代理到 8077）

```powershell
cd apps\web
npm install          # 首次
npm run dev          # http://127.0.0.1:5173
```

`vite.config.ts` 已把 `/api` 与 `/figures` 代理到 `http://127.0.0.1:8077`（`changeOrigin: true`），所以前端代码里一律相对路径。
前置：8077 后端必须先起。

### 2.2 生产构建（同源，由后端托管）

```powershell
cd apps\web
npm run typecheck    # tsc --noEmit
npm run build        # tsc --noEmit && vite build → dist/
cd ..\..
# 后端会自动托管 apps/web/dist：/ → index.html，/assets → dist/assets，/figures → kb/figures
```

要点：
- 后端只挂载 `/assets` 与 `/figures` 两个静态目录（见 `apps/api/app/main.py`），`/` 与 `/admin` 是显式路由；
- **没有 SPA fallback**：新增前端页面请用 query/hash，或在后端加路由；
- `dist/` 已在 `.gitignore`，部署时要么本地构建，要么交给 Docker 阶段 1。

---

## 3. 方式三：Docker / docker compose

```powershell
# 构建 + 启动（首次约 3–6 分钟：node 依赖 + pip + 建索引）
cd D:\桌面\教学agent\核反应堆物理agent
docker compose up -d --build

# 看日志 / 健康
docker compose logs -f reactor-physics
docker inspect --format '{{.State.Health.Status}}' reactor-physics-agent

# 停止（保留数据卷）
docker compose down
```

- 镜像：`reactor-physics-agent:0.1`，两阶段构建（`node:22-alpine` 出 `dist` → `python:3.12-slim` 跑 uvicorn），**镜像内已执行 `python pipeline/build_kb.py`**（`Dockerfile` 第 36 行）。
- 端口：`HOST_PORT`（默认 8077）→ 容器 8077；健康检查跟随平台注入的 `$PORT`。
- 数据：`./data-docker:/app/data`（SQLite：账号/会话/错题/埋点）。**删卷 = 清空账号与学情。**
- 改了 `kb/` 必须 `docker compose up -d --build` 重建镜像（索引在镜像里）；只想热重载不重建时可进容器 `POST /api/admin/reload`，但容器重启会丢。

单容器等价命令：

```powershell
docker build -t reactor-physics-agent:0.1 .
docker run -d --name reactor-physics-agent -p 8077:8077 -v ${PWD}/data-docker:/app/data `
  -e RP_LLM_PROVIDER=mock reactor-physics-agent:0.1
```

---

## 4. Render 部署（公网免费档）

`render.yaml` 已就绪（Blueprint 方式）：

1. Render → **New → Blueprint** → 选中仓库 → Apply；
2. 服务名 `reactor-physics-agent`，`runtime: docker`，`healthCheckPath: /api/health`；
3. **在控制台填 key**（不进仓库）：Service → Environment → `RP_LLM_API_KEY = sk-xxxx`（`render.yaml` 里该变量是 `sync: false`）；
   默认 `RP_LLM_PROVIDER=mock`，**不填 key 也能完整演示**（本地抽取式作答）；
4. 首次构建约 5–8 分钟（node 依赖 + pip + 建索引）；
5. 免费档特性（写进 `render.yaml` 注释）：**15 分钟无访问休眠，下次访问约 40 秒唤醒**；512 MB 内存（运行时约 250–300 MB）；**无持久盘，重启会清空 SQLite**。

切真实模型（示例，线上当前用的是讯飞星辰免费模型）：

```
RP_LLM_PROVIDER = openai-compatible
RP_LLM_MODEL    = spark-x2.6-4b
RP_LLM_BASE_URL = https://maas-api.cn-huabei-1.xf-yun.com/v2
RP_LLM_API_KEY  = <在 Render 控制台填，不进仓库>
# 星火必须关思维链，否则单次 100s+：
RP_LLM_EXTRA_BODY = {"thinking":{"type":"disabled"}}
```

DeepSeek 也可以：

```
RP_LLM_PROVIDER = deepseek
RP_LLM_MODEL    = deepseek-chat
RP_LLM_BASE_URL = https://api.deepseek.com/v1
RP_LLM_API_KEY  = sk-xxxx
```

---

## 5. 环境变量全表

加载顺序：**真实环境变量 > `ROOT/.env` > `ROOT/apps/api/.env`**（`load_dotenv(override=False)`）。`.env` 已在 `.gitignore`，**不要提交 key**；本仓库没有 `.env.example`，可自建：

```powershell
Copy-Item apps\api\.env.example apps\api\.env   # 若存在；否则新建 apps\api\.env 只写 key 两行
```

### 5.1 `RP_` 业务变量（14 个，全部有默认值，不配也能跑）

| 变量 | 默认 | 作用 | 何时改 |
|---|---|---|---|
| `RP_SPARSE_WEIGHT` | `0.45` | 混合检索的 BM25 权重 λ | 重标定检索时 |
| `RP_GATE_TAU` | **`0.40`** | IDF 加权覆盖率门控 τ（标定：课内 min 0.471 / 课外 max 0.326） | 改语料后重标定 |
| `RP_GATE_TAU_CHUNK` | **`0.25`** | 单块覆盖率门限（标定：课内 min 0.284 / 课外 max 0.223） | 同上 |
| `RP_OOV_WEIGHT` | `1.2` | 语料外实义词的权重倍数 | 拒答过松/过紧时 |
| `RP_COVERAGE_MODE` | `docs` | 覆盖率口径：`docs`（按召回块）/ `corpus`（按全库词表） | 语料变大后可试 corpus |
| `RP_GATE_RARE_K` | `2` | 保留配置项（当前实现未使用） | 一般不动 |
| `RP_RECALL_K` | `24` | 单通道召回数 | 语料变大时调高 |
| `RP_TOP_K` | `6` | 送 LLM 的证据条数 | 回答质量 vs 成本 |
| `RP_LLM_PROVIDER` | `mock` | `mock` / `deepseek` / `openai-compatible` | 接真实模型时 |
| `RP_LLM_MODEL` | `deepseek-chat` | 模型名 | 同上 |
| `RP_LLM_BASE_URL` | `https://api.deepseek.com/v1` | OpenAI 兼容端点 | 第三方/自建时 |
| `RP_LLM_API_KEY` | 空（回落 `DEEPSEEK_API_KEY`） | 密钥 | 接真实模型时 |
| `RP_LLM_EXTRA_BODY` | 空 | 追加请求体 JSON（如关思维链） | 推理模型变慢时 |
| `RP_INTERNAL_ONLY` | `1` | `1`=允许版权受限内容入库/检索 | 对外发布改 `0` 前先看 §8 版权边界 |

非 env 的硬编码常量（改代码才变）：`MAX_EVIDENCE_CHARS=1400`、`HASH_DIM=4096`、`MAX_CHUNK_CHARS=350`、`MIN_CHUNK_CHARS=60`、`DB_PATH=data/app.db`。

### 5.2 平台/进程变量

| 变量 | 默认 | 作用 |
|---|---|---|
| `PORT` | `8077` | 容器/Render 注入；`Dockerfile` 的 `CMD` 与健康检查都读它 |
| `PYTHONIOENCODING` | `utf-8` | Windows 中文控制台/日志不乱码（`Dockerfile`、`render.yaml` 已设） |
| `HOST_PORT` | `8077` | 仅 `docker-compose.yml` 用（宿主机映射端口） |

### 5.3 ⚠ 两个必须注意的覆盖问题

1. **`docker-compose.yml` 里显式写了旧标定值**：
   ```yaml
   RP_GATE_TAU: "0.55"
   RP_GATE_TAU_CHUNK: "0.45"
   ```
   它会**覆盖**代码里已按本课程标定好的 `0.40 / 0.25`。用 compose 部署前请把这两行改成 `0.40 / 0.25` 或直接删掉（删掉即用代码默认值）。
2. **`Dockerfile` 里 `ENV RP_LLM_PROVIDER=mock`** 是镜像默认值；compose/Render 若另设 provider，以平台注入的为准（env 优先于镜像 `ENV`）。

---

## 6. 健康检查与自检

### 6.1 `GET /api/health` 怎么看

```json
{"ok": true, "model": "mock(extractive-local)", "provider": "mock",
 "has_key": false, "llm_ready": false,
 "tools": ["kb_search", "...共 11 个"],
 "chunks": 394, "docs": 15, "nodes": 175, "edges": 280,
 "sparse_weight": 0.45, "gate_tau": 0.4,
 "warnings": []}
```

| 字段 | 期望 | 异常含义 |
|---|---|---|
| `ok` | `true` | — |
| `chunks/docs` | `394 / 15`（本仓库实测，会随 kb 变化） | 0 = 索引未建/知识库空 |
| `nodes/edges` | `175 / 280` | 0 = `kb/graph/*.jsonl` 缺失 |
| `tools` | 11 个 | 少 = 工具文件缺失/注册失败 |
| `has_key` / `llm_ready` | mock 模式下 `false/false` 是**正常** | `provider` 非 mock 而 `llm_ready=false` = 没读到 key，会回落 mock |
| `warnings` | `[]` | 任何非空都应在交付前消掉（图谱/图库/辨析对缺失、索引载入失败等） |

### 6.2 自检脚本（按侵入性从低到高）

```powershell
cd D:\桌面\教学agent\核反应堆物理agent
$PY = "apps\api\.venv\Scripts\python.exe"

# ① 规模统计（只读）
& $PY scripts\kb_stats.py

# ② 知识图谱/知识点正反向校验（只读）
& $PY kb\graph\_check.py

# ③ 确定性引擎锚点：68 条（只读）
& $PY apps\api\tests\run_anchors.py

# ④ 工具契约 / 可达性（只读）
& $PY apps\api\tests\check_tools.py
& $PY apps\api\tests\check_reachability.py

# ⑤ 端到端冒烟（进程内，会建 data/app.db）
& $PY apps\api\tests\smoke.py

# ⑥ 端到端 HTTP + SSE + 前端托管（脚本自己起 8093 服务、自己停）
& $PY scripts\e2e_check.py

# ⑦ LLM 连通性（不写文件；--list 只看配置）
#    注意：该脚本的提示文案里仍残留旧前缀 MW_（实际读的是 RP_），以 RP_ 为准
& $PY scripts\check_llm.py --list
& $PY scripts\check_llm.py

# ⑧ 一键全量（要求 8077 已有服务在跑）
& $PY verify_all.py
```

`verify_all.py` 的检查项（5 项 + 评测 + 服务健康 + `dist` 产物）：

| # | 项 | 失败常见原因 |
|---|---|---|
| 1 | 工具自注册（11 个） | 工具文件缺失/`TOOL.name` 与文件名不一致 |
| 2 | 确定性引擎锚点 | 引擎数值回归 |
| 3 | 模块/工具/画布可达性 | `state.MODULES` 声明了不存在的工具/画布 |
| 4 | 端到端冒烟（对话+8 画布） | 知识库/图谱/辨析对缺失 |
| 5 | 模块任务书与代码一致（非必需） | 改了 state/tools/features 未重跑文档生成器 |
| — | 检索与门控（54 题） | 索引未建、阈值被环境变量改坏 |
| — | 服务健康 | 8077 未起 |
| — | 前端构建产物 | 未 `npm run build` |

---

## 7. 常见故障

### 7.1 端口被占用（`[Errno 10048]` / `address already in use`）

**症状**：`uvicorn` 启动即退出，日志 `error while attempting to bind on address ('127.0.0.1', 8077)`。

**处理**：
```powershell
Get-NetTCPConnection -LocalPort 8077 -State Listen | Select-Object LocalPort, OwningProcess
Get-Process -Id <PID> | Select-Object Id, ProcessName, Path
```
- 如果它是**你刚启动的旧 uvicorn**：只结束这个 PID（`Stop-Process -Id <PID>`）；
- 如果是**别人的程序**：不要杀，改用 8078 起服务（见 7.2）；
- 不要用 `taskkill /IM python.exe` 这类按名称杀进程的写法——会连带杀掉用户/队友的其它 Python 进程。

### 7.2 8077 有冲突、改用 8078 —— 但要同步三处

后端可以换端口，**前端代理与自检脚本是写死 8077 的**，只改后端会出现"页面能开、接口 502"：

| 位置 | 内容 | 改法 |
|---|---|---|
| uvicorn | `--port 8077` | 改 8078 |
| `apps/web/vite.config.ts` | dev/preview 的 `/api`、`/figures` 代理 `target: http://127.0.0.1:8077` | 改 8078（并重启 `npm run dev`） |
| `verify_all.py:48` | `http://127.0.0.1:8077` | 改 8078 |
| `scripts/e2e_check.py` | 自己起 8093（独立端口，不受影响） | 不用改 |

> 生产同源部署（后端托管 `dist`）没有代理问题；换端口只影响本地联调。

### 7.3 索引未建 / 知识库为空

**症状**：`/api/health` 的 `chunks=0`；日志或 `warnings` 有「知识库为空：kb/ 下没有可检索内容，请先运行 pipeline/build_kb.py」；提问一律「知识库未收录」。

**原因**：`data/index/` 不存在且 `kb/` 里确实没有可切分内容（或只有空目录）。

**处理**：
```powershell
apps\api\.venv\Scripts\python.exe pipeline\build_kb.py     # 会打印分块数/文档数/词表大小
# 服务已在跑时也可以热重载：
curl.exe -X POST http://127.0.0.1:8077/api/admin/reload
```
> 首次启动在 `kb/` 正常时会**自动建索引**（`state.load_state` 检测不到 `data/index/chunks.jsonl` 就现场切分+建索引），所以"未建索引"通常只意味着 `kb/` 是空的。

### 7.4 缺 API key（provider 设了但没 key）

**症状**：`/api/health` 显示 `provider: "deepseek"` 但 `has_key: false, llm_ready: false`；回答仍是「结论/依据/出处」模板风格；前端工具卡正常、但答案像抽取式。

**原因与行为**：`llm.generate()` 里 `provider == "mock" or not LLM_API_KEY` → 直接走本地抽取式（**不报错、不中断**）。这是设计好的降级，不是故障。

**处理**：在 `apps/api/.env` 写 `RP_LLM_API_KEY=sk-xxxx`（或设系统环境变量，优先级更高），重启服务；用 `scripts/check_llm.py` 验证连通性。

### 7.5 `/api/health` 的 `warnings` 非空

| warning 文本 | 含义 | 处理 |
|---|---|---|
| `知识图谱未装载（kb/graph/nodes.jsonl 缺失或为空）` | 图谱组未产出/文件路径不对 | 恢复 `kb/graph/*.jsonl` |
| `教学图形库未装载（kb/figures/figures.jsonl 缺失或为空）` | 图库未产出 | 恢复 `kb/figures/` |
| `辨析图库未装载（kb/figures/pairs.jsonl 缺失或为空）` | 辨析对未产出 → comparison 画布不可达、`smoke`/`e2e` 会红 | 恢复 `kb/figures/pairs.jsonl`（本仓库已落盘 8 组；再出现说明文件被移走/未随镜像构建） |
| `索引载入失败(XxxError)，已重建` | `data/index/` 损坏 | 已自动重建；仍异常则删 `data/index/` 后重跑 `build_kb.py` |
| `知识库为空：…` | 见 7.3 | 见 7.3 |

### 7.6 中文乱码（控制台/日志）

**症状**：PowerShell 输出 `�`；SSE 中文正常但日志乱码。

**处理**：
```powershell
$env:PYTHONIOENCODING = "utf-8"
chcp 65001
```
容器镜像与 `render.yaml` 已设 `PYTHONIOENCODING=utf-8`；`main.py` 的 SSE 用 `json.dumps(..., ensure_ascii=False)` + `charset=utf-8`，浏览器端一般不会乱。

### 7.7 SSE 看起来"卡住/一次性全出来"

**原因**：中间有反向代理缓冲。本项目响应头已带 `Cache-Control: no-cache` 与 `X-Accel-Buffering: no`（`main.py` 的 `/api/chat`），所以 nginx 需确保 `proxy_buffering off;`；Render 直连无需处理。

**排查**：浏览器 Network → `/api/chat` → Response Headers 是否 `content-type: text/event-stream`；前端解析器对脏帧/缺 `data:` 前缀的行是容错的（`lib/sse.ts`），若整条流无输出，先看后端是否 500。

### 7.8 前端 502 / 跨域 / `/api` 404

| 现象 | 原因 | 处理 |
|---|---|---|
| dev 页 502 | 8077 后端没起 | 起后端（§1） |
| dev 页 `/api/...` 404 但后端 docs 正常 | 代理 target 端口不对 | 见 7.2 |
| 生产页白屏但 `/api/health` 正常 | `apps/web/dist` 不存在 | `cd apps/web; npm run build` |
| 生产页 `/assets/*` 404 | 后端启动时 `dist/assets` 不存在（启动时一次性挂载） | 先 build 再起 uvicorn |
| 登录后立刻掉登录 | 浏览器禁 localStorage / 换域访问 | 用同一 origin；检查隐私模式 |

### 7.9 Docker 相关

| 现象 | 原因 | 处理 |
|---|---|---|
| 改 `kb/` 后线上还是旧答案 | 索引在镜像层里 | `docker compose up -d --build` |
| 容器起但 `/api/health` 502 | 容器内 8077 未监听/健康检查端口不匹配 | `docker logs`；确认 `PORT` 与 `EXPOSE` |
| 账号/错题重启后消失 | 没挂 `data-docker` 卷，或用了无持久盘的平台 | 挂卷；Render 免费档无持久盘（§4） |
| `npm ci` 失败 | `package-lock.json` 与 `package.json` 不同步 | 本地 `npm install` 后提交 lock |
| 构建时 `RUN python pipeline/build_kb.py` 失败 | `kb/` 未 COPY 或为空 | 检查 `.dockerignore` 是否误排 `kb/` |

### 7.10 Render / 平台

| 现象 | 说明 |
|---|---|
| 首次访问 ~40 秒白屏 | 免费档休眠唤醒，正常 |
| 部署后 502 | 构建失败/健康检查未过；看 Deploy Logs 是否 `chunks=0` |
| 填了 key 仍显示 mock | `RP_LLM_PROVIDER` 还是 `mock`，或 key 变量名写错（应为 `RP_LLM_API_KEY`） |
| 构建超时 | 免费档 5–8 分钟属正常；减少 `node_modules` 缓存问题可重试 |

---

## 8. 备份与重建

### 8.1 重建检索索引（kb 变化后的标准动作）

```powershell
# 方式 A：离线流水线（推荐，能看到统计）
apps\api\.venv\Scripts\python.exe pipeline\build_kb.py

# 方式 B：服务在跑时热重载（重建内存态；不重写 data/index）
curl.exe -X POST http://127.0.0.1:8077/api/admin/reload
```

产物：`data/index/{chunks.jsonl, vecs.npy, meta.json}`（可随时删，重建无副作用）。

### 8.2 备份 / 恢复 SQLite（账号、会话、错题、学情）

```powershell
# 备份（服务运行时也可执行；为了绝对一致可先停服务）
Copy-Item data\app.db data\app.db.bak-20261109

# 恢复
Copy-Item data\app.db.bak-20261109 data\app.db -Force
```

- `data/` 与 `data-docker/` 均在 `.gitignore`；**不要提交**。
- 容器部署：备份 `data-docker/` 整个目录（或平台持久卷）。
- 数据库结构由 `app/db.py` 启动时 `CREATE TABLE IF NOT EXISTS` 自动建，**没有迁移脚本**；改表结构需手写 `ALTER`/重建。

### 8.3 知识库内容变更流程（防"改了没生效"）

```
改 kb/  →  python pipeline/build_kb.py  →  （服务在跑）POST /api/admin/reload  →  /api/health 看 chunks/词表变化
        →  跑 eval/run.py（门控是否仍达标）→  跑 smoke.py / e2e_check.py
```

---

## 9. 部署检查清单

| # | 检查 | 命令/位置 | 期望 |
|---|---|---|---|
| 1 | 依赖装齐 | `apps\api\.venv\Scripts\python.exe -c "import fastapi,numpy,jieba"` | 无报错 |
| 2 | 索引已建 | `data\index\chunks.jsonl` 存在 / `pipeline\build_kb.py` 输出 | 分块数 >0 |
| 3 | 服务健康 | `GET /api/health` | `ok=true`、`chunks=394`、`warnings=[]` |
| 4 | 工具注册 | `check_tools.py` | 11 个工具、全部通过 |
| 5 | 引擎锚点 | `run_anchors.py` | 68/68 |
| 6 | 可达性 | `check_reachability.py` | 全绿 |
| 7 | 端到端 | `smoke.py` / `e2e_check.py` | 全绿（本仓库实测 smoke 27/27、e2e 16/16） |
| 8 | 前端产物 | `apps\web\dist\index.html` | 存在（否则 `npm run build`） |
| 9 | 教师端 | `GET /admin` | 返回 HTML，KPI 有数字 |
| 10 | 配置 | `RP_` 变量与 §5 一致；compose 里没有旧 `0.55/0.45` | 见 §5.3 |
| 11 | 数据卷 | `data-docker/` 可写、已挂载 | 重启后账号还在 |
| 12 | 文档一致 | `scripts\gen-module-docs.py --check` | exit 0 |

---

## 11. 实装：让别人电脑用浏览器打开（本机发布）

> 目标：老师/同学在**另一台电脑**上点开一个网址就能用，不需要装 Python、不需要本机同步。

### 11.1 一键发布（推荐）

```powershell
cd D:\桌面\教学agent\核反应堆物理agent
powershell -ExecutionPolicy Bypass -File scripts\serve_public.ps1
```

脚本做三件事，并在 10 秒内打印访问地址：

1. 用 `D:\python\python.exe`（Windows 防火墙已有它的入站放行规则）在 `0.0.0.0:8077` 起后端；
2. 用 localhost.run 的 SSH 反向隧道（免注册）生成公网 HTTPS 地址 `https://xxxx.lhr.life`；
3. 打印 **局域网地址**（`http://<本机IP>:8077/`）与 **公网地址**，并写入 `data/public_url.txt`。

停止：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\stop_serve.ps1
```

### 11.2 两种访问方式怎么选

| 场景 | 用哪个地址 | 前提 |
|---|---|---|
| 同一校园网/办公室网 | `http://<本机IP>:8077/`（脚本会打印，如 `http://10.180.239.226:8077/`） | 对方与你在**同一局域网**且未被网络隔离；本机开机 |
| 任何网络（含手机 4G/5G） | `https://xxxx.lhr.life/` | 本机开机、不休眠；脚本在运行 |

> 公网地址是**临时隧道**：本机重启、断网、隧道进程退出后 URL 会变，重新跑一次脚本即可。
> 需要**永久固定地址**（像旧项目的 `machdraw-agent.onrender.com`）请走 §4 Render 部署，把本仓库推到 GitHub 后在 Render 控制台 Apply `render.yaml`。

### 11.3 安全与合规（务必看）

- **公网链接 = 任何拿到链接的人都能访问**。教师端 `/admin` 也走同一地址（本版无独立鉴权），只发给班级/课程组，不要公开发帖。
- 知识库含**课程内部资料**（习题 `internal_only=true`、教材整理）；对外发布/二次分发前请先看 `docs/11-待人工复核清单.md` 的版权与复核项。
- 想临时收回：跑一次 `scripts\stop_serve.ps1` 即可，端口与公网隧道一起关闭。
- 本机保持开机、关闭睡眠；脚本/后端/隧道都是独立进程，**关闭终端窗口不会停止服务**。
- 若接真实大模型，在 `apps/api/.env` 写 `RP_LLM_PROVIDER=deepseek` + `RP_LLM_API_KEY=...` 后重启后端；不配 Key 也可完整使用（本地抽取模式）。

### 11.4 排障

- 公网 502：本机后端没起来或隧道刚连上——先看 `data/serve_lan.log` 与 `%TEMP%\rp_ssh_tunnel.log`，再重跑脚本。
- 局域网打不开：确认对方同网段；Windows 防火墙需放行 `D:\python\python.exe`（本机已有该规则）。
- 换端口：改脚本里的 `--port` 与隧道 `-R 80:localhost:8077` 两处。

### 11.5 永久在线地址（Render，已部署）

- 学生端：<https://reactor-physics-agent.onrender.com/>
- 教师端：<https://reactor-physics-agent.onrender.com/admin>
- 健康检查：<https://reactor-physics-agent.onrender.com/api/health>

| 项 | 值 |
|---|---|
| GitHub 仓库 | `aoaooooaoaoo/machdraw-agent`，分支 **`reactor-physics`** |
| Render 服务 | `reactor-physics-agent`（Web Service / Docker / Free / Oregon） |
| 源码提交 | 该分支最新 commit（当前 `e0dfa1c`） |
| 构建 | Render 用仓库根 `Dockerfile` 两阶段构建（Node 建前端 → Python 运行时 + 构建期预建索引） |
| 更新 | 改完代码 `git push` 到 `reactor-physics` 分支 → Render 自动重新部署 |
| 休眠 | 免费档 15 分钟无访问休眠，冷启动约 40~60 s |
| 数据 | 免费档无持久磁盘：`data/app.db` 重启即重置；知识库/索引在镜像内，随代码重建 |

> 本机 Docker（`docker compose up -d --build`）未实机复测（本机 Docker Desktop 未启动），但**同一份 `Dockerfile` 已由 Render 在 Linux 上构建并运行成功**，可视为镜像可用性的证据。

