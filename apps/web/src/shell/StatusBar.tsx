import { useActiveSession, useAppStore } from '../lib/store';

/** 底部状态栏：把消息数 / 证据段数 / 覆盖率 / 耗时当产品信息展示（对齐参考作品）。 */
export function StatusBar() {
  const session = useActiveSession();
  const backendOnline = useAppStore((s) => s.backendOnline);
  const { messages, evidences, coverage, ms, frames } = session.stats;
  const streaming = session.streaming;

  const coveragePct = `${(coverage * 100).toFixed(1)}%`;

  return (
    <footer className="statusbar">
      <div className="status-left">
        <span className="status-item">
          <b>{messages}</b> 条消息
        </span>
        <span className="sep">·</span>
        <span className="status-item">
          证据 <b>{evidences}</b> 段
        </span>
        <span className="sep">·</span>
        <span className="status-item">
          覆盖率 <b>{coveragePct}</b>
        </span>
        <span className="sep">·</span>
        <span className="status-item">
          耗时 <b>{ms > 0 ? `${ms} ms` : '—'}</b>
        </span>
        <span className="sep">·</span>
        <span className="status-item status-dim">帧 {frames}</span>
      </div>

      <div className="status-right">
        {streaming ? (
          <span className="status-item status-live">
            <span className="spinner" /> 流式生成中…
          </span>
        ) : (
          <span className="status-item status-dim">就绪</span>
        )}
        <span className="sep">·</span>
        <span className={`status-item ${backendOnline === false ? 'status-bad' : ''}`}>
          <span
            className={`dot ${backendOnline === false ? 'dot-red' : backendOnline ? 'dot-green' : 'dot-gray'}`}
          />
          {backendOnline === false ? '后端离线' : 'SSE · fetch + ReadableStream'}
        </span>
      </div>
    </footer>
  );
}
