# 00a · 后端解剖（二）：RAG 全链路 / `kb/` 逐文件 schema / 数据库·配置·LLM

> 承接 `00-工程解剖与复刻蓝图.md`。本卷覆盖任务清单第 4、5 条与第 8 条（SQLite、配置/env、LLM 降级、mock）。
> 路径相对 `R = D:\桌面\教学agent\机械制图agent`。

---

## 4. RAG 全链路（`apps/api/app/rag/`，5 文件 783 行）

### 4.0 全景：一次检索到底发生了什么

```
load_kb()                         chunking.py:202
 ├─ rglob("kb/**/*.md")           排除 README.md → parse_front_matter → chunk_markdown()
 ├─ kb/knowledge/kp.jsonl         → chunk_knowledge()
 └─ kb/exercises/*.jsonl          （跳过文件名含 "answer" 的）→ chunk_exercises()
        ↓  list[Chunk]（contracts.models.Chunk）
build_index(chunks)               index.py:177
 ├─ 每块 tokenize(section+"\n"+text)  → tf / len / df
 ├─ idf = log(1 + (N-df+0.5)/(df+0.5))                      index.py:59-61
 ├─ 稠密：hashing tf-idf（crc32 → 桶 + 符号）→ HASH_DIM=4096 → L2 归一   :83-104
 └─ save() → data/index/{chunks.jsonl, vecs.npy, meta.json}            :141-161
        ↓
Retriever.search(query, top_k)    retrieve.py:107
 ├─ bm25 = index.bm25_scores(query)        k1=1.5, b=0.75             index.py:108-123
 ├─ dense = index.dense_scores(query)      vecs @ q_vec              index.py:134-137
 ├─ fused = λ*minmax(bm25) + (1-λ)*minmax(dense) + phrase_boost         :120-124
 ├─ 排序 + 角色过滤（默认排除 exercise/answer）+ recall_k=24 截断        :126-141
 ├─ 双门控：coverage(召回块并集) + best_chunk_cov(单块 top10)            :143-166
 └─ top_k 个 Evidence（score 截到 ≤1.0，保留 4 位）                      :168-186
```

### 4.1 符号归一（`rag/symbols.py` 135 行）

机械制图提问大量是符号型（`⌀20H7`、`Ra 3.2`、`⊥ 0.05`、`M12×1.5`），纯语义向量对符号几乎无效，所以**检索前必须先归一**（文件头注释 `symbols.py:1-7`）。

`normalize(text)` 的执行顺序（`symbols.py:53-67`）：

| 步 | 操作 | 代码 |
|---|---|---|
| 1 | `unicodedata.normalize("NFKC")` | `:57` |
| 2 | `to_halfwidth()`：`U+3000`→空格；`U+FF01..FF5E`→减 `0xFEE0` | `:39-50` |
| 3 | 破折号统一：`— – − ‐ ‑ ‒` → `-` | `:36` (`_DASHES`) |
| 4 | 符号别名替换成 ASCII 词（**带前后空格的词**，保证分词边界） | `:14-23` |
| 5 | 单位/记号正则归一（μm→um、mm、`Ra 3.2`→`ra 3.2`、`IT7`→`it 7`） | `:26-34` |
| 6 | `lower()` | `:65` |
| 7 | 空白折叠（含 `\u00a0`） | `:66` |

符号别名表（`_SYMBOL_ALIASES`，`symbols.py:14-23`，改造时**只保留核物理会用到的**）：

```python
"⌀"→" phi ", "Ø"→" phi ", "ø"→" phi ", "Φ"→" phi ", "φ"→" phi ", "Ф"→" phi ",
"±"→" pm ", "×"→" x ", "✕"→" x ", "＊"→" * ",
"°"→" deg ", "′"/"´"→" min ", "″"/"〃"→" sec ",
"≤"→" le ", "≥"→" ge ", "≠"→" ne ", "≈"→" approx ",
"⊥"→" perp ", "∥"→" parallel ", "∠"→" angle ", "⌒"→" arc ",
"○"→" circle ", "□"→" square ", "△"→" triangle ", "→"→" to ", "←"→" from ",
"㎡"→" m2 ", "㈠"→" 1 ", "㈡"→" 2 ",
```

`normalize_keepcase()`（`:70-80`）：同前 4 步但**不小写**——因为配合代号靠大小写区分孔/轴（`H7` vs `h6`）。核物理没有这个需求，但保留它无害。

两个领域抽取器（**真领域逻辑，必须重写**）：
- `extract_fit_spec(text)`（`:83-119`）：正则 `(\d+(?:\.\d+)?)\s*([A-Za-z]{1,2}\d{1,2})(?:\s*/\s*([A-Za-z]{1,2}\d{1,2}))?`，靠 `has_phi`（是否含 ⌀ØøΦφФ）与首字母大小写判断孔/轴，返回 `{phi,hole,shaft}`。
- `extract_thread_spec(text)`（`:122-135`）：正则 `\b(M|Tr|G)\s?(\d+(?:\.\d+)?)(?:\s*[x×*]\s*(\d+(?:\.\d+)?))?`，返回 `"M10"` / `"M10×1.5"` / `"Tr24×5"` / `"G1/2"`。

> 核物理的对应物是"公式/符号抽取"：`k_eff`、`K∞`、`M²`、`Σa`、`Φ`（注意：`Φ` 在核物理里是中子注量率，不是直径！）、`ρ`、`β_eff`、`pcm`、`$`、`MWd/tU`、`EFPD`。**`Φ→phi` 这条别名必须删或改**，否则 `Φ=1e13 n/cm²·s` 会被归一成 `phi` 而丢掉单位语义。

### 4.2 分词（`rag/tokenize.py` 195 行）

| 模块 | 内容 | 行号 |
|---|---|---|
| 主分词 | `jieba.lcut_for_search(joined)`，只保留以 CJK 开头的词元 | `:134-141` |
| ASCII 词元 | 正则 `[a-z]+[0-9]*\|[0-9]+[a-z]*\|[0-9]+(?:\.[0-9]+)?` 单独抽出（保证 `h7`/`ra`/`m10`/`3.2` 不被 jieba 吃掉） | `:14`、`:127` |
| 降级 | 未装 jieba → 单字 + 相邻二元组（会产生"图的""的投"噪声，注释明说生产要装 jieba） | `:143-147` |
| 领域词典 | `_load_domain_dict()` 从 ①`kp.jsonl` 的 `term`/`aliases` ②`figures.jsonl` 的 `structure_tags` ③`kb/**/*.md` 的 `## 标题`（去编号、按 `、，,与和及/` 再切）④ `_CURATED_TERMS`（手写 60 词） | `:40-110` |
| 注入 jieba | `jieba.add_word(w, freq=20000)` | `:113-118` |
| 实义词判定 | `is_content_token()`：不在 `_GENERIC_WORDS`（"意思/区别/如何/为什么…" 40 词）、且至少含一个非虚词字符（`_FUNC_CHARS` 约 70 字） | `:158-178` |
| 门控用词 | `content_tokens(text, min_len=2)`：去重 + 过实义词 + 长度 ≥2 | `:181-195` |

> 为什么 min_len=2：注释举了反例——「打」「印」「油」单字几乎在任何语料里都能撞上，会把"3D打印""润滑油"这类超纲问题的覆盖率抬到门限以上（`:183-187`）。
>
> 改造要点：`_CURATED_TERMS`（`tokenize.py:26-37`）与 `_GENERIC_WORDS`（`:164-169`）是**两个必须整体替换的领域词表**；`_load_domain_dict()` **不用改**（它从 kb 自身抽词），只要新 `kp.jsonl` 有 `term/aliases`、`figures.jsonl` 有 `structure_tags` 就能自动长出核物理词典。

### 4.3 切分器（`rag/chunking.py` 231 行）

`chunk_id` 规范：`chk_<doc_id>_<父块4位>_<子块4位>`（`chunking.py:40-41`，实例 `chk_KP_0003_0000`）。

四套切分器与"哪些文件进索引"：

| 切分器 | 输入 | 规则 | 产出 role | 行号 |
|---|---|---|---|---|
| `chunk_markdown` | `kb/**/*.md`（排除 README.md） | `#`=H1 与 `##`=新父块（`parent_idx += 1`）；`###`→段落内加粗小标题；同父块内段落用 `_merge_paragraphs` 合并到 60–350 字 | front matter 的 `role`（默认 authority） | `:71-127` |
| `chunk_knowledge` | `kb/knowledge/kp.jsonl` | 一章=父块、一条知识点=子块；正文模板 `**term**：definition` + `· points[]` + `⚠ 易错：common_mistakes[]`；`doc_id="KP"`、`document_title="机械制图知识点手册（自建）"` | authority | `:130-168` |
| `chunk_exercises` | `kb/exercises/*.jsonl`（跳过 `answer`） | 一题一块；`doc_id="EX"`、role=exercise、`internal_only=True` | exercise | `:171-199` |
| （StandardSplitter） | — | **未单独实现**：标准文档靠 Markdown 的 `### 5.1` 在 `chunk_markdown` 里表达（文件头注释 `:7`） | standard（来自 front matter） | — |

`_merge_paragraphs`（`:44-68`）细节（决定 chunk 粒度）：
- 逐段累积，若 `len(buf)+len(p)+1 <= 350` 就并入，否则 flush；
- 单段超长时按 `。`/`；` 在 350 字内找切点，切点 < 60 则硬切 350；
- 最后丢掉 `< MIN_CHUNK_CHARS//2`（30 字）的碎片。

`parse_front_matter`（`:23-37`）：手写 YAML 子集，只认 `key: value`，`true/false` 转 bool，去引号，**不支持嵌套/数组**。

`load_kb` 的装载顺序（`:202-231`）：`kb/**/*.md`（sorted）→ `kb/knowledge/kp.jsonl` → `kb/exercises/*.jsonl`。

> 改造要点：切分器**逻辑不用改**，但 ①`chunk_knowledge` 的正文模板要换成核物理知识点结构（若 SPEC 的 `kp.jsonl` 字段同为 `term/definition/points/common_mistakes` 则零改动）；②`document_title="机械制图知识点手册（自建）"` 这类**硬编码中文串要换**（`:158`、`:189`）；③教材 PDF/PPTX 抽出的 Markdown 必须带 front matter（见 §5.9）。

### 4.4 索引构建（`rag/index.py` 178 行）

**两通道，不用向量库**（`index.py:1-7` 的设计取舍注释：语料 1e3 量级，BM25 内存倒排 0.3s，hashing TF-IDF + numpy 全量点积 <10ms）。

**通道 A：BM25**（内存倒排，启动时从 chunk 文本重建）

| 项 | 实现 | 行号 |
|---|---|---|
| 倒排 | `self.tfs: list[Counter]`、`self.lens: list[int]`、`self.df: Counter` | `:48-57` |
| 平均长度 | `avgdl = sum(lens)/n` | `:58` |
| IDF | `log(1 + (N - df + 0.5)/(df + 0.5))` | `:59-61` |
| 打分 | `Σ_t idf(t) · f·(k1+1) / (f + k1·(1-b+b·dl/avgdl))`，`k1=1.5`、`b=0.75` | `:108-123` |
| 索引文本 | `index_text(c) = section + "\n" + text`（**章节标题进索引**，注释说明"只索引正文会让'剖视图的概念是什么'这类提问命中率明显偏低"） | `:30-36` |

**通道 B：hashing TF-IDF 稠密**

| 项 | 实现 | 行号 |
|---|---|---|
| 维度 | `HASH_DIM = 4096`（`config.py:37`） | — |
| 桶+符号 | `h = crc32(tok)`；`bucket = h % dim`；`sign = +1 if (h>>20)&1 else -1`（**signed hashing**，降低碰撞偏置） | `:23-27` |
| 桶级 idf | `bucket_df[b]` 统计"包含该桶的块数"；`idf = log((n+1)/(df+1)) + 1` | `:65-74`、`:86-95` |
| 块向量 | `mat[i,b] += sign * (1+log(tf)) * idf[b]`，再逐行 L2 归一 | `:97-104` |
| 查询向量 | 同公式，L2 归一 | `:125-132` |
| 相似度 | `self.vecs @ q_vec`（线性核） | `:134-137` |
| 持久化 | `chunks.jsonl`（每行 `Chunk.model_dump_json()`）+ `vecs.npy`（np.save）+ `meta.json{n,dim,avgdl,vocab}` | `:141-175` |

> 注释里留了接口位：`index.py:6` "预留 Embedder 接口，接入真实 embedding 模型时只需替换 dense 通道"。改造时若想上真 embedding，只需替换 `_encode_chunks`/`encode_query`，其余不动。

### 4.5 混合检索 + 双门控（`rag/retrieve.py` 203 行）——精确算法

#### 融合打分（`retrieve.py:120-124`）

```python
bm25  = idx.bm25_scores(q)          # 长度 N 向量
dense = idx.dense_scores(q)         # 长度 N 向量
fused = λ * minmax(bm25) + (1-λ) * minmax(dense) + phrase_boost(q)
```

- `_minmax(x)`：`(x-min)/(max-min)`；`max-min < 1e-9` 时返回全零（`:27-33`）
- `λ = SPARSE_WEIGHT`，默认 **0.45**（`config.py:26`；参考作品λ=0.35，制图符号密集所以调高）
- `phrase_boost`（`:93-105`）：对 query 的每个 `content_tokens` 且 `len>=2` 的词 t，

```python
w = 0.06 * min(len(t), 4) * (0.5 + idf.get(t, max_idf) / (max_idf * 2))
# 若 t 原样出现在块文本里，该块 += w
```

#### 召回与过滤（`:126-143`）

```python
order = argsort(-fused)                       # 全量排序
excluded = set(exclude_roles or (() if roles else ("exercise","answer")))  # 默认排除习题/答案
for i in order:
    if not allow_internal and chunks[i].internal_only: continue
    if roles and chunks[i].role.value not in roles:   continue
    if excluded and chunks[i].role.value in excluded: continue
    allow.append(i)
    if len(allow) >= max(recall_k, top_k): break
recall = allow[:recall_k]                     # recall_k 默认 24
```

#### 门控一：IDF 加权关键词覆盖率（`keyword_coverage`，`retrieve.py:36-72`）

```python
toks = content_tokens(query)                 # 去重、去虚词、len>=2
if not toks: return 1.0                      # 纯虚词提问不门控
present = corpus_vocab if COVERAGE_MODE=="corpus" else union(set(tfs[i]) for i in recall)
oov_w = max_idf * OOV_WEIGHT                 # 语料外实义词权重倍数，默认 1.2
total = Σ w_t   where w_t = idf.get(t, oov_w)     # 生僻词权重高、OOV 权重最高
covered = Σ w_t for t in toks if t in present
coverage = covered / total
```

两种口径（`config.py:29` `MW_COVERAGE_MODE`）：
- `docs`（默认）：分母/命中都看**召回的这 24 块并集**——精度高，但召回集只占语料一小部分；
- `corpus`：看**全库词表**——稳定，但语料越大越容易命中，门控会变松（注释 `retrieve.py:49-52`）。

#### 门控二：单块覆盖率（`retrieve.py:150-166`）

```python
q_toks = content_tokens(query)
oov_w = max_idf * OOV_WEIGHT
total_w = Σ idf.get(t, oov_w) for t in q_toks  or 1.0
best_chunk_cov = 0.0
for i in allow[:10]:                          # 只看前 10 个块
    got = Σ idf.get(t, oov_w) for t in q_toks if t in tfs[i]
    best_chunk_cov = max(best_chunk_cov, got / total_w)
```

注释解释了为什么需要第二道（`:150-153`）：关键词覆盖率只回答"语料里有没有这些词"，语料一大就容易全命中；单块覆盖率回答"**是不是有一段就是在讲这个**"。并记录了一次失败尝试："试过只取最稀有的 K 个词，反而更差：同义改写会让稀有词变成 OOV 而误判成超纲"（`config.py:31` 的 `GATE_RARE_K` 因此成为"保留配置项，当前实现未使用"）。

#### 判定与产出（`:164-195`）

```python
gated = apply_gate and (coverage < gate_tau or best_chunk_cov < gate_tau_chunk)
# 返回：hits[Evidence], coverage, chunk_coverage, gated, tau, tau_chunk, recall
# Evidence.score = round(min(fused[i], 1.0), 4)     # 注意：phrase_boost 会让融合分 >1，这里夹到 1.0
# Evidence.snippet = text[:220]
```

#### 参数全表（`config.py`，全部可 env 覆盖）

| 常量 | env | 默认 | 含义 / 调参依据 |
|---|---|---|---|
| `SPARSE_WEIGHT` | `MW_SPARSE_WEIGHT` | 0.45 | λ：BM25 通道权重 |
| `GATE_TAU` | `MW_GATE_TAU` | 0.55 | 覆盖率门控 τ（注释：32 题探针标定 τ=0.45 时 acc 0.969） |
| `OOV_WEIGHT` | `MW_OOV_WEIGHT` | 1.2 | 语料外实义词的权重倍数 |
| `COVERAGE_MODE` | `MW_COVERAGE_MODE` | `docs` | `docs` / `corpus` |
| `GATE_TAU_CHUNK` | `MW_GATE_TAU_CHUNK` | 0.45 | 单块覆盖率门限 |
| `GATE_RARE_K` | `MW_GATE_RARE_K` | 2 | **保留未用** |
| `RECALL_K` | `MW_RECALL_K` | 24 | 单通道召回数 |
| `TOP_K` | `MW_TOP_K` | 6 | 送 LLM 的证据数 |
| `MAX_EVIDENCE_CHARS` | —（硬编码） | 1400 | 证据拼接上限 |
| `HASH_DIM` | —（硬编码） | 4096 | hashing 维度 |
| `MAX_CHUNK_CHARS` | —（硬编码） | 350 | 子块目标字数 |
| `MIN_CHUNK_CHARS` | —（硬编码） | 60 | 子块最小字数 |

> 标定结果（README:17）：held-out 38 题 = 课内 29/30、课外 8/8、acc 0.974；标定集 54 题为 1.000（README 自己标注"属拟合，不作泛化性能"）。**新工程必须用核物理自建探针重新标 λ/τ，不能沿用 0.45/0.55/0.45 当作已经验证过的值。**

---

## 5. `kb/` 逐文件 schema + 真实样例

目录树（实测条目数）：

```
kb/
├── _manifest_web.json            425 行（数组，22 项）
├── knowledge/kp.jsonl            197 行  # 知识点
├── graph/
│   ├── nodes.jsonl               169 行
│   ├── edges.jsonl               279 行
│   ├── questions.jsonl            26 行
│   └── question_edges.jsonl       27 行
├── figures/
│   ├── figures.jsonl              34 行
│   ├── pairs.jsonl                10 行
│   ├── FIG-*.svg                  24 个（figures.jsonl 里 file 字段指向）
│   └── pairs/PAIR-*.svg           10 个
├── exercises/exercises.jsonl     196 行
├── standards/STD-*.md             4 个
└── web/WEB-*.md + DEPTH-*.md     22 个
```

### 5.1 `kb/knowledge/kp.jsonl`（197 条）

| 字段 | 类型 | 说明 |
|---|---|---|
| `kp_id` | str | `KP-<CODE>-<三位>` |
| `chapter` | str | 完整章名（"第一章 制图的基本知识和基本技能"） |
| `section` | str | 小节（"1.1 图纸幅面与格式"） |
| `term` | str | 知识点名（**会被 jieba 词典与图谱节点引用**） |
| `aliases` | str[] | 别名/学生说法（也进 jieba 词典） |
| `definition` | str | 定义 |
| `points` | str[] | 3~5 条要点 |
| `common_mistakes` | str[] | 常见错误（渲染成 `⚠ 易错：`） |
| `refs` | str[] | 依据（国标号/教材章节） |
| `bloom` | str | 记忆/理解/… |
| `level` | int | 1~4 |

真实样例（第 1 条，截断）：
```json
{"kp_id":"KP-BASIC-001","chapter":"第一章 制图的基本知识和基本技能","section":"1.1 图纸幅面与格式",
 "term":"图纸幅面","aliases":["幅面","A3图纸","基本幅面"],
 "definition":"图纸幅面是国标规定的图纸尺寸系列。基本幅面共五种，按长边对折的关系递减：A0 为 841 mm×1189 mm，…",
 "points":["A0 841×1189、A1 594×841、…（mm）","相邻两号幅面为沿长边对折关系，号数越大纸越小","优先用基本幅面；…"],
 "common_mistakes":["把 A3 与 A2 的尺寸记混…","以为幅面可以随意加长…"],
 "refs":["GB/T 14689-2008 技术制图 图纸幅面和格式"],"bloom":"记忆","level":1}
```

消费者：`chunk_knowledge`（进索引）、`tokenize._load_domain_dict`（进 jieba 词典）、`main.py:_kp_index`（`/api/graph` 给节点补 `desc/points/refs/commonMistakes/bloom/section`，`main.py:258-278`）。

### 5.2 `kb/graph/nodes.jsonl`（169 条）

```json
{"id":"KN-001","kp_id":"KP-PROJ-004","label":"三视图形成","tier":"core","chapter":"第三章 点、直线和平面的投影","state":"未学"}
```
`tier ∈ {core, trackA, trackB, branch, concept}`；`state` 固定 `"未学"`（前端用于学习状态着色）。

### 5.3 `kb/graph/edges.jsonl`（279 条）

```json
{"source":"KN-013","target":"KN-014","rel":"prereq","note":"先懂投影法分类，才能理解正投影的度量性"}
```
`rel ∈ {prereq(前置), contrast(易混淆), compose(包含), cause(导致)}`。统计口径见 `main.py:422-427`（`chains` = prereq 数）。
语义方向：`prereq` 是 `source → target`（source 是 target 的前置）；`compose` 的 source 是整体、target 是部分（`main.py:370-374` 由此推 `parent`）。

### 5.4 `kb/graph/questions.jsonl`（26 条）

```json
{"qid":"Q-001","layer":1,"question":"GB/T 14689 规定的 A0～A4 五种基本幅面之间是什么关系？A3 图纸的尺寸是多少（宽×长）？",
 "bloom":"记忆","kp_ids":["KP-BASIC-001"],"hint":"从 A0 起沿长边对折得到下一号；A3 为 297 mm×420 mm。"}
```
`layer ∈ {1,2,3}` = 三层认知递进，层名硬编码在 `main.py:216-220`：`基础理解 / 识图分析 / 综合绘图`（**必须重写**）。

### 5.5 `kb/graph/question_edges.jsonl`（27 条）

```json
{"source":"Q-001","target":"Q-025","relation":"prereq","why":"先知道 A3 的幅面尺寸与图框留边，才能按图幅设置布局并出图"}
```
`relation` 自由字符串（实测 `prereq`、`contrast`）；`why` 是可读理由。由 `main.py:281-302` 读入，`/api/graph` 的 `question_edges` 字段下发。

### 5.6 `kb/figures/figures.jsonl`（34 条）

```json
{"figure_id":"FIG-LINETYPE","file":"FIG-LINETYPE.svg","title":"图线线型对照表（六种图线）",
 "chapter":"第一章 制图的基本知识和基本技能","kp_ids":["KP-BASIC-005","KP-BASIC-006","KP-BASIC-007"],
 "structure_tags":["图线","线型","线宽","波浪线"],
 "caption":"同一张图上并列六种图线的线型样本与线宽关系：粗实线取 d、细线取 d/2，…",
 "license":"自绘","source":"依据 GB/T 17450、GB/T 4457.4 自绘"}
```
- `file` 相对 `kb/figures/`；前端通过 `GET /api/figures` 拿到列表，图片走 `/figures/<file>` 静态挂载（`main.py:701-704`）。
- `kp_ids` / `chapter` 是证据卡自动配图的匹配键（`state.figures_for`，`state.py:127-139`：先按 kp_ids 交集，再按 chapter 前 6 字匹配，`limit=2`）。`structure_tags` 进 jieba 词典。
- 34 条记录对应 **34 个 SVG**（15 个 `FIG-*` 第一批 + 19 个 `FIG2-*` 第二批，一一对应）。

### 5.7 `kb/figures/pairs.jsonl`（10 组辨析对）

```json
{"pair_id":"PAIR-POU-BAN-JUBU","file":"pairs/PAIR-POU-BAN-JUBU.svg","title":"半剖视图 vs 局部剖视图",
 "module":"projection","chapter":"第七章 机件的常用表达方法","kp_ids":["KP-EXPR-010","KP-EXPR-011"],
 "a":{"label":"A","caption":"半剖视图","正确性":"正确"},
 "b":{"label":"B","caption":"局部剖视图","正确性":"正确"},
 "differences":[{"no":1,"name":"分界线","a_desc":"以细点画线（对称中心线）为界",
                 "b_desc":"以细实线波浪线为界，波浪线手画、不规则",
                 "why":"半剖的分界线必须是对称中心线；局部剖的分界线是断裂边界，只能用波浪线"}, …],
 "question":{"stem":"下面两张图分别是什么剖视？判断依据是什么？",
             "options":["A 半剖、B 局部剖","A 局部剖、B 半剖","两张都是半剖","两张都是局部剖"],
             "answer_index":0,"explain":"看分界线：…"},
 "license":"自绘","source":"依据 GB/T 4458.6 自绘"}
```
`正确性` 是中文键（`"正确" / "错误" / "对比项"`）——**非 ASCII 字段名，前端 `types.ts:466-470` 也是 `正确性?: string`**，改契约时注意别把它当 typo 改掉。`comparison_pick` 用 `title`/`structure_tags`/`differences[].name` 做关键词打分挑对（`tools/comparison_pick.py:24-36`），得分规则：title 片段命中 +2、structure_tag 命中 +2、difference.name 命中 +3，取最高分，全 0 则取第 1 组。

### 5.8 `kb/exercises/exercises.jsonl`（196 条）

```json
{"exercise_id":"p03.1","chapter":"第一章 制图的基本知识和基本技能",
 "stem":"D3. 1. 在 指 定 位 置 处 , 熊 样 虫 出 并 补 全 各 种 图 线 和 图 形 。 一 一 一 一 一 一 1 1 一",
 "book_page":"3","qno":"1","answer_page":"2","model_page":"",
 "source":"《机械制图习题集》第6版（高教社，内部教研用）","internal_only":true}
```
- `stem` 来自扫描件 OCR，**带噪声**（上例就是坏样本）；`quality()` 用"中文占比 ≥0.30 且长度 ≥8"过滤（`pipeline/build_exercises.py:37-57`）。
- `answer_page` / `model_page` 用于"溯源回原书"；`internal_only` 一律 true（版权）。
- 检索侧被 `role=exercise` + 默认 `exclude_roles` 挡在知识问答之外，只有 `quiz_from_kb` 用 `roles=["exercise"]` 才碰。

### 5.9 `kb/standards/*.md`（4 个：GB/T 17451、4457.4、4458.4、4458.6）

front matter 字段（`parse_front_matter` 只支持标量）：

```yaml
---
doc_id: STD-GBT17451
title: 视图与三视图投影规律（GB/T 17451 / GB/T 4458.1 整理）
category: 国家标准
role: standard
source: GB/T 17451-1998《技术制图 图样画法 视图》、GB/T 4458.1-2002《机械制图 视图》，自建整理
license: 标准事实性内容整理（非原文复制），引用须注明标准号
version: "1998"
internal_only: false
---
```
正文：`## 一、…` 分节 + Markdown 表格，**只做事实性整理不复制原文**（文件内自述）。`role=standard` 使检索可用它作权威证据；`kb_no`/`clause` 字段在 Chunk 模型里存在（`models.py:51-52`），但 Markdown 切分器**不会自动填**它们（只有 jsonl/结构化输入才填）——如需"条款号溯源"，得在 front matter 加字段并在 `chunk_markdown` 里传下去。

### 5.10 `kb/web/*.md`（22 个）+ `kb/_manifest_web.json`（425 行）

web 文档 front matter 比 standards **多两个字段**（`retrieved`）：

```yaml
---
doc_id: WEB-STD-CHICUN
title: 尺寸标注的基本规则（依据 GB/T 4458.4—2003）
category: 参考资料
role: standard
source: https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=08588A5F3FE19F16B9EE8D5D87E064D5
license: 国家标准公开信息摘编（仅摘编标准号、名称、适用范围与术语，不复制正文）
retrieved: 2026-11-07
internal_only: false
---
```
正文为 3~4 节、每节 2~3 段的自写整理文（不是摘抄），约 3.5–5 KB/篇。

`_manifest_web.json` 是**数组**，每项：`{doc_id,title,category,role,source,license,retrieved,word_count,topics[]}`：

```json
[{"doc_id":"WEB-CUR-TOULIANG","title":"投影理论三章：点线面投影、截交线与相贯线的教学要点",
  "category":"参考资料","role":"curriculum",
  "source":"https://jxx.dgut.edu.cn/__local/8/81/CF/8199CDD105DD8F16882A9E575E0_FD316781_340DD.pdf",
  "license":"高校官网公开教学文件摘编（东莞理工学院《工程制图》课程教学大纲；非开放许可，仅内部教研使用）",
  "retrieved":"2026-11-07","word_count":1295,"topics":["点的投影","直线的投影","平面的投影","截交线","相贯线"]}, …]
```
> 注意：`_manifest_web.json` **不参与检索/装载**（没有任何 Python 代码读它），它只是"资料来源台账"。`role` 的取值集合是 `DocRole` 枚举（`authority/standard/curriculum/lecture/procedure/exercise/answer/figure`，`models.py:16-25`），写错会在 `chunk_markdown` 里回落成 `authority`（`chunking.py:75-78`）。

---

## 8. 持久化、配置与环境变量、LLM 接入与降级

### 8.1 SQLite schema（`app/db.py:16-60`，5 张表）

```sql
CREATE TABLE users (
  account TEXT PRIMARY KEY, pwd_hash TEXT NOT NULL,
  created_at REAL NOT NULL, records TEXT NOT NULL DEFAULT '{}');
CREATE TABLE conversations (
  id TEXT PRIMARY KEY, account TEXT NOT NULL,
  module_key TEXT NOT NULL DEFAULT '__global__', title TEXT NOT NULL DEFAULT '',
  updated_at REAL NOT NULL);
CREATE TABLE messages (
  id TEXT PRIMARY KEY, conv_id TEXT NOT NULL, role TEXT NOT NULL,
  content TEXT NOT NULL, payload TEXT NOT NULL DEFAULT '{}', created_at REAL NOT NULL);
CREATE TABLE wrongbook (
  id TEXT PRIMARY KEY, account TEXT NOT NULL,
  question TEXT NOT NULL, wrong_answer TEXT DEFAULT '', root_cause TEXT DEFAULT '',
  trace_ref TEXT DEFAULT '', correct TEXT DEFAULT '', pitfall TEXT DEFAULT '',
  kp_ids TEXT DEFAULT '[]', source TEXT DEFAULT '', created_at REAL NOT NULL);
CREATE TABLE events (
  id INTEGER PRIMARY KEY AUTOINCREMENT, account TEXT NOT NULL,
  kind TEXT NOT NULL, payload TEXT NOT NULL DEFAULT '{}', created_at REAL NOT NULL);
CREATE INDEX idx_msg_conv ON messages(conv_id, created_at);
CREATE INDEX idx_ev_account ON events(account, created_at);
```

- 全时间戳用 `REAL` Unix 秒；数组字段（`kp_ids`、`records`、`payload`）存 JSON 字符串。
- 密码：`sha256("machdraw" + pwd)`（`db.py:63-66`）——**固定盐、无迭代**，仅"够用不裸奔"，改造时若要对外必须换。
- 账号语义：`login_or_register` 首次输入自动建号（`db.py:79-96`），密码错抛 `PermissionError` → `main.py:182-183` 转 401。
- `get_or_create_conversation`（`db.py:120-132`）：**同一账号+同一模块在 24h 内复用同一会话**（避免每问一句新建）。
- 学情埋点 `log_event(account, kind, payload)`（`:196-201`）的 kind 实测：`feynman`、`wrongbook_diagnose`、`kb_search`、`answer`、`wrongbook_add`、`wrongbook_manual`。
- 教师端聚合 `admin_overview()`（`:210-277`）口径固定：**拒答率/覆盖率都只统计 `kind='kb_search'` 的事件**，保证分母一致（注释 `:233-236` 记录了"混入 answer 事件导致拒答率 100%+覆盖率 0% 自相矛盾"的旧 bug）。

### 8.2 配置全量矩阵（`app/config.py` 53 行，全部实测）

`ROOT` 推导：`Path(__file__).resolve().parents[3]`（`config.py:7`，`app/config.py` → app→api→apps→root）。
`KB_DIR=ROOT/kb`、`DATA_DIR=ROOT/data`、`INDEX_DIR=DATA_DIR/index`、`EVAL_DIR=ROOT/eval`、`DB_PATH=DATA_DIR/app.db`。

`.env` 加载（`:16-23`）：依次尝试 `ROOT/.env` 与 `ROOT/apps/api/.env`，`load_dotenv(override=False)` → **真实环境变量优先**；没装 `python-dotenv` 也不报错。

| 变量 | 默认 | 作用 | 代码位置 |
|---|---|---|---|
| `MW_SPARSE_WEIGHT` | 0.45 | BM25 权重 λ | `:26` |
| `MW_GATE_TAU` | 0.55 | 覆盖率门控 τ | `:27` |
| `MW_OOV_WEIGHT` | 1.2 | OOV 实义词权重倍数 | `:28` |
| `MW_COVERAGE_MODE` | docs | 覆盖率口径 | `:29` |
| `MW_GATE_TAU_CHUNK` | 0.45 | 单块覆盖率门限 | `:30` |
| `MW_GATE_RARE_K` | 2 | 保留未用 | `:31` |
| `MW_RECALL_K` | 24 | 单通道召回数 | `:32` |
| `MW_TOP_K` | 6 | 证据条数 | `:33` |
| `MW_LLM_PROVIDER` | mock | `mock`/`deepseek`/`openai-compatible` | `:42` |
| `MW_LLM_MODEL` | deepseek-chat | 模型名 | `:43` |
| `MW_LLM_BASE_URL` | https://api.deepseek.com/v1 | OpenAI 兼容端点 | `:44` |
| `MW_LLM_API_KEY` | `""` 或回落 `DEEPSEEK_API_KEY` | key | `:45` |
| `MW_LLM_EXTRA_BODY` | `""` | 追加请求体 JSON（关思维链） | `:49` |
| `MW_INTERNAL_ONLY` | `1`（"1" 才允许） | 是否允许版权受限内容入库 | `:53` |

非 env 的硬编码常量：`MAX_EVIDENCE_CHARS=1400`（`:34`）、`HASH_DIM=4096`（`:37`）、`MAX_CHUNK_CHARS=350`（`:38`）、`MIN_CHUNK_CHARS=60`（`:39`）。

**实际仓库里的 `.env`（`apps/api/.env`）**：指向讯飞星辰 MaaS，`provider=openai-compatible`、`base_url=https://maas-api.cn-huabei-1.xf-yun.com/v2`、`model=spark-x2.6-4b`、`MW_LLM_EXTRA_BODY={"thinking":{"type":"disabled"}}`（注释记录实测：关思维链后 115s→5.7s、推理 token 3405→0）。**注意该文件里有一个真实 `ak-` key，改造时不要把它搬进新工程仓库。**

### 8.3 LLM 接入（`app/llm.py` 228 行）

三种模式（`llm.py:1-9`）：

| provider | 触发条件 | 行为 |
|---|---|---|
| `mock` | `MW_LLM_PROVIDER=mock` | 本地**抽取式作答**：从证据句子里挑与 query 词元重叠最高的 4 句，按"结论/依据/出处"模板组织。不编造、不改写事实（`mock_answer`，`:81-147`） |
| `deepseek` / `openai-compatible` | 有 key | `urllib.request` 直连 `{BASE_URL}/chat/completions`，`stream=False`、`temperature=0.2`、超时 90s（`_http_chat`，`:165-185`） |
| `mock-fallback` | 真实调用抛 `URLError/KeyError/TimeoutError/OSError` | 返回抽取式答案 + 尾部追加 `> ⚠ 模型调用失败（XxxError），已自动降级为本地证据抽取模式。`（`:221-228`） |

system prompt（**提示词级耦合，必须重写**，`llm.py:188-193`）：
```
你是机械制图课程的助教。只能依据下面提供的【课程证据】作答，
不得使用课程以外的知识，不得编造国标号、数值或页码。
回答后用“出处：”列出所用证据的文档名与章节。
如果证据不足以回答，直接说明“知识库未收录”，不要猜。
```
`persona`（模块人格）只在真实模型路径拼进 system（`:213`），mock 路径忽略。

mock 抽取算法（`_pick_sentences`，`:59-78`）：
- 切句 `_sentences()`：按 `。；！？\n` 切，过滤 <10 字、表格行（`count("|")>=2`）与分隔线（`set(s) <= set("|-: ")`）——注释说"表格行单独拿出来当结论很难读"（`:45-46`）；
- 打分：`overlap = |q ∩ s| / sqrt(|q|)`，再乘证据权重 `ew = 0.5 + score`；
- 取 top 4 后**按 (证据序, 句序) 还原顺序**（`:76-77`），避免答案里句子乱序。

门控拒答的三条模板（`mock_answer`）：
1. 无 hits → "**知识库未收录**\n\n本课程知识库里没有检索到与「q」相关的内容…可以换个说法再问，或换一个课程内的关键词（例如：三视图、剖视图、尺寸标注、表面结构、极限与配合、螺纹画法）。"（**例子列表是领域耦合**，`:84-89`）
2. gated → 输出覆盖率与门限："关键词覆盖率 X%，低于 0.55 的门限"（`:91-98`）
3. 覆盖率 <0.75 → 尾部追加"这个话题在课程资料里覆盖得不算充分"（`:141-146`）

`/api/health` 的降级可见性（`main.py:70-75`）：`has_key = bool(LLM_API_KEY)`、`llm_ready = (provider!="mock" and has_key)`；注释记录了旧 bug"只看 provider 不看 key，导致显示有 key 实际回落 mock 且不打降级提示"。前端 `TopBar.tsx:42` 用 `health.provider==="mock"` 显示"本地抽取式"。

### 8.4 三条"降级不中断"设计（复刻必须保留）

1. **LLM 失败 → 抽取式**（`llm.py:221-228`），并在答案里明示降级；
2. **工具异常 → `ok=False` 的 ToolOutcome**（`tools/__init__.py:176-179`），编排器照常发 `tool_result`，不中断事件流；
3. **任意异常 → `error` 帧 + `[DONE]`**（`main.py:645-647`），前端把 `msg.error` 渲染成红条而不是白屏。

另有 4 处"防御式 `.get()`"（注释里点名过真实故障）：`llm.py:123-139`（出处字段硬索引导致降级路径 KeyError 打成 500）、`llm.py:207-211`（证据上下文）、`orchestrator.py:454-455`（持久化失败不影响回答）、`store.ts:135-145`（没人认领的 artifact 丢掉并提示）。

### 8.5 `data/` 目录（可重建，不进版本库）

| 路径 | 生成者 | 内容 |
|---|---|---|
| `data/index/chunks.jsonl` | `Index.save()` | 全部 Chunk（pydantic JSON，一行一块） |
| `data/index/vecs.npy` | 同上 | `(N, 4096) float32` 归一化向量 |
| `data/index/meta.json` | 同上 | `{n,dim,avgdl,vocab}` |
| `data/app.db` | `Store()` 首次连接 | SQLite（5 表） |
| `data/models/{M-*.svg, preview.html}` | `pipeline/export_models.py` | 三视图离线预览（仅人工检查用，不被服务读取） |

`.gitignore` / `.dockerignore` 已排除 `data/`（部署时容器内重建索引、挂卷持久化 `app.db`）。
