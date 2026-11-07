import { useMemo, useState } from 'react';
import type { CanvasProps } from '../registry';
import type { CoachArcStep, DrawOp } from '../../lib/types';
import { Icon } from '../../shell/Icons';

/* ---------------------------------------------------------------- 投影 */

interface Projection {
  w: number;
  h: number;
  scale: number;
  sx: (x: number) => number;
  sy: (y: number) => number;
}

/** 把几何坐标（y 向上）投影到 SVG 画布（y 向下），自动缩放并居中。 */
function buildProjection(ops: DrawOp[], W = 420, H = 300, pad = 30): Projection {
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  const add = (x: number, y: number) => {
    if (x < minX) minX = x;
    if (x > maxX) maxX = x;
    if (y < minY) minY = y;
    if (y > maxY) maxY = y;
  };
  const addCircle = (x: number, y: number, r: number) => {
    add(x - r, y - r);
    add(x + r, y + r);
  };

  for (const op of ops) {
    if (op.op === 'line') {
      add(op.a[0], op.a[1]);
      add(op.b[0], op.b[1]);
    } else if (op.op === 'circle' || op.op === 'arc') {
      addCircle(op.c[0], op.c[1], op.r);
    } else if (op.op === 'point') {
      add(op.p[0], op.p[1]);
    }
  }

  if (!Number.isFinite(minX) || !Number.isFinite(minY)) {
    return { w: W, h: H, scale: 1, sx: (x) => x, sy: (y) => y };
  }
  if (maxX - minX < 1e-6) maxX = minX + 1;
  if (maxY - minY < 1e-6) maxY = minY + 1;

  const rangeX = maxX - minX;
  const rangeY = maxY - minY;
  const scale = Math.min((W - 2 * pad) / rangeX, (H - 2 * pad) / rangeY);
  const usedW = rangeX * scale;
  const usedH = rangeY * scale;
  const offX = (W - usedW) / 2 - minX * scale;
  const offY = (H - usedH) / 2 + maxY * scale;

  return {
    w: W,
    h: H,
    scale,
    sx: (x) => offX + x * scale,
    sy: (y) => offY - y * scale,
  };
}

/** 圆弧：后端给的是「度」，且保证 start→end 逆时针扫过 ≤180°（劣弧）。 */
function arcPath(op: Extract<DrawOp, { op: 'arc' }>, proj: Projection): string {
  const toRad = (d: number) => (d * Math.PI) / 180;
  const a1 = toRad(op.start_angle ?? 0);
  const a2 = toRad(op.end_angle ?? 0);
  const [cx, cy] = op.c;
  const p1 = [cx + op.r * Math.cos(a1), cy + op.r * Math.sin(a1)];
  const p2 = [cx + op.r * Math.cos(a2), cy + op.r * Math.sin(a2)];
  const r = op.r * proj.scale;
  // y 轴翻转后，数学逆时针 = 屏幕逆时针 → sweep-flag = 0
  return `M ${proj.sx(p1[0]).toFixed(2)} ${proj.sy(p1[1]).toFixed(2)} A ${r.toFixed(2)} ${r.toFixed(2)} 0 0 0 ${proj
    .sx(p2[0])
    .toFixed(2)} ${proj.sy(p2[1]).toFixed(2)}`;
}

function Drawing({ ops, projection }: { ops: DrawOp[]; projection: Projection }) {
  return (
    <>
      {ops.map((op, i) => {
        if (op.op === 'line') {
          return (
            <line
              key={`l${i}`}
              x1={projection.sx(op.a[0])}
              y1={projection.sy(op.a[1])}
              x2={projection.sx(op.b[0])}
              y2={projection.sy(op.b[1])}
              className="coach-line"
            />
          );
        }
        if (op.op === 'circle') {
          const cx = projection.sx(op.c[0]);
          const cy = projection.sy(op.c[1]);
          const r = op.r * projection.scale;
          return (
            <g key={`c${i}`}>
              <circle cx={cx} cy={cy} r={r} className="coach-circle" />
              {op.label && (
                <text x={cx + r + 5} y={cy - 4} className="coach-op-label" fill="#64748b">
                  {op.label}
                </text>
              )}
            </g>
          );
        }
        if (op.op === 'arc') {
          return <path key={`a${i}`} d={arcPath(op, projection)} className="coach-arc" fill="none" />;
        }
        if (op.op === 'point') {
          const x = projection.sx(op.p[0]);
          const y = projection.sy(op.p[1]);
          return (
            <g key={`p${i}`}>
              <circle cx={x} cy={y} r="3.2" className="coach-point" />
              {op.label && (
                <text x={x + 7} y={y - 6} className="coach-op-label" fill="#1d4ed8">
                  {op.label}
                </text>
              )}
            </g>
          );
        }
        return null;
      })}
    </>
  );
}

/* ---------------------------------------------------------------- 参数 */

const PARAM_LABEL: Record<string, string> = {
  r: 'R',
  c1: 'O1',
  r1: 'R1',
  c2: 'O2',
  r2: 'R2',
  line_p1: 'P1',
  line_p2: 'P2',
  circle_center: 'O',
  circle_r: 'R',
};

function fmtNum(v: number): string {
  const r = Math.round(v * 1000) / 1000;
  return Number.isInteger(r) ? String(r) : r.toFixed(3).replace(/0+$/, '').replace(/\.$/, '');
}

function fmtParam(v: unknown): string {
  if (Array.isArray(v)) return `(${v.map((x) => fmtNum(Number(x))).join(', ')})`;
  if (typeof v === 'number') return fmtNum(v);
  return String(v);
}

/* ---------------------------------------------------------------- 圆弧作图 */

function ArcView({
  kindCn,
  params,
  note,
  steps,
  summary,
  formula,
}: {
  kindCn: string;
  params: Record<string, unknown>;
  note: string;
  steps: CoachArcStep[];
  summary?: string;
  formula?: string;
}) {
  const [active, setActive] = useState(steps.length - 1);

  // 用全部步骤的并集定视图，切换步骤时画布不跳
  const allOps = useMemo(() => steps.flatMap((s) => (Array.isArray(s.draw) ? s.draw : [])), [steps]);
  const projection = useMemo(() => buildProjection(allOps), [allOps]);
  const current = steps[Math.max(0, Math.min(active, steps.length - 1))];
  const currentOps = current?.draw ?? [];
  const paramEntries = Object.entries(params || {}).filter(([, v]) => v !== null && v !== undefined);

  return (
    <div className="canvas-body coach-body">
      <div className="coach-head">
        <div className="coach-title">
          <Icon name="pencil" size={14} />
          <span>{kindCn || '圆弧连接作图'}</span>
        </div>
        {paramEntries.length > 0 && (
          <div className="coach-params">
            {paramEntries.map(([k, v]) => (
              <span className="coach-param" key={k}>
                <span className="coach-param-key">{PARAM_LABEL[k] ?? k}</span>
                <span className="coach-param-val mono">{fmtParam(v)}</span>
              </span>
            ))}
          </div>
        )}
      </div>

      {note && (
        <div className="coach-note">
          <Icon name="alert" size={13} />
          <p>{note}</p>
        </div>
      )}

      <div className="coach-canvas">
        <svg
          className="coach-svg"
          viewBox={`0 0 ${projection.w} ${projection.h}`}
          role="img"
          aria-label="圆弧连接分步作图"
        >
          <defs>
            <pattern id="coachGrid" width="20" height="20" patternUnits="userSpaceOnUse">
              <path d="M20 0H0V20" fill="none" stroke="#e8eef6" strokeWidth="1" />
            </pattern>
          </defs>
          <rect x="0" y="0" width={projection.w} height={projection.h} fill="#fbfdff" />
          <rect x="0" y="0" width={projection.w} height={projection.h} fill="url(#coachGrid)" />
          <Drawing ops={currentOps} projection={projection} />
        </svg>
        <div className="coach-canvas-tag">第 {current?.n ?? '-'} 步 / 共 {steps.length} 步</div>
      </div>

      <div className="coach-step-chips">
        {steps.map((s, i) => (
          <button
            key={s.n}
            type="button"
            className={`coach-step-chip ${i === active ? 'is-active' : ''}`}
            onClick={() => setActive(i)}
            title={s.title}
          >
            {s.n}
          </button>
        ))}
        <span className="coach-step-title">{current?.title}</span>
      </div>

      {current?.detail && (
        <div className="coach-step-detail">
          <p>{current.detail}</p>
        </div>
      )}

      {summary && (
        <div className="coach-summary">
          <span className="coach-summary-label">作图结果</span>
          <p>{summary}</p>
        </div>
      )}
      {formula && (
        <div className="coach-formula">
          <span className="coach-summary-label">几何依据</span>
          <p>{formula}</p>
        </div>
      )}
    </div>
  );
}

/* ---------------------------------------------------------------- 螺纹 */

function ThreadSchematic({ d, d1 }: { d: number; d1: number }) {
  return (
    <svg className="thread-svg" viewBox="0 0 380 120" role="img" aria-label="外螺纹比例画法示意">
      <line x1="12" y1="60" x2="368" y2="60" className="thread-centerline" />
      {/* 大径：粗实线 */}
      <line x1="34" y1="42" x2="342" y2="42" className="thread-major" />
      <line x1="34" y1="78" x2="342" y2="78" className="thread-major" />
      {/* 小径：细实线，画入倒角 */}
      <line x1="56" y1="49" x2="318" y2="49" className="thread-minor" />
      <line x1="56" y1="71" x2="318" y2="71" className="thread-minor" />
      {/* 倒角 */}
      <line x1="34" y1="42" x2="56" y2="49" className="thread-chamfer" />
      <line x1="34" y1="78" x2="56" y2="71" className="thread-chamfer" />
      <line x1="342" y1="42" x2="318" y2="49" className="thread-chamfer" />
      <line x1="342" y1="78" x2="318" y2="71" className="thread-chamfer" />
      {/* 螺纹终止线 */}
      <line x1="300" y1="42" x2="300" y2="78" className="thread-end" />
      <text x="62" y="36" className="thread-label">
        大径 d = {d.toFixed(2)}（粗实线）
      </text>
      <text x="62" y="97" className="thread-label thread-label-minor">
        小径 d₁ ≈ {d1.toFixed(2)}（细实线，画入倒角）
      </text>
      <text x="306" y="58" className="thread-label">
        终止线
      </text>
    </svg>
  );
}

function ThreadView({ data }: { data: Record<string, any> }) {
  const table = (data.table || {}) as Record<string, unknown>;
  const points: string[] = Array.isArray(data.points) ? data.points : [];
  const rows: { key: string; label: string; value: string }[] = [
    { key: 'd', label: '大径 d', value: fmtParam(data.d ?? table.d) },
    { key: 'd1', label: '小径 d₁', value: fmtParam(data.d1 ?? table.d1) },
    { key: 'pitch', label: '螺距 P', value: fmtParam(data.pitch ?? table.pitch) },
    { key: 'series', label: '系列', value: fmtParam(table.series) },
    { key: 'profile', label: '牙型角', value: fmtParam(table.profile) },
    { key: 'standard', label: '标准', value: fmtParam(table.standard) },
  ].filter((r) => r.value && r.value !== 'undefined');

  return (
    <div className="canvas-body coach-body">
      <div className="coach-head">
        <div className="coach-title">
          <Icon name="pencil" size={14} />
          <span>{data.spec ?? '螺纹'}</span>
          {data.type_name && <span className="chip">{data.type_name}</span>}
        </div>
      </div>

      <ThreadSchematic d={Number(data.d) || 0} d1={Number(data.d1) || 0} />

      <div className="thread-table-wrap">
        <table className="thread-table">
          <tbody>
            {rows.map((r) => (
              <tr key={r.key}>
                <td className="thread-key">{r.label}</td>
                <td className="mono">{r.value}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {points.length > 0 && (
        <div className="coach-points">
          <div className="coach-summary-label">画法要点</div>
          <ol>
            {points.map((p, i) => (
              <li key={`${i}-${p.slice(0, 8)}`}>{p}</li>
            ))}
          </ol>
        </div>
      )}

      <p className="coach-foot-note">
        示意图形仅表达线型与比例关系（d₁≈0.85d），不按真实牙型绘制。
      </p>
    </div>
  );
}

/* ---------------------------------------------------------------- 主组件 */

/**
 * coach 画布：
 *  - thread：螺纹参数表 + 比例画法示意 SVG + 画法要点；
 *  - arc_*：按 steps[].draw 逐条画 SVG（line / arc / point / circle），可切步骤；
 *  - 其他：把 steps 当文字步骤渲染，再兜底 JSON。
 */
export function CoachCanvas({ artifact }: CanvasProps) {
  const raw = (artifact.data || {}) as Record<string, any>;
  const kind = String(raw.kind ?? '');
  const payload = (raw.data || {}) as Record<string, any>;
  const note = typeof raw.note === 'string' ? raw.note : '';
  const steps: CoachArcStep[] = Array.isArray(payload.steps) ? payload.steps : [];

  if (kind === 'thread' || (Array.isArray(payload.points) && !steps.length)) {
    return <ThreadView data={payload} />;
  }

  if (steps.length > 0) {
    return (
      <ArcView
        kindCn={String(raw.kind_cn ?? '')}
        params={(raw.params || {}) as Record<string, unknown>}
        note={note}
        steps={steps}
        summary={typeof payload.summary === 'string' ? payload.summary : undefined}
        formula={typeof payload.result?.formula === 'string' ? payload.result.formula : undefined}
      />
    );
  }

  return (
    <div className="canvas-body">
      <div className="canvas-empty-inline">
        <Icon name="pencil" size={20} />
        <p>coach artifact 暂无可渲染的 steps 或 thread 数据。</p>
        <pre className="json-pre">{JSON.stringify(raw, null, 2).slice(0, 1600)}</pre>
      </div>
    </div>
  );
}
