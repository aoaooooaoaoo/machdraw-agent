import type { PlotData } from '../../lib/types';

/**
 * plot 画布本地示例：点堆阶跃响应（单组缓发中子近似）。
 *
 * 输入：ρ = +0.2$ = 0.2β、β = 0.0065、瞬发中子寿命 ℓ = 1e-4 s、λ = 0.0784 s⁻¹。
 * 初始稳态 n/n0 = 1，t = 0 施加正阶跃；解点堆方程
 *   dn/dt = (ρ − β)/ℓ · n + λc
 *   dc/dt = β/ℓ · n − λc
 * 得 n(t)/n0 = A·e^{ω₁t} + B·e^{ω₂t}，其中 ω₁,ω₂ 是特征方程
 *   ℓω² + (β − ρ + λℓ)ω − λρ = 0
 * 的两个根；A + B = 1，c(0) 取稳态值。
 *
 * 物理结果：t→0⁺ 出现瞬跳，比值为 β/(β − ρ) ≈ 1.25；
 * 随后按渐近周期 T ≈ 1/ω₁ ≈ 50 s 指数上升，20 s 时约 1.84。
 *
 * 为什么是「示例数据」：后端 kinetics_calc 尚未联调时用它演示渲染器；
 * 真实对话会下发六组缓发中子的计算结果，画布上会标注「示例」。
 * 注：任务书里「20 s 升到约 11」对应更强的反应性（约 +0.5$）；此处按给定的
 * ρ=+0.2$ 用解析解如实生成，避免示例曲线与标注输入不自洽。
 */

const RHO_DOLLAR = 0.2;
const BETA = 0.0065;
const L = 1e-4;
const LAMBDA = 0.0784;
const T_END = 20;
const RHO = RHO_DOLLAR * BETA;

interface ModeSolution {
  w1: number;
  w2: number;
  a: number;
  b: number;
}

/** 单组缓发中子近似下，阶跃反应性后的解析解系数。 */
function solveModes(rho: number, l: number, beta: number, lambda: number): ModeSolution {
  const bb = beta - rho + lambda * l;
  const disc = bb * bb + 4 * l * lambda * rho; // 特征方程 c = −λρ，故 −4ac = +4ℓλρ
  const sq = Math.sqrt(disc);
  const w1 = (-bb + sq) / (2 * l);
  const w2 = (-bb - sq) / (2 * l);
  const k1 = 1 / (w1 + lambda);
  const k2 = 1 / (w2 + lambda);
  const a = (1 / lambda - k2) / (k1 - k2);
  return { w1, w2, a, b: 1 - a };
}

function responseAt(t: number, s: ModeSolution): number {
  return s.a * Math.exp(s.w1 * t) + s.b * Math.exp(s.w2 * t);
}

const MODES = solveModes(RHO, L, BETA, LAMBDA);

function roundTo(v: number, digits: number): number {
  const p = 10 ** digits;
  return Math.round(v * p) / p;
}

/** 0~20 s：先 0.002 s 细步长抓瞬跳，再 0.25 s 步长画指数段；共 91 个点。 */
function buildStepResponse(): [number, number][] {
  const pts: [number, number][] = [];
  for (let t = 0; t <= 0.02 + 1e-12; t += 0.002) {
    pts.push([roundTo(t, 3), roundTo(responseAt(t, MODES), 5)]);
  }
  for (let t = 0.05; t <= T_END + 1e-9; t += 0.25) {
    pts.push([roundTo(t, 3), roundTo(responseAt(t, MODES), 5)]);
  }
  return pts;
}

const POINTS = buildStepResponse();
const PERIOD = 1 / MODES.w1;
const PROMPT_JUMP = BETA / (BETA - RHO);
const N_AT_20 = responseAt(T_END, MODES);

export const PLOT_DEMO_DATA: PlotData = {
  kind: 'curve',
  title: '点堆阶跃响应（ρ = +0.2$）',
  x_label: 't / s',
  y_label: 'n(t) / n₀',
  series: [{ name: '中子密度 n/n₀', points: POINTS }],
  markers: [
    { x: 0, y: 1, label: 't=0 阶跃 ρ=+0.2$' },
    { x: T_END, label: '20 s' },
  ],
  results: [
    { name: '反应性 ρ', value: roundTo(RHO, 6), unit: 'Δk/k', note: '+0.2$' },
    { name: '瞬跳比 β/(β−ρ)', value: roundTo(PROMPT_JUMP, 3), unit: '—', note: '阶跃后 0⁺ 的 n/n₀' },
    { name: '渐近周期 T', value: roundTo(PERIOD, 2), unit: 's', note: '1/ω₁' },
    { name: 't = 20 s 时 n/n₀', value: roundTo(N_AT_20, 3), unit: '—', note: '示例曲线末点' },
    { name: '采样点数', value: POINTS.length, unit: '点', note: '前 0.02 s 细步长' },
  ],
  note:
    '示例数据：单组缓发中子近似（β=0.0065、ℓ=1e-4 s、λ=0.0784 s⁻¹），初始稳态 n/n₀=1，' +
    't=0 施加 +0.2$ 阶跃；曲线为解析解 A·e^{ω₁t}+B·e^{ω₂t}，未计温度反馈与六组缓发中子结构。',
  refs: ['教材 第八章 8.2 节'],
};
