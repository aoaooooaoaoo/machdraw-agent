import type { CanvasFeature } from '../../lib/canvasFeature';
import { ToleranceCanvas } from '../../modules/tolerance/Canvas';
import { TOLERANCE_DEMO_DATA } from '../../modules/tolerance/demo';

const feature = {
  id: 'tolerance',
  title: '公差与配合画布',
  hint: '孔/轴的上下偏差、极限尺寸与公差带图',
  artifactTypes: ['tolerance'],
  order: 20,
  preview: {
    label: '查看公差带示例',
    data: TOLERANCE_DEMO_DATA as unknown as Record<string, unknown>,
  },
  autoOpenCanvas: true,
  Component: ToleranceCanvas,
} satisfies CanvasFeature;

export default feature;
