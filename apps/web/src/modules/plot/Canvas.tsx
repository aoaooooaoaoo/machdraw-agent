import { useEffect, useId, useMemo, useState } from 'react';
import type { CanvasProps } from '../registry';
import type { PlotData } from '../../lib/types';
import { buildPlotGeometry, type PlotGeometry } from './chart';
import { Icon } from '../../shell/Icons';

/* ---------------------------------------------------------------- SVG 折线图 */

function PlotChart({
  data,
  geo,
  variant = 'inline',
}: {
  data: PlotData;
  geo: PlotGeometry;
  variant?: 'inline' | 'modal';
}) {
  const uid = useId().replace(/[^a-zA-Z0-9_-]/g, '');
  const clipId = `plotclip-${uid}`;
  const { plot } = geo;
  const width = geo.width;
  const height = geo.height;
  const xLabel = data.x_label ?? 'x';
  const yLabel = data.y_label ?? 'y';

  return (
    <svg
      className="plot-svg"
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="xMidYMid meet"
      role="img"
      aria-label={data.title ?? '曲线图'}
      style={
        variant === 'modal'
          ? { display: 'block', width: '100%', maxWidth: `${Math.round(width * 2)}px`, height: 'auto', margin: '0 auto' }
          : { display: 'block', width: '100%', height: 'auto', maxWidth: '100%' }
      }
    >
      <defs>
        <clipPath id={clipId}>
          <rect x={plot.left} y={plot.top} width={plot.width} height={plot.height} />
        </clipPath>
      </defs>

      <rect x={0} y={0} width={width} height={height} fill="#ffffff" />

      {/* 网格 */}
      {geo.xTicks.map((t) => (
        <line
          key={`gx-${t.value}`}
          x1={t.pos}
          x2={t.pos}
          y1={plot.top}
          y2={plot.bottom}
          stroke="#eef2f7"
          strokeWidth="1"
        />
      ))}
      {geo.yTicks.map((t) => (
        <line
          key={`gy-${t.value}`}
          x1={plot.left}
          x2={plot.right}
          y1={t.pos}
          y2={t.pos}
          stroke="#eef2f7"
          strokeWidth="1"
        />
      ))}

      {/* 坐标轴 */}
      <line x1={plot.left} x2={plot.right} y1={plot.bottom} y2={plot.bottom} stroke="#334155" strokeWidth="1.4" />
      <line x1={plot.left} x2={plot.left} y1={plot.top} y2={plot.bottom} stroke="#334155" strokeWidth="1.4" />

      {/* 刻度与标签 */}
      {geo.xTicks.map((t) => (
        <g key={`lx-${t.value}`}>
          <line x1={t.pos} x2={t.pos} y1={plot.bottom} y2={plot.bottom + 5} stroke="#334155" strokeWidth="1" />
          <text x={t.pos} y={plot.bottom + 18} textAnchor="middle" className="plot-axis-label">
            {t.label}
          </text>
        </g>
      ))}
      {geo.yTicks.map((t) => (
        <g key={`ly-${t.value}`}>
          <line x1={plot.left - 5} x2={plot.left} y1={t.pos} y2={t.pos} stroke="#334155" strokeWidth="1" />
          <text x={plot.left - 9} y={t.pos + 4} textAnchor="end" className="plot-axis-label">
            {t.label}
          </text>
        </g>
      ))}

      {/* 轴标题 */}
      <text x={(plot.left + plot.right) / 2} y={height - 8} textAnchor="middle" className="plot-axis-title">
        {xLabel}
        {geo.xLog ? '（对数轴）' : ''}
      </text>
      <text
        x={14}
        y={(plot.top + plot.bottom) / 2}
        transform={`rotate(-90 14 ${(plot.top + plot.bottom) / 2})`}
        textAnchor="middle"
        className="plot-axis-title"
      >
        {yLabel}
      </text>

      {/* 标记竖线（画在曲线下面） */}
      {geo.markers.map((m, i) => (
        <g key={`mk-${i}`}>
          <line
            x1={m.sx}
            x2={m.sx}
            y1={plot.top}
            y2={plot.bottom}
            stroke="#d97706"
            strokeWidth="1.1"
            strokeDasharray="5 4"
            strokeOpacity="0.8"
          />
          {m.sy !== undefined && <circle cx={m.sx} cy={m.sy} r="3.4" fill="#d97706" />}
          {m.label && (
            <text
              x={Math.max(plot.left + 4, Math.min(plot.right - 4, m.sx))}
              y={plot.top - 7}
              textAnchor={m.sx > plot.right - 60 ? 'end' : m.sx < plot.left + 60 ? 'start' : 'middle'}
              className="plot-marker-label"
            >
              {m.label}
            </text>
          )}
        </g>
      ))}

      {/* 曲线（裁剪在绘图区内） */}
      <g clipPath={`url(#${clipId})`}>
        {geo.series.map((s, i) => (
          <path
            key={`s-${i}`}
            d={s.path}
            fill="none"
            stroke={s.color}
            strokeWidth="2"
            strokeLinejoin="round"
            strokeLinecap="round"
            vectorEffect="non-scaling-stroke"
          />
        ))}
      </g>
    </svg>
  );
}

/* ---------------------------------------------------------------- 主组件 */

/** plot 画布：纯 SVG 折线图 + 图例 + 数值表 + 说明/依据，可放大。 */
export function PlotCanvas({ artifact, demo }: CanvasProps) {
  const data = (artifact.data || {}) as PlotData;
  const [zoom, setZoom] = useState(false);

  const geo = useMemo(() => buildPlotGeometry(data), [data]);
  const hasChart = !geo.empty;
  const hasBackendSvg = typeof data.svg === 'string' && data.svg.trim().length > 0;
  const results = Array.isArray(data.results) ? data.results : [];
  const refs = Array.isArray(data.refs) ? data.refs : [];

  useEffect(() => {
    if (!zoom) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setZoom(false);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [zoom]);

  if (!hasChart && !hasBackendSvg) {
    return (
      <div className="canvas-body">
        <div className="canvas-empty-inline">
          <Icon name="alert" size={20} />
          <p>plot artifact 还没有可绘制的 series（曲线点数据未到）。</p>
          <pre className="json-pre">{JSON.stringify(data, null, 2).slice(0, 1600)}</pre>
        </div>
      </div>
    );
  }

  const xLogLabel = geo.xLog ? '对数轴' : '线性轴';

  return (
    <div className="canvas-body plot-body">
      <div className="plot-head">
        <div className="plot-headline">
          <span className="plot-title">{data.title ?? '曲线 / 分布'}</span>
          {data.kind && <span className="chip chip-type mono">{data.kind}</span>}
          {hasChart && <span className="chip chip-type">{xLogLabel}</span>}
          {demo && <span className="chip chip-demo">示例</span>}
        </div>
        {hasChart && (
          <button className="btn btn-ghost btn-xs" type="button" onClick={() => setZoom(true)}>
            <Icon name="expand" size={13} /> 放大
          </button>
        )}
      </div>

      {hasChart && (
        <>
          <div className="tol-chart-wrap plot-sheet">
            <PlotChart data={data} geo={geo} />
          </div>
          {geo.legend.length > 0 && (
            <div className="plot-legend">
              {geo.legend.map((l) => (
                <span className="plot-legend-item" key={l.name}>
                  <i className="plot-swatch" style={{ background: l.color }} />
                  {l.name}
                </span>
              ))}
            </div>
          )}
          <p className="tol-legend-note">
            横轴 {data.x_label ?? 'x'}（{xLogLabel}），纵轴 {data.y_label ?? 'y'}；虚线为标记位置，刻度按「nice」步长取整。
          </p>
        </>
      )}

      {hasBackendSvg && (
        <div className="plot-backend-svg">
          <div className="calc-section-title">后端图示</div>
          <div className="plot-svg-card" dangerouslySetInnerHTML={{ __html: data.svg as string }} />
        </div>
      )}

      {results.length > 0 && (
        <div className="tol-table-wrap">
          <table className="tol-table">
            <thead>
              <tr>
                <th>量</th>
                <th>数值</th>
                <th>单位</th>
                <th>说明</th>
              </tr>
            </thead>
            <tbody>
              {results.map((item, i) => (
                <tr key={`${item.name}_${i}`}>
                  <td>{item.name}</td>
                  <td className="mono calc-result-value">{fmtResult(item.value)}</td>
                  <td className="mono">{item.unit ?? '—'}</td>
                  <td className="calc-result-note">{item.note ?? ''}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {data.note && (
        <div className="tol-note">
          <span className="tol-note-label">说明</span>
          <span>{data.note}</span>
        </div>
      )}

      {refs.length > 0 && (
        <div className="calc-refs">
          <span className="tol-note-label">依据</span>
          {refs.map((r) => (
            <span className="chip chip-doc" key={r}>
              {r}
            </span>
          ))}
        </div>
      )}

      {zoom && hasChart && (
        <div
          className="fig-mask"
          role="dialog"
          aria-modal="true"
          aria-label="曲线放大"
          onClick={() => setZoom(false)}
        >
          <div className="tv-modal" onClick={(e) => e.stopPropagation()}>
            <div className="tv-modal-head">
              <div>
                <div className="tv-modal-title">{data.title ?? '曲线 / 分布'}</div>
                <div className="tv-modal-sub">
                  {data.x_label ?? 'x'} — {data.y_label ?? 'y'} · {xLogLabel}
                </div>
              </div>
              <button className="icon-btn" type="button" onClick={() => setZoom(false)} aria-label="关闭大图">
                <Icon name="x" size={18} />
              </button>
            </div>
            <div className="tv-modal-body">
              <PlotChart data={data} geo={geo} variant="modal" />
            </div>
            <div className="tv-modal-foot">
              <span className="tv-legend-item">
                <i className="plot-line" /> 曲线
              </span>
              <span className="tv-legend-item">
                <i className="plot-line plot-line-dash" /> 标记
              </span>
              <span className="tv-modal-hint">Esc 关闭</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ---------------------------------------------------------------- 数值格式 */

const SUP: Record<string, string> = {
  '0': '⁰',
  '1': '¹',
  '2': '²',
  '3': '³',
  '4': '⁴',
  '5': '⁵',
  '6': '⁶',
  '7': '⁷',
  '8': '⁸',
  '9': '⁹',
  '-': '⁻',
  '+': '⁺',
};

function sup(n: number): string {
  return String(n)
    .split('')
    .map((c) => SUP[c] ?? c)
    .join('');
}

/** 与 calc 画布一致的数值展示：3.33×10⁻⁴ 而不是 3.33e-4。 */
function fmtResult(v: number | string | undefined | null): string {
  if (v === undefined || v === null || v === '') return '—';
  if (typeof v === 'string') return v;
  if (!Number.isFinite(v)) return String(v);
  const abs = Math.abs(v);
  if (abs === 0) return '0';
  if (abs >= 1e-3 && abs < 1e5) {
    return v.toFixed(4).replace(/0+$/, '').replace(/\.$/, '');
  }
  const exp = Math.floor(Math.log10(abs));
  const mant = Number((v / 10 ** exp).toPrecision(3));
  return `${mant}×10${sup(exp)}`;
}

export default PlotCanvas;
