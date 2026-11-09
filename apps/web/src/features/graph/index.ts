import type { CanvasFeature } from '../../lib/canvasFeature';
import { GraphCanvas } from '../../modules/graph/Canvas';
import { GraphPage } from './Page';

const feature = {
  id: 'graph',
  title: '知识图谱画布',
  hint: '核反应堆物理知识图谱 · 前置依赖 · 易混淆对比，点节点换焦点',
  artifactTypes: ['graph'],
  order: 80,
  autoOpenCanvas: true,
  Component: GraphCanvas,
  page: GraphPage,
} satisfies CanvasFeature;

export default feature;
