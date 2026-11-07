import { useState } from 'react';
import type { CanvasProps } from '../registry';
import type { QuizArtifactData } from '../../lib/types';
import { explainQuiz } from '../../lib/api';
import { Markdown } from '../../shell/Markdown';
import { Icon } from '../../shell/Icons';

interface ExplainState {
  status: 'idle' | 'loading' | 'done' | 'error';
  data?: Record<string, unknown>;
  error?: string;
}

/** 解析接口返回形状未定，按常见字段做防御式提取。 */
function extractExplain(payload: Record<string, unknown> | undefined): string | null {
  if (!payload) return null;
  for (const key of ['explain', 'explanation', 'answer', 'analysis', 'text', 'content']) {
    const v = payload[key];
    if (typeof v === 'string' && v.trim()) return v;
  }
  const inner = payload['data'];
  if (inner && typeof inner === 'object' && !Array.isArray(inner)) {
    return extractExplain(inner as Record<string, unknown>);
  }
  return null;
}

interface QuizExplainRef {
  documentTitle?: string;
  section?: string;
  chunkId?: string;
  score?: number;
}

/** POST /api/quiz/explain 已实测返回 {ok,question,section,source,explain,refs[]}。 */
function readExplainMeta(payload: Record<string, unknown> | undefined): {
  source?: string;
  section?: string;
  refs: QuizExplainRef[];
} {
  const d = payload && typeof payload === 'object' ? payload : undefined;
  return {
    source: d && typeof d.source === 'string' ? d.source : undefined,
    section: d && typeof d.section === 'string' ? d.section : undefined,
    refs: d && Array.isArray(d.refs) ? (d.refs as QuizExplainRef[]) : [],
  };
}

/**
 * quiz 画布：题卡列表（答案隔离）。
 * 每题可展开「解析」，展开时才调 POST /api/quiz/explain；接口未就绪时显示空态而不是报错崩掉。
 */
export function QuizCanvas({ artifact, demo }: CanvasProps) {
  const data = (artifact.data || {}) as QuizArtifactData;
  const questions = Array.isArray(data.questions) ? data.questions : [];
  const [open, setOpen] = useState<Record<string, boolean>>({});
  const [explains, setExplains] = useState<Record<string, ExplainState>>({});

  async function loadExplain(chunkId: string) {
    setExplains((prev) => ({ ...prev, [chunkId]: { status: 'loading' } }));
    try {
      const payload = await explainQuiz(chunkId);
      setExplains((prev) => ({ ...prev, [chunkId]: { status: 'done', data: payload } }));
    } catch (err) {
      setExplains((prev) => ({
        ...prev,
        [chunkId]: { status: 'error', error: (err as Error)?.message || String(err) },
      }));
    }
  }

  function toggle(chunkId: string) {
    const next = !open[chunkId];
    setOpen((prev) => ({ ...prev, [chunkId]: next }));
    const state = explains[chunkId];
    if (next && (!state || state.status === 'error')) void loadExplain(chunkId);
  }

  return (
    <div className="canvas-body qz-body">
      <div className="qz-head">
        <div className="qz-title">
          <Icon name="book" size={14} />
          <span>题卡</span>
          <span className="qz-count">{questions.length} 题</span>
        </div>
        <div className="qz-chips">
          {demo && <span className="chip chip-demo">示例</span>}
          {data.answer_withheld && (
            <span className="chip chip-withheld">
              <Icon name="alert" size={11} /> 答案隔离 · 先自己想
            </span>
          )}
        </div>
      </div>

      {questions.length > 0 && (
        <div className="qz-quality">
          <Icon name="alert" size={11} />
          <span>{data.quality_note ?? '题面来自扫描件 OCR，可能有错字，仅供练习'}</span>
        </div>
      )}

      {questions.length === 0 && (
        <div className="canvas-empty-inline">
          <Icon name="book" size={20} />
          <p>本轮没有题目。可以让 Agent 从题库抽一道，或换个知识点提问。</p>
        </div>
      )}

      <div className="qz-list">
        {questions.map((q, i) => {
          const chunkId = q.chunkId || `q-${i}`;
          const opened = Boolean(open[chunkId]);
          const explain = explains[chunkId];
          const text = explain?.status === 'done' ? extractExplain(explain.data) : null;
          const meta = explain?.status === 'done' ? readExplainMeta(explain.data) : null;
          return (
            <article className="qz-card" key={chunkId}>
              <div className="qz-card-head">
                <span className="qz-no">{i + 1}</span>
                <div className="qz-source">
                  <span className="qz-doc">{q.documentTitle ?? '题库'}</span>
                  {q.section && <span className="qz-section">{q.section}</span>}
                </div>
                {data.answer_withheld && <span className="qz-badge">答案暂不下发</span>}
              </div>

              <div className="qz-content">
                <Markdown text={q.content || ''} />
              </div>

              <div className="qz-meta">
                <span className="mono qz-chunk" title="chunk_id">
                  {chunkId}
                </span>
              </div>

              <div className="qz-actions">
                <button className={`qz-toggle ${opened ? 'is-open' : ''}`} type="button" onClick={() => toggle(chunkId)}>
                  <Icon name="chevron" size={12} className={opened ? 'is-open' : ''} />
                  {opened ? '收起解析' : '我先想想'}
                </button>
                {!opened && <span className="qz-action-hint">想好了再看答案解析</span>}
                {opened && <span className="qz-action-hint">答案解析</span>}
              </div>

              {opened && (
                <div className="qz-explain">
                  {explain?.status === 'loading' && (
                    <div className="qz-explain-state">
                      <span className="spinner" /> 正在获取答案解析…
                    </div>
                  )}
                  {explain?.status === 'error' && (
                    <div className="qz-explain-state is-error">
                      <Icon name="alert" size={14} />
                      <div>
                        <div className="qz-explain-error-title">解析接口尚未就绪或请求失败</div>
                        <p className="qz-explain-error-msg">{explain.error}</p>
                        <button
                          className="link-btn link-accent"
                          type="button"
                          onClick={() => void loadExplain(chunkId)}
                        >
                          <Icon name="refresh" size={12} /> 重试
                        </button>
                      </div>
                    </div>
                  )}
                  {explain?.status === 'done' &&
                    (text ? (
                      <div className="qz-explain-body">
                        <Markdown text={text} />
                        {meta && (meta.source || meta.section) && (
                          <div className="qz-explain-source">
                            {meta.source}
                            {meta.section ? ` · ${meta.section}` : ''}
                          </div>
                        )}
                        {meta && meta.refs.length > 0 && (
                          <div className="qz-refs">
                            <div className="qz-refs-label">相关出处</div>
                            <div className="qz-refs-list">
                              {meta.refs.map((r, ri) => (
                                <span
                                  className="chip chip-doc"
                                  key={r.chunkId || `ref-${ri}`}
                                  title={r.section || r.chunkId}
                                >
                                  {r.documentTitle ?? r.chunkId ?? '出处'}
                                  {typeof r.score === 'number'
                                    ? ` · ${Math.round(r.score * 100)}%`
                                    : ''}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="qz-explain-body">
                        <p className="qz-muted">接口已返回，但未识别到解析字段，原始响应：</p>
                        <pre className="json-pre">{JSON.stringify(explain.data, null, 2).slice(0, 2000)}</pre>
                      </div>
                    ))}
                </div>
              )}
            </article>
          );
        })}
      </div>
    </div>
  );
}
