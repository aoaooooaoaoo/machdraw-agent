import { useMemo, useState } from 'react';
import type { GraphFull, GraphNeighbor, GraphNodeDetail, GraphNodeInfo } from '../../lib/types';
import { Icon } from '../../shell/Icons';
import {
  REL_CN,
  REL_PRIORITY,
  REL_STYLE,
  STATE_COLOR,
  TIER_BASE,
  TIER_CN,
  TIER_COLOR,
  TIER_ORDER,
  clipLabel,
  stateColor,
  tierOf,
} from './constants';
import { CHAPTER_COLORS } from './layout';

const W = 460;
const H = 520;
const CX = 230;
const CY = 252;

interface Placed {
  node: GraphNodeInfo;
  rel: string;
  rels: string[];
  note?: string;
  x: number;
  y: number;
  r: number;
  angle: number;
  tier: string;
}

/** 焦点星图：focus 在中心，邻居按 tier 分环（同 tier 人数多时内外交错避免标签重叠）。 */
function buildLayout(neighbors: GraphNeighbor[]): Placed[] {
  // 去重：一个知识点可能有多条关系，只画一个节点，关系挂在 rels 上
  const merged = new Map<string, { node: GraphNodeInfo; note?: string; rels: string[] }>();
  for (const n of neighbors) {
    if (!n || !n.node || !n.node.id) continue;
    const hit = merged.get(n.node.id);
    if (hit) {
      if (!hit.rels.includes(n.rel)) hit.rels.push(n.rel);
      if (!hit.note && n.note) hit.note = n.note;
    } else {
      merged.set(n.node.id, { node: n.node, note: n.note, rels: [n.rel] });
    }
  }

  const groups = new Map<string, { node: GraphNodeInfo; note?: string; rels: string[] }[]>();
  for (const item of merged.values()) {
    const tier = tierOf(item.node);
    const list = groups.get(tier) ?? [];
    list.push(item);
    groups.set(tier, list);
  }

  const placed: Placed[] = [];
  TIER_ORDER.forEach((tier, tierIndex) => {
    const list = groups.get(tier) ?? [];
    if (list.length === 0) return;
    list.sort((a, b) => {
      const ra = Math.min(...a.rels.map((r) => REL_PRIORITY[r] ?? 9));
      const rb = Math.min(...b.rels.map((r) => REL_PRIORITY[r] ?? 9));
      if (ra !== rb) return ra - rb;
      return String(a.node.label).localeCompare(String(b.node.label), 'zh');
    });
    const base = TIER_BASE[tier] ?? 200;
    const crowded = list.length > 6;
    const start = -Math.PI / 2 + tierIndex * 0.32; // 各环错开起始角，避免同一条辐线上叠字
    list.forEach((n, i) => {
      const r = base + (crowded && i % 2 === 1 ? 23 : 0);
      const angle = start + (i / list.length) * Math.PI * 2;
      placed.push({
        node: n.node,
        rel: [...n.rels].sort((x, y) => (REL_PRIORITY[x] ?? 9) - (REL_PRIORITY[y] ?? 9))[0],
        rels: n.rels,
        note: n.note,
        x: CX + r * Math.cos(angle),
        y: CY + r * Math.sin(angle),
        r,
        angle,
        tier,
      });
    });
  });
  return placed;
}

/** 标签锚点：按角度朝外，越界时翻转，避免右侧被裁。 */
function labelPlacement(p: Placed, text: string): { x: number; y: number; anchor: 'start' | 'middle' | 'end' } {
  const cos = Math.cos(p.angle);
  const sin = Math.sin(p.angle);
  const est = text.length * 10;
  if (cos > 0.35) {
    const x = p.x + 9;
    if (x + est > W - 4) return { x: p.x - 9, y: p.y + 4, anchor: 'end' };
    return { x, y: p.y + 4, anchor: 'start' };
  }
  if (cos < -0.35) {
    const x = p.x - 9;
    if (x - est < 4) return { x: p.x + 9, y: p.y + 4, anchor: 'start' };
    return { x, y: p.y + 4, anchor: 'end' };
  }
  return { x: p.x, y: sin < 0 ? p.y - 11 : p.y + 18, anchor: 'middle' };
}

interface FocusViewProps {
  detail: GraphNodeDetail;
  full: GraphFull | null;
  loading: boolean;
  error: string | null;
  onFocus: (id: string) => void;
  onAsk: (text: string) => void;
  onBackToOverview: () => void;
}

/**
 * 焦点视图：chat artifact 直接进入；或全览星图里点节点后进入。
 * 中心 focus + 邻居按 tier 分环，下方是焦点详情 / 前置路径 / 相关课程问题。
 */
export function FocusView({ detail, full, loading, error, onFocus, onAsk, onBackToOverview }: FocusViewProps) {
  const focus = detail.node;
  const neighbors = Array.isArray(detail.neighbors) ? detail.neighbors : [];
  const prereq = Array.isArray(detail.prereq) ? detail.prereq : [];
  const [expandPrereq, setExpandPrereq] = useState(false);

  const placed = useMemo(() => buildLayout(neighbors), [neighbors]);
  const prereqIds = useMemo(() => new Set(prereq.map((p) => p.id)), [prereq]);
  const uniqueNeighbors = useMemo(() => new Set(neighbors.map((n) => n.id)).size, [neighbors]);

  const relatedQuestions = useMemo(() => {
    if (!full || !focus?.kp_id) return [];
    return full.questions.filter((q) => (q.kp_ids || []).includes(focus.kp_id!)).slice(0, 3);
  }, [full, focus]);

  if (!focus || !focus.id) {
    return (
      <div className="canvas-empty-inline">
        <Icon name="alert" size={20} />
        <p>焦点数据缺失。</p>
      </div>
    );
  }

  const focusTier = tierOf(focus);
  const chapterOrder = useMemo(() => {
    const fromSectors = (full?.sectors ?? []).map((s) => s.chapter).filter(Boolean);
    const unique = fromSectors.length
      ? fromSectors
      : [...new Set((full?.nodes ?? []).map((n) => n.chapter).filter(Boolean))];
    return unique as string[];
  }, [full]);
  const colorOf = (node: GraphNodeInfo) => {
    const idx = chapterOrder.indexOf(node.chapter || '');
    return CHAPTER_COLORS[(idx >= 0 ? idx : 0) % CHAPTER_COLORS.length];
  };
  const focusColor = colorOf(focus);
  const shownPrereq = expandPrereq ? prereq : prereq.slice(0, 6);

  return (
    <>
      <div className="kg-view-toolbar">
        <button className="link-btn kg-back" type="button" onClick={onBackToOverview}>
          <Icon name="chevron" size={12} className="kg-chevron-left" />
          全览星图
        </button>
        <span className="kg-view-hint">当前：焦点关系（中心 + 直接邻居）</span>
      </div>

      {error && (
        <div className="kg-error">
          <Icon name="alert" size={13} />
          {error}
        </div>
      )}

      <div className="kg-chart-wrap">
        <svg className="kg-chart" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="知识图谱焦点星图">
          <defs>
            <radialGradient id="kgBg" cx="50%" cy="46%" r="62%">
              <stop offset="0%" stopColor="#ffffff" />
              <stop offset="100%" stopColor="#f3f7fc" />
            </radialGradient>
            <marker
              id="kgArrowCause"
              viewBox="0 0 10 10"
              refX="9"
              refY="5"
              markerWidth="5"
              markerHeight="5"
              orient="auto-start-reverse"
            >
              <path d="M0 0 L10 5 L0 10 z" fill="#16a34a" />
            </marker>
          </defs>

          <rect x="0" y="0" width={W} height={H} fill="url(#kgBg)" />

          {/* tier 环底纹：core→concept 由内到外 */}
          {TIER_ORDER.map((tier) => (
            <circle
              key={`ring-${tier}`}
              cx={CX}
              cy={CY}
              r={TIER_BASE[tier] ?? 200}
              fill="none"
              stroke={TIER_COLOR[tier]}
              strokeOpacity="0.14"
              strokeDasharray="3 5"
            />
          ))}

          {/* 边：focus → 邻居，按关系上色；同一节点多关系时平行微偏移 */}
          {placed.flatMap((p) => {
            const dx = p.x - CX;
            const dy = p.y - CY;
            const len = Math.hypot(dx, dy) || 1;
            const ux = dx / len;
            const uy = dy / len;
            const nx = -uy;
            const ny = ux;
            return p.rels.map((rel, ri) => {
              const style = REL_STYLE[rel] ?? REL_STYLE.prereq;
              const off = (ri - (p.rels.length - 1) / 2) * 3.2;
              const x1 = CX + ux * 19 + nx * off;
              const y1 = CY + uy * 19 + ny * off;
              const x2 = p.x - ux * (p.r + 3) + nx * off;
              const y2 = p.y - uy * (p.r + 3) + ny * off;
              return (
                <line
                  key={`edge-${p.node.id}-${rel}`}
                  x1={x1}
                  y1={y1}
                  x2={x2}
                  y2={y2}
                  stroke={style.stroke}
                  strokeWidth={style.width}
                  strokeDasharray={style.dash}
                  strokeOpacity={rel === 'prereq' ? 0.7 : 0.55}
                  markerEnd={rel === 'cause' ? 'url(#kgArrowCause)' : undefined}
                />
              );
            });
          })}

          {/* 邻居节点 */}
          {placed.map((p) => {
            const color = colorOf(p.node);
            const fill = stateColor(p.node.state);
            const text = clipLabel(p.node.label);
            const lp = labelPlacement(p, text);
            const isPrereq = p.rel === 'prereq' || prereqIds.has(p.node.id);
            return (
              <g
                key={`node-${p.node.id}`}
                className="kg-node"
                onClick={() => onFocus(p.node.id)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') onFocus(p.node.id);
                }}
              >
                <title>
                  {`${p.node.label}（${TIER_CN[p.tier] ?? p.tier} · ${p.node.state ?? '—'}）\n${
                    p.node.chapter ?? ''
                  }\n关系：${p.rels.map((r) => REL_CN[r] ?? r).join(' / ')}${
                    p.note ? ` — ${p.note}` : ''
                  }`}
                </title>
                {isPrereq && (
                  <circle cx={p.x} cy={p.y} r={11} fill="none" stroke={color} strokeOpacity="0.45" strokeDasharray="3 3" />
                )}
                <circle cx={p.x} cy={p.y} r={6.5} fill={fill} stroke={color} strokeWidth="2" />
                <text
                  x={lp.x}
                  y={lp.y}
                  textAnchor={lp.anchor}
                  className="kg-node-label"
                  fill={color}
                  style={{ paintOrder: 'stroke', stroke: '#fff', strokeWidth: 3 }}
                >
                  {text}
                </text>
              </g>
            );
          })}

          {/* 焦点节点（中心） */}
          <g className="kg-focus">
            <circle cx={CX} cy={CY} r={24} fill={focusColor} fillOpacity="0.1" />
            <circle cx={CX} cy={CY} r={17} fill={stateColor(focus.state)} stroke={focusColor} strokeWidth="3.2" />
            <text x={CX} y={CY + 5} textAnchor="middle" className="kg-focus-core">
              {focus.label.slice(0, 1)}
            </text>
            <text
              x={CX}
              y={CY + 40}
              textAnchor="middle"
              className="kg-focus-label"
              style={{ paintOrder: 'stroke', stroke: '#fff', strokeWidth: 4 }}
            >
              {focus.label}
            </text>
            <text x={CX} y={CY + 55} textAnchor="middle" className="kg-focus-sub">
              {TIER_CN[focusTier] ?? focusTier}
              {focus.state ? ` · ${focus.state}` : ''}
            </text>
          </g>

          {loading && (
            <g>
              <rect x="0" y="0" width={W} height={H} fill="#fff" fillOpacity="0.45" />
              <text x={CX} y={CY - 40} textAnchor="middle" className="kg-loading">
                正在加载节点详情…
              </text>
            </g>
          )}
        </svg>
      </div>

      {/* 焦点详情 */}
      <div className="kg-focus-card">
        <div className="kg-focus-head">
          <span className="kg-focus-name">{focus.label}</span>
          <span className="chip" style={{ color: focusColor, borderColor: `${focusColor}55`, background: `${focusColor}10` }}>
            {TIER_CN[focusTier] ?? focusTier}
          </span>
          <span className="kg-state">
            <i className="kg-state-dot" style={{ background: stateColor(focus.state) }} />
            {focus.state ?? '—'}
          </span>
        </div>
        <div className="kg-focus-meta">
          {focus.kp_id && <span className="mono">{focus.kp_id}</span>}
          {focus.chapter && <span className="kg-chapter">{focus.chapter}</span>}
        </div>
        <div className="kg-focus-counts">
          直接关系 <b>{neighbors.length}</b> 条 · <b>{uniqueNeighbors}</b> 个知识点 · 前置{' '}
          <b>{prereq.length}</b> 个
        </div>
      </div>

      {/* 前置复习路径 */}
      {prereq.length > 0 && (
        <div className="kg-section">
          <div className="kg-section-head">
            <span className="kg-section-title">前置复习路径</span>
            <span className="kg-section-sub">按层级排序 · 点击换焦点</span>
          </div>
          <div className="kg-prereq-list">
            {shownPrereq.map((p) => (
              <button
                key={p.id}
                type="button"
                className="kg-prereq-item"
                onClick={() => onFocus(p.id)}
                title={`${p.node.chapter ?? ''}\n${p.note ?? ''}`}
              >
                <span className="kg-level">L{p.level}</span>
                <span className="kg-prereq-label">{p.node.label}</span>
                <span className="kg-prereq-tier" style={{ color: TIER_COLOR[tierOf(p.node)] }}>
                  {TIER_CN[tierOf(p.node)] ?? p.node.tier}
                </span>
              </button>
            ))}
          </div>
          {prereq.length > 6 && (
            <button className="link-btn kg-more" type="button" onClick={() => setExpandPrereq((v) => !v)}>
              <Icon name="chevron" size={12} className={expandPrereq ? 'is-open' : ''} />
              {expandPrereq ? '收起' : `展开全部 ${prereq.length} 个`}
            </button>
          )}
        </div>
      )}

      {/* 与本知识点相关的课程问题 */}
      {relatedQuestions.length > 0 && (
        <div className="kg-section">
          <div className="kg-section-head">
            <span className="kg-section-title">相关课程问题</span>
            <span className="kg-section-sub">点一下填进输入框</span>
          </div>
          <div className="kg-questions">
            {relatedQuestions.map((q) => (
              <button key={q.qid} type="button" className="kg-question" onClick={() => onAsk(q.question)}>
                <span className="kg-qid mono">{q.qid}</span>
                <span className="kg-question-text">{q.question}</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </>
  );
}
