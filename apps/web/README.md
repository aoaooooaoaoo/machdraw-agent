# 核反应堆物理 AI 助教 Agent · 前端工作台（`apps/web`）

三栏工作台前端：**左模块导航 / 中对话 / 右画布**，配顶栏（账号 · 模型 · 连接状态 · 意见反馈）与底部状态栏（消息数 · 证据段数 · 覆盖率 · 耗时）。

- 对话走 `POST /api/chat` 的 **SSE 流**（`fetch` + `ReadableStream`），逐帧渲染思考过程、工具调用、正文流式输出与画布 artifact。
- 画布按 `artifactType` 分发，共 **8 类**：`evidence`（证据+配图）、`calc`（确定性计算卡）、`plot`（纯 SVG 曲线/分布）、`comparison`（成对图辨析）、`annotation`（费曼/步骤标注）、`quiz`（题库题卡）、`wrongbook`（错题诊改）、`graph`（知识图谱）；未知类型回落统一占位。
- 模块清单来自 `GET /api/modules`，中文名不硬编码；画布/示例/自动展开全部走 `features/<id>/index.ts` 自注册，**不改壳**。
- 本工程是 `D:\桌面\教学agent\机械制图agent` 同架构在《核反应堆物理》课程上的复刻；后端契约以 `docs/SPEC-课程对象与数据契约.md` 为唯一事实源。

---

## 1. 技术选型

| 层 | 选型 | 说明 |
|---|---|---|
| 框架 | **React 19 + TypeScript + Vite 6** | 三栏壳 + 模块自注册 |
| 样式 | **原生 CSS 单文件** `src/app.css` | 不引 Tailwind/AntD；CSS 变量做设计令牌 |
| 状态 | **Zustand 5** | 跨子树写入多（右栏追问写中栏、左栏切模块改会话/画布），选择器订阅限制重渲染 |
| 流式 | **fetch + ReadableStream** | `EventSource` 只能 GET，而 `/api/chat` 是 POST 带 body + `X-Account` |
| Markdown | `marked` 15 | 不渲染公式（需求明确） |
| 曲线图 | **纯 SVG（无图表库）** | `modules/plot/chart.ts` 负责 nice 刻度 / log 轴 / 坐标映射，渲染层只摆 SVG |
| 三视图/three.js | **已移除** | 旧 `three_view` 画布由 `plot` 取代，前端不再引 3D 库 |

依赖清单（`package.json`）：`react` `react-dom` `zustand` `marked` + 构建期 `typescript` `vite` `@vitejs/plugin-react` `@types/*`。无全局安装、无全局配置改动。

---

## 2. 安装与启动

前置：后端在 `http://127.0.0.1:8077` 运行（开发期 Vite 代理 `/api` 与 `/figures`）。

```bash
cd apps/web
npm install            # 本工程已随附 node_modules，可跳过

npm run dev            # http://127.0.0.1:5173 ，/api 代理到 127.0.0.1:8077
npm run typecheck      # tsc --noEmit
npm run build          # tsc --noEmit && vite build → dist/
npm run preview        # 预览生产构建（同样带代理，4173）
```

> 接口一律使用相对路径 `/api/...`；开发期由 `vite.config.ts` 代理，生产期前后端同源，**不把后端地址写死进前端**。

---

## 3. 目录结构

```
apps/web/
├── index.html               # 标题 / description：核反应堆物理 AI 助教 Agent
├── package.json             # name: reactor-physics-web
├── tsconfig.json
├── vite.config.ts           # /api、/figures 代理
├── public/
└── src/
    ├── main.tsx
    ├── App.tsx              # 启动态 / 登录态 / 三栏或整页模式（graph.page）
    ├── app.css              # 设计令牌 + 三栏 + 各画布样式（calc/plot 见文件末尾）
    ├── lib/
    │   ├── types.ts         # 契约类型：ArtifactType（8 类）/ CalcData / PlotData / …
    │   ├── sse.ts           # SSE 解析器（容错：脏行、截断、坏 JSON、[DONE]）
    │   ├── api.ts           # health / modules / auth / graph / quiz explain / wrongbook
    │   ├── canvasFeature.ts # ★ 画布自注册契约（CanvasFeature / FeatureProps / preview）
    │   └── store.ts         # Zustand：账号、模块、分模块会话、artifact、统计
    ├── shell/
    │   ├── TopBar.tsx       # 产品名 | 账号 | 模型标识 | 连接状态 | 意见反馈
    │   ├── LeftNav.tsx      # 模块导航（数量/名称来自 /api/modules）
    │   ├── ChatPanel.tsx    # 中栏：消息流 / 空态入口示例 / 输入框
    │   ├── MessageItem.tsx  # 用户气泡 / 思考块 / 工具卡 / 流式光标 / 错误
    │   ├── Markdown.tsx     # marked + 轻量 HTML 清洗
    │   ├── Composer.tsx     # 输入框（Enter 发送 / 附件按钮 / 停止）
    │   ├── CanvasPanel.tsx  # 右栏：registry 分发 + 多画布标签页 + 空态示例
    │   ├── StatusBar.tsx    # N 条消息 · 证据 M 段 · 覆盖率 X% · 耗时 T ms
    │   ├── LoginGate.tsx    # 登录（首次自动建号）
    │   └── Icons.tsx        # 线框图标集
    ├── features/            # ★ 每个画布一个目录（目录名 = id = artifactType）
    │   ├── evidence/index.ts     # order 10
    │   ├── calc/index.ts         # order 20 ← 替代旧 tolerance
    │   ├── plot/index.ts         # order 30 ← 替代旧 three_view
    │   ├── comparison/index.ts   # order 40
    │   ├── annotation/index.ts   # order 50
    │   ├── quiz/index.ts         # order 60
    │   ├── wrongbook/index.ts    # order 70
    │   └── graph/index.ts        # order 80（另有整页 page 组件）
    └── modules/
        ├── registry.ts          # import.meta.glob 扫描 features/*/index.ts
        ├── placeholder/Canvas.tsx
        ├── evidence/Canvas.tsx
        ├── calc/{Canvas.tsx, demo.ts}   # 确定性计算卡
        ├── plot/{Canvas.tsx, chart.ts, demo.ts}  # 纯 SVG 折线图 + 几何计算
        ├── comparison/{Canvas.tsx, demo.ts}
        ├── annotation/Canvas.tsx
        ├── quiz/{Canvas.tsx, demo.ts}
        ├── wrongbook/Canvas.tsx
        └── graph/{Canvas,Overview,FocusView,Questions,constants}.tsx
```

**新增画布** = 新建 `features/<id>/index.ts` + 组件，`id` 必须等于目录名，`artifactTypes` 全局唯一；壳、registry、store 都不用改。`order` 决定 `KNOWN_CANVAS_TYPES` 顺序（= SPEC §4.1 顺序）。

---

## 4. 接口协议与 SSE

### 4.1 对话请求

```http
POST /api/chat
Content-Type: application/json
X-Account: <登录账号>

{"session_id":"local:<module>","messages":[{"role":"user","content":"…"}],
 "feature":{"id":"kinetics","title":"动力学与反应性","persona":"…"}}
```

`feature` 为后端模块身份对象（`__global__` 发 `null`）；后端据此拼系统提示词，新增模块不需要改后端。

### 4.2 事件帧

`data: {json}\n\n` 逐帧下发，结尾 `data: [DONE]\n\n`。

| type | 前端处理 |
|---|---|
| `thinking` | 追加思考块（可折叠，显示字数） |
| `token` | 追加正文，末尾流式光标 `▍` |
| `tool_call` | 新增工具卡（`label` / `name` / `args`），状态"调用中" |
| `tool_result` | 按 `id` 回填：状态"已完成" + `summary` + `detail` |
| `artifact` | 追加到本轮画布列表；右栏按 `artifactType` 切换渲染器 |
| `error` | 消息内红色错误块 + 结束流式 |
| `done` | 写 `data.ms / evidence / coverage`，状态栏收尾 |

### 4.3 解析器容错（`src/lib/sse.ts`）

- 跳过不带 `data:` 前缀的进度行；流式 `TextDecoder` 缓冲，能处理 UTF-8 多字节中间截断；
- 单帧 JSON 解析失败 → 跳过并计数（`dropped`），不中断对话；
- `[DONE]` 后 `cancel()` reader；HTTP 非 2xx 提取 FastAPI `detail` 作为可读错误。

---

## 5. 八类画布渲染器 ↔ `artifactType`

| artifactType | 渲染器 | 说明 |
|---|---|---|
| `evidence` | `modules/evidence/Canvas.tsx` | 证据卡：序号 / 文档名 / 分类 / 章节 / `chunk_id` / 相关度进度条 / 展开全文 / "围绕此段追问"；顶部显示证据数、覆盖率、`配图 N 张`；每卡按相关度配 1 张自绘教学图（点击弹层放大、Esc 关闭） |
| `calc` | `modules/calc/Canvas.tsx` | **确定性计算卡**：标题 → 输入表（量 / 取值 / 单位）→ 计算步骤（`formulas` 逐条编号，等宽公式 + 说明）→ 结果表（量 / 数值 / 单位 / 说明）→ 结论条（`verdict.level` 配色：临界/次临界/超临界）→ 依据（`refs`）→ 可选 `note` / 后端 `svg` |
| `plot` | `modules/plot/Canvas.tsx` | **纯 SVG 折线图**：`series` 多条折线 + 颜色图例 + `markers` 竖虚线/标签 + nice 刻度 + 网格 + 轴标题；`kind==="spectrum"` 或 x 跨度 ≥100× 自动 log10 横轴（标注"对数轴"）；放大弹层（Esc 关闭）；下方 `results` 表、`note`、`refs`；后端若给 `svg` 直接展示 |
| `comparison` | `modules/comparison/Canvas.tsx` | 成对图内联 SVG（`data-pair-id` / `data-panel` / `data-diff`）：点差异点 n → A/B 两图同号高亮、其余变淡；点图内编号反选；空白处开大图（Esc）；内联失败回落 `<img>`，再失败显示"图片加载失败"占位 |
| `annotation` | `modules/annotation/Canvas.tsx` | 费曼/步骤标注：轮次进度、得分、覆盖率、逐句三色色条 + 标签 + 点评；`probes` 可点追问 chip；`final=true` 显示总评 |
| `quiz` | `modules/quiz/Canvas.tsx` | 题库题卡：题号 / 题干 Markdown / 出处 / `chunk_id` / 答案隔离角标 + 题面质量声明；"我先想想"展开才调 `POST /api/quiz/explain`，渲染解析正文 + 来源 + 相关出处 |
| `wrongbook` | `modules/wrongbook/Canvas.tsx` | 六步诊改：原题卡 → 根因 6 选 1 → 竖排时间线（原题/错误作答/根因/溯源/正解/避坑）；溯源内嵌可展开出处卡；写操作 `POST /api/wrongbook` + `GET /api/wrongbook` |
| `graph` | `modules/graph/{Canvas,Overview,FocusView,Questions}.tsx` | 顶部切换「知识图谱 / 问题图谱」。知识图谱：全览星图（章节星系 + 节点 + 关系边、滚轮缩放/拖拽/搜索/悬停）+ 焦点关系（tier 分环、前置路径）；问题图谱：三层递进问题列、Bloom 标签、知识点 chip 跳转。整页模式由 `features/graph/Page.tsx` 提供 |
| 其它未知值 | `modules/placeholder/Canvas.tsx` | 显示 `artifactType` + "尚未在注册表中登记"，绝不抛错 |

### 5.1 `calc` data 契约

```jsonc
{
  "title": "裸圆柱堆次临界校核（单群扩散）",
  "inputs":   [{"name": "无限增殖因数 k∞", "value": 1.06, "unit": "—"}],
  "formulas": [{"step": "M² = L² + τ = 100 + 80 = 180 cm²", "note": "徙动面积"}],
  "results":  [{"name": "有效增殖因数 k_eff", "value": 0.893, "unit": "—", "note": "k_eff < 1 → 次临界"}],
  "verdict":  {"level": "次临界", "note": "Bg² > Bm²，泄漏大于增殖…"},
  "refs":     ["教材 第四章 4.2 节"],
  "note":     "假设：单群扩散、裸圆柱 R = H/2…",
  "svg":      "<svg …>…</svg>"   // 可选，后端预渲染图
}
```

- `value` 可为 number 或 string；number 在画布上按量级格式化为 `3.33×10⁻⁴` 这类形式。
- `verdict.level` 只要含「次临界/超临界/临界」即可自动配色；无 `verdict` 时不显示结论条。

### 5.2 `plot` data 契约

```jsonc
{
  "kind": "curve|spectrum|distribution",
  "title": "点堆阶跃响应（ρ = +0.2$）",
  "x_label": "t / s", "y_label": "n(t) / n₀",
  "series": [{"name": "中子密度 n/n₀", "points": [[0, 1], [0.25, 1.253], …]}],
  "markers": [{"x": 0, "y": 1, "label": "t=0 阶跃 ρ=+0.2$"}],
  "results": [{"name": "渐近周期 T", "value": 51.0, "unit": "s", "note": "1/ω₁"}],
  "note": "示例数据：单组缓发中子近似…",
  "refs": ["教材 第八章 8.2 节"],
  "svg": "<svg …>…</svg>"   // 可选，后端预渲染图
}
```

几何计算在 `modules/plot/chart.ts`（纯函数、可单测）：线性轴用 `niceStep = 1/2/5×10ⁿ` 取整；log 轴取整十次幂，跨度 ≤3 个数量级时补 2/5 倍刻度；所有曲线点裁剪在绘图区内。

### 5.3 本地示例数据（空态入口）

后端未联调时，空态可点示例按钮（画布右上角标「示例」；真实 artifact 到达后优先真实数据）：

| 画布 | demo 文件 | 内容 |
|---|---|---|
| `calc` | `modules/calc/demo.ts` | 裸圆柱堆**次临界校核**：k∞=1.06、L²=100 cm²、τ=80 cm²、R=H/2=89.1 cm → M²=180 cm²、Bm²=3.33×10⁻⁴ cm⁻²、Bg²=1.04×10⁻³ cm⁻²、**k_eff=0.893（次临界）**、临界半径 R_c≈157 cm；refs「教材 第四章 4.2 节」 |
| `plot` | `modules/plot/demo.ts` | **点堆阶跃响应**：ρ=+0.2$=0.0013、β=0.0065、ℓ=1e-4 s、λ=0.0784 s⁻¹；解一阶缓发中子解析式，0~20 s 共 **91 点**；瞬跳比 ≈1.25、渐近周期 ≈51 s、20 s 时 n/n₀≈1.84 |
| `comparison` | `modules/comparison/demo.ts` | 快群 vs 热群（能量范围 / 主导反应 / 临界计算角色 + 随堂题）；图文件 `pairs/PAIR-SPECTRUM.svg`（图库队友产出前会走 `<img>` 兜底/占位） |
| `quiz` | `modules/quiz/demo.ts` | 单群临界条件、停堆碘坑两题；`documentTitle` =「核反应堆物理知识点手册（自建）」 |

> 口径说明：任务书里 calc 示例的 `Bm²=6.67×10⁻⁴` 与 `k_eff=0.893` 在单群公式下不能同时成立（`k_eff = k∞/(1+M²B²)` 只允许一个 B²）。demo 采用**自洽解**：M²=180、材料曲率 Bm²=3.33×10⁻⁴、给定堆芯几何曲率 Bg²=1.04×10⁻³、k_eff=0.893；若把 R 放大到 111.2 cm，则 Bg²≈6.67×10⁻⁴、k_eff≈0.946，仍次临界（demo 注释里写明了这一点）。plot 的「20 s 升到约 11」对应约 +0.5$ 的反应性，按给定的 +0.2$ 如实计算只能到 1.84（注释同样写明）。

一次问答可能推送多个 artifact（如 `plot` + `evidence`、`calc` + `evidence`）。右栏用**标签页**列出本轮全部画布，默认选中最后一个；切换标签即切换渲染器。多画布上限 8 个。

---

## 6. 三栏布局规格

```
顶栏 56px：产品名 | 账号 | 模型标识 | 连接状态 | 意见反馈
──────────────────────────────────────────────────────────
左栏 220px │ 中栏自适应 │ 右栏 clamp(380px, 30vw, 440px)
            │            │
状态栏 34px：N 条消息 · 证据 M 段 · 覆盖率 X% · 耗时 T ms
```

响应式断点：`≤1240` 右栏 360；`≤1120` 左栏收成 68px 图标栏；`≤940` 右栏 320、隐藏模型标识；`≤820` 画布下沉为第二行。

状态栏口径：消息数取当前会话；证据段数取本轮最近 `evidence` artifact 的 `evidences.length`；覆盖率优先 artifact `coverage`，其次 `done` 帧；耗时取 `done.data.ms`；另附本会话累计 SSE 帧数。

---

## 7. 已实现清单

- [x] 三栏布局 + 顶栏 + 底部状态栏；登录页（首次自动建号、密码框回车、后端错误信息）
- [x] 账号存 `localStorage`（key `rp.account`），对话请求带 `X-Account`
- [x] 启动探测 `/api/health`；失败显示红点 + "后端未连接"（点状态 chip 重试）
- [x] 模块导航来自 `GET /api/modules`，点击切换模块 / 会话 / 画布类型
- [x] 消息流：用户气泡 / 助手 Markdown / 思考折叠块 / 工具调用卡 / 流式光标 / 错误块
- [x] 底部输入框：Enter 发送、Shift+Enter 换行、中文输入法不误发、自动增高、停止生成
- [x] 右栏：8 类 artifactType 专用渲染器 + 多画布标签页 + 空态示例（全部走 registry）
- [x] `calc` 画布（输入表 / 编号公式步 / 结果表 / 结论条 / refs / note / 可选 svg）
- [x] `plot` 画布（纯 SVG 折线 + 图例 + 标记 + nice 刻度 + log 轴 + 放大弹层 + 结果表）
- [x] `evidence` 证据卡 + 自绘配图 + 大图弹层
- [x] `comparison` 成对图差异点联动高亮 + 随堂题
- [x] `annotation` 三色逐句标注 + 追问 + 总评
- [x] `wrongbook` 六步诊改 + 错题本写/查
- [x] `quiz` 题卡 + 答案隔离 + `/api/quiz/explain` 解析
- [x] `graph` 全览星图 + 焦点关系 + 问题图谱（整页模式）
- [x] 未知 artifactType 统一占位不崩；`npm run build` / `npm run typecheck` 通过

---

## 8. 已知限制（如实列出）

1. **本轮未连后端做端到端联调**：验收以 `tsc` + `vite build` + `react-dom/server` 渲染 demo 数据为准；SSE 真实链路依赖后端启动。
2. **示例数据与后端工具同构但非同一实现**：`calc`/`plot` demo 的数值由前端按教材公式自算（源码注释给出推导），后端 `critical_calc` / `kinetics_calc` 就绪后以 artifact 为准。
3. **`comparison` demo 的图文件依赖图库队友**：`pairs/PAIR-SPECTRUM.svg` 未产出前会显示"图片加载失败"占位，不影响画布其它区域。
4. **附件按钮仅 UI**：只记录文件名，后端没有上传接口。
5. **意见反馈仅本地**：写入 `localStorage`（`rp.feedback`），后端没有反馈接口。
6. **会话不持久化**：只存内存，刷新即丢；切换模块时各模块会话在内存中保留。
7. **断线不自动重连**：健康检查失败只改状态显示；流式请求失败在消息内显示错误，下次提问重试。
8. **没有单测框架**：`plot/chart.ts` 的几何逻辑用临时 Node 脚本校验（见 §9），未引入 vitest。
9. **公式不渲染**：按需求只用等宽字体呈现公式文本（`calc` 的 `formulas.step`）。
10. **旧画布样式残留**：`app.css` 里保留少量旧 `coach` / 三视图类名（模块已删，不影响构建），后续可清理。

---

## 9. 验证记录

### 9.1 `npm run typecheck` / `npm run build`

```
> reactor-physics-web@0.1.0 typecheck
> tsc --noEmit                       # 通过，无输出

> reactor-physics-web@0.1.0 build
> tsc --noEmit && vite build

vite v6.4.5 building for production...
✓ 76 modules transformed.
dist/index.html                   1.26 kB │ gzip:   0.73 kB
dist/assets/index-Dumz4Ua0.css   75.90 kB │ gzip:  13.41 kB
dist/assets/index-nLieVDnX.js   421.68 kB │ gzip: 132.53 kB
✓ built in ~2s
```

`dist/` 已生成；未启动 dev server、未打开浏览器。

### 9.2 画布渲染校验（无头 `react-dom/server`，临时脚本，已删除）

用 esbuild 打包 `modules/calc/Canvas`、`modules/plot/Canvas` + demo 数据，`renderToStaticMarkup` 后断言 **31/31 通过**，关键项：

| 项 | 结果 |
|---|---|
| calc 标题 / 输入表 / 5 条编号公式 | ✅ |
| calc 科学计数法 `3.33×10⁻⁴`、`1.04×10⁻³` | ✅ |
| calc `k_eff=0.893` + 结论条 `次临界`（配色类 `is-under`） | ✅ |
| calc 依据「教材 第四章 4.2 节」 | ✅ |
| plot 生成 `<svg>` + `<path d="M…">` 折线 | ✅ |
| plot 轴标题 `t / s`、`n(t) / n₀`、标记标签、图例、结果表 | ✅ |
| plot demo 91 点、x 单调、y 有限 | ✅ |
| 曲线点全部落在绘图区包围盒内 | ✅ |
| `kind=spectrum` 自动 log 轴、刻度 `10⁻³ … 10⁷` 等距 | ✅ |
| features 目录 8 个、id=目录名、order 顺序 = evidence/calc/plot/comparison/annotation/quiz/wrongbook/graph | ✅ |

---

## 10. 契约来源（改契约先改后端/SPEC）

- `docs/SPEC-课程对象与数据契约.md` §4 —— 八类画布、`calc` / `plot` data 契约、模块与工具
- `apps/api/app/contracts/models.py` —— 事件类型、`ARTIFACT_TYPES`、`Evidence`、`ModuleManifest`
- `apps/api/app/events.py` —— SSE 帧序列化与 `[DONE]` 哨兵
- `apps/api/app/orchestrator.py` —— 事件产生顺序、`done.data` 字段、各工具 artifact 形状
- `GET /api/graph` / `GET /api/graph/node/{id}` —— 全量知识图谱与焦点详情（模块级缓存）
- `GET /api/figures` / `GET /figures/<file>` —— 自绘教学图库（`evidence.data.figures` 引用；`/figures` 走 Vite 代理）
- `POST /api/quiz/explain` —— 题卡解析（body `{chunk_id}`）
- `GET /api/pairs` / `GET /figures/pairs/<file>.svg` —— 成对图数据与静态 SVG（`comparison.file`）
- 已移除：`GET /api/models` / `GET /api/models/{id}`（旧 three_view 画布专用，随画布一并删除）
