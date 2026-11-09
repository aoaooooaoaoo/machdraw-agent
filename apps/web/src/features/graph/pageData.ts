import type {
  GraphFull,
  GraphNodeInfo,
  GraphQuestion,
  GraphQuestionEdge,
} from '../../lib/types';

/** tier 旧字段 → 参考作品的 level(1-4)（后端补齐 level 后优先用后端）。 */
const TIER_LEVEL: Record<string, number> = {
  core: 1,
  trackA: 2,
  trackB: 2,
  branch: 3,
  concept: 4,
};

export function levelOf(node: GraphNodeInfo): number {
  if (typeof node.level === 'number') return node.level;
  return TIER_LEVEL[node.tier] ?? 4;
}

export const LEVEL_CN: Record<number, string> = {
  1: '课程核心',
  2: '知识链',
  3: '应用分支',
  4: '关键概念',
};

export function chapterIndex(full: GraphFull, chapter?: string): number {
  if (!chapter) return -1;
  return (full.chapters ?? []).findIndex((c) => c.chapter === chapter);
}

export function sectorOf(full: GraphFull, node: GraphNodeInfo): number {
  if (typeof node.sector === 'number') return node.sector;
  return chapterIndex(full, node.chapter);
}

export interface EdgeView {
  source: string;
  target: string;
  rel: string;
  note?: string;
}

export function normalizeEdges(full: GraphFull): EdgeView[] {
  return full.edges.map((e) => ({
    source: e.source,
    target: e.target,
    rel: e.rel || e.relation || 'prereq',
    note: e.note,
  }));
}

export interface NeighborEdge {
  id: string;
  label: string;
  rel: string;
  note?: string;
}

export function prerequisitesOf(full: GraphFull, id: string): NeighborEdge[] {
  return normalizeEdges(full)
    .filter((e) => e.target === id && e.rel === 'prereq')
    .map((e) => {
      const node = full.nodes.find((n) => n.id === e.source);
      return { id: e.source, label: node?.label ?? e.source, rel: e.rel, note: e.note };
    });
}

export function successorsOf(full: GraphFull, id: string): NeighborEdge[] {
  return normalizeEdges(full)
    .filter((e) => e.source === id && e.rel === 'prereq')
    .map((e) => {
      const node = full.nodes.find((n) => n.id === e.target);
      return { id: e.target, label: node?.label ?? e.target, rel: e.rel, note: e.note };
    });
}

/** 旧后端没有 parent：用 compose 边（source 包含 target）兜底出父链。 */
export function parentMap(full: GraphFull): Map<string, string> {
  const map = new Map<string, string>();
  for (const e of normalizeEdges(full)) {
    if (e.rel === 'compose') map.set(e.target, e.source);
  }
  return map;
}

export function questionsOfNode(full: GraphFull, node: GraphNodeInfo): GraphQuestion[] {
  return full.questions.filter(
    (q) =>
      (q.node_ids ?? []).includes(node.id) ||
      (node.kp_id ? (q.kp_ids ?? []).includes(node.kp_id) : false),
  );
}

/** 问题图谱的边：优先后端 question_edges；未交付时用共享知识点/章推导可用的递进边。 */
export function buildQuestionEdges(full: GraphFull): GraphQuestionEdge[] {
  if (Array.isArray(full.question_edges) && full.question_edges.length > 0) {
    return full.question_edges
      .filter((e) => e.source && e.target)
      .map((e) => ({
        source: e.source,
        target: e.target,
        relation: e.relation || 'prereq',
        why: e.why,
      }));
  }

  const qs = full.questions;
  const byQid = new Map(qs.map((q) => [q.qid, q]));
  const key = (a: string, b: string) => `${a}->${b}`;
  const seen = new Set<string>();
  const out: GraphQuestionEdge[] = [];
  const push = (a: string, b: string) => {
    if (!a || !b || a === b) return;
    const k = key(a, b);
    if (seen.has(k)) return;
    seen.add(k);
    out.push({ source: a, target: b, relation: 'prereq' });
  };

  // 1) 共享知识点（最可靠）
  for (const a of qs) {
    for (const b of qs) {
      if ((a.layer ?? 0) >= (b.layer ?? 0)) continue;
      const nodesA = new Set(a.node_ids ?? []);
      const kpA = new Set(a.kp_ids ?? []);
      if ((b.node_ids ?? []).some((id) => nodesA.has(id)) || (b.kp_ids ?? []).some((id) => kpA.has(id))) {
        push(a.qid, b.qid);
      }
    }
  }

  // 2) 同一章的跨层问题（每源最多补 2 条，避免糊成网）
  const chapterByNode = new Map<string, string | undefined>();
  for (const n of full.nodes) chapterByNode.set(n.id, n.chapter);
  const chaptersOf = (q: GraphQuestion) =>
    new Set((q.node_ids ?? []).map((id) => chapterByNode.get(id)).filter(Boolean));
  for (const a of qs) {
    const cs = chaptersOf(a);
    if (cs.size === 0) continue;
    let added = 0;
    for (const b of qs) {
      if (added >= 2) break;
      if ((b.layer ?? 0) !== (a.layer ?? 0) + 1) continue;
      if ([...chaptersOf(b)].some((c) => cs.has(c))) {
        if (!out.some((e) => e.source === a.qid && e.target === b.qid)) {
          push(a.qid, b.qid);
          added += 1;
        }
      }
    }
  }

  // 确保每个 qid 有效
  return out.filter((e) => byQid.has(e.source) && byQid.has(e.target));
}

export interface QuestionPath {
  upstream: Set<string>;
  downstream: Set<string>;
}

export function questionPath(edges: GraphQuestionEdge[], id: string): QuestionPath {
  const upstream = new Set<string>();
  const downstream = new Set<string>();
  const up = (cur: string) => {
    for (const e of edges) {
      if (e.target === cur && !upstream.has(e.source)) {
        upstream.add(e.source);
        up(e.source);
      }
    }
  };
  const down = (cur: string) => {
    for (const e of edges) {
      if (e.source === cur && !downstream.has(e.target)) {
        downstream.add(e.target);
        down(e.target);
      }
    }
  };
  up(id);
  down(id);
  return { upstream, downstream };
}

export function layerOfQuestion(full: GraphFull, q: GraphQuestion): number {
  if (typeof q.layer === 'number') return q.layer;
  for (const layer of full.question_layers ?? []) {
    if ((layer.qids ?? []).includes(q.qid)) return layer.layer;
  }
  return 1;
}
