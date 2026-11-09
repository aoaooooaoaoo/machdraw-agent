import { useEffect, useRef, useState } from 'react';
import { useActiveSession, useAppStore } from '../lib/store';
import { ocrImage } from '../lib/api';
import { MOD_KEY, toast } from '../lib/ui';
import { Icon } from './Icons';

const MAX_TEXTAREA = 180;

interface Attachment {
  name: string;
  dataUrl: string;
}

export function Composer() {
  const session = useActiveSession();
  const setDraft = useAppStore((s) => s.setDraft);
  const send = useAppStore((s) => s.send);
  const stop = useAppStore((s) => s.stop);
  const clearSession = useAppStore((s) => s.clearSession);
  const account = useAppStore((s) => s.account);

  const taRef = useRef<HTMLTextAreaElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const recRef = useRef<{ stop: () => void } | null>(null);
  const draftRef = useRef(session.draft);
  const [attachment, setAttachment] = useState<Attachment | null>(null);
  const [listening, setListening] = useState(false);
  const [ocrBusy, setOcrBusy] = useState(false);

  const streaming = session.streaming;
  const draft = session.draft;
  const canSend = (Boolean(draft.trim()) || Boolean(attachment)) && !streaming && Boolean(account);

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

  function toggleMic() {
    const w = window as unknown as {
      SpeechRecognition?: new () => SpeechRecognitionLike;
      webkitSpeechRecognition?: new () => SpeechRecognitionLike;
    };
    const SR = w.SpeechRecognition || w.webkitSpeechRecognition;
    if (!SR) {
      toast('当前浏览器不支持语音输入（建议 Chrome / Edge）', 'info');
      return;
    }
    if (listening) {
      recRef.current?.stop();
      setListening(false);
      return;
    }
    const rec = new SR();
    rec.lang = 'zh-CN';
    rec.continuous = false;
    rec.interimResults = true;
    let finalText = '';
    rec.onresult = (ev: SpeechResultLike) => {
      let text = '';
      for (let i = 0; i < ev.results.length; i += 1) text += ev.results[i][0].transcript;
      finalText = text;
      setDraft((draftRef.current ? draftRef.current + ' ' : '') + text);
    };
    rec.onend = () => {
      setListening(false);
      recRef.current = null;
      if (finalText) toast('语音已转文字');
    };
    rec.onerror = () => {
      setListening(false);
      toast('语音识别失败，请检查麦克风权限', 'error');
    };
    recRef.current = rec;
    setListening(true);
    try {
      rec.start();
    } catch {
      setListening(false);
    }
  }

  // 用 ref 保存最新 draft，给语音回调拼接口语
  useEffect(() => {
    draftRef.current = draft;
  }, [draft]);

  async function submit() {
    if (!canSend) return;
    const base = draft.trim();
    let text = base;
    if (attachment) {
      setOcrBusy(true);
      try {
        const res = await ocrImage(attachment.dataUrl);
        const recognized = (res.text || '').trim();
        text = recognized
          ? `📷 拍题图片识别：\n${recognized}\n\n${base ? `问题：${base}` : '请讲解这道题。'}`
          : `${base || '请讲解这张图片里的题目。'}\n\n（图片已附，但 OCR 未识别出文字，请补充描述）`;
      } catch (err) {
        text = `${base || '请讲解这张图片里的题目。'}\n\n（图片 OCR 不可用：${(err as Error)?.message || '未知错误'}）`;
      } finally {
        setOcrBusy(false);
      }
    }
    setAttachment(null);
    void send(text);
  }

  return (
    <div className="composer">
      {attachment && (
        <div className="attach-chip">
          <img src={attachment.dataUrl} alt="待识别图片" className="attach-thumb" />
          <span>{attachment.name}</span>
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
          placeholder={
            streaming
              ? '正在生成回答…（可点停止）'
              : attachment
                ? '可补充问题，或直接发送让助教识别图片里的题目'
                : '问一个核反应堆物理问题，或从左侧模块进入专项对话'
          }
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
              e.preventDefault();
              void submit();
            }
          }}
          disabled={!account}
        />

        <div className="composer-actions">
          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            capture="environment"
            className="hidden-input"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) {
                const reader = new FileReader();
                reader.onload = () => {
                  const dataUrl = String(reader.result || '');
                  if (dataUrl) setAttachment({ name: file.name, dataUrl });
                  toast('已附图片，发送时自动 OCR');
                };
                reader.readAsDataURL(file);
              }
              e.target.value = '';
            }}
          />
          <button
            className="icon-btn"
            type="button"
            title="新会话（清空当前模块的对话与画布）"
            aria-label="新会话"
            onClick={() => {
              if (session.messages.length === 0 && !draft) {
                toast('当前已经是空白会话', 'info');
                return;
              }
              clearSession();
              toast('已开始新会话');
              taRef.current?.focus();
            }}
            disabled={streaming}
          >
            <Icon name="refresh" size={16} />
          </button>
          <button
            className={`icon-btn ${listening ? 'is-recording' : ''}`}
            type="button"
            title={listening ? '停止语音输入' : '语音输入（Chrome/Edge）'}
            aria-label="语音输入"
            onClick={toggleMic}
            disabled={streaming}
          >
            <Icon name="mic" size={16} />
          </button>
          <button
            className="icon-btn"
            type="button"
            title="拍题/公式图片（发送时自动 OCR）"
            onClick={() => fileRef.current?.click()}
            disabled={streaming || ocrBusy}
          >
            <Icon name="paperclip" size={17} />
          </button>

          <span className="composer-hint">
            Enter 发送 · Shift+Enter 换行 · <kbd>{MOD_KEY}</kbd> K 搜索
          </span>
          {draft.length > 120 && <span className={`composer-count ${draft.length > 500 ? 'is-warn' : ''}`}>{draft.length} 字</span>}
          {ocrBusy && <span className="composer-count">OCR 识别中…</span>}

          {streaming ? (
            <button className="btn btn-stop" type="button" onClick={stop}>
              <Icon name="stop" size={14} /> 停止
            </button>
          ) : (
            <button className="btn btn-primary btn-send" type="button" disabled={!canSend} onClick={() => void submit()}>
              <Icon name="send" size={15} /> 发送
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

/* Web Speech API 的最小类型（避免依赖 lib.dom 的 experimental 声明） */
interface SpeechResultLike {
  results: ArrayLike<ArrayLike<{ transcript: string }>>;
}
interface SpeechRecognitionLike {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  onresult: ((ev: SpeechResultLike) => void) | null;
  onend: (() => void) | null;
  onerror: (() => void) | null;
  start: () => void;
  stop: () => void;
}
