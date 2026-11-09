import type { CanvasFeature } from '../../lib/canvasFeature';
import { PlotCanvas } from '../../modules/plot/Canvas';
import { PLOT_DEMO_DATA } from '../../modules/plot/demo';

const feature = {
  id: 'plot',
  title: '曲线与分布画布',
  hint: '纯 SVG 折线：能谱 / 阶跃响应 / 中毒曲线 · 自动 nice 刻度 · 能谱自动对数轴',
  artifactTypes: ['plot'],
  order: 30,
  preview: {
    label: '查看点堆阶跃响应示例',
    data: PLOT_DEMO_DATA as unknown as Record<string, unknown>,
  },
  autoOpenCanvas: true,
  Component: PlotCanvas,
} satisfies CanvasFeature;

export default feature;
