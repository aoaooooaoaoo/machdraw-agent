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

export interface ArtifactState {
  artifactType: string;
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

/** solve_fit() 的返回形状（apps/api/app/domain/tolerance.py，见 orchestrator.py:90-125）。 */
export interface ToleranceSide {
  code: string;
  IT: number;
  ES?: number;
  EI?: number;
  es?: number;
  ei?: number;
  max: number;
  min: number;
}

export interface ToleranceFit {
  type: string;
  max_gap: number;
  min_gap: number;
  max_interference?: number;
  note?: string;
}

export interface ToleranceArtifactData {
  basic_size: number;
  system: string;
  hole: ToleranceSide;
  shaft: ToleranceSide;
  fit: ToleranceFit;
  tolerance_zone?: { hole?: string[]; shaft?: string[] };
  process_hint?: string;
  refs?: string[];
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

/* ---------------------------------------------------------------- 作图教练 */

export type DrawOp =
  | { op: 'line'; a: [number, number]; b: [number, number] }
  | {
      op: 'arc';
      c: [number, number];
      r: number;
      start_angle?: number;
      end_angle?: number;
      start?: [number, number];
      end?: [number, number];
    }
  | { op: 'point'; p: [number, number]; label?: string }
  | { op: 'circle'; c: [number, number]; r: number; label?: string };

export interface CoachArcStep {
  n: number;
  title: string;
  detail: string;
  draw?: DrawOp[];
}

export interface CoachArtifactData {
  kind: string;
  data: Record<string, any>;
}

/* ---------------------------------------------------------------- 三视图 */

export interface ThreeViewSegment {
  view: 'front' | 'top' | 'left' | string;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  /** true = 不可见轮廓，画虚线 */
  hidden?: boolean;
  kind?: string;
}

export interface ThreeViewAux {
  kind: string;
  color: string;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  label?: string;
}

export interface ThreeViewSideStats {
  total: number;
  visible: number;
  hidden: number;
}

export interface ThreeViewModelInfo {
  model_id: string;
  name: string;
}

export interface ThreeViewLabel {
  view: string;
  text: string;
  x: number;
  y: number;
}

/** view_boxes 每项是 [x1, y1, x2, y2]（视图在图纸坐标系里的包围盒）。 */
export type ThreeViewBox = [number, number, number, number];

export interface ThreeViewArtifactData {
  model_id?: string;
  name?: string;
  unit?: string;
  size?: { L?: number; W?: number; H?: number };
  segments: ThreeViewSegment[];
  /** SVG viewBox：[x, y, w, h] */
  viewBox?: [number, number, number, number];
  labels?: ThreeViewLabel[];
  aux?: ThreeViewAux[];
  view_boxes?: Record<string, ThreeViewBox>;
  /** 三个视图的实线/虚线数量（后端统计） */
  stats?: Record<string, ThreeViewSideStats>;
  /** 投影法，如"第一角" */
  projection?: string;
  /** 模型包围盒：[[x,y,z], [x,y,z]] */
  bbox?: number[][];
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
