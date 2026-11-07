import { useEffect, useId, useMemo, useState } from 'react';
import type { CanvasProps } from '../registry';
import type {
  ThreeViewArtifactData,
  ThreeViewAux,
  ThreeViewSegment,
  ThreeViewModelInfo,
} from '../../lib/types';
import { getModel, getModels } from '../../lib/api';
import { Icon } from '../../shell/Icons';

const VIEW_CN: Record<string, string> = {
  front: '主视图',
  top: '俯视图',
  left: '左视图',
};

const VIEW_SHORT: Record<string, string> = {
  front: '主视',
  top: '俯视',
  left: '左视',
};

function normViewBox(v?: [number, number, number, number] | number[]): [number, number, number, number] {
  if (Array.isArray(v) && v.length === 4 && v.every((n) => Number.isFinite(n)) && v[2] > 0 && v[3] > 0) {
    return [v[0], v[1], v[2], v[3]];
  }
  return [0, 0, 520, 420];
}

function sizeText(data: ThreeViewArtifactData): string | null {
  const s = data.size;
  if (!s) return null;
  const parts = [s.L, s.W, s.H].filter((n): n is number => typeof n === 'number');
  if (parts.length === 0) return null;
  return `${parts.join(' × ')}${data.unit ? ` ${data.unit}` : ''}`;
}

/**
 * 后端只给 aux 的线段坐标与 label 文本，label 的语义位置由 kind 决定：
 *   长对正 → 竖线底端；高平齐 → 横线左端；宽相等 → 45° 线中点。
 * 不能按 x1,y1 放（三条线都从图左上角出发，会叠在一起）。
 */
function auxLabelPos(a: ThreeViewAux): { x: number; y: number; anchor: 'start' | 'middle' | 'end' } | null {
  if (!a.label) return null;
  if (a.kind === 'long') {
    return { x: Math.min(a.x1, a.x2), y: Math.max(a.y1, a.y2) + 12, anchor: 'middle' };
  }
  if (a.kind === 'height') {
    return { x: Math.min(a.x1, a.x2) - 5, y: a.y1 - 5, anchor: 'end' };
  }
  if (a.kind === 'width') {
    return { x: (a.x1 + a.x2) / 2, y: (a.y1 + a.y2) / 2 + 4, anchor: 'middle' };
  }
  return { x: a.x2 + 4, y: a.y2 + 4, anchor: 'start' };
}

function ProjectionSvg({
  data,
  hover,
  onHover,
  variant = 'inline',
}: {
  data: ThreeViewArtifactData;
  hover: string | null;
  onHover: (view: string | null) => void;
  variant?: 'inline' | 'modal';
}) {
  const gridId = `tvgrid-${useId().replace(/[^a-zA-Z0-9_-]/g, '')}`;
  const vb = normViewBox(data.viewBox);
  const [vx, vy, vw, vh] = vb;
  const boxes = data.view_boxes || {};
  const size = sizeText(data);

  const labels = useMemo(() => {
    if (Array.isArray(data.labels) && data.labels.length > 0) return data.labels;
    return Object.entries(boxes).map(([view, box]) => ({
      view,
      text: VIEW_CN[view] ?? view,
      x: (box[0] + box[2]) / 2,
      y: box[3] + 18,
    }));
  }, [data.labels, boxes]);

  return (
    <svg
      className="tv-svg"
      viewBox={`${vx} ${vy} ${vw} ${vh}`}
      // 默认 xMidYMid meet 已保证等比缩放；显式写出 + 内联 width:100% 防止任何宿主样式把 SVG 撑出容器
      preserveAspectRatio="xMidYMid meet"
      role="img"
      aria-label={`${data.name ?? data.model_id ?? '三视图'} 三视图投影`}
      style={
        variant === 'modal'
          ? {
              display: 'block',
              width: '100%',
              // 放大弹层里限制最大放大倍数（约 2.2 倍原坐标），避免 viewBox 小的模型被放得文字过大
              maxWidth: `${Math.round(vw * 2.2)}px`,
              height: 'auto',
              margin: '0 auto',
            }
          : { display: 'block', width: '100%', height: 'auto', maxWidth: '100%' }
      }
    >
      <defs>
        <pattern id={gridId} width="20" height="20" patternUnits="userSpaceOnUse">
          <path d="M20 0H0V20" fill="none" stroke="#eef2f7" strokeWidth="1" />
        </pattern>
      </defs>

      <rect x={vx} y={vy} width={vw} height={vh} fill="#ffffff" />
      <rect x={vx} y={vy} width={vw} height={vh} fill={`url(#${gridId})`} />

      {/* 投影辅助线：长对正 / 高平齐 / 宽相等 */}
      {(data.aux || []).map((a, i) => {
        const pos = auxLabelPos(a);
        return (
          <g key={`aux-${i}`}>
            <line
              x1={a.x1}
              y1={a.y1}
              x2={a.x2}
              y2={a.y2}
              stroke={a.color || '#2563eb'}
              strokeOpacity="0.7"
              strokeWidth="0.8"
              strokeDasharray="4 4"
            />
            {pos && (
              <text x={pos.x} y={pos.y} textAnchor={pos.anchor} className="tv-aux-label" fill={a.color || '#2563eb'}>
                {a.label}
              </text>
            )}
          </g>
        );
      })}

      {/* 三视图线条：实线 1.9 深色 / 虚线 1.0 浅色；悬停时其它视图变淡 */}
      {(data.segments || []).map((seg, i) => {
        const st = segmentStyle(seg);
        const dimmed = Boolean(hover && seg.view && seg.view !== hover);
        return (
          <line
            key={`seg-${i}`}
            x1={seg.x1}
            y1={seg.y1}
            x2={seg.x2}
            y2={seg.y2}
            stroke={st.stroke}
            strokeWidth={st.width}
            strokeDasharray={st.dash}
            strokeLinecap="butt"
            opacity={dimmed ? 0.2 : 1}
          />
        );
      })}

      {/* 视图区悬停：高亮 + 视图名 */}
      {Object.entries(boxes).map(([view, box]) => {
        const [x1, y1, x2, y2] = box;
        const active = hover === view;
        return (
          <g
            key={`box-${view}`}
            className="tv-viewbox"
            onMouseEnter={() => onHover(view)}
            onMouseLeave={() => onHover(null)}
            onFocus={() => onHover(view)}
            onBlur={() => onHover(null)}
            tabIndex={0}
            role="button"
            aria-label={VIEW_CN[view] ?? view}
          >
            <rect
              x={x1}
              y={y1}
              width={Math.max(1, x2 - x1)}
              height={Math.max(1, y2 - y1)}
              fill="#2563eb"
              fillOpacity={active ? 0.05 : 0}
              stroke={active ? '#2563eb' : 'transparent'}
              strokeOpacity={active ? 0.45 : 0}
              strokeWidth="1"
              strokeDasharray="4 3"
              rx="3"
            />
            {active && (
              <text x={x1 + 5} y={y1 + 14} className="tv-hover-name" fill="#1d4ed8">
                {VIEW_CN[view] ?? view}
              </text>
            )}
          </g>
        );
      })}

      {/* 三个视图标题（后端已给排好版的位置） */}
      {labels.map((l, i) => (
        <text key={`label-${i}`} x={l.x} y={l.y} textAnchor="middle" className="tv-view-label">
          {l.text}
        </text>
      ))}

      {/* 左上角：模型名 + L×W×H */}
      <g>
        <rect
          x={vx + 8}
          y={vy + 8}
          width="150"
          height={size ? 44 : 30}
          rx="6"
          fill="#ffffff"
          fillOpacity="0.9"
          stroke="#e2e8f0"
        />
        <text x={vx + 18} y={vy + 26} className="tv-overlay-name">
          {data.name ?? data.model_id ?? '—'}
        </text>
        {size && (
          <text x={vx + 18} y={vy + 43} className="tv-overlay-size">
            {size}
          </text>
        )}
      </g>

      {/* 右下角：单位 */}
      <text x={vx + vw - 10} y={vy + vh - 10} textAnchor="end" className="tv-unit">
        单位：{data.unit ?? 'mm'}
      </text>
    </svg>
  );
}

function segmentStyle(seg: ThreeViewSegment): { stroke: string; width: number; dash?: string } {
  if (seg.hidden) return { stroke: '#94a3b8', width: 1.0, dash: '6 4' };
  return { stroke: '#0f172a', width: 1.9 };
}

/**
 * three_view 画布：直接按后端下发的图纸坐标画 SVG 三视图（不在前端算投影）。
 * 顶部可切换 /api/models 里的 8 个模型，切换只拉 /api/models/{id} 重绘，不重发对话。
 */
export function ThreeViewCanvas({ artifact, demo }: CanvasProps) {
  const base = (artifact.data || {}) as ThreeViewArtifactData;
  const [remote, setRemote] = useState<ThreeViewArtifactData | null>(null);
  const [catalog, setCatalog] = useState<ThreeViewModelInfo[] | null>(null);
  const [currentId, setCurrentId] = useState(base.model_id ?? '');
  const [switching, setSwitching] = useState(false);
  const [modelError, setModelError] = useState<string | null>(null);
  const [hover, setHover] = useState<string | null>(null);
  const [zoom, setZoom] = useState(false);

  const data = remote ?? base;
  const segments = Array.isArray(data.segments) ? data.segments : [];

  // 新 artifact 到达 → 回到对话里下发的模型
  useEffect(() => {
    setRemote(null);
    setCurrentId(((artifact.data || {}) as ThreeViewArtifactData).model_id ?? '');
    setModelError(null);
  }, [artifact.receivedAt, artifact.data]);

  // 模型清单只拉一次
  useEffect(() => {
    let alive = true;
    getModels()
      .then((list) => {
        if (alive) setCatalog(list);
      })
      .catch(() => {
        /* 下拉不可用不影响画布本身 */
      });
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    if (!zoom) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setZoom(false);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [zoom]);

  async function switchModel(id: string) {
    if (!id || switching) return;
    setSwitching(true);
    setModelError(null);
    try {
      const next = await getModel(id);
      setRemote(next);
      setCurrentId(id);
    } catch (err) {
      setModelError(`切换模型失败：${(err as Error)?.message || String(err)}`);
    } finally {
      setSwitching(false);
    }
  }

  if (segments.length === 0) {
    return (
      <div className="canvas-body">
        <div className="canvas-empty-inline">
          <Icon name="cube" size={20} />
          <p>three_view artifact 还没有 segments（投影引擎数据未到）。</p>
          <pre className="json-pre">{JSON.stringify(base, null, 2).slice(0, 1400)}</pre>
        </div>
      </div>
    );
  }

  const size = sizeText(data);
  const stats = data.stats;
  const inCatalog = catalog?.some((m) => m.model_id === currentId);

  return (
    <div className="canvas-body tv-body">
      <div className="tv-head">
        <div className="tv-model">
          <span className="tv-name">{data.name ?? data.model_id ?? '三视图'}</span>
          {data.model_id && <span className="mono tv-model-id">{data.model_id}</span>}
        </div>
        <div className="tv-head-right">
          {size && <span className="chip chip-size">{size}</span>}
          {demo && <span className="chip chip-demo">示例</span>}
          {catalog && catalog.length > 0 && (
            <label className="tv-select-wrap">
              <span className="tv-select-label">模型</span>
              <select
                className="tv-select"
                value={inCatalog ? currentId : ''}
                disabled={switching}
                onChange={(e) => void switchModel(e.target.value)}
              >
                {!inCatalog && <option value="">{data.name ?? currentId ?? '当前模型'}</option>}
                {catalog.map((m) => (
                  <option key={m.model_id} value={m.model_id}>
                    {m.name}
                  </option>
                ))}
              </select>
              {switching && <span className="spinner" />}
            </label>
          )}
          <button className="btn btn-ghost btn-xs" type="button" onClick={() => setZoom(true)}>
            <Icon name="expand" size={13} /> 放大
          </button>
        </div>
      </div>

      {modelError && (
        <div className="tv-error">
          <Icon name="alert" size={13} />
          {modelError}
        </div>
      )}

      <div className="tv-stats">
        {stats &&
          (['front', 'top', 'left'] as const).map((k) => {
            const s = stats[k];
            if (!s) return null;
            return (
              <span className="tv-stat" key={k}>
                {VIEW_SHORT[k]} <b>{s.visible}</b>实 / <b>{s.hidden}</b>虚
              </span>
            );
          })}
        {data.projection && <span className="tv-proj">{data.projection}投影</span>}
        <span className="tv-stats-hint">悬停视图区可高亮</span>
      </div>

      <div className="tv-sheet">
        <ProjectionSvg data={data} hover={hover} onHover={setHover} />
      </div>

      <div className="tv-legend">
        <span className="tv-legend-item">
          <i className="tv-line tv-line-solid" /> 可见轮廓（粗实线）
        </span>
        <span className="tv-legend-item">
          <i className="tv-line tv-line-hidden" /> 不可见轮廓（虚线）
        </span>
        <span className="tv-legend-item">
          <i className="tv-line tv-line-aux" /> 投影辅助线（长对正 / 高平齐 / 宽相等）
        </span>
      </div>

      {zoom && (
        <div className="fig-mask" role="dialog" aria-modal="true" aria-label="三视图放大" onClick={() => setZoom(false)}>
          <div className="tv-modal" onClick={(e) => e.stopPropagation()}>
            <div className="tv-modal-head">
              <div>
                <div className="tv-modal-title">{data.name ?? data.model_id ?? '三视图'}</div>
                <div className="tv-modal-sub">
                  {data.model_id}
                  {size ? ` · ${size}` : ''}
                  {data.projection ? ` · ${data.projection}投影` : ''}
                </div>
              </div>
              <button className="icon-btn" type="button" onClick={() => setZoom(false)} aria-label="关闭大图">
                <Icon name="x" size={18} />
              </button>
            </div>
            <div className="tv-modal-body">
              <ProjectionSvg data={data} hover={hover} onHover={setHover} variant="modal" />
            </div>
            <div className="tv-modal-foot">
              <span className="tv-legend-item">
                <i className="tv-line tv-line-solid" /> 可见
              </span>
              <span className="tv-legend-item">
                <i className="tv-line tv-line-hidden" /> 不可见
              </span>
              <span className="tv-modal-hint">Esc 关闭</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default ThreeViewCanvas;
