/**
 * plot 画布的纯几何计算（不含 React，方便单独校验坐标/刻度）。
 *
 * 设计约束：
 * - 只用标准坐标 + `nice` 刻度，支持线性横轴与 log10 横轴；
 * - 依赖 `PlotData` 契约（series / markers / x_label / y_label / kind）；
 * - 输出可直接喂给 SVG 的像素坐标与刻度标签，渲染层只负责摆元素。
 */
import type { PlotData } from '../../lib/types';

export const SERIES_COLORS = [
  '#2563eb',
  '#ea580c',
  '#16a34a',
  '#7c3aed',
  '#dc2626',
  '#0891b2',
  '#b45309',
  '#0f766e',
];

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

export function superscript(n: number): string {
  return String(n)
    .split('')
    .map((c) => SUP[c] ?? c)
    .join('');
}

/** 轴刻度的「好看」步长：1 / 2 / 5 / 10 × 10ⁿ。 */
export function niceStep(raw: number): number {
  if (!(raw > 0) || !Number.isFinite(raw)) return 1;
  const pow = 10 ** Math.floor(Math.log10(raw));
  const norm = raw / pow;
  const mult = norm < 1.5 ? 1 : norm < 3 ? 2 : norm < 7 ? 5 : 10;
  return mult * pow;
}

export interface AxisTicks {
  lo: number;
  hi: number;
  ticks: number[];
}

/** 线性轴：向外取整到步长整数倍，保证首末刻度落在轴端。 */
export function linearTicks(min: number, max: number, target = 6): AxisTicks {
  let lo = min;
  let hi = max;
  if (!Number.isFinite(lo) || !Number.isFinite(hi)) return { lo: 0, hi: 1, ticks: [0, 1] };
  if (hi < lo) [lo, hi] = [hi, lo];
  if (hi - lo < 1e-12) {
    const pad = Math.abs(hi) > 0 ? Math.abs(hi) * 0.5 : 1;
    lo -= pad;
    hi += pad;
  }
  const step = niceStep((hi - lo) / Math.max(1, target - 1));
  const p = Math.max(0, -Math.floor(Math.log10(step))) + 1;
  let axisLo = Number((Math.floor(lo / step) * step).toFixed(p));
  let axisHi = Number((Math.ceil(hi / step) * step).toFixed(p));
  // 数据全为非负时，不把 0 以下的空白留出来
  if (min >= 0 && axisLo < 0) axisLo = 0;
  if (axisHi <= axisLo) axisHi = axisLo + step;
  const ticks: number[] = [];
  for (let v = axisLo, guard = 0; v <= axisHi + step * 1e-9 && guard < 200; v += step, guard += 1) {
    ticks.push(Number(v.toFixed(p)));
  }
  return { lo: axisLo, hi: ticks.length > 0 ? ticks[ticks.length - 1] : axisHi, ticks };
}

/** log10 轴：至少取整十次幂刻度；跨度 ≤3 个数量级时补 2/5 倍数。 */
export function logTicks(min: number, max: number): AxisTicks {
  if (!(min > 0) || !(max > 0)) return linearTicks(0, 1);
  if (max <= min) return { lo: min, hi: max, ticks: [min] };
  const startExp = Math.floor(Math.log10(min) - 1e-9);
  const endExp = Math.ceil(Math.log10(max) + 1e-9);
  const decades = endExp - startExp;
  const ks = decades <= 3 ? [1, 2, 5] : [1];
  const ticks: number[] = [];
  for (let e = startExp; e <= endExp; e += 1) {
    for (const k of ks) {
      const v = k * 10 ** e;
      if (v > 0 && v >= min * 0.999 && v <= max * 1.001) ticks.push(Number(v.toPrecision(6)));
    }
  }
  if (ticks.length < 2) {
    ticks.length = 0;
    ticks.push(min, max);
  }
  return { lo: ticks[0], hi: ticks[ticks.length - 1], ticks };
}

/** 刻度标签：log 轴写成 10ⁿ，线性轴按量级取舍。 */
export function tickLabel(v: number, isLog = false): string {
  if (!Number.isFinite(v)) return '—';
  if (isLog) {
    const exp = Math.round(Math.log10(v));
    return `10${superscript(exp)}`;
  }
  if (v === 0) return '0';
  if (Number.isInteger(v)) return String(v);
  const abs = Math.abs(v);
  if (abs < 0.01 || abs >= 1e5) {
    const exp = Math.floor(Math.log10(abs));
    const mant = Number((v / 10 ** exp).toPrecision(2));
    return `${mant}×10${superscript(exp)}`;
  }
  return String(Number(v.toPrecision(4)));
}

export interface SurveyedPoint {
  x: number;
  y: number;
}

export interface BuiltSeries {
  name: string;
  color: string;
  points: SurveyedPoint[];
  path: string;
}

export interface BuiltMarker {
  label?: string;
  x: number;
  y?: number;
  sx: number;
  sy?: number;
}

export interface PlotGeometry {
  width: number;
  height: number;
  plot: { left: number; right: number; top: number; bottom: number; width: number; height: number };
  xLog: boolean;
  xMin: number;
  xMax: number;
  yMin: number;
  yMax: number;
  xTicks: { value: number; label: string; pos: number }[];
  yTicks: { value: number; label: string; pos: number }[];
  series: BuiltSeries[];
  markers: BuiltMarker[];
  legend: { name: string; color: string }[];
  empty: boolean;
}

interface CleanSeries {
  name: string;
  color: string;
  points: SurveyedPoint[];
}

function cleanSeries(data: PlotData): CleanSeries[] {
  const raw = Array.isArray(data.series) ? data.series : [];
  return raw
    .map((s, i) => {
      const pts = (Array.isArray(s.points) ? s.points : [])
        .filter((p): p is [number, number] => Array.isArray(p) && p.length >= 2)
        .map((p) => ({ x: Number(p[0]), y: Number(p[1]) }))
        .filter((p) => Number.isFinite(p.x) && Number.isFinite(p.y))
        .sort((a, b) => a.x - b.x);
      return {
        name: s.name?.trim() || `系列 ${i + 1}`,
        color: SERIES_COLORS[i % SERIES_COLORS.length],
        points: pts,
      };
    })
    .filter((s) => s.points.length > 0);
}

/**
 * 把 plot data 换算成 SVG 像素坐标。
 * 宽高默认 520×360（右栏窄，字号/线宽按此比例设计）。
 */
export function buildPlotGeometry(data: PlotData, width = 520, height = 360): PlotGeometry {
  const plot = {
    left: 58,
    top: 24,
    right: width - 14,
    bottom: height - 44,
    width: width - 58 - 14,
    height: height - 24 - 44,
  };
  const series = cleanSeries(data);
  const markersRaw = Array.isArray(data.markers) ? data.markers : [];

  if (series.length === 0) {
    return {
      width,
      height,
      plot,
      xLog: false,
      xMin: 0,
      xMax: 1,
      yMin: 0,
      yMax: 1,
      xTicks: [],
      yTicks: [],
      series: [],
      markers: [],
      legend: [],
      empty: true,
    };
  }

  let xMin = Infinity;
  let xMax = -Infinity;
  let yMin = Infinity;
  let yMax = -Infinity;
  for (const s of series) {
    for (const p of s.points) {
      if (p.x < xMin) xMin = p.x;
      if (p.x > xMax) xMax = p.x;
      if (p.y < yMin) yMin = p.y;
      if (p.y > yMax) yMax = p.y;
    }
  }
  for (const m of markersRaw) {
    if (Number.isFinite(m.x)) {
      xMin = Math.min(xMin, m.x);
      xMax = Math.max(xMax, m.x);
    }
  }
  const xRatio = xMin > 0 && xMax > 0 ? xMax / xMin : Infinity;
  const xLog = Boolean((data.kind === 'spectrum' || xRatio >= 100) && xMin > 0 && xMax > 0);

  const xPad = (xMax - xMin) * 0.04; // log 轴下用相对留白，不影响刻度
  const xAxis = xLog ? logTicks(xMin, xMax) : linearTicks(xMin - xPad, xMax + xPad, 6);
  const yAxis = linearTicks(yMin, yMax, 6);

  const plotW = plot.width;
  const plotH = plot.height;

  const xPos = (v: number): number => {
    if (xLog) {
      const lo = Math.log10(xAxis.lo);
      const hi = Math.log10(xAxis.hi);
      const span = hi - lo || 1;
      return plot.left + ((Math.log10(v) - lo) / span) * plotW;
    }
    const span = xAxis.hi - xAxis.lo || 1;
    return plot.left + ((v - xAxis.lo) / span) * plotW;
  };
  const yPos = (v: number): number => {
    const span = yAxis.hi - yAxis.lo || 1;
    return plot.bottom - ((v - yAxis.lo) / span) * plotH;
  };
  const clampX = (px: number) => Math.max(plot.left, Math.min(plot.right, px));

  const builtSeries: BuiltSeries[] = series.map((s) => {
    const pts = s.points.map((p) => ({ x: clampX(xPos(p.x)), y: yPos(p.y) }));
    const path = pts
      .map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(2)},${p.y.toFixed(2)}`)
      .join(' ');
    return { name: s.name, color: s.color, points: pts, path };
  });

  const markers: BuiltMarker[] = markersRaw
    .filter((m) => Number.isFinite(m.x))
    .map((m) => {
      const sx = clampX(xPos(m.x));
      const hasY = typeof m.y === 'number' && Number.isFinite(m.y);
      return {
        label: m.label,
        x: m.x,
        y: hasY ? (m.y as number) : undefined,
        sx,
        sy: hasY ? yPos(m.y as number) : undefined,
      };
    });

  return {
    width,
    height,
    plot,
    xLog,
    xMin: xAxis.lo,
    xMax: xAxis.hi,
    yMin: yAxis.lo,
    yMax: yAxis.hi,
    xTicks: xAxis.ticks.map((v) => ({ value: v, label: tickLabel(v, xLog), pos: xPos(v) })),
    yTicks: yAxis.ticks.map((v) => ({ value: v, label: tickLabel(v), pos: yPos(v) })),
    series: builtSeries,
    markers,
    legend: series.map((s) => ({ name: s.name, color: s.color })),
    empty: false,
  };
}
