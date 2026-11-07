import type { CanvasProps } from '../registry';
import { Icon } from '../../shell/Icons';

function topLevelKeys(data: Record<string, unknown>): string[] {
  return Object.keys(data || {});
}

/**
 * 统一占位渲染器。
 * 未登记 / 尚未实现的 artifactType 都落在这里：显示 JSON 摘要 + "该画布开发中"，保证不崩。
 */
export function PlaceholderCanvas({ artifact }: CanvasProps) {
  const data = (artifact.data || {}) as Record<string, unknown>;
  const keys = topLevelKeys(data);
  const preview = JSON.stringify(data, null, 2);

  return (
    <div className="canvas-body">
      <div className="ph-banner">
        <span className="ph-icon">
          <Icon name="cube" size={18} />
        </span>
        <div>
          <strong>该画布开发中</strong>
          <p>
            已收到 <code>artifactType = {artifact.artifactType}</code> 的数据，渲染器排在后续迭代；
            当前用统一占位视图展示 JSON 摘要，不影响对话与证据链路。
          </p>
        </div>
      </div>

      {keys.length > 0 && (
        <div className="ph-keys">
          <span className="ph-keys-label">字段</span>
          {keys.map((k) => (
            <span className="chip" key={k}>
              {k}
            </span>
          ))}
        </div>
      )}

      <pre className="json-pre">{preview.length > 8000 ? `${preview.slice(0, 8000)}\n…（已截断）` : preview}</pre>
    </div>
  );
}
