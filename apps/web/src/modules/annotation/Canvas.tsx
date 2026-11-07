import type { CanvasProps } from '../registry';
import type { AnnotationArtifactData, AnnotationItem } from '../../lib/types';
import { Icon } from '../../shell/Icons';

const COLOR: Record<string, string> = {
  green: '#16a34a',
  amber: '#f59e0b',
  red: '#dc2626',
};

const COLOR_CN: Record<string, string> = {
  green: '讲对',
  amber: '注意',
  red: '需纠正',
};

function barColor(item: AnnotationItem): string {
  return COLOR[item.color] ?? '#64748b';
}

/**
 * annotation 画布：费曼追问的逐句三色标注。
 * 一句话一条：左侧 4px 色条（green / amber / red）+ 标签 + 点评；
 * 顶部是轮次进度与得分；probes 是可点击的追问 chip；final=true 时显示总评。
 */
export function AnnotationCanvas({ artifact, onAsk }: CanvasProps) {
  const data = (artifact.data || {}) as AnnotationArtifactData;
  const annotations = Array.isArray(data.annotations) ? data.annotations : [];
  const probes = Array.isArray(data.probes) ? data.probes : [];
  const round = typeof data.round === 'number' ? data.round : 1;
  const final = Boolean(data.final);
  const coverage = typeof data.coverage === 'number' ? data.coverage : 0;
  const score = data.score;
  const correct = score?.correct ?? annotations.filter((a) => a.color === 'green').length;
  const scoredTotal = score?.total ?? annotations.length;

  return (
    <div className="canvas-body ann-body">
      {/* 轮次 + 进度 */}
      <div className="ann-head">
        <div className="ann-round">
          <span className="ann-round-num">第 {round} 轮</span>
          <span className="ann-round-goal">
            {final ? '已满 3 轮 · 总评' : '至少 3 轮后给总评'}
          </span>
          {final && (
            <span className="chip chip-final">
              <Icon name="check" size={11} /> 总评
            </span>
          )}
        </div>
        <div className="ann-pips" aria-label={`第 ${round} 轮，共 3 轮`}>
          {[1, 2, 3].map((i) => (
            <span
              key={i}
              className={`ann-pip ${i < round ? 'is-done' : ''} ${i === round ? 'is-current' : ''}`}
            />
          ))}
        </div>
      </div>

      {/* 得分 + 覆盖率 */}
      <div className="ann-score-row">
        <div className="ann-score">
          <span className="ann-score-num">
            {correct}
            <span className="ann-score-sep">/</span>
            {scoredTotal}
          </span>
          <span className="ann-score-label">句讲对</span>
        </div>
        <div className="ann-coverage">
          <div className="ann-coverage-head">
            <span>表述覆盖率</span>
            <span className="mono">{Math.round(coverage * 100)}%</span>
          </div>
          <div className="bar">
            <div
              className={`bar-fill ${coverage < 0.5 ? 'is-warn' : ''}`}
              style={{ width: `${Math.max(0, Math.min(100, coverage * 100))}%` }}
            />
          </div>
        </div>
      </div>

      {score?.level && (
        <div className="ann-level">
          <Icon name="mic" size={13} />
          <span>{score.level}</span>
        </div>
      )}

      {/* 逐句标注 */}
      <div className="ann-list">
        {annotations.map((item, i) => {
          const color = barColor(item);
          return (
            <div className="ann-item" key={`${i}-${item.text.slice(0, 12)}`}>
              <span className="ann-bar" style={{ background: color }} />
              <div className="ann-item-body">
                <div className="ann-item-top">
                  <span className="ann-no">{i + 1}</span>
                  <p className="ann-text">{item.text}</p>
                </div>
                <div className="ann-item-meta">
                  <span
                    className="ann-label"
                    style={{ color, background: `${color}14`, borderColor: `${color}44` }}
                  >
                    {item.label || COLOR_CN[item.color] || item.color}
                  </span>
                </div>
                {item.comment && <p className="ann-comment">{item.comment}</p>}
              </div>
            </div>
          );
        })}
        {annotations.length === 0 && (
          <div className="canvas-empty-inline">
            <Icon name="mic" size={20} />
            <p>还没有逐句标注。先用几句话把概念讲一遍，再提交给 Agent 追问。</p>
          </div>
        )}
      </div>

      {/* 继续追问 */}
      {probes.length > 0 && (
        <div className="ann-probes">
          <div className="ann-section-head">
            <span>继续追问</span>
            <span className="ann-section-sub">点一下填进输入框</span>
          </div>
          <div className="ann-probe-list">
            {probes.map((p, i) => (
              <button key={`${i}-${p.slice(0, 10)}`} type="button" className="ann-probe" onClick={() => onAsk(p)}>
                <Icon name="quote" size={12} />
                <span>{p}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* 本轮小结 / 总评 */}
      {data.summary && (
        <div className={`ann-summary ${final ? 'is-final' : ''}`}>
          {final && <div className="ann-summary-title">总评</div>}
          <p>{data.summary}</p>
        </div>
      )}
    </div>
  );
}
