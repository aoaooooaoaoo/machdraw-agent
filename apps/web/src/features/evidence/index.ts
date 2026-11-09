import type { CanvasFeature } from '../../lib/canvasFeature';
import { EvidenceCanvas } from '../../modules/evidence/Canvas';

const feature = {
  id: 'evidence',
  title: '证据溯源画布',
  hint: '每条结论可回翻到教材/课件原文：文档 · 章节 · chunk_id · 相关度',
  artifactTypes: ['evidence'],
  order: 10,
  // 例外：证据溯源是核心交付，收起会让学生看不到出处；保留自动展开。
  autoOpenCanvas: true,
  Component: EvidenceCanvas,
} satisfies CanvasFeature;

export default feature;
