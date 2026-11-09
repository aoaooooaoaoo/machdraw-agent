import { useState } from 'react';
import type { ChatMessage, ToolCallState } from '../lib/types';
import { copyText } from '../lib/ui';
import { toast } from '../lib/ui';
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

interface MessageItemProps {
  message: ChatMessage;
  /** 最后一条助手消息：显示「重新回答」 */
  canRegenerate?: boolean;
  onRegenerate?: () => void;
  /** @deprecated 兼容旧调用 */
  isLast?: boolean;
}

export function MessageItem({ message, canRegenerate, onRegenerate }: MessageItemProps) {
  const [speaking, setSpeaking] = useState(false);

  function speak(text: string) {
    if (!('speechSynthesis' in window)) {
      toast('当前浏览器不支持朗读', 'info');
      return;
    }
    if (speaking) {
      window.speechSynthesis.cancel();
      setSpeaking(false);
      return;
    }
    const plain = text
      .replace(/```[\s\S]*?```/g, '（代码略）')
      .replace(/[#*_`>|]/g, '')
      .replace(/\n{2,}/g, '\n')
      .slice(0, 3000);
    const utter = new SpeechSynthesisUtterance(plain);
    utter.lang = 'zh-CN';
    utter.rate = 1.03;
    utter.onend = () => setSpeaking(false);
    utter.onerror = () => setSpeaking(false);
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utter);
    setSpeaking(true);
  }

  if (message.role === 'user') {
    return (
      <div className="msg msg-user">
        <div className="bubble-user">{message.content}</div>
        <div className="msg-avatar msg-avatar-user">我</div>
        <button
          className="msg-mini-btn msg-user-copy"
          type="button"
          title="复制我的问题"
          aria-label="复制我的问题"
          onClick={() => void copyText(message.content, '问题已复制')}
        >
          <Icon name="copy" size={13} />
        </button>
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

        {!message.streaming && message.content && (
          <div className="msg-actions">
            <button
              className="msg-action"
              type="button"
              title="复制回答"
              onClick={() => void copyText(message.content, '回答已复制')}
            >
              <Icon name="copy" size={13} />
              <span>复制</span>
            </button>
            <button
              className="msg-action"
              type="button"
              title="朗读回答"
              onClick={() => speak(message.content)}
            >
              <Icon name="volume" size={13} />
              <span>{speaking ? '停止' : '朗读'}</span>
            </button>
            {canRegenerate && onRegenerate && (
              <button className="msg-action" type="button" title="用同一个问题重新回答" onClick={onRegenerate}>
                <Icon name="refresh" size={13} />
                <span>重新回答</span>
              </button>
            )}
            <span className="msg-actions-spacer" />
            {message.meta && (
              <span className="msg-foot-inline">
                {message.meta.provider ?? '—'}
                {typeof message.meta.ms === 'number' && <> · {message.meta.ms} ms</>}
                {' · '}
                {message.frames} 帧
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
