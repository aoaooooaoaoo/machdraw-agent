import type { ComparisonArtifactData } from '../../lib/types';

/**
 * comparison 本地示例（半剖 vs 局部剖）。
 * 后端成对图数据未到时用现有图库 SVG 占位自测；接口就绪后直接用真实 file。
 */
export const COMPARISON_DEMO_DATA: ComparisonArtifactData = {
  pair_id: 'PAIR-DEMO-BAN-JUBU',
  file: 'FIG-SANSHITU-BASE.svg',
  title: '半剖视图 vs 局部剖视图',
  a: { label: 'A', caption: '半剖视图', 正确性: '正确' },
  b: { label: 'B', caption: '局部剖视图', 正确性: '正确' },
  differences: [
    {
      no: 1,
      name: '分界线',
      a_desc: '用细点画线（对称中心线）分界',
      b_desc: '用波浪线分界',
      why: '半剖以对称中心线为界，分界处本身就是对称轴；局部剖只剖开局部，其余保持外形，所以用断裂线（波浪线）表示剖切范围。',
    },
    {
      no: 2,
      name: '适用对象',
      a_desc: '对称机件，兼顾内外结构',
      b_desc: '不对称机件，或只需表达局部内部结构',
      why: '半剖要求机件对称才能“一半剖一半视图”；局部剖没有对称要求，适用范围更广。',
    },
    {
      no: 3,
      name: '虚线处理',
      a_desc: '视图部分一般省略虚线',
      b_desc: '未剖开的其余部分按需保留虚线',
      why: '半剖的内外结构都已表达清楚，再画虚线会让图面杂乱；局部剖未表达到的内部结构仍需要虚线补充。',
    },
  ],
  question: {
    stem: '下列关于半剖视图与局部剖视图分界线的说法，正确的是：',
    options: [
      '半剖用波浪线，局部剖用细点画线',
      '半剖用细点画线，局部剖用波浪线',
      '两者都用波浪线',
      '两者都用细点画线',
    ],
    answer_index: 1,
    explain:
      '半剖视图的分界必须是对称中心线（细点画线），不能画成波浪线；局部剖视图的分界用波浪线表示断裂边界。',
  },
  kp_ids: ['KP-EXPR-008'],
};
