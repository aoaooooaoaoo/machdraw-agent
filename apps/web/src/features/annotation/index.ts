import type { CanvasFeature } from '../../lib/canvasFeature';
import { AnnotationCanvas } from '../../modules/annotation/Canvas';

const feature = {
  id: 'annotation',
  title: '费曼/步骤标注画布',
  hint: '费曼追问与计算步骤标注：逐句三色标注 + 追问 + 轮次总评',
  artifactTypes: ['annotation'],
  order: 50,
  // ⚠ 必须 true：逐句三色标注**只在画布里**（中栏只输出 100 字左右的轮次概要），
  // 收起会把核心交付藏起来；而且红色的「待纠正」错句也在画布上，
  // 中栏那句「我在画布里故意写了一句错的」需要学生能立刻看到。
  autoOpenCanvas: true,
  Component: AnnotationCanvas,
} satisfies CanvasFeature;

export default feature;
