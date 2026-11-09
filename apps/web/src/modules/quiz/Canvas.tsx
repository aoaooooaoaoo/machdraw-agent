import { useState } from 'react';
import type { CanvasProps } from '../registry';
import type { QuizArtifactData } from '../../lib/types';
import { addWrongbook, explainQuiz, gradeQuiz, invalidateGraphCache, reportMastery } from '../../lib/api';
import type { QuizGradeResult } from '../../lib/api';
import { useAppStore } from '../../lib/store';
import { refreshMasteryCache } from '../../lib/learner';
import { toast } from '../../lib/ui';
import { Markdown } from '../../shell/Markdown';
import { Icon } from '../../shell/Icons';

interface AssessState {
  status: 'saving' | 'done' | 'error';
  signal: 'got' | 'again';
  state?: string;
  score?: number;
  error?: string;
}

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
  const [assess, setAssess] = useState<Record<string, AssessState>>({});
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [grades, setGrades] = useState<Record<string, { status: 'saving' | 'done' | 'error'; data?: QuizGradeResult; error?: string }>>({});
  const account = useAppStore((s) => s.account);

  async function gradeAnswer(chunkId: string, q: QuizArtifactData['questions'][number]) {
    const answer = (answers[chunkId] || '').trim();
    if (!account) {
      toast('请先登录再判分', 'info');
      return;
    }
    if (!answer) {
      toast('先写下你的答案或思路', 'info');
      return;
    }
    setGrades((prev) => ({ ...prev, [chunkId]: { status: 'saving' } }));
    try {
      const data = await gradeQuiz(chunkId, answer, account);
      setGrades((prev) => ({ ...prev, [chunkId]: { status: 'done', data } }));
      setAssess((prev) => ({
        ...prev,
        [chunkId]: {
          status: 'done',
          signal: data.score >= 60 ? 'got' : 'again',
          state: data.state,
          score: data.score / 100,
        },
      }));
      invalidateGraphCache();
      void refreshMasteryCache(account);
      toast(
        data.score >= 60 ? `判分 ${data.score} 分 · 掌握度已更新` : `判分 ${data.score} 分 · 已记入错题本`,
        data.score >= 60 ? 'success' : 'info',
      );
      if (data.score < 60) {
        // 服务端已自动写错题本；这里只提示，不重复写
        void q;
      }
    } catch (err) {
      setGrades((prev) => ({
        ...prev,
        [chunkId]: { status: 'error', error: (err as Error)?.message || String(err) },
      }));
      toast('判分失败，请稍后再试', 'error');
    }
  }

  async function grade(chunkId: string, q: QuizArtifactData['questions'][number], signal: 'got' | 'again') {
    if (!account) {
      toast('请先登录再记录学习状态', 'info');
      return;
    }
    const explainText = (() => {
      const payload = explains[chunkId]?.data;
      return extractExplain(payload) ?? '';
    })();
    setAssess((prev) => ({ ...prev, [chunkId]: { status: 'saving', signal } }));
    try {
      const res = await reportMastery(
        {
          signal,
          kp_ids: q.kp_ids || [],
          chapter: q.section || '',
          chunk_id: chunkId,
          question: q.content,
          explanation: explainText,
          document_title: q.documentTitle,
        },
        account,
      );
      const item = Object.values(res.updated || {})[0];
      setAssess((prev) => ({
        ...prev,
        [chunkId]: { status: 'done', signal, state: item?.state, score: item?.score },
      }));
      invalidateGraphCache();
      if (signal === 'again') {
        await addWrongbook(
          {
            question: q.content || '',
            wrong_answer: '（自评：还不会）',
            root_cause: '自评未掌握',
            trace_ref: chunkId,
            correct: explainText,
            pitfall: '',
            kp_ids: q.kp_ids || [],
            source: q.documentTitle || '题卡自评',
          },
          account,
        );
        toast('已记入错题本 · 图谱状态更新为「需复习」', 'info');
      } else {
        toast('已记录掌握度 · 图谱状态已更新');
      }
    } catch (err) {
      setAssess((prev) => ({
        ...prev,
        [chunkId]: { status: 'error', signal, error: (err as Error)?.message || String(err) },
      }));
      toast('记录失败，请稍后再试', 'error');
    }
  }

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

              {opened && explain?.status === 'done' && (
                <div className="qz-grade">
                  <div className="qz-grade-head">
                    <span>自动判分</span>
                    <span className="qz-grade-hint">写下你的答案/思路，星火对照参考答案打分并回写掌握度</span>
                  </div>
                  <textarea
                    className="qz-grade-input"
                    rows={2}
                    placeholder="例如：控制棒微分价值是单位插入深度引起的反应性变化，积分价值是累计量…"
                    value={answers[chunkId] || ''}
                    onChange={(e) => setAnswers((prev) => ({ ...prev, [chunkId]: e.target.value }))}
                    disabled={grades[chunkId]?.status === 'saving'}
                  />
                  <div className="qz-grade-actions">
                    <button
                      className="btn btn-primary btn-xs"
                      type="button"
                      disabled={grades[chunkId]?.status === 'saving' || !(answers[chunkId] || '').trim()}
                      onClick={() => void gradeAnswer(chunkId, q)}
                    >
                      {grades[chunkId]?.status === 'saving' ? '判分中…' : '提交判分'}
                    </button>
                    {grades[chunkId]?.status === 'error' && (
                      <span className="qz-grade-error">{grades[chunkId]?.error}</span>
                    )}
                  </div>
                  {grades[chunkId]?.status === 'done' && grades[chunkId]?.data && (() => {
                    const g = grades[chunkId].data!;
                    return (
                      <div className={`qz-grade-result is-${g.score >= 60 ? 'pass' : 'fail'}`}>
                        <div className="qz-grade-score">
                          <b>{g.score}</b> / 100
                          <span className={`qz-grade-verdict is-${g.verdict}`}>
                            {g.verdict === 'pass' ? '通过' : g.verdict === 'partial' ? '部分正确' : '未通过'}
                          </span>
                        </div>
                        {g.feedback && <p className="qz-grade-feedback">{g.feedback}</p>}
                        {g.missing.length > 0 && (
                          <div className="qz-grade-missing">
                            <span>漏掉的点：</span>
                            {g.missing.map((m) => <em key={m}>{m}</em>)}
                          </div>
                        )}
                        {g.reference && (
                          <details className="qz-grade-ref">
                            <summary>对照参考答案</summary>
                            <Markdown text={g.reference} />
                          </details>
                        )}
                      </div>
                    );
                  })()}
                </div>
              )}

              {opened && explain?.status === 'done' && (
                <div className="qz-assess">
                  <span className="qz-assess-label">学完这道题，你现在：</span>
                  {(() => {
                    const a = assess[chunkId];
                    const saving = a?.status === 'saving';
                    return (
                      <>
                        <button
                          className={`qz-assess-btn is-got ${a?.status === 'done' && a.signal === 'got' ? 'is-on' : ''}`}
                          type="button"
                          disabled={saving}
                          onClick={() => void grade(chunkId, q, 'got')}
                        >
                          <Icon name="check" size={12} /> 我会了
                        </button>
                        <button
                          className={`qz-assess-btn is-again ${a?.status === 'done' && a.signal === 'again' ? 'is-on' : ''}`}
                          type="button"
                          disabled={saving}
                          onClick={() => void grade(chunkId, q, 'again')}
                        >
                          <Icon name="alert" size={12} /> 还不会
                        </button>
                        {saving && <span className="qz-assess-tip"><span className="spinner" /> 记录中…</span>}
                        {a?.status === 'done' && (
                          <span className={`qz-assess-state is-${a.state === '已掌握' ? 'got' : a.state === '需复习' ? 'again' : 'learning'}`}>
                            {a.state}
                            {typeof a.score === 'number' ? ` · ${Math.round(a.score * 100)}%` : ''}
                          </span>
                        )}
                        {a?.status === 'error' && <span className="qz-assess-tip is-error">{a.error}</span>}
                      </>
                    );
                  })()}
                </div>
              )}
            </article>
          );
        })}
      </div>
    </div>
  );
}
