import { useMemo } from 'react';
import type { CanvasProps } from '../registry';
import type { ToleranceArtifactData, ToleranceSide } from '../../lib/types';
import { Icon } from '../../shell/Icons';

/* ---------------------------------------------------------------- 数值工具 */

const n = (v: unknown): number => (typeof v === 'number' && Number.isFinite(v) ? v : 0);

/** mm → 带符号字符串（3 位小数）。 */
function fmtMm(v: number): string {
  const clean = Math.abs(v) < 5e-7 ? 0 : v;
  return `${clean >= 0 ? '+' : '−'}${Math.abs(clean).toFixed(3)}`;
}

/** mm → μm 数值（图上习惯用 μm）。 */
function toUm(v: number): number {
  const um = v * 1000;
  return Math.abs(um) < 0.05 ? 0 : Math.round(um * 10) / 10;
}

function fmtUm(v: number): string {
  const um = toUm(v);
  return `${um > 0 ? '+' : um < 0 ? '−' : ''}${Math.abs(um).toFixed(Number.isInteger(um) ? 0 : 1)}`;
}

function niceStep(range: number, target = 6): number {
  if (!(range > 0)) return 5;
  const raw = range / target;
  const pow = Math.pow(10, Math.floor(Math.log10(raw)));
  const norm = raw / pow;
  const mult = norm < 1.5 ? 1 : norm < 3 ? 2 : norm < 7 ? 5 : 10;
  return Math.max(0.5, mult * pow);
}

function roundOut(v: number, step: number, dir: 'down' | 'up'): number {
  const k = v / step;
  return (dir === 'down' ? Math.floor(k) : Math.ceil(k)) * step;
}

/* ---------------------------------------------------------------- 公差带图 */

interface Band {
  code: string;
  lo: number; // μm，下偏差
  hi: number; // μm，上偏差
  color: string;
  pattern: string;
}

function ToleranceBandChart({ data }: { data: ToleranceArtifactData }) {
  const hole: ToleranceSide = data.hole;
  const shaft: ToleranceSide = data.shaft;

  // 孔：ES 上偏差、EI 下偏差；轴：es 上偏差、ei 下偏差（单位 mm → μm）
  const hES = toUm(n(hole?.ES));
  const hEI = toUm(n(hole?.EI));
  const sES = toUm(n(shaft?.es));
  const sEI = toUm(n(shaft?.ei));

  // 竖版画布：右栏只有 ~340–420px 宽，横版会让字缩到 4px，故用窄高比。
  const W = 480;
  const H = 540;
  const plot = { left: 96, right: 372, top: 56, bottom: 456 };
  const plotW = plot.right - plot.left;
  const plotH = plot.bottom - plot.top;

  const values = [0, hES, hEI, sES, sEI];
  const rawMin = Math.min(...values);
  const rawMax = Math.max(...values);
  const span = Math.max(rawMax - rawMin, 10);
  const step = niceStep(span);
  const axisMin = roundOut(rawMin - span * 0.18, step, 'down');
  const axisMax = roundOut(rawMax + span * 0.18, step, 'up');
  const y = (v: number) => plot.top + ((axisMax - v) / (axisMax - axisMin)) * plotH;

  const holes: Band = {
    code: `孔 ${hole?.code ?? '—'}`,
    lo: hEI,
    hi: hES,
    color: '#2563eb',
    pattern: 'holeHatch',
  };
  const shafts: Band = {
    code: `轴 ${shaft?.code ?? '—'}`,
    lo: sEI,
    hi: sES,
    color: '#ea580c',
    pattern: 'shaftHatch',
  };

  // 三类配合区域（偏差空间判定：保证间隙 / 保证过盈 / 两带重叠）
  const zones: { kind: 'clearance' | 'interference' | 'overlap'; top: number; bottom: number }[] = [];
  if (hEI > sES) zones.push({ kind: 'clearance', top: hEI, bottom: sES });
  if (sEI > hES) zones.push({ kind: 'interference', top: sEI, bottom: hES });
  const ovTop = Math.min(hES, sES);
  const ovBottom = Math.max(hEI, sEI);
  if (ovTop > ovBottom) zones.push({ kind: 'overlap', top: ovTop, bottom: ovBottom });

  const fit = data.fit || ({} as ToleranceArtifactData['fit']);
  const xmax = typeof fit.max_gap === 'number' ? toUm(fit.max_gap) : toUm((hES - sEI) / 1000);
  const xmin = typeof fit.min_gap === 'number' ? toUm(fit.min_gap) : toUm((hEI - sES) / 1000);

  const ticks: number[] = [];
  for (let v = axisMin; v <= axisMax + 1e-6; v += step) ticks.push(Math.round(v * 100) / 100);

  const bandY = (b: Band) => ({ y: y(b.hi), h: Math.max(2, y(b.lo) - y(b.hi)) });
  const bandX = plot.left;
  const bandW = plotW;

  return (
    <div className="tol-chart-wrap">
      <svg
        className="tol-chart"
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label={`孔 ${hole?.code} 与轴 ${shaft?.code} 的公差带图`}
        preserveAspectRatio="xMidYMid meet"
      >
        <defs>
          <pattern id="holeHatch" width="8" height="8" patternTransform="rotate(45)" patternUnits="userSpaceOnUse">
            <rect width="8" height="8" fill="#2563eb" fillOpacity="0.10" />
            <line x1="0" y1="0" x2="0" y2="8" stroke="#2563eb" strokeWidth="1.2" strokeOpacity="0.5" />
          </pattern>
          <pattern id="shaftHatch" width="8" height="8" patternTransform="rotate(-45)" patternUnits="userSpaceOnUse">
            <rect width="8" height="8" fill="#ea580c" fillOpacity="0.10" />
            <line x1="0" y1="0" x2="0" y2="8" stroke="#ea580c" strokeWidth="1.2" strokeOpacity="0.5" />
          </pattern>
          <pattern id="clearHatch" width="7" height="7" patternUnits="userSpaceOnUse">
            <rect width="7" height="7" fill="#16a34a" fillOpacity="0.18" />
            <line x1="0" y1="3.5" x2="7" y2="3.5" stroke="#16a34a" strokeOpacity="0.3" />
          </pattern>
        </defs>

        {/* 纵轴标题 */}
        <text x={plot.left} y={26} className="tol-axis-title" textAnchor="start">
          偏差 / μm
        </text>

        {/* 网格 + 纵轴刻度 */}
        {ticks.map((t) => (
          <g key={`t${t}`}>
            <line
              x1={plot.left - 6}
              x2={plot.right + 14}
              y1={y(t)}
              y2={y(t)}
              stroke={t === 0 ? '#334155' : '#e2e8f0'}
              strokeWidth={t === 0 ? 1.6 : 1}
              strokeDasharray={t === 0 ? '8 5' : undefined}
            />
            <text x={plot.left - 12} y={y(t) + 4} textAnchor="end" className="tol-axis-label">
              {t === 0 ? '0' : t}
            </text>
          </g>
        ))}

        {/* 零线标注 */}
        <text x={plot.right + 18} y={y(0) - 8} className="tol-zero-label" textAnchor="start">
          零线 0
        </text>

        {/* 配合区域阴影（画在公差带下面，透过半透明剖面线可见） */}
        {zones.map((z, i) => {
          const top = y(z.top);
          const bottom = y(z.bottom);
          if (Math.abs(bottom - top) < 2) return null;
          const bigEnough = Math.abs(bottom - top) >= 20;
          const fill =
            z.kind === 'clearance' ? 'url(#clearHatch)' : z.kind === 'interference' ? '#dc2626' : '#d97706';
          const fillOpacity = z.kind === 'clearance' ? 1 : z.kind === 'interference' ? 0.16 : 0.14;
          const edge = z.kind === 'clearance' ? '#16a34a' : z.kind === 'interference' ? '#dc2626' : '#d97706';
          const label =
            z.kind === 'clearance' ? '间隙区' : z.kind === 'interference' ? '过盈区' : '两带重叠（过渡）';
          return (
            <g key={`z${i}`}>
              <rect
                x={bandX}
                y={top}
                width={bandW}
                height={bottom - top}
                fill={fill}
                fillOpacity={fillOpacity}
                stroke={edge}
                strokeOpacity="0.4"
                strokeDasharray="4 3"
              />
              {bigEnough && (
                <text
                  x={bandX + bandW / 2}
                  y={(top + bottom) / 2 + 5}
                  textAnchor="middle"
                  className="tol-zone-label"
                  fill={
                    z.kind === 'clearance' ? '#15803d' : z.kind === 'interference' ? '#b91c1c' : '#b45309'
                  }
                >
                  {label}
                </text>
              )}
            </g>
          );
        })}

        {/* 孔公差带 */}
        <rect
          x={bandX}
          y={bandY(holes).y}
          width={bandW}
          height={bandY(holes).h}
          fill={`url(#${holes.pattern})`}
          stroke={holes.color}
          strokeWidth="2"
          rx="2"
        />
        <text x={bandX + 12} y={bandY(holes).y + bandY(holes).h / 2 + 7} className={`tol-band-name`} fill={holes.color}>
          {holes.code}
        </text>

        {/* 轴公差带 */}
        <rect
          x={bandX}
          y={bandY(shafts).y}
          width={bandW}
          height={bandY(shafts).h}
          fill={`url(#${shafts.pattern})`}
          stroke={shafts.color}
          strokeWidth="2"
          rx="2"
        />
        <text
          x={bandX + bandW - 12}
          y={bandY(shafts).y + bandY(shafts).h / 2 + 7}
          className="tol-band-name"
          textAnchor="end"
          fill={shafts.color}
        >
          {shafts.code}
        </text>

        {/* 孔的上下偏差标注：左侧、带外（ES 在上，EI 在下） */}
        <text x={bandX + 2} y={y(hES) - 9} textAnchor="start" className="tol-dev-label" fill="#2563eb">
          ES {fmtUm(hES / 1000)}
        </text>
        <text x={bandX + 2} y={y(hEI) + 20} textAnchor="start" className="tol-dev-label" fill="#2563eb">
          EI {fmtUm(hEI / 1000)}
        </text>

        {/* 轴的上下偏差标注：右侧、带外（es 在上，ei 在下） */}
        <text x={bandX + bandW - 2} y={y(sES) - 9} textAnchor="end" className="tol-dev-label" fill="#ea580c">
          es {fmtUm(sES / 1000)}
        </text>
        <text x={bandX + bandW - 2} y={y(sEI) + 20} textAnchor="end" className="tol-dev-label" fill="#ea580c">
          ei {fmtUm(sEI / 1000)}
        </text>

        {/* 最大间隙 ES − ei */}
        <Bracket x={398} y1={y(hES)} y2={y(sEI)} color="#0f766e" edgeX={plot.right} />
        <text x={398} y={(y(hES) + y(sEI)) / 2 - 8} textAnchor="middle" className="tol-dim-label" fill="#0f766e">
          Xmax
        </text>
        <text x={398} y={(y(hES) + y(sEI)) / 2 + 16} textAnchor="middle" className="tol-dim-value" fill="#0f766e">
          {fmtUm(xmax / 1000)}
        </text>

        {/* 最小间隙 / 最大过盈 EI − es */}
        <Bracket x={450} y1={y(hEI)} y2={y(sES)} color="#7c3aed" edgeX={plot.right} />
        <text x={450} y={(y(hEI) + y(sES)) / 2 - 8} textAnchor="middle" className="tol-dim-label" fill="#7c3aed">
          Xmin
        </text>
        <text x={450} y={(y(hEI) + y(sES)) / 2 + 16} textAnchor="middle" className="tol-dim-value" fill="#7c3aed">
          {fmtUm(xmin / 1000)}
        </text>
      </svg>

      <div className="tol-legend">
        <span className="legend-item">
          <i className="legend-swatch swatch-hole" /> 孔公差带 {hole?.code}
        </span>
        <span className="legend-item">
          <i className="legend-swatch swatch-shaft" /> 轴公差带 {shaft?.code}
        </span>
        <span className="legend-item">
          <i className="legend-swatch swatch-overlap" /> 重叠 = 过渡
        </span>
      </div>
      <p className="tol-legend-note">
        单位 μm；Xmax = ES − ei（最大间隙），Xmin = EI − es（负值为最大过盈）。上图数值由偏差换算，与下表交叉核对。
      </p>
    </div>
  );
}

/** 竖向尺寸线（带两端短横线 + 从公差带右缘引出的虚线）。 */
function Bracket({
  x,
  y1,
  y2,
  color,
  edgeX,
}: {
  x: number;
  y1: number;
  y2: number;
  color: string;
  edgeX: number;
}) {
  const top = Math.min(y1, y2);
  const bottom = Math.max(y1, y2);
  return (
    <g stroke={color} strokeWidth="1.3">
      <line x1={x} y1={top} x2={x} y2={bottom} />
      <line x1={x - 5} y1={top} x2={x + 5} y2={top} />
      <line x1={x - 5} y1={bottom} x2={x + 5} y2={bottom} />
      <line x1={edgeX} y1={top} x2={x} y2={top} strokeDasharray="4 4" strokeOpacity="0.5" />
      <line x1={edgeX} y1={bottom} x2={x} y2={bottom} strokeDasharray="4 4" strokeOpacity="0.5" />
    </g>
  );
}

/* ---------------------------------------------------------------- 主组件 */

/** tolerance 画布：配合特征表 + 公差带图 + 工艺提示。 */
export function ToleranceCanvas({ artifact, demo }: CanvasProps) {
  const data = (artifact.data || {}) as ToleranceArtifactData;
  const hole = data.hole;
  const shaft = data.shaft;
  const fit = data.fit;

  const valid = useMemo(
    () =>
      Boolean(
        typeof data.basic_size === 'number' &&
          hole &&
          shaft &&
          typeof (hole.ES ?? hole.es) === 'number' &&
          typeof (shaft.es ?? shaft.ES) === 'number',
      ),
    [data, hole, shaft],
  );

  if (!valid) {
    return (
      <div className="canvas-body">
        <div className="canvas-empty-inline">
          <Icon name="alert" size={20} />
          <p>tolerance artifact 缺少孔/轴偏差字段，无法绘图。</p>
          <pre className="json-pre">{JSON.stringify(data, null, 2).slice(0, 1600)}</pre>
        </div>
      </div>
    );
  }

  const ok = fit?.type ?? '—';
  const xmax = fit?.max_gap;
  const xmin = fit?.min_gap;
  const inter = fit?.max_interference;

  return (
    <div className="canvas-body tol-body">
      <div className="tol-head">
        <div className="tol-spec">
          <span className="tol-phi">Ø{data.basic_size}</span>{' '}
          <span className="tol-codes">
            {hole.code}/{shaft.code}
          </span>
          <span className="chip chip-system">{data.system}</span>
          <span className="chip chip-fit">{ok}</span>
          {demo && <span className="chip chip-demo">示例</span>}
        </div>
        <div className="tol-kpis">
          <div className="kpi">
            <span className="kpi-label">最大间隙</span>
            <span className="kpi-value">{xmax != null ? `${fmtUm(xmax)} μm` : '—'}</span>
          </div>
          <div className="kpi">
            <span className="kpi-label">最小间隙</span>
            <span className="kpi-value">{xmin != null ? `${fmtUm(xmin)} μm` : '—'}</span>
          </div>
          <div className="kpi">
            <span className="kpi-label">最大过盈</span>
            <span className="kpi-value">{inter != null ? `${fmtUm(inter)} μm` : '—'}</span>
          </div>
        </div>
      </div>

      <ToleranceBandChart data={data} />

      <div className="tol-table-wrap">
        <table className="tol-table">
          <thead>
            <tr>
              <th>项目（mm）</th>
              <th>孔 {hole.code}</th>
              <th>轴 {shaft.code}</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>标准公差 IT</td>
              <td className="mono">{n(hole.IT).toFixed(3)}</td>
              <td className="mono">{n(shaft.IT).toFixed(3)}</td>
            </tr>
            <tr>
              <td>上偏差</td>
              <td className="mono">{fmtMm(n(hole.ES))}</td>
              <td className="mono">{fmtMm(n(shaft.es))}</td>
            </tr>
            <tr>
              <td>下偏差</td>
              <td className="mono">{fmtMm(n(hole.EI))}</td>
              <td className="mono">{fmtMm(n(shaft.ei))}</td>
            </tr>
            <tr>
              <td>极限尺寸</td>
              <td className="mono">
                {n(hole.min).toFixed(3)} ~ {n(hole.max).toFixed(3)}
              </td>
              <td className="mono">
                {n(shaft.min).toFixed(3)} ~ {n(shaft.max).toFixed(3)}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      {fit?.note && (
        <div className="tol-note">
          <span className="tol-note-label">配合说明</span>
          <span>{fit.note}</span>
        </div>
      )}

      {data.process_hint && (
        <div className="tol-hint">
          <Icon name="pencil" size={13} />
          <div>
            <span className="tol-note-label">工艺提示</span>
            <p>{data.process_hint}</p>
          </div>
        </div>
      )}

      {Array.isArray(data.refs) && data.refs.length > 0 && (
        <div className="tol-refs">
          {data.refs.map((r) => (
            <span className="chip chip-doc" key={r}>
              {r}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
