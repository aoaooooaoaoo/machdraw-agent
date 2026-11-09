import type { QuizArtifactData } from '../../lib/types';

/**
 * quiz 本地示例：用核反应堆物理知识点内容自测渲染器。
 * 后端 /api/quiz/explain 就绪前，「看答案解析」会走到空态。
 */
export const QUIZ_DEMO_DATA: QuizArtifactData = {
  answer_withheld: true,
  quality_note: '题面取自教材/习题解答整理稿；仅供练习，正式考核请以校对后的题面为准。',
  questions: [
    {
      chunkId: 'chk_KP_DIFF_0012',
      documentTitle: '核反应堆物理知识点手册（自建）',
      section: '第四章 中子扩散理论与计算 › 4.2 单群扩散临界条件',
      content:
        '**单群临界条件**：裸堆达到临界时，材料曲率等于几何曲率，即 k∞ = 1 + M²B²。其中 M² = L² + τ 为徙动面积，B² 为几何曲率。若 Bg² > Bm²，则泄漏大于增殖，k_eff < 1，堆芯次临界；反之超临界。',
    },
    {
      chunkId: 'chk_KP_BURN_0007',
      documentTitle: '核反应堆物理知识点手册（自建）',
      section: '第六章 燃耗与中毒 › 6.2 氙中毒与停堆碘坑',
      content:
        '**停堆碘坑**：停堆后，I-135 仍按半衰期约 6.6 h 继续衰变生成 Xe-135，而 Xe-135 因中子通量消失不再被燃耗掉，只能按自身半衰期约 9.2 h 衰变，因此氙浓度先升后降，形成“碘坑”。反应性最强的时刻出现在停堆后数小时，可能使堆芯在一段时间内无法重新启动。',
    },
  ],
};
