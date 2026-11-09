# 17 · 第三轮：语音 / 深色 / 移动端 PWA / 拍题 OCR / 持久化镜像

> 用户："一块都做了"。这轮把之前列的"还没做"逐项做成可用版本（不引重型依赖，除 OCR 用系统 tesseract）。

---

## 1. 语音输入 + 朗读（浏览器原生）

- **输入**：输入框新增麦克风按钮，走 `SpeechRecognition / webkitSpeechRecognition`，`zh-CN`，实时把识别结果拼进草稿；再点一次停止。不支持时给 toast 提示（建议 Chrome/Edge），需要麦克风权限。
- **朗读**：助手消息操作条新增「朗读 / 停止」，用 `speechSynthesis` 读回答（先去掉 Markdown 标记、截断 3000 字，避免读代码块）。
- 前端零依赖，不经过后端。

## 2. 全局深色模式

- 顶栏新增太阳/月亮按钮；主题存 localStorage（`rp.theme`），首次跟随系统 `prefers-color-scheme`。
- `[data-theme='dark']` 覆盖设计令牌与主要表面：顶栏/左栏/状态栏毛玻璃、对话、输入框、卡片、证据卡/计算卡/题卡、命令面板、历史/复习抽屉、Markdown/表格/代码。
- 图谱页本来就是深色星图，保持。

## 3. 移动端 / PWA

- ≤820px：底部固定导航「模块 / 对话 / 画布 / 图谱」；左栏变抽屉（点模块自动收起），状态栏隐藏，画布在对话下方整行。
- ≤520px：顶栏进一步收窄（隐藏模型/状态/搜索/账号名），只留品牌、主题、历史、复习、反馈。
- PWA：新增 `manifest.webmanifest`（standalone、theme-color、核符号 SVG 图标）与 `icon.svg`，`index.html` 加 manifest/theme-color/apple meta；后端补 `/manifest.webmanifest`、`/icon.svg` 路由。
- 说明：**没有做 Service Worker 离线缓存**（避免旧 bundle 缓存问题），所以是"可安装、可全屏"，不是离线可用。

## 4. 拍题 / 公式图片 OCR

- 后端 `POST /api/vision/ocr`：接收 dataURL/纯 base64，Pillow 打开（超 1800px 自动缩放），`pytesseract` 走 `chi_sim+eng`；返回识别文字。
- 依赖离线：Dockerfile 里 `apt-get install tesseract-ocr tesseract-ocr-chi-sim tesseract-ocr-eng`；Python 侧 `pytesseract + Pillow`。Render 构建时自动装，不依赖外部 OCR 服务。
- 前端输入框回形针改为"图片"：选图后显示缩略图；发送时先调 OCR，把识别文字以
  `📷 拍题图片识别：… \n\n 问题：…` 拼进消息；OCR 失败会优雅提示并附原问题。
- 局限：印刷体/清晰截图效果最好；手写、复杂公式、上下标识别不稳（tesseract 的已知短板），后续可换 PaddleOCR/多模态模型。

## 5. 持久化（浏览器镜像，跨 Render 重启）

Render 免费档没有持久盘，SQLite 会在重启/重部署后清空。这轮补了**客户端镜像**：

- 掌握度每次变化（自评/判分）后写入 `localStorage['rp.mastery.v1:<账号>']`；
- 登录/启动时 `POST /api/mastery/import`：只导入 `last_at` 比服务端新的条目，再把服务端合并结果写回本地；
- 会话本来就有 localStorage 持久化（`rp.sessions.v1:<账号>`）。
- 效果：同一浏览器、同一账号，Render 重启后掌握度仍能恢复；换设备仍不同步（要真正跨设备需要 Postgres/Supabase）。

## 6. 历史会话恢复画布

- 之前只把消息写进 `messages`，现在 orchestrator 把每轮 `artifacts`（quiz/evidence/calc…）一起写进 assistant 消息的 `payload`；
- `/api/history/{id}` 聚合返回 `artifacts`；
- 历史抽屉点一条 → 恢复消息 + 最近画布（最多 8 个），不再只有文字。

## 7. 验证

- 锚点 68/68、smoke 27/27、标定集 54/54、holdout 25/26（H10 边界未变）。
- 本地：
  - OCR（生成"核反应堆物理 测试 OCR"图片）→ 返回 `核 反 应 堆 物 理 测 试 OCR`；
  - 出题会话题 → history 返回 `artifacts: quiz/evidence`，前端可恢复画布；
  - 深色模式截图（`_p2_dark2.png`）、移动端 390px 截图（`_p2_mobile.png`）正常；
  - 语音/朗读代码路径需真实麦克风，headless 无法自动测。
- 线上：部署后验证 `/api/health`、`/manifest.webmanifest`、`/api/vision/ocr`。

## 8. 仍然受限的

| 项 | 说明 |
|---|---|
| 手写/复杂公式 OCR | tesseract 能力有限，建议换 PaddleOCR/多模态 |
| 离线可用 | 没有 Service Worker，断网不能打开 |
| 跨设备同步 | 掌握度镜像只在同一浏览器 |
| 深色模式细节 | 少数画布内部组件仍可能有浅色残留，逐页再看 |
| 语音 | 依赖浏览器与麦克风权限；Firefox 支持有限 |
| 真正服务端持久化 | 需 Render Disk（付费）或外部 Postgres |

---

相关文件：

- 后端：`api/app/{main.py,orchestrator.py}`、`requirements.txt`、`Dockerfile`
- 前端：`shell/{Composer,MessageItem,TopBar,LeftNav,MobileNav,HistoryDrawer}.tsx`、`lib/{store,api,learner}.ts`、`modules/quiz/Canvas.tsx`、`app.css`、`index.html`、`public/{manifest.webmanifest,icon.svg}`
