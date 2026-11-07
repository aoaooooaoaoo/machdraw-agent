import type { CanvasFeature } from '../../lib/canvasFeature';
import { ThreeViewCanvas } from '../../modules/three/Canvas';
import { THREE_VIEW_DEMO_DATA } from '../../modules/three/demo';

const feature = {
  id: 'three_view',
  title: '三视图投影画布',
  hint: '按后端图纸坐标直出 SVG：三视图 · 虚线不可见轮廓 · 投影辅助线',
  artifactTypes: ['three_view'],
  order: 50,
  preview: {
    label: '查看三视图示例',
    data: THREE_VIEW_DEMO_DATA as unknown as Record<string, unknown>,
  },
  autoOpenCanvas: true,
  Component: ThreeViewCanvas,
} satisfies CanvasFeature;

export default feature;
