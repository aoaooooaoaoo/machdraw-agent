import type { FeatureProps } from '../../lib/canvasFeature';
import { Icon } from '../../shell/Icons';

/** 学习计划是整页模块；这个 Canvas 只在极端情况下（被当作画布注入）兜底。 */
export function StudyCanvas(_props: FeatureProps) {
  return (
    <div className="canvas-empty-inline">
      <Icon name="target" size={20} />
      <p>学习计划是整页模块，请从左侧「学习计划」进入。</p>
    </div>
  );
}
