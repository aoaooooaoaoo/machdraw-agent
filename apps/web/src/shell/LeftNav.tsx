import { useAppStore } from '../lib/store';
import { Icon } from './Icons';

/** 左栏：模块导航。模块清单来自 GET /api/modules，中文名不硬编码。 */
export function LeftNav() {
  const modules = useAppStore((s) => s.modules);
  const modulesError = useAppStore((s) => s.modulesError);
  const activeFeature = useAppStore((s) => s.activeFeature);
  const setActiveFeature = useAppStore((s) => s.setActiveFeature);
  const health = useAppStore((s) => s.health);

  return (
    <aside className="leftnav">
      <div className="leftnav-head">
        <span>模块导航</span>
        <span className="count-badge">{modules.length}</span>
      </div>

      <nav className="leftnav-list">
        {modules.map((m) => {
          const active = m.id === activeFeature;
          return (
            <button
              key={m.id}
              type="button"
              className={`nav-item ${active ? 'is-active' : ''}`}
              onClick={() => setActiveFeature(m.id)}
              title={m.desc || m.name}
            >
              <span className="nav-icon">
                <Icon name={m.icon} size={17} />
              </span>
              <span className="nav-text">
                <span className="nav-name">{m.name}</span>
                {m.canvas_kinds.length > 0 && (
                  <span className="nav-meta">{m.canvas_kinds.join(' · ')}</span>
                )}
              </span>
              {active && <span className="nav-dot" />}
            </button>
          );
        })}
        {modules.length === 0 && !modulesError && (
          <div className="nav-empty">正在加载模块…</div>
        )}
        {modulesError && (
          <div className="nav-empty is-error">
            <Icon name="alert" size={14} /> 模块加载失败：{modulesError}
          </div>
        )}
      </nav>

      <div className="leftnav-foot">
        <div className="foot-row">
          <span>知识库</span>
          <span className="mono">
            {health ? `${health.chunks} 段 · ${health.docs} 文档` : '—'}
          </span>
        </div>
        <div className="foot-row">
          <span>门控 τ</span>
          <span className="mono">{health ? health.gate_tau.toFixed(2) : '—'}</span>
        </div>
        {health && health.warnings.length > 0 && (
          <div className="foot-warn" title={health.warnings.join('\n')}>
            <Icon name="alert" size={12} />
            <span>{health.warnings[0]}</span>
          </div>
        )}
        <div className="foot-hint">SSE · fetch + ReadableStream</div>
      </div>
    </aside>
  );
}
