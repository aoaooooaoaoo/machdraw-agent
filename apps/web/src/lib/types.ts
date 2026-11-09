/**
 * 前端契约类型。
 * 单一事实源在 apps/api/app/contracts/models.py；本文件是它的 TypeScript 镜像，
 * 只做展示用途的字段（at/status 等）是本文件新增的 UI 状态。
 */

export type EventType =
  | 'thinking'
  | 'token'
  | 'tool_call'
  | 'tool_result'
  | 'artifact'
  | 'error'
  | 'done';

/** SSE 一帧。同名同字段对齐 models.SSEEvent。 */
export interface SSEEvent {
  type: EventType;
  seq?: number;
  text?: string;
  id?: string;
  name?: string;
  label?: string;
  args?: Record<string, unknown>;
  summary?: string;
  detail?: string;
  artifactType?: string;
  data?: Record<string, unknown>;
  code?: string;
}

export type ToolStatus = 'running' | 'done' | 'error';

export interface ToolCallState {
  id: string;
  name: string;
  label: string;
  args: Record<string, unknown>;
  status: ToolStatus;
  summary: string;
  detail: string;
}

/** 八类画布（与 SPEC §4.1 和后端 `contracts/models.py` 的 ARTIFACT_TYPES 保持一致）。 */
export type ArtifactType =
  | 'evidence'
  | 'calc'
  | 'plot'
  | 'comparison'
  | 'annotation'
  | 'quiz'
  | 'wrongbook'
  | 'graph';

export interface ArtifactState {
  artifactType: ArtifactType;
  data: Record<string, any>;
  receivedAt: number;
}

export interface DoneMeta {
  provider?: string;
  model?: string;
  evidence?: number;
  coverage?: number;
  ms?: number;
}

export interface ChatMessage {
  id: string;
  /** system = 前端追加的系统提示（如产物类型暂无画布），不发给后端 */
  role: 'user' | 'assistant' | 'system';
  content: string;
  thinking: string;
  tools: ToolCallState[];
  artifact?: ArtifactState;
  streaming: boolean;
  error?: string;
  meta?: DoneMeta;
  /** UI 统计：本消息收到的帧数 */
  frames: number;
}

export interface ModuleManifest {
  id: string;
  name: string;
  icon: string;
  canvas_kinds: string[];
  tools: string[];
  system_prompt: string;
  entry_examples: string[];
  desc: string;
}

export interface HealthInfo {
  ok: boolean;
  model: string;
  provider: string;
  has_key: boolean;
  tools: string[];
  chunks: number;
  docs: number;
  nodes: number;
  edges: number;
  sparse_weight: number;
  gate_tau: number;
  warnings: string[];
}

export interface EvidenceItem {
  chunkId: string;
  documentId: string;
  documentTitle: string;
  category: string;
  section: string;
  score: number;
  content: string;
  snippet: string;
  kbNo?: string;
  clause?: string;
  page?: number | null;
  figureRefs?: string[];
}

export interface EvidenceArtifactData {
  query: string;
  evidences: EvidenceItem[];
  documents?: { id: string; title: string; category: string; status?: string }[];
  totalDocs?: number;
  coverage?: number;
  /** 双门控第二道信号：命中证据块对查询的覆盖比例 */
  chunkCoverage?: number;
  gated?: boolean;
  /** 与本轮检索相关的自绘教学图（后端 /figures 静态资源） */
  figures?: FigureItem[];
}

export interface FigureItem {
  figure_id: string;
  file: string;
  title: string;
  chapter?: string;
  kp_ids?: string[];
  structure_tags?: string[];
  caption?: string;
  license?: string;
  source?: string;
}

/* ---------------------------------------------------------------- 确定性计算（calc） */

/** 计算输入：量 / 取值 / 单位。 */
export interface CalcInput {
  name: string;
  value: number | string;
  unit?: string;
}

/** 计算步骤：一行公式 + 一句说明（等宽字体逐条编号渲染）。 */
export interface CalcFormula {
  step: string;
  note?: string;
}

/** 计算输出：量 / 数值 / 单位 / 说明（inputs 与 results 共用）。 */
export interface CalcResult {
  name: string;
  value: number | string;
  unit?: string;
  note?: string;
}

/** 结论条：level 决定配色（临界/次临界/超临界），note 给出物理判断。 */
export interface CalcVerdict {
  level: string;
  note?: string;
}

/**
 * `calc` 画布 data 契约（SPEC §4.1）。
 * 对应工具：critical_calc / burnup_calc / reactivity_calc（以及任何「输入→公式→结果」型计算）。
 */
export interface CalcData {
  title?: string;
  inputs?: CalcInput[];
  formulas?: CalcFormula[];
  results?: CalcResult[];
  verdict?: CalcVerdict;
  refs?: string[];
  /** 可选补充说明（假设、口径、降级提示） */
  note?: string;
  /** 后端预渲染的自包含 SVG（有就直接展示） */
  svg?: string;
}

/* ---------------------------------------------------------------- 曲线 / 分布（plot） */

export interface PlotSeries {
  name: string;
  /** [[x, y], ...]，按 x 升序；log 轴要求 x > 0 */
  points: [number, number][];
}

export interface PlotMarker {
  x: number;
  y?: number;
  label?: string;
}

/**
 * `plot` 画布 data 契约（SPEC §4.1）。
 * kind==="spectrum" 或 x 跨度 ≥100 倍时，前端自动改用 log10 横轴。
 */
export interface PlotData {
  kind?: 'curve' | 'spectrum' | 'distribution' | string;
  title?: string;
  x_label?: string;
  y_label?: string;
  series?: PlotSeries[];
  markers?: PlotMarker[];
  /** 曲线下方附带的数值表（量 / 数值 / 单位 / 说明） */
  results?: CalcResult[];
  note?: string;
  refs?: string[];
  /** 后端预渲染的自包含 SVG（有就直接展示） */
  svg?: string;
}

/** 前端功能模块的身份，随请求带给后端（参考作品契约）。
 *  后端把它拼进系统提示词，Agent 才知道"自己在哪个模块、负责什么"。 */
export interface FeatureRef {
  id: string;
  title?: string;
  persona?: string;
}

export interface ChatRequestBody {
  session_id: string;
  messages: { role: 'user' | 'assistant' | 'system'; content: string }[];
  /** 兼容两种：旧写法传模块 id 字符串，新写法传 FeatureRef 对象 */
  feature: string | FeatureRef | null;
}

/* ---------------------------------------------------------------- 知识图谱 */

export type GraphTier = 'core' | 'trackA' | 'trackB' | 'branch' | 'concept' | string;

export interface GraphNodeInfo {
  id: string;
  kp_id?: string;
  label: string;
  tier: GraphTier;
  chapter?: string;
  state?: string;
  /** 后端新契约（已下发） */
  level?: number;
  sector?: number;
  parent?: string | null;
  track?: string;
  desc?: string;
  points?: string[];
  refs?: string[];
  commonMistakes?: string[];
  bloom?: string;
  section?: string;
}

export interface GraphEdgeInfo {
  source: string;
  target: string;
  /** 旧字段（当前后端） */
  rel?: string;
  /** 新契约字段（待后端下发） */
  relation?: string;
  note?: string;
}

export interface GraphNeighbor {
  id: string;
  rel: string;
  note?: string;
  node: GraphNodeInfo;
}

export interface GraphPrereqStep {
  id: string;
  level: number;
  node: GraphNodeInfo;
  note?: string;
}

/** kg_lookup 产出的 graph artifact。 */
export interface GraphArtifactData {
  focus: GraphNodeInfo;
  neighbors: GraphNeighbor[];
  prereq: GraphPrereqStep[];
  nodes: GraphNodeInfo[];
  edges: GraphEdgeInfo[];
  /** 整页模式使用：knowledge/question + 聚焦 id（后端后续下发） */
  mode?: 'knowledge' | 'question';
}

export interface GraphQuestion {
  qid: string;
  layer?: number;
  question: string;
  bloom?: string;
  kp_ids?: string[];
  kp_labels?: string[];
  node_ids?: string[];
  hint?: string;
  answer?: string[];
  blindSpot?: string;
  refs?: string[];
}

export interface GraphQuestionEdge {
  source: string;
  target: string;
  relation?: string;
  why?: string;
}

export interface GraphSector {
  sector: number;
  chapter: string;
  count: number;
  angle?: number;
}

export interface GraphChapter {
  chapter: string;
  node_ids: string[];
  count: number;
}

export interface GraphRelationCounts {
  prereq?: number;
  contrast?: number;
  compose?: number;
  cause?: number;
  [key: string]: number | undefined;
}

export interface GraphStats {
  nodes: number;
  edges: number;
  questions: number;
  chains?: number;
  chapters?: number;
  relations?: GraphRelationCounts;
}

export interface GraphQuestionLayer {
  layer: number;
  name: string;
  desc: string;
  count: number;
  qids?: string[];
  blooms?: Record<string, number>;
}

export interface GraphFull {
  nodes: GraphNodeInfo[];
  edges: GraphEdgeInfo[];
  questions: GraphQuestion[];
  chapters?: GraphChapter[];
  stats?: GraphStats;
  question_layers?: GraphQuestionLayer[];
  /** 新契约（已下发） */
  question_edges?: GraphQuestionEdge[];
  sectors?: GraphSector[];
}

export interface GraphNodeDetail {
  node: GraphNodeInfo;
  neighbors: GraphNeighbor[];
  prereq: GraphPrereqStep[];
}

/* ---------------------------------------------------------------- 三色标注 */

export interface AnnotationItem {
  text: string;
  label: string;
  color: 'green' | 'amber' | 'red' | string;
  comment?: string;
}

export interface AnnotationArtifactData {
  round: number;
  final: boolean;
  sentence_count: number;
  coverage?: number;
  annotations: AnnotationItem[];
  probes: string[];
  summary?: string;
  score?: { correct: number; total: number; level?: string };
}

/* ---------------------------------------------------------------- 错题诊改 */

export interface WrongbookTrace {
  ref: string;
  chunk_id: string;
  score: number;
  text: string;
}

export interface WrongbookStep {
  n: number;
  key: string;
  value: string;
}

export interface WrongbookArtifactData {
  question: string;
  wrong_answer?: string;
  root_cause?: string;
  root_causes_all?: string[];
  steps: WrongbookStep[];
  trace?: WrongbookTrace[];
  pitfalls?: string[];
  kp_ids?: string[];
  coverage?: number;
  gated?: boolean;
  note?: string;
  /** 题目来源/诊断来源（写错题本时用） */
  source?: string;
}

/* ---------------------------------------------------------------- 成对图辨析 */

export interface ComparisonSideInfo {
  label: string;
  caption: string;
  正确性?: string;
}

export interface ComparisonDifference {
  no: number;
  name: string;
  a_desc: string;
  b_desc: string;
  why?: string;
}

export interface ComparisonQuestion {
  stem: string;
  options: string[];
  answer_index: number;
  explain?: string;
}

export interface ComparisonArtifactData {
  pair_id?: string;
  file: string;
  title?: string;
  a?: ComparisonSideInfo;
  b?: ComparisonSideInfo;
  differences?: ComparisonDifference[];
  question?: ComparisonQuestion;
  kp_ids?: string[];
}

/* ---------------------------------------------------------------- 题卡 */

export interface QuizQuestion {
  chunkId: string;
  documentTitle?: string;
  section?: string;
  content: string;
}

export interface QuizArtifactData {
  questions: QuizQuestion[];
  answer_withheld?: boolean;
  /** 题面质量声明（后端下发），如"题面来自扫描件 OCR，存在错字…" */
  quality_note?: string;
}
