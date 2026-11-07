import { Fragment, useState } from 'react';
import type { GraphFull, GraphQuestion, GraphQuestionLayer } from '../../lib/types';
import { Icon } from '../../shell/Icons';

const BLOOM_STYLE: Record<string, { color: string; bg: string; border: string }> = {
  记忆: { color: '#1d4ed8', bg: '#eff6ff', border: '#bfdbfe' },
  理解: { color: '#15803d', bg: '#f0fdf4', border: '#bbf7d0' },
  分析: { color: '#b45309', bg: '#fffbeb', border: '#fde68a' },
  应用: { color: '#6d28d9', bg: '#f5f3ff', border: '#ddd6fe' },
  综合: { color: '#b91c1c', bg: '#fef2f2', border: '#fecaca' },
};

/** 转成 React 可用的 CSSProperties。 */
function bloomStyle(bloom?: string): { color: string; backgroundColor: string; borderColor: string } {
  const s = BLOOM_STYLE[bloom ?? ''] ?? { color: '#475569', bg: '#f1f5f9', border: '#e2e8f0' };
  return { color: s.color, backgroundColor: s.bg, borderColor: s.border };
}

const LAYER_FALLBACK: Omit<GraphQuestionLayer, 'count' | 'blooms'>[] = [
  { layer: 1, name: '基础理解', desc: '概念、规则、符号怎么定义' },
  { layer: 2, name: '识图分析', desc: '给图能不能读出结构与表达方法' },
  { layer: 3, name: '综合绘图', desc: '给定条件能不能画对、能不能讲清工艺' },
];

function buildLayers(full: GraphFull): GraphQuestionLayer[] {
  if (full.question_layers && full.question_layers.length > 0) return full.question_layers;
  return LAYER_FALLBACK.map((l) => {
    const qs = full.questions.filter((q) => q.layer === l.layer);
    const blooms: Record<string, number> = {};
    for (const q of qs) if (q.bloom) blooms[q.bloom] = (blooms[q.bloom] ?? 0) + 1;
    return { ...l, count: qs.length, blooms };
  });
}

function questionsOfLayer(full: GraphFull, layer: GraphQuestionLayer): GraphQuestion[] {
  if (Array.isArray(layer.qids) && layer.qids.length > 0) {
    const byId = new Map(full.questions.map((q) => [q.qid, q]));
    return layer.qids.map((qid) => byId.get(qid)).filter((q): q is GraphQuestion => Boolean(q));
  }
  return full.questions.filter((q) => q.layer === layer.layer);
}

interface QuestionsProps {
  full: GraphFull | null;
  fullError: string | null;
  onPickNode: (id: string) => void;
}

/**
 * 问题图谱：三层递进（基础理解 → 识图分析 → 综合绘图）三列卡片。
 * 每张卡带 Bloom 认知标签、知识点 chip（点击跳回知识图谱并聚焦）、可折叠提示（默认收起）。
 */
export function Questions({ full, fullError, onPickNode }: QuestionsProps) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [hints, setHints] = useState<Record<string, boolean>>({});

  if (!full) {
    return (
      <div className="kg-star-state">
        {fullError ? (
          <>
            <Icon name="alert" size={16} />
            <p>问题图谱加载失败：{fullError}</p>
          </>
        ) : (
          <>
            <span className="spinner" /> 正在加载问题图谱…
          </>
        )}
      </div>
    );
  }

  const layers = buildLayers(full).slice(0, 3);
  const total = layers.reduce((sum, l) => sum + l.count, 0);

  function toggleHint(qid: string) {
    setHints({ ...hints, [qid]: !hints[qid] });
  }
  function toggleExpand(qid: string) {
    setExpanded({ ...expanded, [qid]: !expanded[qid] });
  }

  return (
    <>
      {/* 三层概览 */}
      <div className="qg-summary">
        {layers.map((l) => (
          <div className="qg-sum-item" key={l.layer}>
            <div className="qg-sum-head">
              <span className="qg-sum-layer">L{l.layer}</span>
              <span className="qg-sum-name">{l.name}</span>
              <b className="qg-sum-count">{l.count}</b>
              <span className="qg-sum-unit">问</span>
            </div>
            <div className="qg-sum-blooms">
              {Object.entries(l.blooms ?? {}).map(([b, n]) => (
                <span className="qg-bloom-mini" key={b} style={bloomStyle(b)}>
                  {b} {n}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="qg-summary-foot">
        共 {total} 问 · 按布鲁姆认知层级递进 · 横向滚动看三层 · 点知识点 chip 可跳回星图聚焦
      </div>

      {/* 三列 */}
      <div className="qg-board">
        {layers.map((layer, li) => {
          const qs = questionsOfLayer(full, layer);
          return (
            <Fragment key={layer.layer}>
              {li > 0 && (
                <div className="qg-arrow" aria-hidden="true">
                  <Icon name="chevron" size={14} className="qg-arrow-icon" />
                  <span>递进</span>
                </div>
              )}
              <section className="qg-col">
                <header className="qg-col-head">
                  <div className="qg-col-top">
                    <span className="qg-col-layer">L{layer.layer}</span>
                    <span className="qg-col-name">{layer.name}</span>
                    <span className="qg-col-count">{layer.count}</span>
                  </div>
                  <div className="qg-col-desc">{layer.desc}</div>
                  <div className="qg-col-blooms">
                    {Object.entries(layer.blooms ?? {}).map(([b, n]) => (
                      <span className="qg-bloom-mini" key={b} style={bloomStyle(b)}>
                        {b} {n}
                      </span>
                    ))}
                  </div>
                </header>

                <div className="qg-cards">
                  {qs.map((q) => {
                    const isExpanded = Boolean(expanded[q.qid]);
                    const hintOpen = Boolean(hints[q.qid]);
                    const long = q.question.length > 64;
                    return (
                      <article className="qg-card" key={q.qid}>
                        <div className="qg-card-head">
                          <span className="qg-qid mono">{q.qid}</span>
                          {q.bloom && (
                            <span className="qg-bloom" style={bloomStyle(q.bloom)}>
                              {q.bloom}
                            </span>
                          )}
                        </div>
                        <p className={`qg-question ${isExpanded ? 'is-open' : ''}`}>{q.question}</p>
                        {long && (
                          <button
                            className="link-btn qg-expand"
                            type="button"
                            onClick={() => toggleExpand(q.qid)}
                          >
                            <Icon name="expand" size={11} />
                            {isExpanded ? '收起' : '展开全文'}
                          </button>
                        )}

                        {Array.isArray(q.kp_labels) && q.kp_labels.length > 0 && (
                          <div className="qg-kps">
                            {q.kp_labels.map((label, i) => {
                              const nodeId = q.node_ids?.[i] ?? q.node_ids?.[0];
                              return (
                                <button
                                  key={`${q.qid}-${label}-${i}`}
                                  type="button"
                                  className="qg-kp"
                                  disabled={!nodeId}
                                  title={nodeId ? `聚焦知识点：${label}` : '该知识点暂无图谱节点'}
                                  onClick={() => nodeId && onPickNode(nodeId)}
                                >
                                  <Icon name="pin" size={10} />
                                  {label}
                                </button>
                              );
                            })}
                          </div>
                        )}

                        {q.hint && (
                          <div className={`qg-hint ${hintOpen ? 'is-open' : ''}`}>
                            <button type="button" className="qg-hint-btn" onClick={() => toggleHint(q.qid)}>
                              <Icon name={hintOpen ? 'chevron' : 'spark'} size={11} />
                              {hintOpen ? '收起提示' : '看提示'}
                            </button>
                            {hintOpen && <p className="qg-hint-text">{q.hint}</p>}
                          </div>
                        )}
                      </article>
                    );
                  })}
                  {qs.length === 0 && <div className="qg-col-empty">本层暂无问题</div>}
                </div>
              </section>
            </Fragment>
          );
        })}
      </div>
    </>
  );
}
