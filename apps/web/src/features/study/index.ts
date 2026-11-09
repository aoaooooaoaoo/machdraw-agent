import type { CanvasFeature } from '../../lib/canvasFeature';
import { StudyCanvas } from './Canvas';
import { StudyPage } from './Page';

const feature = {
  id: 'study',
  title: '学习计划',
  hint: '今日任务、到期复习、下一步学什么',
  artifactTypes: [],
  order: 90,
  Component: StudyCanvas,
  page: StudyPage,
} satisfies CanvasFeature;

export default feature;
