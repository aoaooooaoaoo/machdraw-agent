import type { CanvasFeature } from '../../lib/canvasFeature';
import { CalcCanvas } from '../../modules/calc/Canvas';
import { CALC_DEMO_DATA } from '../../modules/calc/demo';

const feature = {
  id: 'calc',
  title: '确定性计算画布',
  hint: '输入 → 公式步 → 结果 → 校核：临界/燃耗/反应性换算，每步可复核',
  artifactTypes: ['calc'],
  order: 20,
  preview: {
    label: '查看临界计算示例',
    data: CALC_DEMO_DATA as unknown as Record<string, unknown>,
  },
  autoOpenCanvas: true,
  Component: CalcCanvas,
} satisfies CanvasFeature;

export default feature;
