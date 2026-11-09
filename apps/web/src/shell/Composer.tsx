import { useEffect, useRef, useState } from 'react';
import { useActiveSession, useAppStore } from '../lib/store';
import { Icon } from './Icons';

const MAX_TEXTAREA = 180;

export function Composer() {
  const session = useActiveSession();
  const setDraft = useAppStore((s) => s.setDraft);
  const send = useAppStore((s) => s.send);
  const stop = useAppStore((s) => s.stop);
  const account = useAppStore((s) => s.account);

  const taRef = useRef<HTMLTextAreaElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const [attachment, setAttachment] = useState<string | null>(null);

  const streaming = session.streaming;
  const draft = session.draft;
  const canSend = Boolean(draft.trim()) && !streaming && Boolean(account);

  // 自适应高度
  useEffect(() => {
    const el = taRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, MAX_TEXTAREA)}px`;
  }, [draft]);

  // 画布点「围绕此段追问」→ 写入 draft 后自动聚焦
  useEffect(() => {
    if (draft) taRef.current?.focus();
  }, [draft]);

  function submit() {
    if (!canSend) return;
    const text = attachment
      ? `📎 附件：${attachment}（后端暂未开放文件上传，此处仅记录文件名）\n\n${draft.trim()}`
      : draft.trim();
    setAttachment(null);
    void send(text);
  }

  return (
    <div className="composer">
      {attachment && (
        <div className="attach-chip">
          <Icon name="paperclip" size={12} />
          <span>{attachment}</span>
          <button type="button" className="chip-x" onClick={() => setAttachment(null)} aria-label="移除附件">
            <Icon name="x" size={11} />
          </button>
        </div>
      )}

      <div className="composer-box">
        <textarea
          ref={taRef}
          className="composer-input"
          rows={1}
          value={draft}
          placeholder={streaming ? '正在生成回答…（可点停止）' : '问一个核反应堆物理问题，或从左侧模块进入专项对话'}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
              e.preventDefault();
              submit();
            }
          }}
          disabled={!account}
        />

        <div className="composer-actions">
          <input
            ref={fileRef}
            type="file"
            className="hidden-input"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) setAttachment(file.name);
              e.target.value = '';
            }}
          />
          <button
            className="icon-btn"
            type="button"
            title="添加附件（后端暂未开放上传，仅记录文件名）"
            onClick={() => fileRef.current?.click()}
            disabled={streaming}
          >
            <Icon name="paperclip" size={17} />
          </button>

          <span className="composer-hint">Enter 发送 · Shift+Enter 换行</span>

          {streaming ? (
            <button className="btn btn-stop" type="button" onClick={stop}>
              <Icon name="stop" size={14} /> 停止
            </button>
          ) : (
            <button className="btn btn-primary btn-send" type="button" disabled={!canSend} onClick={submit}>
              <Icon name="send" size={15} /> 发送
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
