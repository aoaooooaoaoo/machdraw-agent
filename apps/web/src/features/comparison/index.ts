import type { CanvasFeature } from '../../lib/canvasFeature';
import { ComparisonCanvas } from '../../modules/comparison/Canvas';
import { COMPARISON_DEMO_DATA } from '../../modules/comparison/demo';

const feature = {
  id: 'comparison',
  title: '成对图辨析画布',
  hint: '成对图 + 差异点 + 随堂做题',
  artifactTypes: ['comparison'],
  order: 90,
  preview: {
    label: '查看辨析示例',
    data: COMPARISON_DEMO_DATA as unknown as Record<string, unknown>,
  },
  autoOpenCanvas: true,
  Component: ComparisonCanvas,
} satisfies CanvasFeature;

export default feature;
