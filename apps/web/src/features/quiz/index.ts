import type { CanvasFeature } from '../../lib/canvasFeature';
import { QuizCanvas } from '../../modules/quiz/Canvas';
import { QUIZ_DEMO_DATA } from '../../modules/quiz/demo';

const feature = {
  id: 'quiz',
  title: '题卡画布',
  hint: '题库抽取的题目（答案隔离）+ 展开看解析',
  artifactTypes: ['quiz'],
  order: 60,
  preview: {
    label: '查看题卡示例',
    data: QUIZ_DEMO_DATA as unknown as Record<string, unknown>,
  },
  autoOpenCanvas: false,
  Component: QuizCanvas,
} satisfies CanvasFeature;

export default feature;
