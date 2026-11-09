import { useState } from 'react';
import type { CanvasProps } from '../registry';
import type { WrongbookArtifactData, WrongbookTrace } from '../../lib/types';
import { addWrongbook, getWrongbook, type WrongbookPayload } from '../../lib/api';
import { useAppStore } from '../../lib/store';
import { Markdown } from '../../shell/Markdown';
import { Icon } from '../../shell/Icons';

function TraceCard({ trace, onAsk }: { trace: WrongbookTrace; onAsk: (t: string) => void }) {
  const [open, setOpen] = useState(false);
  const score = Math.max(0, Math.min(100, Math.round((trace.score || 0) * 100)));
  return (
    <div className="wb-trace">
      <div className="wb-trace-head">
        <span className="wb-trace-ref">{trace.ref}</span>
        <span className="wb-trace-score mono">{score}%</span>
      </div>
      <div className="wb-trace-id mono">{trace.chunk_id}</div>
      <div className={`wb-trace-text ${open ? 'is-open' : ''}`}>
        <p>{trace.text}</p>
      </div>
      <div className="wb-trace-foot">
        <button className="link-btn" type="button" onClick={() => setOpen((v) => !v)}>
          <Icon name="expand" size={12} />
          {open ? '收起原文' : '展开原文'}
        </button>
        <button
          className="link-btn link-accent"
          type="button"
          onClick={() => onAsk(`围绕出处《${trace.ref}》（${trace.chunk_id}）继续追问：`)}
        >
          <Icon name="quote" size={12} />
          围绕出处追问
        </button>
      </div>
    </div>
  );
}

/** 步骤里"溯源"和"避坑"要特殊渲染，其余步骤按 Markdown 正文。 */
function isTraceStep(key: string): boolean {
  return key.includes('溯源');
}
function isPitfallStep(key: string): boolean {
  return key.includes('避坑');
}

function formatTime(value: unknown): string {
  if (typeof value !== 'number') return '';
  const d = new Date(value * 1000);
  if (Number.isNaN(d.getTime())) return '';
  return d.toLocaleString('zh-CN', {
    hour12: false,
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/**
 * wrongbook 画布：六步诊改 + 写入错题本 + 错题本列表入口。
 * 根因用 6 选 1 的 chip 高亮；溯源是带 chunk_id 与相关度的可展开出处卡。
 */
export function WrongbookCanvas({ artifact, onAsk }: CanvasProps) {
  const data = (artifact.data || {}) as WrongbookArtifactData;
  const steps = Array.isArray(data.steps) ? [...data.steps].sort((a, b) => a.n - b.n) : [];
  const trace = Array.isArray(data.trace) ? data.trace : [];
  const pitfalls = Array.isArray(data.pitfalls) ? data.pitfalls : [];
  const rootCauses = Array.isArray(data.root_causes_all) ? data.root_causes_all : [];
  const coverage = typeof data.coverage === 'number' ? data.coverage : null;
  const gated = Boolean(data.gated);

  const account = useAppStore((s) => s.account) ?? 'anonymous';

  const [saving, setSaving] = useState(false);
  const [addedId, setAddedId] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [listOpen, setListOpen] = useState(false);
  const [listLoading, setListLoading] = useState(false);
  const [listError, setListError] = useState<string | null>(null);
  const [items, setItems] = useState<Record<string, unknown>[]>([]);

  function buildPayload(): WrongbookPayload {
    const correct = steps.find((s) => s.key.includes('正解'))?.value ?? '';
    const pitfall =
      pitfalls.length > 0
        ? pitfalls.join('；')
        : steps.find((s) => s.key.includes('避坑'))?.value ?? '';
    return {
      question: data.question || '',
      wrong_answer: data.wrong_answer || '（未提供，按典型错误推断）',
      root_cause: data.root_cause || '',
      trace_ref: trace[0]?.ref ?? '',
      correct,
      pitfall,
      kp_ids: Array.isArray(data.kp_ids) ? data.kp_ids : [],
      source: data.source || 'wrongbook_canvas',
    };
  }

  async function saveWrongbook() {
    if (saving || addedId) return;
    setSaving(true);
    setSaveError(null);
    try {
      const res = await addWrongbook(buildPayload(), account);
      setAddedId(res.id || 'ok');
      if (listOpen) void loadList();
    } catch (err) {
      setSaveError(`加入错题本失败：${(err as Error)?.message || String(err)}`);
    } finally {
      setSaving(false);
    }
  }

  async function loadList() {
    setListLoading(true);
    setListError(null);
    try {
      const res = await getWrongbook(account);
      setItems(Array.isArray(res.items) ? res.items : []);
    } catch (err) {
      setListError(`读取错题本失败：${(err as Error)?.message || String(err)}`);
    } finally {
      setListLoading(false);
    }
  }

  function toggleList() {
    const next = !listOpen;
    setListOpen(next);
    if (next) void loadList();
  }

  return (
    <div className="canvas-body wb-body">
      {/* 原题 */}
      <div className={`wb-question ${gated ? 'is-gated' : ''}`}>
        <div className="wb-question-label">
          <Icon name="alert" size={13} />
          原题
        </div>
        <p className="wb-question-text">{data.question || '（未提供原题）'}</p>
        <div className="wb-question-meta">
          {coverage != null && (
            <span className="wb-coverage">
              知识库覆盖率 <b>{Math.round(coverage * 100)}%</b>
            </span>
          )}
          {gated && <span className="chip chip-demo">低于门限 · 不代为补充</span>}
        </div>
      </div>

      {/* 根因 6 选 1 */}
      {rootCauses.length > 0 && (
        <div className="wb-root">
          <div className="wb-section-head">
            <span>根因归类</span>
            <span className="wb-section-sub">六选一</span>
          </div>
          <div className="wb-root-list">
            {rootCauses.map((r) => (
              <span
                key={r}
                className={`wb-root-chip ${r === data.root_cause ? 'is-active' : ''}`}
              >
                {r === data.root_cause && <Icon name="check" size={11} />}
                {r}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* 写错题本 + 列表入口 */}
      <div className="wb-actions">
        <button
          className="btn btn-primary btn-xs"
          type="button"
          disabled={saving || Boolean(addedId)}
          onClick={() => void saveWrongbook()}
        >
          <Icon name={addedId ? 'check' : 'pin'} size={13} />
          {addedId ? `已加入错题本 · ${addedId}` : saving ? '正在加入…' : '加入错题本'}
        </button>
        <button className="btn btn-ghost btn-xs" type="button" onClick={toggleList}>
          <Icon name="book" size={13} />
          {listOpen ? '收起错题本' : '查看错题本'}
        </button>
        <span className="wb-actions-hint">记录到当前账号：{account}</span>
      </div>

      {saveError && (
        <div className="wb-error">
          <Icon name="alert" size={13} />
          {saveError}
        </div>
      )}

      {listOpen && (
        <div className="wb-list">
          <div className="wb-section-head">
            <span>我的错题本</span>
            <span className="wb-section-sub">
              {listLoading ? '读取中…' : `${items.length} 条`}
            </span>
          </div>
          {listLoading && (
            <div className="wb-list-state">
              <span className="spinner" /> 正在读取…
            </div>
          )}
          {listError && (
            <div className="wb-list-state is-error">
              <Icon name="alert" size={13} />
              <span>{listError}</span>
              <button className="link-btn link-accent" type="button" onClick={() => void loadList()}>
                <Icon name="refresh" size={12} /> 重试
              </button>
            </div>
          )}
          {!listLoading && !listError && items.length === 0 && (
            <div className="wb-list-state">错题本还是空的。</div>
          )}
          {!listLoading &&
            !listError &&
            items.slice(0, 10).map((item, idx) => {
              const id = String(item.id ?? `item-${idx}`);
              const q = String(item.question ?? '（无题干）');
              const root = typeof item.root_cause === 'string' ? item.root_cause : '';
              const source = typeof item.source === 'string' ? item.source : '';
              return (
                <div className="wb-list-item" key={id}>
                  <div className="wb-list-q">{q}</div>
                  <div className="wb-list-meta">
                    {root && <span className="chip chip-cat">{root}</span>}
                    {source && <span className="chip">{source}</span>}
                    <span className="wb-list-time">{formatTime(item.created_at)}</span>
                    <span className="mono wb-list-id">{id}</span>
                  </div>
                </div>
              );
            })}
        </div>
      )}

      {/* 六步 */}
      <div className="wb-steps">
        {steps.map((step) => {
          const showTrace = isTraceStep(step.key);
          const showPitfalls = isPitfallStep(step.key) && pitfalls.length > 0;
          return (
            <div className="wb-step" key={`${step.n}-${step.key}`}>
              <div className="wb-step-rail">
                <span className="wb-step-no">{step.n}</span>
                <span className="wb-step-line" />
              </div>
              <div className="wb-step-body">
                <div className="wb-step-title">{step.key}</div>

                {showTrace ? (
                  <div className="wb-trace-list">
                    {trace.length === 0 && <p className="wb-muted">{step.value}</p>}
                    {trace.map((t) => (
                      <TraceCard key={t.chunk_id} trace={t} onAsk={onAsk} />
                    ))}
                  </div>
                ) : showPitfalls ? (
                  <ul className="wb-pitfalls">
                    {pitfalls.map((p, i) => (
                      <li key={`${i}-${p.slice(0, 8)}`}>
                        <Markdown text={p} />
                      </li>
                    ))}
                  </ul>
                ) : (
                  <div className="wb-step-value">
                    <Markdown text={step.value || '—'} />
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* 收尾说明 */}
      {data.note && (
        <div className={`wb-note ${gated ? 'is-warn' : ''}`}>
          <Icon name={gated ? 'alert' : 'book'} size={13} />
          <p>{data.note}</p>
        </div>
      )}
    </div>
  );
}
