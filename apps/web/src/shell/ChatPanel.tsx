import { useEffect, useRef } from 'react';
import { useActiveSession, useAppStore } from '../lib/store';
import { Icon } from './Icons';
import { MessageItem } from './MessageItem';
import { Composer } from './Composer';

/** 中栏：对话区（消息流 / 思考块 / 工具卡 / 流式光标 / 输入框）。 */
export function ChatPanel() {
  const modules = useAppStore((s) => s.modules);
  const activeFeature = useAppStore((s) => s.activeFeature);
  const send = useAppStore((s) => s.send);
  const globalError = useAppStore((s) => s.globalError);
  const dismissGlobalError = useAppStore((s) => s.dismissGlobalError);
  const session = useActiveSession();

  const listRef = useRef<HTMLDivElement>(null);
  const stickRef = useRef(true);

  const activeModule = modules.find((m) => m.id === activeFeature);

  // 贴底滚动：只有用户本来就在底部时才跟着流式输出走
  useEffect(() => {
    const el = listRef.current;
    if (el && stickRef.current) el.scrollTop = el.scrollHeight;
  }, [session.messages, session.streaming]);

  // 新消息（新一轮提问）出现时强制回到底部，避免上一次手动上翻后新回答落在视口外
  useEffect(() => {
    const el = listRef.current;
    if (el) el.scrollTop = el.scrollHeight;
    stickRef.current = true;
  }, [session.messages.length]);

  function onScroll() {
    const el = listRef.current;
    if (!el) return;
    stickRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
  }

  return (
    <main className="chat">
      <div className="chat-head">
        <div className="chat-title-row">
          <h2 className="chat-title">{activeModule?.name ?? '对话'}</h2>
          <span className="chat-feature mono">{activeFeature}</span>
        </div>
        <p className="chat-desc">{activeModule?.desc ?? '选择左侧模块，或直接提问'}</p>
        <div className="chat-badges">
          {(activeModule?.canvas_kinds ?? []).map((k) => (
            <span className="badge badge-canvas" key={k}>
              画布 · {k}
            </span>
          ))}
          {(activeModule?.tools ?? []).map((t) => (
            <span className="badge" key={t}>
              {t}
            </span>
          ))}
        </div>
      </div>

      {globalError && (
        <div className="global-error">
          <Icon name="alert" size={14} />
          <span>{globalError}</span>
          <button className="icon-btn" type="button" onClick={dismissGlobalError}>
            <Icon name="x" size={13} />
          </button>
        </div>
      )}

      <div className="chat-scroll" ref={listRef} onScroll={onScroll}>
        {session.messages.length === 0 ? (
          <div className="chat-empty">
            <div className="empty-mark">
              <Icon name={activeModule?.icon ?? 'chat'} size={26} />
            </div>
            <h3>{activeModule?.name ?? '开始提问'}</h3>
            <p className="empty-desc">{activeModule?.desc ?? '输入问题开始对话'}</p>
            {(activeModule?.entry_examples ?? []).length > 0 && (
              <div className="examples">
                <div className="examples-label">试试这些入口</div>
                <div className="examples-list">
                  {activeModule!.entry_examples.map((ex) => (
                    <button
                      className="example-chip"
                      type="button"
                      key={ex}
                      onClick={() => void send(ex)}
                    >
                      <Icon name="spark" size={12} />
                      {ex}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="msg-list">
            {session.messages.map((m) => (
              <MessageItem key={m.id} message={m} />
            ))}
          </div>
        )}
      </div>

      <Composer />
    </main>
  );
}
