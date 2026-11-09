import type { CanvasFeature } from '../../lib/canvasFeature';
import { WrongbookCanvas } from '../../modules/wrongbook/Canvas';

const feature = {
  id: 'wrongbook',
  title: '错题诊改画布',
  hint: '六步拆解：原题 → 错误作答 → 根因 → 溯源 → 正解 → 避坑',
  artifactTypes: ['wrongbook'],
  order: 70,
  // 对话型：六步诊断正文在对话流，画布不抢屏
  autoOpenCanvas: false,
  Component: WrongbookCanvas,
} satisfies CanvasFeature;

export default feature;
