import { useEffect, useRef, useState } from 'react';
import type { CanvasProps } from '../registry';
import type { ComparisonArtifactData } from '../../lib/types';
import { Markdown } from '../../shell/Markdown';
import { Icon } from '../../shell/Icons';

function PairLightbox({
  file,
  title,
  caption,
  onClose,
}: {
  file: string;
  title: string;
  caption?: string;
  onClose: () => void;
}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  return (
    <div className="fig-mask" role="dialog" aria-modal="true" aria-label={title} onClick={onClose}>
      <div className="fig-modal" onClick={(e) => e.stopPropagation()}>
        <div className="fig-modal-head">
          <div className="fig-modal-heading">
            <div className="fig-modal-title">{title}</div>
            {caption && <div className="fig-modal-chapter">{caption}</div>}
          </div>
          <button className="icon-btn" type="button" onClick={onClose} aria-label="关闭大图">
            <Icon name="x" size={18} />
          </button>
        </div>
        <div className="fig-modal-img">
          <img src={`/figures/${file}`} alt={title} />
        </div>
        <div className="fig-modal-foot">
          <span className="mono fig-modal-id">{file}</span>
          <span className="fig-modal-hint">Esc 关闭</span>
        </div>
      </div>
    </div>
  );
}

/**
 * 成对图 SVG 只做最小清洗：去脚本/foreignObject/事件属性/javascript:。
 * 图来自我们自己的后端静态资源，不是外部用户内容。
 */
function sanitizeSvg(raw: string): string {
  return raw
    .replace(/<script[\s\S]*?<\/script>/gi, '')
    .replace(/<foreignObject[\s\S]*?<\/foreignObject>/gi, '')
    .replace(/\son\w+\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)/gi, '')
    .replace(/javascript:/gi, '');
}

/** 从内联 SVG 里找出所有 data-diff 编号，判断这张图是否支持联动高亮。 */
function diffMarkIds(svgText: string | null): Set<string> {
  const ids = new Set<string>();
  if (!svgText) return ids;
  const re = /data-diff="([^"]+)"/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(svgText)) !== null) ids.add(m[1]);
  return ids;
}

/**
 * comparison 画布：成对图 + 差异点 + 做题。
 * 图以内联 SVG 渲染（后端在标号圈/数字/图例上埋了 data-diff），
 * 点差异点 n → A/B 两图里所有 data-diff="n" 的元素同时点亮。
 * 内联失败时回落到 <img>（仍可点开大图）。
 */
export function ComparisonCanvas({ artifact, demo }: CanvasProps) {
  const data = (artifact.data || {}) as ComparisonArtifactData;
  const differences = Array.isArray(data.differences) ? data.differences : [];
  const question = data.question;
  const [imageOpen, setImageOpen] = useState(false);
  const [imageFailed, setImageFailed] = useState(false);
  const [picked, setPicked] = useState<number | null>(null);
  const [svgText, setSvgText] = useState<string | null>(null);
  const [inlineFailed, setInlineFailed] = useState(false);
  const [activeDiff, setActiveDiff] = useState<number | null>(null);

  const svgHostRef = useRef<HTMLDivElement>(null);
  const markIds = diffMarkIds(svgText);
  // 只统计「差异点列表里真的有的编号」，避免把图例里的 data-diff="0" 也算成一组
  const linkedCount = differences.filter((d) => markIds.has(String(d.no))).length;
  const supportsLink = linkedCount > 0;

  const correct = picked !== null && question ? picked === question.answer_index : false;

  function choose(index: number) {
    setPicked(index);
  }

  // 换图（新 artifact）：重置答题/高亮，重新内联取图
  useEffect(() => {
    setPicked(null);
    setActiveDiff(null);
    setSvgText(null);
    setInlineFailed(false);
    if (!data.file) return;
    let cancelled = false;
    const ctrl = new AbortController();
    fetch(`/figures/${data.file}`, { signal: ctrl.signal })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.text();
      })
      .then((text) => {
        if (!cancelled) setSvgText(sanitizeSvg(text));
      })
      .catch(() => {
        if (!cancelled) setInlineFailed(true);
      });
    return () => {
      cancelled = true;
      ctrl.abort();
    };
  }, [data.file, artifact.receivedAt]);

  // 高亮同步：只改类名，不动 SVG 结构
  useEffect(() => {
    const host = svgHostRef.current;
    if (!host) return;
    host.classList.toggle('has-hot', activeDiff != null);
    host.querySelectorAll('[data-diff]').forEach((el) => el.classList.remove('is-hot'));
    if (activeDiff != null) {
      host.querySelectorAll(`[data-diff="${activeDiff}"]`).forEach((el) => el.classList.add('is-hot'));
    }
  }, [activeDiff, svgText]);

  // 点图里的标号圈也能反向选中差异点
  useEffect(() => {
    const host = svgHostRef.current;
    if (!host) return;
    const onClick = (e: MouseEvent) => {
      const target = (e.target as Element).closest?.('[data-diff]');
      if (!target) return;
      const n = Number(target.getAttribute('data-diff'));
      if (!Number.isFinite(n)) return;
      e.stopPropagation();
      setActiveDiff((prev) => (prev === n ? null : n));
    };
    host.addEventListener('click', onClick);
    return () => host.removeEventListener('click', onClick);
  }, [svgText]);

  if (!data.file) {
    return (
      <div className="canvas-body">
        <div className="canvas-empty-inline">
          <Icon name="alert" size={20} />
          <p>comparison artifact 缺少 file 字段。</p>
          <pre className="json-pre">{JSON.stringify(data, null, 2).slice(0, 1400)}</pre>
        </div>
      </div>
    );
  }

  const title = data.title || data.pair_id || '成对图辨析';

  return (
    <div className="canvas-body cmp-body">
      <div className="cmp-head">
        <div className="cmp-title">{title}</div>
        <div className="cmp-chips">
          {demo && <span className="chip chip-demo">示例</span>}
          {data.pair_id && <span className="mono chip">{data.pair_id}</span>}
        </div>
      </div>

      {/* 成对图：内联 SVG；点标号圈高亮，点空白处开大图 */}
      <div
        className="cmp-figure"
        role="button"
        tabIndex={0}
        title="点击空白处查看大图"
        onClick={(e) => {
          if ((e.target as Element).closest?.('[data-diff]')) return;
          setImageOpen(true);
        }}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') setImageOpen(true);
        }}
      >
        {svgText ? (
          <div
            className="cmp-svg-inline"
            ref={svgHostRef}
            dangerouslySetInnerHTML={{ __html: svgText }}
          />
        ) : inlineFailed || imageFailed ? (
          imageFailed ? (
            <span className="cmp-figure-fail">
              <Icon name="alert" size={14} /> 图片加载失败：{data.file}
            </span>
          ) : (
            <img src={`/figures/${data.file}`} alt={title} onError={() => setImageFailed(true)} />
          )
        ) : (
          <div className="cmp-figure-loading">
            <span className="spinner" /> 正在加载成对图…
          </div>
        )}
        <span className="ev-figure-zoom">
          <Icon name="expand" size={12} /> 放大
        </span>
      </div>

      {supportsLink && (
        <div className="cmp-link-hint">
          <Icon name="spark" size={12} />
          点下方差异点或图里的编号圈 → A/B 两图同号同时高亮（共 {linkedCount} 组标号）
        </div>
      )}

      {/* A/B 说明 */}
      {(data.a || data.b) && (
        <div className="cmp-sides">
          {[data.a, data.b].filter(Boolean).map((side) => (
            <div className="cmp-side" key={side!.label}>
              <span className={`cmp-side-label side-${side!.label.toLowerCase()}`}>{side!.label}</span>
              <div className="cmp-side-text">
                <span className="cmp-side-caption">{side!.caption}</span>
                {side!.正确性 && <span className="cmp-correct">{side!.正确性}</span>}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 差异点：可点击 → 两图同号高亮 */}
      {differences.length > 0 && (
        <div className="cmp-section">
          <div className="cmp-section-head">
            <span>差异点</span>
            <span className="cmp-section-sub">
              {supportsLink ? '点一条看两图同号高亮' : `${differences.length} 条`}
            </span>
          </div>
          <ol className="cmp-diffs">
            {differences.map((d) => {
              const active = activeDiff === d.no;
              return (
                <li
                  className={`cmp-diff ${active ? 'is-active' : ''}`}
                  key={d.no}
                  role="button"
                  tabIndex={0}
                  aria-pressed={active}
                  onClick={() => setActiveDiff((prev) => (prev === d.no ? null : d.no))}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      setActiveDiff((prev) => (prev === d.no ? null : d.no));
                    }
                  }}
                >
                  <span className="cmp-diff-no">{d.no}</span>
                  <div className="cmp-diff-body">
                    <div className="cmp-diff-name">{d.name}</div>
                    <div className="cmp-diff-ab">
                      <span>
                        <b className="cmp-tag-a">A</b> {d.a_desc}
                      </span>
                      <span>
                        <b className="cmp-tag-b">B</b> {d.b_desc}
                      </span>
                    </div>
                    {d.why && <p className="cmp-diff-why">为什么：{d.why}</p>}
                  </div>
                </li>
              );
            })}
          </ol>
        </div>
      )}

      {/* 做题区 */}
      {question && (
        <div className="cmp-quiz">
          <div className="cmp-section-head">
            <span>随堂一题</span>
            <span className="cmp-section-sub">选完立刻判对错</span>
          </div>
          <p className="cmp-quiz-stem">{question.stem}</p>
          <div className="cmp-options">
            {question.options.map((opt, i) => {
              const letter = String.fromCharCode(65 + i);
              // 只对「用户选中的那一项」判对错；不能因为选了别的项就把正确项提前标绿（泄题）
              const isRight = picked === i && i === question.answer_index;
              const isWrongPick = picked === i && i !== question.answer_index;
              return (
                <button
                  key={`${letter}-${opt}`}
                  type="button"
                  className={`cmp-option ${isRight ? 'is-correct' : ''} ${isWrongPick ? 'is-wrong' : ''}`}
                  onClick={() => choose(i)}
                >
                  <span className="cmp-option-letter">{letter}</span>
                  <span className="cmp-option-text">{opt}</span>
                  {isRight && <Icon name="check" size={14} />}
                  {isWrongPick && <Icon name="x" size={14} />}
                </button>
              );
            })}
          </div>

          {correct ? (
            <div className="cmp-feedback is-correct">
              <div className="cmp-feedback-title">
                <Icon name="check" size={14} /> 答对了
              </div>
              {question.explain && (
                <div className="cmp-feedback-explain">
                  <Markdown text={question.explain} />
                </div>
              )}
            </div>
          ) : picked !== null ? (
            <div className="cmp-feedback is-wrong">
              <div className="cmp-feedback-title">
                <Icon name="x" size={14} /> 再想想：A 是「{data.a?.caption ?? 'A'}」，B 是「
                {data.b?.caption ?? 'B'}」
              </div>
              <p className="cmp-feedback-hint">对照上方差异点，选出正确选项（可重新选择）。</p>
            </div>
          ) : null}
        </div>
      )}

      {imageOpen && (
        <PairLightbox
          file={data.file}
          title={title}
          caption={[data.a?.caption, data.b?.caption].filter(Boolean).join('  /  ')}
          onClose={() => setImageOpen(false)}
        />
      )}
    </div>
  );
}
