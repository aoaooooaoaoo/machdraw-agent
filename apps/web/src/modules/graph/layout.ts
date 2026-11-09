/**
 * 知识图谱布局引擎（零依赖，纯 TS）。
 *
 * 视觉目标：按章分成 10 个彼此分离、内部有机的"知识点星团"，而不是一个挤在一起的毛球。
 *
 * 算法：
 *   1. 4-3-3 网格给每章一个锚点（课程顺序）；
 *   2. 每个簇内部单独做力导：锚点弹簧 + 簇内排斥 + 碰撞 + 半径约束（保证不越界）；
 *   3. 跨章关系只画线、不参与受力（否则会把所有簇拉成一团）；
 *   4. 用成员坐标拟合椭圆，作为章节"晕圈"（渲染层画半透明底 + 虚线轮廓）。
 *
 * 坐标系固定 1200×800；渲染层用 viewBox 自适应。
 */
import type { GraphFull, GraphNodeInfo } from '../../lib/types';

export const LAYOUT_W = 1280;
export const LAYOUT_H = 920;

/** 10 章分类色（浅底上对比度足够、彼此可区分）。 */
export const CHAPTER_COLORS = [
  '#2f6fed',
  '#0e9aa7',
  '#7c5cfc',
  '#e0559b',
  '#ef6c35',
  '#2f9e44',
  '#c9950b',
  '#0f766e',
  '#4c6ef5',
  '#a15c00',
];

export interface LayoutNode {
  node: GraphNodeInfo;
  x: number;
  y: number;
  r: number;
  chapter: string;
  color: string;
  degree: number;
}

export interface LayoutEdge {
  source: string;
  target: string;
  rel: string;
  /** 二次贝塞尔路径 */
  d: string;
}

export interface Cluster {
  chapter: string;
  short: string;
  color: string;
  cx: number;
  cy: number;
  rx: number;
  ry: number;
  /** 椭圆主轴旋转角（弧度） */
  angle: number;
  count: number;
}

export interface GraphLayout {
  nodes: LayoutNode[];
  nodeMap: Map<string, LayoutNode>;
  edges: LayoutEdge[];
  clusters: Cluster[];
  adjacency: Map<string, Set<string>>;
  bounds: { minX: number; minY: number; maxX: number; maxY: number };
}

function shortChapter(chapter: string): string {
  const stripped = chapter.replace(/^第[一二三四五六七八九十]+章\s*/, '');
  const text = stripped || chapter;
  return text.length > 12 ? `${text.slice(0, 12)}…` : text;
}

/** 确定性伪随机（同一份数据每次布局一致，刷新后图形不跳）。 */
function lcg(seed: number): () => number {
  let s = seed >>> 0;
  return () => {
    s = (s * 1664525 + 1013904223) >>> 0;
    return s / 4294967296;
  };
}

const ROWS = 3;
const MARGIN_X = 74;
const MARGIN_Y = 64;

/** 章节网格锚点：按课程顺序 4-3-3 排布。 */
function gridAnchors(n: number): { x: number; y: number; cellW: number; cellH: number }[] {
  const counts: number[] = n <= 4 ? [n, 0, 0] : n <= 8 ? [Math.ceil(n / 2), Math.floor(n / 2), 0] : [4, 3, 3];
  const usableW = LAYOUT_W - MARGIN_X * 2;
  const usableH = LAYOUT_H - MARGIN_Y * 2;
  const cellW = usableW / 4;
  const cellH = usableH / ROWS;
  const out: { x: number; y: number; cellW: number; cellH: number }[] = [];
  counts.forEach((count, ri) => {
    for (let i = 0; i < count; i += 1) {
      // 奇数行错位半格，避免上下两行垂直重叠
      const offset = ri % 2 === 1 ? 0.5 : 0;
      const x = MARGIN_X + (usableW * (i + 0.5 + offset)) / Math.max(count, 1);
      const y = MARGIN_Y + (usableH * (ri + 0.5)) / ROWS;
      out.push({ x, y, cellW, cellH });
    }
  });
  return out;
}

export function buildGraphLayout(full: GraphFull): GraphLayout {
  const nodeById = new Map(full.nodes.map((n) => [n.id, n]));
  const degree = new Map<string, number>();
  for (const e of full.edges) {
    degree.set(e.source, (degree.get(e.source) ?? 0) + 1);
    degree.set(e.target, (degree.get(e.target) ?? 0) + 1);
  }

  // 章节顺序按节点 sector（后端按课程顺序编号），否则按出现顺序
  const chapterOrder: string[] = [];
  for (const n of full.nodes) {
    const ch = n.chapter || '未分章';
    if (!chapterOrder.includes(ch)) chapterOrder.push(ch);
  }
  const sectorOfChapter = new Map<string, number>();
  for (const n of full.nodes) {
    const ch = n.chapter || '未分章';
    const sec = typeof n.sector === 'number' ? n.sector : 99;
    if (!sectorOfChapter.has(ch) || sec < (sectorOfChapter.get(ch) as number)) {
      sectorOfChapter.set(ch, sec);
    }
  }
  const chapters = [...chapterOrder].sort(
    (a, b) => (sectorOfChapter.get(a) ?? 99) - (sectorOfChapter.get(b) ?? 99),
  );
  const anchors = gridAnchors(chapters.length);
  const chapterIndex = new Map(chapters.map((c, i) => [c, i]));
  const rand = lcg(20261109);

  // --- 每章目标半径：随节点数增长，但不超出网格单元 ---
  const countOf = new Map<string, number>();
  for (const n of full.nodes) {
    const ch = n.chapter || '未分章';
    countOf.set(ch, (countOf.get(ch) ?? 0) + 1);
  }
  const radiusOf = new Map<string, number>();
  for (const ch of chapters) {
    const anchor = anchors[chapterIndex.get(ch) ?? 0];
    const cap = anchor ? Math.min(anchor.cellW, anchor.cellH) * 0.42 : 110;
    const want = 54 + 10.5 * Math.sqrt(countOf.get(ch) ?? 1);
    radiusOf.set(ch, Math.min(cap, want));
  }

  const layoutNodes: LayoutNode[] = full.nodes.map((node) => {
    const ch = node.chapter || '未分章';
    const ci = chapterIndex.get(ch) ?? 0;
    const anchor = anchors[ci] ?? { x: LAYOUT_W / 2, y: LAYOUT_H / 2 };
    const R = radiusOf.get(ch) ?? 80;
    const angle = rand() * Math.PI * 2;
    const dist = Math.sqrt(rand()) * R * 0.86;
    const tier = node.tier ?? 'concept';
    const deg = degree.get(node.id) ?? 0;
    const r =
      (tier === 'core' ? 10.5 : tier === 'trackA' || tier === 'trackB' ? 7.2 : tier === 'branch' ? 6.2 : 5.6) +
      Math.min(5, deg * 0.32);
    return {
      node,
      x: anchor.x + Math.cos(angle) * dist,
      y: anchor.y + Math.sin(angle) * dist,
      r,
      chapter: ch,
      color: CHAPTER_COLORS[ci % CHAPTER_COLORS.length],
      degree: deg,
    };
  });
  const nodeMap = new Map(layoutNodes.map((p) => [p.node.id, p]));

  const links = full.edges
    .map((e) => ({ source: e.source, target: e.target, rel: e.rel || e.relation || 'prereq' }))
    .filter((e) => nodeMap.has(e.source) && nodeMap.has(e.target));

  // --- 簇内力导 ---
  const byChapter = new Map<string, LayoutNode[]>();
  for (const p of layoutNodes) {
    const list = byChapter.get(p.chapter) ?? [];
    list.push(p);
    byChapter.set(p.chapter, list);
  }
  const TICKS = 260;
  for (let tick = 0; tick < TICKS; tick += 1) {
    const cool = 1 - tick / TICKS;
    for (const [ch, members] of byChapter) {
      const ci = chapterIndex.get(ch) ?? 0;
      const anchor = anchors[ci];
      const R = radiusOf.get(ch) ?? 80;
      if (!anchor) continue;
      // 锚点弹簧
      for (const p of members) {
        p.x += (anchor.x - p.x) * 0.035 * cool;
        p.y += (anchor.y - p.y) * 0.035 * cool;
      }
      // 簇内排斥 + 碰撞
      for (let i = 0; i < members.length; i += 1) {
        const a = members[i];
        for (let j = i + 1; j < members.length; j += 1) {
          const b = members[j];
          const dx = a.x - b.x;
          const dy = a.y - b.y;
          const d = Math.hypot(dx, dy) || 1;
          const minDist = a.r + b.r + 8;
          if (d < minDist) {
            const push = ((minDist - d) / d) * 0.5;
            a.x += dx * push;
            a.y += dy * push;
            b.x -= dx * push;
            b.y -= dy * push;
          } else if (d < R * 1.5) {
            const f = (900 / (d * d)) * cool;
            const ux = dx / d;
            const uy = dy / d;
            a.x += ux * f * 6;
            a.y += uy * f * 6;
            b.x -= ux * f * 6;
            b.y -= uy * f * 6;
          }
        }
      }
      // 簇内边弹簧
      for (const l of links) {
        if (nodeMap.get(l.source)!.chapter !== ch) continue;
        const a = nodeMap.get(l.source)!;
        const b = nodeMap.get(l.target)!;
        if (b.chapter !== ch) continue;
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const d = Math.hypot(dx, dy) || 1;
        const rest = a.r + b.r + 22;
        const f = (d - rest) * 0.02 * cool;
        const ux = dx / d;
        const uy = dy / d;
        a.x += ux * f;
        a.y += uy * f;
        b.x -= ux * f;
        b.y -= uy * f;
      }
      // 半径约束：超出目标半径就拉回
      for (const p of members) {
        const dx = p.x - anchor.x;
        const dy = p.y - anchor.y;
        const d = Math.hypot(dx, dy);
        const lim = R * 1.02;
        if (d > lim) {
          const scale = lim / d;
          p.x = anchor.x + dx * scale;
          p.y = anchor.y + dy * scale;
        }
      }
    }
  }

  // --- 归一化：整体等比缩放到 1200×800（四周留 46） ---
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  for (const p of layoutNodes) {
    minX = Math.min(minX, p.x - p.r);
    minY = Math.min(minY, p.y - p.r);
    maxX = Math.max(maxX, p.x + p.r);
    maxY = Math.max(maxY, p.y + p.r);
  }
  const pad = 46;
  const scale = Math.min(
    (LAYOUT_W - pad * 2) / Math.max(1, maxX - minX),
    (LAYOUT_H - pad * 2) / Math.max(1, maxY - minY),
  );
  const offsetX = (LAYOUT_W - (maxX - minX) * scale) / 2 - minX * scale;
  const offsetY = (LAYOUT_H - (maxY - minY) * scale) / 2 - minY * scale;
  for (const p of layoutNodes) {
    p.x = p.x * scale + offsetX;
    p.y = p.y * scale + offsetY;
    p.r = Math.max(4, p.r * Math.min(1.1, scale));
  }

  // --- 章节簇椭圆 ---
  const clusters: Cluster[] = chapters.map((chapter, ci) => {
    const members = layoutNodes.filter((p) => p.chapter === chapter);
    const count = members.length || 1;
    const cx = members.reduce((s, p) => s + p.x, 0) / count;
    const cy = members.reduce((s, p) => s + p.y, 0) / count;
    let sxx = 0;
    let syy = 0;
    let sxy = 0;
    for (const p of members) {
      const dx = p.x - cx;
      const dy = p.y - cy;
      sxx += dx * dx;
      syy += dy * dy;
      sxy += dx * dy;
    }
    sxx /= count;
    syy /= count;
    sxy /= count;
    const angle = 0.5 * Math.atan2(2 * sxy, sxx - syy);
    // 用 PCA 主轴上的实际最大投影（而不是标准差）算椭圆半径，保证把成员节点都包住
    const ca = Math.cos(-angle);
    const sa = Math.sin(-angle);
    let maxX = 0;
    let maxY = 0;
    for (const p of members) {
      const dx = p.x - cx;
      const dy = p.y - cy;
      const px = dx * ca - dy * sa;
      const py = dx * sa + dy * ca;
      maxX = Math.max(maxX, Math.abs(px) + p.r);
      maxY = Math.max(maxY, Math.abs(py) + p.r);
    }
    const rx = Math.max(38, maxX + 14);
    const ry = Math.max(34, maxY + 14);
    return {
      chapter,
      short: shortChapter(chapter),
      color: CHAPTER_COLORS[ci % CHAPTER_COLORS.length],
      cx,
      cy,
      rx,
      ry,
      angle,
      count: members.length,
    };
  });

  // --- 边路径 ---
  const edges: LayoutEdge[] = links.map((l, idx) => {
    const a = nodeMap.get(l.source)!;
    const b = nodeMap.get(l.target)!;
    const dx = b.x - a.x;
    const dy = b.y - a.y;
    const len = Math.hypot(dx, dy) || 1;
    const ux = dx / len;
    const uy = dy / len;
    const x1 = a.x + ux * (a.r + 2);
    const y1 = a.y + uy * (a.r + 2);
    const x2 = b.x - ux * (b.r + 2);
    const y2 = b.y - uy * (b.r + 2);
    const sameChapter = a.chapter === b.chapter;
    const bend = sameChapter ? Math.min(14, len * 0.14) : Math.min(64, 16 + len * 0.09);
    const sign = idx % 2 === 0 ? 1 : -1;
    const mx = (x1 + x2) / 2;
    const my = (y1 + y2) / 2;
    const cx = mx + -uy * bend * sign;
    const cy = my + ux * bend * sign;
    return {
      source: l.source,
      target: l.target,
      rel: l.rel,
      d: `M ${x1.toFixed(1)} ${y1.toFixed(1)} Q ${cx.toFixed(1)} ${cy.toFixed(1)} ${x2.toFixed(1)} ${y2.toFixed(1)}`,
    };
  });

  const adjacency = new Map<string, Set<string>>();
  for (const l of links) {
    if (!adjacency.has(l.source)) adjacency.set(l.source, new Set());
    if (!adjacency.has(l.target)) adjacency.set(l.target, new Set());
    adjacency.get(l.source)!.add(l.target);
    adjacency.get(l.target)!.add(l.source);
  }

  const bounds = layoutNodes.reduce(
    (acc, p) => ({
      minX: Math.min(acc.minX, p.x - p.r),
      minY: Math.min(acc.minY, p.y - p.r),
      maxX: Math.max(acc.maxX, p.x + p.r),
      maxY: Math.max(acc.maxY, p.y + p.r),
    }),
    { minX: Infinity, minY: Infinity, maxX: -Infinity, maxY: -Infinity },
  );

  return { nodes: layoutNodes, nodeMap, edges, clusters, adjacency, bounds };
}

/** 估算中文标签宽度（px，11px 字号）。 */
export function estimateLabelWidth(text: string): number {
  let w = 0;
  for (const ch of text) w += /[\u4e00-\u9fff]/.test(ch) ? 11 : 6.5;
  return w;
}
