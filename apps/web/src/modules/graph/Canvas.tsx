import { useEffect, useMemo, useState } from 'react';
import type { CanvasProps } from '../registry';
import type { GraphArtifactData, GraphFull, GraphNodeDetail } from '../../lib/types';
import { getGraph, getGraphNode } from '../../lib/api';
import { Icon } from '../../shell/Icons';
import { GraphLegends } from './constants';
import { Overview } from './Overview';
import { FocusView } from './FocusView';
import { Questions } from './Questions';

/**
 * graph 画布（三种形态）：
 *  - 知识图谱 · 全览星图：中心课程核心 + 9 章星系 + 169 节点（模块导航直接进入时）
 *  - 知识图谱 · 焦点关系：中心 focus + 邻居分环（chat artifact 直接进入；或点节点后）
 *  - 问题图谱：三层递进问题列（11 / 8 / 7），点知识点 chip 跳回焦点
 */
export function GraphCanvas({ artifact, onAsk }: CanvasProps) {
  const base = (artifact.data || {}) as GraphArtifactData;
  const artifactFocus = base.focus?.id ? base.focus : null;

  const [full, setFull] = useState<GraphFull | null>(null);
  const [fullError, setFullError] = useState<string | null>(null);
  const [mode, setMode] = useState<'knowledge' | 'questions'>('knowledge');
  const [view, setView] = useState<'overview' | 'focus'>(artifactFocus ? 'focus' : 'overview');
  const [detail, setDetail] = useState<GraphNodeDetail | null>(() =>
    artifactFocus
      ? {
          node: artifactFocus,
          neighbors: Array.isArray(base.neighbors) ? base.neighbors : [],
          prereq: Array.isArray(base.prereq) ? base.prereq : [],
        }
      : null,
  );
  const [focusId, setFocusId] = useState<string | null>(artifactFocus?.id ?? null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 新 artifact：有 focus 直接进焦点关系，没有就进全览
  useEffect(() => {
    const d = (artifact.data || {}) as GraphArtifactData;
    if (d.focus?.id) {
      setDetail({
        node: d.focus,
        neighbors: Array.isArray(d.neighbors) ? d.neighbors : [],
        prereq: Array.isArray(d.prereq) ? d.prereq : [],
      });
      setFocusId(d.focus.id);
      setView('focus');
      setMode('knowledge');
      setError(null);
    } else {
      setDetail(null);
      setFocusId(null);
      setView('overview');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [artifact.receivedAt]);

  // 全课程星图 / 问题图谱数据：模块级缓存只拉一次
  useEffect(() => {
    let alive = true;
    getGraph()
      .then((g) => {
        if (alive) setFull(g);
      })
      .catch((err) => {
        if (alive) setFullError((err as Error)?.message || String(err));
      });
    return () => {
      alive = false;
    };
  }, []);

  async function focusNode(id: string) {
    if (!id || loading) return;
    setLoading(true);
    setError(null);
    try {
      const next = await getGraphNode(id);
      if (next && next.node) {
        setDetail(next);
        setFocusId(next.node.id);
        setView('focus');
        setMode('knowledge');
      }
    } catch (err) {
      setError(`切换焦点失败：${(err as Error)?.message || String(err)}`);
    } finally {
      setLoading(false);
    }
  }

  const stats = full?.stats;
  const counts = useMemo(
    () => ({
      nodes: stats?.nodes ?? full?.nodes.length ?? 0,
      edges: stats?.edges ?? full?.edges.length ?? 0,
      questions: stats?.questions ?? full?.questions.length ?? 0,
      chapters: stats?.chapters ?? full?.chapters?.length ?? 0,
    }),
    [stats, full],
  );

  return (
    <div className="canvas-body kg-body">
      <div className="kg-modetabs" role="tablist" aria-label="图谱模式">
        <button
          type="button"
          role="tab"
          aria-selected={mode === 'knowledge'}
          className={`kg-modetab ${mode === 'knowledge' ? 'is-active' : ''}`}
          onClick={() => setMode('knowledge')}
        >
          <Icon name="graph" size={14} />
          知识图谱
          <span className="kg-modetab-count">{counts.nodes || '—'}</span>
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={mode === 'questions'}
          className={`kg-modetab ${mode === 'questions' ? 'is-active' : ''}`}
          onClick={() => setMode('questions')}
        >
          <Icon name="book" size={14} />
          问题图谱
          <span className="kg-modetab-count">{counts.questions || '—'}</span>
        </button>
      </div>

      {mode === 'knowledge' ? (
        <>
          <div className="kg-stats">
            <span className="kg-stat">
              <b>{counts.nodes || '—'}</b> 知识点
            </span>
            <span className="kg-stat">
              <b>{counts.edges || '—'}</b> 关系
            </span>
            <span className="kg-stat">
              <b>{counts.questions || '—'}</b> 课程问题
            </span>
            <span className="kg-stat">
              <b>{counts.chapters || '—'}</b> 章
            </span>
            <span className="kg-hint">{view === 'overview' ? '全览星图' : '焦点关系'}</span>
          </div>

          {detail && (
            <div className="kg-viewswitch" role="group" aria-label="知识图谱视图">
              <button
                type="button"
                className={view === 'overview' ? 'is-active' : ''}
                onClick={() => setView('overview')}
              >
                全览星图
              </button>
              <button
                type="button"
                className={view === 'focus' ? 'is-active' : ''}
                onClick={() => setView('focus')}
              >
                焦点关系
              </button>
            </div>
          )}

          {view === 'overview' ? (
            <Overview
              full={full}
              fullError={fullError}
              focusId={focusId ?? undefined}
              onFocus={(id) => void focusNode(id)}
            />
          ) : detail ? (
            <FocusView
              detail={detail}
              full={full}
              loading={loading}
              error={error}
              onFocus={(id) => void focusNode(id)}
              onAsk={onAsk}
              onBackToOverview={() => setView('overview')}
            />
          ) : (
            <div className="kg-star-state">
              <Icon name="graph" size={18} />
              <p>还没有焦点数据：在「全览星图」里点一个知识点即可查看它的关系。</p>
              <button className="btn btn-ghost btn-xs" type="button" onClick={() => setView('overview')}>
                去全览星图
              </button>
            </div>
          )}

          <GraphLegends />
        </>
      ) : (
        <Questions full={full} fullError={fullError} onPickNode={(id) => void focusNode(id)} />
      )}
    </div>
  );
}
