# 机械制图 AI 助教 Agent · 前端工作台（`apps/web`）

三栏工作台前端：**左模块导航 / 中对话 / 右画布**，配上顶栏（账号 · 模型 · 连接状态 · 意见反馈）与底部状态栏（消息数 · 证据段数 · 覆盖率 · 耗时）。

- 对话走 `POST /api/chat` 的 **SSE 流**（`fetch` + `ReadableStream`），逐帧渲染思考过程、工具调用、正文流式输出与画布 artifact。
- 画布按 `artifactType` 切换渲染器：`evidence`（证据+配图）、`tolerance`（公差带）、`graph`（知识图谱 + 问题图谱）、`annotation`（三色标注）、`wrongbook`（六步诊改）、`coach`（作图分步）、`three_view`（真三视图 SVG）、`comparison`（成对图辨析）、`quiz`（题卡）均为专用渲染器；未知类型才回落统一占位。
- 模块清单来自 `GET /api/modules`，中文名不硬编码。

---

## 1. 技术选型

| 层 | 选型 | 说明 |
|---|---|---|
| 框架 | **React 19 + TypeScript + Vite 6** | 按任务书指定 |
| 样式 | **原生 CSS 单文件** `src/app.css` | 不引 Tailwind/AntD，减少依赖；CSS 变量做设计令牌 |
| 状态 | **Zustand 5** | 见下方"为什么不用 useReducer" |
| 流式 | **fetch + ReadableStream** | `EventSource` 只能 GET，而 `/api/chat` 是 POST 带 body + `X-Account` |
| Markdown | `marked` 15 | 不渲染公式（需求明确） |
| 三视图 | **纯 SVG** | 后端已下发排版好的图纸坐标，前端只画 SVG；three.js 已移除（首屏/懒加载各减一个 chunk） |

### 为什么选 Zustand 而不是 useReducer

1. 工作台里跨子树写入很多：右栏"围绕此段追问"要写中栏输入框、左栏切模块要同时改 `feature`/会话/画布/顶栏。Zustand 的 store 可直接在任意组件读写，不用把 provider 层层包进三栏。
2. 流式 token 每帧都要更新一条消息。Zustand 的选择器订阅能把重渲染限制在消息流与状态栏，不必把整个 App 塞进一个 reducer 里重渲染。
3. 会话天然按模块分片（`sessions[featureId]`），是"对象 key 索引"结构，reducer 的 switch 反而更啰嗦。

依赖清单（`package.json`）：`react` `react-dom` `zustand` `marked` + 构建期 `typescript` `vite` `@vitejs/plugin-react` `@types/*`。无全局安装、无全局配置改动。

---

## 2. 安装与启动

前置：后端已在 `http://127.0.0.1:8077` 运行（前端开发期通过 Vite 代理访问它）。

```bash
cd apps/web
npm install

# 开发：http://127.0.0.1:5173 ，/api 自动代理到 127.0.0.1:8077
npm run dev

# 类型检查（tsc --noEmit）
npm run typecheck

# 生产构建：产物 dist/，后端 main.py 会在 / 托管它
npm run build

# 预览生产构建（同样带 /api 代理，端口 4173）
npm run preview
```

> 页面里的接口一律使用相对路径 `/api/...`，开发期由 `vite.config.ts` 代理，生产期前后端同源，**不会把后端地址写死进前端**。

---

## 3. 目录结构

```
apps/web/
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts          # /api 代理 + 生产/预览配置
├── public/
│   └── favicon.svg
└── src/
    ├── main.tsx            # React 挂载
    ├── App.tsx             # 启动态 / 登录态 / 工作台三栏
    ├── app.css             # 全部样式（设计令牌 + 三栏 + 画布 + 响应式）
    ├── lib/
    │   ├── types.ts        # 契约类型（镜像 apps/api/app/contracts/models.py）
    │   ├── sse.ts          # ★ SSE 解析器（独立模块，可单测）
    │   ├── api.ts          # /api/health、/api/modules、/api/auth/login
    │   └── store.ts        # Zustand：账号、模块、分模块会话、artifact、统计
    ├── shell/
    │   ├── TopBar.tsx      # 产品名 | 账号 | 模型标识 | 连接状态 | 意见反馈
    │   ├── LeftNav.tsx     # 9 个模块（来自 /api/modules）
    │   ├── ChatPanel.tsx   # 中栏：消息流 / 空态入口示例 / 输入框
    │   ├── MessageItem.tsx # 用户气泡 / 思考块 / 工具卡 / 流式光标 / 错误
    │   ├── Markdown.tsx    # marked + 轻量 HTML 清洗
    │   ├── Composer.tsx    # 输入框（Enter 发送 / 附件按钮 / 停止）
    │   ├── CanvasPanel.tsx # 右栏：按 artifactType 分发 + 多画布标签页 + 空态
    │   ├── StatusBar.tsx   # N 条消息 · 证据 M 段 · 覆盖率 X% · 耗时 T ms
    │   ├── LoginGate.tsx   # 登录（首次自动建号）
    │   └── Icons.tsx       # 线框图标集
    └── modules/            # ★ 每个模块自己的画布
        ├── registry.ts     # artifactType → 渲染器映射（未知类型回落占位）
        ├── evidence/Canvas.tsx     # 证据卡 + 自绘配图 + 大图弹层
        ├── tolerance/Canvas.tsx    # 配合特征表 + SVG 公差带图
        ├── tolerance/demo.ts       # 后端公差引擎缺失时的示例数据
        ├── graph/Canvas.tsx        # 图谱壳：知识图谱/问题图谱切换、焦点获取
        ├── graph/Overview.tsx      # 全览星图：9 章星系 + 169 节点 + 缩放平移搜索
        ├── graph/FocusView.tsx     # 焦点关系视图（中心 + 邻居按 tier 分环）
        ├── graph/Questions.tsx     # 问题图谱：三层递进问题列
        ├── graph/constants.tsx     # tier/state/rel 常量与图例
        ├── annotation/Canvas.tsx   # 三色标注（费曼追问）
        ├── wrongbook/Canvas.tsx    # 六步诊改
        ├── coach/Canvas.tsx        # 螺纹示意 / 圆弧分步 SVG
        ├── three/Canvas.tsx        # 真三视图 SVG（/api/models 切换 8 个模型）
        ├── three/demo.ts           # L 形块示例（真实 /api/models 快照）
        ├── comparison/Canvas.tsx   # 成对图 + 差异点 + 随堂题
        ├── quiz/Canvas.tsx         # 题卡（答案隔离 + /api/quiz/explain）
        └── placeholder/Canvas.tsx  # 统一占位渲染器（未知类型兜底）
```

---

## 4. 接口协议与 SSE

### 4.1 对话请求

```http
POST /api/chat
Content-Type: application/json
X-Account: <登录账号>

{"session_id":"local:<feature>","messages":[{"role":"user","content":"…"}],"feature":null}
```

`feature` = 模块 id；`__global__` 时发 `null`（全局对话）。

### 4.2 事件帧（对齐 `apps/api/app/events.py` 与 `docs/05 §2.2`）

`data: {json}\n\n` 逐帧下发，结尾 `data: [DONE]\n\n`。

| type | 前端处理 |
|---|---|
| `thinking` | 追加到该消息的思考块（可折叠，显示字数） |
| `token` | 追加到正文，末尾显示流式光标 `▍` |
| `tool_call` | 新增工具卡（`label` / `name` / `args`），状态"调用中" |
| `tool_result` | 按 `id` 回填工具卡：状态"已完成" + `summary` + `detail` |
| `artifact` | 追加到本轮画布列表；右栏按 `artifactType` 切换渲染器 |
| `error` | 消息内红色错误块 + 结束流式 |
| `done` | 写 `data.ms / evidence / coverage`，状态栏收尾 |

### 4.3 解析器容错（`src/lib/sse.ts`）

- 跳过**不带 `data:` 前缀的进度行**（如 `{"revision":2}`）——参考作品线上实测行为；
- 流式 `TextDecoder` 缓冲，能处理任意字节处截断（含 UTF-8 多字节中间）；
- 单帧 JSON 解析失败 → 跳过该帧并计数（`dropped`），不中断对话；
- 服务端不发尾随空行时，流结束时消费缓冲区剩余帧；
- `[DONE]` 后立即 `cancel()` reader；
- HTTP 非 2xx → 解析 FastAPI 的 `detail` 作为可读错误（登录页"密码不正确"即走这里）。

一次问答的帧数统计：`thinking / tool_call / tool_result / artifact / token / done / [DONE]` 全部处理，缺帧不崩。

---

## 5. 画布渲染器 ↔ `artifactType`

契约取值见 `apps/api/app/contracts/models.py` 的 `ARTIFACT_TYPES`。

| artifactType | 渲染器 | 状态 | 说明 |
|---|---|---|---|
| `evidence` | `modules/evidence/Canvas.tsx` | ✅ 完整 | 证据卡：序号 / 文档名 / 分类 / 章节 / `chunk_id` / 相关度进度条 / 展开全文 / "围绕此段追问"；顶部显示证据数、**IDF 覆盖率**（门控指标）、**chunk 覆盖率**（双门控第二道）与 `配图 N 张`；每张卡按相关度配 1 张**自绘教学图**（SVG 浅色底、可展开图注、点击弹层放大，弹层显示 source/license，Esc 关闭，按 `figure_id` 去重） |
| `tolerance` | `modules/tolerance/Canvas.tsx` | ✅ 完整 | 配合特征表（孔/轴上下偏差、极限尺寸）+ **SVG 公差带图**（零线、孔/轴矩形、间隙/过盈/重叠阴影、ES/EI/es/ei 与 Xmax/Xmin 标注，单位 μm）+ 工艺提示 + 依据 |
| `graph` | `modules/graph/{Canvas,Overview,FocusView,Questions}.tsx` | ✅ 完整 | 顶部切换「**知识图谱** / **问题图谱**」。知识图谱：① **全览星图**——中心课程核心 + 9 章星系（每章一簇，簇内螺旋排布 169 个发光节点、279 条二次贝塞尔关系边），滚轮缩放 + 拖拽平移（直接改 `<g>` transform 不重渲染）、搜索定位、悬停高亮该节点所有边并弹出 kp_id/章节卡片、单击星系名聚焦该章、点节点进焦点；② **焦点关系**——focus 居中 + 邻居按 tier 分环（保留原逻辑），下方前置路径 / 相关课程问题。问题图谱：三层递进三列（11/8/7），每卡 Q 编号 + Bloom 标签 + 知识点 chip（点击跳回星图聚焦）+ 可折叠提示，列间有递进箭头。两种入口：chat artifact 带 focus → 直接焦点；左侧导航无 artifact → 全览星图（`全览入口` 标记） |
| `annotation` | `modules/annotation/Canvas.tsx` | ✅ 完整 | **三色标注**：轮次进度（第 N 轮 / 满 3 轮给总评）、得分 `x/y 句讲对`、表述覆盖率、逐句左侧 4px 色条（green/amber/red）+ 标签 + 点评；`probes` 是可点追问 chip；`final=true` 显示"总评"徽章 |
| `wrongbook` | `modules/wrongbook/Canvas.tsx` | ✅ 完整 | **六步诊改**：原题卡 → 根因 6 选 1 chip → 竖排时间线（原题/错误作答/根因/溯源/正解/避坑）；溯源内嵌带 `chunk_id` 与相关度的可展开出处卡；避坑按 `pitfalls` 列表；`note` 底部提示，`gated=true` 时用警示色 |
| `coach` | `modules/coach/Canvas.tsx` | ✅ 完整 | **螺纹**：比例画法示意 SVG + 参数表 + 画法要点；**圆弧连接**：按 `steps[].draw` 的 `line/arc/point/circle` 逐条画 SVG，可切 1–N 步；`note` 用提示条显示（如"R30 无解，按标准示例 R80 演示"） |
| `three_view` | `modules/three/Canvas.tsx` | ✅ 完整 | **真三视图 SVG**（后端排好版，前端不算投影）：可见轮廓 1.9px 深色 / 不可见 1.0px 虚线（6 4）；`aux` 投影辅助线按 color + 4 4 虚线，标签按 kind 语义放（长对正竖线底端 / 高平齐横线左端 / 宽相等 45° 中点）；悬停视图区高亮并淡化其它视图；左上角模型名 + L×W×H；底部"单位：mm"；顶部模型下拉（`/api/models` 8 个模型，切换只拉 `/api/models/{id}` 重绘）；放大弹层。**SVG 始终按容器等比缩放**（`preserveAspectRatio="xMidYMid meet"` + 内联 `width:100%/height:auto`，外层 `overflow:hidden`），不裁边；放大弹层最大放到 2.2× 原坐标 |
| `quiz` | `modules/quiz/Canvas.tsx` | ✅ 完整 | 题卡列表（题号 / 题干 Markdown / 出处 / `chunk_id` / 答案隔离角标）+ **题面 OCR 质量声明小灰字**（优先用后端 `quality_note`，缺失时回落到内置同义提示）；每题"我先想想"展开才调 `POST /api/quiz/explain`，渲染解析正文 + 来源 + 相关出处（文档/相关度）；接口失败显示空态 + 重试 |
| `comparison` | `modules/comparison/Canvas.tsx` | ✅ 完整 | 成对图**内联 SVG**渲染（可读 `data-pair-id` / `data-panel` / `data-diff`）：点差异点 n → A/B 两图里所有 `[data-diff="n"]` 同时点亮、其余变淡；点图里的编号圈反向选中差异点；点空白处开大图（Esc）；内联失败自动回落 `<img>`。A/B 说明与正确性；差异点列表（① 分界线：A … / B … —— 为什么…）；随堂题 4 选项，只对"用户选中项"判对错（答错显示 A/B 说明并允许再选，答对显示 explain） |
| `wrongbook` 写操作 | `modules/wrongbook/Canvas.tsx` | ✅ 完整 | 六步诊改之外，新增「加入错题本」（`POST /api/wrongbook`，带 `X-Account`，成功显示 `已加入 · w_xxxx` 并禁用）与「查看错题本」列表（`GET /api/wrongbook`，显示题干/根因/来源/时间/id，失败可重试） |
| 其它未知值 | `placeholder/Canvas.tsx` | ✅ 兜底 | 显示 `artifactType` + "尚未在注册表中登记"，**绝不抛错** |

### 5.1 新增画布消费的 artifact 形状（实测）

```jsonc
// evidence（kb_search）—— 本轮新增 figures / chunkCoverage
{ "query", "evidences":[…], "documents":[…], "totalDocs",
  "coverage": 1, "chunkCoverage": 1, "gated": false,
  "figures": [
    {"figure_id":"FIG-SANSHITU-BASE","file":"FIG-SANSHITU-BASE.svg",
     "title":"三视图的形成与三等规律","chapter":"第三章…",
     "caption":"…","structure_tags":["三视图","长对正"],
     "kp_ids":["KP-PROJ-004"],"license":"自绘","source":"依据 GB/T 17451 自绘"}
  ] }
// 图用 <img src={"/figures/"+file}> 引用（不内联），figure 列表 → 证据卡的分配：
// 章节前缀 + structure_tags（章节内命中权重更高）+ 图题实义片段 做贪心匹配，
// 分不出去的图顺序补给空卡；按 figure_id 去重，每张卡最多 1 张图。

// graph（kg_lookup 的 artifact —— 焦点入口）
{ "focus": {id,label,tier,chapter,kp_id,state},
  "neighbors": [{id, rel, note, node:{...}}],   // 同一 id 可能有多条 rel：画布按 id 去重、多关系画平行线
  "prereq": [{id, level, node:{...}, note}],
  "nodes": [...169], "edges": [...279] }        // 全量图，用于顶栏计数与后续扩展

// GET /api/graph（全览星图 / 问题图谱的数据源，约 70 KB，模块级缓存只拉一次）
{ "nodes":[169], "edges":[279],
  "chapters":[{chapter,node_ids:[...],count} x9],
  "stats":{nodes,edges,questions,chains,chapters,relations:{prereq,contrast,compose,cause}},
  "questions":[{qid,layer,question,bloom,kp_ids,kp_labels,node_ids,hint} x26],
  "question_layers":[{layer,name,desc,count,qids,blooms} x3] }
// 全览星图按 chapters 分 9 个星系（中心是"课程核心"，不是数据节点）；
// 问题图谱按 question_layers 三列渲染，kp chip 用 node_ids 跳回焦点。

// annotation（费曼追问）
{ "round": 1, "final": false, "sentence_count": 3, "coverage": 0.25,
  "annotations": [{text,label,color,comment}],   // annotations 比 sentence_count 多 1 条（故意说错的）
  "probes": ["…"], "summary": "…", "score": {correct,total,level} }

// wrongbook（六步诊改）
{ "question", "wrong_answer", "root_cause", "root_causes_all":[6项],
  "steps": [{n,key,value} x6], "trace": [{ref,chunk_id,score,text}],
  "pitfalls": ["…"], "coverage", "gated", "note" }

// coach
// 螺纹： {kind:"thread", data:{spec,type_name,d,d1,pitch,points:[…],table:{…}}}
// 圆弧： {kind:"arc_arc_outer|arc_arc_inner|line_line|line_arc",
//         kind_cn:"圆弧-圆弧外切", params:{r,c1,r1,c2,r2|line_p1,line_p2|circle_center,circle_r},
//         note:"无解时的降级说明", data:{steps:[{n,title,detail,draw:[…]}], summary}}
// ⚠️ arc.start_angle / end_angle 是**度**（`geometry/arc.py::_angle_deg` 注明"度，[0,360)"），
//    不是弧度。前端按度转 SVG 路径（劣弧、sweep=0）。

// three_view（projection_render，实测 /api/models/M-L-BLOCK）
{ "model_id":"M-L-BLOCK", "name":"L 形块", "unit":"mm",
  "size":{L,W,H}, "bbox":[[0,0,0],[100,60,60]], "projection":"第一角",
  "segments":[{"view":"front","x1":46,"y1":128,"x2":146,"y2":128,"hidden":false}], // 20 条
  "stats":{"front":{total,visible,hidden},"top":{...},"left":{...}},
  "viewBox":[0,0,292,262],
  "labels":[{view,text,x,y}],                    // 后端已排好版
  "aux":[{kind,color,x1,y1,x2,y2,label}],        // 9 条；label 只有 3 条非空
  "view_boxes":{"front":[46,68,146,128], ...} }  // [x1,y1,x2,y2]
// aux label 位置由 kind 决定（统一按 x1,y1 会叠在一起）：
//   long → 竖线底端；height → 横线左端；width → 45° 线中点。

// comparison（成对图辨析）
{ "pair_id", "file":"pairs/PAIR-….svg", "title",
  "a":{label:"A",caption,正确性}, "b":{label:"B",caption,正确性},
  "differences":[{no,name,a_desc,b_desc,why}],
  "question":{stem,options:[4],answer_index,explain}, "kp_ids":[] }
// 成对图 SVG 里带：根 data-pair-id；两个图形区 <g data-panel="a|b">；
// 标号圈/数字/图例行带 data-diff="n" —— 画布内联渲染后按 n 同步高亮 A/B 两图。

// quiz（题卡，答案隔离）
{ "questions":[{chunkId,documentTitle,section,content}], "answer_withheld":true,
  "quality_note":"题面来自扫描件 OCR，存在错字…" }   // 对话链路的 artifact 目前可能没有该字段，前端有同义回落
// 展开解析：POST /api/quiz/explain {chunk_id}
//   实测返回 {ok,question,section,source,explain,refs:[{documentTitle,section,chunkId,score}]}
```

`/api/graph` 一次约 46 KB，**模块级缓存只拉一次**（用于 169/279/26 计数与课程问题），画布重绘不重复请求。
`/api/models`（8 个模型清单）同样模块级缓存；画布内切换模型只请求 `/api/models/{id}`。

一次问答可能推送多个 artifact（实测：`graph` + `evidence`、`tolerance` + `evidence`、`three_view` + `evidence`）。右栏会用**标签页**列出本轮全部画布，默认选中最后一个；切换标签即切换渲染器。

`tolerance` / `three_view` / `comparison` / `quiz` 画布在**空态**下提供本地示例入口（`modules/*/demo.ts`），全部带"示例"标记；后端数据一旦下发，真实 artifact 优先，不会显示示例标记。projection 模块空态可一键在「辨析示例 / 题卡示例」之间切换。

---

## 6. 三栏布局规格（1366 宽实测）

```
顶栏 56px：产品名 | 账号 | 模型标识 | 连接状态 | 意见反馈
──────────────────────────────────────────────────────────
左栏 220px │ 中栏自适应 │ 右栏 clamp(380px, 30vw, 440px)
            │            │
状态栏 34px：N 条消息 · 证据 M 段 · 覆盖率 X% · 耗时 T ms
```

1366×768 实测（CDP 设置视口后读取 `getBoundingClientRect`）：

| 区域 | 宽度 |
|---|---|
| 左栏 `.leftnav` | **220px** |
| 中栏 `.chat` | 736px（自适应） |
| 右栏 `.canvas` | **410px**（在 380–440 区间内） |

响应式断点：`≤1240` 右栏 360；`≤1120` 左栏收成 68px 图标栏；`≤940` 右栏 320、隐藏模型标识；`≤820` 画布下沉为第二行。

### 状态栏口径

- **N 条消息**：当前会话消息数（用户 + 助手）
- **证据 M 段**：本轮最近一个 `evidence` artifact 的 `evidences.length`
- **覆盖率 X%**：IDF 覆盖率（门控指标，来自 artifact `coverage` 或 `done` 帧）
- **耗时 T ms**：`done.data.ms`（后端实测耗时，不是前端网络时间）
- 另附 **帧 N**：本会话累计收到的 SSE 帧数（把"流式开销"也当产品信息展示）

---

## 7. 已实现清单

- [x] 三栏布局 + 顶栏 + 底部状态栏（1366 下 220 / 736 / 410）
- [x] 登录页：账号/密码、首次自动建号、**密码框回车提交**、错误显示后端 `detail`（实测"密码不正确"）
- [x] 账号存 `localStorage`（key `machdraw.account`），对话请求带 `X-Account`
- [x] 启动时探测 `/api/health`，失败显示红点 + "后端未连接" + 状态栏"后端离线"（点状态 chip 可重试）
- [x] 模块导航 9 个，全部来自 `GET /api/modules`，点击切换 `feature` + 会话 + 画布类型
- [x] 消息流：用户气泡 / 助手 Markdown / **思考过程折叠块** / **工具调用卡（调用中→已完成，可展开参数与原始返回）** / **流式光标** / 错误块
- [x] 底部输入框：Enter 发送、Shift+Enter 换行、中文输入法 composing 时不误发、自动增高、附件按钮、生成中可"停止"
- [x] 右栏：按 `artifactType` 切换渲染器；多 artifact 标签页；无画布时显示空态
- [x] `evidence` 完整画布（相关度进度条 / IDF+chunk 双覆盖率 / 展开 / 追问填输入框）
- [x] `evidence` 自绘教学配图：按相关度把 figure 分配到证据卡（figure_id 去重、每卡最多 1 张）、浅色底 SVG 缩略图、图注可折叠、点击弹层放大（title/chapter/caption/source/license/tags，Esc 关闭）、`配图 N 张` 标记
- [x] `tolerance` 完整画布（配合表 + SVG 公差带图，μm 口径）
- [x] `graph` 完整画布：**全览星图**（中心课程核心 + 9 章星系 + 169 节点 + 279 贝塞尔边 / 滚轮缩放 / 拖拽平移 / 搜索定位 / 悬停高亮边与卡片 / 星系名聚焦 / 图例 3 类）+ **焦点关系**（tier 分环 / rel 分色 / 前置路径 / 相关课程问题）+ **问题图谱**（三层递进三列 11/8/7、Bloom 标签、知识点 chip 跳转、可折叠提示、递进箭头）；两种入口（chat artifact → 焦点；导航 → 全览）
- [x] `annotation` 完整画布（三色逐句标注 / 轮次进度 / 得分与覆盖率 / 追问 chips / 总评）
- [x] `wrongbook` 完整画布（六步时间线 / 根因 6 选 1 / 溯源出处卡 / 避坑 / gated 提示）
- [x] `coach` 完整画布（螺纹比例画法示意 + 参数表；圆弧连接按 draw 指令分步 SVG，note 降级说明）
- [x] `three_view` 真三视图 SVG（后端图纸坐标直画 / 实线虚线线宽 / aux 标签按 kind 放 / 悬停视图高亮 / 模型下拉 8 个 + `/api/models/{id}` 切换 / 放大弹层）
- [x] `comparison` 完整画布（成对图 + A/B 说明 + 差异点 + 随堂题判对错，答错不泄题可重选）
- [x] `quiz` 完整画布（题卡 + 答案隔离角标 + 展开调 `/api/quiz/explain` + 解析/来源/相关出处 + 失败重试）
- [x] 未知 `artifactType` 统一占位，未知类型不崩
- [x] `npm run build` 通过（`tsc --noEmit` 严格模式）

---

## 8. 已知未完成项 / 限制（如实列出）

1. **全览星图的节点标签按层级显示**：初始 100% 只显示 core 级 + 悬停/搜索命中节点的标签（避免 169 个标签糊成一团）；放大到 ≥220% 才展开全部标签。星系名做了 7 字截断。
2. **`quiz.quality_note` 的对话链路暂缺**：`quiz_from_kb` 工具产出的 artifact 带 `quality_note`，但 `/api/chat` 当前下发的 `quiz` artifact 只有 `questions/answer_withheld`；前端已回落到内置同义提示（"题面来自扫描件 OCR，可能有错字，仅供练习"），后端补上字段后会自动优先用后端文案。
3. **`quiz` 解析接口的返回形状**：已实测 `{source,explain,refs[]}` 并做了防御式渲染；若后端改字段名仍能兜底显示原始 JSON。
4. **附件按钮仅 UI**：选择文件后只在消息里记录文件名，后端没有上传接口，不会真正上传。
5. **意见反馈仅本地**：写入 `localStorage`（`machdraw.feedback`），后端没有反馈接口。
6. **会话不持久化**：只存内存，刷新即丢；未接 `/api/auth/records`。切换模块时各模块会话在内存中保留。
7. **断线不自动重连**：健康检查失败只改状态显示；流式请求失败会在消息内显示后端错误，下一次提问会重试。
8. **没有单测框架**：`sse.ts` 的容错逻辑用浏览器内动态 import 手工验证（见 §9），未引入 vitest。
9. **公式不渲染**（需求明确不需要）。
10. **`coach` 的圆弧角度单位**：后端 `_arc_draw` 给的是**度**，与交接说明里的"弧度"不一致；渲染器按代码实际（度）实现。

---

## 9. 验证记录（真实后端，非模拟）

### 9.1 `npm run build`

```
> machdraw-web@0.1.0 build
> tsc --noEmit && vite build

vite v6.4.5 building for production...
transforming...
✓ 65 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   1.05 kB │ gzip:   0.69 kB
dist/assets/index-CvD33ZKO.css   72.35 kB │ gzip:  12.90 kB
dist/assets/index-D5lP0OsG.js   392.11 kB │ gzip: 122.72 kB
✓ built in 1.05s
```

three.js 已移除（三视图改为后端坐标直出 SVG），产物不再有 477 KB 的 `Canvas-*.js` 懒加载 chunk。

### 9.2 真实问答端到端（`npm run dev` → 5173 → 后端 8077）

问题：`剖视图和断面图的区别是什么？`

在页面内 monkey-patch `fetch` 记录到的**真实 SSE 帧序**（时间戳为页面 `performance.now()`）：

```
thinking ×3 → tool_call(kg_lookup) → tool_result → artifact(graph)
→ tool_call(kb_search) → tool_result → artifact(evidence)
→ thinking → token ×19 → done → [DONE]
```

- 思考块：113 字，先"学生提问/计划调用"，后"已有确定性结果…"
- 工具卡 2 张：`kg_lookup`（剖视图 · 18 条关系 · 前置 16 层）、`kb_search`（命中 6 段原文证据）
- 正文：19 个 `token` 帧流式拼接，结束光标消失
- 右栏：`evidence` 画布 6 张卡，首张《机械制图知识点手册（自建）》`chk_KP_0001_0021`，相关度 96%
- 状态栏：`2 条消息 · 证据 6 段 · 覆盖率 86.2% · 耗时 34 ms · 帧 29`（与 `done.data` 一致）
- 浏览器 console：**0 条 error/warn**

网络限速（CDP `Network.emulateNetworkConditions`）下截到的**流式中间态**：思考块"进行中…"、工具卡"调用中"（spinner）、"正在生成…"、发送按钮变"停止"、状态栏"帧 3 | 流式生成中…"。

### 9.3 生产构建（后端 :8077 直接托管 `dist/`）

同一问题 `Φ30 H7/k6 是什么配合？`（此时 `app/domain/tolerance.py` 已就绪）：

- 工具卡：`tolerance_calc` → "Φ30H7/k6 → 过渡配合"、`kb_search` → 6 段证据
- 右栏标签页：`tolerance` | `evidence`，默认选中后者
- `tolerance` 画布（**真实引擎数据，无"示例"标记**）：`ES +21 / EI 0 / es +15 / ei +2`，`Xmax +19 μm`、`Xmin −15 μm`，与配合表 `+0.021 / 0.000 / +0.015 / +0.002` 一致
- 状态栏：`2 条消息 · 证据 6 段 · 覆盖率 100.0% · 耗时 38 ms · 帧 26`

### 9.4 四个新增画布（真实后端）

| 画布 | 实测入口 | 结果 |
|---|---|---|
| `graph` | 知识图谱 →「剖视图依赖哪些前置知识？」 | 顶栏 `169 节点 · 279 关系 · 26 课程问题`；焦点"剖视图"，`直接关系 18 条 · 13 个知识点 · 前置 16 个`；SVG 13 节点 / 18 条边（多关系平行微偏移）；点「组合体」→ 调 `/api/graph/node/KN-004` 换焦点成功（`直接关系 15 条 · 15 个知识点 · 前置 14 个`）；相关课程问题命中 Q-020 |
| `annotation` | 形体重构 →「剖视图就是把零件切开来看，比较直观，大概能看出里面的孔。」 | 第 1 轮 / 至少 3 轮；`1/4 句讲对`、表述覆盖率 25%；4 条逐句标注（讲对绿 / 表述模糊黄 ×2 / 待纠正红）+ 点评；2 个可点追问 chip；本轮小结 |
| `wrongbook` | 智能找茬 →「为什么尺寸链不能标注成封闭的？」 | 原题 + 覆盖率 100%；根因 6 选 1（概念混淆高亮）；六步时间线齐全；溯源 3 张出处卡（`chk_DEPTH-CHICUNLIAN_0002_0000` 等，相关度 100%）；避坑 6 条；底部 note |
| `coach` | 虚拟画图教练 4 问 | 螺纹：参数表 `d=10 / d₁=8.5 / P=1.5 / 粗牙 / 60°` + 比例画法示意 SVG + 6 条要点；外切：`R20 / O1(0,0) R1 30 / O2(100,0) R2 30`，4 步可切换；内切 R30：**note 提示条显示后端降级说明**（"R30 这组示例无解…按标准示例 R80 演示"）；圆角 R10：`line_line` 4 步正常 |

### 9.5 证据画布自绘配图（生产构建 :8077）

问题：「三视图的投影规律是什么？」

- 顶部 `配图 2 张` + `chunk 覆盖率 100%`（双门控第二道）
- 2 张图按相关度分别落在**第 1 张卡**（`FIG-SANSHITU-BASE` 三视图形成与三等规律）与**第 3 张卡**（`FIG-SANSHITU-EXAMPLE` 组合体示例），`figure_id` 无重复
- 缩略图 `<img src="/figures/….svg">` 从后端静态路由加载成功（`complete && naturalWidth>0`），浅色底（`#f8fafc`）圆角容器
- 点击 → 弹层：标题/章节/图注/`依据 GB/T 17451、GB/T 4458.1 自绘`/`许可：自绘`/结构标签/`FIG-SANSHITU-BASE`，大图 662×463，`Esc` 关闭验证通过
- 图注「展开图注/收起图注」切换正常

### 9.6 三视图 / 成对图 / 题卡（生产构建 :8077）

| 画布 | 实测入口 | 结果 |
|---|---|---|
| `three_view` | 3D 可视化沙盒 →「这个零件的三视图怎么画？」 | 一轮下发 `three_view` + `evidence` 两个 artifact，标签页切换；`M-L-BLOCK`：**20 条 segments / 9 条 aux / 2 条虚线**，viewBox `0 0 292 262`，三视标题齐全；`stats` 行 `主视 6实/0虚 · 俯视 7实/2虚 · 左视 5实/0虚 · 第一角投影`；aux 标签 `长对正 / 高平齐 / 宽相等` 按 kind 放在竖线底端 / 横线左端 / 45° 中点，无叠字；悬停「俯视图」→ 视图名出现且其它视图线淡化（opacity 0.2）；**模型下拉 8 个**，切到「圆筒 M-TUBE」→ `GET /api/models/M-TUBE` 重绘（viewBox `0 0 260 276`，89 条线，stats 变为 `主视 6实/2虚 · 俯视 64实/0虚 · 左视 6实/2虚`），不重发对话 |
| `comparison` | 剖视与投影辨析 → 空态「查看辨析示例」 | 成对图 + A/B 说明 + 3 条差异点 + 随堂题；**点错 A 只标红 A（不再提前把正确项标绿）**，显示"A 是半剖视图，B 是局部剖视图"并允许再选；点 B → 绿色"答对了"+ explain；点图放大 + Esc 关闭 |
| `quiz` | 剖视与投影辨析 → 示例切到「题卡」 | 2 张题卡（题号/出处/`chunk_id`/「答案暂不下发」）；点「我先想想」→ **实测调用 `POST /api/quiz/explain` 成功**：解析正文 226 字 + 来源「机械制图知识点手册（自建） · 第五章…5.4」+ 3 个相关出处（含相关度 100%），按钮变「收起解析」，无报错 |

### 9.7 本轮修复与写操作（生产构建 :8077）

| 项 | 实测 |
|---|---|
| 三视图不裁边 | 1366/1256/1024/900 四档宽度量 `.tv-sheet` 与 `.tv-svg` 包围盒：SVG 均完整落在容器内（`fitsInside=true`、`contentOverflow=0`）；`preserveAspectRatio="xMidYMid meet"` + 内联 `width:100%;height:auto;max-width:100%` 已生效 |
| 放大弹层 | 真数据 viewBox 292×262 → 弹层 SVG 宽 642px（2.2× 上限），容器 968×578 无横向滚动（`hOverflow=0`） |
| 一轮多 artifact | 「考考我：三视图的投影规律和半剖局部剖的区别」→ 同时下发 `comparison` / `quiz` / `three_view` / `evidence`，标签页 4 个可切换 |
| 真实 comparison | `PAIR-POU-BAN-JUBU` / `PAIR-DUANMIAN-POUSHI`：图 `/figures/pairs/*.svg` 内联渲染成功（`data-pair-id`、`data-panel=a/b`、16 个 `data-diff`），A/B + 3 条差异 + 随堂题；后端按关键词自动挑对组 |
| 差异点联动高亮 | 点差异点 1 → 内联 SVG 里 5 个 `[data-diff="1"]` 元素同时点亮（跨 `data-panel=a` / `b` 两图 + 图例），其余标号降到 opacity 0.22；点图里的编号圈「2」→ 列表自动切到第 2 条；再点同一编号 → 全部取消；点图空白处 → 大图弹层（Esc 关闭） |
| 国标直径符号 | 公差画布由 `Φ` 改为 **`Ø`**（`Ø30 H7/k6`），符合国标规范 |
| 真实 quiz | 2 张题卡（《机械制图习题（内部）》），显示 OCR 质量声明行；「我先想想」→ `/api/quiz/explain` 返回解析 + 来源 + 3 个相关出处 |
| 加入错题本 | 六步诊改页点「加入错题本」→ `POST /api/wrongbook` 返回 `w_b036576f8ae0`，按钮变「已加入 · w_…」并禁用；「查看错题本」→ `GET /api/wrongbook` 列出 1 条（题干 / 概念混淆 / wrongbook_canvas / 时间 / id） |

### 9.8 知识图谱 / 问题图谱（生产构建 :8077，独立 headless Edge 实测）

| 项 | 结果 |
|---|---|
| 全览星图 | 左侧导航进入（无 artifact）：`169 节点 / 279 边 / 9 星系`，顶部 `169 知识点 · 279 关系 · 26 课程问题 · 9 章`，`全览入口` 标记；中心"课程核心"，9 个星系各自成簇 |
| 缩放 / 平移 | 真实鼠标滚轮：`100% → 162%`，组 transform `scale(1.616)`；拖拽后 transform 平移生效；「重置」回 100% |
| 搜索 | 输入「三视图」→ 命中「画三视图步骤」并居中放大到 240%，169 个节点标签展开，`.is-selected` 高亮；输入不存在词 → 显示"未找到…"提示 |
| 悬停 | 节点弹出卡片（`组合体 / KP-COMP-001 / 课程核心 / 未学 / 第五章…`），该节点 15 条边高亮、其余 153 个节点淡化 |
| 点节点 → 焦点 | 点「三视图形成」→ `KP-PROJ-004`，`直接关系 8 条 · 7 个知识点 · 前置 2 个`，出现「全览星图 / 焦点关系」切换与返回链接 |
| 问题图谱 | 三列 `基础理解 11 / 识图分析 8 / 综合绘图 7`，26 张题卡、54 个知识点 chip、26 个「看提示」、2 个递进箭头；概览行显示 Bloom 分布（记忆5 理解6 / 分析4 应用4 / 综合7） |
| 提示折叠 | 点「看提示」展开 A0-A4 幅面提示，默认收起不泄题 |
| 知识点 chip 跳转 | 点「图纸幅面」→ 回知识图谱焦点视图，focus=图纸幅面 |
| 对话 artifact 入口 | 问「剖视图依赖哪些前置知识？」→ 下发 `graph + evidence`，graph 标签直接进焦点：focus=剖视图，`直接关系 18 条 · 13 个知识点 · 前置 16 个` |
| console | 无 JS error/warn；修掉了唯一的 404（后端不托管 `/favicon.svg`，改为内联 data URI） |

### 9.9 其它逐项验证

| 项 | 结果 |
|---|---|
| 密码框回车提交 | ✅ 回车直接进入工作台 |
| 登录错误显示后端 message | ✅ 错密码显示"密码不正确"（FastAPI `detail`） |
| "围绕此段追问" → 输入框 | ✅ 填入"围绕证据【1】《…》…这段原文继续追问："且自动聚焦 |
| 占位渲染器（未知类型） | ✅ 只有未登记类型才会出现"该画布开发中" + 字段 chips + JSON，不崩 |
| 未知 `artifactType` | ✅ 回落到占位（"尚未在注册表中登记"） |
| `graph` 多关系去重 | ✅ 18 条关系 → 13 个节点（同一知识点多关系画平行线，不再重复出节点） |
| 断线检测 | ✅ CDP 离线后点状态 chip → 红点"后端未连接"/状态栏"后端离线"；恢复后回绿 |
| 1366 三栏 | ✅ 220 / 736 / 410（见 §6） |
| SSE 脏流容错 | ✅ 喂入 `{"revision":2}` 进度行 + 坏 JSON：解析出 2 帧、`dropped=1`，不抛错 |
| 附件按钮 | ✅ 选择文件后 chip 显示文件名（仅本地标记，见限制 3） |
| 长回答贴底滚动 | ✅ 去掉 `scroll-behavior: smooth` 并在新消息出现时强制回底部；实测 `distanceToBottom=0` |
| `/figures` 静态路由 | ✅ 生产 :8077 与开发 :5173（Vite 代理）均 200 / `image/svg+xml` |

截图存于 `apps/web/_shots/`：`01-login` `02-workbench-empty` `03-answer` `04-thinking-tools` `05-placeholder-graph` `06-tolerance`（示例）`07-three-view` `08-1366` `09-login-error` `10-offline` `11-streaming` `12-prod-8077` `13-tolerance-live`（真实）`14-coach-placeholder`（旧占位，仅留档）；**新增**：`15-graph` `16-graph-drill` `17-annotation` `18-wrongbook` `19-coach-thread` `20-coach-arc` `21-coach-note` `22-coach-fillet` `23-evidence-figures` `24-figure-lightbox` `25-three-view`（示例）`26-three-view-zoom` `27-comparison` `28-comparison-wrong` `29-comparison-correct` `30-comparison-lightbox` `31-three-view-real`（真数据）`32-three-view-switch`（切圆筒）`33-quiz-explain`（真解析）`34-comparison-wrong-fixed` `35-three-view-1024` `36-three-view-900`（裁边核查）`37-three-view-modal-fit` `38-quiz-real` `39-comparison-real`（真数据）`40-wrongbook-save` `41-three-view-1366` `42-comparison-diff-sync`（差异点联动高亮）`43-graph-overview`（全览星图）`44-graph-focus-from-overview`（点节点进焦点）`45-graph-questions`（问题图谱三列）`46-graph-chat-focus`（对话入口进焦点）。`

---

## 10. 契约来源（改契约先改后端）

- `apps/api/app/contracts/models.py` —— 事件类型、`artifactType` 枚举、`Evidence`、`ModuleManifest`
- `apps/api/app/events.py` —— SSE 帧序列化与 `[DONE]` 哨兵
- `apps/api/app/orchestrator.py` —— 事件产生顺序、`done.data` 字段、公差返回形状
- `GET /api/graph` / `GET /api/graph/node/{id}` —— 全量知识图谱（169 节点 / 279 边 / 9 章 / 26 问题 / 三层问题分层）；模块级缓存
- `GET /api/figures` / `GET /figures/<file>` —— 自绘教学图库（由 `evidence.data.figures` 引用；开发期 Vite 代理 `/figures`）
- `GET /api/models` / `GET /api/models/{model_id}` —— 8 个三维模型与已排版的三视图数据（`three_view` artifact 同构；画布内切换模型用）
- `POST /api/quiz/explain` —— 题卡解析（body `{chunk_id}`，返回 `{source,explain,refs[]}`）
- `GET /api/pairs` / `GET /figures/pairs/<file>.svg` —— 成对图数据与静态 SVG（comparison artifact 的数据源；SVG 内联后用 `data-diff` 做 A/B 同号高亮）
- `docs/05-线上站点逆向观察.md` §2 —— 参考作品的真实事件协议（`token` 命名、`{"revision":N}` 进度行）
