import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import type { GraphFull, GraphQuestion } from '../../lib/types';
import type { TeachingCourse } from '../../lib/api';
import { Icon } from '../../shell/Icons';
import {
  buildQuestionEdges,
  layerOfQuestion,
  questionPath,
} from './pageData';

const LAYER_STYLE = [
  { accent: '#6366f1', bg: 'rgba(99,102,241,0.06)', border: 'rgba(99,102,241,0.28)' },
  { accent: '#14b8a6', bg: 'rgba(20,184,166,0.07)', border: 'rgba(20,184,166,0.28)' },
  { accent: '#f59e0b', bg: 'rgba(245,158,11,0.08)', border: 'rgba(245,158,11,0.30)' },
];

const BLOOM_COLOR: Record<string, string> = {
  记忆: '#8b5cf6',
  理解: '#3b82f6',
  分析: '#f59e0b',
  应用: '#0ea5e9',
  综合: '#ef4444',
};

const REL_COLOR: Record<string, string> = {
  prereq: '#22d3ee',
  cause: '#f59e0b',
  contrast: '#a78bfa',
};

const DEFAULT_HIGHLIGHT = 'Q-004';

interface Anchors {
  left: { x: number; y: number };
  right: { x: number; y: number };
}

interface Props {
  full: GraphFull;
  cases?: TeachingCourse['cases'];
  abilities?: TeachingCourse['abilities'];
  onJumpCase?: (id: string) => void;
  onJumpAbility?: (id: string) => void;
  focusId: string | null;
  onSelectQuestion: (qid: string | null) => void;
  onJumpKnowledge: (nodeId: string) => void;
}

const STYLE = `
.qp-wrap { flex: 1; min-height: 0; display: flex; flex-direction: column; position: relative; background: #f6f8fc; }
.qp-bar { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; padding: 8px 16px; border-bottom: 1px solid rgba(120,150,200,.18); font-size: 12px; color: #475569; background: rgba(255,255,255,.6); }
.qp-bar input, .qp-bar select { border: 1px solid #bfcde0; border-radius: 6px; background: #fff; color: #1e293b; font: inherit; padding: 5px 7px; }
.qp-bar b { color: #334155; }
.qp-bar .spacer { flex: 1; }
.qp-scroll { flex: 1; min-height: 0; overflow: auto; padding: 14px 18px 28px; }
.qp-board { position: relative; display: grid; grid-template-columns: repeat(3, minmax(280px, 1fr)); gap: 30px; align-items: start; min-width: 900px; }
.qp-col { display: flex; flex-direction: column; gap: 12px; min-width: 0; }
.qp-col-head { padding: 2px 2px 8px; }
.qp-col-top { display: flex; align-items: baseline; gap: 8px; font-size: 13px; font-weight: 700; }
.qp-col-top .cnt { font-size: 11px; color: #64748b; font-weight: 400; }
.qp-col-desc { margin-top: 3px; font-size: 10.5px; color: #64748b; }
.qp-col-bar { margin-top: 8px; height: 2px; border-radius: 2px; opacity: .55; }
.qp-svg { position: absolute; inset: 0; width: 100%; height: 100%; overflow: visible; pointer-events: none; }
.qp-flow { animation: qp-dash 1.1s linear infinite; }
@keyframes qp-dash { to { stroke-dashoffset: -32; } }
.qp-card { position: relative; border-radius: 13px; padding: 11px 14px 11px 15px; cursor: pointer; background: #fff; border: 1px solid rgba(120,150,200,.25); transition: opacity .18s, box-shadow .18s, transform .18s; }
.qp-card::before { content: ''; position: absolute; left: 0; top: 10px; bottom: 10px; width: 3px; border-radius: 3px; background: var(--qp-accent); opacity: .75; }
.qp-card:hover { transform: translateY(-1px); box-shadow: 0 8px 20px rgba(15,23,42,.10); }
.qp-card.sel { box-shadow: 0 0 0 1.5px var(--qp-accent), 0 12px 28px rgba(15,23,42,.12); }
.qp-card.dim { opacity: .25; }
.qp-card .top { display: flex; align-items: center; gap: 7px; margin-bottom: 6px; }
.qp-card .idx { font: 600 10px/1 var(--mono, monospace); color: var(--qp-accent); background: color-mix(in srgb, var(--qp-accent) 12%, transparent); border: 1px solid color-mix(in srgb, var(--qp-accent) 35%, transparent); padding: 2px 5px; border-radius: 5px; }
.qp-card .tier { font-size: 10.5px; color: var(--qp-accent); }
.qp-card .detail { margin-left: auto; border: 0; background: none; color: #64748b; font-size: 10.5px; cursor: pointer; padding: 0; }
.qp-card .qtitle { font-size: 12.5px; line-height: 1.6; margin: 0 0 7px; color: #1e293b; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }
.qp-card.open .qtitle { display: block; }
.qp-card .more { border: 0; background: none; color: #2563eb; font-size: 10px; cursor: pointer; padding: 0; }
.qp-card .foot { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
.qp-bloom { font-size: 10px; border-radius: 5px; border: 1px solid currentColor; padding: 1px 7px; }
.qp-chips { display: flex; gap: 5px; flex-wrap: wrap; margin-top: 7px; }
.qp-chip { border: 1px solid rgba(37,99,235,.25); background: rgba(37,99,235,.06); color: #2563eb; border-radius: 6px; font-size: 10px; padding: 2px 7px; cursor: pointer; }
.qp-chip:hover { background: rgba(37,99,235,.12); }
.qp-hintbtn { margin-top: 7px; border: 1px dashed #fde68a; background: #fffbeb; color: #b45309; border-radius: 999px; font-size: 9.5px; padding: 2px 8px; cursor: pointer; }
.qp-hinttext { margin: 6px 0 0; font-size: 10.5px; line-height: 1.55; color: #92400e; background: #fffbeb; border: 1px solid #fde68a; border-radius: 6px; padding: 6px 8px; }
.qp-drawer { position: absolute; right: 14px; top: 53px; bottom: 14px; width: min(360px, calc(100% - 28px)); z-index: 20; overflow-y: auto; border-radius: 14px; padding: 14px 15px 18px; background: #fff; border: 1px solid rgba(120,150,200,.32); box-shadow: 0 18px 46px rgba(15,23,42,.18); }
.qp-drawer h4 { margin: 0 0 8px; font-size: 13px; line-height: 1.6; color: #0f172a; padding-right: 22px; }
.qp-drawer .close { position: absolute; right: 10px; top: 10px; width: 24px; height: 24px; border-radius: 7px; border: 1px solid rgba(120,150,200,.3); background: none; color: #475569; cursor: pointer; }
.qp-drawer .sec { display: block; margin: 13px 0 5px; font-size: 10.5px; font-weight: 700; color: #64748b; }
.qp-drawer p, .qp-drawer li { font-size: 11.5px; line-height: 1.7; color: #334155; }
.qp-drawer ul { margin: 4px 0 0; padding-left: 17px; }
.qp-drawer .warn { margin-top: 10px; padding: 8px 10px; border-radius: 8px; font-size: 11px; line-height: 1.65; color: #b45309; background: #fffbeb; border: 1px solid #fde68a; }
.qp-drawer .acts { display: flex; gap: 7px; margin-top: 14px; }
.qp-drawer .acts button { flex: 1; border: 1px solid rgba(37,99,235,.35); background: rgba(37,99,235,.08); color: #1d4ed8; border-radius: 8px; padding: 7px 0; font-size: 11.5px; cursor: pointer; }
.qp-drawer .acts button.ghost { background: #f8fafc; color: #475569; border-color: rgba(120,150,200,.3); }
@media (max-width: 640px) { .qp-drawer { top: 104px; } }
`;

export function QuestionPage({ full, focusId, onSelectQuestion, onJumpKnowledge, cases, abilities, onJumpCase, onJumpAbility }: Props) {
  const boardRef = useRef<HTMLDivElement>(null);
  const cardRefs = useRef(new Map<string, HTMLDivElement>());
  const [anchors, setAnchors] = useState<Record<string, Anchors>>({});
  const [selected, setSelected] = useState<string | null>(focusId ?? null);
  const [hover, setHover] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [hintOpen, setHintOpen] = useState<Set<string>>(new Set());
  const [query, setQuery] = useState('');
  const [caseFilter, setCaseFilter] = useState('');

  useEffect(() => {
    if (focusId) setSelected(focusId);
  }, [focusId]);

  const edges = useMemo(() => buildQuestionEdges(full), [full]);
  const filter = cases?.find((item) => item.id === caseFilter);
  const visible = useMemo(() => {
    const term = query.trim().toLowerCase();
    const caseScope = filter ? new Set(filter.question_ids.flatMap((qid) => [
      qid, ...questionPath(edges, qid).upstream,
    ])) : null;
    const matched = full.questions.filter((q) => (!caseScope || caseScope.has(q.qid)) &&
      (!term || `${q.qid} ${q.question} ${q.kp_labels?.join(' ') ?? ''}`.toLowerCase().includes(term)));
    return new Set(matched.map((q) => q.qid));
  }, [query, filter, full.questions, edges]);
  const layers = useMemo(() => {
    const raw = full.question_layers?.length
      ? full.question_layers
      : [1, 2, 3].map((layer) => ({ layer, name: `第${layer}层`, desc: '', count: 0, qids: [] as string[] }));
    return raw.map((l) => {
      const qids = Array.isArray(l.qids) && l.qids.length
        ? l.qids
        : full.questions.filter((q) => layerOfQuestion(full, q) === l.layer).map((q) => q.qid);
      const qs = qids
        .map((qid) => full.questions.find((q) => q.qid === qid))
        .filter((q): q is GraphQuestion => !!q && visible.has(q.qid));
      return { layer: l.layer, name: l.name, desc: l.desc, qs };
    });
  }, [full, visible]);

  const activeQid = hover ?? selected ?? (visible.size === full.questions.length ? DEFAULT_HIGHLIGHT : null);
  const path = useMemo(
    () => (activeQid ? questionPath(edges, activeQid) : null),
    [edges, activeQid],
  );
  const activeIds = useMemo(() => {
    if (!path || !activeQid) return null;
    return new Set<string>([activeQid, ...path.upstream, ...path.downstream]);
  }, [path, activeQid]);

  const measure = () => {
    const board = boardRef.current;
    if (!board) return;
    const base = board.getBoundingClientRect();
    const next: Record<string, Anchors> = {};
    for (const [qid, el] of cardRefs.current) {
      const r = el.getBoundingClientRect();
      next[qid] = {
        left: { x: r.left - base.left, y: r.top - base.top + r.height / 2 },
        right: { x: r.right - base.left, y: r.top - base.top + r.height / 2 },
      };
    }
    setAnchors(next);
  };

  useLayoutEffect(() => {
    measure();
    const t = window.setTimeout(measure, 120);
    const ro = new ResizeObserver(measure);
    if (boardRef.current) ro.observe(boardRef.current);
    window.addEventListener('resize', measure);
    return () => {
      window.clearTimeout(t);
      ro.disconnect();
      window.removeEventListener('resize', measure);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const t = window.setTimeout(measure, 40);
    return () => window.clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [expanded, hintOpen, full, visible]);

  useEffect(() => {
    if (focusId) cardRefs.current.get(focusId)?.scrollIntoView({ block: 'nearest', inline: 'nearest' });
  }, [focusId]);

  // 同源多连线在锚点处扇形散开（参考作品公式）
  const geometry = useMemo(() => {
    const groups = new Map<string, typeof edges>();
    for (const e of edges) {
      const list = groups.get(e.source) ?? [];
      list.push(e);
      groups.set(e.source, list);
    }
    const out: { key: string; d: string; rel: string; on: boolean; dim: boolean }[] = [];
    for (const [source, list] of groups) {
      const sorted = [...list].sort(
        (a, b) => (anchors[a.target]?.left.y ?? 0) - (anchors[b.target]?.left.y ?? 0),
      );
      sorted.forEach((e, i) => {
        const a = anchors[source];
        const b = anchors[e.target];
        if (!a || !b) return;
        const off = (i - (sorted.length - 1) / 2) * 10;
        const x1 = a.right.x;
        const y1 = a.right.y + off;
        const x2 = b.left.x;
        const y2 = b.left.y + off * 0.4;
        const dx = Math.max(48, (x2 - x1) * 0.46);
        const on = activeIds ? activeIds.has(e.source) && activeIds.has(e.target) : false;
        const dim = activeIds ? !on : false;
        out.push({
          key: `${e.source}-${e.target}`,
          d: `M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`,
          rel: e.relation || 'prereq',
          on,
          dim,
        });
      });
    }
    return out;
  }, [edges, anchors, activeIds]);

  const counts = useMemo(() => {
    const out: Record<string, number> = {};
    const inc: Record<string, number> = {};
    for (const e of edges) {
      out[e.source] = (out[e.source] ?? 0) + 1;
      inc[e.target] = (inc[e.target] ?? 0) + 1;
    }
    return { out, inc };
  }, [edges]);

  const selectedQ = selected && visible.has(selected) ? full.questions.find((q) => q.qid === selected) : undefined;
  const selectedPath = selected ? questionPath(edges, selected) : null;
  const relatedCases = cases?.filter((item) => selected && item.question_ids.includes(selected)) ?? [];
  const relatedAbilities = abilities?.filter((item) => relatedCases.some((entry) =>
    entry.rubric.some((row) => row.ability_id === item.id))) ?? [];
  const relatedEdges = edges.filter((edge) => edge.why && (edge.source === selected || edge.target === selected));
  const focusQuestion = (qid: string) => {
    if (!visible.has(qid)) {
      setCaseFilter('');
      setQuery('');
    }
    setSelected(qid);
    onSelectQuestion(qid);
  };

  const renderCard = (q: GraphQuestion, index: number) => {
    const layer = layerOfQuestion(full, q);
    const style = LAYER_STYLE[layer - 1] ?? LAYER_STYLE[0];
    const dim = activeIds ? !activeIds.has(q.qid) : false;
    const isSel = selected === q.qid;
    const isExpanded = expanded.has(q.qid);
    const nodeIds = q.node_ids ?? [];
    const kps = nodeIds.slice(0, isExpanded ? nodeIds.length : 3);
    const rest = nodeIds.length - kps.length;
    return (
      <div
        key={q.qid}
        ref={(el) => {
          if (el) cardRefs.current.set(q.qid, el);
          else cardRefs.current.delete(q.qid);
        }}
        className={`qp-card${isSel ? ' sel' : ''}${dim ? ' dim' : ''}${isExpanded ? ' open' : ''}`}
        style={{ ['--qp-accent' as string]: style.accent, background: style.bg, borderColor: style.border }}
        onMouseEnter={() => setHover(q.qid)}
        onMouseLeave={() => setHover((h) => (h === q.qid ? null : h))}
        onClick={() => {
          const next = isSel ? null : q.qid;
          setSelected(next);
          onSelectQuestion(next);
        }}
      >
        <div className="top">
          <span className="idx">T{layer}-{String(index + 1).padStart(2, '0')}</span>
          <span className="tier">{q.bloom ?? ''}</span>
          <button
            className="detail"
            onClick={(e) => {
              e.stopPropagation();
              setSelected(q.qid);
              onSelectQuestion(q.qid);
            }}
          >
            详情 ›
          </button>
        </div>
        <p className="qtitle">{q.question}</p>
        {q.question.length > 70 && (
          <button
            className="more"
            onClick={(e) => {
              e.stopPropagation();
              setExpanded((prev) => {
                const next = new Set(prev);
                if (next.has(q.qid)) next.delete(q.qid);
                else next.add(q.qid);
                return next;
              });
            }}
          >
            {isExpanded ? '收起' : '展开全文'}
          </button>
        )}
        <div className="foot">
          {q.bloom && (
            <span className="qp-bloom" style={{ color: BLOOM_COLOR[q.bloom] ?? '#475569' }}>
              {q.bloom}
            </span>
          )}
        </div>
        <div className="qp-chips">
          {kps.map((id, i) => {
            const node = full.nodes.find((n) => n.id === id);
            const label = q.kp_labels?.[i] ?? node?.label ?? id;
            return (
              <button
                key={`${q.qid}-${id}`}
                className="qp-chip"
                title={node?.label ?? label}
                onClick={(e) => {
                  e.stopPropagation();
                  onJumpKnowledge(id);
                }}
              >
                {label}
              </button>
            );
          })}
          {rest > 0 && <span className="qp-chip">+{rest}</span>}
        </div>
        {q.hint && (
          <div>
            <button
              className="qp-hintbtn"
              onClick={(e) => {
                e.stopPropagation();
                setHintOpen((prev) => {
                  const next = new Set(prev);
                  if (next.has(q.qid)) next.delete(q.qid);
                  else next.add(q.qid);
                  return next;
                });
              }}
            >
              {hintOpen.has(q.qid) ? '收起提示' : '看提示'}
            </button>
            {hintOpen.has(q.qid) && <p className="qp-hinttext">{q.hint}</p>}
          </div>
        )}
        {counts.out[q.qid] > 0 && (
          <span className="qp-chip" style={{ position: 'absolute', right: -9, top: '50%', transform: 'translateY(-50%)', borderRadius: 999, padding: '1px 5px', background: '#fff' }}>
            {counts.out[q.qid]}
          </span>
        )}
      </div>
    );
  };

  return (
    <div className="qp-wrap">
      <style>{STYLE}</style>
      <div className="qp-bar">
        <label>搜索问题 <input value={query} onChange={(event) => {
          setQuery(event.target.value);
          setSelected(null);
          setHover(null);
        }} placeholder="问题编号或关键词" /></label>
        <label>按案例看前置 <select value={caseFilter} onChange={(event) => {
          setCaseFilter(event.target.value);
          setQuery('');
          setSelected(null);
          setHover(null);
        }}>
          <option value="">全部问题</option>
          {cases?.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}
        </select></label>
        <span className="spacer" />
        <span>{visible.size} / {full.questions.length} 个问题 · {edges.filter((edge) => visible.has(edge.source) && visible.has(edge.target)).length} 条可见关系</span>
      </div>
      <div className="qp-scroll">
        {visible.size === 0 && <p role="status">没有匹配的问题。</p>}
        <div className="qp-board" ref={boardRef}>
          <svg className="qp-svg" aria-hidden="true">
            <defs>
              {Object.entries(REL_COLOR).map(([rel, color]) => (
                <marker key={rel} id={`qp-arrow-${rel}`} viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto">
                  <path d="M0 0 L8 4 L0 8 z" fill={color} />
                </marker>
              ))}
            </defs>
            {geometry.map((e) => {
              const color = REL_COLOR[e.rel] ?? REL_COLOR.prereq;
              return (
                <g key={e.key}>
                  <path
                    d={e.d}
                    fill="none"
                    stroke={color}
                    strokeWidth={e.on ? 2 : 1.1}
                    strokeDasharray={e.rel === 'contrast' ? '6 5' : undefined}
                    opacity={e.dim ? 0.1 : e.rel === 'contrast' ? 0.85 : 0.6}
                    markerEnd={`url(#qp-arrow-${e.rel in REL_COLOR ? e.rel : 'prereq'})`}
                  />
                  {e.on && (
                    <path
                      className="qp-flow"
                      d={e.d}
                      fill="none"
                      stroke="rgba(190,240,255,.95)"
                      strokeWidth={2.4}
                      strokeDasharray="6 10"
                      opacity={0.8}
                    />
                  )}
                </g>
              );
            })}
          </svg>

          {layers.map((layer) => {
            const style = LAYER_STYLE[layer.layer - 1] ?? LAYER_STYLE[0];
            return (
              <div className="qp-col" key={layer.layer}>
                <div className="qp-col-head">
                  <div className="qp-col-top" style={{ color: style.accent }}>
                    L{layer.layer} {layer.name}
                    <span className="cnt">（{layer.qs.length} 个问题）</span>
                  </div>
                  <div className="qp-col-desc">{layer.desc}</div>
                  <div className="qp-col-bar" style={{ background: style.accent }} />
                </div>
                {layer.qs.map((q, i) => renderCard(q, i))}
              </div>
            );
          })}
        </div>
      </div>

      {selectedQ && (
        <div className="qp-drawer">
          <button className="close" onClick={() => { setSelected(null); onSelectQuestion(null); }} aria-label="关闭详情">
            ✕
          </button>
          <h4>{selectedQ.question}</h4>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {selectedQ.bloom && (
              <span className="qp-bloom" style={{ color: BLOOM_COLOR[selectedQ.bloom] ?? '#475569' }}>
                {selectedQ.bloom}
              </span>
            )}
            <span className="qp-chip">L{layerOfQuestion(full, selectedQ)}</span>
            <span className="qp-chip">{(selectedQ.node_ids ?? []).length} 个知识点</span>
          </div>

          {selectedQ.hint && (
            <>
              <b className="sec">提示</b>
              <p>{selectedQ.hint}</p>
            </>
          )}
          {!!selectedQ.answer?.length && (
            <>
              <b className="sec">答案要点</b>
              <ul>
                {selectedQ.answer.map((a, i) => (
                  <li key={i}>{a}</li>
                ))}
              </ul>
            </>
          )}
          {selectedQ.blindSpot && <div className="warn">⚠ 常见错误：{selectedQ.blindSpot}</div>}

          <b className="sec">关联知识点</b>
          <div className="qp-chips">
            {(selectedQ.node_ids ?? []).map((id, i) => {
              const node = full.nodes.find((n) => n.id === id);
              return (
                <button key={id} className="qp-chip" onClick={() => onJumpKnowledge(id)}>
                  {selectedQ.kp_labels?.[i] ?? node?.label ?? id}
                </button>
              );
            })}
          </div>

          {relatedCases.length > 0 && (
            <>
              <b className="sec">工程案例</b>
              <div className="qp-chips">
                {relatedCases.map((item) => (
                  <button key={item.id} className="qp-chip" onClick={() => onJumpCase?.(item.id)}>{item.title}</button>
                ))}
              </div>
            </>
          )}
          {relatedAbilities.length > 0 && (
            <>
              <b className="sec">案例考查的能力</b>
              <div className="qp-chips">{relatedAbilities.map((item) => (
                <button key={item.id} className="qp-chip" onClick={() => onJumpAbility?.(item.id)}>{item.title}</button>
              ))}</div>
            </>
          )}
          {relatedEdges.length > 0 && (
            <>
              <b className="sec">递进依据</b>
              <ul>{relatedEdges.map((edge) => (
                <li key={`${edge.source}-${edge.target}`}>{edge.source} → {edge.target} · {edge.why}</li>
              ))}</ul>
            </>
          )}

          {selectedPath && (selectedPath.upstream.size > 0 || selectedPath.downstream.size > 0) && (
            <>
              {selectedPath.upstream.size > 0 && (
                <>
                  <b className="sec">上游问题（{selectedPath.upstream.size}）</b>
                  <div className="qp-chips">
                    {[...selectedPath.upstream].slice(0, 6).map((qid) => {
                      const q = full.questions.find((x) => x.qid === qid);
                      if (!q) return null;
                      return (
                        <button
                          key={qid}
                          className="qp-chip"
                          onClick={() => focusQuestion(qid)}
                        >
                          {q.question.length > 18 ? `${q.question.slice(0, 18)}…` : q.question}
                        </button>
                      );
                    })}
                  </div>
                </>
              )}
              {selectedPath.downstream.size > 0 && (
                <>
                  <b className="sec">下游进阶（{selectedPath.downstream.size}）</b>
                  <div className="qp-chips">
                    {[...selectedPath.downstream].slice(0, 6).map((qid) => {
                      const q = full.questions.find((x) => x.qid === qid);
                      if (!q) return null;
                      return (
                        <button
                          key={qid}
                          className="qp-chip"
                          onClick={() => focusQuestion(qid)}
                        >
                          {q.question.length > 18 ? `${q.question.slice(0, 18)}…` : q.question}
                        </button>
                      );
                    })}
                  </div>
                </>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
