# 22 · `preview` 与 `autoOpenCanvas` 下沉记录

> 本阶段目标：把「空态示例数据」和「产出 artifact 时是否自动展开画布」从壳里下沉成
> `features/*/index.ts` 的模块字段，让新增画布不再需要改 `CanvasPanel`。
>
> 相关文件：
> `apps/web/src/lib/canvasFeature.ts`、`apps/web/src/features/*/index.ts`、
> `apps/web/src/modules/registry.ts`、`apps/web/src/shell/CanvasPanel.tsx`、
> `scripts/gen-module-docs.py`。

---

## 0. 一句话结果

- 4 个 feature 的 `preview` 已下沉（tolerance / three_view / comparison / quiz），label 逐字沿用旧壳文案；
- `autoOpenCanvas` 已加入契约，9 个 feature 全部显式声明；
- 壳删除了 4 个 `demo.ts` 硬编码 import 与 `demoItems()`，改为 `getPreview(type)` + `getPreviewType`；
- 新增可收起/展开的画布（细栏按钮），`autoOpenCanvas=true` 时 artifact 到达会自动展开；
- `autoOpenCanvas` 已按「展示型 / 对话型」声明；`evidence` 保留 `true`（例外，见 §3.3）；
- `verify_all.py` 已按新基础设施变为 **11 项**，全绿；模块任务书 `--check` 也全绿。

---

## 1. A 步：改造前的真实行为（先查再改）

### 1.1 结论

**改造前右栏没有“自动展开”，因为它从来不会关闭：`CanvasPanel` 是常驻组件，右栏永远渲染。**

具体证据：

1. `apps/web/src/App.tsx:36-45`：无论当前模块/是否有 artifact，`<CanvasPanel />` 都直接写死在 `.workbench` 里：
   ```tsx
   <div className="workbench">
     <LeftNav />
     <ChatPanel />
     <CanvasPanel />   {/* 常驻 */}
   </div>
   ```
2. `apps/web/src/shell/CanvasPanel.tsx`（改造前）没有任何 `panelOpen/collapsed` 状态；
   只有 `selected` 这个「本轮第几个 artifact」的标签选择：
   ```ts
   // 改造前 CanvasPanel.tsx:85-87
   useEffect(() => {
     setSelected(artifacts.length > 0 ? artifacts.length - 1 : 0);
   }, [artifacts.length, activeFeature]);
   ```
3. `apps/web/src/shell/TopBar.tsx` 没有画布开合按钮；`store.ts` 的 `applyEvent` 只把 artifact
   放进 `session.artifacts`，没有任何 layout/open 状态。
4. 因此「artifact 到达时会不会自动展开」的答案是：**没有这个动作；画布始终可见**，只是
   `selected` 会自动指向最新 artifact。不存在“在哪个文件哪一行决定自动展开”的既有逻辑。

### 1.2 为什么 A 步会影响设计

参考作品的默认是「画布收起」，`autoOpenCanvas` 决定 artifact 到达时是否把 `panelOpen` 置 true。
我们默认「画布常驻」，要让 `autoOpenCanvas` 有意义，必须先补一个**可手动收起**的画布，
否则字段只能是个永远为真的注释。

本次补的收起能力是壳内局部状态，不影响默认布局：
- 默认仍展开（三栏工作台外观不变）；
- 用户可点画布标题右侧的「收起画布」按钮（`aria-label="收起画布"`）；
- 收起后右栏变成 48px 细条，有条「展开画布」按钮 + 竖排「画布 已收起」；
- 切模块时按声明决定初始开合：展示型展开、对话型收起。

---

## 2. 契约与实现

### 2.1 `lib/canvasFeature.ts`

```ts
export interface CanvasPreview {
  /** 空态按钮文案，如「查看公差带示例」 */
  label: string;
  /** 样例 artifact 数据 */
  data: Record<string, unknown>;
}

export interface CanvasFeature {
  id: string;
  title: string;
  hint: string;
  artifactTypes: string[];
  order: number;
  preview?: CanvasPreview;      // 新增
  autoOpenCanvas?: boolean;     // 新增
  Component: ComponentType<FeatureProps>;
}
```

### 2.2 `preview` 下沉（4 个 feature，label 逐字沿用）

| feature | preview 来源 | label（与改造前一致） | 说明 |
|---|---|---|---|
| `tolerance` | `modules/tolerance/demo.ts` → `TOLERANCE_DEMO_DATA` | 查看公差带示例 | 单示例 |
| `three_view` | `modules/three/demo.ts` → `THREE_VIEW_DEMO_DATA` | 查看三视图示例 | 单示例 |
| `comparison` | `modules/comparison/demo.ts` → `COMPARISON_DEMO_DATA` | 查看辨析示例 | projection 模块的第一个示例 |
| `quiz` | `modules/quiz/demo.ts` → `QUIZ_DEMO_DATA` | 查看题卡示例 | projection 模块的第二个示例 |

> `demo.ts` 文件全部保留，只是不再被壳直接 import。示例数据仍标注「示例数据」，
> `Component` 的 `demo` prop 语义没变。

`features/tolerance/index.ts` 实际写法：

```ts
import { TOLERANCE_DEMO_DATA } from '../../modules/tolerance/demo';

const feature = {
  id: 'tolerance',
  // …title/hint/artifactTypes/order…
  preview: {
    label: '查看公差带示例',
    data: TOLERANCE_DEMO_DATA as unknown as Record<string, unknown>,
  },
  autoOpenCanvas: true,
  Component: ToleranceCanvas,
} satisfies CanvasFeature;
```

### 2.3 registry 汇总

`modules/registry.ts` 新增三张表与三个 getter（原有三个导出不动）：

```ts
const PREVIEWS = new Map<string, CanvasPreview>();
const PREVIEW_TYPES = new Map<string, string>();
const AUTO_OPEN = new Map<string, boolean>();

for (const feature of features) {
  // …REGISTRY 原有逻辑…
  const firstType = feature.artifactTypes[0];
  if (firstType) {
    PREVIEW_TYPES.set(feature.id, firstType);
    for (const t of feature.artifactTypes) PREVIEW_TYPES.set(t, t);
  }
  if (feature.preview) {
    PREVIEWS.set(feature.id, feature.preview);
    for (const t of feature.artifactTypes) PREVIEWS.set(t, feature.preview);
  }
  for (const t of feature.artifactTypes) {
    AUTO_OPEN.set(t, Boolean(feature.autoOpenCanvas));
  }
}

export function getPreview(featureId: string): CanvasPreview | null {
  return PREVIEWS.get(featureId) ?? null;
}
export function getPreviewType(featureId: string): string | null {
  return PREVIEW_TYPES.get(featureId) ?? null;
}
export function shouldAutoOpen(artifactType: string): boolean {
  return AUTO_OPEN.get(artifactType) ?? false;
}
```

`getCanvasDef` / `KNOWN_CANVAS_TYPES` / `isPlaceholder` 签名与行为不变。

### 2.4 CanvasPanel 读取方式（以及为什么不是字面 `getPreview(activeFeature)`）

`CanvasPanel` 删除了：

```ts
import { TOLERANCE_DEMO_DATA } from '../modules/tolerance/demo';
import { THREE_VIEW_DEMO_DATA } from '../modules/three/demo';
import { COMPARISON_DEMO_DATA } from '../modules/comparison/demo';
import { QUIZ_DEMO_DATA } from '../modules/quiz/demo';
function demoItems(feature: string) { /* 4 个 case */ }
```

改为按**当前模块声明的 canvas_kinds**取示例：

```ts
const previews = useMemo(() => {
  const kinds = activeModule?.canvas_kinds ?? [];
  const list: { type: string; preview: CanvasPreview }[] = [];
  const seen = new Set<string>();
  for (const type of kinds) {
    if (seen.has(type)) continue;
    seen.add(type);
    const preview = getPreview(type);
    if (preview) list.push({ type, preview });
  }
  return list;
}, [activeModule]);
```

**为什么不是 `getPreview(activeFeature)`**：我们的 `activeFeature` 是**后端模块 id**，
而 `CanvasFeature.id` 是**前端画布 id**，两者不是一一对应：

| 模块 id | canvas_kinds | feature id |
|---|---|---|
| `sandbox3d` | `['three_view']` | `three_view` |
| `projection` | `['comparison','quiz']` | `comparison` + `quiz` |
| `kbrag` | `['evidence']` | `evidence` |

所以按 `canvas_kinds` 逐个取（`getPreview('three_view')` / `getPreview('comparison')`…）
才能同时拿到 projection 的两个示例。`getPreview` 本身按 feature.id/artifactType 存，
壳之所以能拿到，是因为我们对每个 artifactType 都做了同一条 preview 的映射。
（若硬按 `getPreview(activeFeature)`，`sandbox3d`/`projection` 会返回 null —— 这是本次
发现的「模块 id ≠ feature id」水土不服，见 §5。）

`demoArtifact` 用 `getPreviewType(type)` 构造 artifact 的 `artifactType`，保证与真实产物同形：

```ts
const hit = previews.find((p) => p.type === demoType);
const artifactType = getPreviewType(hit.type) ?? hit.type;
return { artifactType, data: { ...hit.preview.data }, receivedAt: Date.now() };
```

---

## 3. `autoOpenCanvas` 取值表与理由

### 3.1 最终取值（与 `docs/模块任务书` 自动生成的值一致）

| # | feature | artifactType | autoOpenCanvas | 理由 |
|---|---|---|---|---|
| 1 | `evidence` | `evidence` | **true（例外）** | 证据溯源是核心交付；收起会让学生看不到出处（对应 §5 D 的「保留 true」）。 |
| 2 | `tolerance` | `tolerance` | true | 公差带图是交付物。 |
| 3 | `graph` | `graph` | true | 星图/问题图是交付物。 |
| 4 | `coach` | `coach` | true | 分步作图以图为主体。 |
| 5 | `three_view` | `three_view` | true | 三视图本身是交付物。 |
| 6 | `quiz` | `quiz` | false | 做题，正文/解析在对话流。 |
| 7 | `annotation` | `annotation` | false | 费曼追问在正文，画布是附注。 |
| 8 | `wrongbook` | `wrongbook` | false | 六步诊断在正文，画布是附注。 |
| 9 | `comparison` | `comparison` | true | 成对图是主体。 |

> 与需求表的差异：需求表把 `evidence` 写成 false，我按 D 条例外保留 true，报告明确说明。
> 其余 8 个与需求表一致。

### 3.2 实现语义

```ts
// 切模块：按该模块 canvas_kinds 的声明决定初始开合
useEffect(() => {
  setDemoType(null);
  const kinds = activeModule?.canvas_kinds ?? [];
  if (kinds.length === 0) return;               // 全局对话不强制改开合
  setCollapsed(!kinds.some((type) => shouldAutoOpen(type)));
}, [activeFeature, activeModule]);

// artifact 到达：true 才重新展开；false 保持用户当前状态（不抢屏）
useEffect(() => {
  if (latestArtifactType && shouldAutoOpen(latestArtifactType)) setCollapsed(false);
}, [latestArtifactType, artifacts.length]);
```

- `true`：即使画布被用户收起，artifact 到达也会自动展开（实测 three_view、evidence）；
- `false`：**不会自动展开**；进入该模块时若它只有 false 类型，画布初始就是收起的；
- 用户随时可点细栏的「展开画布」手动打开；
- 收起只影响布局，不删除 `session.artifacts`，展开后内容仍在。

### 3.3 行为变化清单（有意变化）

| 场景 | 改造前 | 改造后 | 原因 |
|---|---|---|---|
| 进入 `形体重构与费曼追问`（annotation） | 右栏常驻展开 | 初始收起（细栏），artifact 到达仍不展开 | 对话型，画布不抢屏 |
| 进入 `智能找茬与错题本`（annotation/wrongbook） | 右栏常驻展开 | 初始收起，artifact 到达仍不展开 | 同上 |
| 在 `projection` 里已收起画布后问出 quiz | 无法收起，恒展开 | 保持收起（quiz autoOpen=false） | quiz 是对话型 |
| 问出 evidence | 恒展开 | 仍展开（autoOpen=true 例外） | 证据溯源需要被看到 |
| tolerance/graph/coach/three_view/comparison | 恒展开 | 切模块/artifact 到达均自动展开 | 展示型 |
| 其他模块的“手动收起” | 不存在 | 新增能力；默认展开，用户主动收起才生效 | 让 autoOpen 有可观测语义 |

**内容不丢**：`session.artifacts` 与 `selected` 逻辑未动；收起只是 `CanvasPanel` 返回细栏，
展开后仍是原 artifact/标签页。

---

## 4. 验收输出（逐条）

### 4.1 `npm run build`

```
> machdraw-web@0.1.0 build
> tsc --noEmit && vite build

vite v6.4.5 building for production...
✓ 74 modules transformed.
dist/index.html                   1.05 kB │ gzip:   0.69 kB
dist/assets/index-CvD33ZKO.css   72.35 kB │ gzip:  12.90 kB
dist/assets/index-CubjG0uc.js   397.28 kB │ gzip: 124.05 kB
✓ built in 873ms
```

### 4.2 9 个画布仍正常渲染

9 个模块实测（浏览器 1256×800，独立 headless Edge）：

| type | auto | 进入时收起？ | 提问后 | 标题（读回） | 画布根节点 |
|---|---|---|---|---|---|
| evidence | true | false | 展开 | 证据溯源画布 | `.ev-summary` ✅ |
| tolerance | true | false | 展开 | 公差与配合画布 | `.tol-body` ✅ |
| graph | true | false | 展开 | 知识图谱画布 | `.kg-body` ✅ |
| coach | true | false | 展开 | 作图教练画布 | `.coach-body` ✅ |
| three_view | true | false | 展开 | 三视图投影画布 | `.tv-body` ✅ |
| quiz | false | false（projection 模块因 comparison=true 展开） | 保持展开 | 题卡画布 | `.qz-body` ✅ |
| annotation | false | **true** | 手动展开后渲染 | 三色标注画布 | `.ann-body` ✅ |
| wrongbook | false | **true** | 手动展开后渲染 | 错题诊改画布 | `.wb-body` ✅ |
| comparison | true | false | 展开 | 成对图辨析画布 | `.cmp-body` ✅ |

截图：`_shots/47-registry-{evidence,tolerance,graph,coach,three_view,quiz,annotation,wrongbook,comparison}.png`
（关键：evidence / tolerance / graph）。

### 4.3 4 个有 preview 的 feature（3 个模块）空态示例

| 模块 | 空态按钮 label | 点击后 | 「示例数据」标记 |
|---|---|---|---|
| 公差与配合侦探 | 查看公差带示例 | `.tol-body` 渲染 | ✅ |
| 3D 可视化沙盒 | 查看三视图示例 | `.tv-body` 渲染 | ✅ |
| 剖视与投影辨析 | 查看辨析示例 | `.cmp-body` 渲染 | ✅ |
| 剖视与投影辨析 | 查看题卡示例（示例切换 chip） | `.qz-body` 渲染 | ✅ |

截图：`_shots/49-preview-tolerance.png`、`49-preview-three.png`、`49-preview-comparison.png`、
`49-preview-quiz.png`。

### 4.4 5 个没有 preview 的模块：空态无示例按钮

| 模块 | `.btn-demo` 数量 |
|---|---|
| 国标与概念溯源 | 0 |
| 知识图谱 | 0（有全览入口画布，不是空态，但同样无示例按钮） |
| 虚拟画图教练 | 0 |
| 形体重构与费曼追问 | 0 |
| 智能找茬与错题本 | 0 |

没有死按钮。

### 4.5 autoOpenCanvas 实测

| 用例 | 操作 | 声明 | 实测 |
|---|---|---|---|
| three_view | 先手动收起，再问「三视图的投影规律」 | true | **自动展开** ✅ |
| evidence | 先手动收起，再问「剖视图和断面图的区别？」 | true（例外） | **自动展开** ✅ |
| annotation | 进入费曼模块（初始收起），问「我来讲讲什么是剖视图…」 | false | **进入收起，artifact 后仍收起** ✅；手动点细栏可展开并渲染 |

截图：`_shots/50-autoopen-three.png`、`50-autoopen-evidence.png`、
`50-autoopen-feynman-collapsed.png`。

### 4.6 `python apps\api\tests\check_reachability.py`

```
[2] artifact_type 认领检查
  后端可产出 9 种：annotation, coach, comparison, evidence, graph, quiz, three_view, tolerance, wrongbook
  前端 features 注册 9 个 feature / 9 个 artifactType
  OK   annotation … OK wrongbook
[3] 空画布检查（前端注册了但后端永不产出）
  OK   annotation … OK wrongbook
全部通过：11 工具可达 · 9 artifact_type 均有认领 · 9 画布均有产出
```

（加 `preview` / `autoOpenCanvas` 字段不影响它；它只扫 `artifactTypes`。）

### 4.7 `python verify_all.py`

```
[PASS] 后端工具自注册                    全部通过：11 个工具自注册成功 · 三条硬校验全绿 · …
[PASS] 确定性引擎（公差/螺纹/圆弧）            通过 31 / 失败 0
[PASS] 三视图真投影                     通过 14 / 失败 0
[PASS] 工具/画布可达性                   全部通过：11 工具可达 · 9 artifact_type 均有认领 · 9 画布均有产出
[PASS] 模块任务书与代码一致                 [OK] 10 份任务书与代码一致
[PASS] 剖视图真剖切（全剖）                 …
[PASS] 半剖 / 局部剖                   通过 9 / 失败 0
[PASS] 手绘找茬                       通过 12 / 失败 0
[PASS] 端到端冒烟                      …
[PASS] 检索与门控（54 题标定集）             τ=0.55 λ=0.45 acc=1.0 课内min=0.5796 课外max=1.0 分离带=-0.4204
[PASS] 服务健康                       语料 566 块 / 32 文档 · 图谱 169 节点 279 边 · 工具 11 个
合计 11 项，通过 11，失败 0
```

> 按新基础设施是 **11 项**（不是 10 项）：任务书一致性、工具自注册等已并入。

### 4.8 `gen-module-docs.py`

`python scripts/gen-module-docs.py` 已重新生成 `docs/模块任务书/`（9 份 + README），
`python scripts/gen-module-docs.py --check` 输出：

```
[OK] 10 份任务书与代码一致
```

生成后的索引（自动记录 autoOpen 值）：

| 模块 | artifactType | 自动展开 |
|---|---|---|
| 三色标注画布 | annotation | false |
| 作图教练画布 | coach | true |
| 成对图辨析画布 | comparison | true |
| 证据溯源画布 | evidence | true |
| 知识图谱画布 | graph | true |
| 题卡画布 | quiz | false |
| 三视图投影画布 | three_view | true |
| 公差与配合画布 | tolerance | true |
| 错题诊改画布 | wrongbook | false |

**脚本改动（必要）**：`parse_ts_object` 原来用 `preview:\s*(\w+)` 只认变量名，
我们的 preview 是对象 `{ label, data }`，会解析失败 → 任务书显示「样例数据 无」。
已改成从 preview 对象里抽 `label`（保留变量名兜底）；同时把生成的验收清单「全量 10 项」改为 11 项。
否则 `--check` 会因文档与代码不一致而红。

---

## 5. `autoOpenCanvas` 在我们项目里成立吗？（水土不服）

结论：**成立，但只能当「展开提示」而不是「默认收起/展开的硬契约」**。原因如下：

### 5.1 默认布局不同

参考作品默认画布收起，`autoOpenCanvas` 是一个真正的“开/关”动作；
我们默认三栏常驻，画布一直可见。为了让字段有意义，我加了「手动收起」；
`autoOpenCanvas=false` 的语义变成「**不要把用户收起的画布抢开**」，而不是「关掉画布」。
`true` 的语义则保持不变（artifact 到达自动展开）。

如果产品以后决定改成“默认收起、需要才展开”，可以把 `collapsed` 初始值设为 true，
`autoOpenCanvas` 就能完全对齐参考语义；但那会改变当前三栏工作台的首屏，需要单独决策。

### 5.2 模块 id ≠ feature id

参考作品一个模块一个 artifactType，`activeFeature` 基本等于 feature id；
我们的后端模块 id（`sandbox3d`/`projection`/`kbrag`…）与前端 feature id
（`three_view`/`comparison`+`quiz`/`evidence`…）是两套命名，而且一个模块可对应多个 feature。
所以：
- `getPreview(activeFeature)` 不能直接工作，必须按 `activeModule.canvas_kinds` 逐个查；
- `autoOpenCanvas` 必须按 **artifactType** 判断（`shouldAutoOpen`），不能按模块 id；
- 一个模块里可能混合 true/false（如 `projection` = comparison(true)+quiz(false)），
  进入模块时按 `some(true)` 展开，单个 quiz artifact 到达时仍遵守 false（不抢开）。

### 5.3 数据在后端，artifact 到达时机不同

参考作品模块自己持有静态数据，artifact 只带 `{mode, focus}`，模块可以在本地随时预览；
我们的画布数据完全由后端 SSE 的 artifact 下发，`preview` 只是空态兜底。
这带来两个后果：
1. `preview` 与真实 artifact 的字段可能长期漂移（demo 数据是快照）；本次只是把
   `demo.ts` 的引用移进模块，没有解决漂移检测（需要像 `types.ts` 一样给 demo 做类型校验，
   目前 `as unknown as Record<string, unknown>` 会绕过检查）。
2. 一轮可能下发多个 artifact（graph+evidence、comparison+quiz+three_view+evidence），
   `autoOpenCanvas` 只能按「最后一个 artifact 的类型」判断；如果同一轮既有 true 又有 false，
   后到的 false 不会把已展开的画布收起（符合“不抢屏”，但“该开还是该关”没有全局优先级）。
   建议后续定义：一轮内任意 true 则展开，否则保持当前状态。

### 5.4 收起状态未持久化

`collapsed` 是 `CanvasPanel` 的局部 state，刷新/切账号会回到默认展开；
如果要像参考作品那样记住用户偏好，需要放进 store/localStorage（本次没做，避免扩大改动面）。

### 5.5 壳的布局改动是运行时写 `--right-w`

收起时在 `.workbench` 上内联 `--right-w:48px`，展开时移除（不改 `styles/`）。
窄屏（<=820px，画布在底部整行）不参与收起。这属于壳内的轻量 implementation，
但严格说“壳的布局”仍由 CanvasPanel 控制；若以后要加“全屏/拖宽”，建议把这些状态上移。

---

## 6. 文件清单

**新增/修改（本阶段）**

```
apps/web/src/lib/canvasFeature.ts        # CanvasPreview + preview/autoOpenCanvas 字段
apps/web/src/features/{evidence,tolerance,graph,coach,three_view,quiz,annotation,wrongbook,comparison}/index.ts
                                         # 4 个 preview + 9 个 autoOpenCanvas
apps/web/src/modules/registry.ts         # PREVIEWS/PREVIEW_TYPES/AUTO_OPEN + 3 个 getter
apps/web/src/shell/CanvasPanel.tsx       # 删 4 个 demo import/demoItems；从 registry 取 preview；
                                         # 新增收起/展开 + autoOpen 逻辑
scripts/gen-module-docs.py               # preview 对象解析 + 验收项 10→11
docs/模块任务书/*.md                     # 重新生成（自动记录 autoOpen / 样例数据）
```

**未改**：`styles/`；9 个 `modules/*/Canvas.tsx`；4 个 `modules/*/demo.ts`（保留）；
`package.json`（无新依赖）。

---

## 7. 截图

- 9 个画布：`_shots/47-registry-*`
- 4 个 preview：`_shots/49-preview-*`
- autoOpen：`_shots/50-autoopen-{three,evidence,feynman-collapsed}.png`
