import type { GraphNodeInfo } from '../../lib/types';

/* ---------------------------------------------------------------- 枚举映射 */

export const TIER_ORDER = ['core', 'trackA', 'trackB', 'branch', 'concept'];

export const TIER_CN: Record<string, string> = {
  core: '课程核心',
  trackA: '形体表达链',
  trackB: '工程规范链',
  branch: '应用分支',
  concept: '关键概念',
};

export const TIER_COLOR: Record<string, string> = {
  core: '#1d4ed8',
  trackA: '#0891b2',
  trackB: '#7c3aed',
  branch: '#db2777',
  concept: '#64748b',
};

/** 焦点视图里各 tier 的环半径（单位：viewBox 坐标）。 */
export const TIER_BASE: Record<string, number> = {
  core: 72,
  trackA: 118,
  trackB: 156,
  branch: 190,
  concept: 210,
};

export const STATE_COLOR: Record<string, string> = {
  未学: '#cbd5e1',
  在学: '#f59e0b',
  已掌握: '#16a34a',
  需复习: '#dc2626',
};

export const REL_CN: Record<string, string> = {
  prereq: '前置',
  contrast: '易混淆',
  compose: '组成',
  cause: '导致',
};

export const REL_PRIORITY: Record<string, number> = { contrast: 0, cause: 1, compose: 2, prereq: 3 };

export const REL_STYLE: Record<string, { stroke: string; width: number; dash?: string }> = {
  prereq: { stroke: '#94a3b8', width: 1.5 },
  contrast: { stroke: '#ea580c', width: 1.5, dash: '5 4' },
  compose: { stroke: '#3b82f6', width: 1, dash: '2 3' },
  cause: { stroke: '#16a34a', width: 1.5 },
};

export function tierOf(node: GraphNodeInfo): string {
  return TIER_ORDER.includes(node.tier) ? node.tier : 'concept';
}

export function stateColor(state?: string): string {
  return (state && STATE_COLOR[state]) || '#cbd5e1';
}

export function clipLabel(label: string, max = 7): string {
  return label.length > max ? `${label.slice(0, max)}…` : label;
}

/** 关系 / 分层 / 掌握 三行图例，焦点视图与全览视图共用。 */
export function GraphLegends() {
  return (
    <div className="kg-legend">
      <div className="kg-legend-row">
        <span className="kg-legend-title">分层</span>
        {TIER_ORDER.map((t) => (
          <span className="kg-legend-item" key={t}>
            <i className="kg-swatch" style={{ background: TIER_COLOR[t] }} />
            {TIER_CN[t]}
          </span>
        ))}
      </div>
      <div className="kg-legend-row">
        <span className="kg-legend-title">掌握</span>
        {Object.entries(STATE_COLOR).map(([s, c]) => (
          <span className="kg-legend-item" key={s}>
            <i className="kg-swatch kg-swatch-round" style={{ background: c }} />
            {s}
          </span>
        ))}
      </div>
      <div className="kg-legend-row">
        <span className="kg-legend-title">关系</span>
        <span className="kg-legend-item">
          <i className="kg-line" style={{ background: REL_STYLE.prereq.stroke }} /> 前置
        </span>
        <span className="kg-legend-item">
          <i className="kg-line kg-line-dash" style={{ background: REL_STYLE.contrast.stroke }} /> 易混淆
        </span>
        <span className="kg-legend-item">
          <i className="kg-line" style={{ background: REL_STYLE.compose.stroke }} /> 组成
        </span>
        <span className="kg-legend-item">
          <i className="kg-line" style={{ background: REL_STYLE.cause.stroke }} /> 导致
        </span>
      </div>
    </div>
  );
}
