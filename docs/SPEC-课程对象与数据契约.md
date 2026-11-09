# 核反应堆物理 AI 助教 Agent · 复刻规格（单一事实源）

> 本文件是团队施工的**唯一事实源**。所有模块、知识库、题库、图库、前后端、评测、文档都必须服从本文件的命名与字段。
> 参照工程：`D:\桌面\教学agent\机械制图agent`（已完成，只读）。本工程为同一套架构在《核反应堆物理》课程上的复刻。
> 更新原则：任何契约变更先改本文件，再改代码。

---

## 0. 课程身份

- 课程：**核反应堆物理**（西安交通大学 核科学与技术学院，曹良志 教授课程；教材《核反应堆物理分析》清样）
- 课程物料：根目录 10 章 PPTX + 教材 PDF（255 页，有文字层）+ 复习笔记 v0.4（28 页）+ 课后习题解答 v4.0（37 页）+ 2 个 Word97 教材/习题 doc + 2 个扫描 PDF（11-14 核物理反应堆、压水堆燃料管理） + `物理分析PPT.zip`
- 定位：**懂方程、通能谱、能算准、可溯源**。每句结论都能翻到教材/课件/标准原文；越界问题明确拒答。
- 三条硬能力（对标机械制图的"公差/圆弧/三视图"）：
  1. **临界与扩散计算**（k∞/M²/材料曲率/几何曲率/临界尺寸/反射层节省）
  2. **点堆动力学与反应性**（六组缓发中子、倒时方程、周期、瞬发临界、反应性换算）
  3. **燃耗与中毒**（碘氙/钐的平衡与停堆瞬变、燃耗深度、循环长度）

---

## 1. 章节代码（固定，不得改动文案）

| 代码 | 章名（数据里逐字使用） | 内容 |
|---|---|---|
| `C01`/`INTRO` | 第一章 绪论 | 反应堆定义、分类、堆芯与输运过程 |
| `C02`/`NUCPHY` | 第二章 核物理基础 | 中子与核作用、截面、1/v、共振与多普勒、裂变 |
| `C03`/`NEUTRON` | 第三章 反应堆中子学过程 | 链式反应、k_eff、四因子、慢化、扩散、徙动长度 |
| `C04`/`DIFF` | 第四章 中子扩散理论与计算 | 单群扩散、临界条件、多群、功率计算 |
| `C05`/`SPEC` | 第五章 中子能谱与群常数计算 | 裂变谱、1/E 谱、共振能谱、热谱、非均匀 |
| `C06`/`BURN` | 第六章 燃耗与中毒 | 燃耗链、氙/钐、燃耗数值、寿期与燃耗深度 |
| `C07`/`REACT` | 第七章 反应性系数与反应性控制 | 温度/空泡/功率系数、控制棒/可燃毒物/硼 |
| `C08`/`KIN` | 第八章 核反应堆中子动力学 | 缓发中子、点堆方程、周期、瞬发临界 |
| `C09`/`FUEL` | 第九章 堆芯核燃料管理 | 循环长度、换料方式、多循环 |
| `C10`/`DESIGN` | 第十章 堆芯核设计 | 核设计流程、堆芯布置、安全限值 |

数据库/知识库中的 `chapter` 字段一律用**完整章名**（如 `"第四章 中子扩散理论与计算"`），不得写 `C04` 或 `第4章`。

---

## 2. ID 规约

| 对象 | 格式 | 示例 |
|---|---|---|
| 知识点 | `KP-<CODE>-<三位>` | `KP-DIFF-007` |
| 图谱节点 | `KN-<三位>` | `KN-042` |
| 图谱问题 | `Q-<三位>` | `Q-003` |
| 教学图 | `FIG-<大写TAG>` | `FIG-XENON-CURVE` |
| 辨析对 | `PAIR-<大写TAG>` | `PAIR-SPECTRUM` |
| 习题 | `EX-<CODE>-<两位>` | `EX-DIFF-03` |
| 文档 | `DOC-TEXTBOOK` / `DOC-NOTES` / `DOC-SLIDES-C04` / `DOC-STD-<X>` / `DOC-WEB-<X>` | — |
| 分块 | `chk_<doc_id>_<父块4位>_<子块4位>`（由流水线生成） | — |

---

## 3. 知识库数据契约（逐字段，缺失字段由装载器容错）

### 3.1 `kb/knowledge/kp.jsonl`（一行一个知识点）
| 字段 | 类型 | 说明 |
|---|---|---|
| `kp_id` | str | 见规约 |
| `chapter` | str | 完整章名 |
| `section` | str | 小节路径，如 `"4.2 增殖介质单能中子扩散方程"` |
| `term` | str | 知识点名 |
| `aliases` | str[] | 别名/学生常说错的说法 |
| `definition` | str | 教材口径的定义（自写表述，落原文依据） |
| `points` | str[] | 3~5 条要点 |
| `common_mistakes` | str[] | 常见错误（学生视角） |
| `refs` | str[] | 依据（教材章节/页码、课件页码、标准号） |
| `bloom` | str | 记忆/理解/应用/分析/综合 |
| `level` | int | 1~4 难度 |

### 3.2 `kb/graph/nodes.jsonl`
`{"id","kp_id","label","tier","chapter","state"}`；`tier ∈ {core, trackA, trackB, branch, concept}`；`state` 固定 `"未学"`。

### 3.3 `kb/graph/edges.jsonl`
`{"source","target","rel","note"}`；`rel ∈ {prereq, contrast, cause, compose}`。`note` 一句话说清为什么。

### 3.4 `kb/graph/questions.jsonl`
`{"qid","layer","question","bloom","kp_ids","hint"}`；`layer ∈ {1,2,3}`（1 记忆/2 理解/3 综合）。

### 3.5 `kb/figures/figures.jsonl`
`{"figure_id","file","title","chapter","kp_ids","structure_tags","caption","license","source"}`
- `file` 相对 `kb/figures/`，如 `FIG-XENON-CURVE.svg`
- `license` 一律 `"自绘"`；`source` 写明依据（`"依据教材第6章 6.x 节自绘"`）

### 3.6 `kb/figures/pairs.jsonl`（辨析对）
`{"pair_id","file","title","module","chapter","kp_ids","a":{"label","caption","正确性"},"b":{...},"differences":[{"no","name","a_desc","b_desc","why"}],"question":{"stem","options":[],"answer_index","explain"},"license","source"}`
- `module ∈ {concept, graph}`；`正确性 ∈ {正确, 错误, 对比项}`
- `file` 相对 `kb/figures/`，如 `pairs/PAIR-XENON.svg`

### 3.7 `kb/exercises/exercises.jsonl`
`{"exercise_id","chapter","stem","book_page","qno","answer_page","model_page","source","internal_only"}`
- `source` 写清出处；`internal_only` 一律 `true`（版权受限，仅内部教研）
- 有解答的必须给 `answer_page`；教材例题用 `model_page`

### 3.8 `kb/standards/*.md`
front matter：`doc_id,title,category,role,source,license,version,internal_only,effective`。`role` 一律 `standard`；`category` 如 `"核安全法规"`、`"国家标准"`、`"核数据"`。
正文：Markdown，一、二、三 结构；**只做事实性整理 + 自写表述，不复制标准原文**。

### 3.9 `kb/web/*.md`
front matter：`doc_id,title,category,role,source,license,retrieved,internal_only`。`role` 一律 `authority` 或 `lecture`，`category` 如 `"拓展阅读"`。只收可公开引用的资料，逐份记来源与许可。
清单：`kb/_manifest_web.json`（数组，每项含 `doc_id,title,source,license,retrieved`）。

---

## 4. 画布（Artifact）与模块

### 4.1 八类画布（`ARTIFACT_TYPES`，前端一模块一画布）
| 画布 | 用途 | 对应旧工程 |
|---|---|---|
| `evidence` | 证据溯源卡 | 同 |
| `calc` | **确定性计算卡**：输入 → 公式步 → 结果 → 校核 | 替代 `tolerance` |
| `plot` | **曲线/分布图卡**：能谱、响应、中毒曲线 | 替代 `three_view` |
| `comparison` | 成对图辨析 | 同 |
| `annotation` | 逐句三色标注 / 费曼 / 计算步骤标注 | 同 |
| `quiz` | 随堂题 | 同 |
| `wrongbook` | 错题六步诊改 | 同 |
| `graph` | 知识图谱 | 同 |

**`calc` 画布 data 契约**：
```json
{"title":"Φ... 临界计算","inputs":[{"name":"材料曲率 B_m²","value":0.0031,"unit":"cm⁻²"}],
 "formulas":[{"step":"k_eff = k∞ / (1 + M²B²)","note":"单群临界条件"}],
 "results":[{"name":"k_eff","value":1.0021,"unit":"","note":""}],
 "verdict":{"level":"临界","note":"..."},
 "refs":["教材 4.3 节 p.114"],
 "svg":"<svg ...>..."}
```
**`plot` 画布 data 契约**：
```json
{"kind":"curve|spectrum|distribution","title":"...","x_label":"t / s","y_label":"n/n0",
 "series":[{"name":"功率响应","points":[[0,1.0],[0.1,1.8]]}],
 "markers":[{"x":0.0,"y":1.0,"label":"阶跃"}],
 "note":"...","refs":["教材 8.x"],"svg":"<svg ...>..."}
```

### 4.2 九个模块（`app/state.py` MODULES）
| id | 名称 | canvas_kinds | tools |
|---|---|---|---|
| `__global__` | 全局对话 | evidence | kb_search, kg_lookup, critical_calc, kinetics_calc, poison_calc |
| `kbrag` | 教材与概念溯源 | evidence | kb_search, kg_lookup |
| `critical` | 临界与扩散计算 | calc | critical_calc, spectrum_plot, kb_search |
| `kinetics` | 动力学与反应性 | plot | kinetics_calc, reactivity_calc, spectrum_plot, kb_search |
| `poison` | 燃耗与中毒 | plot | poison_calc, burnup_calc, kb_search |
| `concept` | 概念辨析 | comparison, quiz | comparison_pick, quiz_from_kb, kb_search |
| `graph` | 知识图谱 | graph | kg_lookup, kb_search |
| `wrongbook` | 错题与计算批改 | annotation, wrongbook | wrongbook_crud, kb_search, quiz_from_kb |
| `feynman` | 费曼追问 | annotation | kb_search |

### 4.3 十一个工具（`app/tools/<name>.py`，自注册，`TOOL.name` 必须等于文件名）
| name | 画布 | 说明 |
|---|---|---|
| `kb_search` | evidence | 课程原文检索（带双门控） |
| `kg_lookup` | graph | 图谱查询 |
| `critical_calc` | calc | 单群/双群临界计算（k_eff、临界尺寸、反射层节省、不泄漏概率） |
| `kinetics_calc` | plot | 点堆动力学（倒时方程、周期、瞬发跳跃、阶跃响应曲线） |
| `poison_calc` | plot | 氙/钐平衡与停堆瞬变（碘坑、反应性当量） |
| `burnup_calc` | calc | 燃耗深度、U-235 消耗、循环长度（线性反应性模型） |
| `reactivity_calc` | calc | 反应性换算（pcm/$/Δk·k⁻¹）、温度系数、功率亏损 |
| `spectrum_plot` | plot | 能谱/分布曲线（裂变谱、1/E、Maxwell、压水堆合成谱） |
| `comparison_pick` | comparison | 辨析对选择 + 差异点 + 随堂题 |
| `quiz_from_kb` | quiz | 从题库出题 |
| `wrongbook_crud` | wrongbook | 错题本增删查 |

---

## 5. 确定性引擎契约（`app/domain/`）

> 铁律：能算的绝不让模型背。所有常数、公式必须来自教材/习题解答原文，并在 docstring 标注出处（章·节·页）。
> 每个引擎必须有 `tests/` 下的**锚点校验**（教材例题/习题的原题原答案），不通过不算完成。

| 模块 | 函数（建议签名） | 输出 |
|---|---|---|
| `critical.py` | `k_inf_from_four_factor(eps,p,f,eta)`；`buckling_material(k_inf,L2,tau)`；`buckling_geometric(geometry,dims,d)`；`k_eff_single_group(...)`；`critical_size(geometry,k_inf,L2,tau,d,reflector_saving)`；`four_factor(...)` | Bm²、Bg²、k_eff、Ps/Pd/PL、临界尺寸、ρ |
| `kinetics.py` | `inhour_root(rho,l,beta_groups)`；`period(...)`；`prompt_jump(...)`；`response_curve(rho, t_end, dt, ...)`；`SIX_GROUP_U235` | 周期 T、s、n/n0 曲线、瞬发临界判定 |
| `poison.py` | `xenon_equilibrium(flux,...)`；`xenon_transient(flux,t_irr,t_down)`；`samarium_equilibrium(...)`；`reactivity_worth(...)` | I/Xe/Pm/Sm 浓度、ρ_eq、碘坑深度、允许停堆时间 |
| `burnup.py` | `burnup_depth(...)`；`u235_consumption(...)`；`cycle_length_linear(...)`；`conversion_ratio(...)` | MWd/tU、kg、EFPD |
| `reactivity.py` | `rho_from_k`；`k_from_rho`；`rho_dollar`；`unit_convert`；`temperature_coefficient`；`power_defect` | 数值 + 单位 |
| `spectrum.py` | `fission_spectrum(E)`；`maxwellian(E,T)`；`fermi_spectrum(E)`；`pwr_spectrum(E)`；`group_average(sigma_fn, bounds, weight)` | 曲线点 + 群平均截面 |
| `rod.py` | `rod_integral_worth(...)`；`rod_differential_worth(...)`；`boron_worth(...)`；`critical_boron(...)` | 价值（pcm）、微分价值曲线 |

`app/plots/`：把曲线数据渲染成自包含 SVG（无 JS 依赖，统一 16px 字体、深色底可读），供 `plot` 画布与图库复用。

---

## 6. 工程结构与品牌

```
apps/api/app/        后端（FastAPI）
  contracts/models.py  契约（改这里=改全项目）
  rag/                 符号归一/分词/切分/索引/检索/门控（基本照搬）
  tools/               11 个工具（自注册）
  domain/              7 个确定性引擎
  plots/               SVG 曲线渲染
  modules/             feynman.py / wrongbook.py（照搬后改写文案）
  orchestrator.py      ReAct 规则编排（重写 _plan/_answer_from_tool）
  state.py             模块注册表 + 装载
apps/web/src/        前端（React 三栏壳，模块自注册）
kb/                  知识库（standards/knowledge/graph/figures/web/exercises）
pipeline/            离线构建（build_kb.py 重写切分规则）
eval/                探针 + 评测
docs/                规划与验收文档
data/                索引与数据库（可重建，不进版本库）
working/             材料抽取中间产物（机读，可删）
```

- 品牌：`核反应堆物理 AI 助教`；页面标题、TopBar、README、Docker 镜像名统一。
- 环境变量前缀：**`RP_`**（替换旧 `MW_`）：`RP_SPARSE_WEIGHT / RP_GATE_TAU / RP_OOV_WEIGHT / RP_COVERAGE_MODE / RP_GATE_TAU_CHUNK / RP_RECALL_K / RP_TOP_K / RP_LLM_PROVIDER / RP_LLM_MODEL / RP_LLM_BASE_URL / RP_LLM_API_KEY / RP_LLM_EXTRA_BODY / RP_INTERNAL_ONLY`。

---

## 7. 语料与版权

- 教材、课件、复习笔记、习题解答均为**用户提供的课程内部资料**，入库标 `internal_only=true`（与机械制图对习题集的处理一致）。
- 自建知识条目、图谱、图库、标准整理为**自写表述**，可对外。
- 扫描版 PDF（11-14 核物理反应堆、压水堆燃料管理）无文字层：只做"背景参考"，不强行 OCR 入库；如需引用，必须人工核对。

---

## 8. 验收口径（全项目）

1. 后端可启动：`uvicorn app.main:app`，`GET /api/health` 返回 kb/tools/modules/figures 装载数且无 warning。
2. 11 个工具全部注册成功；每个确定性工具至少有 1 条锚点校验通过；全部锚点测试 `python tests/run_anchors.py` 全绿。
3. `npm run build` 通过；前端 9 个模块条目自注册、**8 类画布**可渲染（calc/plot 有 demo 数据）。
4. 题库 ≥ 100 题、知识点 ≥ 140、图谱节点 ≥ 140 / 边 ≥ 220 / 问题 ≥ 20、图 ≥ 26 张、辨析对 ≥ 6 组。
5. 评测：课内探针命中率 ≥ 0.85，课外探针拒答率 ≥ 0.85（门控）。
6. 文档齐全（见第 9 节）。

## 9. 文档清单（docs/）
`00-工程解剖与复刻蓝图`（anatomy）、`SPEC-课程对象与数据契约`（本文件）、`01-课程材料盘点`、`02-知识库与图谱`、`03-确定性引擎`、`04-教学图库`、`05-系统实现与验收`、`06-评测与门控`、`07-交付说明`、`08-复刻对照表`。
