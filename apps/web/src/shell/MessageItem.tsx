import { useState } from 'react';
import type { ChatMessage, ToolCallState } from '../lib/types';
import { Icon } from './Icons';
import { Markdown } from './Markdown';

function ThinkingBlock({ text, streaming }: { text: string; streaming: boolean }) {
  const [open, setOpen] = useState(true);
  return (
    <div className="thinking">
      <button className="thinking-head" type="button" onClick={() => setOpen((v) => !v)}>
        <Icon name="spark" size={13} />
        <span className="thinking-title">思考过程</span>
        <span className="thinking-meta">
          {streaming ? '进行中…' : `${text.length} 字`}
        </span>
        <Icon name="chevron" size={14} className={`chev ${open ? 'is-open' : ''}`} />
      </button>
      {open && <div className="thinking-body">{text || '…'}</div>}
    </div>
  );
}

function ToolCard({ tool }: { tool: ToolCallState }) {
  const [open, setOpen] = useState(false);
  const argsText = Object.keys(tool.args || {}).length ? JSON.stringify(tool.args, null, 2) : '';
  return (
    <div className={`tool-card is-${tool.status}`}>
      <button className="tool-head" type="button" onClick={() => setOpen((v) => !v)}>
        <span className="tool-status">
          {tool.status === 'running' ? <span className="spinner" /> : <Icon name="check" size={13} />}
        </span>
        <span className="tool-label">{tool.label}</span>
        <span className="tool-name">{tool.name}</span>
        <span className="tool-hint">{tool.status === 'running' ? '调用中' : '已完成'}</span>
        <Icon name="chevron" size={14} className={`chev ${open ? 'is-open' : ''}`} />
      </button>
      {tool.summary && <div className="tool-summary">{tool.summary}</div>}
      {open && (
        <div className="tool-detail">
          {argsText && (
            <>
              <div className="tool-detail-label">参数</div>
              <pre>{argsText}</pre>
            </>
          )}
          {tool.detail && (
            <>
              <div className="tool-detail-label">返回</div>
              <pre>{tool.detail}</pre>
            </>
          )}
          {!argsText && !tool.detail && <div className="tool-detail-empty">（无更多内容）</div>}
        </div>
      )}
    </div>
  );
}

export function MessageItem({ message }: { message: ChatMessage }) {
  if (message.role === 'user') {
    return (
      <div className="msg msg-user">
        <div className="bubble-user">{message.content}</div>
        <div className="msg-avatar msg-avatar-user">我</div>
      </div>
    );
  }

  return (
    <div className="msg msg-assistant">
      <div className="msg-avatar msg-avatar-bot">教</div>
      <div className="msg-body">
        {message.thinking && (
          <ThinkingBlock text={message.thinking} streaming={message.streaming} />
        )}

        {message.tools.length > 0 && (
          <div className="tools">
            {message.tools.map((t) => (
              <ToolCard key={t.id} tool={t} />
            ))}
          </div>
        )}

        {message.content && <Markdown text={message.content} />}
        {message.streaming && !message.content && (
          <div className="msg-placeholder">
            <span className="spinner" /> 正在生成…
          </div>
        )}
        {message.streaming && message.content && <span className="stream-cursor" />}

        {message.error && (
          <div className="msg-error">
            <Icon name="alert" size={14} />
            <span>{message.error}</span>
          </div>
        )}

        {message.meta && !message.streaming && (
          <div className="msg-foot">
            <span>{message.meta.provider ?? '—'}</span>
            <span>·</span>
            <span>{message.meta.model ?? '—'}</span>
            {typeof message.meta.ms === 'number' && (
              <>
                <span>·</span>
                <span>{message.meta.ms} ms</span>
              </>
            )}
            <span>·</span>
            <span>{message.frames} 帧</span>
          </div>
        )}
      </div>
    </div>
  );
}
