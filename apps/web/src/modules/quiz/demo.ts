import type { QuizArtifactData } from '../../lib/types';

/**
 * quiz 本地示例：用真实知识库 chunk 内容自测渲染器。
 * 后端 /api/quiz/explain 就绪前，"看答案解析"会走到空态。
 */
export const QUIZ_DEMO_DATA: QuizArtifactData = {
  answer_withheld: true,
  quality_note: '题面来自扫描件 OCR，存在错字；仅供练习，正式考核请以校对后的题面为准。',
  questions: [
    {
      chunkId: 'chk_KP_0005_0016',
      documentTitle: '机械制图知识点手册（自建）',
      section: '第五章 组合体的视图与形体构型 › 5.4 组合体的尺寸标注',
      content:
        '**尺寸链不封闭**：同一方向首尾相接、形成封闭回路的尺寸链称为封闭尺寸链。封闭尺寸链会使各尺寸互相制约，加工误差累积后必然出现矛盾，因此标注时不允许出现封闭尺寸链——应去掉一个最不重要的尺寸，留出一个“开口环”，让误差落在该环上。',
    },
    {
      chunkId: 'chk_KP_0001_0021',
      documentTitle: '机械制图知识点手册（自建）',
      section: '第七章 机件的常用表达方法 › 7.4 断面图',
      content:
        '**断面图与剖视图的区别**：断面图只画出剖切面与机件接触的断面形状，不画剖切面后面的可见轮廓线；剖视图既要画出断面形状，又要画出剖切面后面所有可见的轮廓线。因此断面图图形简洁，剖视图表达更完整，二者不能混用。',
    },
  ],
};
