import type { ToleranceArtifactData } from '../../lib/types';

/**
 * 公差画布的本地示例数据（Ø30 H7/k6）。
 * 为什么需要它：后端 app/domain/tolerance.py 尚未就绪，tolerance artifact 暂时到不了前端。
 * 数据按 orchestrator.py:90-125 已写死的 solve_fit 返回形状构造，仅用于演示渲染器；
 * 画布上会明确标注「示例」，不与真实后端结果混淆。
 */
export const TOLERANCE_DEMO_DATA: ToleranceArtifactData = {
  basic_size: 30,
  system: '基孔制',
  hole: { code: 'H7', IT: 0.021, ES: 0.021, EI: 0, max: 30.021, min: 30.0 },
  shaft: { code: 'k6', IT: 0.013, es: 0.015, ei: 0.002, max: 30.015, min: 30.002 },
  fit: {
    type: '过渡配合',
    max_gap: 0.019,
    min_gap: -0.015,
    max_interference: 0.015,
    note: '孔 H7 与轴 k6 组合，可能出现间隙也可能出现过盈，属于过渡配合；装配多用过渡或小过盈。',
  },
  tolerance_zone: { hole: ['EI', 'ES'], shaft: ['ei', 'es'] },
  process_hint:
    'Ø30 H7 孔建议精铰或磨削；k6 轴建议精车后磨削。装配时优先压入或温差装配，避免反复敲击。',
  refs: ['GB/T 1800.1-2020', 'GB/T 1800.2-2020'],
};
