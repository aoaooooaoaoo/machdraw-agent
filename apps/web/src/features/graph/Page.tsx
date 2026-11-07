import { useEffect, useMemo, useRef, useState } from 'react';
import type { CanvasProps } from '../../modules/registry';
import type { ChatMessage, GraphArtifactData, GraphFull, GraphNodeInfo } from '../../lib/types';
import { getGraph } from '../../lib/api';
import { Icon } from '../../shell/Icons';
import { MessageItem } from '../../shell/MessageItem';
import { Overview } from '../../modules/graph/Overview';
import { REL_STYLE, TIER_CN, TIER_COLOR, tierOf, stateColor } from '../../modules/graph/constants';
import { QuestionPage } from './QuestionPage';
import {
  LEVEL_CN,
  levelOf,
  prerequisitesOf,
  questionsOfNode,
  successorsOf,
  parentMap,
} from './pageData';

type Tab = 'knowledge' | 'question';

const LEVEL_TIERS: Record<number, string[]> = {
  1: ['core'],
  2: ['trackA', 'trackB'],
  3: ['branch'],
  4: ['concept'],
};

const PAGE_STYLE = `
.gp-root { height: 100%; min-height: 0; display: flex; flex-direction: column; background: #f4f7fc; color: #1e293b; position: relative; overflow: hidden; }
.gp-head { flex-shrink: 0; display: flex; align-items: center; gap: 14px; padding: 10px 18px; border-bottom: 1px solid rgba(120,150,200,.22); background: #fff; }
.gp-brand { display: flex; align-items: center; gap: 9px; min-width: 0; }
.gp-mark { width: 32px; height: 32px; border-radius: 10px; display: grid; place-items: center; flex-shrink: 0; color: #fff; background: radial-gradient(circle at 32% 28%, #38bdf8, #2563eb 58%, #1e3a8a); box-shadow: 0 0 14px rgba(37,99,235,.35); }
.gp-brand b { font-size: 14px; }
.gp-brand .sub { font-size: 10px; color: #64748b; white-space: nowrap; }
.gp-tabs { display: inline-flex; padding: 3px; gap: 3px; border-radius: 10px; background: #eef3fb; border: 1px solid rgba(120,150,200,.25); }
.gp-tabs button { border: 0; background: none; color: #64748b; border-radius: 8px; padding: 6px 16px; font-size: 12.5px; cursor: pointer; }
.gp-tabs button.on { background: #fff; color: #1d4ed8; font-weight: 700; box-shadow: 0 1px 5px rgba(15,23,42,.08); }
.gp-head-right { margin-left: auto; display: flex; align-items: center; gap: 9px; }
.gp-stat { font-size: 10.5px; color: #64748b; }
.gp-agent-btn { display: inline-flex; align-items: center; gap: 7px; padding: 7px 12px; border-radius: 9px; cursor: pointer; font-size: 12px; color: #475569; background: #f8fafc; border: 1px solid rgba(120,150,200,.3); }
.gp-agent-btn.on { color: #1d4ed8; border-color: rgba(37,99,235,.45); background: rgba(37,99,235,.08); }
.gp-agent-btn .pulse { width: 7px; height: 7px; border-radius: 50%; background: #22c55e; }
.gp-agent-btn .pulse.busy { background: #22d3ee; animation: gp-pulse 1.1s ease-in-out infinite; }
@keyframes gp-pulse { 0%,100% { opacity: .3; transform: scale(.8); } 50% { opacity: 1; transform: scale(1.15); } }
.gp-body { flex: 1; min-height: 0; display: flex; gap: 10px; padding: 10px 12px; }
.gp-main { flex: 1; min-width: 0; min-height: 0; display: flex; flex-direction: column; gap: 8px; }
.gp-filters { display: flex; flex-wrap: wrap; align-items: center; gap: 5px; padding: 6px 9px; background: #fff; border: 1px solid rgba(120,150,200,.22); border-radius: 9px; }
.gp-filters .lbl { font-size: 9.5px; color: #94a3b8; margin-right: 2px; }
.gp-filters button { border: 1px solid transparent; background: #f1f5f9; color: #475569; border-radius: 999px; font-size: 9.5px; padding: 2px 8px; cursor: pointer; }
.gp-filters button.on { background: rgba(37,99,235,.08); color: #1d4ed8; border-color: rgba(37,99,235,.3); }
.gp-filters .sep { width: 1px; height: 16px; background: rgba(120,150,200,.24); margin: 0 4px; }
.gp-overview { flex: 1; min-height: 0; display: flex; flex-direction: column; background: #fff; border: 1px solid rgba(120,150,200,.22); border-radius: 12px; padding: 8px; }
.gp-legend { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; padding: 6px 10px; background: #fff; border: 1px solid rgba(120,150,200,.2); border-radius: 9px; font-size: 9.5px; color: #64748b; }
.gp-legend b { font-size: 9.5px; color: #475569; font-weight: 700; }
.gp-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 3px; }
.gp-line { display: inline-block; width: 14px; border-top: 2px solid; margin-right: 3px; vertical-align: middle; }
.gp-detail { width: 340px; flex-shrink: 0; overflow-y: auto; background: #fff; border: 1px solid rgba(120,150,200,.25); border-radius: 12px; padding: 14px 15px; box-shadow: 0 12px 30px rgba(15,23,42,.06); }
.gp-detail h3 { margin: 0 0 6px; font-size: 15px; line-height: 1.45; color: #0f172a; }
.gp-detail .meta { display: flex; flex-wrap: wrap; gap: 5px; margin-bottom: 8px; }
.gp-pill { font-size: 9.5px; border-radius: 999px; padding: 2px 8px; background: #f1f5f9; color: #475569; border: 1px solid rgba(120,150,200,.22); }
.gp-detail p { font-size: 11.5px; line-height: 1.7; color: #334155; margin: 6px 0; }
.gp-detail .sec { display: block; margin: 14px 0 5px; font-size: 10.5px; color: #64748b; font-weight: 700; }
.gp-chips { display: flex; flex-wrap: wrap; gap: 5px; }
.gp-chip { border: 1px solid rgba(37,99,235,.24); background: rgba(37,99,235,.05); color: #1d4ed8; border-radius: 6px; padding: 2px 7px; font-size: 10px; cursor: pointer; }
.gp-chip:hover { background: rgba(37,99,235,.12); }
.gp-list { margin: 0; padding-left: 16px; }
.gp-list li { font-size: 11px; line-height: 1.65; color: #334155; margin-bottom: 3px; }
.gp-warn { padding: 7px 9px; border-radius: 7px; background: #fffbeb; border: 1px solid #fde68a; color: #b45309; font-size: 10.5px; line-height: 1.6; }
.gp-crumb { display: flex; flex-wrap: wrap; align-items: center; gap: 3px; font-size: 9.5px; color: #94a3b8; margin-bottom: 8px; }
.gp-crumb button { border: 0; background: none; padding: 0; color: #2563eb; font-size: 9.5px; cursor: pointer; }
.gp-empty { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px; color: #94a3b8; font-size: 11px; }
.gp-agent { position: absolute; right: 12px; top: 54px; bottom: 12px; width: 380px; z-index: 30; display: flex; flex-direction: column; background: #fff; border: 1px solid rgba(120,150,200,.3); border-radius: 14px; box-shadow: 0 20px 50px rgba(15,23,42,.2); overflow: hidden; }
.gp-agent-head { flex-shrink: 0; display: flex; align-items: center; gap: 8px; padding: 10px 12px; border-bottom: 1px solid rgba(120,150,200,.18); font-size: 12.5px; font-weight: 700; }
.gp-agent-head .dot { width: 7px; height: 7px; border-radius: 50%; background: #22c55e; }
.gp-agent-head .dot.busy { background: #22d3ee; animation: gp-pulse 1.1s ease-in-out infinite; }
.gp-agent-head .sub { font-size: 10px; color: #94a3b8; font-weight: 400; }
.gp-agent-head button { margin-left: auto; width: 24px; height: 24px; border-radius: 7px; border: 1px solid rgba(120,150,200,.28); background: none; color: #475569; cursor: pointer; }
.gp-agent-list { flex: 1; min-height: 0; overflow-y: auto; padding: 10px 12px; }
.gp-agent-empty { border: 1px dashed rgba(120,150,200,.35); border-radius: 10px; padding: 11px; font-size: 11px; line-height: 1.8; color: #64748b; }
.gp-agent-empty button { display: block; width: 100%; text-align: left; margin-top: 6px; padding: 5px 8px; border-radius: 7px; border: 1px solid rgba(37,99,235,.2); background: rgba(37,99,235,.05); color: #1d4ed8; font-size: 10.5px; cursor: pointer; }
.gp-agent-input { flex-shrink: 0; border-top: 1px solid rgba(120,150,200,.2); padding: 9px 11px; }
.gp-agent-input .row { display: flex; gap: 7px; }
.gp-agent-input input { flex: 1; min-width: 0; padding: 8px 11px; border-radius: 9px; border: 1px solid rgba(120,150,200,.3); background: #f8fafc; font: inherit; font-size: 12px; outline: none; }
.gp-agent-input button { padding: 0 14px; border-radius: 9px; border: 1px solid rgba(37,99,235,.35); background: rgba(37,99,235,.08); color: #1d4ed8; font-size: 12px; cursor: pointer; }
.gp-agent-input button:disabled { opacity: .45; cursor: default; }
.gp-float { position: absolute; right: 16px; bottom: 16px; z-index: 25; display: inline-flex; align-items: center; gap: 7px; padding: 8px 13px; border-radius: 999px; background: #0f172a; color: #fff; font-size: 11.5px; box-shadow: 0 10px 26px rgba(15,23,42,.3); }
.gp-float .pulse { width: 7px; height: 7px; border-radius: 50%; background: #22d3ee; animation: gp-pulse 1.1s ease-in-out infinite; }
`;

export function GraphPage({ artifact, onSendMessage = () => {}, messages = [], busy = false }: CanvasProps) {
  const [full, setFull] = useState<GraphFull | null>(null);
  const [fullError, setFullError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>('knowledge');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [qFocus, setQFocus] = useState<string | null>(null);
  const [hiddenLevelIds, setHiddenLevelIds] = useState<Set<number>>(new Set());
  const [hiddenSectorIds, setHiddenSectorIds] = useState<Set<number>>(new Set());
  const [agentOpen, setAgentOpen] = useState(false);

  useEffect(() => {
    let alive = true;
    getGraph()
      .then((data) => {
        if (alive) setFull(data);
      })
      .catch((err) => {
        if (alive) setFullError((err as Error)?.message || String(err));
      });
    return () => {
      alive = false;
    };
  }, []);

  // chat 下发 graph artifact：{mode, focus} 或旧的 focus 对象 → 切 tab 并聚焦
  useEffect(() => {
    const data = (artifact?.data ?? {}) as GraphArtifactData;
    if (!data || !data.focus) return;
    const mode = data.mode === 'question' ? 'question' : 'knowledge';
    setTab(mode);
    if (mode === 'question') setQFocus(data.focus.id);
    else setSelectedId(data.focus.id);
  }, [artifact?.receivedAt]);

  const hiddenLevels = useMemo(() => {
    const set = new Set<string>();
    for (const level of hiddenLevelIds) for (const tier of LEVEL_TIERS[level] ?? []) set.add(tier);
    return set;
  }, [hiddenLevelIds]);

  const hiddenSectors = hiddenSectorIds;

  const chapters = useMemo(() => {
    if (full?.sectors?.length) {
      return full.sectors.map((s, i) => ({ index: s.sector ?? i, label: s.chapter, count: s.count }));
    }
    return (full?.chapters ?? []).map((c, i) => ({ index: i, label: c.chapter, count: c.count }));
  }, [full]);

  const levelCounts = useMemo(() => {
    const out: Record<number, number> = { 1: 0, 2: 0, 3: 0, 4: 0 };
    for (const n of full?.nodes ?? []) out[levelOf(n)] = (out[levelOf(n)] ?? 0) + 1;
    return out;
  }, [full]);

  const selectedNode = useMemo(
    () => full?.nodes.find((n) => n.id === selectedId) ?? null,
    [full, selectedId],
  );
  const parents = useMemo(() => (full ? parentMap(full) : new Map<string, string>()), [full]);
  const breadcrumb = useMemo(() => {
    if (!full || !selectedNode) return [] as GraphNodeInfo[];
    const chain: GraphNodeInfo[] = [];
    let cur: GraphNodeInfo | undefined = selectedNode;
    const seen = new Set<string>();
    while (cur && !seen.has(cur.id) && chain.length < 6) {
      seen.add(cur.id);
      chain.unshift(cur);
      const pid: string | null | undefined = cur.parent ?? parents.get(cur.id);
      cur = pid ? full.nodes.find((n) => n.id === pid) : undefined;
    }
    return chain;
  }, [full, selectedNode, parents]);

  const prereq = useMemo(() => (full && selectedNode ? prerequisitesOf(full, selectedNode.id) : []), [full, selectedNode]);
  const successors = useMemo(() => (full && selectedNode ? successorsOf(full, selectedNode.id) : []), [full, selectedNode]);
  const relatedQuestions = useMemo(
    () => (full && selectedNode ? questionsOfNode(full, selectedNode) : []),
    [full, selectedNode],
  );

  const toggleLevel = (level: number) => {
    setHiddenLevelIds((prev) => {
      const next = new Set(prev);
      if (next.has(level)) next.delete(level);
      else next.add(level);
      return next;
    });
  };
  const toggleSector = (index: number) => {
    setHiddenSectorIds((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  };

  const jumpToQuestion = (qid: string) => {
    setTab('question');
    setQFocus(qid);
  };
  const jumpToKnowledge = (kid: string) => {
    setTab('knowledge');
    setSelectedId(kid);
  };

  const stats = full?.stats;

  return (
    <div className="gp-root">
      <style>{PAGE_STYLE}</style>

      <header className="gp-head">
        <div className="gp-brand">
          <span className="gp-mark">✦</span>
          <div style={{ minWidth: 0 }}>
            <b>课程图谱</b>
            <div className="sub">
              {stats?.nodes ?? full?.nodes.length ?? '—'} 个知识点 · {stats?.edges ?? full?.edges.length ?? '—'} 条关系 ·{' '}
              {stats?.questions ?? full?.questions.length ?? '—'} 个课程问题 · {chapters.length} 章
            </div>
          </div>
        </div>
        <div className="gp-tabs" role="tablist" aria-label="课程图谱视图">
          <button role="tab" aria-selected={tab === 'knowledge'} className={tab === 'knowledge' ? 'on' : ''} onClick={() => setTab('knowledge')}>
            知识图谱
          </button>
          <button role="tab" aria-selected={tab === 'question'} className={tab === 'question' ? 'on' : ''} onClick={() => setTab('question')}>
            问题图谱
          </button>
        </div>
        <div className="gp-head-right">
          <span className="gp-stat">左栏可切模块 · 画布模式在其他模块仍可用</span>
          <button className={`gp-agent-btn${agentOpen ? ' on' : ''}`} onClick={() => setAgentOpen((v) => !v)}>
            <span className={`pulse${busy ? ' busy' : ''}`} />
            {agentOpen ? '收起问答' : 'Agent 问答'}
          </button>
        </div>
      </header>

      {tab === 'knowledge' ? (
        <div className="gp-body">
          <div className="gp-main">
            <div className="gp-filters">
              <span className="lbl">层级</span>
              {[1, 2, 3, 4].map((level) => (
                <button key={level} className={hiddenLevelIds.has(level) ? '' : 'on'} onClick={() => toggleLevel(level)}>
                  L{level} {LEVEL_CN[level]}（{levelCounts[level] ?? 0}）
                </button>
              ))}
              <span className="sep" />
              <span className="lbl">章</span>
              {chapters.map((c) => (
                <button key={c.index} className={hiddenSectorIds.has(c.index) ? '' : 'on'} onClick={() => toggleSector(c.index)} title={c.label}>
                  {c.label.replace(/^第[一二三四五六七八九十]+章\s*/, '').slice(0, 8)}（{c.count}）
                </button>
              ))}
            </div>
            <div className="gp-overview">
              <Overview
                full={full}
                fullError={fullError}
                externalSelectedId={selectedId}
                onSelect={setSelectedId}
                onFocus={() => {}}
                hiddenLevels={hiddenLevels}
                hiddenSectors={hiddenSectors}
                denseLabels
                fillHeight
              />
            </div>
            <div className="gp-legend">
              <b>层级</b>
              {[1, 2, 3, 4].map((level) => {
                const tier = LEVEL_TIERS[level][0];
                return (
                  <span key={level}>
                    <i className="gp-dot" style={{ background: TIER_COLOR[tier] }} /> L{level} {LEVEL_CN[level]}
                  </span>
                );
              })}
              <span className="sep" />
              <b>关系</b>
              {(['prereq', 'contrast', 'compose', 'cause'] as const).map((rel) => (
                <span key={rel}>
                  <i
                    className="gp-line"
                    style={{
                      borderTopColor: REL_STYLE[rel].stroke,
                      borderTopStyle: rel === 'contrast' || rel === 'compose' ? 'dashed' : 'solid',
                    }}
                  />
                  {rel === 'prereq' ? '前置' : rel === 'contrast' ? '易混淆' : rel === 'compose' ? '组成' : '导致'}
                </span>
              ))}
              <span style={{ marginLeft: 'auto', color: '#94a3b8' }}>滚轮缩放 · 拖拽平移 · 点节点看详情 · 点空白/再点一次回全景</span>
            </div>
          </div>

          {selectedNode && (
            <aside className="gp-detail">
              {breadcrumb.length > 1 && (
                <div className="gp-crumb">
                  {breadcrumb.map((n, i) => (
                    <span key={n.id} style={{ display: 'inline-flex', alignItems: 'center', gap: 3 }}>
                      {i > 0 && <span>›</span>}
                      <button onClick={() => setSelectedId(n.id)}>{n.label.length > 12 ? `${n.label.slice(0, 12)}…` : n.label}</button>
                    </span>
                  ))}
                </div>
              )}
              <h3>{selectedNode.label}</h3>
              <div className="meta">
                <span className="gp-pill">L{levelOf(selectedNode)} {LEVEL_CN[levelOf(selectedNode)]}</span>
                <span className="gp-pill">{TIER_CN[tierOf(selectedNode)] ?? selectedNode.tier}</span>
                <span className="gp-pill">{selectedNode.chapter ?? '—'}</span>
                <span className="gp-pill" style={{ color: stateColor(selectedNode.state) }}>
                  {selectedNode.state ?? '未学'}
                </span>
              </div>
              {selectedNode.kp_id && <div className="gp-stat mono">{selectedNode.kp_id}</div>}
              {selectedNode.desc && <p>{selectedNode.desc}</p>}

              {!!selectedNode.points?.length && (
                <>
                  <b className="sec">要点</b>
                  <ul className="gp-list">
                    {selectedNode.points.map((p, i) => (
                      <li key={i}>{p}</li>
                    ))}
                  </ul>
                </>
              )}

              {!!prereq.length && (
                <>
                  <b className="sec">前置知识（{prereq.length}）</b>
                  <div className="gp-chips">
                    {prereq.map((n) => (
                      <button key={n.id} className="gp-chip" title={n.note} onClick={() => setSelectedId(n.id)}>
                        {n.label}
                      </button>
                    ))}
                  </div>
                </>
              )}
              {!!successors.length && (
                <>
                  <b className="sec">后继知识（{successors.length}）</b>
                  <div className="gp-chips">
                    {successors.map((n) => (
                      <button key={n.id} className="gp-chip" title={n.note} onClick={() => setSelectedId(n.id)}>
                        {n.label}
                      </button>
                    ))}
                  </div>
                </>
              )}
              {!!relatedQuestions.length && (
                <>
                  <b className="sec">关联课程问题（{relatedQuestions.length}）</b>
                  <div className="gp-chips">
                    {relatedQuestions.map((q) => (
                      <button key={q.qid} className="gp-chip" onClick={() => jumpToQuestion(q.qid)}>
                        {q.question.length > 24 ? `${q.question.slice(0, 24)}…` : q.question}
                      </button>
                    ))}
                  </div>
                </>
              )}
              {!!selectedNode.commonMistakes?.length && (
                <>
                  <b className="sec">易错点</b>
                  <div className="gp-warn">
                    {selectedNode.commonMistakes.map((m, i) => (
                      <div key={i}>· {m}</div>
                    ))}
                  </div>
                </>
              )}
              {!!selectedNode.refs?.length && (
                <>
                  <b className="sec">课程出处</b>
                  <p>{selectedNode.refs.join('；')}</p>
                </>
              )}
              {selectedNode.section && <div className="gp-stat">章节：{selectedNode.section}</div>}
              <div className="gp-chips" style={{ marginTop: 12 }}>
                <button className="gp-chip" onClick={() => setSelectedId(null)}>
                  关闭详情（回全景）
                </button>
              </div>
            </aside>
          )}
        </div>
      ) : (
        <div className="gp-body">
          {full ? (
            <div className="gp-main">
              <QuestionPage
                full={full}
                focusId={qFocus}
                onSelectQuestion={setQFocus}
                onJumpKnowledge={jumpToKnowledge}
              />
            </div>
          ) : (
            <div className="gp-empty">{fullError ? `图谱加载失败：${fullError}` : '正在加载问题图谱…'}</div>
          )}
        </div>
      )}

      {agentOpen && (
        <AgentDrawer
          messages={messages}
          busy={busy}
          onSend={onSendMessage}
          onClose={() => setAgentOpen(false)}
        />
      )}
      {busy && !agentOpen && (
        <button className="gp-float" onClick={() => setAgentOpen(true)}>
          <span className="pulse" /> Agent 正在回答，点击查看
        </button>
      )}
      {!full && (
        <div className="gp-empty" style={{ position: 'absolute', inset: '60px 0 0', pointerEvents: 'none' }}>
          {fullError ? `图谱加载失败：${fullError}` : '正在加载全课程星图…'}
        </div>
      )}
    </div>
  );
}

function AgentDrawer({
  messages,
  busy,
  onSend,
  onClose,
}: {
  messages: ChatMessage[];
  busy: boolean;
  onSend: (text: string) => void;
  onClose: () => void;
}) {
  const [text, setText] = useState('');
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = listRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages]);

  const submit = () => {
    const trimmed = text.trim();
    if (!trimmed || busy) return;
    onSend(trimmed);
    setText('');
  };

  return (
    <aside className="gp-agent">
      <div className="gp-agent-head">
        <span className={`dot${busy ? ' busy' : ''}`} />
        Agent 问答
        <span className="sub">{busy ? '正在回答…' : '与图谱联动'}</span>
        <button onClick={onClose} title="收起问答">✕</button>
      </div>
      <div className="gp-agent-list" ref={listRef}>
        {messages.length === 0 && (
          <div className="gp-agent-empty">
            在这里提问，Agent 的回答与工具调用会显示出来。试试：
            <button onClick={() => onSend('剖视图依赖哪些前置知识？请给出课程出处')}>剖视图依赖哪些前置知识</button>
            <button onClick={() => onSend('问题图谱里 Q-004 到 Q-021 这条链在讲什么？')}>问题链 Q-004→Q-021 讲什么</button>
            <button onClick={() => onSend('半剖视图和局部剖视图有什么区别？')}>半剖 vs 局部剖</button>
          </div>
        )}
        {messages.map((m) => (
          <MessageItem key={m.id} message={m} />
        ))}
      </div>
      <div className="gp-agent-input">
        <div className="row">
          <input
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.nativeEvent.isComposing) submit();
            }}
            placeholder={busy ? 'Agent 正在回答…' : '问点什么…（Enter 发送）'}
            disabled={busy}
          />
          <button onClick={submit} disabled={busy || !text.trim()}>
            发送
          </button>
        </div>
      </div>
    </aside>
  );
}
