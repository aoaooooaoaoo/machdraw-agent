import type { CanvasFeature } from '../../lib/canvasFeature';
import { CoachCanvas } from '../../modules/coach/Canvas';

const feature = {
  id: 'coach',
  title: '作图教练画布',
  hint: '圆弧连接分步作图 / 螺纹比例画法',
  artifactTypes: ['coach'],
  order: 40,
  autoOpenCanvas: true,
  Component: CoachCanvas,
} satisfies CanvasFeature;

export default feature;
